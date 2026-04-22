from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from api_service.config import APISettings
from api_service.db.base import Base
from api_service.db.models import (
    APIClient,
    ClassificationRun,
    ExtractionRun,
    Job,
    JobEvent,
)
from api_service.dependencies import get_authenticated_operator
from api_service.errors import APIError
from api_service.main import app
from api_service.repositories.webhooks import create_webhook_delivery, create_webhook_subscription
from api_service.services.operator_dashboard import (
    get_operator_dashboard_summary,
    get_operator_job_detail,
    list_operator_jobs,
)


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


def test_operator_json_routes_are_registered() -> None:
    jobs_route = next(route for route in app.routes if route.path == "/internal/operator/jobs")
    detail_route = next(route for route in app.routes if route.path == "/internal/operator/jobs/{job_id}")
    dashboard_route = next(route for route in app.routes if route.path == "/internal/operator/dashboard")

    assert jobs_route.methods == {"GET"}
    assert detail_route.methods == {"GET"}
    assert dashboard_route.methods == {"GET"}


def test_operator_auth_rejects_public_api_key_header() -> None:
    request = Request({"type": "http", "headers": [(b"x-api-key", b"demo-secret")]})

    try:
        get_authenticated_operator(request, build_settings())
    except APIError as exc:
        assert exc.status_code == 401
        assert exc.error_code == "unauthorized"
    else:
        raise AssertionError("Expected operator auth to reject public API-key style access")


def test_operator_dashboard_summary_and_list_surface_counts_and_filters() -> None:
    session_factory = build_session_factory()
    seed_operator_data(session_factory)

    with session_factory() as session:
        summary = get_operator_dashboard_summary(session=session)
        jobs = list_operator_jobs(session=session, status="failed", client_id="demo-client", q="timeout", limit=10)

    assert summary.queued == 1
    assert summary.running == 1
    assert summary.completed == 1
    assert summary.failed == 1
    assert len(jobs) == 1
    assert jobs[0].job_id == "job-failed"
    assert jobs[0].webhook_delivery_status == "failed"
    assert jobs[0].failure is not None


def test_operator_job_detail_returns_stage_history_models_and_webhook_attempts() -> None:
    session_factory = build_session_factory()
    seed_operator_data(session_factory)

    with session_factory() as session:
        detail = get_operator_job_detail(session=session, job_id="job-failed")

    assert detail.job_id == "job-failed"
    assert [event.stage for event in detail.stage_events] == ["accepted", "classifying"]
    assert detail.classification_model == "baseline-keyword"
    assert detail.webhook_deliveries[0].delivery_status == "failed"
    assert detail.failure is not None


def test_operator_job_detail_surfaces_dead_letter_metadata() -> None:
    session_factory = build_session_factory()
    seed_operator_data(session_factory)

    with session_factory() as session:
        detail = get_operator_job_detail(session=session, job_id="job-failed")

    assert detail.retry_count == 3
    assert detail.max_retry_count == 3
    assert detail.dead_letter_reason == "classification_retries_exhausted"
    assert detail.terminal_failure_category == "poison_job"


def seed_operator_data(session_factory: sessionmaker[Session]) -> None:
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
        jobs = [
            Job(
                id="job-queued",
                document_id="doc-queued",
                tenant_id="tenant-123",
                client_id="demo-client",
                idempotency_key="idem-queued",
                status="queued",
                current_stage="accepted",
                source_filename="queued.pdf",
                source_media_type="application/pdf",
                storage_key="jobs/queued.pdf",
                failure_code=None,
                failure_message=None,
                created_at=now,
                updated_at=now,
            ),
            Job(
                id="job-running",
                document_id="doc-running",
                tenant_id="tenant-123",
                client_id="demo-client",
                idempotency_key="idem-running",
                status="running",
                current_stage="extracting",
                source_filename="running.pdf",
                source_media_type="application/pdf",
                storage_key="jobs/running.pdf",
                failure_code=None,
                failure_message=None,
                created_at=now,
                updated_at=now,
            ),
            Job(
                id="job-complete",
                document_id="doc-complete",
                tenant_id="tenant-123",
                client_id="demo-client",
                idempotency_key="idem-complete",
                status="completed",
                current_stage="classified",
                source_filename="complete.pdf",
                source_media_type="application/pdf",
                storage_key="jobs/complete.pdf",
                failure_code=None,
                failure_message=None,
                created_at=now,
                updated_at=now,
            ),
            Job(
                id="job-failed",
                document_id="doc-failed",
                tenant_id="tenant-123",
                client_id="demo-client",
                idempotency_key="idem-failed",
                status="failed",
                current_stage="classifying",
                source_filename="failed.pdf",
                source_media_type="application/pdf",
                storage_key="jobs/failed.pdf",
                failure_code="classification_timeout",
                failure_message="Classifier timeout while processing page 2",
                retry_count=3,
                max_retry_count=3,
                dead_letter_reason="classification_retries_exhausted",
                terminal_failure_category="poison_job",
                created_at=now,
                updated_at=now,
            ),
        ]
        session.add_all(jobs)
        session.add_all(
            [
                JobEvent(
                    id="event-1",
                    job_id="job-failed",
                    event_type="job.accepted",
                    stage="accepted",
                    payload_json={},
                    created_at=now,
                ),
                JobEvent(
                    id="event-2",
                    job_id="job-failed",
                    event_type="job.classifying",
                    stage="classifying",
                    payload_json={"message": "timeout"},
                    created_at=now,
                ),
            ]
        )
        session.add(
            ExtractionRun(
                id="extract-run-1",
                job_id="job-failed",
                stage="extracting",
                extraction_path="ocr",
                fallback_used=False,
                fallback_reason=None,
                page_count=2,
                source_artifact_ids_json=["artifact-1"],
                trace_json={"provider": "extractor-service", "model": "heuristic-router", "version": "0.1.0"},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ClassificationRun(
                id="classification-run-1",
                job_id="job-failed",
                stage="classifying",
                final_label="unknown_other",
                confidence=0.22,
                low_confidence_policy="threshold_to_unknown_other",
                threshold_applied=0.6,
                candidate_labels_json=[{"label": "invoice", "score": 0.22}],
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
        create_webhook_delivery(
            session,
            job_id="job-failed",
            client_id="demo-client",
            subscription_id=subscription.id,
            event_type="job.failed",
            payload_json={"job_id": "job-failed"},
            delivery_status="failed",
        )
        session.commit()
