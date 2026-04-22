"""Webhook subscription and delivery attempt schema for Phase 5."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision = "0005_webhook_delivery_contract"
down_revision = "0004_classification_results"
branch_labels = None
depends_on = None

TABLE_NAMES: Sequence[str] = ("webhook_subscriptions", "webhook_deliveries")
WEBHOOK_SUBSCRIPTION_COLUMNS: Sequence[str] = (
    "client_id",
    "target_url",
    "signing_secret",
    "subscribed_events_json",
    "is_active",
)
WEBHOOK_DELIVERY_COLUMNS: Sequence[str] = (
    "job_id",
    "client_id",
    "subscription_id",
    "event_type",
    "payload_json",
    "delivery_status",
    "attempt_count",
    "last_http_status",
    "last_error_message",
    "next_retry_at",
    "last_attempt_at",
)


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("target_url", sa.String(length=1024), nullable=False),
        sa.Column("signing_secret", sa.String(length=255), nullable=False),
        sa.Column("subscribed_events_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["api_clients.client_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_subscriptions_client_id", "webhook_subscriptions", ["client_id"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_error_message", sa.String(length=512), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["api_clients.client_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_deliveries_job_id", "webhook_deliveries", ["job_id"])
    op.create_index("ix_webhook_deliveries_client_id", "webhook_deliveries", ["client_id"])
    op.create_index("ix_webhook_deliveries_delivery_status", "webhook_deliveries", ["delivery_status"])


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_delivery_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_client_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_job_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_webhook_subscriptions_client_id", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")
