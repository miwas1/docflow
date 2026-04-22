"""Shared domain records for early platform contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class JobRecord:
    id: str
    document_id: str
    tenant_id: str
    client_id: str | None
    idempotency_key: str | None
    status: str
    current_stage: str
    source_filename: str
    source_media_type: str
    storage_key: str
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class JobEventRecord:
    id: str
    job_id: str
    event_type: str
    stage: str
    payload_json: dict
    created_at: datetime


@dataclass(slots=True)
class ArtifactRecord:
    id: str
    job_id: str
    artifact_type: str
    stage: str
    storage_key: str
    media_type: str
    metadata_json: dict
    created_at: datetime


@dataclass(slots=True)
class ModelVersionRecord:
    id: str
    model_family: str
    version: str
    routing_policy: str
    rollout_bucket: str
    created_at: datetime


@dataclass(slots=True)
class ApiClientRecord:
    id: str
    client_id: str
    display_name: str
    api_key_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
