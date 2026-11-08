import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .service import cancel_job, get_job

router = APIRouter(prefix="/jobs", tags=["任务"])


@router.get("/{job_id}")
def detail(
    request: Request,
    job_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = get_job(db, user_id, job_id)
    return envelope(request, result.model_dump(by_alias=True))


@router.get("/{job_id}/events")
async def events(
    request: Request,
    job_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """SSE 事件流，客户端断开后可使用 GET /jobs/{jobId} 轮询"""
    async def event_generator():
        last_status = None
        while True:
            job = get_job(db, user_id, job_id)
            if job.status != last_status:
                data = json.dumps({
                    "status": job.status,
                    "progress": job.progress,
                    "stage": job.stage,
                })
                terminal = job.status in ("SUCCEEDED", "FAILED", "CANCELLED")
                event_type = "job.completed" if terminal else "job.progress"
                yield f"event: {event_type}\ndata: {data}\n\n"
                last_status = job.status
                if job.status in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    break
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/cancel")
def cancel(
    request: Request,
    job_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = cancel_job(db, user_id, job_id)
    return envelope(request, result.model_dump(by_alias=True))
