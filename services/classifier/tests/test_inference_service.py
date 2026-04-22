from classifier_service.config import ClassifierSettings
from classifier_service.inference import (
    ClassificationRequest,
    SimilarityClassifierRuntime,
    run_classification,
)
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


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            if "invoice" in normalized or "bill to" in normalized or "total due" in normalized:
                embeddings.append([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            elif "receipt" in normalized or "cashier" in normalized:
                embeddings.append([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            elif "bank statement" in normalized or "account summaries" in normalized:
                embeddings.append([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            elif "identification card" in normalized or "date of birth" in normalized:
                embeddings.append([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
            elif "utility bill" in normalized or "service charges" in normalized:
                embeddings.append([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
            elif "contract" in normalized or "agreement" in normalized:
                embeddings.append([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0])
            elif "medical record" in normalized or "patient" in normalized:
                embeddings.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])
            elif "tax form" in normalized or "withholding" in normalized:
                embeddings.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
            else:
                embeddings.append([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
        return embeddings


def build_settings() -> ClassifierSettings:
    return ClassifierSettings(
        POSTGRES_DSN="postgresql+psycopg://doc_platform:doc_platform@localhost:5432/doc_platform",
        RABBITMQ_URL="amqp://doc_platform:doc_platform@localhost:5672/doc_platform",
        OBJECT_STORAGE_ENDPOINT="http://localhost:9000",
        OBJECT_STORAGE_BUCKET="doc-platform-artifacts",
        OBJECT_STORAGE_ACCESS_KEY="minioadmin",
        OBJECT_STORAGE_SECRET_KEY="minioadmin",
        CLASSIFIER_MODEL_NAME="answerdotai/ModernBERT-base",
        CLASSIFIER_MODEL_VERSION="dev-modernbert",
        CLASSIFIER_CONFIDENCE_THRESHOLD=0.6,
        CLASSIFIER_LABEL_DESCRIPTIONS_JSON={
            "invoice": "Invoice document with bill to and total due amounts.",
            "receipt": "Receipt document from a cashier after payment.",
            "unknown_other": "Unknown or other document type.",
        },
    )


def test_run_classification_returns_supported_taxonomy_label_for_invoice_like_text() -> None:
    runtime = SimilarityClassifierRuntime(settings=build_settings(), embedder=FakeEmbedder())
    result = run_classification(
        build_request(
            "Invoice Number INV-42\nTotal Due: $120.00\nBill To: Acme Corp",
        ),
        settings=build_settings(),
        runtime=runtime,
    )

    assert result.final_label == "invoice"
    assert result.confidence > 0.6
    assert result.candidate_labels[0].label == "invoice"


def test_run_classification_maps_low_confidence_documents_to_unknown_other() -> None:
    runtime = SimilarityClassifierRuntime(settings=build_settings(), embedder=FakeEmbedder())
    result = run_classification(
        build_request(
            "This memo contains general discussion notes with no stable document-type keywords.",
        ),
        settings=build_settings(),
        runtime=runtime,
    )

    assert result.final_label == "unknown_other"
    assert result.low_confidence_policy == "threshold_to_unknown_other"
    assert result.threshold_applied > 0


def test_run_classification_uses_settings_trace_metadata_for_modernbert_runtime() -> None:
    settings = build_settings()
    runtime = SimilarityClassifierRuntime(settings=settings, embedder=FakeEmbedder())

    result = run_classification(
        build_request("Receipt for purchase\nCashier: Jane Doe"),
        settings=settings,
        runtime=runtime,
    )

    assert result.produced_by.model == "answerdotai/ModernBERT-base"
    assert result.produced_by.version == "dev-modernbert"


def test_classification_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/classifications:run")

    assert route.methods == {"POST"}
