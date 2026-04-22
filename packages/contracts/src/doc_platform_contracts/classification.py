"""Normalized classification payload contracts shared across services."""

from datetime import datetime

from pydantic import BaseModel


class ClassificationCandidate(BaseModel):
    label: str
    score: float


class ClassifierTrace(BaseModel):
    provider: str
    model: str
    version: str


class DocumentClassificationResult(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    final_label: str
    confidence: float
    candidate_labels: list[ClassificationCandidate]
    low_confidence_policy: str
    threshold_applied: float
    produced_by: ClassifierTrace
    created_at: datetime
