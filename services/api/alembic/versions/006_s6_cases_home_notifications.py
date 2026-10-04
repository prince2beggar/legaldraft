"""006 Sprint S6: Case Folder (M06), Home / Next Action (M02), Notifications (M07)

Revision ID: 006_s6_cases_home_notifications
Revises: 005_s5_notice_interpreter_m04
Create Date: 2026-10-04

Adds:
- case_parties table
- case_events table
- case_facts table
- case_notes table (with strict include_in_analysis flag)
- case_documents association table
- notifications table (in-app, SMS, daily digest, delivery receipts)
- notification_preferences table (channels, quiet hours 22:00-07:00)
- Enhancements to cases (legacy_matter_id for Decision D08, metadata_json)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_s6_cases_home_notifications"
down_revision: str | None = "005_s5_notice_interpreter_m04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    case_cols = [c["name"] for c in insp.get_columns("cases")] if "cases" in tables else []

    # 1. Add columns to cases
    if "cases" in tables:
        if "legacy_matter_id" not in case_cols:
            op.add_column("cases", sa.Column("legacy_matter_id", sa.String(64), nullable=True))
        if "metadata_json" not in case_cols:
            op.add_column("cases", sa.Column("metadata_json", sa.Text(), nullable=True))
        if "triage_urgency" not in case_cols:
            op.add_column("cases", sa.Column("triage_urgency", sa.String(32), nullable=True))
        if "is_urgent_triage" not in case_cols:
            op.add_column("cases", sa.Column("is_urgent_triage", sa.Boolean(), server_default=sa.text("0"), nullable=True))

    # 2. case_parties table
    if "case_parties" not in tables:
        op.create_table(
            "case_parties",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("role", sa.String(64), nullable=False),
            sa.Column("contact_info", sa.String(255), nullable=True),
        )
    else:
        party_cols = [c["name"] for c in insp.get_columns("case_parties")]
        if "contact_info" not in party_cols:
            op.add_column("case_parties", sa.Column("contact_info", sa.String(255), nullable=True))

    # 3. case_events table
    if "case_events" not in tables:
        op.create_table(
            "case_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("event_date", sa.String(32), nullable=False),
            sa.Column("date_precision", sa.String(16), server_default="day", nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )
    else:
        event_cols = [c["name"] for c in insp.get_columns("case_events")]
        if "date_precision" not in event_cols:
            op.add_column("case_events", sa.Column("date_precision", sa.String(16), server_default="day", nullable=False))
        if "event_type" not in event_cols:
            op.add_column("case_events", sa.Column("event_type", sa.String(64), server_default="other", nullable=False))

    # 4. case_facts table
    if "case_facts" not in tables:
        op.create_table(
            "case_facts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("fact_text", sa.Text(), nullable=False),
            sa.Column("source_doc_id", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), server_default="active", nullable=False),
            sa.Column("is_proposed", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )
    else:
        fact_cols = [c["name"] for c in insp.get_columns("case_facts")]
        if "fact_text" not in fact_cols:
            op.add_column("case_facts", sa.Column("fact_text", sa.Text(), nullable=True))
        if "source_doc_id" not in fact_cols:
            op.add_column("case_facts", sa.Column("source_doc_id", sa.String(64), nullable=True))
        if "status" not in fact_cols:
            op.add_column("case_facts", sa.Column("status", sa.String(32), server_default="active", nullable=False))
        if "is_proposed" not in fact_cols:
            op.add_column("case_facts", sa.Column("is_proposed", sa.Boolean(), server_default=sa.text("0"), nullable=False))

    # 5. case_notes table
    if "case_notes" not in tables:
        op.create_table(
            "case_notes",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("note_text", sa.Text(), nullable=False),
            sa.Column("is_private", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("include_in_analysis", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("include_in_brief", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
            sa.Column("updated_at", sa.String(64), nullable=False),
        )
    else:
        note_cols = [c["name"] for c in insp.get_columns("case_notes")]
        if "include_in_brief" not in note_cols:
            op.add_column("case_notes", sa.Column("include_in_brief", sa.Boolean(), server_default=sa.text("0"), nullable=False))

    # 6. case_documents table
    if "case_documents" not in tables:
        op.create_table(
            "case_documents",
            sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", sa.String(64), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("attached_at", sa.String(64), nullable=False),
            sa.PrimaryKeyConstraint("case_id", "document_id"),
        )

    # 7. notifications table
    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("channel", sa.String(32), server_default="in_app", nullable=False),
            sa.Column("category", sa.String(64), nullable=False),
            sa.Column("deadline_id", sa.String(64), nullable=True),
            sa.Column("case_id", sa.String(64), nullable=True),
            sa.Column("scheduled_at", sa.String(64), nullable=False),
            sa.Column("sent_at", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), server_default="pending", nullable=False),
            sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.String(64), nullable=False),
        )
    else:
        notif_cols = [c["name"] for c in insp.get_columns("notifications")]
        if "title" not in notif_cols:
            op.add_column("notifications", sa.Column("title", sa.String(255), nullable=True))
        if "message" not in notif_cols:
            op.add_column("notifications", sa.Column("message", sa.Text(), nullable=True))
        if "channel" not in notif_cols:
            op.add_column("notifications", sa.Column("channel", sa.String(32), server_default="in_app", nullable=False))
        if "category" not in notif_cols:
            op.add_column("notifications", sa.Column("category", sa.String(64), server_default="general", nullable=False))
        if "deadline_id" not in notif_cols:
            op.add_column("notifications", sa.Column("deadline_id", sa.String(64), nullable=True))
        if "case_id" not in notif_cols:
            op.add_column("notifications", sa.Column("case_id", sa.String(64), nullable=True))
        if "scheduled_at" not in notif_cols:
            op.add_column("notifications", sa.Column("scheduled_at", sa.String(64), nullable=True))
        if "sent_at" not in notif_cols:
            op.add_column("notifications", sa.Column("sent_at", sa.String(64), nullable=True))
        if "status" not in notif_cols:
            op.add_column("notifications", sa.Column("status", sa.String(32), server_default="pending", nullable=False))
        if "retry_count" not in notif_cols:
            op.add_column("notifications", sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
        if "error_message" not in notif_cols:
            op.add_column("notifications", sa.Column("error_message", sa.Text(), nullable=True))

    # 8. notification_preferences table
    if "notification_preferences" not in tables:
        op.create_table(
            "notification_preferences",
            sa.Column("user_id", sa.String(64), primary_key=True),
            sa.Column("enable_in_app", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("enable_sms", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("quiet_hours_enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("quiet_hours_start", sa.String(8), server_default="22:00", nullable=False),
            sa.Column("quiet_hours_end", sa.String(8), server_default="07:00", nullable=False),
            sa.Column("language", sa.String(8), server_default="bn", nullable=False),
            sa.Column("updated_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "notification_preferences" in tables:
        op.drop_table("notification_preferences")
    if "case_documents" in tables:
        op.drop_table("case_documents")
    if "case_notes" in tables:
        op.drop_table("case_notes")
