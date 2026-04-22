# Phase 3: Hybrid Extraction Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 03-hybrid-extraction-pipeline
**Areas discussed:** Routing policy, Normalized extracted-text contract, File-type handling policy, Failure and fallback behavior

---

## Routing Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Try embedded-text detection first, use direct extraction when usable, otherwise fall back to OCR | Best fit for the hybrid roadmap and system design | ✓ |
| Route by file type only | Simpler but too blunt for PDFs | |
| Always OCR PDFs | Operationally simple but defeats the hybrid advantage for native PDFs | |

**User's choice:** Try embedded-text detection first, then fall back to OCR if needed
**Notes:** This locks in the hybrid PDF rule for Phase 3.

## Normalized Extracted-Text Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Text plus traceability metadata | Includes page order, extraction path, source artifact references, and production traceability | ✓ |
| Text only | Too thin for debugging and downstream classification | |
| Text plus full page-level/layout detail in the main contract | Richer, but pushes layout-product concerns into Phase 3 | |

**User's choice:** Text plus traceability metadata
**Notes:** The Phase 3 output stays text-first without becoming a full layout API.

## File-Type Handling Policy

| Option | Description | Selected |
|--------|-------------|----------|
| One normalized extraction pipeline with format-specific adapters | Keeps one public contract while using the right parser/OCR path per type | ✓ |
| Split digital parsing and OCR into visibly different public contracts | Weakens the normalized-pipeline goal | |
| Treat only PDFs and images in Phase 3 | Leaves DOCX/TXT/JSON requirements partially unresolved | |

**User's choice:** One normalized extraction pipeline with format-specific adapters
**Notes:** All supported inputs converge on the same extracted-text contract.

## Failure and Fallback Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Use defined fallback rules and record the chosen path in metadata | Best fit for a production pipeline | ✓ |
| Fail fast on the first extraction-path failure | Simpler but gives up useful recovery | |
| Always try every possible path before failing | More aggressive but less predictable and more expensive | |

**User's choice:** Use defined fallback rules with explicit metadata
**Notes:** Fallback behavior must be deterministic and traceable in stage/artifact metadata.

---

## Outcome

All initially identified gray areas for Phase 3 were discussed and resolved.
