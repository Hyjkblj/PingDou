from datetime import datetime

from app.core.schemas import AppSchema


class EntitlementView(AppSchema):
    id: str
    project_id: str
    status: str
    source_asset_limit: int
    source_assets_used: int = 0
    ai_jobs_total: int
    ai_jobs_used: int
    edit_expires_at: datetime | None = None
    download_expires_at: datetime | None = None
