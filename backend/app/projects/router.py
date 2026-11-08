from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import CreateProjectRequest, UpdateProjectRequest
from .service import create_project, delete_project, get_project, list_projects, update_project

router = APIRouter(prefix="/projects", tags=["项目"])


@router.get("")
def list_items(
    request: Request,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    query: str | None = None,
):
    result = list_projects(
        db, user_id, cursor=cursor, limit=limit, status=status_filter, query=query
    )
    return envelope(request, result.model_dump(by_alias=True))


@router.post("", status_code=status.HTTP_201_CREATED)
def create(
    request: Request,
    body: CreateProjectRequest,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = create_project(db, user_id, body)
    return envelope(request, result.model_dump(by_alias=True), status_code=201)


@router.get("/{project_id}")
def detail(
    request: Request,
    project_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = get_project(db, user_id, project_id)
    return envelope(request, result.model_dump(by_alias=True))


@router.patch("/{project_id}")
def update(
    request: Request,
    project_id: str,
    body: UpdateProjectRequest,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = update_project(db, user_id, project_id, body)
    return envelope(request, result.model_dump(by_alias=True))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    project_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    delete_project(db, user_id, project_id)
    return None
