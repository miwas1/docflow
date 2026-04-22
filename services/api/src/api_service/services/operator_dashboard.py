"""Operator dashboard service layer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api_service.errors import APIError
from api_service.repositories.operator_dashboard import (
    get_job_detail,
    get_job_status_counts,
    get_latest_classification_run,
    get_latest_extraction_run,
    list_jobs,
    list_stage_events,
    list_webhook_deliveries,
)
from api_service.schemas import (
    OperatorDashboardSummaryResponse,
    OperatorFailureResponse,
    OperatorJobDetailResponse,
    OperatorJobListItemResponse,
    OperatorStageEventResponse,
    OperatorWebhookDeliveryResponse,
)


def get_operator_dashboard_summary(*, session: Session) -> OperatorDashboardSummaryResponse:
    counts = get_job_status_counts(session)
    return OperatorDashboardSummaryResponse(**counts)


def list_operator_jobs(
    *,
    session: Session,
    status: str | None,
    client_id: str | None,
    q: str | None,
    limit: int,
) -> list[OperatorJobListItemResponse]:
    rows = list_jobs(session, status=status, client_id=client_id, q=q, limit=limit)
    items = []
    for job, webhook_delivery_status in rows:
        items.append(
            OperatorJobListItemResponse(
                job_id=job.id,
                document_id=job.document_id,
                client_id=job.client_id,
                status=job.status,
                current_stage=job.current_stage,
                failure=_build_failure(job.failure_code, job.failure_message),
                webhook_delivery_status=webhook_delivery_status,
                retry_count=job.retry_count,
                max_retry_count=job.max_retry_count,
                dead_letter_reason=job.dead_letter_reason,
                terminal_failure_category=job.terminal_failure_category,
                updated_at=job.updated_at,
            )
        )
    return items


def get_operator_job_detail(*, session: Session, job_id: str) -> OperatorJobDetailResponse:
    job = get_job_detail(session, job_id=job_id)
    if job is None:
        raise APIError(status_code=404, error_code="job_not_found", message="Job not found.")

    extraction_run = get_latest_extraction_run(session, job_id=job_id)
    classification_run = get_latest_classification_run(session, job_id=job_id)
    stage_events = list_stage_events(session, job_id=job_id)
    deliveries = list_webhook_deliveries(session, job_id=job_id)

    return OperatorJobDetailResponse(
        job_id=job.id,
        document_id=job.document_id,
        client_id=job.client_id,
        tenant_id=job.tenant_id,
        status=job.status,
        current_stage=job.current_stage,
        failure=_build_failure(job.failure_code, job.failure_message),
        retry_count=job.retry_count,
        max_retry_count=job.max_retry_count,
        dead_lettered_at=job.dead_lettered_at,
        dead_letter_reason=job.dead_letter_reason,
        terminal_failure_category=job.terminal_failure_category,
        extraction_model=(extraction_run.trace_json.get("model") if extraction_run else None),
        classification_model=(classification_run.trace_json.get("model") if classification_run else None),
        classification_version=(classification_run.trace_json.get("version") if classification_run else None),
        stage_events=[
            OperatorStageEventResponse(
                event_type=event.event_type,
                stage=event.stage,
                created_at=event.created_at,
                payload=event.payload_json,
            )
            for event in stage_events
        ],
        webhook_deliveries=[
            OperatorWebhookDeliveryResponse(
                id=delivery.id,
                event_type=delivery.event_type,
                delivery_status=delivery.delivery_status,
                attempt_count=delivery.attempt_count,
                last_http_status=delivery.last_http_status,
                last_error_message=delivery.last_error_message,
                next_retry_at=delivery.next_retry_at,
                updated_at=delivery.updated_at,
            )
            for delivery in deliveries
        ],
    )


def _build_failure(code: str | None, message: str | None) -> OperatorFailureResponse | None:
    if code and message:
        return OperatorFailureResponse(code=code, message=message)
    return None
