"""005 Sprint S5: Legal Notice Interpreter & Deadlines (M04, M07)

Revision ID: 005_s5_notice_interpreter_m04
Revises: 004_s4_documents_m03
Create Date: 2026-10-03

Adds:
- reminder_schedules table (AC-M07-1)
- notice_analyses table for structured M04 explanation results
- Enhancements to deadlines (document_id, user_id, calculation_basis, is_user_set)
- Enhancements to tasks (document_id)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_s5_notice_interpreter_m04"
down_revision: str | None = "004_s4_documents_m03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    deadline_cols = (
        [c["name"] for c in insp.get_columns("deadlines")] if "deadlines" in tables else []
    )
    task_cols = [c["name"] for c in insp.get_columns("tasks")] if "tasks" in tables else []

    # 1. Enhance deadlines table
    if "deadlines" in tables:
        with op.batch_alter_table("deadlines") as batch_op:
            if "document_id" not in deadline_cols:
                batch_op.add_column(sa.Column("document_id", sa.String(64), nullable=True))
            if "user_id" not in deadline_cols:
                batch_op.add_column(sa.Column("user_id", sa.String(64), nullable=True))
            if "calculation_basis" not in deadline_cols:
                batch_op.add_column(sa.Column("calculation_basis", sa.Text(), nullable=True))
            if "is_user_set" not in deadline_cols:
                batch_op.add_column(
                    sa.Column("is_user_set", sa.Boolean(), server_default="0", nullable=False)
                )

    # 2. Enhance tasks table
    if "tasks" in tables:
        with op.batch_alter_table("tasks") as batch_op:
            if "document_id" not in task_cols:
                batch_op.add_column(sa.Column("document_id", sa.String(64), nullable=True))

    # 3. Create reminder_schedules table (AC-M07-1)
    if "reminder_schedules" not in tables:
        op.create_table(
            "reminder_schedules",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "deadline_id",
                sa.String(64),
                sa.ForeignKey("deadlines.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("offset_days", sa.Integer(), nullable=False),
            sa.Column("scheduled_at", sa.String(64), nullable=False),
            sa.Column("channel", sa.String(32), server_default="in_app", nullable=False),
            sa.Column("status", sa.String(32), server_default="pending", nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 4. Create notice_analyses table (M04 persistence)
    if "notice_analyses" not in tables:
        op.create_table(
            "notice_analyses",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "document_id",
                sa.String(64),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("analysis_json", sa.Text(), nullable=False),
            sa.Column("simpler_json", sa.Text(), nullable=True),
            sa.Column("certainty", sa.String(32), nullable=False),
            sa.Column("as_of_date", sa.String(32), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
            sa.Column("updated_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "notice_analyses" in tables:
        op.drop_table("notice_analyses")
    if "reminder_schedules" in tables:
        op.drop_table("reminder_schedules")
