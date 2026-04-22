# Phase 4: Classification and Results - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 04-classification-and-results
**Areas discussed:** Results contract shape, Classification response richness, Low-confidence policy, Initial classifier strategy, Results retrieval UX

---

## Results Contract Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Return full extracted text inline, plus classification, model metadata, and artifact references | Best fit for external integrators and traceability | ✓ |
| Return classification + metadata only, fetch extracted text separately | Leaner response but adds client round-trips | |
| Return a compact preview inline and rely on artifact references for full text | Smaller payload but weaker default client ergonomics | |

**User's choice:** Return full extracted text inline, plus classification, model metadata, and artifact references
**Notes:** Phase 4 results should be one useful client-facing response without giving up durable traceability.

## Classification Response Richness

| Option | Description | Selected |
|--------|-------------|----------|
| Final label + confidence only | Simple, but thin for threshold tuning and diagnostics | |
| Final label + confidence + top candidate labels/scores | Good observability without heavy explainability scope | ✓ |
| Final label + confidence + candidate labels + simple reasons/policy metadata | Richer, but more contract surface than needed for the baseline | |

**User's choice:** Final label + confidence + top candidate labels/scores
**Notes:** Candidate labels are included for debugging and operational clarity without turning Phase 4 into a full explainability phase.

## Low-Confidence Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Below threshold, final API label is always `unknown/other` | Safest and most stable public contract | ✓ |
| Return best label anyway, but mark it `low_confidence` | More permissive, but weaker safety semantics | |
| Return both `predicted_label` and `final_label` | Richer internals, but more contract complexity for the first pass | |

**User's choice:** Below threshold, final API label is always `unknown/other`
**Notes:** The public contract should be conservative when the model is not confident.

## Initial Classifier Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pragmatic baseline first, even if the first model is simple | Best fit for a shippable Phase 4 vertical slice | ✓ |
| Integrate a stronger open source ML model from the start | Potentially better quality, but slower to ship and verify | |
| Hybrid baseline now with explicit model-swapping design | Strong direction, but the baseline-first recommendation already implies this shape | |

**User's choice:** Pragmatic baseline first
**Notes:** Phase 4 should get the end-to-end classification/results contract working first while preserving later model-swap flexibility.

## Results Retrieval UX

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated results endpoint only | Clean separation, but no direct bridge from current polling flow | |
| Embed results in the existing job status response when completed | Simpler surface count, but overloads status semantics | |
| Both: status endpoint for lifecycle, dedicated results endpoint for final payload | Best fit for stable client polling plus clear final retrieval | ✓ |

**User's choice:** Both: status endpoint for lifecycle, dedicated results endpoint for final payload
**Notes:** Status remains lifecycle-focused while results retrieval gets its own stable contract.

---

## Outcome

All identified gray areas for Phase 4 were discussed and resolved using the recommended defaults.
