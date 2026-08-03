"""支付服务

处理支付回调、订单状态推进和业务码发放。
使用 Outbox 模式保证事务一致性。
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import (
    encrypt_redemption_code,
    generate_redemption_code,
    hash_redemption_code,
)
from app.domain.enums import OrderStatus, RedemptionCodeStatus
from app.domain.models import Order, OutboxEvent, RedemptionCode


def handle_payment_callback(
    db: Session,
    order_id: str,
    channel: str,
    amount_cents: int,
    status: str,
    channel_transaction_id: str | None = None,
) -> None:
    """处理支付回调

    在同一事务内推进订单状态并写入 Outbox 事件。
    重复回调返回成功但不重复发码。
    """
    # 查找订单
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise AppError("ORDER_NOT_FOUND", "订单不存在", status_code=404)

    # 验证金额
    if order.amount_cents != amount_cents:
        raise AppError("PAYMENT_AMOUNT_MISMATCH", "支付金额不一致", status_code=400)

    # 重复回调：已支付的订单直接返回成功
    if order.status == OrderStatus.PAID:
        return

    # 验证订单状态
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise AppError("ORDER_NOT_PAID", "订单状态异常", status_code=400)

    if status != "SUCCESS":
        # 支付失败，关闭订单
        order.status = OrderStatus.CLOSED
        db.commit()
        return

    # 推进订单状态
    order.status = OrderStatus.PAID
    order.paid_at = utcnow()

    # 写入 Outbox 事件（发码由 Outbox Consumer 完成）
    outbox = OutboxEvent(
        aggregate_type="Order",
        aggregate_id=order.id,
        event_type="PaymentSucceeded",
        payload={
            "order_id": order.id,
            "user_id": order.user_id,
            "product_snapshot": order.product_snapshot,
            "channel": channel,
            "channel_transaction_id": channel_transaction_id,
        },
    )
    db.add(outbox)
    db.commit()


def process_payment_outbox(db: Session, outbox_id: str) -> None:
    """处理支付成功的 Outbox 事件：发放业务码

    由 Celery Worker 调用。
    """
    outbox = db.query(OutboxEvent).filter(OutboxEvent.id == outbox_id).first()
    if not outbox or outbox.processed_at:
        return

    payload = outbox.payload
    order_id = payload["order_id"]
    product_snapshot = payload["product_snapshot"]

    # 检查是否已发码
    existing_code = db.query(RedemptionCode).filter(RedemptionCode.order_id == order_id).first()
    if existing_code:
        outbox.processed_at = utcnow()
        db.commit()
        return

    # 生成业务码
    code = generate_redemption_code()
    code_hash = hash_redemption_code(code).encode("utf-8")
    code_ciphertext = encrypt_redemption_code(code)
    code_hint = code[-4:]  # 保存后四位用于客服定位

    # 计算有效期
    validity_days = product_snapshot.get("code_validity_days", 180)
    expires_at = utcnow() + timedelta(days=validity_days)

    # 创建业务码
    redemption_code = RedemptionCode(
        order_id=order_id,
        code_hash=code_hash,
        code_ciphertext=code_ciphertext,
        code_hint=code_hint,
        status=RedemptionCodeStatus.UNREDEEMED,
        expires_at=expires_at,
    )
    db.add(redemption_code)

    # 标记 Outbox 已处理
    outbox.processed_at = utcnow()
    db.commit()

    print(f"[FakePayment] 为订单 {order_id} 发放业务码: {code}")
