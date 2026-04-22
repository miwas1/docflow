PYTHONPATH_COMMON=packages/contracts/src

.PHONY: bootstrap test test-api test-orchestrator test-extractor test-classifier

bootstrap:
	python3 -m pip install -e packages/contracts -e services/api -e services/orchestrator -e services/extractor -e services/classifier

test: test-api test-orchestrator test-extractor test-classifier

test-api:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=$(PYTHONPATH_COMMON):services/api/src pytest services/api/tests/test_health.py services/api/tests/test_foundation_schema.py services/api/tests/test_storage_keys.py services/api/tests/test_ingestion_schema.py services/api/tests/test_auth_api_keys.py services/api/tests/test_upload_api.py services/api/tests/test_status_api.py services/api/tests/test_extraction_contract.py -q

test-orchestrator:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=$(PYTHONPATH_COMMON):services/orchestrator/src pytest services/orchestrator/tests/test_celery_app.py services/orchestrator/tests/test_extraction_tasks.py -q

test-extractor:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=$(PYTHONPATH_COMMON):services/extractor/src pytest services/extractor/tests/test_health.py services/extractor/tests/test_extraction_service.py -q

test-classifier:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=$(PYTHONPATH_COMMON):services/classifier/src pytest services/classifier/tests/test_health.py -q
