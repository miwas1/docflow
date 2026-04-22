from unittest.mock import Mock

import pytest

from doc_platform_contracts.classification import (
    ClassificationCandidate,
    ClassifierTrace,
    DocumentClassificationResult,
)
from orchestrator_service.classifier_client import ClassifierClient, ClassifierClientError
from orchestrator_service.tasks import build_classification_request, dispatch_classification_task, run_classification


def build_payload() -> DocumentClassificationResult:
    return DocumentClassificationResult(
        job_id="job-789",
        document_id="doc-789",
        tenant_id="tenant-789",
        final_label="invoice",
        confidence=0.91,
        candidate_labels=[
            ClassificationCandidate(label="invoice", score=0.91),
            ClassificationCandidate(label="receipt", score=0.34),
        ],
        low_confidence_policy="threshold_to_unknown_other",
        threshold_applied=0.6,
        produced_by=ClassifierTrace(provider="classifier-service", model="baseline-keyword", version="0.1.0"),
        created_at="2026-04-22T00:00:00Z",
    )


def test_build_classification_request_preserves_extracted_text_metadata() -> None:
    request = build_classification_request(
        job_id="job-789",
        document_id="doc-789",
        tenant_id="tenant-789",
        source_media_type="application/pdf",
        text="Invoice Number INV-42",
        source_artifact_ids=["artifact-extracted-1"],
    )

    assert request["job_id"] == "job-789"
    assert request["text"] == "Invoice Number INV-42"
    assert request["source_artifact_ids"] == ["artifact-extracted-1"]


def test_dispatch_classification_task_calls_classifier_client() -> None:
    classifier_client = Mock(spec=ClassifierClient)
    classifier_client.run_classification_request.return_value = build_payload()

    result = dispatch_classification_task(
        classifier_client=classifier_client,
        job_id="job-789",
        document_id="doc-789",
        tenant_id="tenant-789",
        source_media_type="application/pdf",
        text="Invoice Number INV-42",
        source_artifact_ids=["artifact-extracted-1"],
    )

    classifier_client.run_classification_request.assert_called_once()
    assert result.final_label == "invoice"
    assert result.confidence == 0.91


def test_dispatch_classification_task_surfaces_client_failures() -> None:
    classifier_client = Mock(spec=ClassifierClient)
    classifier_client.run_classification_request.side_effect = ClassifierClientError("timeout")

    with pytest.raises(ClassifierClientError):
        dispatch_classification_task(
            classifier_client=classifier_client,
            job_id="job-789",
            document_id="doc-789",
            tenant_id="tenant-789",
            source_media_type="application/pdf",
            text="Invoice Number INV-42",
            source_artifact_ids=["artifact-extracted-1"],
        )


def test_run_classification_surfaces_transient_failures_for_retry_handling(monkeypatch) -> None:
    classifier_client = Mock(spec=ClassifierClient)
    classifier_client.run_classification_request.side_effect = ClassifierClientError("422 invalid_request")
    monkeypatch.setattr("orchestrator_service.tasks.build_default_classifier_client", lambda: classifier_client)

    with pytest.raises(ClassifierClientError):
        run_classification(payload={"job_id": "job-789"})


def test_run_classification_retries_transient_failures_with_backoff(monkeypatch) -> None:
    classifier_client = Mock(spec=ClassifierClient)
    classifier_client.run_classification_request.side_effect = ClassifierClientError("timeout")
    monkeypatch.setattr("orchestrator_service.tasks.build_default_classifier_client", lambda: classifier_client)
    monkeypatch.setattr(
        "orchestrator_service.tasks.get_settings",
        lambda: Mock(classify_max_attempts=3, classify_retry_backoff_seconds=[30, 120]),
    )
    enqueue_retry = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.enqueue_classify_job", enqueue_retry)

    result = run_classification(payload={"job_id": "job-789"}, attempt=1)

    assert result["status"] == "retrying"
    enqueue_retry.assert_called_once_with({"job_id": "job-789"}, attempt=2, countdown=30)
