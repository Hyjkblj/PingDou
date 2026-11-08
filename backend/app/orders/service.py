"""订单服务

处理订单创建、查询和状态管理。遵循幂等性和状态机规则。
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import (
    decrypt_redemption_code,
)
from app.domain.enums import OrderStatus, RedemptionCodeStatus
from app.domain.models import Order, Product, RedemptionCode

from .schemas import (
    CreateOrderResponse,
    OrderView,
    PaymentInfo,
    PaymentPayload,
    RedemptionCodeView,
)


def create_order(
    db: Session, user_id: str, product_id: str, channel: str, idempotency_key: str
) -> tuple[CreateOrderResponse, bool]:
    """创建订单（幂等）

    Returns:
        (response, is_new): 响应和是否是新创建的订单
    """
    # 检查幂等键
    existing = db.query(Order).filter(
        Order.user_id == user_id,
        Order.idempotency_key == idempotency_key,
    ).first()
    if existing:
        response = _order_to_create_response(existing)
        return response, False

    # 查找商品
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active.is_(True),
    ).first()
    if not product:
        raise AppError("PRODUCT_UNAVAILABLE", "商品不可购买", status_code=400)

    # 创建订单
    order = Order(
        user_id=user_id,
        product_id=product.id,
        product_snapshot={
            "name": product.name,
            "price_cents": product.price_cents,
            "source_asset_limit": product.source_asset_limit,
            "ai_jobs_total": 1,
            "ai_candidate_count": product.ai_candidate_count,
            "edit_window_hours": product.edit_window_hours,
            "download_retention_days": product.download_retention_days,
            "code_validity_days": product.code_validity_days,
            "export_formats": product.export_formats,
        },
        amount_cents=product.price_cents,
        channel=channel,
        status=OrderStatus.PENDING_PAYMENT,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    response = _order_to_create_response(order)
    return response, True


def get_order(db: Session, user_id: str, order_id: str) -> OrderView:
    """查询订单详情"""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise AppError("ORDER_NOT_FOUND", "订单不存在", status_code=404)

    redemption_code_view = None
    if order.status == OrderStatus.PAID:
        rc = db.query(RedemptionCode).filter(RedemptionCode.order_id == order.id).first()
        if rc:
            # 只有未兑换的业务码才返回完整码
            code = None
            masked_code = rc.code_hint
            if rc.status == RedemptionCodeStatus.UNREDEEMED and rc.code_ciphertext:
                try:
                    code = decrypt_redemption_code(rc.code_ciphertext)
                except Exception:
                    pass

            redemption_code_view = RedemptionCodeView(
                code=code,
                masked_code=masked_code,
                status=rc.status,
                expires_at=rc.expires_at,
            )

    return OrderView(
        id=order.id,
        status=order.status,
        amount_cents=order.amount_cents,
        paid_at=order.paid_at,
        redemption_code=redemption_code_view,
    )


def _order_to_create_response(order: Order) -> CreateOrderResponse:
    """将订单转换为创建响应"""
    # Fake 支付：模拟预支付信息
    expires_at = utcnow() + timedelta(minutes=30)
    return CreateOrderResponse(
        id=order.id,
        status=order.status,
        amount_cents=order.amount_cents,
        payment=PaymentInfo(
            channel=order.channel,
            payload=PaymentPayload(prepay_id=f"fake_prepay_{order.id[:8]}"),
            expires_at=expires_at,
        ),
    )
