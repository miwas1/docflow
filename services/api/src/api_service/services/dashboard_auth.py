"""Service layer: dashboard user signup, login, and logout."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from api_service.config import APISettings
from api_service.db.models import User
from api_service.repositories.sessions import (
    create_session,
    delete_session_by_token_hash,
)
from api_service.repositories.users import create_user, get_user_by_email
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _hash_token(token: str) -> str:
    """Return SHA-256 hex digest of a raw session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def signup_user(
    session: Session,
    email: str,
    password: str,
    display_name: str,
) -> User:
    """Create a new user account.

    Raises ValueError if the email is already registered.
    """
    password_hash = _pwd_context.hash(password)
    try:
        user = create_user(
            session=session,
            email=email,
            password_hash=password_hash,
            display_name=display_name,
        )
        session.commit()
        return user
    except IntegrityError:
        session.rollback()
        raise ValueError("An account with that email already exists.")


def login_user(
    session: Session,
    email: str,
    password: str,
    settings: APISettings,
) -> tuple[User, str]:
    """Verify credentials and create a new session.

    Returns (User, plaintext_session_token).
    Raises ValueError on bad credentials.
    """
    user = get_user_by_email(session, email)
    if user is None or not user.is_active:
        raise ValueError("Invalid email or password.")
    if not _pwd_context.verify(password, user.password_hash):
        raise ValueError("Invalid email or password.")

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.session_expire_seconds
    )
    create_session(
        session=session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.commit()
    return user, token


def logout_user(session: Session, session_token: str) -> None:
    """Invalidate the current session."""
    token_hash = _hash_token(session_token)
    delete_session_by_token_hash(session, token_hash)
    session.commit()
