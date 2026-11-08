from datetime import datetime

from app.core.schemas import AppSchema


class CreateOrderRequest(AppSchema):
    product_id: str
    channel: str


class PaymentPayload(AppSchema):
    prepay_id: str | None = None


class PaymentInfo(AppSchema):
    channel: str
    payload: PaymentPayload
    expires_at: datetime


class CreateOrderResponse(AppSchema):
    id: str
    status: str
    amount_cents: int
    payment: PaymentInfo


class RedemptionCodeView(AppSchema):
    code: str | None = None
    masked_code: str | None = None
    status: str
    expires_at: datetime


class OrderView(AppSchema):
    id: str
    status: str
    amount_cents: int
    paid_at: datetime | None = None
    redemption_code: RedemptionCodeView | None = None
