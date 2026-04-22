# Phase 5: Client Delivery and Operator Visibility - Research

**Researched:** 2026-04-22
**Domain:** Signed webhook delivery, internal operator dashboard, and production observability for the existing FastAPI + Celery pipeline
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Webhook Registration and Delivery Model
- **D-01:** Webhook configuration should live at the client/tenant integration level rather than being supplied per upload job.
- **D-02:** Phase 5 webhooks should be emitted for terminal states covering both `completed` and `failed` jobs.
- **D-03:** Webhook delivery should remain asynchronous and consume already-persisted job/results state rather than becoming part of the synchronous client happy path.

### Webhook Payload and Signing Contract
- **D-04:** Webhook requests should use header-based signing with an HMAC-style shared secret over the raw payload.
- **D-05:** The webhook payload should be richer than a pure reference-only callback: it must include stable identifiers and final status plus an inline result summary that helps integrators avoid an immediate follow-up fetch in the common case.
- **D-06:** Even with an inline summary, the webhook contract should still include a durable results reference so clients can retrieve the canonical final payload from the results API when needed.

### Internal Operator Dashboard
- **D-07:** Phase 5 should deliver a rich internal operator dashboard rather than only operator APIs or a thin status page.
- **D-08:** The internal dashboard should prioritize searchable job history, queue/job health, stage progression, webhook delivery visibility, failure diagnostics, and model-version visibility for internal operators.
- **D-09:** The dashboard in this phase is for internal operations staff only, not for external clients.

### Observability and Diagnostics
- **D-10:** Phase 5 should implement production-focused observability with all three layers: alertable aggregate metrics, structured logs, and end-to-end per-job traces.
- **D-11:** Observability must cover API, orchestrator, extraction, classification, persistence, and webhook-delivery flows.
- **D-12:** The operator experience should make failed-job diagnosis possible in normal cases without requiring manual database inspection.

### Claude's Discretion
- Exact webhook subscription schema, secret rotation mechanics, retry schedule, and bounded delivery-attempt counts, as long as the delivery model stays client-level, terminal-state-based, and asynchronous.
- Exact inline result-summary field names and header naming for the webhook signature, as long as the contract remains signed, stable, and traceable back to the canonical results endpoint.
- Exact operator dashboard implementation approach and UI architecture, as long as it remains an internal operational surface and fulfills the richer diagnostics/history goals above.
- Exact observability library/tool wiring and metric names, as long as the platform preserves the locked split of aggregate metrics, per-job traces, and structured logs.

### Deferred Ideas (OUT OF SCOPE)
- External client job-history dashboard — useful future product surface, but outside the internal operator visibility scope of Phase 5.
- Client self-service webhook configuration UI — valuable, but belongs in a later client-management phase rather than the first internal delivery/ops phase.
- Client API key management UI or portal — out of scope for this phase; Phase 2 only locked the backend API-key auth contract.
- Separate future client-facing management console plus a broader internal admin suite — keep as roadmap candidates after the internal operator foundation is in place.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DLV-04 | Platform supports signed completion webhooks with retries and bounded failure behavior. | Durable webhook endpoint + delivery-attempt tables, Celery retry/backoff on `document.webhook`, HMAC timestamp signing, replay protection, operator visibility for failed deliveries. |
| DLV-05 | Webhook payload includes job ID, document ID, final status, and result reference fields. | Payload should be assembled from persisted `jobs`, `classification_runs`, artifacts, and canonical results route, with inline summary plus results URL. |
| OPS-03 | Operator dashboard shows queued, running, completed, and failed job counts plus per-job stage progression. | API-owned read models over `jobs` + `job_events`, queue health inputs, searchable list/detail views, and internal dashboard templates. |
| OPS-04 | Operator dashboard exposes failure reasons, latency signals, and model versions used for each job. | Dashboard drill-down should join `jobs`, `extraction_runs`, `classification_runs`, and webhook deliveries; metrics provide latency aggregates while traces/logs provide deep diagnostics. |
| OPS-05 | Platform emits structured logs, metrics, and traces for APIs, workers, extraction, classification, and webhook delivery. | Shared OpenTelemetry bootstrap, Prometheus metrics, JSON logging, and trace context propagation across FastAPI, Celery, SQLAlchemy, outbound HTTP, and worker stages. |
</phase_requirements>

