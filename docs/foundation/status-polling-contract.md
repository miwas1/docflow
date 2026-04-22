# Status Polling Contract

## Polling Endpoint

`GET /v1/jobs/{job_id}`

Clients poll the job resource after upload acceptance. Responses are stage-based and do not include percentage progress.

## Response Fields

- `job_id`
- `document_id`
- `status`
- `current_stage`
- `created_at`
- `updated_at`
- `accepted_at`
- `failure.code`
- `failure.message`

Stable Phase 6 failure categories now include:

- `unsafe_input_type_mismatch`
- `encrypted_pdf`
- `corrupt_pdf`
- `invalid_image_encoding`
- `transient_upstream_exhausted`
- `poison_job`
- `webhook_delivery_exhausted`

## Queued Example

```json
{
  "job_id": "queued-job",
  "document_id": "doc-queued-job",
  "status": "queued",
  "current_stage": "accepted",
  "created_at": "2026-04-21T16:00:00Z",
  "updated_at": "2026-04-21T16:00:00Z",
  "accepted_at": "2026-04-21T16:00:00Z",
  "failure": null
}
```

## Failed Example

```json
{
  "job_id": "failed-job",
  "document_id": "doc-failed-job",
  "status": "failed",
  "current_stage": "extract",
  "created_at": "2026-04-21T16:00:00Z",
  "updated_at": "2026-04-21T16:05:00Z",
  "accepted_at": "2026-04-21T16:00:00Z",
  "failure": {
    "code": "poison_job",
    "message": "Extraction exhausted retries and moved to dead-letter handling."
  }
}
```
