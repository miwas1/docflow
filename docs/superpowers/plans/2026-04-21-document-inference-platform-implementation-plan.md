# Document Inference Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready asynchronous document OCR and classification platform that accepts PDFs/images, processes them through independent OCR and classification services, persists artifact lineage, and exposes results through polling APIs, webhooks, and operator visibility tools.

**Architecture:** The platform follows a queue-driven backend design with an upload API, Postgres metadata store, object storage for raw and derived artifacts, a workflow/worker layer that orchestrates preprocessing, OCR, aggregation, classification, result writing, and webhook delivery, plus separate OCR and classification inference services behind HTTP/gRPC. The delivery strategy is phased: establish the platform contract and infrastructure first, then ship a thin end-to-end MVP, then add resilience, observability, rollout safety, and operational hardening until the Definition of Done is met.

**Tech Stack:** Python services, Postgres, object storage, Redis/RabbitMQ/Kafka, HTTP/gRPC inference services, Prometheus metrics, tracing, structured logging, containerized deployment, CI/CD.

---

## Planning Assumptions

- The existing `system_design.txt` is the approved architecture baseline.
- The DoD checklist is the release-quality target, not the MVP target.
- The initial milestone should optimize for a working asynchronous happy path before full hardening.
- OCR runs at page level with document-level aggregation.
- Classification runs after OCR aggregation and can scale independently from OCR.
- Model routing/version tracking is a first-class requirement and should not be deferred too late.

## Delivery Strategy

- **MVP boundary:** Upload, async orchestration, preprocessing, OCR, aggregation, classification, result persistence, status polling, and basic observability.
- **Production-ready boundary:** Security controls, retries, dead-lettering, webhook guarantees, dashboarding, performance validation, rollout controls, and documented operations.
- **Execution pattern:** Complete each phase with unit/integration/E2E validation before opening the next phase.

## Phase 0: Foundations and Scope Lock

**Objective**
- Turn the architecture into explicit product and engineering contracts so implementation does not drift.

**Workstreams**
- Define supported file types, max file size, max page count, timeout budgets, and SLA assumptions.
- Separate MVP scope from post-MVP items in the DoD checklist.
- Freeze API contracts for upload, job status, results, and webhook payloads.
- Define the canonical job state machine: `queued -> preprocessing -> ocr -> classifying -> persisting -> completed/failed`.
- Define artifact naming conventions and storage layout for original files, page images, OCR JSON, aggregated text, and classification outputs.
- Define model routing metadata to persist on every job: OCR version, classifier version, routing policy, rollout bucket, tenant override.

**Deliverables**
- Product scope document with MVP/non-MVP split.
- API schema definitions.
- Job state machine diagram.
- Artifact storage contract.
- Model versioning/routing contract.

**Exit Criteria**
- The team can answer every checklist item in sections 1, 2, and the documentation prerequisites without ambiguity.
- No unresolved questions remain around file limits, response schemas, or state transitions.

## Phase 1: Platform Skeleton and Local Developer Stack

**Objective**
- Stand up the minimum deployable system skeleton so every subsystem can be developed against real interfaces.

**Workstreams**
- Bootstrap the API service, worker service, OCR service wrapper, and classification service wrapper.
- Provision local Postgres, object storage emulator, and queue broker.
- Create database schema for documents, jobs, job events, artifacts, webhook subscriptions, and model versions.
- Add service health/readiness endpoints.
- Add shared config, secrets loading, correlation IDs, and structured logging scaffolding.
- Establish CI for linting, unit tests, container builds, and representative local startup.

**Deliverables**
- Repo/service layout.
- Environment configuration templates.
- Initial migrations.
- Docker/dev-compose or equivalent local stack.
- CI pipeline for build/test.

**Exit Criteria**
- A developer can run a representative subset of the platform locally.
- CI builds all services successfully.
- Health probes work for every deployable service.

## Phase 2: Ingestion API and Durable Job Creation

**Objective**
- Accept documents safely, persist them durably, and create asynchronous jobs without performing inline inference.

**Workstreams**
- Implement the upload endpoint for PDFs and supported image formats.
- Validate MIME type, file signature, malformed requests, file size, and page-count limits.
- Add idempotency-key support and duplicate-upload behavior.
- Persist raw files to object storage and metadata to Postgres.
- Enqueue workflow messages and return stable `job_id` and `document_id`.
- Implement job status polling endpoint with consistent schemas across states.

**Deliverables**
- Upload API.
- Job status API.
- Durable storage adapters.
- Queue producer integration.
- Input validation and abuse-protection baseline.

