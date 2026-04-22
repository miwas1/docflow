from doc_platform_contracts.storage_keys import ARTIFACT_TYPES, STORAGE_KEY_TEMPLATE, build_storage_key


def test_storage_key_template_matches_documented_namespace() -> None:
    assert STORAGE_KEY_TEMPLATE == "tenants/{tenant_id}/jobs/{job_id}/{stage}/{artifact_type}/{filename}"


def test_storage_key_generation_uses_exact_phase_one_contract() -> None:
    key = build_storage_key(
        tenant_id="tenant-123",
        job_id="job-456",
        stage="extract",
        artifact_type="ocr-json",
        filename="page-001.json",
    )

    assert key == "tenants/tenant-123/jobs/job-456/extract/ocr-json/page-001.json"
    assert ARTIFACT_TYPES == (
        "original",
        "page-image",
        "ocr-json",
        "extracted-text",
        "classification-result",
    )
