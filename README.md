# Document OCR and Classification Platform

An API-first backend platform for asynchronous document text extraction and document classification.

## Local Setup

### Prerequisites

- Python 3.13 or newer
- `pip`
- Docker with the `docker compose` plugin (Docker Engine 25+)

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

### 3. Pre-download the classifier model cache

The classifier now expects a local Hugging Face cache with the configured ModernBERT model before the container starts. On Linux or EC2, run the one-time bootstrap script:

```bash
./scripts/bootstrap_ec2_dev.sh --skip-docker-install
```

The script:

- keeps your existing `.env` if present, or creates one from `.env.example`
- creates the host cache directory from `CLASSIFIER_MODEL_CACHE_HOST_PATH`
- downloads `CLASSIFIER_MODEL_NAME` into that cache

On EC2 you can omit `--skip-docker-install` and let the script install Docker too.

### 4. Install Python dependencies

```bash
make bootstrap
```

This installs the editable packages for:

- `packages/contracts`
- `services/api`
- `services/orchestrator`
- `services/extractor`
- `services/classifier`

### 5. Run the test suite

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
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py services/classifier/tests/test_bootstrap_config.py -q
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

### 6. Start the local infrastructure and services

```bash
docker compose up --build
```

This builds and starts:

| Service | Description |
|---|---|
| `postgres` | PostgreSQL 17 — primary datastore |
| `rabbitmq` | RabbitMQ 3.13 — task broker |
| `minio` | MinIO — local object storage (S3-compatible) |
| `api` | FastAPI — external-facing HTTP API (port 8000) |
| `orchestrator` | Celery worker — pipeline control plane |
| `extractor` | FastAPI — text extraction service (port 8001) |
| `classifier` | FastAPI — document classification service (port 8002) |
| `dozzle` | Real-time Docker log viewer — accessible at `/dozzle` via nginx |
| `nginx` | Reverse proxy — public entry point on port 80 |

On first run the API container automatically runs `alembic upgrade head` before starting uvicorn.

The classifier container mounts `${CLASSIFIER_MODEL_CACHE_HOST_PATH}` into `${CLASSIFIER_MODEL_CACHE_DIR}` and reads ModernBERT from the local cache instead of downloading it on startup.

### 7. Verify the stack

Check container status:

```bash
docker compose ps
```

Health endpoints (local):

- API: `http://localhost:8000/healthz`
- Extractor: `http://localhost:8001/healthz`
- Classifier: `http://localhost:8002/healthz`
- nginx (proxies API): `http://localhost/healthz`

Admin UIs:

| UI | URL | Notes |
|---|---|---|
| MinIO console | `http://localhost:9001` | credentials: `minioadmin / minioadmin` |
| RabbitMQ management | `http://localhost:15672` | default guest login |
| Dozzle log viewer | `http://localhost/dozzle` | real-time container logs |

Internal operator surface:

- Dashboard HTML: `http://localhost:8000/internal/operator/dashboard`
- Jobs JSON: `http://localhost:8000/internal/operator/jobs`

---

## User Dashboard

The platform includes a self-service web dashboard for external API clients to manage their credentials and monitor jobs.

### Access

| Page | URL |
|---|---|
| Landing page | `http://localhost:8000/` |
| Sign up | `http://localhost:8000/dashboard/signup` |
| Log in | `http://localhost:8000/dashboard/login` |
| Home (stats) | `http://localhost:8000/dashboard/home` |
| API Keys | `http://localhost:8000/dashboard/api-keys` |
| Webhooks | `http://localhost:8000/dashboard/webhooks` |
| Job History | `http://localhost:8000/dashboard/jobs` |

### What you can do

| Feature | Details |
|---|---|
| **Sign up / Log in** | Email + password; bcrypt-hashed passwords; 30-day HttpOnly session cookie |
| **API Keys** | Generate named keys (`dp_…`); plaintext shown once at creation; revoke at any time |
| **Webhooks** | Add webhook subscriptions per API key; each gets a `whsec_…` HMAC-SHA256 signing secret |
| **Job History** | Browse all jobs submitted via your API keys; filter by status; drill into stage timeline, classification result, and artifacts |

### Session configuration

Two environment variables control session behaviour (set in `.env` for local dev, or via docker-compose `environment:` for containers):

| Variable | Default | Notes |
|---|---|---|
| `SESSION_SECRET_KEY` | `dev-session-secret-change-me` | **Change this in production.** Used as a salt for session token hashing. |
| `SESSION_EXPIRE_SECONDS` | `2592000` (30 days) | How long a login session stays valid. |

### Security notes

