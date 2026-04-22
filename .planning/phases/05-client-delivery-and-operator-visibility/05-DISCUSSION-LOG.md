# Phase 5: Client Delivery and Operator Visibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 05-client-delivery-and-operator-visibility
**Areas discussed:** Webhook registration and delivery model, Webhook payload and signing contract, Internal operator dashboard scope, Observability and diagnostics surface

---

## Webhook Registration and Delivery Model

| Option | Description | Selected |
|--------|-------------|----------|
| Per-client webhook config, completion + failure events | Stable webhook subscription lives with the API client/tenant, and jobs inherit it automatically. Phase 5 emits callbacks for `completed` and `failed`. | ✓ |
| Per-client webhook config, completion-only | Stable client-level config, but only successful completion emits webhooks in v1. | |
| Per-job callback URL supplied at upload time | Each upload can override callback behavior. More flexible, but higher validation and security complexity. | |
| Hybrid: client default with optional per-job override | Flexible default-plus-override model with the most contract complexity. | |

**User's choice:** Per-client webhook config, completion + failure events.
**Notes:** User selected `1`. This keeps webhook configuration at the integration level and includes terminal state delivery for both successful and failed jobs.

## Webhook Payload and Signing Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Thin payload + signed header | Identifiers, status, timestamps, and results reference only, signed through headers. | |
| Thin payload + signature embedded in body | Similar thin callback, but signature metadata lives inside the JSON body. | |
| Rich payload + signed header | Includes stable identifiers and terminal state plus an inline result summary, with request signing in headers. | ✓ |
| Rich payload + full final result | Sends most or all of the final result document inside the webhook body. | |

**User's choice:** Rich payload + signed header.
**Notes:** User selected `3`. The callback should remain signed through headers while carrying enough inline result summary to be useful immediately, without losing the durable canonical results endpoint.

## Internal Operator Dashboard Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Thin internal dashboard | Queue health, job counts, recent failures, per-job stage history, and model versions. | |
| Rich internal operator dashboard | Stronger drill-downs, filtering, searchable job history, webhook delivery visibility, and better diagnostics for internal operators only. | ✓ |

**User's choice:** Rich internal operator dashboard.
**Notes:** The user first proposed a broader split between client-facing user surfaces and internal admin surfaces. That broader proposal was recognized as valuable but out of Phase 5 scope. The final in-scope choice was `2`: a richer internal dashboard for operators only.

## Observability and Diagnostics Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline observability | Structured logs, a small metrics set, and traces mainly for debugging. | |
| Production-focused observability | Alertable aggregate metrics, structured logs, and end-to-end per-job traces across API, orchestrator, extractor, classifier, persistence, and webhook delivery. | ✓ |
| Metrics-first, minimal tracing | Heavier emphasis on metrics with lighter trace coverage. | |
| Trace-heavy observability | Heavier emphasis on traces/logs with fewer aggregate metrics. | |

**User's choice:** Production-focused observability.
**Notes:** User selected `2`. Failed-job diagnosis should usually be possible through the dashboard/observability surface without manual DB inspection.

## the agent's Discretion

- Retry backoff shape, bounded attempt counts, and exact dead-letter or terminal-delivery metadata for webhook delivery.
- Exact header names and summary field names for the signed rich webhook contract.
- Exact internal dashboard implementation architecture and UX details.
- Exact telemetry implementation libraries, naming conventions, and dashboard tooling choices.

## Deferred Ideas

- Client-facing dashboard for job history.
- Client self-service webhook configuration UI.
- Client API key management UI or portal.
- Broader split between an external customer management console and a separate deeper internal admin dashboard.
