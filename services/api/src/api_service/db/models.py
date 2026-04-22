"""Foundation metadata models for the platform."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_service.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_letter_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    terminal_failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    events: Mapped[list["JobEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    extraction_runs: Mapped[list["ExtractionRun"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    classification_runs: Mapped[list["ClassificationRun"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    webhook_deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_client_id", "client_id"),
        Index("ix_jobs_idempotency_key", "idempotency_key"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_current_stage", "current_stage"),
        Index("ix_jobs_dead_lettered_at", "dead_lettered_at"),
        Index("ix_jobs_terminal_failure_category", "terminal_failure_category"),
    )


class APIClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    webhook_subscriptions: Mapped[list["WebhookSubscription"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        primaryjoin="APIClient.client_id == foreign(WebhookSubscription.client_id)",
    )
    webhook_deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        primaryjoin="APIClient.client_id == foreign(WebhookDelivery.client_id)",
    )


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="events")

    __table_args__ = (Index("ix_job_events_job_id", "job_id"),)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="artifacts")

    __table_args__ = (Index("ix_artifacts_job_id", "job_id"),)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_path: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(nullable=False, default=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    page_count: Mapped[int] = mapped_column(nullable=False)
    source_artifact_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trace_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="extraction_runs")

    __table_args__ = (Index("ix_extraction_runs_job_id", "job_id"),)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_family: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    routing_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    rollout_bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ClassificationRun(Base):
    __tablename__ = "classification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    final_label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    low_confidence_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    threshold_applied: Mapped[float] = mapped_column(nullable=False)
    candidate_labels_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    trace_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="classification_runs")

    __table_args__ = (Index("ix_classification_runs_job_id", "job_id"),)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="CASCADE"), nullable=False)
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    signing_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    subscribed_events_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    client: Mapped[APIClient] = relationship(back_populates="webhook_subscriptions")
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_webhook_subscriptions_client_id", "client_id"),)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(ForeignKey("api_clients.client_id", ondelete="CASCADE"), nullable=False)
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_http_status: Mapped[int | None] = mapped_column(nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="webhook_deliveries")
    client: Mapped[APIClient] = relationship(back_populates="webhook_deliveries")
    subscription: Mapped[WebhookSubscription] = relationship(back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_deliveries_job_id", "job_id"),
        Index("ix_webhook_deliveries_client_id", "client_id"),
        Index("ix_webhook_deliveries_delivery_status", "delivery_status"),
    )