## Summary

Phase 5 should be planned as three tightly related deliverables that share the same durable source of truth: `jobs`, `job_events`, `artifacts`, `extraction_runs`, and `classification_runs` already exist, and the webhook queue already exists. The cleanest plan is to extend the API-owned metadata schema with client-level webhook configuration and delivery-attempt records, drive webhook dispatch through the existing `document.webhook` queue after terminal state is durably written, and build the operator dashboard as an internal read surface over those same persisted records rather than inventing a second state store.

Because the repo is currently Python-only and has no frontend build pipeline, the least risky dashboard approach is to keep the operator UI inside `services/api` using FastAPI templates plus read-only operator routes and optional JSON endpoints for richer drill-downs. That avoids introducing a separate React/Vite application, separate deployment artifact, and a second auth/runtime stack in the middle of an operations-focused phase.

Observability should be planned as shared infrastructure, not as a set of ad hoc per-service add-ons. Use OpenTelemetry for traces and log correlation, Prometheus-style metrics for alertable aggregates, and structured JSON logs with stable identifiers. Do not put `job_id`, `document_id`, webhook URL, or tenant IDs into metric labels; those belong in traces/logs and in the dashboard’s searchable views.

**Primary recommendation:** Plan Phase 5 around a durable webhook outbox pattern, API-integrated internal dashboard, and shared OpenTelemetry + Prometheus instrumentation bootstrap across all services.

## Project Constraints (from AGENTS.md)

- Deployment target is AWS or GCP, not a local-only design.
- Keep v1 API/backend-first; do not turn this phase into a customer portal.
- Prefer open source libraries and self-hostable components.
- Preserve the asynchronous staged pipeline; extraction and classification remain independently deployable.
- Preserve production-grade tracing, metrics, and logs as a first-class requirement.
- Do not make direct repo edits outside a GSD workflow unless explicitly asked to bypass it.
- Local setup documentation in `README.md` must stay current when implementation lands.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | Existing repo constraint `>=0.115,<1.0` (current PyPI head verified: `0.135.2`, 2026-03-23) | Keep API and internal operator routes in one service | Preserves current service boundary and avoids a second app stack for an internal-only dashboard. |
| Celery | Existing repo constraint `>=5.4,<6.0` (current PyPI head verified: `5.6.3`, 2026-03-26) | Durable async webhook delivery on `document.webhook` | Already owns worker orchestration; built-in retry/backoff is sufficient for webhook delivery. |
| HTTPX | `0.28.1` (2024-12-06) | Outbound webhook delivery client | Modern Python HTTP client with strict timeouts and sync/async support. |
| Jinja2 | `3.1.6` (2025-03-05) | Internal dashboard templating in `services/api` | Supported directly by FastAPI templating; keeps dashboard deployment simple. |
| OpenTelemetry SDK | `1.41.0` (2026-04-09) | Shared traces, log correlation, metrics pipeline foundation | Official Python telemetry stack covering metrics, logs, and traces. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| opentelemetry-exporter-otlp-proto-http | `1.41.0` (2026-04-09) | OTLP export to collector | Use for all services to send traces/logs/metrics to one collector endpoint. |
| opentelemetry-instrumentation-fastapi | `0.62b0` (2026-04-09) | API trace instrumentation | Instrument `services/api`, `services/extractor`, and `services/classifier`. |
| opentelemetry-instrumentation-celery | `0.62b0` (2026-04-09) | Worker trace instrumentation | Instrument orchestrator task publish/consume lifecycle. |
| opentelemetry-instrumentation-sqlalchemy | `0.62b0` (2026-04-09) | DB tracing | Instrument API DB engine used for status, results, dashboard, and webhook metadata writes. |
| opentelemetry-instrumentation-httpx | `0.62b0` (2026-04-09) | Outbound webhook request tracing | Add trace context to delivery attempts and dependency latency. |
| prometheus-client | `0.25.0` (2026-04-09) | Application metrics exposition | Use for counters, gauges, and histograms exposed per service. |
| python-json-logger | `4.1.0` (2026-03-29) | Structured JSON logging | Low-friction way to standardize logs across services without building a custom formatter. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI + Jinja2 internal dashboard | Separate React/Vite SPA | Better UI freedom, but adds a second runtime, package manager workflow, build artifact, and auth boundary. Not justified for this phase. |
| Celery task retry/backoff | Custom retry scheduler table processed by cron | More explicit state control, but unnecessary complexity for bounded webhook retries in v1. |
| Prometheus client metrics + OpenTelemetry traces/logs | OpenTelemetry-only metrics exporter | Possible, but the project docs and system design already assume Prometheus-style alertable aggregates. |
| API-integrated operator surface | Separate dashboard service | Stronger isolation later, but duplicates auth/config/deployment before there is stable operator product scope. |

