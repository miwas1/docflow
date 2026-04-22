"""Static API-key authentication helpers."""

from dataclasses import dataclass
import hashlib
import hmac

from sqlalchemy.orm import Session

from api_service.config import APISettings
from api_service.errors import APIError
from api_service.repositories.clients import get_active_client_by_api_key_hash


@dataclass(slots=True)
class AuthenticatedClient:
    client_id: str
    display_name: str


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def authenticate_api_key(
    *,
    api_key: str | None,
    settings: APISettings,
    session: Session,
) -> AuthenticatedClient:
    if not api_key:
        raise APIError(
            status_code=401,
            error_code="unauthorized",
            message="Missing API key.",
        )

    for client_id, configured_key in settings.api_keys_json.items():
        if hmac.compare_digest(api_key, configured_key):
            return AuthenticatedClient(client_id=client_id, display_name=client_id)

    hashed_key = hash_api_key(api_key)
    api_client = get_active_client_by_api_key_hash(session, hashed_key)
    if api_client is not None:
        return AuthenticatedClient(
            client_id=api_client.client_id,
            display_name=api_client.display_name,
        )

    raise APIError(
        status_code=401,
        error_code="unauthorized",
        message="Invalid API key.",
    )
