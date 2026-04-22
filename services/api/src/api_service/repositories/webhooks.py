"""Webhook subscription and delivery repository helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from api_service.db.models import WebhookDelivery, WebhookSubscription
from sqlalchemy import select
from sqlalchemy.orm import Session


def create_webhook_subscription(
    session: Session,
    *,
    client_id: str,
    target_url: str,
    signing_secret: str,
    subscribed_events: list[str],
) -> WebhookSubscription:
    subscription = WebhookSubscription(
        id=str(uuid4()),
        client_id=client_id,
        target_url=target_url,
        signing_secret=signing_secret,
        subscribed_events_json=subscribed_events,
        is_active=True,
    )
    session.add(subscription)
    session.flush()
    return subscription


def get_active_webhook_subscription_for_client(
    session: Session, *, client_id: str
) -> WebhookSubscription | None:
    statement = (
        select(WebhookSubscription)
        .where(
            WebhookSubscription.client_id == client_id,
            WebhookSubscription.is_active.is_(True),
        )
        .order_by(WebhookSubscription.created_at.desc())
    )
    return session.scalars(statement).first()


def create_webhook_delivery(
    session: Session,
    *,
    job_id: str,
    client_id: str,
    subscription_id: str,
    event_type: str,
    payload_json: dict,
    delivery_status: str,
) -> WebhookDelivery:
    delivery = WebhookDelivery(
        id=str(uuid4()),
        job_id=job_id,
        client_id=client_id,
        subscription_id=subscription_id,
        event_type=event_type,
        payload_json=payload_json,
        delivery_status=delivery_status,
        attempt_count=0,
    )
    session.add(delivery)
    session.flush()
    return delivery


def update_webhook_delivery_attempt(
    session: Session,
    *,
    delivery_id: str,
    attempt_count: int,
    delivery_status: str,
    last_http_status: int | None,
    last_error_message: str | None,
    next_retry_at: datetime | None,
) -> WebhookDelivery:
    delivery = session.get(WebhookDelivery, delivery_id)
    if delivery is None:
        raise ValueError(f"Webhook delivery {delivery_id} not found")
    delivery.attempt_count = attempt_count
    delivery.delivery_status = delivery_status
    delivery.last_http_status = last_http_status
    delivery.last_error_message = last_error_message
    delivery.next_retry_at = next_retry_at
    delivery.last_attempt_at = datetime.now(UTC)
    session.flush()
    return delivery


def list_webhook_deliveries_for_job(
    session: Session, *, job_id: str
) -> list[WebhookDelivery]:
    statement = (
        select(WebhookDelivery)
        .where(WebhookDelivery.job_id == job_id)
        .order_by(WebhookDelivery.created_at.asc())
    )
    return list(session.scalars(statement))


def get_webhook_delivery_for_job(
    session: Session, *, job_id: str, delivery_id: str
) -> WebhookDelivery | None:
    statement = select(WebhookDelivery).where(
        WebhookDelivery.job_id == job_id,
        WebhookDelivery.id == delivery_id,
    )
    return session.scalar(statement)


def list_subscriptions_for_user(
    session: Session,
    user_id: str,
) -> list[WebhookSubscription]:
    """Return all webhook subscriptions for clients owned by a dashboard user."""
    from api_service.db.models import APIClient  # local import avoids circularity

    statement = (
        select(WebhookSubscription)
        .join(APIClient, APIClient.client_id == WebhookSubscription.client_id)
        .where(APIClient.user_id == user_id)
        .order_by(WebhookSubscription.created_at.desc())
    )
    return list(session.scalars(statement))


def get_subscription_for_user(
    session: Session,
    subscription_id: str,
    user_id: str,
) -> WebhookSubscription | None:
    """Return a subscription only if it belongs to a client owned by user."""
    from api_service.db.models import APIClient

    statement = (
        select(WebhookSubscription)
        .join(APIClient, APIClient.client_id == WebhookSubscription.client_id)
        .where(
            WebhookSubscription.id == subscription_id,
            APIClient.user_id == user_id,
        )
    )
    return session.scalar(statement)


def update_subscription(
    session: Session,
    *,
    subscription_id: str,
    user_id: str,
    target_url: str,
    subscribed_events: list[str],
    is_active: bool,
) -> WebhookSubscription | None:
    """Update mutable fields of a subscription owned by the user."""
    sub = get_subscription_for_user(session, subscription_id, user_id)
    if sub is None:
        return None
    sub.target_url = target_url
    sub.subscribed_events_json = subscribed_events
    sub.is_active = is_active
    session.flush()
    return sub


def delete_subscription(session: Session, subscription_id: str, user_id: str) -> None:
    """Delete a subscription owned by the user."""
    sub = get_subscription_for_user(session, subscription_id, user_id)
    if sub:
        session.delete(sub)
        session.flush()