**Exit Criteria**
- Checklist sections 2.1, 2.2, 3, and 4.1-4.4 pass at unit/integration level.
- Upload requests create durable jobs and never block on OCR/classification execution.

## Phase 3: Workflow Engine and Preprocessing Pipeline

**Objective**
- Orchestrate the document through durable asynchronous stages with page-level decomposition and recoverable state transitions.

**Workstreams**
- Implement worker control flow for preprocessing, OCR fan-out, OCR aggregation, classification trigger, result persistence, and terminal state updates.
- Add rasterization, normalization, page splitting, autorotation, and deskew as moderate preprocessing defaults.
- Preserve page ordering and page-count metadata throughout the workflow.
- Add timeout handling, retry policies, duplicate message protection, and dead-letter handling.
- Persist stage progress and failure reasons to the job record.

**Deliverables**
- Workflow stage handlers.
- Preprocessing service/module.
- Page artifact generation.
- Retry/dead-letter configuration.
- Job progress/state transition persistence.

**Exit Criteria**
- Multi-page PDFs and single-image uploads traverse the workflow correctly.
- Independent stage retries work without corrupting prior-stage outputs.
- Worker restart/recovery behavior meets documented guarantees.

## Phase 4: OCR Service Integration and Aggregation

**Objective**
- Run page-level OCR through an independently scalable inference service and aggregate outputs into a document-level result.

**Workstreams**
- Wrap OCR inference behind a stable HTTP/gRPC client/service boundary.
- Send preprocessed page inputs to OCR and persist per-page OCR JSON artifacts.
- Aggregate page OCR into ordered document text and optional layout metadata.
- Record OCR latency, failures, retries, and model version per job.
- Handle OCR timeout, unavailability, and malformed output paths safely.

**Deliverables**
- OCR client wrapper.
- OCR service integration tests.
- Per-page artifact persistence.
- OCR aggregation logic.
- OCR observability instrumentation.

**Exit Criteria**
- Representative PDFs and images produce persisted OCR output in the documented format.
- OCR failures move jobs into retriable or failed states correctly.
- OCR can be scaled separately from classification with no shared mutable state assumptions.

## Phase 5: Classification Service and Result Materialization

**Objective**
- Classify OCR-derived document content using a separate inference service and expose completed results durably.

**Workstreams**
- Wrap the classification model behind a stable service boundary.
- Feed aggregated OCR text and relevant document features into classification.
- Persist label, confidence, model version, and policy-derived outputs such as `unknown` or low-confidence handling.
- Implement results API returning OCR output, classification output, confidence fields, and model/version metadata.
- Finalize result-writer stage to update jobs only after all required outputs are durable.

**Deliverables**
- Classification client wrapper.
- Classification integration tests.
- Results API.
- Final persistence and completion logic.

**Exit Criteria**
- A valid PDF and image can complete end-to-end through upload, async processing, OCR, classification, persistence, and results retrieval.
- Jobs only reach `completed` after all mandatory artifacts and metadata are stored.

## Phase 6: Webhooks, Operator Visibility, and Core Observability

**Objective**
- Make the platform operationally usable for both machine consumers and human operators.

**Workstreams**
- Implement webhook registration, signing/verification, retries with backoff, bounded retry behavior, and dead-letter/terminal failure handling.
- Emit metrics for upload rate, queue depth, OCR latency, classification latency, end-to-end duration, stage failure counts, callback success rate, and model-version request counts.
- Add distributed tracing across API, workers, OCR, classification, persistence, and callback delivery.
- Add structured logs with correlation/job/document/tenant/model identifiers.
- Build a minimal dashboard or operator view for queue depth, job state counts, per-job stage progression, failure reasons, and model versions.

**Deliverables**
- Webhook subsystem.
- Metrics dashboards.
- Alert definitions.
- Tracing setup.
- Operator dashboard/status surfaces.

**Exit Criteria**
- Checklist sections 11, 12, and 13 pass.
- Operators can diagnose job failures without inspecting raw infrastructure logs manually.

## Phase 7: Security, Multi-Tenancy, and Reliability Hardening

**Objective**
- Close the core production-risk gaps around malicious inputs, secrets, tenant isolation, and safe failure behavior.

**Workstreams**
- Enforce authentication/authorization on protected endpoints.
- Add malicious/malformed file handling policy, including corrupt PDFs, encrypted PDFs, spoofed extensions, invalid images, and path safety.
- Protect secrets in config, logs, metrics, and responses.
- Add least-privilege access for object storage and database.
- Add tenant-aware data isolation if multi-tenancy is in scope.
- Validate safe behavior for DB outages, object storage outages, worker crashes, and repeated webhook failures.

