"""Ingestion contract schema for API clients and upload lifecycle fields."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0002_ingestion_contract"
down_revision = "0001_foundation_schema"
branch_labels = None
depends_on = None

TABLE_NAMES: Sequence[str] = ("api_clients", "jobs")
JOB_COLUMNS: Sequence[str] = (
    "client_id",
    "idempotency_key",
    "failure_code",
    "failure_message",
)


def upgrade() -> None:
    op.create_table(
        "api_clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_api_clients_client_id"),
    )

    op.add_column("jobs", sa.Column("client_id", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("jobs", sa.Column("failure_code", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("failure_message", sa.String(length=512), nullable=True))
    op.create_index("ix_jobs_client_id", "jobs", ["client_id"])
    op.create_index("ix_jobs_idempotency_key", "jobs", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_client_id", table_name="jobs")
    op.drop_column("jobs", "failure_message")
    op.drop_column("jobs", "failure_code")
    op.drop_column("jobs", "idempotency_key")
    op.drop_column("jobs", "client_id")
    op.drop_table("api_clients")
