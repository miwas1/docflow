"""Celery task helpers for extraction dispatch."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

from doc_platform_contracts.classification import DocumentClassificationResult
from doc_platform_contracts.extraction import ExtractedTextArtifact

from orchestrator_service.classifier_client import ClassifierClient, ClassifierClientError
from orchestrator_service.celery_app import (  # noqa: E402
    celery_app,
    enqueue_classify_job,
    enqueue_extract_job,
    enqueue_webhook_delivery,
)
from orchestrator_service.config import get_settings
from orchestrator_service.extractor_client import ExtractorClient, ExtractorClientError
from orchestrator_service.observability import observe_task_finish, observe_task_start
from orchestrator_service.pipeline_client import PipelineClient
from orchestrator_service.webhook_client import WebhookClient


def build_extraction_request(
    *,
    job_id: str,
    document_id: str,
    tenant_id: str,
    source_media_type: str,
    source_filename: str,
    source_artifact_id: str,
    content: bytes,
) -> dict:
    return {
        "job_id": job_id,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "source_media_type": source_media_type,
        "source_filename": source_filename,
        "source_artifact_id": source_artifact_id,
        "inline_content_base64": base64.b64encode(content).decode("utf-8"),
    }


def dispatch_extraction_task(
    *,
    extractor_client: ExtractorClient,
    job_id: str,
    document_id: str,
    tenant_id: str,
    source_media_type: str,
    source_filename: str,
    source_artifact_id: str,
    content: bytes,
) -> ExtractedTextArtifact:
    payload = build_extraction_request(
        job_id=job_id,
        document_id=document_id,
        tenant_id=tenant_id,
        source_media_type=source_media_type,
        source_filename=source_filename,
        source_artifact_id=source_artifact_id,
        content=content,
    )
    return extractor_client.run_extraction_request(payload)


def build_default_extractor_client() -> ExtractorClient:
    settings = get_settings()
    return ExtractorClient(base_url=settings.extractor_base_url, timeout_seconds=settings.extractor_timeout_seconds)


def build_classification_request(
    *,
    job_id: str,
    document_id: str,
    tenant_id: str,
    source_media_type: str,
    text: str,
    source_artifact_ids: list[str],
) -> dict:
    return {
        "job_id": job_id,
        "document_id": document_id,
        "tenant_id": tenant_id,
        "source_media_type": source_media_type,
        "text": text,
        "source_artifact_ids": source_artifact_ids,
    }


def dispatch_classification_task(
    *,
    classifier_client: ClassifierClient,
    job_id: str,
    document_id: str,
    tenant_id: str,
    source_media_type: str,
    text: str,
    source_artifact_ids: list[str],
) -> DocumentClassificationResult:
    payload = build_classification_request(
        job_id=job_id,
        document_id=document_id,
        tenant_id=tenant_id,
        source_media_type=source_media_type,
        text=text,
        source_artifact_ids=source_artifact_ids,
    )
    return classifier_client.run_classification_request(payload)


def build_default_classifier_client() -> ClassifierClient:
    settings = get_settings()
    return ClassifierClient(base_url=settings.classifier_base_url, timeout_seconds=settings.classifier_timeout_seconds)


def build_default_webhook_client() -> WebhookClient:
    settings = get_settings()
    return WebhookClient(
        api_base_url=settings.api_base_url,
        internal_service_token=settings.internal_service_token,
        timeout_seconds=settings.webhook_timeout_seconds,
    )


def build_default_pipeline_client() -> PipelineClient:
    """Build a PipelineClient from the current orchestrator settings."""
    settings = get_settings()
    return PipelineClient(
        api_base_url=settings.api_base_url,
        internal_service_token=settings.internal_service_token,
    )


def record_webhook_delivery_outcome(
    *,
    webhook_client: WebhookClient,
    job_id: str,
    delivery_id: str,
    attempt_count: int,
    delivery_status: str,
    last_http_status: int | None,
    last_error_message: str | None,
    next_retry_at: datetime | None,
) -> dict:
    payload = {
        "attempt_count": attempt_count,
        "delivery_status": delivery_status,
        "last_http_status": last_http_status,
        "last_error_message": last_error_message,
        "next_retry_at": next_retry_at.isoformat().replace("+00:00", "Z") if next_retry_at else None,
    }
    return webhook_client.record_delivery_outcome(job_id, delivery_id, payload)


def _retry_delay(backoff_seconds: list[int], *, attempt: int) -> int | None:
    index = attempt - 1
    if index < 0 or index >= len(backoff_seconds):
        return None
    return backoff_seconds[index]


def _is_transient_error(message: str) -> bool:
    normalized = message.lower()
    return any(
        token in normalized
        for token in (
            "timeout",
            "timed out",
            "connection reset",
            "temporarily unavailable",
            "502",
            "503",
            "504",
        )
    )


def _is_terminal_unsafe_input_error(message: str) -> bool:
    normalized = message.lower()
    return any(
        token in normalized
        for token in (
            "corrupt_pdf",
            "encrypted_pdf",
            "invalid_image_encoding",
            "unsupported_media_type",
            "unsafe_input_type_mismatch",
        )
    )


@celery_app.task(name="document.preprocess.accepted")
def preprocess_accepted(*, job_id: str, document_id: str, extraction_payload: dict) -> dict[str, str]:
    """Advance an accepted job into the extraction stage.

    Receives the pre-built extraction payload (including inline file content) from the
    API service so that the orchestrator does not require direct storage access.
    Enqueues ``document.extract.run`` immediately and returns the accepted identifiers
    for Celery result tracking.

    Args:
        job_id: The job ID.
        document_id: The document ID.
        extraction_payload: Complete extraction request dict ready for the extractor service.

    Returns:
        Dict with ``job_id``, ``document_id``, and ``status`` set to ``"extracting"``.
    """
    enqueue_extract_job(extraction_payload)
    return {"job_id": job_id, "document_id": document_id, "status": "extracting"}


@celery_app.task(name="document.extract.run")
def run_extraction(*, payload: dict, attempt: int = 1) -> dict:
    """Run document text extraction and advance the pipeline to classification.

    On success the extraction result is persisted via the API's internal endpoint,
    then a ``document.classify.run`` task is enqueued using the extracted text.
    Transient failures are retried with exponential back-off; terminal unsafe-input
    errors are re-raised immediately so the job is failed without retrying.

    Args:
        payload: Extraction request dict forwarded to the extractor service.
        attempt: 1-based attempt counter used to select the correct retry delay.

    Returns:
        Serialised ``ExtractedTextArtifact`` dict on success, or a retrying status
        dict when a retry has been scheduled.
    """
    observe_task_start("document.extract", stage="extract", event_type="document.extract")
    extractor_client = build_default_extractor_client()
    pipeline_client = build_default_pipeline_client()
    settings = get_settings()
    try:
        extraction_result = extractor_client.run_extraction_request(payload)
        result_dict = extraction_result.model_dump(mode="json")

        # Persist the extraction result in the API service.
        persistence_response = pipeline_client.record_extraction_complete(
            extraction_result.job_id, result_dict
        )
        extracted_artifact_id = persistence_response.get("extracted_text_artifact_id", "")

        # Enqueue the next pipeline stage — classification.
        classify_payload = build_classification_request(
            job_id=extraction_result.job_id,
            document_id=extraction_result.document_id,
            tenant_id=extraction_result.tenant_id,
            source_media_type=extraction_result.source_media_type,
            text=extraction_result.text,
            source_artifact_ids=[extracted_artifact_id] if extracted_artifact_id else extraction_result.source_artifact_ids,
        )
        enqueue_classify_job(classify_payload)

        observe_task_finish("document.extract", outcome="success", stage="extract", event_type="document.extract")
        return result_dict
    except ExtractorClientError as exc:
        if _is_terminal_unsafe_input_error(str(exc)) or not _is_transient_error(str(exc)):
            observe_task_finish("document.extract", outcome="failed", stage="extract", event_type="document.extract")
            raise
        retry_delay = _retry_delay(settings.extract_retry_backoff_seconds, attempt=attempt)
        if attempt < settings.extract_max_attempts and retry_delay is not None:
            enqueue_extract_job(payload, attempt=attempt + 1, countdown=retry_delay)
            observe_task_finish("document.extract", outcome="retrying", stage="extract", event_type="document.extract")
            return {"job_id": payload.get("job_id"), "status": "retrying", "attempt": attempt}
        observe_task_finish("document.extract", outcome="failed", stage="extract", event_type="document.extract")
        raise


@celery_app.task(name="document.classify.run")
def run_classification(*, payload: dict, attempt: int = 1) -> dict:
    """Run document classification and advance the pipeline to webhook delivery.

    On success the classification result is persisted via the API's internal endpoint,
    the job is marked completed, and a ``document.webhook.deliver`` task is enqueued.

    Args:
        payload: Classification request dict forwarded to the classifier service.
        attempt: 1-based attempt counter used to select the correct retry delay.

    Returns:
        Serialised ``DocumentClassificationResult`` dict on success, or a retrying
        status dict when a retry has been scheduled.
    """
    observe_task_start("document.classify", stage="classify", event_type="document.classify")
    classifier_client = build_default_classifier_client()
    pipeline_client = build_default_pipeline_client()
    settings = get_settings()
    try:
        classification_result = classifier_client.run_classification_request(payload)
        result_dict = classification_result.model_dump(mode="json")

        # Persist the classification result and mark the job completed in the API.
        pipeline_client.record_classification_complete(classification_result.job_id, result_dict)

        # Enqueue the final pipeline stage — webhook delivery.
        enqueue_webhook_delivery(classification_result.job_id)

        observe_task_finish("document.classify", outcome="success", stage="classify", event_type="document.classify")
        return result_dict
    except ClassifierClientError as exc:
        if _is_terminal_unsafe_input_error(str(exc)) or not _is_transient_error(str(exc)):
            observe_task_finish("document.classify", outcome="failed", stage="classify", event_type="document.classify")
            raise
        retry_delay = _retry_delay(settings.classify_retry_backoff_seconds, attempt=attempt)
        if attempt < settings.classify_max_attempts and retry_delay is not None:
            enqueue_classify_job(payload, attempt=attempt + 1, countdown=retry_delay)
            observe_task_finish("document.classify", outcome="retrying", stage="classify", event_type="document.classify")
            return {"job_id": payload.get("job_id"), "status": "retrying", "attempt": attempt}
        observe_task_finish("document.classify", outcome="failed", stage="classify", event_type="document.classify")
        raise


@celery_app.task(name="document.webhook.deliver")
def deliver_webhook(*, job_id: str, attempt: int = 1) -> dict:
    observe_task_start("document.webhook", stage="webhook", event_type="document.webhook")
    webhook_client = build_default_webhook_client()
    settings = get_settings()
    dispatch_payload = webhook_client.fetch_dispatch_payload(job_id)
    delivery_id = dispatch_payload["delivery"]["id"]
    try:
        response = webhook_client.deliver(
            dispatch_payload["payload"],
            dispatch_payload["target_url"],
            dispatch_payload["signature"],
        )
        status_code = response["status_code"]
        if 200 <= status_code < 300:
            record_webhook_delivery_outcome(
                webhook_client=webhook_client,
                job_id=job_id,
                delivery_id=delivery_id,
                attempt_count=attempt,
                delivery_status="delivered",
                last_http_status=status_code,
                last_error_message=None,
                next_retry_at=None,
            )
            observe_task_finish("document.webhook", outcome="success", stage="webhook", event_type="document.webhook")
            return {"job_id": job_id, "delivery_status": "delivered", "status_code": status_code}
        raise TimeoutError(f"Webhook callback returned status {status_code}")
    except TimeoutError as exc:
        next_retry_at = None
        delivery_status = "failed"
        retry_delay = _retry_delay(settings.webhook_retry_backoff_seconds, attempt=attempt)
        if attempt < settings.webhook_max_attempts and retry_delay is not None:
            delivery_status = "retrying"
            next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay)
            enqueue_webhook_delivery(
                job_id,
                attempt=attempt + 1,
                countdown=retry_delay,
            )
        record_webhook_delivery_outcome(
            webhook_client=webhook_client,
            job_id=job_id,
            delivery_id=delivery_id,
            attempt_count=attempt,
            delivery_status=delivery_status,
            last_http_status=None,
            last_error_message=str(exc),
            next_retry_at=next_retry_at,
        )
        observe_task_finish("document.webhook", outcome=delivery_status, stage="webhook", event_type="document.webhook")
        return {"job_id": job_id, "delivery_status": delivery_status, "status_code": None}
