# Results Contract

Phase 4 introduces one normalized final-results payload for completed document jobs.

## Results Endpoint

`GET /v1/jobs/{job_id}/results`

Results are only served after the job reaches the `classified` stage and has status `completed`.

## Classification Fields

Every classification payload uses these JSON fields:

- `job_id`
- `document_id`
- `tenant_id`
- `final_label`
- `confidence`
- `candidate_labels`
- `low_confidence_policy`
- `threshold_applied`
- `produced_by`
- `created_at`

Allowed public final labels:

- `invoice`
- `receipt`
- `bank_statement`
- `id_card`
- `utility_bill`
- `contract`
- `medical_record`
- `tax_form`
- `unknown/other`

## Low-Confidence Policy

Low-confidence documents resolve publicly to `unknown/other`.

The classifier metadata still records:

- the numeric `confidence`
- the applied threshold
- ordered `candidate_labels`
- the classifier model/version trace in `produced_by`

## Storage Contract

Completed classification outputs persist as `artifact_type="classification-result"` in the shared storage namespace.

The classification-result artifact metadata records:

- `document_id`
- `final_label`
- `confidence`
- `low_confidence_policy`
- `threshold_applied`
- `candidate_labels`

## Results API Expectations

Completed results must include:

- extracted text
- classification output
- artifact references
- model/version metadata

The final response payload uses these fields:

- `job_id`
- `document_id`
- `status`
- `extracted_text`
- `classification`
- `artifacts`
- `completed_at`

Results are only available after the extracted-text and classification-result artifacts have been durably persisted.

Phase 6 keeps delivery reliability separate from core result truth:

- completed jobs with exhausted webhook delivery attempts still return results
- retrying or dead-lettered jobs still return `results_not_ready`
- delivery exhaustion must not invalidate already persisted extracted/classification artifacts

## Postgres Lineage

The API-owned metadata schema stores classification lineage in `classification_runs` with:

- `job_id`
- `stage`
- `final_label`
- `confidence`
- `low_confidence_policy`
- `threshold_applied`
- `candidate_labels_json`
- `trace_json`
