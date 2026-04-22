"""Canonical object-storage naming helpers."""

from typing import Literal, get_args

ArtifactType = Literal[
    "original",
    "page-image",
    "ocr-json",
    "extracted-text",
    "classification-result",
]

ARTIFACT_TYPES = get_args(ArtifactType)
STORAGE_KEY_TEMPLATE = "tenants/{tenant_id}/jobs/{job_id}/{stage}/{artifact_type}/{filename}"


def build_storage_key(
    *,
    tenant_id: str,
    job_id: str,
    stage: str,
    artifact_type: ArtifactType,
    filename: str,
) -> str:
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unsupported artifact type: {artifact_type}")

    return STORAGE_KEY_TEMPLATE.format(
        tenant_id=tenant_id,
        job_id=job_id,
        stage=stage,
        artifact_type=artifact_type,
        filename=filename,
    )
