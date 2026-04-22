# Phase 6: Reliability and Input Safety - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the existing asynchronous document-processing platform against unsafe inputs, transient upstream failures, repeated stage failures, and worker restarts. It defines how the platform validates uploaded files, classifies retryable versus terminal failures, isolates poison jobs, preserves durable consistency across retries, and keeps webhook delivery bounded without turning delivery issues into duplicate final side effects or inconsistent job state.

</domain>

<decisions>
## Implementation Decisions

### Unsafe Input Validation Policy
- **D-01:** Uploaded files must be validated by file signature / magic bytes rather than trusting the declared MIME type or extension alone.
- **D-02:** If the declared type and detected type mismatch, the upload should be rejected by default as an unsafe input mismatch.
- **D-03:** Corrupt PDFs, unreadable files, and invalid image encodings should fail fast as terminal input errors at the first stage that can prove the input is invalid.
- **D-04:** Encrypted PDFs should not proceed through extraction; they should fail with a dedicated encrypted-PDF failure reason instead of being retried.
- **D-05:** For unsafe or corrupt inputs, retain the original uploaded artifact for traceability, but do not create derived extraction/classification artifacts.

### Retry Classification and Scheduling
- **D-06:** Automatic retries for extraction and classification should be limited to clearly transient failures such as timeouts, upstream 5xx responses, or connection resets.
- **D-07:** Terminal input-safety failures must not be retried automatically.
- **D-08:** Retry timing should use exponential backoff with a capped attempt budget rather than immediate loops or one fixed retry delay for every failure.
- **D-09:** Webhook delivery should use three distinct retry windows at separate later intervals before being treated as exhausted.

### Poison Job and Dead-Letter Handling
- **D-10:** Jobs that exhaust their retry budget should be marked `failed` and also recorded with a dedicated poison/dead-letter state plus a clear terminal reason.
- **D-11:** Dead-lettered jobs should remain visible in normal operator workflows rather than disappearing into an opaque side channel.
- **D-12:** Phase 6 operator handling is inspect-only; replay/remediation UX is deferred to a later phase.

### Durable Side-Effect Safety
- **D-13:** Stage writes must be idempotent across retries and worker restarts.
- **D-14:** Final side effects must only be emitted after the durable state needed to justify them has already been persisted.
- **D-15:** Worker restart and retry behavior must preserve consistent job state rather than relying on overwriting artifacts and hoping later stages converge.

### Failure Visibility and Delivery Semantics
- **D-16:** Status, events, and operator surfaces should expose stable failure categories such as `unsafe_input`, `encrypted_pdf`, `transient_upstream`, and `poison_job` rather than only generic failures.
- **D-17:** Public client APIs should keep stable bounded failure codes and messages, while deeper diagnostics stay in operator-facing logs/events rather than being dumped into the client contract.
- **D-18:** A job that has already completed classification remains `completed` even if downstream webhook delivery later exhausts retries; delivery exhaustion is a separate delivery failure, not a reversal of the core processing result.

### the agent's Discretion
- Exact signature-detection library choice and how aggressively validation is centralized at upload time versus rechecked at extraction time.
- Exact transient-error taxonomy for extractor/classifier/webhook failures, as long as it cleanly separates retryable failures from terminal unsafe-input failures.
- Exact exponential backoff values for extraction/classification retries, as long as retries stay bounded and operator-visible.
- Exact three webhook retry intervals, as long as they are separate later intervals rather than one repeated constant delay.
- Exact schema/table/field design for dead-letter tracking, as long as dead-letter status is durable, queryable, and visible to operators.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements
- `.planning/PROJECT.md` — Product shape, reliability expectations, hybrid extraction strategy, and cloud-deployment constraints that Phase 6 must preserve.
- `.planning/REQUIREMENTS.md` — Phase 6 requirements `SEC-02`, `SEC-03`, and `SEC-04`.
- `.planning/ROADMAP.md` — Phase 6 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current project progress and workflow state.

### Prior Phase Contracts
- `.planning/phases/01-core-platform-foundation/01-CONTEXT.md` — Locked service boundaries, RabbitMQ/Celery async backbone, Postgres metadata model, and object-storage contract.
- `.planning/phases/02-external-ingestion-contract/02-CONTEXT.md` — Locked authenticated upload flow, idempotent client retries, and stage-based status semantics that failure handling must extend rather than replace.
- `.planning/phases/03-hybrid-extraction-pipeline/03-CONTEXT.md` — Locked extraction fallback/traceability behavior and normalized extraction pipeline expectations.
- `.planning/phases/04-classification-and-results/04-CONTEXT.md` — Locked final-results durability rules and classification/result state expectations.
- `.planning/phases/05-client-delivery-and-operator-visibility/05-CONTEXT.md` — Locked asynchronous webhook delivery model, bounded delivery behavior direction, observability contract, and operator visibility expectations.

