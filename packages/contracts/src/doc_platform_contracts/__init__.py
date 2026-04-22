"""Shared contracts for the document OCR and classification platform."""

from .classification import ClassificationCandidate, ClassifierTrace, DocumentClassificationResult
from .extraction import ExtractedTextArtifact, ExtractionPage, ExtractionTrace
from .models import ApiClientRecord, ArtifactRecord, JobEventRecord, JobRecord, ModelVersionRecord
from .observability import CORRELATION_FIELDS, METRIC_DEFINITIONS, SERVICE_NAMES, SPAN_NAMES
from .settings import BasePlatformSettings
from .storage_keys import ARTIFACT_TYPES, STORAGE_KEY_TEMPLATE, build_storage_key

__all__ = [
    "ARTIFACT_TYPES",
    "ApiClientRecord",
    "ArtifactRecord",
    "BasePlatformSettings",
    "ClassificationCandidate",
    "ClassifierTrace",
    "CORRELATION_FIELDS",
    "DocumentClassificationResult",
    "ExtractedTextArtifact",
    "ExtractionPage",
    "ExtractionTrace",
    "JobEventRecord",
    "JobRecord",
    "METRIC_DEFINITIONS",
    "ModelVersionRecord",
    "SERVICE_NAMES",
    "SPAN_NAMES",
    "STORAGE_KEY_TEMPLATE",
    "build_storage_key",
]
