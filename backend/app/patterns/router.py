from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import (
    CellPatchRequest,
    CreatePatternVersionRequest,
    PatternGenerationRequest,
    ReplaceColorRequest,
)
from .service import (
    color_usage,
    create_generation_job,
    create_snapshot,
    get_pattern,
    patch_cells,
    replace_color,
)

router = APIRouter(tags=["图纸"])


@router.post("/patterns/generation-jobs", status_code=202)
def generation_job(
    request: Request,
    body: PatternGenerationRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, _ = create_generation_job(db, user_id, body, idempotency_key)
    return envelope(request, result.model_dump(by_alias=True), status_code=202)


@router.get("/patterns/{pattern_id}")
def detail(
    request: Request,
    pattern_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return envelope(request, get_pattern(db, user_id, pattern_id))


@router.patch("/patterns/{pattern_id}/cells")
def update_cells(
    request: Request,
    pattern_id: str,
    body: CellPatchRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    return envelope(request, patch_cells(db, user_id, pattern_id, body))


@router.post("/patterns/{pattern_id}/replace-color")
def replace(
    request: Request,
    pattern_id: str,
    body: ReplaceColorRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    return envelope(request, replace_color(db, user_id, pattern_id, body))


@router.post("/patterns/{pattern_id}/versions", status_code=201)
def version(
    request: Request,
    pattern_id: str,
    body: CreatePatternVersionRequest,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return envelope(request, create_snapshot(db, user_id, pattern_id, body), status_code=201)


@router.get("/patterns/{pattern_id}/color-usage")
def usage(
    request: Request,
    pattern_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
    version: int | None = None,
    waste_rate: float = Query(0.05, alias="wasteRate", ge=0, le=0.5),
):
    return envelope(request, color_usage(db, user_id, pattern_id, version, waste_rate))
