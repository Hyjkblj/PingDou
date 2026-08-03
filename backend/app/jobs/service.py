"""异步任务服务"""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.enums import JobStatus
from app.domain.models import AsyncJob

from .schemas import AsyncJobView, JobErrorView


def get_job(db: Session, user_id: str, job_id: str) -> AsyncJobView:
    """查询异步任务状态"""
    job = db.query(AsyncJob).filter(
        AsyncJob.id == job_id,
        AsyncJob.user_id == user_id,
    ).first()

    if not job:
        raise AppError("JOB_NOT_FOUND", "任务不存在", status_code=404)

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


def cancel_job(db: Session, user_id: str, job_id: str) -> AsyncJobView:
    """取消异步任务"""
    job = db.query(AsyncJob).filter(
        AsyncJob.id == job_id,
        AsyncJob.user_id == user_id,
    ).first()

    if not job:
        raise AppError("JOB_NOT_FOUND", "任务不存在", status_code=404)

    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise AppError("JOB_NOT_CANCELLABLE", "当前状态不能取消", status_code=409)

    job.status = JobStatus.CANCELLED
    db.commit()

    return get_job(db, user_id, job_id)
