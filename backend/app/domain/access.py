"""Shared authorization checks for project-owned resources."""

from sqlalchemy.orm import Session

from app.core.db import is_past
from app.core.errors import AppError
from app.domain.enums import EntitlementStatus
from app.domain.models import Project, ServiceEntitlement


def require_project(db: Session, user_id: str, project_id: str) -> Project:
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.deleted_at.is_(None),
        )
        .first()
    )
    if not project:
        raise AppError("PROJECT_NOT_FOUND", "项目不存在", status_code=404)
    return project


def require_entitlement(
    db: Session,
    user_id: str,
    project_id: str,
    *,
    require_edit_window: bool = False,
    require_download_window: bool = False,
) -> ServiceEntitlement:
    require_project(db, user_id, project_id)
    entitlement = (
        db.query(ServiceEntitlement)
        .filter(ServiceEntitlement.project_id == project_id)
        .first()
    )
    if not entitlement or entitlement.status == EntitlementStatus.VOIDED:
        raise AppError("ENTITLEMENT_UNAVAILABLE", "服务权益不可用", status_code=403)
    if require_edit_window and entitlement.edit_expires_at and is_past(entitlement.edit_expires_at):
        raise AppError("EDIT_WINDOW_EXPIRED", "编辑期已结束", status_code=403)
    if (
        require_download_window
        and entitlement.download_expires_at
        and is_past(entitlement.download_expires_at)
    ):
        raise AppError("DOWNLOAD_EXPIRED", "项目下载期已结束", status_code=403)
    return entitlement
