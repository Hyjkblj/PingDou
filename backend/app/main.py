"""PingDou API 入口

FastAPI 应用配置，包含路由注册、中间件安装和异常处理。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db import Base, engine
from app.core.errors import install_error_handlers
from app.core.middleware import install_middleware

from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.redemption.router import router as redemption_router
from app.entitlements.router import router as entitlements_router
from app.jobs.router import router as jobs_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建表，关闭时清理连接"""
    # 开发环境自动建表（生产环境使用 Alembic 迁移）
    if not settings.is_production:
        Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="拼豆图纸生成平台 API",
    description="PingDou Backend API - 拼豆图纸生成与 AI 美化平台",
    version="0.1.0",
    lifespan=lifespan,
)

# 安装中间件和异常处理
install_middleware(app)
install_error_handlers(app)

# 注册路由
app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(redemption_router, prefix="/api/v1")
app.include_router(entitlements_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
