"""Baseline document classification helpers."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

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


class TextEmbedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""


def _normalize_embedding(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return [0.0 for _ in vector]
    return [value / magnitude for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding vectors must have equal dimensions.")
    normalized_left = _normalize_embedding(left)
    normalized_right = _normalize_embedding(right)
    return max(0.0, sum(a * b for a, b in zip(normalized_left, normalized_right, strict=True)))


class ModernBertTextEmbedder:
    def __init__(self, settings: ClassifierSettings) -> None:
        try:
            import torch
            from transformers import AutoModel
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "ModernBERT runtime dependencies are not installed. "
                "Install classifier extras before starting the service."
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            settings.classifier_model_name,
            cache_dir=settings.classifier_model_cache_dir,
            local_files_only=settings.classifier_model_local_files_only,
        )
        self._model = AutoModel.from_pretrained(
            settings.classifier_model_name,
            cache_dir=settings.classifier_model_cache_dir,
            local_files_only=settings.classifier_model_local_files_only,
        )
        self._model.eval()
        self._device = settings.classifier_device
        self._model.to(self._device)
        self._max_length = settings.classifier_max_length

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with self._torch.no_grad():
            outputs = self._model(**encoded)

        attention_mask = encoded["attention_mask"].unsqueeze(-1)
        masked_hidden_state = outputs.last_hidden_state * attention_mask
        pooled = masked_hidden_state.sum(dim=1) / attention_mask.sum(dim=1).clamp(min=1)
        normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)
        return normalized.cpu().tolist()


class SimilarityClassifierRuntime:
    def __init__(self, settings: ClassifierSettings, embedder: TextEmbedder | None = None) -> None:
        self.settings = settings
        self.embedder = embedder or ModernBertTextEmbedder(settings)
        self._labels = [
            (label, description)
            for label, description in settings.classifier_label_descriptions.items()
            if label != "unknown_other"
        ]
        if not self._labels:
            raise ValueError("At least one supported taxonomy label must be configured.")
        label_descriptions = [description for _, description in self._labels]
        self._prototype_embeddings = self.embedder.embed_texts(label_descriptions)

    def classify(self, text: str) -> list[ClassificationCandidate]:
        query_embedding = self.embedder.embed_texts([text])[0]
        candidates = [
            ClassificationCandidate(
                label=label,
                score=_cosine_similarity(query_embedding, prototype_embedding),
            )
            for (label, _), prototype_embedding in zip(
                self._labels,
                self._prototype_embeddings,
                strict=True,
            )
        ]
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates


@lru_cache(maxsize=1)
def get_runtime() -> SimilarityClassifierRuntime:
    return SimilarityClassifierRuntime(get_settings())


def warm_runtime() -> SimilarityClassifierRuntime:
    return get_runtime()


def run_classification(
    request: ClassificationRequest | dict,
    settings: ClassifierSettings | None = None,
    runtime: SimilarityClassifierRuntime | None = None,
) -> DocumentClassificationResult:
    parsed_request = request if isinstance(request, ClassificationRequest) else ClassificationRequest.model_validate(request)
    settings = settings or get_settings()
    runtime = runtime or (get_runtime() if settings is get_settings() else SimilarityClassifierRuntime(settings))

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