**Installation:**
```bash
python3 -m pip install \
  httpx==0.28.1 \
  Jinja2==3.1.6 \
  opentelemetry-sdk==1.41.0 \
  opentelemetry-exporter-otlp-proto-http==1.41.0 \
  opentelemetry-instrumentation-fastapi==0.62b0 \
  opentelemetry-instrumentation-celery==0.62b0 \
  opentelemetry-instrumentation-sqlalchemy==0.62b0 \
  opentelemetry-instrumentation-httpx==0.62b0 \
  prometheus-client==0.25.0 \
  python-json-logger==4.1.0
```

**Version verification:** Use `python3 -m pip index versions <package>` or verify against PyPI release pages before tightening repo pins. Existing repo constraints for FastAPI and Celery do not require a Phase 5 framework upgrade by themselves.

## Architecture Patterns

### Recommended Project Structure
```text
services/api/src/api_service/
├── dashboard/            # internal operator routes, queries, templates, assets
├── webhook/              # endpoint config, payload assembly, signing helpers
├── observability/        # telemetry bootstrap, metric registry, log helpers
├── repositories/         # DB reads/writes for webhook and dashboard metadata
└── db/                   # model + migration extensions

services/orchestrator/src/orchestrator_service/
├── webhook_tasks.py      # webhook dispatch task(s) on document.webhook
└── observability.py      # worker telemetry bootstrap and task context helpers
```

### Pattern 1: Durable Webhook Outbox
**What:** Persist tenant-level webhook endpoint config and per-job delivery records in the API database, enqueue dispatch only after the job is durably `completed` or `failed`, and let the webhook worker read the durable row to deliver and retry.
**When to use:** For all terminal job notifications; never deliver directly from the request path or from an in-memory callback.
**Example:**
```python
# Source: Celery docs + existing repo queue topology
@celery_app.task(
    name="document.webhook.deliver",
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def deliver_webhook(*, delivery_id: str) -> None:
    ...
```

### Pattern 2: Rich Payload Plus Canonical Reference
**What:** Send a terminal webhook payload that includes `job_id`, `document_id`, `tenant_id` or `client_id`, final `status`, stage/failure summary, model/version summary, and a durable `results_url`. For completed jobs, inline only a concise classification/extraction summary, not the full canonical artifact payload.
**When to use:** All client-facing terminal callbacks in this phase.
**Example:**
```json
{
  "event_id": "whdel_123",
  "event_type": "document.job.completed",
  "job_id": "job-123",
  "document_id": "doc-123",
  "status": "completed",
  "completed_at": "2026-04-22T10:00:00Z",
  "result_summary": {
    "final_label": "invoice",
    "confidence": 0.91,
    "model_version": "0.1.0"
  },
  "results_url": "/v1/jobs/job-123/results"
}
```

### Pattern 3: API-Integrated Internal Dashboard
**What:** Build the operator dashboard inside `services/api` with server-rendered templates and focused read models for list/detail screens, queue health, webhook history, and diagnostics.
**When to use:** Internal operations-only UI in v1.
**Example:**
```python
# Source: FastAPI templating docs
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
```

### Pattern 4: Shared Telemetry Bootstrap
**What:** Add one reusable observability bootstrap module that initializes resource attributes, OTLP exporter configuration, JSON logging format, and per-service metric registration. Import it from API startup and worker startup instead of repeating setup code everywhere.
**When to use:** All deployable services in this repo.
**Example:**
```python
# Source: OpenTelemetry Python docs + contrib instrumentation docs
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)
```

