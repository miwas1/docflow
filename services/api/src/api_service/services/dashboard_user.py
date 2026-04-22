"""Service layer: dashboard user-facing API key, webhook, and job management."""

import hashlib
import secrets

from api_service.db.models import APIClient, Job, WebhookSubscription
from api_service.repositories.clients import (
    create_client_for_user,
    list_clients_for_user,
    revoke_client,
)
from api_service.repositories.webhooks import (
    create_webhook_subscription,
    delete_subscription,
    list_subscriptions_for_user,
    update_subscription,
)
from sqlalchemy.orm import Session


def _hash_api_key(key: str) -> str:
    """Return SHA-256 hex digest of a plaintext API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------


def get_api_keys_for_user(session: Session, user_id: str) -> list[APIClient]:
    """Return all API clients (active or not) owned by the user."""
    return list_clients_for_user(session, user_id)


def create_api_key(
    session: Session,
    user_id: str,
    display_name: str,
) -> tuple[APIClient, str]:
    """Generate a new API key for the user.

    Returns (APIClient, plaintext_key). The plaintext key is shown **once**
    and never stored; only the SHA-256 hash is persisted.
    """
    plaintext = f"dp_{secrets.token_urlsafe(32)}"
    key_hash = _hash_api_key(plaintext)
    client = create_client_for_user(
        session=session,
        user_id=user_id,
        display_name=display_name,
        api_key_hash=key_hash,
    )
    session.commit()
    return client, plaintext


def revoke_api_key(session: Session, client_id: str, user_id: str) -> None:
    """Soft-revoke an API key owned by the user."""
    revoke_client(session=session, client_id=client_id, user_id=user_id)
    session.commit()


# ---------------------------------------------------------------------------
# Webhook subscription management
# ---------------------------------------------------------------------------


def get_webhooks_for_user(session: Session, user_id: str) -> list[WebhookSubscription]:
    """Return all webhook subscriptions for clients owned by the user."""
    return list_subscriptions_for_user(session, user_id)


def create_webhook_for_user(
    session: Session,
    user_id: str,
    client_id: str,
    target_url: str,
    subscribed_events: list[str],
) -> WebhookSubscription:
    """Create a webhook subscription for an API client owned by the user."""
    signing_secret = f"whsec_{secrets.token_urlsafe(32)}"
    sub = create_webhook_subscription(
        session=session,
        client_id=client_id,
        target_url=target_url,
        signing_secret=signing_secret,
        subscribed_events=subscribed_events,
    )
    session.commit()
    return sub


def update_webhook_for_user(
    session: Session,
    subscription_id: str,
    user_id: str,
    target_url: str,
    subscribed_events: list[str],
    is_active: bool,
) -> WebhookSubscription | None:
    """Update a webhook subscription owned by the user."""
    sub = update_subscription(
        session=session,
        subscription_id=subscription_id,
        user_id=user_id,
        target_url=target_url,
        subscribed_events=subscribed_events,
        is_active=is_active,
    )
    if sub:
        session.commit()
    return sub


def delete_webhook_for_user(
    session: Session,
    subscription_id: str,
    user_id: str,
) -> None:
    """Delete a webhook subscription owned by the user."""
    delete_subscription(session, subscription_id, user_id)
    session.commit()


# ---------------------------------------------------------------------------
# Job history
# ---------------------------------------------------------------------------


def list_jobs_for_user(
    session: Session,
    user_id: str,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    """Return jobs belonging to any of the user's API clients."""
    from api_service.db.models import APIClient as _APIClient

    client_ids_query = (
        session.query(_APIClient.client_id)
        .filter(_APIClient.user_id == user_id)
        .subquery()
    )
    query = session.query(Job).filter(Job.client_id.in_(client_ids_query))
    if status_filter:
        query = query.filter(Job.status == status_filter)
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(limit)
    return list(query)
