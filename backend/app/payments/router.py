from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.responses import envelope

from .schemas import PaymentCallbackRequest
from .service import handle_payment_callback

router = APIRouter(prefix="/payments", tags=["支付"])


@router.post("/callback/{channel}")
def payment_callback(
    request: Request,
    channel: str,
    body: PaymentCallbackRequest,
    db: Session = Depends(get_db),
):
    """支付渠道回调接口

    该接口由支付渠道调用，不使用用户 JWT。
    需要验证渠道签名（Fake 实现中跳过签名验证）。
    """
    handle_payment_callback(
        db,
        order_id=body.order_id,
        channel=channel,
        amount_cents=body.amount_cents,
        status=body.status,
        channel_transaction_id=body.channel_transaction_id,
    )
    return envelope(request, {"status": "ok"})
