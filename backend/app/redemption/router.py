from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import RedeemRequest
from .service import redeem_code

router = APIRouter(prefix="/redemption-codes", tags=["兑换"])


@router.post("/redeem", status_code=201)
def redeem(
    request: Request,
    body: RedeemRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    response, is_new = redeem_code(db, user_id, body.code, idempotency_key)
    status_code = 201 if is_new else 200
    return envelope(request, response.model_dump(by_alias=True), status_code=status_code)