**Deliverables**
- Security controls for API and service-to-service paths.
- Input safety validation suite.
- Resilience test matrix for dependency outages.
- Tenant isolation controls where applicable.

**Exit Criteria**
- Checklist sections 3, 10, and 17 pass for in-scope requirements.
- No critical gaps remain around auth, secret handling, or unsafe file processing.

## Phase 8: Model Registry, Rollouts, and No-Downtime Versioning

**Objective**
- Make model updates traceable, reversible, and safe under live traffic.

**Workstreams**
- Implement the explicit routing/model registry layer.
- Persist active OCR/classifier versions and rollout policy metadata.
- Support tenant override and rollout bucket selection.
- Implement and validate shadow traffic for major changes and canary rollout for live model updates.
- Document and test rollback flows.
- Ensure mixed-version traffic remains traceable per job during rollout windows.

**Deliverables**
- Model registry/routing component.
- Rollout configuration and audit trail.
- Canary/shadow test flows.
- Rollback runbook.

**Exit Criteria**
- Checklist section 16 passes.
- New model versions can be introduced without platform downtime and every processed job remains version-traceable.

## Phase 9: Performance, Quality Gates, and Release Readiness

**Objective**
- Prove the platform is fast enough, accurate enough, observable enough, and documented enough to release.

**Workstreams**
- Build representative OCR/classification evaluation datasets and record quality thresholds.
- Measure OCR quality and classification accuracy/F1 by class and model version.
- Run normal-load and peak-load tests for queue backlog, OCR concurrency, classification concurrency, and autoscaling behavior.
- Tune resource requests/limits and backlog-drain behavior.
- Complete the testing pyramid: unit, integration, E2E happy path, failure path, retry path, and model-rollout traceability.
- Finish README, API docs, deployment docs, runbooks, observability docs, supported/unsupported scenarios, and known limitations.

**Deliverables**
- Evaluation datasets and reports.
- Load/performance test results.
- Completed automated test suite in CI.
- Release runbooks and handoff documentation.

**Exit Criteria**
- Checklist sections 14, 15, 18, 19, 20, and 21 pass.
- The team can process representative real documents from upload to final result without manual intervention outside defined review paths.

## Optional Phase 10: Excellent-Not-Just-Done Enhancements

**Objective**
- Add operator and product capabilities that materially improve platform leverage after the core release.

**Candidates**
- Manual review queue for low-confidence documents.
- Reprocessing against newer model versions.
- Per-tenant quotas and rate limits.
- Search over extracted text.
- Cost-per-document metrics.
- SLA/SLO dashboards.
- Shadow benchmarking and regression detection suite.

**Exit Criteria**
- Optional checklist section 22 items are prioritized by business value and sequenced as a follow-on roadmap rather than blocking the first release.

## Recommended Milestone Grouping

### Milestone A: Thin Vertical Slice
- Phase 0
- Phase 1
- Phase 2
- Phase 3
- Phase 4
- Phase 5

**Outcome**
- Working asynchronous platform for upload -> OCR -> classification -> results API.

### Milestone B: Production Operations
- Phase 6
- Phase 7
- Phase 8

**Outcome**
- Operable, secure, traceable, and rollout-safe production platform.

### Milestone C: Release Validation
- Phase 9
- Optional Phase 10

**Outcome**
- Release-quality verification plus roadmap extensions.

## Critical Sequencing Notes

- Do not build the dashboard before the job model, metrics, and failure semantics are stable.
- Do not delay model version persistence until late phases; it must exist before meaningful rollout testing.
- Do not attempt aggressive preprocessing enhancements until baseline OCR quality is measured.
- Do not treat webhook delivery as part of the core happy path; it should consume durable persisted results and remain retryable.
- Do not mark the platform done at MVP completion; most DoD items land after the first vertical slice is working.

## Definition of Done Mapping

- **MVP-complete:** Sections 1, 2, 4, 5, 6, 7, 8, and 9 happy-path criteria.
- **Production-ready:** Sections 3, 10, 11, 12, 13, 16, 17, and 18.
- **Release-ready:** Sections 14, 15, 19, 20, and 21.
- **Stretch roadmap:** Section 22.

## Immediate Next Actions

- [ ] Review and approve this phased plan.
- [ ] Break Milestone A into task-level engineering tickets.
- [ ] Decide the initial broker choice: Redis, RabbitMQ, or Kafka.
- [ ] Decide the initial inference protocol: HTTP or gRPC.
- [ ] Choose the first representative document set for E2E validation.

