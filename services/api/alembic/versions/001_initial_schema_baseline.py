"""001 Initial Schema Baseline

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-02

Creates initial database tables per AIN-AI SRS Part 4 Data Model:
- Identity: users, user_roles, devices
- Case Workflow: cases, case_parties, case_events, case_facts, tasks, deadlines
- Documents: documents, document_pages, document_fields
- Knowledge & Rules: sources, source_versions, source_passages, rules, rule_versions, templates, drafts
- Security & Audit: consents, audit_log, notifications
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Identity & Access
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("phone", sa.String(32), unique=True, nullable=False),
        sa.Column("email", sa.String(128), nullable=True),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("preferred_lang", sa.String(8), server_default="bn", nullable=False),
        sa.Column("numeral_style", sa.String(8), server_default="bn", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            onupdate=sa.func.now(),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("org_id", sa.String(36), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. Cases & Workflow
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("case_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("urgency", sa.String(16), server_default="normal", nullable=False),
        sa.Column("status", sa.String(32), server_default="new", nullable=False),
        sa.Column("next_action_id", sa.String(36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            onupdate=sa.func.now(),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "case_parties",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("org", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "case_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_date", sa.String(32), nullable=False),
        sa.Column("date_precision", sa.String(16), server_default="day", nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("origin", sa.String(16), server_default="user", nullable=False),
        sa.Column("source_ref", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(16), server_default="proposed", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "case_facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(16), server_default="proposed", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assignee_id", sa.String(36), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("status", sa.String(32), server_default="not_started", nullable=False),
        sa.Column("origin", sa.String(16), server_default="user", nullable=False),
        sa.Column("related_document_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "deadlines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("due_date", sa.String(32), nullable=False),
        sa.Column("rule_key", sa.String(64), nullable=True),
        sa.Column("rule_version", sa.String(16), nullable=True),
        sa.Column("calc_steps", sa.JSON(), nullable=True),
        sa.Column("assumptions", sa.JSON(), nullable=True),
        sa.Column("confirmed_by_user", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), server_default="upcoming", nullable=False),
        sa.Column("source_ref", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=True),
        sa.Column("language", sa.String(16), server_default="bn", nullable=True),
        sa.Column(
            "processing_status",
            sa.String(32),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column("intent", sa.String(32), server_default="understand", nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("image_key", sa.String(255), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("engine", sa.String(32), nullable=True),
        sa.Column("engine_version", sa.String(32), nullable=True),
    )

    op.create_table(
        "document_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("crop_key", sa.String(255), nullable=True),
        sa.Column("state", sa.String(16), server_default="extracted", nullable=False),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Sources, Rules, Templates, Drafts
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("title_bn", sa.String(255), nullable=True),
        sa.Column("authority", sa.String(128), nullable=False),
        sa.Column("jurisdiction", sa.String(8), server_default="BD", nullable=False),
        sa.Column("language", sa.String(8), server_default="bn", nullable=False),
        sa.Column("official", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("rights", sa.String(32), server_default="official", nullable=False),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "source_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_label", sa.String(32), nullable=False),
        sa.Column("publication_date", sa.String(32), nullable=True),
        sa.Column("effective_from", sa.String(32), nullable=False),
        sa.Column("effective_to", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("file_key", sa.String(255), nullable=True),
        sa.Column("reviewer_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "source_passages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.String(36),
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_ref", sa.String(64), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=True),
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_key", sa.String(64), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(64), nullable=False),
    )

    op.create_table(
        "rule_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "rule_id",
            sa.String(36),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("effective_from", sa.String(32), nullable=False),
        sa.Column("effective_to", sa.String(32), nullable=True),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("doc_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_bn", sa.String(255), nullable=True),
        sa.Column("version", sa.String(16), server_default="0.1.0", nullable=False),
        sa.Column(
            "approval_status",
            sa.String(32),
            server_default="draft_not_reviewed",
            nullable=False,
        ),
        sa.Column("question_schema", sa.JSON(), nullable=True),
        sa.Column("execution_checklist", sa.JSON(), nullable=True),
    )

    op.create_table(
        "drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "template_id",
            sa.String(36),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_version", sa.String(16), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(32), server_default="in_progress", nullable=False),
        sa.Column("docx_key", sa.String(255), nullable=True),
        sa.Column("pdf_key", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 5. Consents, Audit, Notifications
    op.create_table(
        "consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "grantor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grantee_id", sa.String(36), nullable=False),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", sa.String(64), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title_key", sa.String(64), nullable=False),
        sa.Column("body_key", sa.String(64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("object_type", sa.String(32), nullable=True),
        sa.Column("object_id", sa.String(36), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    tables = [
        "notifications",
        "audit_log",
        "consents",
        "drafts",
        "templates",
        "rule_versions",
        "rules",
        "source_passages",
        "source_versions",
        "sources",
        "document_fields",
        "document_pages",
        "documents",
        "deadlines",
        "tasks",
        "case_facts",
        "case_events",
        "case_parties",
        "cases",
        "devices",
        "user_roles",
        "users",
    ]
    for table in tables:
        op.drop_table(table)
