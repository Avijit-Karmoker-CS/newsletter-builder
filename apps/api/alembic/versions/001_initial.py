"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("plan", sa.Enum("free", "premium", name="plantype"), nullable=False),
        sa.Column("brand_color", sa.String(32), nullable=True),
        sa.Column("default_background_url", sa.String(512), nullable=True),
        sa.Column("headline_style", sa.String(64), nullable=True),
        sa.Column("ai_provider", sa.String(64), nullable=True),
        sa.Column("ai_model", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.Enum("bader", "lead", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "newsletters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("headline", sa.String(255), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("background_url", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "drafting",
                "in_review",
                "changes_requested",
                "review_complete",
                "ready_to_send",
                "sent",
                name="newsletterstatus",
            ),
            nullable=False,
        ),
        sa.Column("section_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mailchimp_campaign_id", sa.String(128), nullable=True),
        sa.Column("mailchimp_editor_url", sa.String(512), nullable=True),
        sa.Column("slack_message_ts", sa.String(64), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_newsletters_status", "newsletters", ["status"])

    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("newsletter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("newsletters.id"), nullable=False),
        sa.Column(
            "section_type",
            sa.Enum("news", "featured_story", "tips", "events", "cta", name="sectiontype"),
            nullable=False,
        ),
        sa.Column("layout_key", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("image_urls", sa.JSON(), nullable=True),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "section_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("newsletter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("newsletters.id"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("newsletter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("newsletters.id"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("assets")
    op.drop_table("review_events")
    op.drop_table("section_comments")
    op.drop_table("sections")
    op.drop_index("ix_newsletters_status", table_name="newsletters")
    op.drop_table("newsletters")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("workspaces")
    op.execute("DROP TYPE IF EXISTS newsletterstatus")
    op.execute("DROP TYPE IF EXISTS sectiontype")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS plantype")
