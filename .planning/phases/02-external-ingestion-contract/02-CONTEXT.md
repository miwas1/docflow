# Phase 2: External Ingestion Contract - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the authenticated external ingestion surface for clients to submit supported files, receive stable asynchronous identifiers, and poll lifecycle state consistently. It does not implement extraction/classification logic or webhook delivery yet; it defines the upload, idempotency, auth, and status contracts that hand work off to the existing async backbone.

</domain>

<decisions>
## Implementation Decisions

### Authentication Contract
- **D-01:** Protect Phase 2 external client APIs with static API keys per client.
- **D-02:** Treat API key authentication as the Phase 2 v1 contract instead of bearer token or JWT issuance flows.

### Upload Contract
- **D-03:** Expose a single authenticated `multipart/form-data` upload endpoint as the primary submission surface.
- **D-04:** Phase 2 should optimize for a simple reliable ingestion contract rather than presigned-upload or split create-job/upload flows.

### Idempotency
- **D-05:** Duplicate submissions with the same idempotency key must return the original accepted `job_id` and `document_id` instead of creating a new job.
- **D-06:** Client retries should be transparent when the server recognizes the same accepted submission.

### Status Polling
- **D-07:** Status responses should be stage-based and include `status`, `current_stage`, stable identifiers, timestamps, and terminal failure reason when relevant.
- **D-08:** Do not commit to percentage-based progress in Phase 2; rely on lifecycle and stage semantics backed by the existing job/event model.

### the agent's Discretion
- Exact API key storage/rotation schema, as long as Phase 2 clearly supports static per-client keys.
- Exact endpoint naming, request validation structure, and error envelope layout, as long as they satisfy the upload/status/idempotency requirements.
- Exact timestamp field names and whether stage history is returned inline or derived from `job_events`, as long as the status contract stays stage-based.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements
- `.planning/PROJECT.md` — API-first product scope, supported input types, and deployment constraints for the platform.
- `.planning/REQUIREMENTS.md` — Phase 2 requirements `ING-01`, `ING-02`, `ING-03`, `ING-04`, `ING-05`, `DLV-01`, `DLV-02`, and `SEC-01`.
- `.planning/ROADMAP.md` — Phase 2 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current project state and workflow context.

### Prior Phase Contracts
- `.planning/phases/01-core-platform-foundation/01-CONTEXT.md` — Locked decisions for service boundaries, async backbone, storage contract, and deployment baseline.
- `services/api/src/api_service/db/models.py` — Existing `jobs`, `job_events`, `artifacts`, and `model_versions` persistence contract that Phase 2 should extend rather than replace.
- `services/api/src/api_service/storage.py` — Current storage adapter stub and artifact URI behavior.
- `packages/contracts/src/doc_platform_contracts/storage_keys.py` — Canonical object-storage namespace strategy already fixed in Phase 1.
- `docs/foundation/storage-contract.md` — Object storage vs Postgres responsibility boundary established for the platform.

### System Design
- `system_design.txt` — Source-of-truth architecture decisions for upload API → object storage + job DB → workflow engine handoff.
- `system_design_diagram.md` — Visual topology for the upload/status surface and async control flow.
- `document_inference_platform_done_checklist.md` — Release-quality checklist that Phase 2 should support without reopening architecture choices.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/api/src/api_service/main.py`: existing FastAPI app scaffold and service boundary for adding external ingestion endpoints.
- `services/api/src/api_service/db/models.py`: existing `jobs`, `job_events`, and `artifacts` tables provide the natural persistence extension points for upload metadata and stage polling.
- `services/api/src/api_service/storage.py`: storage adapter stub already matches the Phase 1 object-storage contract and can back raw upload persistence.
- `services/api/src/api_service/config.py` and `packages/contracts/src/doc_platform_contracts/settings.py`: existing environment-driven config path can absorb auth and upload-related settings.

### Established Patterns
- API work belongs in the dedicated `services/api` service rather than in the orchestrator or shared package.
- RabbitMQ + Celery remain the handoff mechanism after a request is durably accepted.
- Postgres stores job metadata and stage state while object storage stores uploaded file blobs and derived artifacts.
- Status semantics should align with `jobs.status`, `jobs.current_stage`, and `job_events` instead of inventing a parallel tracking system.

### Integration Points
- New upload and status endpoints should attach to the existing FastAPI app in `services/api`.
- Accepted uploads should create/extend `jobs`, `job_events`, and `artifacts` records and persist the raw file through the storage adapter.
- Auth enforcement should live at the API boundary and apply to both upload and polling endpoints.
- Async submission should hand off to the existing queue-driven orchestrator boundary once durable acceptance is complete.

</code_context>

<specifics>
## Specific Ideas

- Authentication should stay intentionally simple in v1: static API keys per external client rather than token issuance.
- The upload contract should be simple for client integrators: one authenticated multipart submission endpoint.
- Retry safety matters more than novelty: the same idempotency key should return the original accepted identifiers.
- Polling should expose lifecycle stage and terminal error detail, but not percentage progress that the current platform cannot yet justify accurately.

</specifics>

<deferred>
## Deferred Ideas

- Bearer token / JWT authentication flows were considered but deferred because they add issuance and validation complexity beyond the needs of this phase.
- Presigned object-storage uploads and two-step create-job/upload flows were considered but deferred to keep the first client contract straightforward.
- Percentage-based progress reporting was deferred until later phases produce reliable measurable progress signals.

</deferred>

---
*Phase: 02-external-ingestion-contract*
*Context gathered: 2026-04-21*
