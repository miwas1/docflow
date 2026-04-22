# Extraction Contract

Phase 3 introduces one normalized extracted-text payload for both digital parsing and OCR outputs.

## Normalized Fields

Every extracted payload uses these JSON fields:

- `job_id`
- `document_id`
- `tenant_id`
- `source_media_type`
- `extraction_path`
- `fallback_used`
- `fallback_reason`
- `page_count`
- `pages`
- `text`
- `source_artifact_ids`
- `produced_by`
- `created_at`

Allowed `extraction_path` values:

- `direct`
- `ocr`

## Storage Contract

Both direct and OCR paths persist the final normalized payload as `artifact_type="extracted-text"` in the shared storage namespace.

The extracted-text artifact metadata records:

- `extraction_path`
- `fallback_used`
- `fallback_reason`
- `page_count`
- `source_artifact_ids`

## Postgres Lineage

The API-owned metadata schema stores extraction lineage in `extraction_runs` with:

- `job_id`
- `stage`
- `extraction_path`
- `fallback_used`
- `fallback_reason`
- `page_count`
- `source_artifact_ids_json`
- `trace_json`
