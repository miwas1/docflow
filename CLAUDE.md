<!-- GSD:project-start source:PROJECT.md -->
## Project

**Open Source Document OCR and Classification Platform**

This project is an API-first backend platform for asynchronous document text extraction and document classification, built primarily for external client systems that integrate through APIs, polling endpoints, and webhooks. It accepts scanned/image-based files that require OCR as well as native digital documents such as normal PDFs, DOCX, TXT, and JSON, choosing direct text extraction when possible and OCR only when needed. The platform stores raw and derived artifacts, runs text extraction and classification as distinct pipeline stages, and provides an operator dashboard for internal monitoring and debugging. The platform is designed around open source models and libraries and is intended for deployment on AWS or GCP.

**Core Value:** External clients can reliably submit scanned or digital documents and receive accurate extracted text plus document classification results through a production-ready asynchronous platform.

### Constraints

- **Deployment**: Target AWS or GCP — the platform should be designed for cloud deployment rather than local-only hosting.
- **Product Scope**: API/backend platform first — avoid turning v1 into a full end-user SaaS product.
- **Model Strategy**: Prefer open source models and libraries — reduce lock-in and keep model hosting under our control.
- **Classification Scope**: Fixed initial taxonomy — prioritize quality and evaluation on a known label set before expanding.
- **Extraction Strategy**: Hybrid extraction path — use direct parsing for digital documents and OCR for scanned/image-based inputs.
- **Architecture**: Asynchronous staged pipeline — extraction and classification must remain independently deployable and scalable.
- **Observability**: Production-grade tracing, metrics, and logs — external integrations require operable failure diagnosis and rollout safety.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