### Anti-Patterns to Avoid
- **Synchronous webhook delivery from upload/status/results paths:** Violates locked async delivery behavior and couples client latency to third-party endpoints.
- **Using the webhook body as the source of truth:** The results endpoint remains canonical; webhook payloads are convenience notifications plus stable references.
- **Metric labels with `job_id`, `document_id`, webhook URL, or tenant ID:** Prometheus explicitly warns against high-cardinality labels; use traces/logs/dashboard filters instead.
- **A parallel dashboard state store:** The dashboard should read API-owned durable metadata rather than duplicate job state in Redis or template-specific tables.
- **Reusing client API-key auth for operators without a separate boundary:** Internal operator routes need a separate auth strategy or network restriction; do not expose them with external client credentials by default.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Webhook retry scheduler | Custom backoff scheduler or cron retry loop | Celery task retry/backoff/jitter with durable delivery rows | Celery already owns async delivery and supports bounded retries. |
| Trace propagation | Ad hoc trace ID headers and manual span timing everywhere | OpenTelemetry SDK + official instrumentations | Official libraries already handle FastAPI, Celery, SQLAlchemy, and outbound HTTP. |
| Metrics format | Custom `/metrics` text serializer | `prometheus-client` | Avoids exposition bugs and keeps metrics queryable by standard tooling. |
| Dashboard rendering stack | Separate SPA build system for internal-only ops UI | FastAPI + Jinja2 templates | Lower operational overhead for a backend-first repo with no frontend pipeline today. |
| Queue health inference | Guessing queue backlog from DB stage counts alone | RabbitMQ queue metrics plus DB-backed job counts | DB state and broker backlog answer different questions; operators need both. |

**Key insight:** The hard parts here are durability, correlation, and operability. Reuse the existing DB ownership and worker topology instead of adding bespoke systems.

## Common Pitfalls

### Pitfall 1: Webhooks Triggered Before Durable Terminal State
**What goes wrong:** Clients receive a callback before the final result row/artifacts or failure metadata are fully persisted.
**Why it happens:** Delivery is coupled to workflow execution rather than to persisted terminal state.
**How to avoid:** Create delivery rows only after terminal status and final artifacts/failure fields are committed.
**Warning signs:** Webhook points to `/results` but results API still returns `409`.

### Pitfall 2: Duplicate or Untraceable Deliveries
**What goes wrong:** Retries produce duplicate business side effects, or operators cannot tell which attempts happened.
**Why it happens:** No durable delivery ID, no attempt history, and no idempotency semantics in the payload.
**How to avoid:** Add stable webhook delivery IDs, persist every attempt, and document at-least-once semantics.
**Warning signs:** Client reports duplicates and the dashboard cannot distinguish retries from first delivery.

### Pitfall 3: Metrics Cardinality Explosion
**What goes wrong:** Metrics become expensive or unusable because labels contain unbounded IDs or URLs.
**Why it happens:** Treating metrics like searchable logs.
**How to avoid:** Keep labels bounded to stage, status, worker/service, and endpoint class. Put identifiers in traces/logs only.
**Warning signs:** Metrics include `job_id`, `document_id`, `tenant_id`, or raw webhook host/path labels.

### Pitfall 4: Dashboard Built Before Read Models Are Stable
**What goes wrong:** UI work churns because job history, delivery status, and failure semantics keep changing underneath it.
**Why it happens:** The dashboard is designed before webhook tables, queue health queries, and diagnostic fields are defined.
**How to avoid:** Plan schema/read-model work first, then build views on top of those stable contracts.
**Warning signs:** Dashboard code starts parsing low-level ORM objects directly or duplicating business logic from services.

### Pitfall 5: Operator Diagnosis Still Requires DB Inspection
**What goes wrong:** The dashboard only shows top-level failure strings, so operators still have to inspect rows manually.
**Why it happens:** No drill-down into stage history, delivery attempts, artifact references, model versions, and correlated logs/traces.
**How to avoid:** The job detail view must surface stage events, terminal failure data, model metadata, trace/log correlation IDs, and webhook history.
**Warning signs:** A failed job detail page cannot answer "where did it fail?" or "was the callback delivered?".

