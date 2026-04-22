"""Internal pipeline service — handles extraction and classification completion callbacks.

The orchestrator calls these functions via HTTP after each pipeline stage completes.
The API service owns all database state and is the single authority for persisting
results, advancing job stages, and transitioning job status.
"""

from __future__ import annotations

from uuid import uuid4

from doc_platform_contracts.classification import DocumentClassificationResult
from doc_platform_contracts.extraction import ExtractedTextArtifact
from doc_platform_contracts.storage_keys import build_storage_key
from sqlalchemy.orm import Session

from api_service.repositories.jobs import (
    record_extraction_completion,
    record_classification_completion,
)


def handle_extraction_complete(
    session: Session,
    *,
    payload: ExtractedTextArtifact,
) -> dict:
    """Persist an extraction result and advance the job to the extracted stage.

    Generates a storage key for the extracted-text artifact, delegates persistence
    to the jobs repository, and returns the new artifact ID so the orchestrator can
    link the subsequent classification task to it.

    Args:
        session: Active SQLAlchemy session (caller commits).
        payload: Validated extraction result from the extractor service.

    Returns:
        Dict containing ``extracted_text_artifact_id`` and ``status``.
    """
    storage_key = build_storage_key(
        tenant_id=payload.tenant_id,
        job_id=payload.job_id,
        stage="extracted",
        artifact_type="extracted-text",
        filename="text.json",
    )
    _, artifact = record_extraction_completion(
        session,
        payload=payload,
        storage_key=storage_key,
    )
    session.commit()
    return {"extracted_text_artifact_id": artifact.id, "status": "extracted"}


def handle_classification_complete(
    session: Session,
    *,
    payload: DocumentClassificationResult,
) -> dict:
    """Persist a classification result and mark the job as completed.

    Generates a storage key for the classification-result artifact, delegates
    persistence to the jobs repository (which sets ``job.status = "completed"``
    and ``job.current_stage = "classified"``), and returns the final job status.

    Args:
        session: Active SQLAlchemy session (caller commits).
        payload: Validated classification result from the classifier service.

    Returns:
        Dict containing ``classification_artifact_id`` and ``status``.
    """
    storage_key = build_storage_key(
        tenant_id=payload.tenant_id,
        job_id=payload.job_id,
        stage="classified",
        artifact_type="classification-result",
        filename="result.json",
    )
    _, artifact = record_classification_completion(
        session,
        payload=payload,
        storage_key=storage_key,
    )
    session.commit()
    return {"classification_artifact_id": artifact.id, "status": "completed"}
