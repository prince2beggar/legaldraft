"""003 Sprint S3: Rules Engine, Citation Verifier, AI Gateway, Eval Harness

Revision ID: 003_s3_rules_verifier_gateway
Revises: 002_trust_kernel_s2
Create Date: 2026-10-03

Adds:
- rule_tests
- prompts
- ai_outputs
- claim_links
- eval_runs
- eval_results
- columns to rules and rule_versions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_s3_rules_verifier_gateway"
down_revision: str | None = "002_trust_kernel_s2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    rules_cols = (
        [c["name"] for c in insp.get_columns("rules")] if "rules" in insp.get_table_names() else []
    )
    rule_ver_cols = (
        [c["name"] for c in insp.get_columns("rule_versions")]
        if "rule_versions" in insp.get_table_names()
        else []
    )
    tables = insp.get_table_names()

    # 0. Add S3 columns to existing rules and rule_versions tables
    with op.batch_alter_table("rules") as batch_op:
        if "name" not in rules_cols:
            batch_op.add_column(sa.Column("name", sa.String(255), nullable=True))
        if "description" not in rules_cols:
            batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        if "category" not in rules_cols:
            batch_op.add_column(sa.Column("category", sa.String(64), nullable=True))
        if "created_at" not in rules_cols:
            batch_op.add_column(sa.Column("created_at", sa.String(64), nullable=True))

    with op.batch_alter_table("rule_versions") as batch_op:
        if "parameters_schema_json" not in rule_ver_cols:
            batch_op.add_column(sa.Column("parameters_schema_json", sa.Text(), nullable=True))
        if "is_active" not in rule_ver_cols:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), server_default="1", nullable=True)
            )
        if "created_at" not in rule_ver_cols:
            batch_op.add_column(sa.Column("created_at", sa.String(64), nullable=True))

    # 1. Rule Tests Table
    if "rule_tests" not in tables:
        op.create_table(
            "rule_tests",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("rule_id", sa.String(64), sa.ForeignKey("rules.id"), nullable=False),
            sa.Column("version", sa.String(32), nullable=False),
            sa.Column("test_name", sa.String(255), nullable=False),
            sa.Column("input_json", sa.Text(), nullable=False),
            sa.Column("expected_output_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 2. Prompts Registry Table
    if "prompts" not in tables:
        op.create_table(
            "prompts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("version", sa.String(32), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("user_template", sa.Text(), nullable=False),
            sa.Column("schema_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 3. AI Outputs Table
    if "ai_outputs" not in tables:
        op.create_table(
            "ai_outputs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("prompt_id", sa.String(64), nullable=True),
            sa.Column("prompt_version", sa.String(32), nullable=True),
            sa.Column("model", sa.String(64), nullable=False),
            sa.Column("raw_input", sa.Text(), nullable=False),
            sa.Column("redacted_input", sa.Text(), nullable=False),
            sa.Column("raw_output", sa.Text(), nullable=False),
            sa.Column("unredacted_output", sa.Text(), nullable=False),
            sa.Column("cost_tokens", sa.Integer(), server_default="0", nullable=False),
            sa.Column("status", sa.String(32), server_default="success", nullable=False),
            sa.Column("security_flags", sa.Text(), server_default="[]", nullable=True),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 4. Claim Links Table (Citation Verifier)
    if "claim_links" not in tables:
        op.create_table(
            "claim_links",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("output_id", sa.String(64), sa.ForeignKey("ai_outputs.id"), nullable=True),
            sa.Column("claim_text", sa.Text(), nullable=False),
            sa.Column("source_id", sa.String(64), nullable=False),
            sa.Column("source_version_id", sa.String(64), nullable=False),
            sa.Column("section_ref", sa.String(64), nullable=True),
            sa.Column(
                "verification_status", sa.String(32), server_default="UNVERIFIED", nullable=False
            ),
            sa.Column("verification_score", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("details_json", sa.Text(), server_default="{}", nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 5. Eval Runs Table
    if "eval_runs" not in tables:
        op.create_table(
            "eval_runs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("suite_name", sa.String(128), nullable=False),
            sa.Column("total_cases", sa.Integer(), server_default="0", nullable=False),
            sa.Column("passed_cases", sa.Integer(), server_default="0", nullable=False),
            sa.Column("failed_cases", sa.Integer(), server_default="0", nullable=False),
            sa.Column("accuracy_rate", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("gate_passed", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )

    # 6. Eval Results Table
    if "eval_results" not in tables:
        op.create_table(
            "eval_results",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("run_id", sa.String(64), sa.ForeignKey("eval_runs.id"), nullable=False),
            sa.Column("case_id", sa.String(64), nullable=False),
            sa.Column("input_summary", sa.Text(), nullable=False),
            sa.Column("expected_output", sa.Text(), nullable=False),
            sa.Column("actual_output", sa.Text(), nullable=False),
            sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("passed", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("latency_ms", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("created_at", sa.String(64), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("claim_links")
    op.drop_table("ai_outputs")
    op.drop_table("prompts")
    op.drop_table("rule_tests")

    with op.batch_alter_table("rule_versions") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("parameters_schema_json")

    with op.batch_alter_table("rules") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("category")
        batch_op.drop_column("description")
        batch_op.drop_column("name")
