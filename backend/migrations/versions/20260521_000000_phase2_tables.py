"""Phase 2 tables: trigger_logs, trigger_state, intent_tags, message_tags, tag_corrections

Revision ID: a1b2c3d4e5f6
Revises: 002
Create Date: 2026-05-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # intent_tags (no FKs, create first so other tables can reference it)
    op.create_table(
        "intent_tags",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # trigger_logs
    op.create_table(
        "trigger_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("message_content", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('sent', 'skipped', 'failed')", name="ck_trigger_logs_status"),
        sa.CheckConstraint(
            "trigger_type IN ('weather', 'festival', 'memory', 'time_gap')",
            name="ck_trigger_logs_type",
        ),
    )
    op.create_index("ix_trigger_logs_elder_id", "trigger_logs", ["elder_id"])

    # trigger_state
    op.create_table(
        "trigger_state",
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("today_trigger_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_trigger_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("today_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("elder_id"),
    )

    # message_tags
    op.create_table(
        "message_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(16), nullable=False, server_default="llm"),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["intent_tags.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source IN ('llm', 'manual')", name="ck_message_tags_source"),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_message_tags_confidence"),
    )
    op.create_index("ix_message_tags_elder_id", "message_tags", ["elder_id"])
    op.create_index("ix_message_tags_message_id", "message_tags", ["message_id"])

    # tag_corrections
    op.create_table(
        "tag_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("message_tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("corrected_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_tag_id"], ["message_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_tag_id"], ["intent_tags.id"]),
        sa.ForeignKeyConstraint(["corrected_tag_id"], ["intent_tags.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tag_corrections_message_tag_id", "tag_corrections", ["message_tag_id"])

    # Seed 9 default intent tags
    op.bulk_insert(
        sa.table(
            "intent_tags",
            sa.column("name", sa.String),
            sa.column("description", sa.Text),
            sa.column("is_active", sa.Boolean),
            sa.column("sort_order", sa.SmallInteger),
        ),
        [
            {"name": "闲聊", "description": "日常闲聊、问候、天气等轻松话题", "is_active": True, "sort_order": 1},
            {"name": "情感倾诉", "description": "表达情绪、心情、孤独、思念等", "is_active": True, "sort_order": 2},
            {"name": "健康相关", "description": "身体状况、用药、看病、健康咨询", "is_active": True, "sort_order": 3},
            {"name": "购物需求", "description": "买东西、购物相关请求", "is_active": True, "sort_order": 4},
            {"name": "出行需求", "description": "打车、出门、交通相关请求", "is_active": True, "sort_order": 5},
            {"name": "信息查询", "description": "查天气、查新闻、查知识等", "is_active": True, "sort_order": 6},
            {"name": "任务委托", "description": "请求小伴帮忙做某件具体的事", "is_active": True, "sort_order": 7},
            {"name": "社交相关", "description": "家人、朋友、社区活动相关话题", "is_active": True, "sort_order": 8},
            {"name": "其他", "description": "不属于以上分类的内容", "is_active": True, "sort_order": 9},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_tag_corrections_message_tag_id", table_name="tag_corrections")
    op.drop_table("tag_corrections")
    op.drop_index("ix_message_tags_message_id", table_name="message_tags")
    op.drop_index("ix_message_tags_elder_id", table_name="message_tags")
    op.drop_table("message_tags")
    op.drop_table("trigger_state")
    op.drop_index("ix_trigger_logs_elder_id", table_name="trigger_logs")
    op.drop_table("trigger_logs")
    op.drop_table("intent_tags")
