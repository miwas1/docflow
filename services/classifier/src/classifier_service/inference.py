"""Baseline document classification helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

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


class KeywordRule(BaseModel):
    label: str
    keywords: tuple[str, ...]
    score: float


RULES: ClassVar[tuple[KeywordRule, ...]] = (
    KeywordRule(label="invoice", keywords=("invoice", "bill to", "total due"), score=0.92),
    KeywordRule(label="receipt", keywords=("receipt", "change due", "cashier"), score=0.86),
    KeywordRule(label="bank_statement", keywords=("account summary", "statement period", "ending balance"), score=0.9),
    KeywordRule(label="id_card", keywords=("date of birth", "identification", "card number"), score=0.88),
    KeywordRule(label="utility_bill", keywords=("service address", "meter", "utility"), score=0.87),
    KeywordRule(label="contract", keywords=("agreement", "party", "terms and conditions"), score=0.84),
    KeywordRule(label="medical_record", keywords=("patient", "diagnosis", "treatment"), score=0.89),
    KeywordRule(label="tax_form", keywords=("tax", "withholding", "social security"), score=0.91),
)


def run_classification(
    request: ClassificationRequest | dict,
    settings: ClassifierSettings | None = None,
) -> DocumentClassificationResult:
    parsed_request = request if isinstance(request, ClassificationRequest) else ClassificationRequest.model_validate(request)
    settings = settings or get_settings()

    normalized_text = parsed_request.text.lower()
    matched_candidates = [
        ClassificationCandidate(label=rule.label, score=rule.score)
        for rule in RULES
        if any(keyword in normalized_text for keyword in rule.keywords)
    ]

    if not matched_candidates:
        matched_candidates = [ClassificationCandidate(label="unknown_other", score=0.2)]

    matched_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
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
            provider="classifier-service",
            model=settings.classifier_model_name,
            version=settings.classifier_model_version,
        ),
        created_at=datetime.now(UTC),
    )
