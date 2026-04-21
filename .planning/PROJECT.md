# Open Source Document OCR and Classification Platform

## What This Is

This project is an API-first backend platform for asynchronous document text extraction and document classification, built primarily for external client systems that integrate through APIs, polling endpoints, and webhooks. It accepts scanned/image-based files that require OCR as well as native digital documents such as normal PDFs, DOCX, TXT, and JSON, choosing direct text extraction when possible and OCR only when needed. The platform stores raw and derived artifacts, runs text extraction and classification as distinct pipeline stages, and provides an operator dashboard for internal monitoring and debugging. The platform is designed around open source models and libraries and is intended for deployment on AWS or GCP.

## Core Value

External clients can reliably submit scanned or digital documents and receive accurate extracted text plus document classification results through a production-ready asynchronous platform.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Clients can upload PDFs, supported image files, DOCX, TXT, and JSON to an asynchronous processing API and retrieve job status/results through stable APIs and webhooks.
- [ ] The platform can route documents through direct text extraction for native digital files and OCR for scanned/image-based files, with classification running as a distinct downstream service using open source models and libraries.
- [ ] The platform can classify documents into the initial v1 taxonomy: invoice, receipt, bank statement, ID card, utility bill, contract, medical record, tax form, and unknown/other.
- [ ] The platform stores raw uploads, page-level and document-level artifacts, model/version metadata, and operational status for traceability and reprocessing.
- [ ] Operators can monitor queue depth, job state, failures, latency, and model versions through an internal dashboard and observability stack.
- [ ] The system is designed for cloud deployment on AWS or GCP with no-downtime model rollout capability.

### Out of Scope

- End-user SaaS features such as customer accounts, billing, and polished self-serve UI — v1 is backend/API-first for external system integration.
- Open-ended arbitrary classification taxonomy editing in v1 — start with a fixed high-value label set before adding configurable labels.
- Human review workflows and advanced adjudication tooling — useful later, but not required to validate the core asynchronous platform.
- Heavy image enhancement beyond practical normalization, deskew, and autorotation — defer until dataset evidence proves it materially improves OCR quality.
- Arbitrary binary office formats beyond the initial supported set of PDF, image, DOCX, TXT, and JSON — expand after the ingestion and extraction contracts stabilize.

## Context

The source design describes a queue-driven document-processing backend with an upload API, durable metadata store, object storage for artifacts, a workflow engine, preprocessing workers, OCR and classification inference services, result writing, webhook delivery, and status/dashboard surfaces. That design now needs a broader extraction layer: native digital files should bypass OCR when their text can be extracted directly, while scanned PDFs and images still follow page-level OCR with document-level aggregation so retries are cheap, scaling is independent, and large multi-page documents are handled more safely. The system must preserve artifact lineage, model versions, routing policy, and rollout metadata because reliability, observability, and reproducibility matter as much as model quality.

The initial release is intended for external client systems rather than internal-only operators, so the API contract, webhook semantics, traceability, and failure handling are core product requirements rather than internal implementation details. Model quality matters for both extraction and classification, but the platform also needs to be production-reliable from the first release. Open source models and libraries are preferred across parsing, OCR, classification, orchestration, storage, and observability where practical.

## Constraints

- **Deployment**: Target AWS or GCP — the platform should be designed for cloud deployment rather than local-only hosting.
- **Product Scope**: API/backend platform first — avoid turning v1 into a full end-user SaaS product.
- **Model Strategy**: Prefer open source models and libraries — reduce lock-in and keep model hosting under our control.
- **Classification Scope**: Fixed initial taxonomy — prioritize quality and evaluation on a known label set before expanding.
- **Extraction Strategy**: Hybrid extraction path — use direct parsing for digital documents and OCR for scanned/image-based inputs.
- **Architecture**: Asynchronous staged pipeline — extraction and classification must remain independently deployable and scalable.
- **Observability**: Production-grade tracing, metrics, and logs — external integrations require operable failure diagnosis and rollout safety.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build an API/backend-first platform for v1 | External client systems are the primary users, and the operator dashboard supports operations rather than serving as the main product | — Pending |
| Optimize for both useful extraction/classification quality and reliable production execution | The project should not trade away document understanding usefulness or platform reliability | — Pending |
| Start with a fixed document taxonomy including `unknown / other` | A known v1 label set enables clearer evaluation, fallbacks, and rollout criteria | — Pending |
| Use open source models and libraries where practical | The project explicitly aims for controllable, self-hostable infrastructure and inference components | — Pending |
| Design for AWS or GCP deployment from the start | Cloud deployment is a stated constraint and affects architecture, observability, and rollout design | — Pending |
| Support both scanned and native digital documents in v1 | External clients will upload normal PDFs, DOCX, TXT, and JSON in addition to OCR-heavy inputs, so extraction must branch by document type | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-21 after initialization*
