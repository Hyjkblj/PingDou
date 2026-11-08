from datetime import datetime

from app.core.schemas import AppSchema


class UploadInitRequest(AppSchema):
    project_id: str
    file_name: str
    mime_type: str
    size: int
    sha256: str
    asset_type: str = "SOURCE_IMAGE"


class UploadInitResponse(AppSchema):
    upload_id: str
    method: str = "PUT"
    upload_url: str
    headers: dict[str, str]
    expires_at: datetime


class UploadCompleteRequest(AppSchema):
    upload_id: str


class AssetView(AppSchema):
    id: str
    type: str
    file_name: str
    mime_type: str
    size: int
    width: int
    height: int
    preview_url: str
    created_at: datetime

