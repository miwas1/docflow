from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.db.base import Base
from api_service.db.models import Artifact, Job
from api_service.repositories.jobs import (
    create_classification_result_artifact,
    create_classification_run,
    get_classification_run_for_job,
    record_classification_completion,
)
from doc_platform_contracts.classification import (
    ClassificationCandidate,
    ClassifierTrace,
    DocumentClassificationResult,
)


def load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0004_classification_results.py"
    )
    spec = spec_from_file_location("classification_results", migration_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_payload(*, final_label: str, confidence: float, low_confidence_policy: str) -> DocumentClassificationResult:
    return DocumentClassificationResult(
        job_id="job-456",
        document_id="doc-456",
        tenant_id="tenant-456",
        final_label=final_label,
        confidence=confidence,
        candidate_labels=[
            ClassificationCandidate(label="invoice", score=0.92),
            ClassificationCandidate(label="receipt", score=0.41),
        ],
        low_confidence_policy=low_confidence_policy,
        threshold_applied=0.6,
        produced_by=ClassifierTrace(
            provider="unit-test",
            model="baseline-keyword",
            version="2026.04.22",
        ),
        created_at=datetime(2026, 4, 22, tzinfo=UTC),
    )


def test_document_classification_result_round_trips_supported_and_unknown_payloads() -> None:
    invoice_payload = build_payload(
        final_label="invoice",
        confidence=0.92,
        low_confidence_policy="threshold_to_unknown_other",
    )
    unknown_payload = build_payload(
        final_label="unknown_other",
        confidence=0.31,
        low_confidence_policy="threshold_to_unknown_other",
    )

    invoice_dump = invoice_payload.model_dump()
    unknown_dump = unknown_payload.model_dump()

    assert invoice_dump["final_label"] == "invoice"
    assert invoice_dump["confidence"] == 0.92
    assert [candidate["label"] for candidate in invoice_dump["candidate_labels"]] == ["invoice", "receipt"]

    assert unknown_dump["final_label"] == "unknown_other"
    assert unknown_dump["low_confidence_policy"] == "threshold_to_unknown_other"
    assert unknown_dump["produced_by"]["version"] == "2026.04.22"


def test_classification_run_and_artifact_are_persisted() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    payload = build_payload(final_label="invoice", confidence=0.92, low_confidence_policy="threshold_to_unknown_other")

    with session_factory() as session:
        _create_job_fixture(session)
        run = create_classification_run(session, payload=payload, stage="classifying")
        artifact = create_classification_result_artifact(
            session,
            payload=payload,
            storage_key="tenants/tenant-456/jobs/job-456/classified/classification-result/result.json",
            stage="classified",
        )
        session.commit()

        loaded_run = get_classification_run_for_job(session, job_id="job-456")
        loaded_artifact = session.query(Artifact).filter(Artifact.id == artifact.id).one()

    assert run.final_label == "invoice"
    assert run.confidence == 0.92
    assert loaded_run is not None
    assert loaded_run.candidate_labels_json[0]["label"] == "invoice"
    assert loaded_artifact.artifact_type == "classification-result"
    assert loaded_artifact.metadata_json["final_label"] == "invoice"


def test_migration_module_tracks_classification_schema() -> None:
    migration = load_migration_module()

    assert migration.revision == "0004_classification_results"
    assert "classification_runs" in migration.TABLE_NAMES
    assert "final_label" in migration.CLASSIFICATION_COLUMNS
    assert "confidence" in migration.CLASSIFICATION_COLUMNS
    assert "candidate_labels_json" in migration.CLASSIFICATION_COLUMNS


def test_record_classification_completion_marks_job_classified_and_completed() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    payload = build_payload(
        final_label="unknown_other",
        confidence=0.31,
        low_confidence_policy="threshold_to_unknown_other",
    )

    with session_factory() as session:
        _create_job_fixture(session)
        run, artifact = record_classification_completion(
            session,
            payload=payload,
            storage_key="tenants/tenant-456/jobs/job-456/classified/classification-result/result.json",
        )
        session.commit()

        persisted_job = session.get(Job, "job-456")

    assert run.final_label == "unknown_other"
    assert artifact.metadata_json["low_confidence_policy"] == "threshold_to_unknown_other"
    assert persisted_job is not None
    assert persisted_job.current_stage == "classified"
    assert persisted_job.status == "completed"


def _create_job_fixture(session: Session) -> None:
    now = datetime.now(UTC)
    session.add(
        Job(
            id="job-456",
            document_id="doc-456",
            tenant_id="tenant-456",
            client_id="tenant-456",
            idempotency_key="idem-job-456",
            status="queued",
            current_stage="extracted",
            source_filename="sample.pdf",
            source_media_type="application/pdf",
            storage_key="tenants/tenant-456/jobs/job-456/accepted/original/sample.pdf",
            failure_code=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
