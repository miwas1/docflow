"""Upload acceptance and idempotent ingestion flow."""

from collections.abc import Callable
import json
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api_service.auth import AuthenticatedClient
from api_service.config import APISettings
from api_service.db.models import Artifact, Job, JobEvent
from api_service.errors import APIError
from api_service.repositories.jobs import (
    create_artifact,
    create_job,
    create_job_event,
    get_job_by_idempotency_key,
)
from api_service.schemas import AcceptedUploadResponse
from api_service.storage import StorageAdapter

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/json",
}

EnqueueUploadJob = Callable[[str, str], None]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8"
PDF_SIGNATURE = b"%PDF-"


def _detect_media_type(content: bytes) -> str | None:
    if content.startswith(PDF_SIGNATURE):
        return "application/pdf"
    if content.startswith(PNG_SIGNATURE):
        return "image/png"
    if content.startswith(JPEG_SIGNATURE):
        return "image/jpeg"
    if content.startswith(b"PK"):
        try:
            with ZipFile(BytesIO(content)) as archive:
                if "word/document.xml" in archive.namelist():
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except BadZipFile:
            return None
    try:
        json.loads(content.decode("utf-8"))
        return "application/json"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        content.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return None


def _validate_upload_content(*, settings: APISettings, declared_content_type: str | None, content: bytes) -> None:
    if not settings.input_signature_validation_enabled or not declared_content_type:
        return

    detected_content_type = _detect_media_type(content)
    if detected_content_type is None:
        raise APIError(
            status_code=422,
            error_code="invalid_input_payload",
            message="Uploaded content is invalid or unreadable.",
        )

    if declared_content_type == "application/pdf" and b"/Encrypt" in content[:4096]:
        raise APIError(
            status_code=422,
            error_code="encrypted_pdf",
            message="Encrypted PDFs are not supported.",
        )

    if settings.unsafe_input_reject_mismatch and detected_content_type != declared_content_type:
        raise APIError(
            status_code=422,
            error_code="unsafe_input_type_mismatch",
            message="Uploaded content does not match the declared media type.",
            details={
                "declared_content_type": declared_content_type,
                "detected_content_type": detected_content_type,
            },
        )


def _build_duplicate_response(job: Job) -> AcceptedUploadResponse:
    return AcceptedUploadResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        current_stage=job.current_stage,
    )


def ingest_upload(
    *,
    session: Session,
    storage: StorageAdapter,
    settings: APISettings,
    client: AuthenticatedClient,
    upload_file: UploadFile,
    idempotency_key: str | None,
    enqueue_upload_job: EnqueueUploadJob,
) -> AcceptedUploadResponse:
    if not idempotency_key:
        raise APIError(
            status_code=400,
            error_code="missing_idempotency_key",
            message="Idempotency-Key header is required.",
        )

    duplicate_job = get_job_by_idempotency_key(
        session,
        client_id=client.client_id,
        idempotency_key=idempotency_key,
    )
    if duplicate_job is not None:
        return _build_duplicate_response(duplicate_job)

    if upload_file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise APIError(
            status_code=415,
            error_code="unsupported_media_type",
            message="Unsupported media type.",
            details={"content_type": upload_file.content_type},
        )

    content = upload_file.file.read()
    if not content:
        raise APIError(
            status_code=400,
            error_code="empty_file",
            message="Uploaded file is empty.",
        )
    if len(content) > settings.max_upload_bytes:
        raise APIError(
            status_code=413,
            error_code="file_too_large",
            message="Uploaded file exceeds the configured size limit.",
            details={"max_upload_bytes": settings.max_upload_bytes},
        )

    _validate_upload_content(
        settings=settings,
        declared_content_type=upload_file.content_type,
        content=content,
    )

    job_id = str(uuid4())
    document_id = str(uuid4())
    filename = upload_file.filename or f"{document_id}{Path(upload_file.filename or 'upload.bin').suffix}"
    stage = "accepted"
    storage_key = storage.build_storage_key(
        tenant_id=client.client_id,
        job_id=job_id,
        stage=stage,
        artifact_type="original",
        filename=filename,
    )
    storage.put_artifact(storage_key=storage_key, content=content)

    job = Job(
        id=job_id,
        document_id=document_id,
        tenant_id=client.client_id,
        client_id=client.client_id,
        idempotency_key=idempotency_key,
        status="queued",
        current_stage=stage,
        source_filename=filename,
        source_media_type=upload_file.content_type,
        storage_key=storage_key,
    )
    create_job(session, job)

    create_job_event(
        session,
        JobEvent(
            id=str(uuid4()),
            job_id=job_id,
            event_type="upload.accepted",
            stage=stage,
            payload_json={
                "filename": filename,
                "content_type": upload_file.content_type,
                "bytes": len(content),
            },
        ),
    )
    create_artifact(
        session,
        Artifact(
            id=str(uuid4()),
            job_id=job_id,
            artifact_type="original",
            stage=stage,
            storage_key=storage_key,
            media_type=upload_file.content_type,
            metadata_json={"filename": filename, "bytes": len(content)},
        ),
    )
    session.commit()

    enqueue_upload_job(job_id, document_id)

    return AcceptedUploadResponse(
        job_id=job_id,
        document_id=document_id,
        status="queued",
        current_stage=stage,
    )
