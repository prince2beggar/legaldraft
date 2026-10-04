"""002 Trust Kernel & S2 Knowledge Registry Enhancements

Revision ID: 002_trust_kernel_s2
Revises: 001_initial_schema
Create Date: 2026-10-02

Adds:
- Trust Kernel real persistence tables:
  * trust_users
  * trust_devices
  * trust_consents
  * trust_audit_logs
  * trust_blocked_phone_hashes
- S2 Ingestion jobs table:
  * ingestion_jobs
- Columns for Source Registry:
  * sources.source_label
  * source_versions.uploader_id
  * source_versions.superseded_by_version_id
  * source_versions.approval_notes
  * source_passages.heading
  * source_passages.embedding_json
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_trust_kernel_s2"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Trust Kernel: Users
    op.create_table(
        "trust_users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("phone", sa.String(32), index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), server_default="citizen", nullable=False),
        sa.Column("roles_json", sa.Text(), server_default='["citizen"]', nullable=False),
        sa.Column("preferred_lang", sa.String(16), server_default="bn", nullable=False),
        sa.Column("numeral_style", sa.String(16), server_default="bn", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("is_onboarded", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("deleted_at", sa.String(64), nullable=True),
    )

    # 2. Trust Kernel: Devices
    op.create_table(
        "trust_devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), index=True, nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("last_seen_at", sa.String(64), nullable=True),
        sa.Column("revoked_at", sa.String(64), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
    )

    # 3. Trust Kernel: Consents
    op.create_table(
        "trust_consents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("grantor_id", sa.String(64), index=True, nullable=False),
        sa.Column("grantee_id", sa.String(64), index=True, nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("permissions_json", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.String(64), nullable=False),
        sa.Column("revoked_at", sa.String(64), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
    )

    # 4. Trust Kernel: Append-Only Audit Logs
    op.create_table(
        "trust_audit_logs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("at", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(64), index=True, nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", sa.String(64), nullable=False),
        sa.Column("ip", sa.String(64), server_default="127.0.0.1", nullable=False),
        sa.Column("meta_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
    )

    # 5. Trust Kernel: Salted Blocked Phone Hashes
    op.create_table(
        "trust_blocked_phone_hashes",
        sa.Column("phone_hash", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.String(64), nullable=False),
    )

    # 6. S2 Ingestion Pipeline Jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("source_version_id", sa.String(64), nullable=False),
        sa.Column("step", sa.String(32), server_default="uploaded", nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("details_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.String(64), nullable=False),
    )

    # 7. S2 Source Metadata Columns
    with op.batch_alter_table("sources") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_label", sa.String(64), server_default="FAKE_TEST_DATA", nullable=False
            )
        )

    with op.batch_alter_table("source_versions") as batch_op:
        batch_op.add_column(sa.Column("uploader_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_version_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("approval_notes", sa.Text(), nullable=True))

    with op.batch_alter_table("source_passages") as batch_op:
        batch_op.add_column(sa.Column("heading", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("embedding_json", sa.Text(), nullable=True))

    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column("owner_id", nullable=True)
        batch_op.alter_column("filename", nullable=True)
        batch_op.alter_column("mime", nullable=True)
        batch_op.alter_column("size_bytes", nullable=True)
        batch_op.alter_column("sha256", nullable=True)
        batch_op.alter_column("storage_key", nullable=True)
        batch_op.add_column(sa.Column("org_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("matter_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(255), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(50), server_default="draft", nullable=True)
        )
        batch_op.add_column(sa.Column("structured_facts", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("selected_clauses", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("full_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("book_grounding_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("book_chapter_reference", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("book_applied_rules", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("draft_audit", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("docx_path", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("pdf_path", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("pdf_path")
        batch_op.drop_column("docx_path")
        batch_op.drop_column("draft_audit")
        batch_op.drop_column("book_applied_rules")
        batch_op.drop_column("book_chapter_reference")
        batch_op.drop_column("book_grounding_score")
        batch_op.drop_column("full_text")
        batch_op.drop_column("selected_clauses")
        batch_op.drop_column("structured_facts")
        batch_op.drop_column("status")
        batch_op.drop_column("title")
        batch_op.drop_column("template_id")
        batch_op.drop_column("matter_id")
        batch_op.drop_column("org_id")

    with op.batch_alter_table("source_passages") as batch_op:
        batch_op.drop_column("embedding_json")
        batch_op.drop_column("heading")

    with op.batch_alter_table("source_versions") as batch_op:
        batch_op.drop_column("approval_notes")
        batch_op.drop_column("superseded_by_version_id")
        batch_op.drop_column("uploader_id")

    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("source_label")

    op.drop_table("ingestion_jobs")
    op.drop_table("trust_blocked_phone_hashes")
    op.drop_table("trust_audit_logs")
    op.drop_table("trust_consents")
    op.drop_table("trust_devices")
    op.drop_table("trust_users")
