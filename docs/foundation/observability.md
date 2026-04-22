# Observability Contract

Phase 5 standardizes the platform observability vocabulary around bounded metrics, correlated structured logs, and span names shared across services.

## Correlation Fields

- `job_id`
- `document_id`
- `tenant_id`
- `current_stage`
- `trace_id`

These fields belong in logs and traces, not in metric labels.

## Span Names

- `api.request`
- `orchestrator.task`
- `extractor.run`
- `classifier.run`
- `webhook.deliver`

## Metric Names

- `doc_platform_api_requests_total`
- `doc_platform_job_stage_failures_total`
- `doc_platform_queue_tasks_total`
- `doc_platform_extraction_latency_seconds`
- `doc_platform_classification_latency_seconds`
- `doc_platform_webhook_delivery_attempts_total`
- `doc_platform_job_duration_seconds`

## Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_SERVICE_NAMESPACE`
- `TRACE_SAMPLE_RATIO`

## Label Policy

Allowed metric labels stay bounded, such as `route`, `method`, `status_family`, `service`, `stage`, `outcome`, and `event_type`.

Forbidden high-cardinality labels include raw `job_id`, `document_id`, `tenant_id`, and webhook target URLs.

## Reliability Events

Phase 6 reliability hardening introduces stable event/failure vocabulary that should appear in logs, traces, or bounded outcome labels:

- `unsafe_input_type_mismatch`
- `encrypted_pdf`
- `corrupt_pdf`
- `invalid_image_encoding`
- `stage.retry_scheduled`
- `stage.dead_lettered`
- `poison_job`
- `webhook_delivery_exhausted`
