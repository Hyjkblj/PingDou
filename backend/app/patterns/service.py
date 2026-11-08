import math
from collections import Counter
from datetime import timedelta

from PIL import Image
from sqlalchemy.orm import Session

from app.assets.service import asset_view, create_derived_asset
from app.core.db import utcnow
from app.core.errors import AppError
from app.core.storage import storage
from app.domain.access import require_entitlement
from app.domain.enums import (
    AssetType,
    EntitlementStatus,
    JobType,
    ProjectStatus,
    RedemptionCodeStatus,
)
from app.domain.models import (
    Asset,
    BaseImageVersion,
    EntitlementEvent,
    Order,
    Palette,
    PaletteColor,
    Pattern,
    PatternOperation,
    PatternSnapshot,
    Project,
    RedemptionCode,
    ServiceEntitlement,
)
from app.jobs.service import create_job, run_eager_job, to_job_view

from .engine import encode_locked, encode_matrix, matrix_checksum, render_preview, score_matrix
from .engine import generate_matrix as convert_image
from .schemas import (
    CellPatchRequest,
    CreatePatternVersionRequest,
    PatternGenerationRequest,
    ReplaceColorRequest,
)


def create_generation_job(
    db: Session, user_id: str, body: PatternGenerationRequest, idempotency_key: str
):
    entitlement = require_entitlement(db, user_id, body.project_id)
    base = db.query(BaseImageVersion).filter(
        BaseImageVersion.id == body.base_image_version_id,
        BaseImageVersion.project_id == body.project_id,
    ).first()
    if not base:
        raise AppError("BASE_IMAGE_VERSION_NOT_FOUND", "已确认基底不存在", status_code=404)
    palette = db.query(Palette).filter(
        Palette.id == body.palette.id,
        Palette.version == body.palette.version,
        Palette.status == "ACTIVE",
    ).first()
    if not palette:
        raise AppError("PALETTE_VERSION_NOT_FOUND", "色板版本不存在", status_code=404)
    all_colors = db.query(PaletteColor).filter(
        PaletteColor.palette_id == palette.id,
        PaletteColor.enabled.is_(True),
    ).order_by(PaletteColor.sort_order).all()
    colors = [
        color for color in all_colors if color.id not in set(body.palette.disabled_color_ids)
    ]
    if len(colors) < 2:
        raise AppError("PALETTE_VERSION_NOT_FOUND", "可用色号不足", status_code=400)
    if base.background_palette_color_id and base.background_palette_color_id not in {
        color.id for color in colors
    }:
        raise AppError("COLOR_NOT_IN_PALETTE", "背景色号不属于锁定色板", status_code=400)
    job, created = create_job(
        db,
        user_id=user_id,
        project_id=body.project_id,
        job_type=JobType.PATTERN_GENERATION,
        idempotency_key=idempotency_key,
        initial_stage="MAPPING_PALETTE",
    )
    if created:
        def worker():
            input_asset_id = base.foreground_asset_id or base.source_asset_id
            input_asset = db.query(Asset).filter(Asset.id == input_asset_id).first()
            image = Image.open(storage.path(input_asset.storage_key))
            if base.mask_asset_id:
                mask_asset = db.query(Asset).filter(Asset.id == base.mask_asset_id).first()
                mask = Image.open(storage.path(mask_asset.storage_key)).convert("L")
                image = image.convert("RGBA")
                image.putalpha(mask.resize(image.size))
            matrix = convert_image(
                image,
                base,
                colors,
                width=body.grid.width,
                height=body.grid.height,
                max_colors=body.options.max_colors,
            )
            checksum = matrix_checksum(matrix, all_colors)
            score = score_matrix(matrix)
            preview_bytes = render_preview(matrix, all_colors)
            preview = create_derived_asset(
                db,
                user_id=user_id,
                project_id=body.project_id,
                asset_type=AssetType.PATTERN_PREVIEW,
                file_name="pattern-preview.png",
                mime_type="image/png",
                content=preview_bytes,
                width=body.grid.width * 8,
                height=body.grid.height * 8,
            )
            pattern = Pattern(
                project_id=body.project_id,
                base_image_version_id=base.id,
                palette_id=palette.id,
                palette_version=palette.version,
                version=1,
                width=body.grid.width,
                height=body.grid.height,
                bead_size_mm=body.grid.bead_size_mm,
                background_mode=base.background_mode,
                matrix=matrix,
                locked_cells=[],
                params=body.model_dump(by_alias=True),
                score=score,
                matrix_checksum=checksum,
                preview_asset_id=preview.id,
            )
            db.add(pattern)
            db.flush()
            project = db.query(Project).filter(Project.id == body.project_id).first()
            project.current_pattern_id = pattern.id
            project.cover_asset_id = preview.id
            project.status = ProjectStatus.EDITING
            edit_hours, retention_days = _entitlement_policy(db, entitlement)
            now = utcnow()
            if entitlement.edit_expires_at is None:
                entitlement.edit_expires_at = now + timedelta(hours=edit_hours)
            if entitlement.download_expires_at is None:
                entitlement.download_expires_at = now + timedelta(days=retention_days)
            entitlement.status = EntitlementStatus.GENERATED
            entitlement.version += 1
            redemption = db.query(RedemptionCode).filter(
                RedemptionCode.id == entitlement.redemption_code_id
            ).first()
            if redemption:
                redemption.status = RedemptionCodeStatus.GENERATED
                redemption.code_ciphertext = None
            db.add(
                EntitlementEvent(
                    entitlement_id=entitlement.id,
                    event_type="PATTERN_GENERATED",
                    payload={"patternId": pattern.id, "version": 1},
                )
            )
            db.commit()
            db.refresh(pattern)
            db.refresh(preview)
            usage = Counter(cell for row in matrix for cell in row if cell)
            return {
                "patternId": pattern.id,
                "patternVersion": pattern.version,
                "matrixChecksum": checksum,
                "score": score,
                "colorCount": len(usage),
                "beadCount": sum(usage.values()),
                "previewAsset": asset_view(preview).model_dump(by_alias=True),
                "autoRepairApplied": True,
            }

        run_eager_job(db, job, worker, failure_code="PATTERN_GENERATION_FAILED")
    db.refresh(job)
    return to_job_view(job), created


