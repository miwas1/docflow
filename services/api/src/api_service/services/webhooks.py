"""Webhook payload, dispatch, and signing helpers."""

from __future__ import annotations

import hashlib
import hmac

from sqlalchemy.orm import Session

from api_service.db.models import Job, WebhookDelivery
from api_service.errors import APIError
from api_service.repositories.jobs import (
    get_classification_run_for_job,
    get_latest_artifact_for_job,
)
from api_service.repositories.webhooks import (
    create_webhook_delivery,
    get_active_webhook_subscription_for_client,
    get_webhook_delivery_for_job,
    update_webhook_delivery_attempt,
)
from api_service.schemas import (
    TerminalWebhookPayload,
    WebhookDeliveryResponse,
    WebhookDispatchResponse,
    WebhookDeliveryOutcomeRequest,
    WebhookFailureResponse,
    WebhookResultSummaryResponse,
)


def build_terminal_webhook_payload(
    *,
    session: Session,
    job_id: str,
    client_id: str,
    tenant_id: str,
    event_type: str,
    base_results_url: str,
) -> TerminalWebhookPayload:
    job = session.get(Job, job_id)
    if job is None or job.client_id != client_id or job.tenant_id != tenant_id:
        raise APIError(status_code=404, error_code="job_not_found", message="Job not found.")

    results_url = f"{base_results_url.rstrip('/')}/v1/jobs/{job_id}/results"
    occurred_at = job.updated_at
    if event_type == "job.completed":
        classification_run = get_classification_run_for_job(session, job_id=job_id)
        extracted_artifact = get_latest_artifact_for_job(session, job_id=job_id, artifact_type="extracted-text")
        classification_artifact = get_latest_artifact_for_job(session, job_id=job_id, artifact_type="classification-result")
        if classification_run is None or extracted_artifact is None or classification_artifact is None:
            raise APIError(status_code=409, error_code="results_not_ready", message="Results are not ready for this job.")
        trace = classification_run.trace_json
        result_summary = WebhookResultSummaryResponse(
            final_label=classification_run.final_label,
            confidence=classification_run.confidence,
            low_confidence_policy=classification_run.low_confidence_policy,
            model=trace.get("model", ""),
            version=trace.get("version", ""),
            artifact_types=[extracted_artifact.artifact_type, classification_artifact.artifact_type],
        )
        failure = None
    elif event_type == "job.failed":
        result_summary = None
        failure = WebhookFailureResponse(
            code=job.failure_code or "job_failed",
            message=job.failure_message or "Job failed.",
        )
    else:
        raise APIError(status_code=400, error_code="unsupported_event_type", message="Unsupported webhook event type.")

    return TerminalWebhookPayload(
        event_type=event_type,
        job_id=job.id,
        document_id=job.document_id,
        client_id=client_id,
        tenant_id=tenant_id,
        status=job.status,
        current_stage=job.current_stage,
        results_url=results_url,
        result_summary=result_summary,
        failure=failure,
        occurred_at=occurred_at,
    )


def sign_webhook_payload(secret: str, raw_payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def get_webhook_dispatch_payload(
    *,
    session: Session,
    job_id: str,
    base_results_url: str,
) -> WebhookDispatchResponse:
    job = session.get(Job, job_id)
    if job is None or not job.client_id:
        raise APIError(status_code=404, error_code="job_not_found", message="Job not found.")

    subscription = get_active_webhook_subscription_for_client(session, client_id=job.client_id)
    if subscription is None:
        raise APIError(
            status_code=404,
            error_code="webhook_subscription_not_found",
            message="Active webhook subscription not found.",
        )

    if job.status == "completed":
        event_type = "job.completed"
    elif job.status == "failed":
        event_type = "job.failed"
    else:
        raise APIError(
            status_code=409,
            error_code="job_not_terminal",
            message="Webhook dispatch is only available for terminal jobs.",
        )

    payload = build_terminal_webhook_payload(
        session=session,
        job_id=job_id,
        client_id=job.client_id,
        tenant_id=job.tenant_id,
        event_type=event_type,
        base_results_url=base_results_url,
    )
    delivery = create_webhook_delivery(
        session,
        job_id=job.id,
        client_id=job.client_id,
        subscription_id=subscription.id,
        event_type=event_type,
        payload_json=payload.model_dump(mode="json"),
        delivery_status="pending",
    )
    session.commit()
    return WebhookDispatchResponse(
        target_url=subscription.target_url,
        signing_secret=subscription.signing_secret,
        payload=payload,
        delivery=_delivery_to_response(delivery),
    )


def record_webhook_delivery_outcome(
    *,
    session: Session,
    job_id: str,
    delivery_id: str,
    outcome: WebhookDeliveryOutcomeRequest,
) -> WebhookDeliveryResponse:
    delivery = get_webhook_delivery_for_job(session, job_id=job_id, delivery_id=delivery_id)
    if delivery is None:
        raise APIError(status_code=404, error_code="webhook_delivery_not_found", message="Webhook delivery not found.")
    updated = update_webhook_delivery_attempt(
        session,
        delivery_id=delivery_id,
        attempt_count=outcome.attempt_count,
        delivery_status=outcome.delivery_status,
        last_http_status=outcome.last_http_status,
        last_error_message=outcome.last_error_message,
        next_retry_at=outcome.next_retry_at,
    )
    session.commit()
    return _delivery_to_response(updated)


def _delivery_to_response(delivery: WebhookDelivery) -> WebhookDeliveryResponse:
    return WebhookDeliveryResponse(
        id=delivery.id,
        job_id=delivery.job_id,
        delivery_status=delivery.delivery_status,
        attempt_count=delivery.attempt_count,
        last_http_status=delivery.last_http_status,
        last_error_message=delivery.last_error_message,
        next_retry_at=delivery.next_retry_at,
    )
