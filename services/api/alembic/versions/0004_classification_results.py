"""Classification results schema for durable classifier lineage."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0004_classification_results"
down_revision = "0003_extraction_contract"
branch_labels = None
depends_on = None

TABLE_NAMES: Sequence[str] = ("classification_runs",)
CLASSIFICATION_COLUMNS: Sequence[str] = (
    "job_id",
    "stage",
    "final_label",
    "confidence",
    "low_confidence_policy",
    "threshold_applied",
    "candidate_labels_json",
    "trace_json",
)


def upgrade() -> None:
    op.create_table(
        "classification_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("final_label", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("low_confidence_policy", sa.String(length=128), nullable=False),
        sa.Column("threshold_applied", sa.Float(), nullable=False),
        sa.Column("candidate_labels_json", sa.JSON(), nullable=False),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classification_runs_job_id", "classification_runs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_classification_runs_job_id", table_name="classification_runs")
    op.drop_table("classification_runs")
