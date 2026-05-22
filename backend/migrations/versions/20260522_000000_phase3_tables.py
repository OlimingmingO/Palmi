"""Phase 3 tables: elder_profiles, configurators, pke_query_logs, unmet_needs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # elder_profiles
    op.create_table(
        "elder_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, comment="Structured understanding doc (Markdown)"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1", comment="Version number, increments on update"),
        sa.Column("last_updated_by", sa.String(16), nullable=False, server_default="configurator", comment="Source: configurator / system / elder"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_elder_profiles_elder_version", "elder_profiles", ["elder_id", "version"])

    # configurators
    op.create_table(
        "configurators",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("login_name", sa.String(128), nullable=False, comment="Login identifier (email or username)"),
        sa.Column("nickname", sa.String(64), nullable=True, comment="Display name"),
        sa.Column("relationship", sa.String(32), nullable=False, comment="子女/社工/邻居/老伴/本人"),
        sa.Column("phone", sa.String(20), nullable=True, comment="Phone for emergency SMS fallback"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false", comment="Primary contact for notifications"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login_name"),
    )
    op.create_index("idx_configurators_elder", "configurators", ["elder_id"])

    # pke_query_logs
    op.create_table(
        "pke_query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False, comment="User message that triggered the query"),
        sa.Column("result_snippet", sa.Text(), nullable=True, comment="First 200 chars of PKE response"),
        sa.Column("hit", sa.Boolean(), nullable=False, server_default="false", comment="Whether PKE returned non-empty result"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0", comment="Query duration in milliseconds"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pke_query_logs_elder_created", "pke_query_logs", ["elder_id", "created_at"])

    # unmet_needs
    op.create_table(
        "unmet_needs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("need_description", sa.Text(), nullable=False, comment="Extracted need description"),
        sa.Column("need_category", sa.String(64), nullable=False, comment="Need category (e.g., 购物类, 打车类)"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8", comment="Detection confidence 0.0-1.0"),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1", comment="Times this category appeared for this elder"),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default="false", comment="Marked as false positive by ops"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_unmet_needs_elder_category", "unmet_needs", ["elder_id", "need_category"])
    op.create_index("idx_unmet_needs_dismissed", "unmet_needs", ["is_dismissed"])


def downgrade() -> None:
    op.drop_index("idx_unmet_needs_dismissed", table_name="unmet_needs")
    op.drop_index("idx_unmet_needs_elder_category", table_name="unmet_needs")
    op.drop_table("unmet_needs")
    op.drop_index("idx_pke_query_logs_elder_created", table_name="pke_query_logs")
    op.drop_table("pke_query_logs")
    op.drop_index("idx_configurators_elder", table_name="configurators")
    op.drop_table("configurators")
    op.drop_index("idx_elder_profiles_elder_version", table_name="elder_profiles")
    op.drop_table("elder_profiles")
