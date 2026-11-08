"""Seed the local product, users, palette and one development redemption code."""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db import SessionLocal, utcnow
from app.core.security import encrypt_redemption_code, hash_redemption_code
from app.domain.enums import OrderStatus, RedemptionCodeStatus
from app.domain.models import Order, Product, RedemptionCode, User
from app.palettes.service import ensure_default_palette


def seed() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == "13800000000").first()
        if not user:
            user = User(phone="13800000000", phone_masked="138****0000")
            db.add(user)
            db.flush()
        admin = db.query(User).filter(User.phone == "13900000000").first()
        if not admin:
            admin = User(
                phone="13900000000",
                phone_masked="139****0000",
                is_admin=True,
            )
            db.add(admin)
            db.flush()
        product = db.query(Product).filter(
            Product.name == "AI 拼豆图纸制作兑换码"
        ).first()
        if not product:
            product = Product(
                name="AI 拼豆图纸制作兑换码",
                price_cents=1290,
                list_price_cents=1990,
                currency="CNY",
                source_asset_limit=1,
                ai_candidate_count=2,
                edit_window_hours=72,
                download_retention_days=30,
                code_validity_days=180,
                export_formats=["PNG", "PDF", "CSV"],
                refund_policy_version="2026-08-01",
                is_active=True,
            )
            db.add(product)
            db.flush()
        test_code = "PD-TEST-CODE-FOR-DEV"
        code_hash = hash_redemption_code(test_code).encode("utf-8")
        redemption = db.query(RedemptionCode).filter(
            RedemptionCode.code_hash == code_hash
        ).first()
        if not redemption:
            order = Order(
                user_id=user.id,
                product_id=product.id,
                product_snapshot={
                    "name": product.name,
                    "source_asset_limit": product.source_asset_limit,
                    "ai_jobs_total": 1,
                    "ai_candidate_count": product.ai_candidate_count,
                    "edit_window_hours": product.edit_window_hours,
                    "download_retention_days": product.download_retention_days,
                    "code_validity_days": product.code_validity_days,
                    "export_formats": product.export_formats,
                },
                amount_cents=product.price_cents,
                channel="WECHAT_PAY",
                status=OrderStatus.PAID,
                idempotency_key="seed-development-order",
                paid_at=utcnow(),
            )
            db.add(order)
            db.flush()
            db.add(
                RedemptionCode(
                    order_id=order.id,
                    code_hash=code_hash,
                    code_ciphertext=encrypt_redemption_code(test_code),
                    code_hint="DEV",
                    status=RedemptionCodeStatus.UNREDEEMED,
                    expires_at=utcnow() + timedelta(days=180),
                )
            )
        ensure_default_palette(db)
        db.commit()
        print("Seed complete. Login: 13800000000, SMS: 123456")
        print(f"Development redemption code: {test_code}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
