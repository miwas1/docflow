from __future__ import annotations

from classifier_service.config import ClassifierSettings
from classifier_service.inference import (
    ClassificationRequest,
    SequenceClassifierRuntime,
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


def build_settings() -> ClassifierSettings:
    return ClassifierSettings(
        POSTGRES_DSN="postgresql+psycopg://doc_platform:doc_platform@localhost:5432/doc_platform",
        RABBITMQ_URL="amqp://doc_platform:doc_platform@localhost:5672/doc_platform",
        OBJECT_STORAGE_ENDPOINT="http://localhost:9000",
        OBJECT_STORAGE_BUCKET="doc-platform-artifacts",
        OBJECT_STORAGE_ACCESS_KEY="minioadmin",
        OBJECT_STORAGE_SECRET_KEY="minioadmin",
        CLASSIFIER_MODEL_NAME="/models/huggingface/finetuned/doc-ocr-modernbert/model",
        CLASSIFIER_MODEL_VERSION="modernbert-finetuned-v1",
        CLASSIFIER_CONFIDENCE_THRESHOLD=0.6,
    )


class FakeTensor:
    def __init__(self, data):
        self._data = data

    def to(self, _device: str) -> "FakeTensor":
        return self

    def cpu(self) -> "FakeTensor":
        return self

    def __getitem__(self, index):
        return FakeTensor(self._data[index])

    def tolist(self):
        return self._data


class FakeTokenizer:
    def __call__(self, texts, **_kwargs):
        return {"input_texts": FakeTensor(list(texts))}


class FakeModelOutput:
    def __init__(self, logits):
        self.logits = FakeTensor(logits)


class FakeModel:
    class Config:
        id2label = {0: "invoice", 1: "receipt", 2: "unknown_other"}

    def __init__(self) -> None:
        self.config = self.Config()

    def eval(self) -> None:
        return None

    def to(self, _device: str) -> "FakeModel":
        return self

    def __call__(self, **encoded):
        logits = []
        for text in encoded["input_texts"].tolist():
            normalized = text.lower()
            if "invoice" in normalized or "bill to" in normalized or "total due" in normalized:
                logits.append([8.0, 1.0, -1.0])
            elif "receipt" in normalized or "cashier" in normalized:
                logits.append([0.5, 7.5, -2.0])
            else:
                logits.append([0.2, 0.3, 0.4])
        return FakeModelOutput(logits)


class FakeTorchModule:
    class no_grad:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class nn:
        class functional:
            @staticmethod
            def softmax(fake_tensor: FakeTensor, dim: int):
                rows = fake_tensor.tolist()
                probabilities = []
                for row in rows:
                    total = sum(pow(2.718281828459045, value) for value in row)
                    probabilities.append([pow(2.718281828459045, value) / total for value in row])
                return FakeTensor(probabilities)


def build_runtime() -> SequenceClassifierRuntime:
    return SequenceClassifierRuntime(
        settings=build_settings(),
        torch_module=FakeTorchModule(),
        tokenizer=FakeTokenizer(),
        model=FakeModel(),
    )


def test_run_classification_returns_supported_taxonomy_label_for_invoice_like_text() -> None:
    runtime = build_runtime()
    result = run_classification(
        build_request("Invoice Number INV-42\nTotal Due: $120.00\nBill To: Acme Corp"),
        settings=build_settings(),
        runtime=runtime,
    )

    assert result.final_label == "invoice"
    assert result.confidence > 0.6
    assert result.candidate_labels[0].label == "invoice"


def test_run_classification_maps_low_confidence_documents_to_unknown_other() -> None:
    runtime = build_runtime()
    result = run_classification(
        build_request("This memo contains general discussion notes with no stable document-type keywords."),
        settings=build_settings(),
        runtime=runtime,
    )

    assert result.final_label == "unknown_other"
    assert result.low_confidence_policy == "threshold_to_unknown_other"
    assert result.threshold_applied > 0


def test_run_classification_uses_settings_trace_metadata_for_finetuned_runtime() -> None:
    settings = build_settings()
    runtime = build_runtime()

    result = run_classification(
        build_request("Receipt for purchase\nCashier: Jane Doe"),
        settings=settings,
        runtime=runtime,
    )

    assert result.produced_by.model == "/models/huggingface/finetuned/doc-ocr-modernbert/model"
    assert result.produced_by.version == "modernbert-finetuned-v1"


def test_classification_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/classifications:run")

    assert route.methods == {"POST"}
