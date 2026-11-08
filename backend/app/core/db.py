from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def is_past(value: datetime) -> bool:
    """Compare timestamps consistently when a database drops timezone metadata."""
    return value.replace(tzinfo=None) < utcnow().replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


settings = get_settings()

# 根据数据库 URL 选择驱动和连接池参数
connect_args: dict = {}
engine_options: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # MySQL 默认会回收空闲连接，主动回收可避免取到服务端已关闭的连接。
    engine_options["pool_recycle"] = 1800

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **engine_options,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
