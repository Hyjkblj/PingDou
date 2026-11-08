"""PingDou API 入口

FastAPI 应用配置，包含路由注册、中间件安装和异常处理。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.assets.router import router as assets_router
from app.auth.router import router as auth_router
from app.auth.router import users_router
from app.catalog.router import router as catalog_router
from app.core.errors import install_error_handlers
from app.core.middleware import install_middleware
from app.entitlements.router import router as entitlements_router
from app.exports.router import router as exports_router
from app.imaging.router import router as imaging_router
from app.jobs.router import router as jobs_router
from app.orders.router import router as orders_router
from app.palettes.router import router as palettes_router
from app.patterns.router import router as patterns_router
from app.payments.router import router as payments_router
from app.projects.router import router as projects_router
from app.redemption.router import router as redemption_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期；数据库结构统一由 Alembic 管理。"""
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
app.include_router(users_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(redemption_router, prefix="/api/v1")
app.include_router(entitlements_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(imaging_router, prefix="/api/v1")
app.include_router(palettes_router, prefix="/api/v1")
app.include_router(patterns_router, prefix="/api/v1")
app.include_router(exports_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
