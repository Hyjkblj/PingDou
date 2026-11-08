import hashlib
import io

from PIL import Image, ImageDraw

from app.domain.models import Pattern, RedemptionCode, ServiceEntitlement


def _source_image() -> bytes:
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 12, 48, 52), fill="#D83A3A")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _paid_project(client, db, auth_headers, seed_product):
    order = client.post(
        "/api/v1/orders",
        json={"productId": seed_product.id, "channel": "WECHAT_PAY"},
        headers={**auth_headers, "Idempotency-Key": "workflow-order"},
    ).json()["data"]
    callback = {
        "orderId": order["id"],
        "channel": "WECHAT_PAY",
        "channelTransactionId": "txn-workflow",
        "amountCents": seed_product.price_cents,
        "status": "SUCCESS",
    }
    assert client.post("/api/v1/payments/callback/WECHAT_PAY", json=callback).status_code == 200
    assert client.post("/api/v1/payments/callback/WECHAT_PAY", json=callback).status_code == 200
    assert db.query(RedemptionCode).count() == 1
    order_detail = client.get(
        f"/api/v1/orders/{order['id']}", headers=auth_headers
    ).json()["data"]
    code = order_detail["redemptionCode"]["code"]
    redeemed = client.post(
        "/api/v1/redemption-codes/redeem",
        json={"code": code},
        headers={**auth_headers, "Idempotency-Key": "workflow-redeem"},
    )
    assert redeemed.status_code == 201
    replay = client.post(
        "/api/v1/redemption-codes/redeem",
        json={"code": code},
        headers={**auth_headers, "Idempotency-Key": "workflow-redeem"},
    )
    assert replay.status_code == 200
    assert replay.json()["data"]["project"]["id"] == redeemed.json()["data"]["project"]["id"]
    return redeemed.json()["data"]


def _upload_source(client, auth_headers, project_id):
    content = _source_image()
    initialized = client.post(
        "/api/v1/assets/upload-init",
        json={
            "projectId": project_id,
            "fileName": "portrait.png",
            "mimeType": "image/png",
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        },
        headers={**auth_headers, "Idempotency-Key": "workflow-upload"},
    )
    assert initialized.status_code == 201
    upload_id = initialized.json()["data"]["uploadId"]
    assert client.put(
        f"/api/v1/uploads/{upload_id}/content",
        content=content,
        headers={**auth_headers, "Content-Type": "image/png"},
    ).status_code == 204
    completed = client.post(
        "/api/v1/assets/upload-complete",
        json={"uploadId": upload_id},
        headers=auth_headers,
    )
    assert completed.status_code == 201
    return completed.json()["data"]


