import hashlib
import io
import re
from datetime import timedelta
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import is_past, utcnow
from app.core.errors import AppError
from app.core.storage import storage
from app.domain.access import require_entitlement, require_project
from app.domain.enums import AssetType, EntitlementStatus
from app.domain.models import Asset, EntitlementEvent, UploadSession

from .schemas import AssetView, UploadInitRequest, UploadInitResponse

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_ASSET_TYPES = {AssetType.SOURCE_IMAGE, AssetType.SUBJECT_MASK}


def _safe_name(file_name: str) -> str:
    name = Path(file_name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return cleaned[:180] or "image"


def asset_view(asset: Asset) -> AssetView:
    return AssetView(
        id=asset.id,
        type=asset.type,
        file_name=asset.file_name,
        mime_type=asset.mime_type,
        size=asset.size,
        width=asset.width,
        height=asset.height,
        preview_url=f"/api/v1/assets/{asset.id}/content",
        created_at=asset.created_at,
    )


def init_upload(
    db: Session,
    user_id: str,
    body: UploadInitRequest,
    idempotency_key: str,
) -> tuple[UploadInitResponse, bool]:
    require_entitlement(db, user_id, body.project_id)
    settings = get_settings()
    if body.size <= 0 or body.size > settings.max_upload_bytes:
        raise AppError("FILE_TOO_LARGE", "文件超过限制", status_code=413)
    if body.mime_type not in ALLOWED_MIME_TYPES:
        raise AppError("FILE_TYPE_UNSUPPORTED", "文件格式不支持", status_code=400)
    if body.asset_type not in ALLOWED_ASSET_TYPES:
        raise AppError("FILE_TYPE_UNSUPPORTED", "不支持该资产类型", status_code=400)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", body.sha256):
        raise AppError("VALIDATION_ERROR", "sha256 格式错误", status_code=422)
    existing = (
        db.query(UploadSession)
        .filter(
            UploadSession.project_id == body.project_id,
            UploadSession.sha256 == body.sha256.lower(),
            UploadSession.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing:
        return _upload_response(existing), False
    session = UploadSession(
        project_id=body.project_id,
        user_id=user_id,
        asset_type=body.asset_type,
        file_name=_safe_name(body.file_name),
        mime_type=body.mime_type,
        size=body.size,
        sha256=body.sha256.lower(),
        storage_key=(
            f"users/{user_id}/projects/{body.project_id}/uploads/"
            f"{hashlib.sha256(idempotency_key.encode()).hexdigest()}"
        ),
        idempotency_key=idempotency_key,
        expires_at=utcnow() + timedelta(minutes=15),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _upload_response(session), True


def _upload_response(session: UploadSession) -> UploadInitResponse:
    return UploadInitResponse(
        upload_id=session.id,
        upload_url=f"/api/v1/uploads/{session.id}/content",
        headers={"Content-Type": session.mime_type},
        expires_at=session.expires_at,
    )


def write_upload(db: Session, user_id: str, upload_id: str, content: bytes) -> None:
    session = _require_upload(db, user_id, upload_id)
    if is_past(session.expires_at):
        raise AppError("UPLOAD_EXPIRED", "上传会话已过期", status_code=410)
    if len(content) != session.size:
        raise AppError(
            "UPLOAD_SIZE_MISMATCH",
            "上传文件大小不一致",
            status_code=400,
            details={"expected": session.size, "actual": len(content)},
        )
    storage.write(session.storage_key, content)
    session.status = "UPLOADED"
    db.commit()


def complete_upload(db: Session, user_id: str, upload_id: str) -> tuple[AssetView, bool]:
    session = _require_upload(db, user_id, upload_id)
    existing = db.query(Asset).filter(Asset.upload_id == upload_id).first()
    if existing:
        return asset_view(existing), False
    if session.status != "UPLOADED" or not storage.exists(session.storage_key):
        raise AppError("UPLOAD_INCOMPLETE", "文件尚未上传完成", status_code=409)
    actual_hash = storage.sha256(session.storage_key)
    if actual_hash != session.sha256:
        raise AppError("UPLOAD_HASH_MISMATCH", "文件校验失败", status_code=400)
    raw = storage.read(session.storage_key)
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
        width, height = image.size
        detected_mime = Image.MIME.get(image.format, "")
    except (UnidentifiedImageError, OSError) as exc:
        raise AppError("IMAGE_DECODE_FAILED", "图片无法解析", status_code=400) from exc
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise AppError("FILE_TYPE_UNSUPPORTED", "文件格式不支持", status_code=400)
    if width < 32 or height < 32:
        raise AppError("IMAGE_TOO_SMALL", "图片分辨率过低且无法继续", status_code=400)
    entitlement = require_entitlement(db, user_id, session.project_id)
    if session.asset_type == AssetType.SOURCE_IMAGE and entitlement.source_asset_id:
        raise AppError("SOURCE_ASSET_LIMIT_REACHED", "该服务已绑定源图", status_code=409)
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[
        detected_mime
    ]
    asset = Asset(
        project_id=session.project_id,
        user_id=user_id,
        upload_id=session.id,
        type=session.asset_type,
        file_name=session.file_name,
        mime_type=detected_mime,
        size=len(raw),
        width=width,
        height=height,
        sha256=actual_hash,
        storage_key=f"users/{user_id}/projects/{session.project_id}/source/{session.id}{extension}",
    )
    storage.copy(session.storage_key, asset.storage_key)
    db.add(asset)
    db.flush()
    if session.asset_type == AssetType.SOURCE_IMAGE:
        entitlement.source_asset_id = asset.id
        entitlement.status = EntitlementStatus.ACTIVE
        entitlement.version += 1
        db.add(
            EntitlementEvent(
                entitlement_id=entitlement.id,
                event_type="SOURCE_ASSET_BOUND",
                payload={"assetId": asset.id},
            )
        )
    session.status = "COMPLETED"
    db.commit()
    db.refresh(asset)
    return asset_view(asset), True


def require_asset(db: Session, user_id: str, asset_id: str, project_id: str | None = None) -> Asset:
    query = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user_id)
    if project_id:
        query = query.filter(Asset.project_id == project_id)
    asset = query.first()
    if not asset:
        raise AppError("ASSET_NOT_FOUND", "图片资产不存在", status_code=404)
    return asset


def create_derived_asset(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    asset_type: str,
    file_name: str,
    mime_type: str,
    content: bytes,
    width: int,
    height: int,
    metadata: dict | None = None,
) -> Asset:
    digest = hashlib.sha256(content).hexdigest()
    extension = {"image/png": ".png", "text/csv": ".csv", "application/pdf": ".pdf"}.get(
        mime_type, ""
    )
    asset = Asset(
        project_id=project_id,
        user_id=user_id,
        type=asset_type,
        file_name=file_name,
        mime_type=mime_type,
        size=len(content),
        width=width,
        height=height,
        sha256=digest,
        storage_key="pending",
        metadata_json=metadata or {},
    )
    db.add(asset)
    db.flush()
    asset.storage_key = f"users/{user_id}/projects/{project_id}/derived/{asset.id}{extension}"
    storage.write(asset.storage_key, content)
    db.flush()
    return asset


def _require_upload(db: Session, user_id: str, upload_id: str) -> UploadSession:
    session = (
        db.query(UploadSession)
        .filter(UploadSession.id == upload_id, UploadSession.user_id == user_id)
        .first()
    )
    if not session:
        raise AppError("UPLOAD_NOT_FOUND", "上传会话不存在", status_code=404)
    require_project(db, user_id, session.project_id)
    return session
