"""Reusable FastAPI dependencies."""

import hashlib
from collections.abc import Generator
from datetime import datetime, timezone

from api_service.auth import AuthenticatedClient, authenticate_api_key
from api_service.config import APISettings, get_settings
from api_service.db.models import User, UserSession
from api_service.db.session import build_session_factory
from api_service.errors import APIError
from api_service.storage import StorageAdapter
from fastapi import Cookie, Depends, Request
from fastapi.responses import RedirectResponse
from orchestrator_service.celery_app import enqueue_preprocess_job
from sqlalchemy.orm import Session


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


def _hash_token(token: str) -> str:
    """Return SHA-256 hex digest of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_optional_current_user(
    session_id: str | None = Cookie(default=None),
    settings: APISettings = Depends(get_settings_dependency),
    db: Session = Depends(get_db_session),
) -> User | None:
    """Return the authenticated User for a valid session cookie, or None."""
    if not session_id:
        return None
    token_hash = _hash_token(session_id)
    now = datetime.now(timezone.utc)
    user_session: UserSession | None = (
        db.query(UserSession)
        .filter(
            UserSession.session_token_hash == token_hash,
            UserSession.expires_at > now,
        )
        .first()
    )
    if user_session is None:
        return None
    user_session.last_used_at = now
    db.commit()
    return (
        db.query(User)
        .filter(User.id == user_session.user_id, User.is_active.is_(True))
        .first()
    )


def require_current_user(
    user: User | None = Depends(get_optional_current_user),
) -> User:
    """Redirect to login if session is missing or expired."""
    if user is None:
        raise _LoginRedirect()
    return user


class _LoginRedirect(Exception):
    """Sentinel used to redirect unauthenticated dashboard requests."""
