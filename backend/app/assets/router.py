from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope
from app.core.storage import storage

from .schemas import UploadCompleteRequest, UploadInitRequest
from .service import complete_upload, init_upload, require_asset, write_upload

router = APIRouter(tags=["素材"])


@router.post("/assets/upload-init")
def upload_init(
    request: Request,
    body: UploadInitRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, created = init_upload(db, user_id, body, idempotency_key)
    return envelope(
        request,
        result.model_dump(by_alias=True),
        status_code=201 if created else 200,
    )


@router.put("/uploads/{upload_id}/content", status_code=204)
async def upload_content(
    upload_id: str,
    request: Request,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    write_upload(db, user_id, upload_id, await request.body())
    return Response(status_code=204)


@router.post("/assets/upload-complete")
def upload_complete(
    request: Request,
    body: UploadCompleteRequest,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result, created = complete_upload(db, user_id, body.upload_id)
    return envelope(
        request,
        result.model_dump(by_alias=True),
        status_code=201 if created else 200,
    )


@router.get("/assets/{asset_id}/content")
def asset_content(
    asset_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    asset = require_asset(db, user_id, asset_id)
    return FileResponse(storage.path(asset.storage_key), media_type=asset.mime_type)