## Code Examples

Verified patterns from official sources:

### FastAPI Templating
```python
# Source: https://fastapi.tiangolo.com/reference/templating/
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
```

### FastAPI Trace Instrumentation
```python
# Source: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

### SQLAlchemy Trace Instrumentation
```python
# Source: https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/sqlalchemy/sqlalchemy.html
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

SQLAlchemyInstrumentor().instrument(engine=engine)
```

### HMAC Webhook Signature Pattern
```python
# Source pattern: https://docs.stripe.com/webhooks
signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling-only integrations | Polling plus terminal webhooks | Already locked in roadmap/context | Clients get lower-latency completion signals without losing a canonical results API. |
| Logs-only operational debugging | Metrics + traces + structured logs split | Locked from Phase 1 onward | Keeps aggregates alertable and detailed diagnostics queryable without high-cardinality metrics. |
| Separate SPA by default for dashboards | SSR/internal app is often the pragmatic first ops surface in backend-first repos | Inference from current repo shape | Lowers integration cost and keeps auth/config simpler for v1. |

**Deprecated/outdated:**
- Using raw identifiers as Prometheus labels: current Prometheus guidance treats this as a cardinality hazard.
- Treating webhook success/failure as invisible worker behavior: Phase 5 requires explicit operator visibility and durable attempt history.

## Open Questions

1. **What is the operator authentication boundary?**
   - What we know: External client APIs use static API keys; the dashboard is internal-only.
   - What's unclear: Whether Phase 5 should add separate operator auth now or rely on network restriction plus a simple internal credential.
   - Recommendation: Plan one explicit operator protection mechanism up front. Do not expose dashboard routes behind client API keys.

2. **Where should queue health come from in the dashboard?**
   - What we know: Job counts come from Postgres; queue depth is a broker concern.
   - What's unclear: Whether the dashboard will read RabbitMQ management metrics directly, scrape Prometheus, or expose an API-level aggregation endpoint.
   - Recommendation: Plan a thin queue-health read path sourced from broker metrics, not inferred from DB counts alone.

3. **Should webhook configuration secrets be stored encrypted or hashed?**
   - What we know: Delivery requires access to a secret for signing, so a one-way hash is insufficient.
   - What's unclear: Whether the repo will use KMS-backed encryption later or an application-level encrypted column now.
   - Recommendation: Plan for encrypted-at-rest storage of webhook secrets and a future rotation flow, even if full rotation UX is deferred.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | service/runtime/tests | ✓ | 3.13.11 | — |
| GNU Make | bootstrap/test shortcuts | ✓ | 4.3 | Run underlying commands directly |
| pytest | validation | ✓ | 9.0.2 | `python3 -m pytest` |
| npm | only needed if planner chooses a JS dashboard stack | ✓ | 11.6.2 | Avoid by using Jinja2 dashboard |
| Docker | local multi-service stack | ✗ | — | none in current repo |
| Docker Compose plugin | local multi-service stack | ✗ | — | none in current repo |
| psql | direct local DB probing | ✗ | — | SQLAlchemy tests / app queries |
| rabbitmqctl | direct broker CLI inspection | ✗ | — | RabbitMQ management API if broker is running elsewhere |

**Missing dependencies with no fallback:**
- Docker and Docker Compose are currently absent, so the documented local stack in `README.md` cannot be run on this machine as-is.

