from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.auth import AuthenticatedClient
from api_service.db.base import Base
from api_service.db.models import Job
from api_service.errors import APIError
from api_service.main import app
from api_service.schemas import JobStatusResponse
from api_service.services.status import get_job_status


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


def create_job(
    *,
    session: Session,
    job_id: str,
    status: str,
    current_stage: str,
    failure_code: str | None = None,
    failure_message: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    session.add(
        Job(
            id=job_id,
            document_id=f"doc-{job_id}",
            tenant_id="demo-client",
            client_id="demo-client",
            idempotency_key=f"idem-{job_id}",
            status=status,
            current_stage=current_stage,
            source_filename=f"{job_id}.pdf",
            source_media_type="application/pdf",
            storage_key=f"tenants/demo-client/jobs/{job_id}/accepted/original/{job_id}.pdf",
            failure_code=failure_code,
            failure_message=failure_message,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()


def test_status_service_returns_stage_based_views(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        create_job(session=session, job_id="queued-job", status="queued", current_stage="accepted")
        create_job(session=session, job_id="extracting-job", status="queued", current_stage="extracting")
        create_job(session=session, job_id="failed-job", status="failed", current_stage="extract", failure_code="ocr_timeout", failure_message="OCR timed out")

    with session_factory() as session:
        queued = get_job_status(
            session=session,
                client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
                job_id="queued-job",
            )
        extracting = get_job_status(
            session=session,
            client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
            job_id="extracting-job",
        )
        failed = get_job_status(
            session=session,
            client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
            job_id="failed-job",
        )

    assert queued.current_stage == "accepted"
    assert extracting.current_stage == "extracting"
    assert queued.failure is None
    assert failed.failure is not None
    assert failed.failure.code == "ocr_timeout"
    assert failed.failure.message == "OCR timed out"


def test_status_service_surfaces_poison_job_failure_codes(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        create_job(
            session=session,
            job_id="poison-job",
            status="failed",
            current_stage="extracting",
            failure_code="poison_job",
            failure_message="Extraction exhausted retries and moved to dead-letter handling.",
        )

    with session_factory() as session:
        failed = get_job_status(
            session=session,
            client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
            job_id="poison-job",
        )

    assert failed.failure is not None
    assert failed.failure.code == "poison_job"


def test_status_service_returns_404_for_unknown_jobs(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        with pytest.raises(APIError) as exc_info:
            get_job_status(
                session=session,
                client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
                job_id="missing-job",
            )

    assert exc_info.value.status_code == 404


def test_status_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/jobs/{job_id}")

    assert route.methods == {"GET"}


def test_status_response_schema_remains_lifecycle_only() -> None:
    schema = JobStatusResponse.model_json_schema()

    assert "classification" not in schema["properties"]
    assert "extracted_text" not in schema["properties"]
