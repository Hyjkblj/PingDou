"""Central SQLAlchemy models for the PingDou domain."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BINARY,
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, utcnow


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    phone_masked: Mapped[str] = mapped_column(String(20), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    list_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    source_asset_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_candidate_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    edit_window_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    download_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    code_validity_days: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    export_formats: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    refund_policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False
    )
    product_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_PAYMENT", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_order_user_idempotency"),
        Index("ix_orders_user_status", "user_id", "status"),
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), default="未命名拼豆项目", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True)
    cover_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_base_image_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_pattern_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_projects_user_updated", "user_id", "updated_at"),)


class RedemptionCode(Base, TimestampMixin):
    __tablename__ = "redemption_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), unique=True, nullable=False
    )
    # HMAC-SHA256 十六进制摘要固定为 64 字节；BINARY 可在 MySQL 中直接建立唯一索引。
    code_hash: Mapped[bytes] = mapped_column(BINARY(64), unique=True, nullable=False)
    code_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    code_hint: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="UNREDEEMED", nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), unique=True
    )
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ServiceEntitlement(Base, TimestampMixin):
    __tablename__ = "service_entitlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    redemption_code_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redemption_codes.id"), unique=True, nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", nullable=False)
    source_asset_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    source_asset_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_jobs_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_jobs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    edit_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    download_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EntitlementEvent(Base):
    __tablename__ = "entitlement_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    entitlement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_entitlements.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class UploadSession(Base, TimestampMixin):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), default="SOURCE_IMAGE", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="INITIALIZED", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "project_id", "sha256", "idempotency_key", name="uq_upload_idempotency"
        ),
    )


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    upload_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("upload_sessions.id"), unique=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)


class BaseImagePreview(Base, TimestampMixin):
    __tablename__ = "base_image_previews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    source_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    foreground_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id"))
    mask_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id"))
    preview_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    crop: Mapped[dict] = mapped_column(JSON, nullable=False)
    background_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    background_palette_color_id: Mapped[str | None] = mapped_column(String(36))
    estimated_background_bead_count: Mapped[int] = mapped_column(Integer, default=0)


class BaseImageVersion(Base, TimestampMixin):
    __tablename__ = "base_image_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    preview_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("base_image_previews.id"), unique=True, nullable=False
    )
    source_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    foreground_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id"))
    mask_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id"))
    preview_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    crop: Mapped[dict] = mapped_column(JSON, nullable=False)
    background_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    background_palette_color_id: Mapped[str | None] = mapped_column(String(36))
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Palette(Base, TimestampMixin):
    __tablename__ = "palettes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    brand: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    series: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    __table_args__ = (UniqueConstraint("brand", "series", "version", name="uq_palette_version"),)


class PaletteColor(Base, TimestampMixin):
    __tablename__ = "palette_colors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    palette_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("palettes.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    rgb: Mapped[str] = mapped_column(String(7), nullable=False)
    lab: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attributes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("palette_id", "code", name="uq_palette_color_code"),)


class Pattern(Base, TimestampMixin):
    __tablename__ = "patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    base_image_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("base_image_versions.id"), nullable=False
    )
    palette_id: Mapped[str] = mapped_column(String(36), ForeignKey("palettes.id"), nullable=False)
    palette_version: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    bead_size_mm: Mapped[float] = mapped_column(Float, nullable=False)
    background_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    matrix: Mapped[list] = mapped_column(JSON, nullable=False)
    locked_cells: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    score: Mapped[dict] = mapped_column(JSON, nullable=False)
    matrix_checksum: Mapped[str] = mapped_column(String(80), nullable=False)
    preview_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id"))


class PatternOperation(Base):
    __tablename__ = "pattern_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pattern_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patterns.id"), nullable=False, index=True
    )
    operation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    response_body: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("pattern_id", "operation_id", name="uq_pattern_operation"),
    )


class PatternSnapshot(Base, TimestampMixin):
    __tablename__ = "pattern_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pattern_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patterns.id"), nullable=False, index=True
    )
    pattern_version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    matrix: Mapped[list] = mapped_column(JSON, nullable=False)
    locked_cells: Mapped[list] = mapped_column(JSON, nullable=False)
    checksum: Mapped[str] = mapped_column(String(80), nullable=False)


class ExportJob(Base, TimestampMixin):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    pattern_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patterns.id"), nullable=False, index=True
    )
    pattern_version: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    options: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), unique=True)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    retained_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "pattern_id", "pattern_version", "idempotency_key", name="uq_export_idempotency"
        ),
    )


class AsyncJob(Base, TimestampMixin):
    __tablename__ = "async_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str | None] = mapped_column(String(50))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("project_id", "type", "idempotency_key", name="uq_job_idempotency"),
        Index("ix_jobs_user_status", "user_id", "status"),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SmsVerification(Base):
    __tablename__ = "sms_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    scene: Mapped[str] = mapped_column(String(20), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scope: Mapped[str] = mapped_column(String(200), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)
