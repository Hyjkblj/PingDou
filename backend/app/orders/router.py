from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.middleware import require_auth
from app.core.responses import envelope

from .schemas import CreateOrderRequest
from .service import create_order, get_order

router = APIRouter(prefix="/orders", tags=["订单"])


@router.post("", status_code=201)
def create(
    request: Request,
    body: CreateOrderRequest,
    user_id: str = Depends(require_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    response, is_new = create_order(
        db, user_id, body.product_id, body.channel, idempotency_key
    )
    status_code = 201 if is_new else 200
    return envelope(request, response.model_dump(by_alias=True), status_code=status_code)


@router.get("/{order_id}")
def detail(
    request: Request,
    order_id: str,
    user_id: str = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = get_order(db, user_id, order_id)
    return envelope(request, result.model_dump(by_alias=True))
