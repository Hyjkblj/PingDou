"""服务权益服务"""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.models import Project, ServiceEntitlement

from .schemas import EntitlementView


def get_entitlement(db: Session, user_id: str, entitlement_id: str) -> EntitlementView:
    """查询服务权益"""
    entitlement = (
        db.query(ServiceEntitlement)
        .join(Project, Project.id == ServiceEntitlement.project_id)
        .filter(
            ServiceEntitlement.id == entitlement_id,
            Project.user_id == user_id,
            Project.deleted_at.is_(None),
        )
        .first()
    )

    if not entitlement:
        raise AppError("ENTITLEMENT_UNAVAILABLE", "服务权益不存在", status_code=404)

    return EntitlementView(
        id=entitlement.id,
        project_id=entitlement.project_id,
        status=entitlement.status,
        source_asset_limit=entitlement.source_asset_limit,
        source_assets_used=1 if entitlement.source_asset_id else 0,
        ai_jobs_total=entitlement.ai_jobs_total,
        ai_jobs_used=entitlement.ai_jobs_used,
        edit_expires_at=entitlement.edit_expires_at,
        download_expires_at=entitlement.download_expires_at,
    )
