"""Create elders table.

Revision ID: 001
Revises: None
Create Date: 2026-05-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    op.create_table(
        "elders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("wechat_user_id", sa.String(128), nullable=False, unique=True),
        sa.Column("nickname", sa.String(64), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'paused', 'archived')", name="ck_elders_status"),
    )
    op.create_index("idx_elders_status", "elders", ["status"])
    op.create_index("idx_elders_wechat_user_id", "elders", ["wechat_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_elders_wechat_user_id")
    op.drop_index("idx_elders_status")
    op.drop_table("elders")
