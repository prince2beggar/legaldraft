"""007 Sprint S7: Intake and Triage (M11)

Revision ID: 007_s7_intake_triage_m11
Revises: 006_s6_cases_home_notifications
Create Date: 2026-10-07

Adds:
- intake_sessions table (one-question-per-screen intake, answers, profile, urgency)
- emergency_contacts table (admin-managed, verification timestamps, categories)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_s7_intake_triage_m11"
down_revision: str | None = "006_s6_cases_home_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. intake_sessions table
    if "intake_sessions" not in tables:
        op.create_table(
            "intake_sessions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(64),
                sa.ForeignKey("trust_users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("status", sa.String(32), server_default="in_progress", nullable=False),
            sa.Column("current_step", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("triage_chips_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("urgency", sa.String(32), server_default="normal", nullable=False),
            sa.Column("urgency_reason", sa.Text(), nullable=True),
            sa.Column("answers_json", sa.Text(), server_default="{}", nullable=False),
            sa.Column("profile_json", sa.Text(), nullable=True),
            sa.Column(
                "created_case_id",
                sa.String(64),
                sa.ForeignKey("cases.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.String(64), nullable=False),
            sa.Column("updated_at", sa.String(64), nullable=False),
        )

    # 2. emergency_contacts table
    if "emergency_contacts" not in tables:
        op.create_table(
            "emergency_contacts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("phone", sa.String(64), nullable=False),
            sa.Column("category", sa.String(64), server_default="emergency", nullable=False),
            sa.Column("description_bn", sa.Text(), nullable=True),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("last_verified_at", sa.String(64), nullable=True),
            sa.Column("verified_by", sa.String(64), nullable=True),
            sa.Column("source_note", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "emergency_contacts" in tables:
        op.drop_table("emergency_contacts")

    if "intake_sessions" in tables:
        op.drop_table("intake_sessions")
