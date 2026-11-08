from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import (
    AiGenerationRequest,
    BackgroundRemovalRequest,
    BaseImageConfirmRequest,
    BaseImagePreviewRequest,
    ImageAnalysisRequest,
)
from .service import (
    confirm_base_image,
    create_ai_job,
    create_analysis_job,
    create_background_removal_job,
    create_base_preview,
)

router = APIRouter(tags=["图片处理"])


@router.post("/image-analysis/jobs", status_code=202)
def analysis_job(
    request: Request,
    body: ImageAnalysisRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, _ = create_analysis_job(db, user_id, body, idempotency_key)
    return envelope(request, result.model_dump(by_alias=True), status_code=202)


@router.post("/background-removal/jobs", status_code=202)
def background_removal_job(
    request: Request,
    body: BackgroundRemovalRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, _ = create_background_removal_job(db, user_id, body, idempotency_key)
    return envelope(request, result.model_dump(by_alias=True), status_code=202)


@router.post("/projects/{project_id}/base-image-previews", status_code=201)
def base_preview(
    request: Request,
    project_id: str,
    body: BaseImagePreviewRequest,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = create_base_preview(db, user_id, project_id, body)
    return envelope(request, result, status_code=201)


@router.post("/projects/{project_id}/base-images/confirm")
def base_confirm(
    request: Request,
    project_id: str,
    body: BaseImageConfirmRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, created = confirm_base_image(db, user_id, project_id, body)
    return envelope(
        request,
        result.model_dump(by_alias=True),
        status_code=201 if created else 200,
    )


@router.post("/ai-generation/jobs", status_code=202)
def ai_job(
    request: Request,
    body: AiGenerationRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    result, _ = create_ai_job(db, user_id, body, idempotency_key)
    return envelope(request, result.model_dump(by_alias=True), status_code=202)