def get_pattern(db: Session, user_id: str, pattern_id: str) -> dict:
    pattern = _require_pattern(db, user_id, pattern_id)
    colors = _pattern_colors(db, pattern)
    return {
        "id": pattern.id,
        "projectId": pattern.project_id,
        "version": pattern.version,
        "width": pattern.width,
        "height": pattern.height,
        "beadSizeMm": pattern.bead_size_mm,
        "backgroundMode": pattern.background_mode,
        "paletteId": pattern.palette_id,
        "paletteVersion": pattern.palette_version,
        "matrix": {
            "encoding": "RLE_UINT16_BASE64",
            "data": encode_matrix(pattern.matrix, colors),
            "checksum": pattern.matrix_checksum,
            "colorIndex": [
                {"index": index + 1, "colorId": color.id, "code": color.code, "rgb": color.rgb}
                for index, color in enumerate(colors)
            ],
        },
        "lockedCells": {
            "encoding": "BITSET_BASE64",
            "data": encode_locked(pattern.width, pattern.height, pattern.locked_cells),
        },
        "score": pattern.score,
        "colorUsage": color_usage(db, user_id, pattern.id, pattern.version, 0.05),
        "previewUrl": (
            f"/api/v1/assets/{pattern.preview_asset_id}/content"
            if pattern.preview_asset_id
            else None
        ),
    }


