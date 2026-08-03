import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import AppError


settings = get_settings()


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def create_token(subject: str, token_type: str, ttl_seconds: int) -> str:
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str, expected_type: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AppError("TOKEN_EXPIRED", "登录状态已过期", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError("AUTH_REQUIRED", "请先登录", status_code=401) from exc
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise AppError("AUTH_REQUIRED", "请先登录", status_code=401)
    return str(payload["sub"])


def generate_redemption_code() -> str:
    """生成安全随机业务码，排除 O/0/I/1，格式 PD-XXXX-XXXX-XXXX-XXXX"""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    chunks = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "PD-" + "-".join(chunks)


def hash_redemption_code(code: str) -> str:
    """使用 HMAC 哈希业务码用于存储和校验"""
    normalized = code.strip().upper().encode("utf-8")
    return hmac.new(settings.secret_key.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


def encrypt_redemption_code(code: str) -> bytes:
    """KMS 信封加密业务码明文，用于未兑换阶段交付"""
    return _fernet().encrypt(code.encode("utf-8"))


def decrypt_redemption_code(ciphertext: bytes) -> str:
    """解密业务码明文"""
    return _fernet().decrypt(ciphertext).decode("utf-8")


def create_access_token(user_id: str) -> str:
    return create_token(user_id, "access", settings.access_token_ttl_seconds)


def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, "refresh", settings.refresh_token_ttl_seconds)
