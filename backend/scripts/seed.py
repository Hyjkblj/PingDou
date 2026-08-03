"""Seed 数据脚本

写入测试用户、商品、色板和业务码。
运行方式：python -m scripts.seed
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db import SyncSessionLocal, Base, sync_engine
from app.core.security import generate_redemption_code, hash_redemption_code, encrypt_redemption_code
from app.domain.models import Product, User, RedemptionCode
from app.domain.enums import RedemptionCodeStatus
from datetime import datetime, timedelta, timezone


def utcnow():
    return datetime.now(timezone.utc)


def seed():
    """写入测试数据"""
    # 创建表
    Base.metadata.create_all(sync_engine)

    db = SyncSessionLocal()
    try:
        # 测试用户
        user = db.query(User).filter(User.phone == "13800000000").first()
        if not user:
            user = User(
                phone="13800000000",
                phone_masked="138****0000",
                is_admin=False,
            )
            db.add(user)
            db.flush()
            print(f"[Seed] 创建测试用户: {user.phone_masked} (ID: {user.id})")

        # 管理员用户
        admin = db.query(User).filter(User.phone == "13900000000").first()
        if not admin:
            admin = User(
                phone="13900000000",
                phone_masked="139****0000",
                is_admin=True,
            )
            db.add(admin)
            db.flush()
            print(f"[Seed] 创建管理员用户: {admin.phone_masked} (ID: {admin.id})")

        # 商品
        product = db.query(Product).filter(Product.name == "AI 拼豆图纸制作兑换码").first()
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
            print(f"[Seed] 创建商品: {product.name} (ID: {product.id})")

        # 测试业务码（未兑换）
        existing_code = db.query(RedemptionCode).filter(
            RedemptionCode.code_hint == "TEST"
        ).first()
        if not existing_code:
            test_code = "PD-TEST-CODE-FOR-DEV"
            code_hash = hash_redemption_code(test_code).encode("utf-8")
            code_ciphertext = encrypt_redemption_code(test_code)
            rc = RedemptionCode(
                order_id="00000000-0000-0000-0000-000000000001",
                code_hash=code_hash,
                code_ciphertext=code_ciphertext,
                code_hint="TEST",
                status=RedemptionCodeStatus.UNREDEEMED,
                expires_at=utcnow() + timedelta(days=180),
            )
            db.add(rc)
            print(f"[Seed] 创建测试业务码: {test_code}")

        db.commit()
        print("[Seed] 完成！")

    except Exception as e:
        db.rollback()
        print(f"[Seed] 错误: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