def patch_cells(
    db: Session, user_id: str, pattern_id: str, body: CellPatchRequest
) -> dict:
    pattern = _require_editable_pattern(db, user_id, pattern_id)
    replay = _operation_replay(db, pattern.id, body.operation_id)
    if replay:
        return replay
    _check_version(pattern, body.pattern_version)
    allowed = {color.id for color in _pattern_colors(db, pattern)}
    matrix = [row[:] for row in pattern.matrix]
    locked = set(pattern.locked_cells)
    delta: Counter[str] = Counter()
    for change in body.changes:
        outside_grid = (
            change.row < 0
            or change.row >= pattern.height
            or change.column < 0
            or change.column >= pattern.width
        )
        if outside_grid:
            raise AppError("CELL_OUT_OF_RANGE", "单元格坐标越界", status_code=400)
        key = f"{change.row}:{change.column}"
        if key in locked:
            raise AppError("LOCKED_CELL_MODIFICATION", "尝试修改锁定格", status_code=409)
        if change.to_color_id and change.to_color_id not in allowed:
            raise AppError("COLOR_NOT_IN_PALETTE", "色号不属于锁定色板", status_code=400)
        current = matrix[change.row][change.column]
        if current != change.from_color_id:
            raise AppError(
                "PATTERN_CELL_CONFLICT",
                "单元格已发生变化",
                status_code=409,
                details={"row": change.row, "column": change.column, "currentColorId": current},
            )
        if current:
            delta[current] -= 1
        if change.to_color_id:
            delta[change.to_color_id] += 1
        matrix[change.row][change.column] = change.to_color_id
    pattern.matrix = matrix
    pattern.version += 1
    pattern.matrix_checksum = matrix_checksum(matrix, _pattern_colors(db, pattern))
    response = {
        "patternVersion": pattern.version,
        "appliedChanges": len(body.changes),
        "beadCount": sum(1 for row in matrix for cell in row if cell),
        "matrixChecksum": pattern.matrix_checksum,
        "colorUsageDelta": [
            {"colorId": color_id, "delta": count} for color_id, count in delta.items() if count
        ],
    }
    _save_operation(db, pattern.id, body.operation_id, "CELLS", response)
    db.commit()
    return response


def replace_color(
    db: Session, user_id: str, pattern_id: str, body: ReplaceColorRequest
) -> dict:
    pattern = _require_editable_pattern(db, user_id, pattern_id)
    replay = _operation_replay(db, pattern.id, body.operation_id)
    if replay:
        return replay
    _check_version(pattern, body.pattern_version)
    allowed = {color.id for color in _pattern_colors(db, pattern)}
    if body.to_color_id and body.to_color_id not in allowed:
        raise AppError("COLOR_NOT_IN_PALETTE", "色号不属于锁定色板", status_code=400)
    matrix = [row[:] for row in pattern.matrix]
    locked = set(pattern.locked_cells)
    changed = 0
    for row in range(pattern.height):
        for column in range(pattern.width):
            if matrix[row][column] != body.from_color_id:
                continue
            if f"{row}:{column}" in locked:
                if body.respect_locked_cells:
                    continue
                raise AppError("LOCKED_CELL_MODIFICATION", "尝试修改锁定格", status_code=409)
            matrix[row][column] = body.to_color_id
            changed += 1
    pattern.matrix = matrix
    pattern.version += 1
    pattern.matrix_checksum = matrix_checksum(matrix, _pattern_colors(db, pattern))
    response = {
        "patternVersion": pattern.version,
        "replacedCells": changed,
        "beadCount": sum(1 for row in matrix for cell in row if cell),
        "matrixChecksum": pattern.matrix_checksum,
    }
    _save_operation(db, pattern.id, body.operation_id, "REPLACE_COLOR", response)
    db.commit()
    return response


