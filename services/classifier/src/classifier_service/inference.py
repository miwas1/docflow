"""Fine-tuned document classification helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from pydantic import BaseModel

from doc_platform_contracts.classification import (
    ClassificationCandidate,
    ClassifierTrace,
    DocumentClassificationResult,
)

from classifier_service.config import ClassifierSettings, get_settings


class ClassificationRequest(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    source_media_type: str
    text: str
    source_artifact_ids: list[str]


class ClassificationError(Exception):
    def __init__(self, *, error_code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def _softmax(scores: list[float]) -> list[float]:
    # Lightweight fallback for tests; production uses torch.softmax.
    import math

    if not scores:
        return []
    max_score = max(scores)
    exps = [math.exp(score - max_score) for score in scores]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


class SequenceClassifierRuntime:
    def __init__(
        self,
        settings: ClassifierSettings,
        *,
        torch_module=None,
        tokenizer=None,
        model=None,
    ) -> None:
        self.settings = settings

        if torch_module is None or tokenizer is None or model is None:
            try:
                import torch
                from transformers import AutoModelForSequenceClassification
                from transformers import AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "Fine-tuned classifier runtime dependencies are not installed. "
                    "Install classifier extras before starting the service."
                ) from exc

            torch_module = torch
            tokenizer = AutoTokenizer.from_pretrained(
                settings.classifier_model_name,
                cache_dir=settings.classifier_model_cache_dir,
                local_files_only=settings.classifier_model_local_files_only,
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                settings.classifier_model_name,
                cache_dir=settings.classifier_model_cache_dir,
                local_files_only=settings.classifier_model_local_files_only,
            )

        self._torch = torch_module
        self._tokenizer = tokenizer
        self._model = model
        self._model.eval()
        self._device = settings.classifier_device
        self._model.to(self._device)
        self._max_length = settings.classifier_max_length
        self._id2label = self._load_id2label()

    def _load_id2label(self) -> dict[int, str]:
        mapping = getattr(self._model.config, "id2label", None)
        if isinstance(mapping, dict) and mapping:
            return {int(key): value for key, value in mapping.items()}
        raise ValueError(
            "The configured classifier model does not expose id2label metadata. "
            "Point CLASSIFIER_MODEL_NAME at a fine-tuned sequence-classification model directory."
        )

    def classify(self, text: str) -> list[ClassificationCandidate]:
        encoded = self._tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with self._torch.no_grad():
            outputs = self._model(**encoded)

        probabilities = self._probabilities_from_logits(outputs.logits)
        candidates = [
            ClassificationCandidate(label=self._id2label[index], score=score)
            for index, score in enumerate(probabilities)
        ]
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates

    def _probabilities_from_logits(self, logits) -> list[float]:
        if hasattr(self._torch, "nn") and hasattr(self._torch.nn, "functional"):
            probs = self._torch.nn.functional.softmax(logits, dim=-1)
            return probs[0].cpu().tolist()
        return _softmax(logits[0])


@lru_cache(maxsize=1)
def get_runtime() -> SequenceClassifierRuntime:
    return SequenceClassifierRuntime(get_settings())


def warm_runtime() -> SequenceClassifierRuntime:
    return get_runtime()


def run_classification(
    request: ClassificationRequest | dict,
    settings: ClassifierSettings | None = None,
    runtime: SequenceClassifierRuntime | None = None,
) -> DocumentClassificationResult:
    parsed_request = request if isinstance(request, ClassificationRequest) else ClassificationRequest.model_validate(request)
    settings = settings or get_settings()
    runtime = runtime or (get_runtime() if settings is get_settings() else SequenceClassifierRuntime(settings))

    matched_candidates = runtime.classify(parsed_request.text)
    if not matched_candidates:
        matched_candidates = [ClassificationCandidate(label="unknown_other", score=0.0)]

    best_candidate = matched_candidates[0]
    final_label = best_candidate.label
    if best_candidate.score < settings.classifier_confidence_threshold:
        final_label = "unknown_other"

    return DocumentClassificationResult(
        job_id=parsed_request.job_id,
        document_id=parsed_request.document_id,
        tenant_id=parsed_request.tenant_id,
        final_label=final_label,
        confidence=best_candidate.score,
        candidate_labels=matched_candidates,
        low_confidence_policy="threshold_to_unknown_other",
        threshold_applied=settings.classifier_confidence_threshold,
        produced_by=ClassifierTrace(
            provider=settings.classifier_model_provider,
            model=settings.classifier_model_name,
            version=settings.classifier_model_version,
        ),
        created_at=datetime.now(UTC),
    )
