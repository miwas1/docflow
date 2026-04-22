# Webhook Contract

Phase 5 adds terminal-state webhook events for client-level integrations.

## Delivery Model

- Webhook subscriptions are stored per client integration.
- Only terminal-state events are sent:
  - `job.completed`
  - `job.failed`
- Each payload references the canonical results endpoint instead of replacing it:
  - `/v1/jobs/{job_id}/results`

## Signature Header

- Header name: `X-DocPlatform-Signature`
- Header value format: `sha256=<hex digest>`
- Signing algorithm: HMAC-SHA256 over the raw JSON payload body

## Payload Fields

- `event_type`
- `job_id`
- `document_id`
- `client_id`
- `tenant_id`
- `status`
- `current_stage`
- `results_url`
- `result_summary`
- `failure`
- `occurred_at`

## Result Summary Rules

- `job.completed` payloads include `result_summary` with:
  - `final_label`
  - `confidence`
  - `low_confidence_policy`
  - `model`
  - `version`
  - `artifact_types`
- `job.failed` payloads set `result_summary` to `null` and populate `failure.code` and `failure.message`.