def create_snapshot(
    db: Session, user_id: str, pattern_id: str, body: CreatePatternVersionRequest
) -> dict:
    pattern = _require_editable_pattern(db, user_id, pattern_id)
    _check_version(pattern, body.pattern_version)
    snapshot = PatternSnapshot(
        pattern_id=pattern.id,
        pattern_version=pattern.version,
        name=body.name,
        note=body.note,
        matrix=pattern.matrix,
        locked_cells=pattern.locked_cells,
        checksum=pattern.matrix_checksum,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {
        "id": snapshot.id,
        "patternId": pattern.id,
        "patternVersion": snapshot.pattern_version,
        "name": snapshot.name,
        "note": snapshot.note,
        "createdAt": snapshot.created_at,
    }


def color_usage(
    db: Session,
    user_id: str,
    pattern_id: str,
    version: int | None,
    waste_rate: float,
) -> list[dict]:
    pattern = _require_pattern(db, user_id, pattern_id)
    matrix = pattern.matrix
    if version is not None and version != pattern.version:
        snapshot = db.query(PatternSnapshot).filter(
            PatternSnapshot.pattern_id == pattern.id,
            PatternSnapshot.pattern_version == version,
        ).order_by(PatternSnapshot.created_at.desc()).first()
        if not snapshot:
            raise AppError("PATTERN_VERSION_NOT_FOUND", "图纸版本不存在", status_code=404)
        matrix = snapshot.matrix
    counts = Counter(cell for row in matrix for cell in row if cell)
    total = sum(counts.values())
    colors = {color.id: color for color in _pattern_colors(db, pattern)}
    return [
        {
            "colorId": color_id,
            "code": colors[color_id].code,
            "name": colors[color_id].name,
            "rgb": colors[color_id].rgb,
            "netCount": count,
            "wasteRate": waste_rate,
            "recommendedCount": math.ceil(count * (1 + waste_rate)),
            "percentage": round(count / total, 4) if total else 0,
        }
        for color_id, count in sorted(counts.items(), key=lambda item: colors[item[0]].code)
    ]


def _require_pattern(db: Session, user_id: str, pattern_id: str) -> Pattern:
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise AppError("PATTERN_NOT_FOUND", "图纸不存在", status_code=404)
    require_entitlement(db, user_id, pattern.project_id)
    return pattern


def _require_editable_pattern(db: Session, user_id: str, pattern_id: str) -> Pattern:
    pattern = _require_pattern(db, user_id, pattern_id)
    require_entitlement(db, user_id, pattern.project_id, require_edit_window=True)
    return pattern


def _pattern_colors(db: Session, pattern: Pattern) -> list[PaletteColor]:
    return db.query(PaletteColor).filter(
        PaletteColor.palette_id == pattern.palette_id
    ).order_by(PaletteColor.sort_order).all()


def _check_version(pattern: Pattern, requested: int) -> None:
    if pattern.version != requested:
        raise AppError(
            "PATTERN_VERSION_CONFLICT",
            "图纸已在其他位置更新",
            status_code=409,
            details={"currentVersion": pattern.version},
        )


def _operation_replay(db: Session, pattern_id: str, operation_id: str) -> dict | None:
    operation = db.query(PatternOperation).filter(
        PatternOperation.pattern_id == pattern_id,
        PatternOperation.operation_id == operation_id,
    ).first()
    return operation.response_body if operation else None


def _save_operation(
    db: Session, pattern_id: str, operation_id: str, operation_type: str, response: dict
) -> None:
    db.add(
        PatternOperation(
            pattern_id=pattern_id,
            operation_id=operation_id,
            operation_type=operation_type,
            response_body=response,
        )
    )


def _entitlement_policy(db: Session, entitlement: ServiceEntitlement) -> tuple[int, int]:
    redemption = db.query(RedemptionCode).filter(
        RedemptionCode.id == entitlement.redemption_code_id
    ).first()
    order = db.query(Order).filter(Order.id == redemption.order_id).first() if redemption else None
    snapshot = order.product_snapshot if order else {}
    return snapshot.get("edit_window_hours", 72), snapshot.get("download_retention_days", 30)
