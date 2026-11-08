from typing import Any

from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.domain.access import require_project
from app.domain.enums import ProjectStatus
from app.domain.models import (
    Asset,
    BaseImageVersion,
    Pattern,
    Project,
    ServiceEntitlement,
)

from .schemas import (
    CreateProjectRequest,
    ProjectDetail,
    ProjectList,
    ProjectSummary,
    UpdateProjectRequest,
)


def asset_url(asset_id: str | None) -> str | None:
    if not asset_id:
        return None
    return f"/api/v1/assets/{asset_id}/content"


def project_summary(db: Session, project: Project) -> ProjectSummary:
    entitlement = (
        db.query(ServiceEntitlement)
        .filter(ServiceEntitlement.project_id == project.id)
        .first()
    )
    return ProjectSummary(
        id=project.id,
        name=project.name,
        status=project.status,
        cover_url=asset_url(project.cover_asset_id),
        entitlement_id=entitlement.id if entitlement else None,
        latest_pattern_id=project.current_pattern_id,
        updated_at=project.updated_at,
    )


def list_projects(
    db: Session,
    user_id: str,
    *,
    status: str | None = None,
    query: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> ProjectList:
    projects_query = db.query(Project).filter(
        Project.user_id == user_id,
        Project.deleted_at.is_(None),
    )
    if status:
        projects_query = projects_query.filter(Project.status == status)
    if query:
        projects_query = projects_query.filter(Project.name.ilike(f"%{query}%"))
    projects = projects_query.order_by(Project.updated_at.desc()).limit(min(limit, 100)).all()
    return ProjectList(items=[project_summary(db, item) for item in projects])


def create_project(db: Session, user_id: str, body: CreateProjectRequest) -> ProjectSummary:
    project = Project(user_id=user_id, name=body.name.strip() or "未命名拼豆项目")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_summary(db, project)


def get_project(db: Session, user_id: str, project_id: str) -> ProjectDetail:
    project = require_project(db, user_id, project_id)
    assets = db.query(Asset).filter(
        Asset.project_id == project.id,
        Asset.type == "SOURCE_IMAGE",
    ).order_by(Asset.created_at).all()
    base = None
    if project.current_base_image_version_id:
        version = db.query(BaseImageVersion).filter(
            BaseImageVersion.id == project.current_base_image_version_id
        ).first()
        if version:
            base = {
                "id": version.id,
                "backgroundMode": version.background_mode,
                "backgroundPaletteColorId": version.background_palette_color_id,
                "previewAsset": {
                    "id": version.preview_asset_id,
                    "previewUrl": asset_url(version.preview_asset_id),
                },
                "confirmedAt": version.confirmed_at,
            }
    pattern = None
    if project.current_pattern_id:
        current = db.query(Pattern).filter(Pattern.id == project.current_pattern_id).first()
        if current:
            pattern = {
                "id": current.id,
                "version": current.version,
                "width": current.width,
                "height": current.height,
                "beadCount": sum(1 for row in current.matrix for cell in row if cell),
                "matrixChecksum": current.matrix_checksum,
            }
    entitlement = db.query(ServiceEntitlement).filter(
        ServiceEntitlement.project_id == project.id
    ).first()
    entitlement_view: dict[str, Any] | None = None
    if entitlement:
        entitlement_view = {
            "id": entitlement.id,
            "status": entitlement.status,
            "aiJobsTotal": entitlement.ai_jobs_total,
            "aiJobsUsed": entitlement.ai_jobs_used,
            "editExpiresAt": entitlement.edit_expires_at,
            "downloadExpiresAt": entitlement.download_expires_at,
        }
    return ProjectDetail(
        **project_summary(db, project).model_dump(),
        source_assets=[
            {
                "id": asset.id,
                "type": asset.type,
                "fileName": asset.file_name,
                "mimeType": asset.mime_type,
                "size": asset.size,
                "width": asset.width,
                "height": asset.height,
                "previewUrl": asset_url(asset.id),
                "createdAt": asset.created_at,
            }
            for asset in assets
        ],
        base_image_version=base,
        pattern=pattern,
        entitlement=entitlement_view,
    )


def update_project(
    db: Session, user_id: str, project_id: str, body: UpdateProjectRequest
) -> ProjectSummary:
    project = require_project(db, user_id, project_id)
    if body.name is not None:
        project.name = body.name.strip() or project.name
    db.commit()
    db.refresh(project)
    return project_summary(db, project)


def delete_project(db: Session, user_id: str, project_id: str) -> None:
    project = require_project(db, user_id, project_id)
    project.deleted_at = utcnow()
    project.status = ProjectStatus.DELETED
    db.commit()
