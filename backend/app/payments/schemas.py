from datetime import datetime
from typing import Any

from app.core.schemas import AppSchema


class PaymentCallbackRequest(AppSchema):
    """支付渠道回调请求（由支付渠道调用，非前端调用）"""
    order_id: str
    channel: str
    channel_transaction_id: str | None = None
    amount_cents: int
    status: str  # SUCCESS, FAILED
    raw_data: dict[str, Any] | None = None
