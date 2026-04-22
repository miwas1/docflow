"""Request and response schemas for the API service."""

from datetime import datetime

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict | None = None


class AcceptedUploadResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    current_stage: str
    # Populated only when the synchronous fast-path completes inline.
    # Clients should check ``status == "completed"`` before reading these fields.
    extracted_text: str | None = None
    classification: "ClassificationMetadataResponse | None" = None


class FailureResponse(BaseModel):
    code: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    current_stage: str
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime
    failure: FailureResponse | None = None


class ArtifactReferenceResponse(BaseModel):
    artifact_type: str
    stage: str
    storage_key: str


class ClassificationCandidateResponse(BaseModel):
    label: str
    score: float


class ClassificationMetadataResponse(BaseModel):
    final_label: str
    confidence: float
    low_confidence_policy: str
    threshold_applied: float
    candidate_labels: list[ClassificationCandidateResponse]
    model: str
    version: str


class JobResultsResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    extracted_text: str
    classification: ClassificationMetadataResponse
    artifacts: list[ArtifactReferenceResponse]
    completed_at: datetime


class WebhookFailureResponse(BaseModel):
    code: str
    message: str


class WebhookResultSummaryResponse(BaseModel):
    final_label: str
    confidence: float
    low_confidence_policy: str
    model: str
    version: str
    artifact_types: list[str]


class TerminalWebhookPayload(BaseModel):
    event_type: str
    job_id: str
    document_id: str
    client_id: str
    tenant_id: str
    status: str
    current_stage: str
    results_url: str
    result_summary: WebhookResultSummaryResponse | None
    failure: WebhookFailureResponse | None
    occurred_at: datetime


class WebhookDeliveryResponse(BaseModel):
    id: str
    job_id: str
    delivery_status: str
    attempt_count: int
    last_http_status: int | None
    last_error_message: str | None
    next_retry_at: datetime | None


class WebhookDispatchResponse(BaseModel):
    target_url: str
    signing_secret: str
    payload: TerminalWebhookPayload
    delivery: WebhookDeliveryResponse


class WebhookDeliveryOutcomeRequest(BaseModel):
    attempt_count: int
    delivery_status: str
    last_http_status: int | None = None
    last_error_message: str | None = None
    next_retry_at: datetime | None = None


class OperatorFailureResponse(BaseModel):
    code: str
    message: str


class OperatorDashboardSummaryResponse(BaseModel):
    queued: int
    running: int
    completed: int
    failed: int


class OperatorJobListItemResponse(BaseModel):
    job_id: str
    document_id: str
    client_id: str | None
    status: str
    current_stage: str
    failure: OperatorFailureResponse | None
    webhook_delivery_status: str | None
    retry_count: int = 0
    max_retry_count: int = 0
    dead_letter_reason: str | None = None
    terminal_failure_category: str | None = None
    updated_at: datetime


class OperatorStageEventResponse(BaseModel):
    event_type: str
    stage: str
    created_at: datetime
    payload: dict


class OperatorWebhookDeliveryResponse(BaseModel):
    id: str
    event_type: str
    delivery_status: str
    attempt_count: int
    last_http_status: int | None
    last_error_message: str | None
    next_retry_at: datetime | None
    updated_at: datetime


class OperatorJobDetailResponse(BaseModel):
    job_id: str
    document_id: str
    client_id: str | None
    tenant_id: str
    status: str
    current_stage: str
    failure: OperatorFailureResponse | None
    retry_count: int = 0
    max_retry_count: int = 0
    dead_lettered_at: datetime | None = None
    dead_letter_reason: str | None = None
    terminal_failure_category: str | None = None
    extraction_model: str | None
    classification_model: str | None
    classification_version: str | None
    stage_events: list[OperatorStageEventResponse]
    webhook_deliveries: list[OperatorWebhookDeliveryResponse]
