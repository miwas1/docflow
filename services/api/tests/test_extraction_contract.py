from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.db.base import Base
from api_service.db.models import Artifact, Job
from api_service.repositories.jobs import (
    create_extracted_text_artifact,
    create_extraction_run,
    get_extraction_run_for_job,
    record_extraction_completion,
)
from doc_platform_contracts.extraction import ExtractedTextArtifact, ExtractionPage, ExtractionTrace


def load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0003_extraction_contract.py"
    )
    spec = spec_from_file_location("extraction_contract", migration_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_payload(*, extraction_path: str, fallback_used: bool, fallback_reason: str | None) -> ExtractedTextArtifact:
    return ExtractedTextArtifact(
        job_id="job-123",
        document_id="doc-123",
        tenant_id="tenant-123",
        source_media_type="application/pdf",
        extraction_path=extraction_path,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        page_count=2,
        pages=[
            ExtractionPage(page_number=1, text="Page one", source_artifact_id="artifact-source-1"),
            ExtractionPage(page_number=2, text="Page two", source_artifact_id="artifact-source-2"),
        ],
        text="Page one\n\nPage two",
        source_artifact_ids=["artifact-source-1", "artifact-source-2"],
        produced_by=ExtractionTrace(
            provider="unit-test",
            model="fixture-model",
            version="2026.04.21",
        ),
        created_at=datetime(2026, 4, 21, tzinfo=UTC),
    )


def test_extracted_text_artifact_round_trips_direct_and_ocr_payloads() -> None:
    direct_payload = build_payload(
        extraction_path="direct",
        fallback_used=False,
        fallback_reason=None,
    )
    ocr_payload = build_payload(
        extraction_path="ocr",
        fallback_used=True,
        fallback_reason="embedded_text_unusable",
    )

    direct_dump = direct_payload.model_dump()
    ocr_dump = ocr_payload.model_dump()

    assert direct_dump["extraction_path"] == "direct"
    assert direct_dump["fallback_used"] is False
    assert [page["page_number"] for page in direct_dump["pages"]] == [1, 2]

    assert ocr_dump["extraction_path"] == "ocr"
    assert ocr_dump["fallback_used"] is True
    assert ocr_dump["fallback_reason"] == "embedded_text_unusable"
    assert ocr_dump["source_artifact_ids"] == ["artifact-source-1", "artifact-source-2"]


def test_extraction_payload_pages_stay_in_numeric_order() -> None:
    payload = build_payload(extraction_path="direct", fallback_used=False, fallback_reason=None)

    assert [page.page_number for page in payload.pages] == [1, 2]
    assert payload.pages[0].text == "Page one"
    assert payload.pages[1].source_artifact_id == "artifact-source-2"


def test_extraction_run_and_artifact_are_persisted() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    payload = build_payload(extraction_path="direct", fallback_used=False, fallback_reason=None)

    with session_factory() as session:
        _create_job_fixture(session)
        run = create_extraction_run(session, payload=payload, stage="extracting")
        artifact = create_extracted_text_artifact(
            session,
            payload=payload,
            storage_key="tenants/tenant-123/jobs/job-123/extracted/extracted-text/document.json",
            stage="extracted",
        )
        session.commit()

        loaded_run = get_extraction_run_for_job(session, job_id="job-123")
        loaded_artifact = session.query(Artifact).filter(Artifact.id == artifact.id).one()

    assert run.extraction_path == "direct"
    assert run.fallback_used is False
    assert run.page_count == 2
    assert loaded_run is not None
    assert loaded_run.source_artifact_ids_json == ["artifact-source-1", "artifact-source-2"]
    assert loaded_artifact.artifact_type == "extracted-text"
    assert loaded_artifact.metadata_json["extraction_path"] == "direct"


def test_migration_module_tracks_extraction_schema() -> None:
    migration = load_migration_module()

    assert migration.revision == "0003_extraction_contract"
    assert "extraction_runs" in migration.TABLE_NAMES
    assert "extraction_path" in migration.EXTRACTION_COLUMNS
    assert "fallback_used" in migration.EXTRACTION_COLUMNS
    assert "page_count" in migration.EXTRACTION_COLUMNS


def test_record_extraction_completion_persists_ocr_payload_metadata() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    payload = build_payload(
        extraction_path="ocr",
        fallback_used=True,
        fallback_reason="embedded_text_unusable",
    )

    with session_factory() as session:
        _create_job_fixture(session)
        run, artifact = record_extraction_completion(
            session,
            payload=payload,
            storage_key="tenants/tenant-123/jobs/job-123/extracted/extracted-text/document.json",
        )
        session.commit()

        persisted_job = session.get(Job, "job-123")

    assert run.extraction_path == "ocr"
    assert artifact.metadata_json["source_artifact_ids"] == ["artifact-source-1", "artifact-source-2"]
    assert persisted_job is not None
    assert persisted_job.current_stage == "extracted"
    assert persisted_job.status == "completed"


def _create_job_fixture(session: Session) -> None:
    now = datetime.now(UTC)
    session.add(
        Job(
            id="job-123",
            document_id="doc-123",
            tenant_id="tenant-123",
            client_id="tenant-123",
            idempotency_key="idem-job-123",
            status="queued",
            current_stage="accepted",
            source_filename="sample.pdf",
            source_media_type="application/pdf",
            storage_key="tenants/tenant-123/jobs/job-123/accepted/original/sample.pdf",
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
