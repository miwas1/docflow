# Phase 5: Client Delivery and Operator Visibility - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the platform operationally usable for machine consumers and internal operators by adding signed terminal-state webhooks, an internal operator dashboard, and production-grade observability across the API, orchestration, extraction, classification, persistence, and webhook-delivery flow. It does not expand into client self-service product surfaces such as customer job-history dashboards, webhook self-service management, or API key administration portals.

</domain>

<decisions>
## Implementation Decisions

### Webhook Registration and Delivery Model
- **D-01:** Webhook configuration should live at the client/tenant integration level rather than being supplied per upload job.
- **D-02:** Phase 5 webhooks should be emitted for terminal states covering both `completed` and `failed` jobs.
- **D-03:** Webhook delivery should remain asynchronous and consume already-persisted job/results state rather than becoming part of the synchronous client happy path.

### Webhook Payload and Signing Contract
- **D-04:** Webhook requests should use header-based signing with an HMAC-style shared secret over the raw payload.
- **D-05:** The webhook payload should be richer than a pure reference-only callback: it must include stable identifiers and final status plus an inline result summary that helps integrators avoid an immediate follow-up fetch in the common case.
- **D-06:** Even with an inline summary, the webhook contract should still include a durable results reference so clients can retrieve the canonical final payload from the results API when needed.

### Internal Operator Dashboard
- **D-07:** Phase 5 should deliver a rich internal operator dashboard rather than only operator APIs or a thin status page.
- **D-08:** The internal dashboard should prioritize searchable job history, queue/job health, stage progression, webhook delivery visibility, failure diagnostics, and model-version visibility for internal operators.
- **D-09:** The dashboard in this phase is for internal operations staff only, not for external clients.

### Observability and Diagnostics
- **D-10:** Phase 5 should implement production-focused observability with all three layers: alertable aggregate metrics, structured logs, and end-to-end per-job traces.
- **D-11:** Observability must cover API, orchestrator, extraction, classification, persistence, and webhook-delivery flows.
- **D-12:** The operator experience should make failed-job diagnosis possible in normal cases without requiring manual database inspection.

### the agent's Discretion
- Exact webhook subscription schema, secret rotation mechanics, retry schedule, and bounded delivery-attempt counts, as long as the delivery model stays client-level, terminal-state-based, and asynchronous.
- Exact inline result-summary field names and header naming for the webhook signature, as long as the contract remains signed, stable, and traceable back to the canonical results endpoint.
- Exact operator dashboard implementation approach and UI architecture, as long as it remains an internal operational surface and fulfills the richer diagnostics/history goals above.
- Exact observability library/tool wiring and metric names, as long as the platform preserves the locked split of aggregate metrics, per-job traces, and structured logs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements
- `.planning/PROJECT.md` — Product shape, API-first constraints, external integration model, and observability requirement baseline.
- `.planning/REQUIREMENTS.md` — Phase 5 requirements `DLV-04`, `DLV-05`, `OPS-03`, `OPS-04`, and `OPS-05`.
- `.planning/ROADMAP.md` — Phase 5 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current workflow state and milestone progress snapshot.

### Prior Phase Contracts
- `.planning/phases/01-core-platform-foundation/01-CONTEXT.md` — Locked async backbone, service boundaries, observability philosophy, storage layout, and cloud baseline.
- `.planning/phases/02-external-ingestion-contract/02-CONTEXT.md` — Locked API-key client auth and stage-based status semantics that webhook and operator surfaces must extend.
- `.planning/phases/03-hybrid-extraction-pipeline/03-CONTEXT.md` — Locked extraction lineage and stage-traceability expectations that the dashboard and diagnostics must expose.
- `.planning/phases/04-classification-and-results/04-CONTEXT.md` — Locked results contract, dedicated results endpoint, and traceable classification metadata that webhook payloads should build on.
- `docs/foundation/status-polling-contract.md` — Existing lifecycle/status fields and failure-shape contract that operator visibility should stay consistent with.
- `docs/foundation/results-contract.md` — Canonical final-results payload and trace/model metadata that webhook summaries and operator drill-downs should align with.
- `docs/foundation/storage-contract.md` — Durable artifact responsibilities and object-storage lineage conventions that delivery/diagnostic tooling must reference correctly.

