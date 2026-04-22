"""Shared observability contract for the platform."""

from __future__ import annotations

CORRELATION_FIELDS = ("job_id", "document_id", "tenant_id", "current_stage", "trace_id")
FORBIDDEN_METRIC_LABELS = {"job_id", "document_id", "tenant_id", "trace_id", "target_url"}

SERVICE_NAMES = {
    "api": "api",
    "orchestrator": "orchestrator",
    "extractor": "extractor",
    "classifier": "classifier",
}

SPAN_NAMES = {
    "api_request": "api.request",
    "orchestrator_task": "orchestrator.task",
    "extractor_run": "extractor.run",
    "classifier_run": "classifier.run",
    "webhook_deliver": "webhook.deliver",
}

METRIC_DEFINITIONS = {
    "doc_platform_api_requests_total": {"labels": ("route", "method", "status_family")},
    "doc_platform_job_stage_failures_total": {"labels": ("service", "stage", "outcome")},
    "doc_platform_queue_tasks_total": {"labels": ("service", "stage", "outcome", "event_type")},
    "doc_platform_extraction_latency_seconds": {"labels": ("service", "stage", "outcome")},
    "doc_platform_classification_latency_seconds": {"labels": ("service", "stage", "outcome")},
    "doc_platform_webhook_delivery_attempts_total": {"labels": ("service", "stage", "outcome", "event_type")},
    "doc_platform_job_duration_seconds": {"labels": ("service", "stage", "outcome")},
}
