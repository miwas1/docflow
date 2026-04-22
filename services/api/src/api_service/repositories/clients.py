"""Client repository helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from api_service.db.models import APIClient


def get_active_client_by_api_key_hash(session: Session, api_key_hash: str) -> APIClient | None:
    statement = select(APIClient).where(
        APIClient.api_key_hash == api_key_hash,
        APIClient.is_active.is_(True),
    )
    return session.scalar(statement)
