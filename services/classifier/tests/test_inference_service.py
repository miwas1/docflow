from classifier_service.inference import ClassificationRequest, run_classification
from classifier_service.main import app


def build_request(text: str) -> ClassificationRequest:
    return ClassificationRequest(
        job_id="job-789",
        document_id="doc-789",
        tenant_id="tenant-789",
        source_media_type="application/pdf",
        text=text,
        source_artifact_ids=["artifact-extracted-1"],
    )


def test_run_classification_returns_supported_taxonomy_label_for_invoice_like_text() -> None:
    result = run_classification(
        build_request(
            "Invoice Number INV-42\nTotal Due: $120.00\nBill To: Acme Corp",
        )
    )

    assert result.final_label == "invoice"
    assert result.confidence > 0.6
    assert result.candidate_labels[0].label == "invoice"


def test_run_classification_maps_low_confidence_documents_to_unknown_other() -> None:
    result = run_classification(
        build_request(
            "This memo contains general discussion notes with no stable document-type keywords.",
        )
    )

    assert result.final_label == "unknown_other"
    assert result.low_confidence_policy == "threshold_to_unknown_other"
    assert result.threshold_applied > 0


def test_classification_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/classifications:run")

    assert route.methods == {"POST"}