### System Design and Delivery Expectations
- `system_design.txt` — Source-of-truth architecture for webhook worker, dashboard/status API, and the metrics/traces/logs split.
- `system_design_diagram.md` — Visual topology for webhook delivery, dashboard reads, and observability taps across services.
- `document_inference_platform_done_checklist.md` — Webhook, dashboard, observability, and failure-diagnosis acceptance checklist for production readiness.
- `docs/superpowers/plans/2026-04-21-document-inference-platform-implementation-plan.md` — Broader implementation guidance for webhook delivery, operator visibility, metrics, and alerting expectations.

### Existing Code Contracts
- `services/orchestrator/src/orchestrator_service/celery_app.py` — Existing reserved `document.webhook` queue and orchestration queue topology.
- `services/api/src/api_service/db/models.py` — Existing `jobs`, `job_events`, `artifacts`, `extraction_runs`, and `classification_runs` persistence model that the dashboard and webhook flow should extend.
- `services/api/src/api_service/services/status.py` — Current status-response construction and failure-shape behavior.
- `services/api/src/api_service/services/results.py` — Existing canonical results retrieval path that webhook payloads should reference rather than replace.
- `services/api/src/api_service/main.py` — Current client-facing API surface and authentication boundary for future operator/delivery endpoints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/orchestrator/src/orchestrator_service/celery_app.py`: already defines a dedicated `document.webhook` queue, which gives Phase 5 a natural async delivery lane without changing the core queue topology.
- `services/api/src/api_service/db/models.py`: already provides durable job, event, artifact, extraction-run, and classification-run records that can anchor operator drill-downs and webhook payload assembly.
- `services/api/src/api_service/services/status.py`: already shapes status and failure responses in a way the operator dashboard can reuse for consistency.
- `services/api/src/api_service/services/results.py`: already exposes the canonical final result payload, which supports a “rich summary + results reference” webhook design.

### Established Patterns
- The platform uses stage-based job tracking with durable DB records rather than ephemeral in-memory state.
- Client-facing workflow semantics are intentionally split: polling/status for lifecycle state and a dedicated results endpoint for canonical final payload retrieval.
- Async work belongs on queues and in workers rather than in synchronous API request handling.
- Observability philosophy is already constrained by the system design: aggregate metrics for alerting, per-job traces for deep debugging, and structured logs for operational context without high-cardinality metric abuse.

### Integration Points
- Webhook configuration, delivery metadata, and terminal delivery outcomes will likely extend the API-owned metadata model and/or adjacent delivery tables tied to client/job identity.
- Webhook dispatch should plug into the existing orchestrator queue topology through the reserved `document.webhook` queue.
- Operator visibility should read from `jobs`, `job_events`, `artifacts`, `extraction_runs`, and `classification_runs` rather than inventing a parallel state store.
- Observability instrumentation must attach across API, orchestrator, extractor, classifier, persistence, and webhook delivery so traces and metrics span the full job lifecycle.

</code_context>

<specifics>
## Specific Ideas

- The webhook contract should feel practical for external integrators: signed headers, stable identifiers, terminal state, and enough inline result summary to be immediately useful.
- Internal operators should have a richer dashboard with job-history and webhook-visibility depth, not just a thin health page.
- Diagnostic quality matters: the operator workflow should usually answer “what failed and where?” without opening the database directly.
- The richer client-facing ideas discussed were intentionally separated from this phase to avoid turning Phase 5 into both an internal operations phase and a customer portal phase.

</specifics>

<deferred>
## Deferred Ideas

- External client job-history dashboard — useful future product surface, but outside the internal operator visibility scope of Phase 5.
- Client self-service webhook configuration UI — valuable, but belongs in a later client-management phase rather than the first internal delivery/ops phase.
- Client API key management UI or portal — out of scope for this phase; Phase 2 only locked the backend API-key auth contract.
- Separate future client-facing management console plus a broader internal admin suite — keep as roadmap candidates after the internal operator foundation is in place.

</deferred>

---
*Phase: 05-client-delivery-and-operator-visibility*
*Context gathered: 2026-04-22*
