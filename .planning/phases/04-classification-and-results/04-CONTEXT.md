# Phase 4: Classification and Results - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase converts the normalized extracted-text payload into a fixed-taxonomy document classification and exposes a stable final-results contract for external clients. It must deliver classifier output, confidence handling, model-version traceability, and durable result retrieval without reopening webhook delivery, dashboard work, or later rollout-hardening concerns.

</domain>

<decisions>
## Implementation Decisions

### Results Contract Shape
- **D-01:** The results payload should return full extracted text inline for the primary client happy path.
- **D-02:** The same payload should also include artifact references and model/version metadata so clients get a complete result without losing traceability to durable storage.

### Classification Response Richness
- **D-03:** The public result contract should always include a final classification label and confidence score.
- **D-04:** The result contract should also include optional top candidate labels and scores so operators and integrators can debug threshold behavior without requiring a separate explainability system.

### Low-Confidence Policy
- **D-05:** The classifier may compute a best internal prediction, but below the configured confidence threshold the final public label should resolve to `unknown/other`.
- **D-06:** The low-confidence policy must be explicit in the result contract rather than implied by missing fields or undocumented behavior.

### Initial Classifier Strategy
- **D-07:** Phase 4 should optimize for a pragmatic baseline classifier that is easy to ship, test, and verify end-to-end before chasing higher-complexity model integration.
- **D-08:** Even with a pragmatic baseline, the service boundary and stored metadata must preserve a clean path to swap in stronger open source models later.

### Results Retrieval UX
- **D-09:** Keep the existing job status endpoint focused on lifecycle polling semantics rather than turning it into the only result surface.
- **D-10:** Add a dedicated results endpoint for final payload retrieval while still allowing clients to use job polling for lifecycle state.
- **D-11:** Results must only be returned after the required extracted-text and classification artifacts have been durably persisted.

### the agent's Discretion
- Exact classifier implementation choice for the pragmatic baseline, as long as it remains an open source-friendly path and preserves later model-swapping flexibility.
- Exact result schema field names for candidate labels, artifact references, and low-confidence policy metadata, as long as the locked behaviors above remain explicit and stable.
- Exact confidence threshold storage/config approach, as long as low-confidence behavior is deterministic and traceable.

</decisions>

<specifics>
## Specific Ideas

- The results API should feel easy for external integrators: one final response should include the usable extracted text, the classification answer, and enough metadata to debug or trace the run.
- Candidate labels are valuable for threshold tuning and diagnostics, but Phase 4 should avoid expanding into a heavy explainability feature set.
- The public contract should be conservative: low-confidence documents resolve safely to `unknown/other` instead of exposing uncertain labels as if they were final truth.
- The classification phase should prioritize a shippable baseline service contract first, while keeping the architecture open for stronger open source ML models later.
- Retrieval should use both lifecycle polling and a dedicated final-results endpoint rather than overloading one endpoint with both responsibilities.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements
- `.planning/PROJECT.md` — Product shape, fixed taxonomy, external-client integration model, and open source model preference.
- `.planning/REQUIREMENTS.md` — Phase 4 requirements `CLS-01`, `CLS-02`, `CLS-03`, `CLS-04`, and `DLV-03`.
- `.planning/ROADMAP.md` — Phase 4 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current workflow state and project progress snapshot.

### Prior Phase Contracts
- `.planning/phases/01-core-platform-foundation/01-CONTEXT.md` — Locked service boundaries, metadata store, object-storage strategy, and async backbone.
- `.planning/phases/02-external-ingestion-contract/02-CONTEXT.md` — Locked upload/auth/idempotency/status semantics that Phase 4 must extend rather than replace.
- `.planning/phases/03-hybrid-extraction-pipeline/03-CONTEXT.md` — Locked normalized extraction contract and extraction traceability decisions that classification must consume.
- `docs/foundation/extraction-contract.md` — Canonical extracted-text payload fields and storage/lineage expectations from Phase 3.
- `docs/foundation/status-polling-contract.md` — Existing status endpoint scope and lifecycle semantics that should remain clean in Phase 4.
- `docs/foundation/storage-contract.md` — Canonical artifact types and durable storage responsibilities, including `classification-result`.

### Existing Code Contracts
- `packages/contracts/src/doc_platform_contracts/extraction.py` — Normalized extracted-text contract the classifier consumes.
- `services/api/src/api_service/db/models.py` — Existing persistence model, including `jobs`, `artifacts`, `extraction_runs`, and `model_versions`.
- `services/api/src/api_service/repositories/jobs.py` — Current extraction completion persistence patterns and job/artifact update helpers to extend for classification/results.
- `services/api/src/api_service/schemas.py` — Existing API response-schema style for upload/status contracts.
- `services/classifier/src/classifier_service/main.py` — Current classifier service boundary to evolve into the Phase 4 inference surface.
- `services/classifier/src/classifier_service/config.py` — Existing config path for classifier runtime settings.

### System Design
- `system_design.txt` — Source-of-truth architecture for extraction -> classification -> persistence -> result delivery.
- `system_design_diagram.md` — Visual system topology for downstream classification and result flow.
- `document_inference_platform_done_checklist.md` — Release-quality checklist for classification, results, and end-to-end completion expectations.
- `docs/superpowers/plans/2026-04-21-document-inference-platform-implementation-plan.md` — End-to-end platform plan describing classification, result persistence, and final retrieval expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/contracts/src/doc_platform_contracts/extraction.py`: already defines the normalized extracted-text contract that Phase 4 should consume without introducing format-specific branching.
- `services/api/src/api_service/db/models.py`: already has durable job, artifact, extraction lineage, and model-version tables that can anchor classification persistence and result retrieval.
- `services/api/src/api_service/repositories/jobs.py`: already establishes the pattern for recording stage completion, creating derived artifacts, and advancing job state.
- `services/api/src/api_service/schemas.py`: existing API schema style gives a natural place to add a dedicated results response model.
- `services/classifier/src/classifier_service/main.py`: classifier service boundary exists and can become the stable HTTP surface for baseline classification.

### Established Patterns
- API accepts and serves client-facing contracts, while background pipeline work remains asynchronous and service-separated.
- Durable artifacts belong in object storage with Postgres storing metadata, lineage, and status rather than embedding large payloads inline in relational tables.
- Stage-based polling is already a locked contract, so Phase 4 should extend it with final retrieval rather than replacing it.
- Extraction output is already normalized and text-first, so classification should remain format-agnostic and consume that shared contract.

### Integration Points
- Phase 4 should extend the existing extraction completion path so jobs advance from extracted artifacts into classification, persistence, and final result readiness.
- The classifier service should consume `ExtractedTextArtifact`-shaped inputs or closely adjacent payloads from the orchestrator/control plane.
- Classification outputs should be persisted as durable `classification-result` artifacts plus DB metadata that links classifier version and final decision to the job.
- The API service should add a dedicated results endpoint while preserving the current status endpoint for lifecycle polling.

</code_context>

<deferred>
## Deferred Ideas

- Rich explainability beyond candidate labels and policy metadata is deferred; Phase 4 should not expand into full rationale-generation or human-review tooling.
- Stronger or larger open source model integrations are deferred beyond the pragmatic baseline, as long as Phase 4 preserves swap-friendly boundaries.
- Webhook delivery, operator dashboard surfaces, and broader observability concerns remain out of scope for this phase and belong to Phase 5.

</deferred>

---
*Phase: 04-classification-and-results*
*Context gathered: 2026-04-21*
