from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.schemas import AppSchema


class CreateProjectRequest(AppSchema):
    name: str = "未命名拼豆项目"


class UpdateProjectRequest(AppSchema):
    name: str | None = None


class ProjectSummary(AppSchema):
    id: str
    name: str
    status: str
    cover_url: str | None = None
    entitlement_id: str | None = None
    latest_pattern_id: str | None = None
    updated_at: datetime


class ProjectDetail(ProjectSummary):
    source_assets: list[dict[str, Any]] = Field(default_factory=list)
    base_image_version: dict[str, Any] | None = None
    pattern: dict[str, Any] | None = None
    entitlement: dict[str, Any] | None = None


class ProjectList(AppSchema):
    items: list[ProjectSummary]
    next_cursor: str | None = None
