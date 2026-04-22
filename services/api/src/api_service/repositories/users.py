"""Repository: user account queries."""

import uuid
from datetime import datetime, timezone

from api_service.db.models import User
from sqlalchemy.orm import Session


def get_user_by_email(session: Session, email: str) -> User | None:
    """Fetch an active user by email address."""
    return session.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(session: Session, user_id: str) -> User | None:
    """Fetch an active user by primary key."""
    return (
        session.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    )


def create_user(
    session: Session, email: str, password_hash: str, display_name: str
) -> User:
    """Insert a new user record and return it."""
    now = datetime.now(timezone.utc)
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        password_hash=password_hash,
        display_name=display_name.strip(),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()
    return user
