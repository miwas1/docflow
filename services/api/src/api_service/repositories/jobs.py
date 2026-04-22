"""Job repository helpers for ingestion and polling flows."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from api_service.db.models import Artifact, ClassificationRun, ExtractionRun, Job, JobEvent
from doc_platform_contracts.classification import DocumentClassificationResult
from doc_platform_contracts.extraction import ExtractedTextArtifact


def get_job_by_idempotency_key(session: Session, *, client_id: str, idempotency_key: str) -> Job | None:
    statement = select(Job).where(
        Job.client_id == client_id,
        Job.idempotency_key == idempotency_key,
    )
    return session.scalar(statement)


def get_job_for_client(session: Session, *, client_id: str, job_id: str) -> Job | None:
    statement = select(Job).where(Job.client_id == client_id, Job.id == job_id)
    return session.scalar(statement)


def create_job(session: Session, job: Job) -> Job:
    session.add(job)
    session.flush()
    return job


def create_job_event(session: Session, event: JobEvent) -> JobEvent:
    session.add(event)
    session.flush()
    return event


def create_artifact(session: Session, artifact: Artifact) -> Artifact:
    session.add(artifact)
    session.flush()
    return artifact


def create_extraction_run(
    session: Session,
    *,
    payload: ExtractedTextArtifact,
    stage: str,
) -> ExtractionRun:
    extraction_run = ExtractionRun(
        id=str(uuid4()),
        job_id=payload.job_id,
        stage=stage,
        extraction_path=payload.extraction_path,
        fallback_used=payload.fallback_used,
        fallback_reason=payload.fallback_reason,
        page_count=payload.page_count,
        source_artifact_ids_json=payload.source_artifact_ids,
        trace_json=payload.produced_by.model_dump(),
    )
    session.add(extraction_run)
    session.flush()
    return extraction_run


def get_extraction_run_for_job(session: Session, *, job_id: str) -> ExtractionRun | None:
    statement = select(ExtractionRun).where(ExtractionRun.job_id == job_id)
    return session.scalar(statement)


def create_extracted_text_artifact(
    session: Session,
    *,
    payload: ExtractedTextArtifact,
    storage_key: str,
    stage: str,
) -> Artifact:
    artifact = Artifact(
        id=str(uuid4()),
        job_id=payload.job_id,
        artifact_type="extracted-text",
        stage=stage,
        storage_key=storage_key,
        media_type="application/json",
        metadata_json={
            "document_id": payload.document_id,
            "source_media_type": payload.source_media_type,
            "extraction_path": payload.extraction_path,
            "fallback_used": payload.fallback_used,
            "fallback_reason": payload.fallback_reason,
            "page_count": payload.page_count,
            "source_artifact_ids": payload.source_artifact_ids,
            "text": payload.text,
            "produced_by": payload.produced_by.model_dump(),
        },
    )
    session.add(artifact)
    session.flush()
    return artifact


def record_extraction_completion(
    session: Session,
    *,
    payload: ExtractedTextArtifact,
    storage_key: str,
) -> tuple[ExtractionRun, Artifact]:
    extraction_run = create_extraction_run(session, payload=payload, stage="extracting")
    artifact = create_extracted_text_artifact(
        session,
        payload=payload,
        storage_key=storage_key,
        stage="extracted",
    )
    job = session.get(Job, payload.job_id)
    if job is not None:
        job.current_stage = "extracted"
        job.status = "running"  # still running — classification stage follows
    session.flush()
    session.refresh(extraction_run)
    session.refresh(artifact)
    session.expunge(extraction_run)
    session.expunge(artifact)
    return extraction_run, artifact


def create_classification_run(
    session: Session,
    *,
    payload: DocumentClassificationResult,
    stage: str,
) -> ClassificationRun:
    classification_run = ClassificationRun(
        id=str(uuid4()),
        job_id=payload.job_id,
        stage=stage,
        final_label=payload.final_label,
        confidence=payload.confidence,
        low_confidence_policy=payload.low_confidence_policy,
        threshold_applied=payload.threshold_applied,
        candidate_labels_json=[candidate.model_dump() for candidate in payload.candidate_labels],
        trace_json=payload.produced_by.model_dump(),
    )
    session.add(classification_run)
    session.flush()
    return classification_run


def get_classification_run_for_job(session: Session, *, job_id: str) -> ClassificationRun | None:
    statement = select(ClassificationRun).where(ClassificationRun.job_id == job_id)
    return session.scalar(statement)


def create_classification_result_artifact(
    session: Session,
    *,
    payload: DocumentClassificationResult,
    storage_key: str,
    stage: str,
) -> Artifact:
    artifact = Artifact(
        id=str(uuid4()),
        job_id=payload.job_id,
        artifact_type="classification-result",
        stage=stage,
        storage_key=storage_key,
        media_type="application/json",
        metadata_json={
            "document_id": payload.document_id,
            "final_label": payload.final_label,
            "confidence": payload.confidence,
            "low_confidence_policy": payload.low_confidence_policy,
            "threshold_applied": payload.threshold_applied,
            "candidate_labels": [candidate.model_dump() for candidate in payload.candidate_labels],
            "produced_by": payload.produced_by.model_dump(),
        },
    )
    session.add(artifact)
    session.flush()
    return artifact


def record_classification_completion(
    session: Session,
    *,
    payload: DocumentClassificationResult,
    storage_key: str,
) -> tuple[ClassificationRun, Artifact]:
    classification_run = create_classification_run(session, payload=payload, stage="classifying")
    artifact = create_classification_result_artifact(
        session,
        payload=payload,
        storage_key=storage_key,
        stage="classified",
    )
    job = session.get(Job, payload.job_id)
    if job is not None:
        job.current_stage = "classified"
        job.status = "completed"
    session.flush()
    session.refresh(classification_run)
    session.refresh(artifact)
    session.expunge(classification_run)
    session.expunge(artifact)
    return classification_run, artifact


def get_latest_artifact_for_job(
    session: Session,
    *,
    job_id: str,
    artifact_type: str,
) -> Artifact | None:
    statement = (
        select(Artifact)
        .where(Artifact.job_id == job_id, Artifact.artifact_type == artifact_type)
        .order_by(Artifact.created_at.desc())
    )
    return session.scalars(statement).first()


def mark_job_retrying(
    session: Session,
    *,
    job_id: str,
    stage: str,
    retry_count: int,
    max_retry_count: int,
    failure_code: str,
    failure_message: str,
    terminal_failure_category: str = "transient_upstream",
) -> Job | None:
    job = session.get(Job, job_id)
    if job is None:
        return None
    job.status = "running"
    job.current_stage = stage
    job.retry_count = retry_count
    job.max_retry_count = max_retry_count
    job.failure_code = failure_code
    job.failure_message = failure_message
    job.terminal_failure_category = terminal_failure_category
    create_job_event(
        session,
        JobEvent(
            id=str(uuid4()),
            job_id=job_id,
            event_type="stage.retry_scheduled",
            stage=stage,
            payload_json={
                "retry_count": retry_count,
                "max_retry_count": max_retry_count,
                "failure_code": failure_code,
                "failure_message": failure_message,
            },
            created_at=datetime.now(UTC),
        ),
    )
    session.flush()
    return job


def mark_job_failed(
    session: Session,
    *,
    job_id: str,
    stage: str,
    failure_code: str,
    failure_message: str,
    terminal_failure_category: str,
) -> Job | None:
    job = session.get(Job, job_id)
    if job is None:
        return None
    job.status = "failed"
    job.current_stage = stage
    job.failure_code = failure_code
    job.failure_message = failure_message
    job.terminal_failure_category = terminal_failure_category
    create_job_event(
        session,
        JobEvent(
            id=str(uuid4()),
            job_id=job_id,
            event_type="stage.failed",
            stage=stage,
            payload_json={
                "failure_code": failure_code,
                "failure_message": failure_message,
                "terminal_failure_category": terminal_failure_category,
            },
            created_at=datetime.now(UTC),
        ),
    )
    session.flush()
    return job


def mark_job_dead_lettered(
    session: Session,
    *,
    job_id: str,
    stage: str,
    retry_count: int,
    max_retry_count: int,
    failure_code: str,
    failure_message: str,
    dead_letter_reason: str,
    terminal_failure_category: str = "poison_job",
) -> Job | None:
    job = session.get(Job, job_id)
    if job is None:
        return None
    job.status = "failed"
    job.current_stage = stage
    job.retry_count = retry_count
    job.max_retry_count = max_retry_count
    job.failure_code = failure_code
    job.failure_message = failure_message
    job.dead_lettered_at = datetime.now(UTC)
    job.dead_letter_reason = dead_letter_reason
    job.terminal_failure_category = terminal_failure_category
    create_job_event(
        session,
        JobEvent(
            id=str(uuid4()),
            job_id=job_id,
            event_type="stage.dead_lettered",
            stage=stage,
            payload_json={
                "retry_count": retry_count,
                "max_retry_count": max_retry_count,
                "failure_code": failure_code,
                "failure_message": failure_message,
                "dead_letter_reason": dead_letter_reason,
                "terminal_failure_category": terminal_failure_category,
            },
            created_at=datetime.now(UTC),
        ),
    )
    session.flush()
    return job
