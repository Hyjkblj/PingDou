from datetime import datetime

from app.core.schemas import AppSchema


class RedeemRequest(AppSchema):
    code: str


class ProjectBrief(AppSchema):
    id: str
    status: str


class EntitlementBrief(AppSchema):
    id: str
    status: str
    source_asset_limit: int
    ai_jobs_total: int
    ai_jobs_used: int
    edit_expires_at: datetime | None = None
    download_expires_at: datetime | None = None


class RedeemResponse(AppSchema):
    redemption_code_status: str
    project: ProjectBrief
    entitlement: EntitlementBrief
