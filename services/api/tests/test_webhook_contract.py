from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.db.base import Base
from api_service.db.models import APIClient, Artifact, ClassificationRun, Job
from api_service.repositories.webhooks import (
    create_webhook_delivery,
    create_webhook_subscription,
    get_active_webhook_subscription_for_client,
    list_webhook_deliveries_for_job,
    update_webhook_delivery_attempt,
)
from api_service.services.webhooks import build_terminal_webhook_payload, sign_webhook_payload


def load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0005_webhook_delivery_contract.py"
    )
    spec = spec_from_file_location("webhook_delivery_contract", migration_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_migration_module_tracks_webhook_schema() -> None:
    migration = load_migration_module()

    assert migration.revision == "0005_webhook_delivery_contract"
    assert tuple(migration.TABLE_NAMES) == ("webhook_subscriptions", "webhook_deliveries")
    assert "client_id" in migration.WEBHOOK_SUBSCRIPTION_COLUMNS
    assert "attempt_count" in migration.WEBHOOK_DELIVERY_COLUMNS


def test_webhook_subscription_and_delivery_records_are_persisted() -> None:
    session_factory = build_session_factory()
    now = datetime.now(UTC)

    with session_factory() as session:
        seed_completed_job(session, now=now)
        subscription = create_webhook_subscription(
            session,
            client_id="demo-client",
            target_url="https://example.com/hooks/doc-platform",
            signing_secret="whsec-demo",
            subscribed_events=["job.completed", "job.failed"],
        )
        delivery = create_webhook_delivery(
            session,
            job_id="job-123",
            client_id="demo-client",
            subscription_id=subscription.id,
            event_type="job.completed",
            payload_json={"job_id": "job-123"},
            delivery_status="pending",
        )
        update_webhook_delivery_attempt(
            session,
            delivery_id=delivery.id,
            attempt_count=2,
            delivery_status="retrying",
            last_http_status=500,
            last_error_message="remote server error",
            next_retry_at=now,
        )
        session.commit()

    with session_factory() as session:
        loaded_subscription = get_active_webhook_subscription_for_client(session, client_id="demo-client")
        deliveries = list_webhook_deliveries_for_job(session, job_id="job-123")

    assert loaded_subscription is not None
    assert loaded_subscription.target_url == "https://example.com/hooks/doc-platform"
    assert loaded_subscription.subscribed_events_json == ["job.completed", "job.failed"]
    assert len(deliveries) == 1
    assert deliveries[0].attempt_count == 2
    assert deliveries[0].delivery_status == "retrying"
    assert deliveries[0].last_http_status == 500


def test_completed_webhook_payload_contains_summary_and_results_reference() -> None:
    session_factory = build_session_factory()
    now = datetime.now(UTC)

    with session_factory() as session:
        seed_completed_job(session, now=now)
        payload = build_terminal_webhook_payload(
            session=session,
            job_id="job-123",
            client_id="demo-client",
            tenant_id="tenant-123",
            event_type="job.completed",
            base_results_url="http://localhost:8000",
        )

    assert payload.event_type == "job.completed"
    assert payload.job_id == "job-123"
    assert payload.document_id == "doc-123"
    assert payload.status == "completed"
    assert payload.results_url == "http://localhost:8000/v1/jobs/job-123/results"
    assert payload.result_summary is not None
    assert payload.result_summary.final_label == "invoice"
    assert payload.result_summary.model == "baseline-keyword"
    assert payload.result_summary.artifact_types == ["extracted-text", "classification-result"]
    assert payload.failure is None


def test_failed_webhook_payload_contains_failure_and_no_summary() -> None:
    session_factory = build_session_factory()
    now = datetime.now(UTC)

    with session_factory() as session:
        seed_failed_job(session, now=now)
        payload = build_terminal_webhook_payload(
            session=session,
            job_id="job-failed",
            client_id="demo-client",
            tenant_id="tenant-123",
            event_type="job.failed",
            base_results_url="http://localhost:8000",
        )

    assert payload.event_type == "job.failed"
    assert payload.status == "failed"
    assert payload.results_url == "http://localhost:8000/v1/jobs/job-failed/results"
    assert payload.result_summary is None
    assert payload.failure is not None
    assert payload.failure.code == "classification_timeout"
    assert payload.failure.message == "Classifier timed out"


def test_sign_webhook_payload_returns_sha256_header_value() -> None:
    signature = sign_webhook_payload("whsec-demo", b'{"job_id":"job-123"}')

    assert signature.startswith("sha256=")
    assert len(signature.removeprefix("sha256=")) == 64


def seed_completed_job(session: Session, *, now: datetime) -> None:
    session.add(
        APIClient(
            id="api-client-1",
            client_id="demo-client",
            display_name="Demo Client",
            api_key_hash="hashed-demo",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        Job(
            id="job-123",
            document_id="doc-123",
            tenant_id="tenant-123",
            client_id="demo-client",
            idempotency_key="idem-123",
            status="completed",
            current_stage="classified",
            source_filename="invoice.pdf",
            source_media_type="application/pdf",
            storage_key="tenants/tenant-123/jobs/job-123/accepted/original/invoice.pdf",
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.add_all(
        [
            Artifact(
                id="artifact-extracted",
                job_id="job-123",
                artifact_type="extracted-text",
                stage="extracted",
                storage_key="tenants/tenant-123/jobs/job-123/extracted/extracted-text/document.json",
                media_type="application/json",
                metadata_json={"text": "Invoice Number INV-42"},
                created_at=now,
            ),
            Artifact(
                id="artifact-classification",
                job_id="job-123",
                artifact_type="classification-result",
                stage="classified",
                storage_key="tenants/tenant-123/jobs/job-123/classified/classification-result/result.json",
                media_type="application/json",
                metadata_json={},
                created_at=now,
            ),
        ]
    )
    session.add(
        ClassificationRun(
            id="classification-run-1",
            job_id="job-123",
            stage="classifying",
            final_label="invoice",
            confidence=0.91,
            low_confidence_policy="threshold_to_unknown_other",
            threshold_applied=0.6,
            candidate_labels_json=[
                {"label": "invoice", "score": 0.91},
                {"label": "receipt", "score": 0.34},
            ],
            trace_json={"provider": "classifier-service", "model": "baseline-keyword", "version": "0.1.0"},
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()


def seed_failed_job(session: Session, *, now: datetime) -> None:
    session.add(
        APIClient(
            id="api-client-2",
            client_id="demo-client",
            display_name="Demo Client",
            api_key_hash="hashed-demo",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        Job(
            id="job-failed",
            document_id="doc-failed",
            tenant_id="tenant-123",
            client_id="demo-client",
            idempotency_key="idem-failed",
            status="failed",
            current_stage="classifying",
            source_filename="invoice.pdf",
            source_media_type="application/pdf",
            storage_key="tenants/tenant-123/jobs/job-failed/accepted/original/invoice.pdf",
            failure_code="classification_timeout",
            failure_message="Classifier timed out",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
