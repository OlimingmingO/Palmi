"""Add channel to conversations and last_message_read to trigger_state

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-28 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("channel", sa.String(16), nullable=True))
    op.add_column("trigger_state", sa.Column("last_message_read", sa.Boolean(),
                  nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("trigger_state", "last_message_read")
    op.drop_column("conversations", "channel")
