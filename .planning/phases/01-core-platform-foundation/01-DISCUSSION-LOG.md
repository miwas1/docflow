# Phase 1: Core Platform Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 1-Core Platform Foundation
**Areas discussed:** Service layout, Async backbone, Storage contract, Deployment baseline

---

## Service Layout

| Option | Description | Selected |
|--------|-------------|----------|
| One Python monorepo with multiple deployable services inside it | Fastest to build, shared contracts stay close together, still service-oriented | |
| Fully separate repos/services from day one | Stronger operational boundaries from the start, but more setup overhead | ✓ |
| One API app + one worker app first, split OCR/classification later | Simplest short-term path, but drifts away from the settled system design | |

**User's choice:** Fully separate repos/services from day one.
**Notes:** User selected `2` after confirming that much of the architecture was already settled in `system_design.txt`.

## Async Backbone

| Option | Description | Selected |
|--------|-------------|----------|
| RabbitMQ + Celery | Mature, pragmatic queue-first worker stack and the recommended Phase 1 choice | ✓ |
| Redis + Celery/RQ | Simpler locally, but weaker durability/fit for the intended production workflow | |
| Kafka + custom consumers | Powerful at scale, but too heavy for the foundation phase | |
| Temporal | Strong workflow semantics, but a bigger platform commitment than needed at this stage | |

**User's choice:** RabbitMQ + Celery.
**Notes:** This locks the initial async/control-plane stack for planning.

## Storage Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Single Postgres metadata schema + single object-storage bucket/prefix strategy | Cleanest foundation, logical namespacing handles separation without extra infrastructure | ✓ |
| Separate databases or buckets per service | More isolated, but unnecessarily complex for Phase 1 | |
| Single Postgres with separate buckets/containers by artifact type | Stronger physical separation, but more moving parts than needed initially | |

**User's choice:** Single Postgres metadata store + single object-storage namespace strategy.
**Notes:** Logical separation should happen by tenant/job/stage rather than infrastructure sprawl.

## Deployment Baseline

| Option | Description | Selected |
|--------|-------------|----------|
| Docker Compose locally + Kubernetes-ready manifests for cloud later | Fast dev loop, Kubernetes-aligned path later | |
| Docker Compose locally + Terraform for managed AWS/GCP services, Kubernetes deferred | Cloud-oriented without K8s overhead in the first runnable version | ✓ |
| Kubernetes from day one | Most production-like, but too much foundation-phase overhead | |

**User's choice:** Docker Compose locally + Terraform for managed AWS/GCP services, Kubernetes deferred.
**Notes:** Keeps the platform cloud-oriented for AWS/GCP without requiring Kubernetes immediately.

---

*Phase: 01-core-platform-foundation*
*Discussion logged: 2026-04-21*
