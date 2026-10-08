"""008 Sprint S9: Brief, Secure Links, and Sharing (M08)

Revision ID: 008_s9_brief_links_m08
Revises: 007_s7_intake_triage_m11
Create Date: 2026-10-08

Adds:
- briefs table (generated case briefs, confirmed facts/events, lawyer notes)
- brief_links table (secure token hashes, recipient contact, OTP verification, access counts)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_s9_brief_links_m08"
down_revision: str | None = "007_s7_intake_triage_m11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. briefs table
    if "briefs" not in tables:
        op.create_table(
            "briefs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "case_id",
                sa.String(64),
                sa.ForeignKey("cases.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "owner_id",
                sa.String(64),
                sa.ForeignKey("trust_users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("sections_json", sa.Text(), nullable=False),
            sa.Column("is_edited", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
            sa.Column("updated_at", sa.String(64), nullable=False),
        )

    # 2. brief_links table
    if "brief_links" not in tables:
        op.create_table(
            "brief_links",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "consent_id",
                sa.String(64),
                sa.ForeignKey("trust_consents.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "case_id",
                sa.String(64),
                sa.ForeignKey("cases.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("recipient_contact", sa.String(128), nullable=False),
            sa.Column("otp_hash", sa.String(64), nullable=True),
            sa.Column("otp_expires_at", sa.String(64), nullable=True),
            sa.Column("otp_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("otp_locked_until", sa.String(64), nullable=True),
            sa.Column("otp_verified_at", sa.String(64), nullable=True),
            sa.Column("view_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("last_viewed_at", sa.String(64), nullable=True),
            sa.Column("expires_at", sa.String(64), nullable=False),
            sa.Column("revoked_at", sa.String(64), nullable=True),
            sa.Column("created_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "brief_links" in tables:
        op.drop_table("brief_links")

    if "briefs" in tables:
        op.drop_table("briefs")
