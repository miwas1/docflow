import base64
from unittest.mock import Mock

import pytest

from doc_platform_contracts.extraction import ExtractedTextArtifact, ExtractionPage, ExtractionTrace
from orchestrator_service.extractor_client import ExtractorClient, ExtractorClientError
from orchestrator_service.tasks import build_extraction_request, dispatch_extraction_task, run_extraction


def build_payload() -> ExtractedTextArtifact:
    return ExtractedTextArtifact(
        job_id="job-123",
        document_id="doc-123",
        tenant_id="tenant-123",
        source_media_type="image/png",
        extraction_path="ocr",
        fallback_used=False,
        fallback_reason=None,
        page_count=1,
        pages=[ExtractionPage(page_number=1, text="ocr text", source_artifact_id="artifact-source-1")],
        text="ocr text",
        source_artifact_ids=["artifact-source-1"],
        produced_by=ExtractionTrace(provider="extractor-service", model="heuristic-router", version="0.1.0"),
        created_at="2026-04-21T00:00:00Z",
    )


def test_build_extraction_request_preserves_scanned_input_metadata() -> None:
    request = build_extraction_request(
        job_id="job-123",
        document_id="doc-123",
        tenant_id="tenant-123",
        source_media_type="image/png",
        source_filename="scan.png",
        source_artifact_id="artifact-source-1",
        content=b"binary-image",
    )

    assert request["job_id"] == "job-123"
    assert request["source_media_type"] == "image/png"
    assert request["source_artifact_id"] == "artifact-source-1"
    assert request["inline_content_base64"] == base64.b64encode(b"binary-image").decode()


def test_dispatch_extraction_task_calls_extractor_client() -> None:
    extractor_client = Mock(spec=ExtractorClient)
    extractor_client.run_extraction_request.return_value = build_payload()

    result = dispatch_extraction_task(
        extractor_client=extractor_client,
        job_id="job-123",
        document_id="doc-123",
        tenant_id="tenant-123",
        source_media_type="image/png",
        source_filename="scan.png",
        source_artifact_id="artifact-source-1",
        content=b"binary-image",
    )

    extractor_client.run_extraction_request.assert_called_once()
    assert result.extraction_path == "ocr"
    assert result.page_count == 1


def test_dispatch_extraction_task_surfaces_client_failures() -> None:
    extractor_client = Mock(spec=ExtractorClient)
    extractor_client.run_extraction_request.side_effect = ExtractorClientError("timeout")

    with pytest.raises(ExtractorClientError):
        dispatch_extraction_task(
            extractor_client=extractor_client,
            job_id="job-123",
            document_id="doc-123",
            tenant_id="tenant-123",
            source_media_type="application/pdf",
            source_filename="scan.pdf",
            source_artifact_id="artifact-source-1",
            content=b"%PDF-1.4",
        )


def test_run_extraction_reraises_terminal_unsafe_input_errors(monkeypatch) -> None:
    extractor_client = Mock(spec=ExtractorClient)
    extractor_client.run_extraction_request.side_effect = ExtractorClientError("422 corrupt_pdf")
    monkeypatch.setattr("orchestrator_service.tasks.build_default_extractor_client", lambda: extractor_client)

    with pytest.raises(ExtractorClientError):
        run_extraction(payload={"job_id": "job-123"})


def test_run_extraction_retries_transient_failures_with_backoff(monkeypatch) -> None:
    extractor_client = Mock(spec=ExtractorClient)
    extractor_client.run_extraction_request.side_effect = ExtractorClientError("503 upstream unavailable")
    monkeypatch.setattr("orchestrator_service.tasks.build_default_extractor_client", lambda: extractor_client)
    monkeypatch.setattr(
        "orchestrator_service.tasks.get_settings",
        lambda: Mock(extract_max_attempts=3, extract_retry_backoff_seconds=[30, 120]),
    )
    enqueue_retry = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.enqueue_extract_job", enqueue_retry)

    result = run_extraction(payload={"job_id": "job-123"}, attempt=1)

    assert result["status"] == "retrying"
    enqueue_retry.assert_called_once_with({"job_id": "job-123"}, attempt=2, countdown=30)
