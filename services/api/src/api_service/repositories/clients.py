"""Client repository helpers."""

import uuid
from datetime import datetime, timezone

from api_service.db.models import APIClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_active_client_by_api_key_hash(
    session: Session, api_key_hash: str
) -> APIClient | None:
    statement = select(APIClient).where(
        APIClient.api_key_hash == api_key_hash,
        APIClient.is_active.is_(True),
    )
    return session.scalar(statement)


def list_clients_for_user(session: Session, user_id: str) -> list[APIClient]:
    """Return all active API clients owned by a dashboard user."""
    statement = (
        select(APIClient)
        .where(APIClient.user_id == user_id)
        .order_by(APIClient.created_at.desc())
    )
    return list(session.scalars(statement))


def create_client_for_user(
    session: Session,
    user_id: str,
    display_name: str,
    api_key_hash: str,
) -> APIClient:
    """Create a new API client record owned by a dashboard user."""
    now = datetime.now(timezone.utc)
    client_id = str(uuid.uuid4())
    client = APIClient(
        id=str(uuid.uuid4()),
        client_id=client_id,
        display_name=display_name.strip(),
        api_key_hash=api_key_hash,
        is_active=True,
        user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(client)
    session.flush()
    return client


def revoke_client(session: Session, client_id: str, user_id: str) -> None:
    """Soft-revoke an API client, verifying it belongs to the given user."""
    client = (
        session.query(APIClient)
        .filter(APIClient.client_id == client_id, APIClient.user_id == user_id)
        .first()
    )
    if client:
        client.is_active = False
        client.updated_at = datetime.now(timezone.utc)
        session.flush()
