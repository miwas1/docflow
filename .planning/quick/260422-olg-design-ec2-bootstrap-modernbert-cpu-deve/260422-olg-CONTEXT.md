# Quick Task 260422-olg: Design EC2 bootstrap + ModernBERT CPU development setup for classifier service - Context

**Gathered:** 2026-04-22
**Status:** Completed

<domain>
## Task Boundary

Design a one-time EC2 bootstrap workflow for CPU-only ModernBERT development. The setup must pre-download the model during setup and keep daily development centered on normal `docker compose up --build` runs using current repo code.

</domain>

<decisions>
## Implementation Decisions

- Use a one-time bootstrap script rather than cloud-init or per-boot automation.
- Target CPU-only EC2 development.
- Download the ModernBERT model during setup instead of at first classifier startup.
- Keep the existing Docker Compose workflow as the daily development entry point.
- Persist the Hugging Face model cache on the EC2 host and mount it into the classifier container.

</decisions>

<specifics>
## Specific Ideas

- The classifier service should stay the only service aware of the model runtime.
- The bootstrap script should be idempotent.
- Startup should fail clearly if the configured model is missing from the mounted cache.
- README updates are required once implementation lands so the repo’s local and EC2 setup remains current.

</specifics>
