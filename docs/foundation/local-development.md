# Local Development

Phase 3 ships a local runtime foundation for Postgres, RabbitMQ, MinIO, and the four Python services, plus the normalized extraction pipeline between the API, orchestrator, and extractor.

## Commands

- `docker compose up --build`
- `docker compose ps`
- `make test-api`
- `make test-orchestrator`
- `make test-extractor`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_results_contract.py services/api/tests/test_results_api.py services/api/tests/test_status_api.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src:services/orchestrator/src:services/extractor/src:services/classifier/src pytest services/api/tests/test_webhook_contract.py services/api/tests/test_webhook_dispatch_api.py services/api/tests/test_observability.py services/api/tests/test_operator_dashboard.py services/orchestrator/tests/test_webhook_tasks.py services/orchestrator/tests/test_observability.py -q`

## Health Verification

After the stack is running, verify the HTTP-facing services:

- `http://localhost:8000/healthz`
- `http://localhost:8001/healthz`
- `http://localhost:8002/healthz`

Infrastructure endpoints:

- MinIO console: `http://localhost:9001`
- RabbitMQ management: `http://localhost:15672`

## Extraction Verification

After the stack is running:

- Submit a sample with `POST /v1/documents:upload`
- Confirm the extractor service responds on `http://localhost:8001/healthz`
- Use `EXTRACTOR_BASE_URL=http://localhost:8001` for local non-Docker runs
- Docker Compose overrides the orchestrator container to use `http://extractor:8001`

Targeted verification commands:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_extraction_contract.py services/api/tests/test_status_api.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_celery_app.py services/orchestrator/tests/test_extraction_tasks.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q`

## Classification and Results Verification

After the stack is running:

- Confirm the classifier service responds on `http://localhost:8002/healthz`
- Run the classifier verification suite
- Run the API results verification suite
- Submit a sample with `POST /v1/documents:upload`
- Poll `GET /v1/jobs/{job_id}` until the job reaches `classified`
- Fetch `GET /v1/jobs/{job_id}/results` for the final payload

Targeted verification commands:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_classification_tasks.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_results_contract.py services/api/tests/test_results_api.py services/api/tests/test_status_api.py -q`

## Webhook, Observability, and Operator Verification

After the stack is running:

- Set `INTERNAL_SERVICE_TOKEN` and `OPERATOR_BEARER_TOKEN` in `.env`.
- Confirm webhook contract docs in `docs/foundation/webhook-contract.md`.
- Confirm observability contract docs in `docs/foundation/observability.md`.
- Visit `/internal/operator/dashboard` with `Authorization: Bearer <OPERATOR_BEARER_TOKEN>`.
- Query `/internal/operator/jobs` and `/internal/operator/jobs/{job_id}` with the same bearer token.
- Verify failed jobs show failure diagnostics and webhook delivery history.

Targeted verification command:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src:services/orchestrator/src:services/extractor/src:services/classifier/src pytest services/api/tests/test_webhook_contract.py services/api/tests/test_webhook_dispatch_api.py services/api/tests/test_observability.py services/api/tests/test_operator_dashboard.py services/orchestrator/tests/test_webhook_tasks.py services/orchestrator/tests/test_observability.py -q`

## Phase 6 Reliability and Input-Safety Verification

After the stack is running:

- Submit a spoofed upload, such as a PNG payload declared as `application/pdf`, and verify the API returns `unsafe_input_type_mismatch`.
- Submit an encrypted PDF fixture and verify the API returns `encrypted_pdf` before any async work is enqueued.
- Force webhook callback failures and confirm retry windows occur at three separate later intervals: 30 seconds, 120 seconds, and 600 seconds.
- Inspect operator job detail for `retry_count`, `dead_letter_reason`, and `terminal_failure_category` when retries exhaust.
- Confirm completed jobs still return `/v1/jobs/{job_id}/results` even when webhook delivery later exhausts retries.

Targeted verification commands:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_upload_api.py services/api/tests/test_status_api.py services/api/tests/test_results_api.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_extraction_tasks.py services/orchestrator/tests/test_classification_tasks.py services/orchestrator/tests/test_webhook_tasks.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/api/src pytest services/api/tests/test_operator_dashboard.py services/api/tests/test_webhook_dispatch_api.py -q`
