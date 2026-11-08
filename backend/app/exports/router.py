from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope
from app.core.storage import storage

from .schemas import ExportRequest
from .service import create_export, get_export, get_export_file

router = APIRouter(prefix="/export-jobs", tags=["导出"])


@router.post("", status_code=202)
def create(
    request: Request,
    body: ExportRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, _ = create_export(db, user_id, body, idempotency_key)
    return envelope(request, result.model_dump(by_alias=True), status_code=202)


@router.get("/{export_id}")
def detail(
    request: Request,
    export_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = get_export(db, user_id, export_id)
    return envelope(request, result.model_dump(by_alias=True))


@router.get("/{export_id}/download")
def download(
    export_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    export, mime_type = get_export_file(db, user_id, export_id)
    return FileResponse(
        storage.path(export.storage_key),
        media_type=mime_type,
        filename=export.file_name,
    )
