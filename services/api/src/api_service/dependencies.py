"""Reusable FastAPI dependencies."""

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from api_service.auth import AuthenticatedClient, authenticate_api_key
from api_service.config import APISettings, get_settings
from api_service.db.session import build_session_factory
from api_service.errors import APIError
from api_service.storage import StorageAdapter
from orchestrator_service.celery_app import enqueue_preprocess_job


def get_settings_dependency() -> APISettings:
    return get_settings()


def get_db_session(
    settings: APISettings = Depends(get_settings_dependency),
) -> Generator[Session, None, None]:
    session_factory = build_session_factory(settings.postgres_dsn)
    with session_factory() as session:
        yield session


def get_storage_dependency(
    settings: APISettings = Depends(get_settings_dependency),
) -> StorageAdapter:
    return StorageAdapter(settings)


def get_enqueue_upload_dependency() -> callable:
    return enqueue_preprocess_job


def get_authenticated_client(
    request: Request,
    settings: APISettings = Depends(get_settings_dependency),
    session: Session = Depends(get_db_session),
) -> AuthenticatedClient:
    api_key = request.headers.get(settings.api_key_header_name)
    return authenticate_api_key(api_key=api_key, settings=settings, session=session)


def get_internal_service_token(
    request: Request,
    settings: APISettings = Depends(get_settings_dependency),
) -> str:
    authorization = request.headers.get("Authorization")
    expected = f"Bearer {settings.internal_service_token}"
    if authorization != expected:
        raise APIError(
            status_code=401,
            error_code="unauthorized",
            message="Invalid internal service token.",
        )
    return settings.internal_service_token


def get_authenticated_operator(
    request: Request,
    settings: APISettings = Depends(get_settings_dependency),
) -> str:
    authorization = request.headers.get("Authorization")
    expected = f"Bearer {settings.operator_bearer_token}"
    if not settings.operator_dashboard_enabled or authorization != expected:
        raise APIError(
            status_code=401,
            error_code="unauthorized",
            message="Invalid operator token.",
        )
    return settings.operator_bearer_token
