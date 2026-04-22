# Hybrid Extraction Pipeline

Phase 3 turns the extractor and orchestrator services into a normalized extraction pipeline.

## Stage Flow

The current extraction flow uses these stage names:

- `accepted`
- `extracting`
- `extracted`

Uploads still enter the system through the Phase 2 upload contract. The orchestrator then prepares an extraction request and forwards it to the extractor service.

## Routing Rules

- `application/pdf` tries embedded text first.
- PDFs with unusable embedded text switch to OCR with `fallback_reason="embedded_text_unusable"`.
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, and `application/json` use direct parsing.
- `image/png` and `image/jpeg` are OCR-first inputs.

Stable terminal extractor failure codes for unsafe inputs:

- `corrupt_pdf`
- `encrypted_pdf`
- `invalid_image_encoding`

## Artifact Types

Phase 3 keeps the shared storage namespace and uses these artifact types during extraction:

- `page-image`
- `ocr-json`
- `extracted-text`

The normalized extractor response is posted through `POST /v1/extractions:run`.

## Local Verification

- Start the stack with `docker compose up --build`
- Upload a sample through `POST /v1/documents:upload`
- Verify extractor health at `http://localhost:8001/healthz`
- Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/orchestrator/src pytest services/orchestrator/tests/test_celery_app.py services/orchestrator/tests/test_extraction_tasks.py -q`
- Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q`
