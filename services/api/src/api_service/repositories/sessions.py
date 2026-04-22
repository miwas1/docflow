"""Repository: user session queries."""

import uuid
from datetime import datetime, timezone

from api_service.db.models import UserSession
from sqlalchemy.orm import Session


def create_session(
    session: Session,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> UserSession:
    """Persist a new session record and return it."""
    now = datetime.now(timezone.utc)
    user_session = UserSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_token_hash=token_hash,
        expires_at=expires_at,
        created_at=now,
        last_used_at=None,
    )
    session.add(user_session)
    session.flush()
    return user_session


def get_session_by_token_hash(session: Session, token_hash: str) -> UserSession | None:
    """Return an unexpired session matching the given token hash."""
    now = datetime.now(timezone.utc)
    return (
        session.query(UserSession)
        .filter(
            UserSession.session_token_hash == token_hash,
            UserSession.expires_at > now,
        )
        .first()
    )


def delete_session(session: Session, session_id: str) -> None:
    """Delete a session by its primary key."""
    user_session = (
        session.query(UserSession).filter(UserSession.id == session_id).first()
    )
    if user_session:
        session.delete(user_session)
        session.flush()


def delete_session_by_token_hash(session: Session, token_hash: str) -> None:
    """Delete a session identified by its token hash (used during logout)."""
    user_session = (
        session.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash)
        .first()
    )
    if user_session:
        session.delete(user_session)
        session.flush()
