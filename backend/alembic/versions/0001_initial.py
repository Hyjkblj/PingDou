"""Initial PingDou backend schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

from app.core.db import Base
import app.domain.models  # noqa: F401

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
