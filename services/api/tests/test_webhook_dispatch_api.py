from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from api_service.config import APISettings
from api_service.db.base import Base
from api_service.db.models import APIClient, Artifact, ClassificationRun, Job
from api_service.dependencies import get_internal_service_token
from api_service.errors import APIError
from api_service.main import app
from api_service.repositories.webhooks import create_webhook_subscription
from api_service.schemas import WebhookDeliveryOutcomeRequest
from api_service.services.webhooks import get_webhook_dispatch_payload, record_webhook_delivery_outcome


def build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def build_settings() -> APISettings:
    return APISettings.model_construct(
        postgres_dsn="sqlite+pysqlite:///:memory:",
        rabbitmq_url="amqp://guest:guest@localhost:5672//",
        object_storage_endpoint="http://localhost:9000",
        object_storage_bucket="doc-platform-artifacts",
        object_storage_access_key="minioadmin",
        object_storage_secret_key="minioadmin",
        log_level="INFO",
        api_key_header_name="X-API-Key",
        api_keys_json={"demo-client": "demo-secret"},
        max_upload_bytes=10485760,
        host="0.0.0.0",
        port=8000,
        internal_service_token="internal-secret",
        operator_bearer_token="operator-secret",
        operator_dashboard_enabled=True,
    )


def test_internal_dispatch_route_requires_internal_bearer_token() -> None:
    route = next(route for route in app.routes if route.path == "/internal/webhooks/jobs/{job_id}/dispatch")

    assert route.methods == {"GET"}


def test_internal_delivery_outcome_route_requires_internal_bearer_token() -> None:
    route = next(route for route in app.routes if route.path == "/internal/webhooks/jobs/{job_id}/deliveries/{delivery_id}")

    assert route.methods == {"POST"}


def test_public_api_key_cannot_fetch_internal_webhook_dispatch_payload() -> None:
    request = Request({"type": "http", "headers": [(b"x-api-key", b"demo-secret")]})

    try:
        get_internal_service_token(request, build_settings())
    except APIError as exc:
        assert exc.status_code == 401
        assert exc.error_code == "unauthorized"
    else:
        raise AssertionError("Expected internal token authentication to reject a public API key")


def test_internal_dispatch_endpoint_returns_payload_and_subscription_metadata() -> None:
    session_factory = build_session_factory()
    seed_completed_job(session_factory)

    with session_factory() as session:
        payload = get_webhook_dispatch_payload(
            session=session,
            job_id="job-123",
            base_results_url="http://localhost:8000",
        ).model_dump(mode="json")

    assert payload["target_url"] == "https://example.com/hooks/doc-platform"
    assert payload["signing_secret"] == "whsec-demo"
    assert payload["payload"]["event_type"] == "job.completed"
    assert payload["payload"]["results_url"].endswith("/v1/jobs/job-123/results")
    assert payload["delivery"]["delivery_status"] == "pending"


def test_internal_delivery_outcome_endpoint_persists_retrying_state() -> None:
    session_factory = build_session_factory()
    seed_completed_job(session_factory)

    with session_factory() as session:
        dispatch = get_webhook_dispatch_payload(
            session=session,
            job_id="job-123",
            base_results_url="http://localhost:8000",
        )
        body = record_webhook_delivery_outcome(
            session=session,
            job_id="job-123",
            delivery_id=dispatch.delivery.id,
            outcome=WebhookDeliveryOutcomeRequest(
                attempt_count=2,
                delivery_status="retrying",
                last_http_status=503,
                last_error_message="upstream unavailable",
                next_retry_at="2026-04-22T12:00:00Z",
            ),
        ).model_dump(mode="json")

    assert body["delivery_status"] == "retrying"
    assert body["attempt_count"] == 2
    assert body["last_http_status"] == 503


def test_webhook_delivery_failure_does_not_rewrite_completed_job_status() -> None:
    session_factory = build_session_factory()
    seed_completed_job(session_factory)

    with session_factory() as session:
        dispatch = get_webhook_dispatch_payload(
            session=session,
            job_id="job-123",
            base_results_url="http://localhost:8000",
        )
        record_webhook_delivery_outcome(
            session=session,
            job_id="job-123",
            delivery_id=dispatch.delivery.id,
            outcome=WebhookDeliveryOutcomeRequest(
                attempt_count=4,
                delivery_status="failed",
                last_http_status=None,
                last_error_message="webhook exhausted retries",
                next_retry_at=None,
            ),
        )
        job = session.get(Job, "job-123")

    assert job is not None
    assert job.status == "completed"
    assert job.current_stage == "classified"


def seed_completed_job(session_factory: sessionmaker[Session]) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
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
        subscription = create_webhook_subscription(
            session,
            client_id="demo-client",
            target_url="https://example.com/hooks/doc-platform",
            signing_secret="whsec-demo",
            subscribed_events=["job.completed", "job.failed"],
        )
        assert subscription.client_id == "demo-client"
        session.commit()
