from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.schemas import AppSchema


class ExportRequest(AppSchema):
    pattern_id: str
    pattern_version: int
    format: str
    options: dict[str, Any] = Field(default_factory=dict)


class ExportView(AppSchema):
    export_id: str
    status: str
    format: str
    file_name: str | None = None
    file_size: int | None = None
    page_count: int | None = None
    download_url: str | None = None
    download_url_expires_at: datetime | None = None
    retained_until: datetime | None = None
    error: dict[str, Any] | None = None