def test_complete_toc_workflow(client, db, auth_headers, seed_product, monkeypatch):
    redeemed = _paid_project(client, db, auth_headers, seed_product)
    project_id = redeemed["project"]["id"]
    source = _upload_source(client, auth_headers, project_id)

    removal = client.post(
        "/api/v1/background-removal/jobs",
        json={
            "projectId": project_id,
            "sourceAssetId": source["id"],
            "strength": "STANDARD",
        },
        headers={**auth_headers, "Idempotency-Key": "workflow-removal"},
    )
    assert removal.status_code == 202
    removal_result = removal.json()["data"]["result"]

    preview = client.post(
        f"/api/v1/projects/{project_id}/base-image-previews",
        json={
            "sourceAssetId": source["id"],
            "foregroundAssetId": removal_result["foregroundAsset"]["id"],
            "maskAssetId": removal_result["maskAsset"]["id"],
            "crop": {"x": 0, "y": 0, "width": 1, "height": 1},
            "background": {"mode": "WHITE_PREVIEW", "paletteColorId": None},
        },
        headers=auth_headers,
    )
    assert preview.status_code == 201
    assert preview.json()["data"]["estimatedBackgroundBeadCount"] == 0
    assert preview.json()["data"]["backgroundCountsAsBeads"] is False

    confirmed = client.post(
        f"/api/v1/projects/{project_id}/base-images/confirm",
        json={"baseImagePreviewId": preview.json()["data"]["id"]},
        headers={**auth_headers, "Idempotency-Key": "workflow-confirm"},
    )
    assert confirmed.status_code == 201
    base_version_id = confirmed.json()["data"]["id"]

    palettes = client.get("/api/v1/palettes").json()["data"]
    palette = palettes[0]
    ai_body = {
        "projectId": project_id,
        "sourceAssetId": source["id"],
        "style": "ANIME",
        "similarity": "HIGH",
        "detailLevel": "STANDARD",
        "composition": "PORTRAIT",
        "backgroundMode": "WHITE_PREVIEW",
        "constraints": {
            "targetGrid": {"width": 16, "height": 16},
            "beadSizeMm": 5,
            "paletteId": palette["id"],
            "paletteVersion": palette["version"],
            "maxColors": 8,
            "outlineProtection": "STANDARD",
        },
        "candidateCount": 2,
    }
    from app.imaging.service import image_provider

    original_generate = image_provider.generate_candidates

    def provider_failure(content, count):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(image_provider, "generate_candidates", provider_failure)
    failed_ai = client.post(
        "/api/v1/ai-generation/jobs",
        json=ai_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-ai-failed"},
    )
    assert failed_ai.status_code == 500
    entitlement = db.query(ServiceEntitlement).filter(
        ServiceEntitlement.project_id == project_id
    ).first()
    db.refresh(entitlement)
    assert entitlement.ai_jobs_used == 0
    monkeypatch.setattr(image_provider, "generate_candidates", original_generate)
    successful_ai = client.post(
        "/api/v1/ai-generation/jobs",
        json=ai_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-ai-success"},
    )
    assert successful_ai.status_code == 202
    assert len(successful_ai.json()["data"]["result"]["candidates"]) == 2
    exhausted_ai = client.post(
        "/api/v1/ai-generation/jobs",
        json=ai_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-ai-exhausted"},
    )
    assert exhausted_ai.status_code == 403
    assert exhausted_ai.json()["error"]["code"] == "AI_QUOTA_EXHAUSTED"

    generated = client.post(
        "/api/v1/patterns/generation-jobs",
        json={
            "projectId": project_id,
            "baseImageVersionId": base_version_id,
            "grid": {"width": 16, "height": 16, "beadSizeMm": 5},
            "palette": {"id": palette["id"], "version": palette["version"], "disabledColorIds": []},
            "options": {"maxColors": 8},
        },
        headers={**auth_headers, "Idempotency-Key": "workflow-pattern"},
    )
    assert generated.status_code == 202
    generation_result = generated.json()["data"]["result"]
    assert 0 < generation_result["beadCount"] < 16 * 16
    pattern_id = generation_result["patternId"]
    pattern_detail = client.get(f"/api/v1/patterns/{pattern_id}", headers=auth_headers)
    assert pattern_detail.status_code == 200
    assert (
        pattern_detail.json()["data"]["matrix"]["checksum"]
        == generation_result["matrixChecksum"]
    )

    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    row, column = next(
        (row_index, column_index)
        for row_index, row_values in enumerate(pattern.matrix)
        for column_index, value in enumerate(row_values)
        if value
    )
    current_color = pattern.matrix[row][column]
    edit_body = {
        "patternVersion": 1,
        "operationId": "workflow-operation",
        "changes": [
            {
                "row": row,
                "column": column,
                "fromColorId": current_color,
                "toColorId": None,
            }
        ],
    }
    edited = client.patch(
        f"/api/v1/patterns/{pattern_id}/cells",
        json=edit_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-edit"},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["patternVersion"] == 2
    replay = client.patch(
        f"/api/v1/patterns/{pattern_id}/cells",
        json=edit_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-edit"},
    )
    assert replay.json()["data"] == edited.json()["data"]
    conflict_body = {**edit_body, "operationId": "workflow-conflict"}
    conflict = client.patch(
        f"/api/v1/patterns/{pattern_id}/cells",
        json=conflict_body,
        headers={**auth_headers, "Idempotency-Key": "workflow-conflict"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "PATTERN_VERSION_CONFLICT"

    for export_format in ("PNG", "PDF", "CSV"):
        exported = client.post(
            "/api/v1/export-jobs",
            json={
                "patternId": pattern_id,
                "patternVersion": 2,
                "format": export_format,
                "options": {"includeMaterialList": True, "wasteRate": 0.05},
            },
            headers={**auth_headers, "Idempotency-Key": f"workflow-export-{export_format}"},
        )
        assert exported.status_code == 202
        export_data = exported.json()["data"]
        assert export_data["status"] == "SUCCEEDED"
        download = client.get(export_data["downloadUrl"], headers=auth_headers)
        assert download.status_code == 200
        assert len(download.content) > 20
