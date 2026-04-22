# Quick Task 260422-tp1: Implement ModernBERT CPU EC2 bootstrap and classifier runtime - Context

**Gathered:** 2026-04-22
**Status:** Ready for execution

<domain>
## Task Boundary

Implement the approved ModernBERT EC2 dev setup design by adding a CPU-friendly classifier runtime, a one-time EC2 bootstrap script, compose wiring for a persistent model cache, and README updates.

</domain>

<decisions>
## Locked Decisions

- Use a one-time bootstrap script, not cloud-init.
- Target CPU-only EC2 development.
- Download the model during bootstrap rather than lazy startup.
- Keep daily development centered on `docker compose up --build`.
- Mount a persistent host Hugging Face cache into the classifier container.

</decisions>
