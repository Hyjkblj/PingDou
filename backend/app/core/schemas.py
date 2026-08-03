from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class AppSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorBody(AppSchema):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class ErrorEnvelope(AppSchema):
    request_id: str
    error: ErrorBody


class AsyncJobView(AppSchema):
    id: str
    type: str
    status: str
    progress: int = Field(ge=0, le=100)
    stage: str | None = None
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: ErrorBody | None = None