### Foundation Contracts
- `docs/foundation/status-polling-contract.md` — Canonical lifecycle/status fields and failure-shape contract that Phase 6 failure visibility must stay consistent with.
- `docs/foundation/results-contract.md` — Canonical rule that results are only available after required artifacts are durably persisted.
- `docs/foundation/observability.md` — Shared logs/metrics/traces vocabulary and bounded-label policy for surfacing retry/dead-letter behavior.
- `docs/foundation/webhook-contract.md` — Existing webhook delivery contract that Phase 6 retry/dead-letter policy must refine without changing the core signed terminal-event shape.
- `docs/foundation/storage-contract.md` — Durable artifact responsibilities that constrain unsafe-input retention and derived-artifact behavior.

### Existing Code Contracts
- `services/api/src/api_service/services/ingestion.py` — Current upload validation and durable-acceptance flow; Phase 6 input-safety checks must extend this path.
- `services/api/src/api_service/db/models.py` — Existing `jobs`, `job_events`, `artifacts`, `extraction_runs`, `classification_runs`, and `webhook_deliveries` schema that Phase 6 reliability state should build on.
- `services/api/src/api_service/repositories/jobs.py` — Current extraction/classification completion persistence patterns and job-stage mutation helpers that need restart-safe semantics.
- `services/api/src/api_service/services/status.py` — Existing public status contract and failure-shape construction.
- `services/api/src/api_service/services/webhooks.py` — Existing terminal webhook dispatch/outcome persistence flow that Phase 6 must harden.
- `services/orchestrator/src/orchestrator_service/tasks.py` — Current extraction/classification/webhook Celery task boundaries and webhook retry behavior that Phase 6 must generalize and harden.
- `services/orchestrator/src/orchestrator_service/celery_app.py` — Existing queue topology and retry-enqueue integration point.
- `services/orchestrator/src/orchestrator_service/config.py` — Existing timeout and webhook retry configuration surface to extend for bounded retry policy.

### System Design
- `system_design.txt` — Source-of-truth architecture for async control flow, artifact durability, and machine-to-machine webhook integration.
- `system_design_diagram.md` — Visual system topology for upload, orchestration, extraction, classification, persistence, and delivery flow.
- `document_inference_platform_done_checklist.md` — Release-quality checklist that reliability hardening and unsafe-input handling should satisfy.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/api/src/api_service/services/ingestion.py`: already owns initial upload validation, raw artifact persistence, and durable acceptance before queue handoff.
- `services/api/src/api_service/db/models.py`: already provides durable tables for jobs, job events, artifacts, extraction runs, classification runs, and webhook deliveries that can absorb retry/dead-letter metadata.
- `services/api/src/api_service/services/status.py`: already shapes the public failure contract for stage-based polling.
- `services/api/src/api_service/services/webhooks.py`: already persists delivery attempts and exposes a natural place to separate processing completion from webhook exhaustion.
- `services/orchestrator/src/orchestrator_service/tasks.py`: already contains stage task entry points and a first bounded retry example in webhook delivery.

### Established Patterns
- The platform persists accepted jobs before async processing and uses Celery queues for background work rather than synchronous inline execution.
- Final results are only considered ready after durable artifacts and metadata are persisted.
- Status semantics are stage-based and already expose bounded failure details rather than raw stack traces.
- Operator and observability surfaces already expect durable job/event state instead of inferring reliability history from ephemeral worker memory.

### Integration Points
- Input-safety checks should attach to the existing ingestion acceptance flow and possibly be reinforced at extractor boundaries when actual content decoding occurs.
- Retry/dead-letter logic should extend the existing orchestrator task boundaries for extraction, classification, and webhook delivery rather than inventing a separate workflow engine.
- Poison/dead-letter state should be recorded in the API-owned metadata model so status/events/operator surfaces can query it consistently.
- Failure categorization must flow through `jobs`, `job_events`, and delivery/run records so public status and internal diagnostics stay aligned.

</code_context>

<specifics>
## Specific Ideas

- The user chose all recommended defaults for the phase discussion rather than custom exceptions.
- Webhook delivery should retry at three different later times with separate intervals, not just repeat one constant retry delay.
- Delivery exhaustion should not rewrite a successfully processed document job from `completed` to `failed`.
- Input-safety policy should be conservative by default: verify the real file type, fail fast on proven unsafe/corrupt inputs, and avoid speculative retries for bad documents.

</specifics>

<deferred>
## Deferred Ideas

- Operator replay/remediation UX for dead-lettered jobs — deferred to a later phase; Phase 6 only requires inspectable poison/dead-letter visibility.

</deferred>

---
*Phase: 06-reliability-and-input-safety*
*Context gathered: 2026-04-22*
