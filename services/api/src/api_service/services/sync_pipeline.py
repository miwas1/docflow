"""Synchronous fast-path pipeline for digital document types.

For media types that do not require OCR (plain-text, JSON, DOCX, and PDFs with
embedded text), the API service can call the extractor and classifier services
directly within the upload request and return fully-resolved results immediately.

If either downstream service is slow or unavailable the caller should catch
``SyncPipelineError`` and fall back to the standard async Celery queue path.

Design contract
---------------
- **No DB writes** — this module only makes HTTP calls and returns structured
  results.  Persistence is the caller's responsibility so that, on failure,
  nothing needs to be rolled back.
- **Hard budget** — the total wall-clock time across both service calls is
  bounded by ``timeout_seconds``.  Each call gets the remaining budget; if time
  runs out a ``SyncPipelineError`` is raised so the caller can enqueue async.
- **Always async for OCR inputs** — ``image/png`` and ``image/jpeg`` are not in
  ``SYNC_ELIGIBLE_MEDIA_TYPES``.  Scanned PDFs will naturally time-out and fall
  back to the async path via the 20-second budget.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib import error, request as urllib_request

from doc_platform_contracts.classification import DocumentClassificationResult
from doc_platform_contracts.extraction import ExtractedTextArtifact

# ---------------------------------------------------------------------------
# Media types eligible for synchronous processing.
# OCR types (image/png, image/jpeg) are intentionally excluded.
# Scanned PDFs will be attempted but will timeout and fall back to async.
# ---------------------------------------------------------------------------
SYNC_ELIGIBLE_MEDIA_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/json",
})


class SyncPipelineError(Exception):
    """Raised when the synchronous fast-path times out or a service call fails.

    The caller should catch this and enqueue the job on the async Celery path.
    """


@dataclass(slots=True)
class SyncPipelineResult:
    """Holds the raw results from a successful synchronous pipeline run."""

    extraction: ExtractedTextArtifact
    classification: DocumentClassificationResult


def run_sync_pipeline(
    *,
    job_id: str,
    document_id: str,
    tenant_id: str,
    source_media_type: str,
    source_filename: str,
    source_artifact_id: str,
    content: bytes,
    extractor_base_url: str,
    classifier_base_url: str,
    timeout_seconds: float,
) -> SyncPipelineResult:
    """Call extractor and classifier synchronously within a shared time budget.

    This function is **pure HTTP** — it makes no database writes.  Persistence
    is left to the caller so that a failure here leaves the database in a clean
    state (only the original upload artifact has been committed).

    Args:
        job_id: Job ID created at upload time.
        document_id: Document ID created at upload time.
        tenant_id: Tenant/client ID for storage-key scoping.
        source_media_type: MIME type of the uploaded file.
        source_filename: Original filename of the uploaded file.
        source_artifact_id: Artifact row ID of the persisted original file.
        content: Raw file bytes.
        extractor_base_url: Base URL of the extractor service.
        classifier_base_url: Base URL of the classifier service.
        timeout_seconds: Total wall-clock budget shared across both calls.

    Returns:
        :class:`SyncPipelineResult` containing validated extraction and
        classification domain objects.

    Raises:
        SyncPipelineError: If either service call fails or the budget expires.
    """
    import base64

    deadline = time.monotonic() + timeout_seconds

    # ------------------------------------------------------------------
    # Stage 1: extraction
    # ------------------------------------------------------------------
    extraction_payload = {
        "job_id": job_id,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "source_media_type": source_media_type,
        "source_filename": source_filename,
        "source_artifact_id": source_artifact_id,
        "inline_content_base64": base64.b64encode(content).decode("utf-8"),
    }

    extractor_timeout = max(deadline - time.monotonic(), 0.5)
    try:
        req = urllib_request.Request(
            url=f"{extractor_base_url.rstrip('/')}/v1/extractions:run",
            data=json.dumps(extraction_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=extractor_timeout) as resp:
            extraction_result = ExtractedTextArtifact.model_validate(
                json.loads(resp.read().decode("utf-8"))
            )
    except TimeoutError as exc:
        raise SyncPipelineError(f"Extractor timed out: {exc}") from exc
    except (error.HTTPError, error.URLError, Exception) as exc:
        raise SyncPipelineError(f"Extractor call failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Stage 2: classification
    # ------------------------------------------------------------------
    classify_payload = {
        "job_id": job_id,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "source_media_type": source_media_type,
        "text": extraction_result.text,
        "source_artifact_ids": extraction_result.source_artifact_ids,
    }

    classifier_timeout = max(deadline - time.monotonic(), 0.5)
    try:
        req = urllib_request.Request(
            url=f"{classifier_base_url.rstrip('/')}/v1/classifications:run",
            data=json.dumps(classify_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=classifier_timeout) as resp:
            classification_result = DocumentClassificationResult.model_validate(
                json.loads(resp.read().decode("utf-8"))
            )
    except TimeoutError as exc:
        raise SyncPipelineError(f"Classifier timed out: {exc}") from exc
    except (error.HTTPError, error.URLError, Exception) as exc:
        raise SyncPipelineError(f"Classifier call failed: {exc}") from exc

    return SyncPipelineResult(
        extraction=extraction_result,
        classification=classification_result,
    )
