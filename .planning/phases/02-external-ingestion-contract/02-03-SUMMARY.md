# Plan 02-03 Summary

## Completed

- Added the stage-based polling service and `GET /v1/jobs/{job_id}` endpoint.
- Extended the API schemas with the stable polling response shape.
- Documented the polling contract in `docs/foundation/status-polling-contract.md`.
- Updated the README to link the Phase 2 client contract docs.

## Verification

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest services/api/tests/test_status_api.py -q`
- `rg -n "@app.get\\(\"/v1/jobs/\\{job_id\\}\"\\)|current_stage|accepted_at|failure" services/api/src/api_service/main.py services/api/src/api_service/services/status.py services/api/src/api_service/schemas.py`
- `rg -n "GET /v1/jobs/\\{job_id\\}|failure.code|failure.message|status-polling-contract" docs/foundation/status-polling-contract.md README.md`
