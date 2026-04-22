"""Reliability and dead-letter metadata for Phase 6."""

from alembic import op
import sqlalchemy as sa

revision = "0006_reliability_and_dead_letter"
down_revision = "0005_webhook_delivery_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("max_retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("dead_letter_reason", sa.String(length=128), nullable=True))
    op.add_column("jobs", sa.Column("terminal_failure_category", sa.String(length=64), nullable=True))
    op.create_index("ix_jobs_dead_lettered_at", "jobs", ["dead_lettered_at"])
    op.create_index("ix_jobs_terminal_failure_category", "jobs", ["terminal_failure_category"])


def downgrade() -> None:
    op.drop_index("ix_jobs_terminal_failure_category", table_name="jobs")
    op.drop_index("ix_jobs_dead_lettered_at", table_name="jobs")
    op.drop_column("jobs", "terminal_failure_category")
    op.drop_column("jobs", "dead_letter_reason")
    op.drop_column("jobs", "dead_lettered_at")
    op.drop_column("jobs", "max_retry_count")
    op.drop_column("jobs", "retry_count")
