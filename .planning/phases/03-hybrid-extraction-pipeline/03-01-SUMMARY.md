# Plan 03-01 Summary

## Completed

- Added a shared normalized extraction contract in `packages/contracts/src/doc_platform_contracts/extraction.py`.
- Exported the new extraction contract types from `doc_platform_contracts`.
- Extended the API metadata schema with `extraction_runs` plus repository helpers for extraction lineage and extracted-text artifacts.
- Added the `0003_extraction_contract.py` migration metadata and documented the extraction contract in `docs/foundation/extraction-contract.md`.

## Verification

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest services/api/tests/test_extraction_contract.py services/api/tests/test_foundation_schema.py -q`
- `rg -n "ExtractionPage|ExtractionTrace|ExtractedTextArtifact" packages/contracts/src/doc_platform_contracts/extraction.py packages/contracts/src/doc_platform_contracts/__init__.py`
- `rg -n "__tablename__ = \"extraction_runs\"|extraction_path|fallback_used|page_count" services/api/src/api_service/db/models.py services/api/alembic/versions/0003_extraction_contract.py`
- `rg -n "artifact_type=\"extracted-text\"|source_artifact_ids|fallback_used" docs/foundation/extraction-contract.md`
