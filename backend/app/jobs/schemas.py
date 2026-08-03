from datetime import datetime
from typing import Any

from app.core.schemas import AppSchema


class AsyncJobView(AppSchema):
    id: str
    type: str
    status: str
    progress: int
    stage: str | None = None
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: "JobErrorView | None" = None


class JobErrorView(AppSchema):
    code: str
    message: str
    retryable: bool = False
