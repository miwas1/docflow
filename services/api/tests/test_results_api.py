from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.auth import AuthenticatedClient
from api_service.db.base import Base
from api_service.db.models import Artifact, ClassificationRun, Job
from api_service.errors import APIError
from api_service.main import app
from api_service.services.results import get_job_results


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_results_service_returns_completed_payload_with_extracted_text_and_classification(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        create_completed_job_fixture(session)

    with session_factory() as session:
        result = get_job_results(
            session=session,
            client=AuthenticatedClient(client_id="tenant-456", display_name="tenant-456"),
            job_id="job-456",
        )

    assert result.job_id == "job-456"
    assert result.extracted_text == "Invoice Number INV-42"
    assert result.classification.final_label == "invoice"
    assert result.artifacts[0].artifact_type == "extracted-text"


def test_results_service_rejects_incomplete_jobs(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        create_incomplete_job_fixture(session)
        with pytest.raises(APIError) as exc_info:
            get_job_results(
                session=session,
                client=AuthenticatedClient(client_id="tenant-456", display_name="tenant-456"),
                job_id="job-incomplete",
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "results_not_ready"


def test_results_service_allows_completed_job_even_if_webhook_delivery_failed(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        create_completed_job_fixture(session)
        job = session.get(Job, "job-456")
        assert job is not None
        job.failure_code = "webhook_delivery_exhausted"
        job.failure_message = "Webhook delivery exhausted retries after result persistence."
        session.commit()

    with session_factory() as session:
        result = get_job_results(
            session=session,
            client=AuthenticatedClient(client_id="tenant-456", display_name="tenant-456"),
            job_id="job-456",
        )

    assert result.job_id == "job-456"
    assert result.classification.final_label == "invoice"


def test_results_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/jobs/{job_id}/results")

    assert route.methods == {"GET"}


def create_completed_job_fixture(session: Session) -> None:
    now = datetime.now(UTC)
    job = Job(
        id="job-456",
        document_id="doc-456",
        tenant_id="tenant-456",
        client_id="tenant-456",
        idempotency_key="idem-job-456",
        status="completed",
        current_stage="classified",
        source_filename="sample.pdf",
        source_media_type="application/pdf",
        storage_key="tenants/tenant-456/jobs/job-456/accepted/original/sample.pdf",
        failure_code=None,
        failure_message=None,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()
    session.add_all(
        [
            Artifact(
                id="artifact-extracted-1",
                job_id="job-456",
                artifact_type="extracted-text",
                stage="extracted",
                storage_key="tenants/tenant-456/jobs/job-456/extracted/extracted-text/document.json",
                media_type="application/json",
                metadata_json={"text": "Invoice Number INV-42"},
                created_at=now,
            ),
            Artifact(
                id="artifact-classification-1",
                job_id="job-456",
                artifact_type="classification-result",
                stage="classified",
                storage_key="tenants/tenant-456/jobs/job-456/classified/classification-result/result.json",
                media_type="application/json",
                metadata_json={
                    "final_label": "invoice",
                    "confidence": 0.91,
                    "low_confidence_policy": "threshold_to_unknown_other",
                    "candidate_labels": [
                        {"label": "invoice", "score": 0.91},
                        {"label": "receipt", "score": 0.34},
                    ],
                },
                created_at=now,
            ),
        ]
    )
    session.add(
        ClassificationRun(
            id="classification-run-1",
            job_id="job-456",
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


def create_incomplete_job_fixture(session: Session) -> None:
    now = datetime.now(UTC)
    session.add(
        Job(
            id="job-incomplete",
            document_id="doc-incomplete",
            tenant_id="tenant-456",
            client_id="tenant-456",
            idempotency_key="idem-job-incomplete",
            status="queued",
            current_stage="classifying",
            source_filename="sample.pdf",
            source_media_type="application/pdf",
            storage_key="tenants/tenant-456/jobs/job-incomplete/accepted/original/sample.pdf",
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
