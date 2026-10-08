"""004 Sprint S4: Document Ingestion, Resumable Uploads, Field Review States (M03)

Revision ID: 004_s4_documents_m03
Revises: 003_s3_rules_verifier_gateway
Create Date: 2026-10-03

Adds:
- Resumable upload tracking: document_uploads_resumable
- Document retry and error handling columns to documents
- Confidence words and review states enhancement in document_fields
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_s4_documents_m03"
down_revision: str | None = "003_s3_rules_verifier_gateway"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    doc_cols = [c["name"] for c in insp.get_columns("documents")] if "documents" in tables else []
    field_cols = (
        [c["name"] for c in insp.get_columns("document_fields")]
        if "document_fields" in tables
        else []
    )

    # 1. Add S4 columns to existing documents table
    with op.batch_alter_table("documents") as batch_op:
        if "retry_count" not in doc_cols:
            batch_op.add_column(
                sa.Column("retry_count", sa.Integer(), server_default="0", nullable=True)
            )
        if "error_message" not in doc_cols:
            batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        if "page_count" not in doc_cols:
            batch_op.add_column(
                sa.Column("page_count", sa.Integer(), server_default="1", nullable=True)
            )

    # 2. Add S4 confidence_word column to document_fields table
    with op.batch_alter_table("document_fields") as batch_op:
        if "confidence_word" not in field_cols:
            batch_op.add_column(sa.Column("confidence_word", sa.String(16), nullable=True))

    # 3. Create document_uploads_resumable table for chunked and offline uploads
    if "document_uploads_resumable" not in tables:
        op.create_table(
            "document_uploads_resumable",
            sa.Column("upload_id", sa.String(64), primary_key=True),
            sa.Column("owner_id", sa.String(64), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("total_size", sa.Integer(), nullable=False),
            sa.Column("total_chunks", sa.Integer(), nullable=False),
            sa.Column("uploaded_chunks_json", sa.Text(), nullable=False),
            sa.Column("sha256_hash", sa.String(64), nullable=False),
            sa.Column("temp_file_path", sa.String(255), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("document_uploads_resumable")

    with op.batch_alter_table("document_fields") as batch_op:
        batch_op.drop_column("confidence_word")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("page_count")
        batch_op.drop_column("error_message")
        batch_op.drop_column("retry_count")
