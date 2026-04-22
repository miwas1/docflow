# Phase 2: External Ingestion Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 02-external-ingestion-contract
**Areas discussed:** Authentication contract, Upload API shape, Idempotency behavior, Status response contract

---

## Authentication Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Static API key per client | Simple server-to-server auth and best fit for the phase | ✓ |
| Bearer token / JWT | More flexible but adds issuance and validation complexity | |
| Both | Most flexible but expands v1 surface area | |

**User's choice:** Static API key per client
**Notes:** User chose the simplest v1 auth contract for external clients.

## Upload API Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single authenticated `multipart/form-data` upload endpoint | Simplest client experience and fastest path to a working async contract | ✓ |
| Two-step create-job then upload-binary flow | Cleaner separation but adds immediate client/server complexity | |
| Presigned object-storage upload flow | Most scalable long term but pushes storage details into the external contract too early | |

**User's choice:** Single authenticated `multipart/form-data` upload endpoint
**Notes:** User preferred the most straightforward ingestion surface for Phase 2.

## Idempotency Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Return the original accepted job/document IDs without creating a new job | Safest and most typical retry behavior | ✓ |
| Reject the duplicate with a specific conflict/error response | Clearer duplicate signaling but forces special-case retry handling | |
| Re-accept if the binary differs, otherwise return the original job | Flexible but adds subtle duplicate semantics early | |

**User's choice:** Return the original accepted identifiers
**Notes:** User wants duplicate retries to be transparent rather than produce new jobs.

## Status Response Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Stage-based status with `status`, `current_stage`, IDs, timestamps, and failure reason when relevant | Best fit for the existing job/event schema | ✓ |
| Minimal status only | Simpler but too thin for realistic external integrations | |
| Rich status plus explicit percentage progress | More informative but hard to justify accurately this early | |

**User's choice:** Stage-based status with identifiers, timestamps, and failure reason
**Notes:** User chose richer lifecycle visibility without locking the platform into percentage progress semantics.

---

## Outcome

All initially identified gray areas for Phase 2 were discussed and resolved.
