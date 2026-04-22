# Operator Dashboard

Phase 5 adds an internal-only operator surface for queue health, searchable job history, and per-job diagnostics.

## Routes

- `GET /internal/operator/dashboard`
- `GET /internal/operator/jobs`
- `GET /internal/operator/jobs/{job_id}`

## Auth

- All operator routes require `Authorization: Bearer <OPERATOR_BEARER_TOKEN>`.
- Public API keys are not valid for these routes.

## Query Filters

`GET /internal/operator/jobs` supports:

- `status`
- `client_id`
- `q`
- `limit`

## Drill-Down Fields

Per-job detail includes:

- stage events
- failure diagnostics
- extraction model
- classification model and version
- webhook delivery history
