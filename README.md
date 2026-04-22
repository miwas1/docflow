# Document OCR and Classification Platform

An API-first backend platform for asynchronous document text extraction and document classification.

## Local Setup

### Prerequisites

- Python 3.12 or newer
- `pip`
- Docker with the `docker compose` plugin

### 1. Clone and enter the repo

```bash
git clone <your-repo-url>
cd doc_ocr_classification
```

### 2. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

The default local values are already set up for:

- Postgres on `localhost:5432`
- RabbitMQ on `localhost:5672`
- MinIO on `localhost:9000`
- API service on `localhost:8000`
- Extractor service on `localhost:8001`
- Classifier service on `localhost:8002`
- Static API key auth using `X-API-Key`
- Signature-based upload validation with mismatch rejection enabled
- Internal service auth using `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>`
- Internal operator auth using `Authorization: Bearer <OPERATOR_BEARER_TOKEN>`
- Orchestrator-to-extractor base URL on `http://localhost:8001`
- Bounded stage retries plus three-window webhook retry backoff

You can keep `.env.example` as-is for the default local stack, or override values in `.env`.

### 3. Install Python dependencies

```bash
make bootstrap
```

This installs the editable packages for:

- `packages/contracts`
- `services/api`
- `services/orchestrator`
- `services/extractor`
- `services/classifier`

### 4. Run the test suite

Run the full Phase 1 and Phase 2 Python checks:

```bash
make test
```

If you only want the API suite:

```bash
make test-api
```

If you want the Phase 3 extraction-focused checks:

```bash
make test-orchestrator
make test-extractor
```

If you want the Phase 4 classification/results checks:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_classification_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_results_contract.py services/api/tests/test_results_api.py services/api/tests/test_status_api.py -q
```

If you want the Phase 5 webhook, observability, and operator checks:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src:services/orchestrator/src:services/extractor/src:services/classifier/src pytest services/api/tests/test_webhook_contract.py services/api/tests/test_webhook_dispatch_api.py services/api/tests/test_observability.py services/api/tests/test_operator_dashboard.py services/orchestrator/tests/test_webhook_tasks.py services/orchestrator/tests/test_observability.py -q
```

If you want the Phase 6 reliability and input-safety checks:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_upload_api.py services/api/tests/test_status_api.py services/api/tests/test_results_api.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_extraction_tasks.py services/orchestrator/tests/test_classification_tasks.py services/orchestrator/tests/test_webhook_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_operator_dashboard.py services/api/tests/test_webhook_dispatch_api.py -q
```

### 5. Start the local infrastructure and services

```bash
docker compose up --build
```

This starts:

- Postgres
- RabbitMQ
- MinIO
- API
- Orchestrator
- Extractor
- Classifier

### 6. Verify the stack

Check container status:

```bash
docker compose ps
```

Health endpoints:

- API: `http://localhost:8000/healthz`
- Extractor: `http://localhost:8001/healthz`
- Classifier: `http://localhost:8002/healthz`

Useful infrastructure UIs:

- MinIO console: `http://localhost:9001`
- RabbitMQ management: `http://localhost:15672`

Internal operator surface:

- Dashboard HTML: `http://localhost:8000/internal/operator/dashboard`
- Jobs JSON: `http://localhost:8000/internal/operator/jobs`

### 7. Try the upload contract

Phase 2 adds a protected multipart upload endpoint and stage-based polling contract.

Example upload request:

```bash
curl -X POST http://localhost:8000/v1/documents:upload \
  -H "X-API-Key: demo-secret-key" \
  -H "Idempotency-Key: local-readme-demo-1" \
  -F "file=@sample.pdf;type=application/pdf"
```

If accepted, the response includes `job_id`, `document_id`, `status`, and `current_stage`.

### 8. Verify the Phase 3 extraction pipeline

Check the extractor endpoint directly:

```bash
curl -X POST http://localhost:8001/v1/extractions:run \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job-local-1","document_id":"doc-local-1","tenant_id":"demo-client","source_media_type":"text/plain","source_filename":"sample.txt","source_artifact_id":"artifact-local-1","inline_content_base64":"SGVsbG8gZnJvbSBQaGFzZSAz"}'
```

