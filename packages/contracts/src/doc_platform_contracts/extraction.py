"""Normalized extraction payload contracts shared across services."""

from datetime import datetime

from pydantic import BaseModel


class ExtractionPage(BaseModel):
    page_number: int
    text: str
    source_artifact_id: str


class ExtractionTrace(BaseModel):
    provider: str
    model: str
    version: str


class ExtractedTextArtifact(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    source_media_type: str
    extraction_path: str
    fallback_used: bool
    fallback_reason: str | None = None
    page_count: int
    pages: list[ExtractionPage]
    text: str
    source_artifact_ids: list[str]
    produced_by: ExtractionTrace
    created_at: datetime
