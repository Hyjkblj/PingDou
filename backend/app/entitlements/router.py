from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .service import get_entitlement

router = APIRouter(prefix="/service-entitlements", tags=["服务权益"])


@router.get("/{entitlement_id}")
def detail(
    request: Request,
    entitlement_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = get_entitlement(db, user_id, entitlement_id)
    return envelope(request, result.model_dump(by_alias=True))
