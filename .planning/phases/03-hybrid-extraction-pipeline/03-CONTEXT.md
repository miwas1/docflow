# Phase 3: Hybrid Extraction Pipeline - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the normalized extraction pipeline for supported digital and scanned inputs. It decides whether each document should use direct parsing or OCR, converts all supported file types into one shared extracted-text contract, and records enough metadata to explain which path was used and how the final text was produced. It does not add classification behavior, webhook delivery, or richer layout-product contracts yet.

</domain>

<decisions>
## Implementation Decisions

### Routing Policy
- **D-01:** For PDFs, try embedded-text detection first and use direct extraction when the detected text is usable.
- **D-02:** If embedded-text detection fails or yields unusable PDF text, fall back to OCR instead of routing by MIME type alone or always OCRing PDFs.

### Normalized Output Contract
- **D-03:** The shared extracted-text contract must include extracted text plus traceability metadata.
- **D-04:** That metadata should include page order, extraction path used, source artifact references, and enough information to explain how the text was produced.

### File-Type Handling
- **D-05:** Keep one normalized extraction pipeline for all supported formats.
- **D-06:** Use format-specific adapters per input type so DOCX, TXT, JSON, native PDFs, scanned PDFs, and images each use the right parser/OCR path before converging on the shared extracted-text contract.

### Failure and Fallback Behavior
- **D-07:** Use defined fallback rules when extraction fails or yields unusable output, rather than failing immediately on the first path.
- **D-08:** Whenever a fallback path is used, record the chosen path explicitly in extraction metadata and stage/artifact records.

### the agent's Discretion
- Exact heuristics for what counts as “usable” embedded PDF text, as long as the system tries direct extraction first and falls back explicitly when needed.
- Exact extracted-text schema field names and internal adapter/module layout, as long as the output includes text plus the locked traceability metadata.
- Exact retry thresholds or parser/OCR fallback triggers per file type, as long as the final behavior remains deterministic and traceable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements
- `.planning/PROJECT.md` — Product shape, supported inputs, fixed taxonomy boundary, and cloud/backend constraints.
- `.planning/REQUIREMENTS.md` — Phase 3 requirements `EXT-01`, `EXT-02`, `EXT-03`, `EXT-04`, `EXT-05`, and `EXT-06`.
- `.planning/ROADMAP.md` — Phase 3 goal, mapped requirements, and success criteria.
- `.planning/STATE.md` — Current project state and workflow context.

### Prior Phase Contracts
- `.planning/phases/01-core-platform-foundation/01-CONTEXT.md` — Locked architecture decisions for service boundaries, storage strategy, queue backbone, and system design authority.
- `.planning/phases/02-external-ingestion-contract/02-CONTEXT.md` — Locked upload, idempotency, and stage-based status semantics that the extraction pipeline must build on.
- `services/api/src/api_service/services/ingestion.py` — Current upload acceptance flow and initial `accepted` stage creation.
- `services/api/src/api_service/db/models.py` — Existing `jobs`, `job_events`, and `artifacts` persistence contract that extraction must extend.
- `packages/contracts/src/doc_platform_contracts/storage_keys.py` — Canonical object-storage key strategy for raw and derived artifacts.
- `docs/foundation/storage-contract.md` — Shared artifact namespace and metadata-vs-blob storage responsibilities.

### System Design
- `system_design.txt` — Source-of-truth architecture decisions including hybrid extraction, OCR/classification service boundaries, and page-level OCR with document-level aggregation.
- `system_design_diagram.md` — Visual topology for upload → workflow → extraction/OCR → classification.
- `document_inference_platform_done_checklist.md` — Release-quality expectations the extraction pipeline should support.
- `docs/superpowers/plans/2026-04-21-document-inference-platform-implementation-plan.md` — Project implementation plan that explicitly describes hybrid extraction, OCR aggregation, and extracted artifact lineage.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/api/src/api_service/services/ingestion.py`: current upload acceptance flow already validates supported types, persists the original artifact, and creates the first job/event records.
- `services/api/src/api_service/storage.py`: storage adapter already builds canonical artifact keys and URIs.
- `services/api/src/api_service/db/models.py`: `jobs`, `job_events`, and `artifacts` tables already support stage/state/artifact lineage tracking.
- `services/extractor/src/extractor_service/main.py`: extractor service boundary exists and can evolve into the OCR/direct-extraction surface.

### Established Patterns
- API accepts work, persists it durably, and hands off to the async queue backbone rather than performing heavy work inline.
- Storage artifacts should stay in the single object-storage namespace strategy established in Phase 1.
- Status semantics are stage-based, so extraction should record meaningful path/stage metadata instead of inventing a separate progress model.
- Service boundaries remain split, so extraction logic should fit the existing API/orchestrator/extractor separation rather than collapsing into one monolith.

### Integration Points
- Phase 3 should extend the accepted upload flow by moving jobs from `accepted` into extraction-specific stages.
- The extractor service boundary is the natural place for OCR and direct-parsing adapters or the HTTP surface that wraps them.
- `job_events` and `artifacts` should record which extraction path was used and which output artifacts were produced.
- The normalized extracted-text output should be shaped so Phase 4 classification can consume it without needing format-specific branches.

</code_context>

<specifics>
## Specific Ideas

- Native PDFs should use direct extraction only when embedded text is actually usable, not just because the MIME type says PDF.
- The extracted-text contract should stay text-first, with traceability metadata included, rather than becoming a rich layout API in this phase.
- Every supported input type should enter one normalized extraction pipeline through a format-specific adapter.
- Fallback behavior should be explicit and observable in metadata whenever the system switches paths.

</specifics>

<deferred>
## Deferred Ideas

- Rich page-layout or bounding-box output in the main extraction contract was deferred; this phase only locks text plus traceability metadata.
- “Always try every possible extraction path” was deferred in favor of deterministic fallback rules with explicit metadata.
- Any richer layout-product behavior or advanced extraction representation belongs in later phases once the text pipeline is stable.

</deferred>

---
*Phase: 03-hybrid-extraction-pipeline*
*Context gathered: 2026-04-21*