Run the targeted extraction verification suites:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_extraction_contract.py services/api/tests/test_status_api.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_celery_app.py services/orchestrator/tests/test_extraction_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q
```

### 9. Verify the Phase 4 classification and results pipeline

Confirm the classifier endpoint directly:

```bash
curl -X POST http://localhost:8002/v1/classifications:run \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job-local-2","document_id":"doc-local-2","tenant_id":"demo-client","source_media_type":"application/pdf","text":"Invoice Number INV-42\nTotal Due: $120.00","source_artifact_ids":["artifact-local-2"]}'
```

After a job reaches the `classified` stage, fetch the final result payload:

```bash
curl -H "X-API-Key: demo-secret-key" \
  http://localhost:8000/v1/jobs/<job_id>/results
```

Run the targeted classification/results verification suites:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_classification_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_results_contract.py services/api/tests/test_results_api.py services/api/tests/test_status_api.py -q
```

### 10. Verify the Phase 5 webhook, observability, and operator surfaces

Set the internal bearer tokens in `.env` if you changed them from `.env.example`:

- `INTERNAL_SERVICE_TOKEN`
- `OPERATOR_BEARER_TOKEN`

Useful routes:

- `GET /internal/webhooks/jobs/{job_id}/dispatch`
- `POST /internal/webhooks/jobs/{job_id}/deliveries/{delivery_id}`
- `GET /internal/operator/jobs`
- `GET /internal/operator/jobs/{job_id}`
- `GET /internal/operator/dashboard`

Run the targeted Phase 5 verification suite:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src:services/orchestrator/src:services/extractor/src:services/classifier/src pytest services/api/tests/test_webhook_contract.py services/api/tests/test_webhook_dispatch_api.py services/api/tests/test_observability.py services/api/tests/test_operator_dashboard.py services/orchestrator/tests/test_webhook_tasks.py services/orchestrator/tests/test_observability.py -q
```

### 11. Verify the Phase 6 reliability and input-safety behavior

Phase 6 adds conservative validation and bounded failure handling:

- uploads are validated against the real file signature, not only the declared media type
- encrypted PDFs, corrupt PDFs, and invalid image encodings fail with stable terminal codes
- webhook delivery retries across three later windows: 30 seconds, 120 seconds, and 600 seconds
- exhausted retries surface as poison/dead-letter state for operators without invalidating already completed results

Run the targeted reliability suites:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_upload_api.py services/api/tests/test_status_api.py services/api/tests/test_results_api.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_extraction_tasks.py services/orchestrator/tests/test_classification_tasks.py services/orchestrator/tests/test_webhook_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_operator_dashboard.py services/api/tests/test_webhook_dispatch_api.py -q
```

Useful checks while the stack is running:

- submit a spoofed upload and confirm `unsafe_input_type_mismatch`
- submit an encrypted PDF and confirm `encrypted_pdf`
- verify `/internal/operator/jobs/{job_id}` shows `retry_count`, `dead_letter_reason`, and `terminal_failure_category`
- confirm a completed job still returns `/v1/jobs/<job_id>/results` even if webhook delivery later exhausts retries

## Repository Layout

- `services/api` contains the HTTP-facing API service, persistence ownership, and storage adapter stubs.
- `services/orchestrator` contains the Celery control-plane scaffold backed by RabbitMQ queues.
- `services/extractor` contains the OCR/extraction service boundary with its own health surface.
- `services/classifier` contains the classification service boundary with its own health surface.
- `packages/contracts` contains shared settings, storage-key helpers, and domain contracts reused across services.
- `infra/terraform` contains the cloud baseline for managed AWS and GCP foundation resources.
- `docs/foundation` contains the storage and local development contracts for operators and future phases.

## Phase 1 Scope

Phase 1 establishes the platform skeleton:

- separate service workspaces
- environment-driven configuration
- a Postgres metadata schema foundation
- an object-storage namespace contract
- a RabbitMQ/Celery orchestration scaffold
- Docker Compose for local runtime
- Terraform baselines for AWS and GCP

Business workflows such as upload processing, OCR fan-out, and classification execution are intentionally deferred to later phases.

## Phase 2 Contracts

- [External ingestion API](docs/foundation/external-ingestion-api.md)
- [Status polling contract](docs/foundation/status-polling-contract.md)
- [Local development notes](docs/foundation/local-development.md)

## Phase 3 Contracts

- [Extraction contract](docs/foundation/extraction-contract.md)
- [Hybrid extraction pipeline](docs/foundation/hybrid-extraction-pipeline.md)

## Phase 4 Contracts

- [Results contract](docs/foundation/results-contract.md)

## Phase 5 Contracts

- [Webhook contract](docs/foundation/webhook-contract.md)
- [Observability contract](docs/foundation/observability.md)
- [Operator dashboard](docs/foundation/operator-dashboard.md)