- Session tokens are stored as SHA-256 hashes in the `user_sessions` table — the plaintext token only exists in the browser cookie.
- API key plaintexts are never persisted; only the SHA-256 hash is stored in `api_clients`.
- Session cookies are `HttpOnly` and `SameSite=Lax`. Set `secure=True` in `routers/dashboard/auth.py` when deploying behind HTTPS.
- Passwords are hashed with bcrypt at 12 rounds.

---

## EC2 Development Setup

The stack is designed to run on an EC2 instance with nginx as the public entry point on port 80.

### Recommended instance sizes

- `t3.xlarge` — lowest-cost dev box that can work for a single developer
- `t3.2xlarge` — better burstable dev option if you run the full stack often
- `m7i.2xlarge` — smoother default if you want more headroom and fewer CPU-credit surprises

### EC2 security group rules (recommended)

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 80 | TCP | 0.0.0.0/0 | nginx → API + Dozzle |
| 22 | TCP | Your IP | SSH |
| 15672 | TCP | Your IP | RabbitMQ management UI |
| 9001 | TCP | Your IP | MinIO console |

Do **not** expose ports 8000, 8001, or 8002 publicly — all external API traffic should go through port 80.

### First-time EC2 setup

```bash
git clone <your-repo-url>
cd doc_ocr_classification

# One-time bootstrap: installs Docker if needed, creates .env, and pre-downloads ModernBERT
./scripts/bootstrap_ec2_dev.sh --user ec2-user

# If this is the first time your user was added to the docker group:
newgrp docker

# Start the stack with current repo code
docker compose up --build -d
```

The bootstrap script seeds the model cache into `CLASSIFIER_MODEL_CACHE_HOST_PATH` so later `docker compose up --build` runs reuse the downloaded weights while still rebuilding your latest code.

### Accessing services on EC2

Replace `<EC2_PUBLIC_IP>` with your instance public IP or DNS name.

| Surface | URL |
|---|---|
| API | `http://<EC2_PUBLIC_IP>/v1/...` |
| Dozzle | `http://<EC2_PUBLIC_IP>/dozzle` |
| MinIO console | `http://<EC2_PUBLIC_IP>:9001` |
| RabbitMQ management | `http://<EC2_PUBLIC_IP>:15672` |

### Rebuilding after code changes

```bash
docker compose up --build -d
```

To rebuild only one service:

```bash
docker compose up --build -d api
```

### 8. Try the upload contract

Phase 2 adds a protected multipart upload endpoint and stage-based polling contract.

Example upload request:

```bash
curl -X POST http://localhost:8000/v1/documents:upload \
  -H "X-API-Key: demo-secret-key" \
  -H "Idempotency-Key: local-readme-demo-1" \
  -F "file=@sample.pdf;type=application/pdf"
```

If accepted, the response includes `job_id`, `document_id`, `status`, and `current_stage`.

### 9. Verify the Phase 3 extraction pipeline

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

### 10. Verify the Phase 4 classification and results pipeline

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
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py services/classifier/tests/test_bootstrap_config.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_classification_tasks.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_results_contract.py services/api/tests/test_results_api.py services/api/tests/test_status_api.py -q
```

### 11. Verify the Phase 5 webhook, observability, and operator surfaces

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

### 12. Verify the Phase 6 reliability and input-safety behavior

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

### 13. Synchronous fast-path for digital documents

For `text/plain`, `application/json`, `application/pdf` (digital), and `application/vnd.openxmlformats-officedocument.wordprocessingml.document` uploads the API attempts inline extraction + classification within a configurable deadline before the HTTP response is returned. If both stages complete in time the upload response will contain `status: "completed"` and the full classification result immediately. If either stage exceeds the deadline or fails, the job is transparently handed off to the Celery async queue and the response will contain `status: "queued"` instead.

The following environment variables control the fast-path behaviour:

| Variable | Default | Description |
|---|---|---|
| `SYNC_CLASSIFICATION_ENABLED` | `true` | Enable/disable the sync fast-path. Set to `false` to always use the async queue. |
| `SYNC_CLASSIFICATION_TIMEOUT_SECONDS` | `20` | Total wall-clock deadline (seconds) shared between extractor and classifier calls. |
| `EXTRACTOR_BASE_URL` | `http://localhost:8001` | Base URL the API uses to reach the extractor service. In Docker Compose this must be `http://extractor:8001`. |
| `CLASSIFIER_BASE_URL` | `http://localhost:8002` | Base URL the API uses to reach the classifier service. In Docker Compose this must be `http://classifier:8002`. |

These are already pre-configured in `docker-compose.yml` for local development. When deploying to EC2 or another environment, ensure the API container can resolve the extractor and classifier hostnames.

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