**Missing dependencies with fallback:**
- `psql` and `rabbitmqctl` are absent, but planning work can still rely on ORM tests and broker/API metrics rather than local CLI inspection.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` |
| Config file | none — commands are Makefile-driven |
| Quick run command | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_status_api.py services/api/tests/test_results_api.py -q` |
| Full suite command | `make test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DLV-04 | Signed terminal-state webhooks retry with bounded failure behavior | unit + integration | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src:services/api/src pytest services/orchestrator/tests/test_webhook_tasks.py services/api/tests/test_webhook_delivery.py -q` | ❌ Wave 0 |
| DLV-05 | Webhook payload includes IDs, terminal status, and results reference | unit | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_webhook_contract.py -q` | ❌ Wave 0 |
| OPS-03 | Dashboard shows counts and stage progression | unit + route | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_operator_dashboard.py -q` | ❌ Wave 0 |
| OPS-04 | Dashboard exposes failure reasons, latency signals, and model versions | unit + route | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_operator_dashboard.py -q` | ❌ Wave 0 |
| OPS-05 | Metrics, logs, and traces cover API/workers/services/webhooks | unit + smoke | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src:services/orchestrator/src pytest services/api/tests/test_observability.py services/orchestrator/tests/test_observability.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** targeted phase-specific pytest command for the touched area
- **Per wave merge:** `make test` plus phase-specific webhook/dashboard/observability tests
- **Phase gate:** Full suite green plus one documented manual smoke of webhook delivery and dashboard drill-down

### Wave 0 Gaps
- [ ] `services/api/tests/test_webhook_contract.py` — payload shape, signature headers, completed vs failed event body
- [ ] `services/api/tests/test_webhook_delivery.py` — delivery row lifecycle, bounded retry metadata, final failure state
- [ ] `services/orchestrator/tests/test_webhook_tasks.py` — Celery retry/backoff behavior and HTTPX failure handling
- [ ] `services/api/tests/test_operator_dashboard.py` — list/detail reads, counts, stage progression, webhook visibility
- [ ] `services/api/tests/test_observability.py` — metrics endpoint/registry, trace bootstrap, log formatter wiring
- [ ] `services/orchestrator/tests/test_observability.py` — worker telemetry bootstrap and outbound webhook span hooks

## Sources

### Primary (HIGH confidence)
- FastAPI templating docs — https://fastapi.tiangolo.com/reference/templating/ — verified built-in `Jinja2Templates` support.
- OpenTelemetry Python docs — https://opentelemetry.io/docs/languages/python/ — verified Python telemetry scope covers metrics, logs, and traces.
- OpenTelemetry Python instrumentation docs — https://opentelemetry.io/docs/languages/python/instrumentation/ — verified logging guidance and manual instrumentation model.
- OpenTelemetry FastAPI instrumentation docs — https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html — verified `FastAPIInstrumentor.instrument_app(app)`.
- OpenTelemetry SQLAlchemy instrumentation docs — https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/sqlalchemy/sqlalchemy.html — verified engine instrumentation pattern and sqlcommenter warning.
- Prometheus instrumentation practices — https://prometheus.io/docs/practices/instrumentation/ — verified cardinality guidance.
- Prometheus metric/label naming practices — https://prometheus.io/docs/practices/naming/ — verified warning against high-cardinality labels.
- Stripe webhook docs — https://docs.stripe.com/webhooks — verified timestamped HMAC-over-raw-payload pattern and replay window guidance.
- PyPI project pages for release verification:
  - https://pypi.org/project/celery/
  - https://pypi.org/project/fastapi/
  - https://pypi.org/project/httpx/
  - https://pypi.org/project/Jinja2/
  - https://pypi.org/project/opentelemetry-sdk/
  - https://pypi.org/project/opentelemetry-exporter-otlp/
  - https://pypi.org/project/opentelemetry-instrumentation-fastapi/
  - https://pypi.org/project/opentelemetry-instrumentation-celery/
  - https://pypi.org/project/opentelemetry-instrumentation-sqlalchemy/
  - https://pypi.org/project/prometheus-client/
  - https://pypi.org/project/python-json-logger/

### Secondary (MEDIUM confidence)
- Celery task retry docs/search result — https://docs.celeryq.dev/en/v5.4.0/userguide/tasks.html — verified autoretry/backoff/jitter options exist; version-specific wording may differ slightly from 5.6.x.

### Tertiary (LOW confidence)
- None. The main recommendations are grounded in repo inspection plus official documentation. The only inference-heavy recommendation is keeping the dashboard server-rendered inside FastAPI; that is based on current repo shape, not on a locked product requirement.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions and APIs were verified against official docs/PyPI; only the SSR dashboard recommendation is an architectural inference.
- Architecture: MEDIUM - durable webhook outbox and API-integrated dashboard fit the current repo strongly, but operator auth and exact queue-health source still need planning decisions.
- Pitfalls: HIGH - directly supported by repo constraints, Prometheus guidance, and the current async architecture.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22
