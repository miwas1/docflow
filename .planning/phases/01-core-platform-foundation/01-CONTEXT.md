# Phase 1: Core Platform Foundation - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase establishes the initial backend platform foundation for the project: repository structure, deployable service boundaries, durable storage model, and cloud-ready local/deployment baseline. It does not implement document ingestion behavior, extraction logic, classification behavior, or customer-facing integrations yet; it creates the stable platform skeleton those later phases will build on.

</domain>

<decisions>
## Implementation Decisions

### Service Layout
- **D-01:** Start with fully separate services from day one rather than a modular monolith.
- **D-02:** The Phase 1 service split should reflect the system design boundary: API-facing service(s), worker/control-plane service(s), and separate extraction/OCR and classification service surfaces even if some start as stubs.

### Async Backbone
- **D-03:** Standardize on `RabbitMQ + Celery` as the initial queue-and-worker backbone.
- **D-04:** Phase 1 should optimize for pragmatic reliability and fast implementation, not for event-streaming complexity or heavyweight workflow infrastructure.

### Storage Contract
- **D-05:** Use a single Postgres metadata store for jobs, state transitions, audit-relevant records, and model/version metadata.
- **D-06:** Use a single object-storage bucket/container strategy with logical namespacing by tenant/job/stage instead of separate infrastructure per service or artifact type.

### Deployment Baseline
- **D-07:** Use Docker Compose for local development.
- **D-08:** Use Terraform to target managed AWS/GCP infrastructure for the cloud baseline.
- **D-09:** Defer Kubernetes-first deployment; Phase 1 should be cloud-aligned without requiring Kubernetes from the first runnable version.

### Settled From Existing Design
- **D-10:** Treat `system_design.txt` as the source of truth for the high-level architecture: queue-driven workflow, Postgres metadata, object storage artifacts, worker-orchestrated control flow, separate OCR/classification services behind HTTP/gRPC, and page-level OCR with document-level aggregation.
- **D-11:** Treat the observability split as already decided for this phase foundation: metrics for aggregates, traces for per-job detail, logs for operational context, and DB for business state.

### the agent's Discretion
- Exact Python framework, package manager, and repo tooling choices within the separate-service architecture.
- Exact Terraform module layout and how aggressively AWS/GCP support is abstracted in the first pass.
- Exact Docker Compose service names and local developer ergonomics, as long as they preserve the locked service boundaries above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Product and Scope
- `.planning/PROJECT.md` — Product shape, fixed constraints, hybrid extraction strategy, deployment target, and v1 boundaries.
- `.planning/REQUIREMENTS.md` — Phase-adjacent requirements, especially `OPS-01`, `OPS-02`, and `SEC-06`.
- `.planning/ROADMAP.md` — Phase 1 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current project state and initialization decisions.

### System Design
- `system_design.txt` — Canonical architecture decisions for workflow, storage, service boundaries, observability, and rollout/versioning direction.
- `system_design_diagram.md` — Visual system topology aligned with the textual design.
- `document_inference_platform_done_checklist.md` — Definition-of-done criteria that the platform foundation must support later.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No reusable application code exists yet — Phase 1 will create the initial project structure and shared foundation assets.

### Established Patterns
- Planning artifacts establish the intended pattern: separate services, queue-driven orchestration, single metadata database, single object-storage namespace strategy, and cloud-oriented deployment.

### Integration Points
- Phase 1 should create the structural integration points that later phases plug into:
- API service boundary for upload/status/results surfaces
- Worker/control-plane boundary for async job orchestration
- Extraction/OCR service boundary
- Classification service boundary
- Shared Postgres metadata contract
- Shared object-storage artifact contract
- Shared messaging contract via RabbitMQ/Celery

</code_context>

<specifics>
## Specific Ideas

- The user explicitly called out that many Phase 1 decisions were already settled in `system_design.txt`; discussion should not reopen those settled architecture choices.
- Observability was intentionally not re-discussed because the design already fixed the metrics/traces/logs split and high-cardinality guidance.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 01-core-platform-foundation*
*Context gathered: 2026-04-21*
