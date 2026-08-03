from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.security import decode_token


def install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.user_id = None
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


async def get_current_user_id(request: Request) -> str | None:
    """从 Authorization header 提取用户 ID，不强制要求登录"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        return decode_token(token, "access")
    except Exception:
        return None


async def require_auth(request: Request) -> str:
    """要求登录，返回用户 ID"""
    user_id = await get_current_user_id(request)
    if not user_id:
        from app.core.errors import AppError
        raise AppError("AUTH_REQUIRED", "请先登录", status_code=401)
    return user_id
