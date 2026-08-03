"""认证服务

处理短信验证码发送、手机号登录和令牌刷新。
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.domain.models import SmsVerification, User

from .schemas import (
    RefreshTokenResponse,
    SendSmsResponse,
    SmsLoginResponse,
    UserView,
)

settings = get_settings()


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****0000"""
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return phone


def send_sms_code(db: Session, phone: str, scene: str) -> SendSmsResponse:
    """发送短信验证码（Fake 实现：使用固定验证码）"""
    # 检查频率限制：60 秒内只能发送一次
    recent = (
        db.query(SmsVerification)
        .filter(
            SmsVerification.phone == phone,
            SmsVerification.created_at > utcnow() - timedelta(seconds=60),
        )
        .first()
    )
    if recent:
        raise AppError("RATE_LIMITED", "请求过于频繁，请稍后再试", status_code=429)

    # Fake 实现：使用固定验证码
    code = settings.fake_sms_code
    verification = SmsVerification(
        phone=phone,
        code=code,
        scene=scene,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    db.add(verification)
    db.commit()

    # 实际生产环境这里会调用 SMS Provider
    print(f"[FakeSMS] 向 {phone} 发送验证码: {code}")

    return SendSmsResponse(cooldown_seconds=60)


def login_with_sms(db: Session, phone: str, code: str) -> SmsLoginResponse:
    """手机号验证码登录"""
    # 查找最近 5 分钟内的有效验证码
    verification = (
        db.query(SmsVerification)
        .filter(
            SmsVerification.phone == phone,
            SmsVerification.code == code,
            SmsVerification.used == False,
            SmsVerification.expires_at > utcnow(),
        )
        .order_by(SmsVerification.created_at.desc())
        .first()
    )
    if not verification:
        raise AppError("SMS_CODE_INVALID", "验证码错误或已过期", status_code=400)

    # 标记验证码已使用
    verification.used = True

    # 查找或创建用户
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, phone_masked=mask_phone(phone))
        db.add(user)
        db.flush()

    # 生成令牌
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    db.commit()

    return SmsLoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_ttl_seconds,
        refresh_token=refresh_token,
        user=UserView(id=user.id, phone_masked=user.phone_masked),
    )


def refresh_token(db: Session, refresh_token_str: str) -> RefreshTokenResponse:
    """刷新访问令牌"""
    user_id = decode_token(refresh_token_str, "refresh")

    # 验证用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError("AUTH_REQUIRED", "用户不存在", status_code=401)

    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_ttl_seconds,
        refresh_token=new_refresh_token,
    )


def get_current_user(db: Session, user_id: str) -> UserView:
    """获取当前用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError("AUTH_REQUIRED", "用户不存在", status_code=401)
    return UserView(id=user.id, phone_masked=user.phone_masked)
