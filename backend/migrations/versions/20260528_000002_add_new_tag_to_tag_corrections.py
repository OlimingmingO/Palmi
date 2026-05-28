"""Add new_tag column to tag_corrections for multi-tag correction audit

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-28 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tag_corrections",
        sa.Column("new_tag", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tag_corrections", "new_tag")
