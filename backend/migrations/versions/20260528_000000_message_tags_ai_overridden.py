"""Allow 'ai_overridden' source on message_tags

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replace the source CHECK constraint to permit the 'ai_overridden' value
    # used by the tag-correction flow (PATCH /api/admin/tags/{id}).
    op.drop_constraint("ck_message_tags_source", "message_tags", type_="check")
    op.create_check_constraint(
        "ck_message_tags_source",
        "message_tags",
        "source IN ('llm', 'manual', 'ai_overridden')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_message_tags_source", "message_tags", type_="check")
    op.create_check_constraint(
        "ck_message_tags_source",
        "message_tags",
        "source IN ('llm', 'manual')",
    )
