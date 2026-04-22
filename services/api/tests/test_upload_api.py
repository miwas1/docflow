from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.auth import AuthenticatedClient
from api_service.config import APISettings
from api_service.db.base import Base
from api_service.db.models import Artifact, Job
from api_service.errors import APIError
from api_service.services.ingestion import ingest_upload
from api_service.storage import StorageAdapter


@pytest.fixture()
def api_settings() -> APISettings:
    return APISettings(
        postgres_dsn="sqlite+pysqlite:///:memory:",
        rabbitmq_url="amqp://guest:guest@localhost:5672//",
        object_storage_endpoint="http://localhost:9000",
        object_storage_bucket="doc-platform-artifacts",
        object_storage_access_key="minioadmin",
        object_storage_secret_key="minioadmin",
        api_key_header_name="X-API-Key",
        api_keys_json={"demo-client": "demo-secret-key"},
        max_upload_bytes=1024 * 1024,
        host="127.0.0.1",
        port=8000,
        log_level="INFO",
    )


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def build_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def test_unsupported_media_type_returns_documented_client_error(
    api_settings: APISettings, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        with pytest.raises(APIError) as exc_info:
            ingest_upload(
                session=session,
                storage=StorageAdapter(api_settings),
                settings=api_settings,
                client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
                upload_file=build_upload_file("notes.csv", b"a,b,c", "text/csv"),
                idempotency_key="idem-unsupported",
                enqueue_upload_job=lambda *_: None,
            )

    assert exc_info.value.status_code == 415
    assert exc_info.value.error_code == "unsupported_media_type"


def test_upload_acceptance_and_idempotent_retry_return_same_identifiers(
    api_settings: APISettings, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        first = ingest_upload(
            session=session,
            storage=StorageAdapter(api_settings),
            settings=api_settings,
            client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
            upload_file=build_upload_file("document.pdf", b"%PDF-1.4\nfake", "application/pdf"),
            idempotency_key="idem-accepted",
            enqueue_upload_job=lambda *_: None,
        )

    with session_factory() as session:
        second = ingest_upload(
            session=session,
            storage=StorageAdapter(api_settings),
            settings=api_settings,
            client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
            upload_file=build_upload_file("document.pdf", b"%PDF-1.4\nfake", "application/pdf"),
            idempotency_key="idem-accepted",
            enqueue_upload_job=lambda *_: None,
        )

    assert first.job_id == second.job_id
    assert first.document_id == second.document_id
    assert first.status == "queued"
    assert first.current_stage == "accepted"

    with session_factory() as session:
        job = session.scalar(select(Job).where(Job.id == first.job_id))
        artifact = session.scalar(select(Artifact).where(Artifact.job_id == first.job_id))

    assert job is not None
    assert artifact is not None
    assert artifact.artifact_type == "original"


def test_upload_rejects_spoofed_media_type_before_persisting_job(
    api_settings: APISettings, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        with pytest.raises(APIError) as exc_info:
            ingest_upload(
                session=session,
                storage=StorageAdapter(api_settings),
                settings=api_settings,
                client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
                upload_file=build_upload_file("document.pdf", b"\x89PNG\r\n\x1a\nfake", "application/pdf"),
                idempotency_key="idem-spoofed",
                enqueue_upload_job=lambda *_: None,
            )

        jobs = session.scalars(select(Job)).all()
        artifacts = session.scalars(select(Artifact)).all()

    assert exc_info.value.status_code == 422
    assert exc_info.value.error_code == "unsafe_input_type_mismatch"
    assert jobs == []
    assert artifacts == []


def test_upload_rejects_encrypted_pdf_before_persisting_job(
    api_settings: APISettings, session_factory: sessionmaker[Session]
) -> None:
    encrypted_pdf = b"%PDF-1.7\n1 0 obj\n<< /Encrypt 5 0 R >>\nendobj\n%%EOF"

    with session_factory() as session:
        with pytest.raises(APIError) as exc_info:
            ingest_upload(
                session=session,
                storage=StorageAdapter(api_settings),
                settings=api_settings,
                client=AuthenticatedClient(client_id="demo-client", display_name="demo-client"),
                upload_file=build_upload_file("locked.pdf", encrypted_pdf, "application/pdf"),
                idempotency_key="idem-encrypted",
                enqueue_upload_job=lambda *_: None,
            )

        jobs = session.scalars(select(Job)).all()
        artifacts = session.scalars(select(Artifact)).all()

    assert exc_info.value.status_code == 422
    assert exc_info.value.error_code == "encrypted_pdf"
    assert jobs == []
    assert artifacts == []
