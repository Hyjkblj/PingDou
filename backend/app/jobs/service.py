"""Async job lifecycle and ownership checks."""

from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.enums import JobStatus
from app.domain.models import AsyncJob

from .schemas import AsyncJobView, JobErrorView


def create_job(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    job_type: str,
    idempotency_key: str,
    initial_stage: str,
) -> tuple[AsyncJob, bool]:
    existing = (
        db.query(AsyncJob)
        .filter(
            AsyncJob.project_id == project_id,
            AsyncJob.type == job_type,
            AsyncJob.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing:
        if existing.user_id != user_id:
            raise AppError("AUTH_REQUIRED", "无权访问该任务", status_code=403)
        return existing, False
    job = AsyncJob(
        user_id=user_id,
        project_id=project_id,
        type=job_type,
        idempotency_key=idempotency_key,
        status=JobStatus.QUEUED,
        progress=0,
        stage=initial_stage,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True


def run_eager_job(
    db: Session,
    job: AsyncJob,
    worker: Callable[[], dict[str, Any]],
    *,
    failure_code: str,
) -> None:
    if job.status == JobStatus.SUCCEEDED:
        return
    job.status = JobStatus.RUNNING
    job.progress = 10
    db.commit()
    try:
        result = worker()
        job.result = jsonable_encoder(result)
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        job.stage = "COMPLETED"
        job.error_code = None
        job.error_message = None
        db.commit()
    except AppError as exc:
        db.rollback()
        current = db.query(AsyncJob).filter(AsyncJob.id == job.id).first()
        if current:
            current.status = JobStatus.FAILED
            current.error_code = exc.code
            current.error_message = exc.message
            db.commit()
        raise
    except Exception as exc:
        db.rollback()
        current = db.query(AsyncJob).filter(AsyncJob.id == job.id).first()
        if current:
            current.status = JobStatus.FAILED
            current.error_code = failure_code
            current.error_message = str(exc)
            db.commit()
        raise AppError(failure_code, "任务执行失败", status_code=500, retryable=True) from exc


def to_job_view(job: AsyncJob) -> AsyncJobView:
    error = None
    if job.status == JobStatus.FAILED and job.error_code:
        error = JobErrorView(
            code=job.error_code,
            message=job.error_message or "任务执行失败",
            retryable=True,
        )
    return AsyncJobView(
        id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
        error=error,
    )


def get_job(db: Session, user_id: str, job_id: str) -> AsyncJobView:
    job = (
        db.query(AsyncJob)
        .filter(AsyncJob.id == job_id, AsyncJob.user_id == user_id)
        .first()
    )
    if not job:
        raise AppError("JOB_NOT_FOUND", "任务不存在", status_code=404)
    return to_job_view(job)


def cancel_job(db: Session, user_id: str, job_id: str) -> AsyncJobView:
    job = (
        db.query(AsyncJob)
        .filter(AsyncJob.id == job_id, AsyncJob.user_id == user_id)
        .first()
    )
    if not job:
        raise AppError("JOB_NOT_FOUND", "任务不存在", status_code=404)
    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise AppError("JOB_NOT_CANCELLABLE", "当前状态不能取消", status_code=409)
    job.status = JobStatus.CANCELLED
    db.commit()
    return to_job_view(job)
