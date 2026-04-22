"""Extraction contract schema for normalized extraction lineage."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0003_extraction_contract"
down_revision = "0002_ingestion_contract"
branch_labels = None
depends_on = None

TABLE_NAMES: Sequence[str] = ("extraction_runs",)
EXTRACTION_COLUMNS: Sequence[str] = (
    "job_id",
    "stage",
    "extraction_path",
    "fallback_used",
    "fallback_reason",
    "page_count",
    "source_artifact_ids_json",
    "trace_json",
)


def upgrade() -> None:
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("extraction_path", sa.String(length=32), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fallback_reason", sa.String(length=128), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("source_artifact_ids_json", sa.JSON(), nullable=False),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_runs_job_id", "extraction_runs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_extraction_runs_job_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")
