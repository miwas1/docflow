"""Dashboard webhook subscription management routes."""

from api_service.dashboard_render import render_dashboard
from api_service.db.models import User
from api_service.dependencies import get_db_session, require_current_user
from api_service.repositories.clients import list_clients_for_user
from api_service.services.dashboard_user import (
    create_webhook_for_user,
    delete_webhook_for_user,
    get_webhooks_for_user,
    update_webhook_for_user,
)
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")

_ALL_EVENTS = ["job.completed", "job.failed"]


@router.get("/webhooks", response_class=HTMLResponse, include_in_schema=False)
def webhooks_page(
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> HTMLResponse:
    """Render the webhooks management page."""
    subs = get_webhooks_for_user(db, user.id)
    clients = list_clients_for_user(db, user.id)
    active_clients = [c for c in clients if c.is_active]

    rows = "".join(
        f"<tr>"
        f"<td>{s.client_id[:8]}…</td>"
        f"<td><a href='{s.target_url}' target='_blank' rel='noopener'>{s.target_url}</a></td>"
        f"<td>{', '.join(s.subscribed_events_json)}</td>"
        f'<td><span class="badge badge-{"completed" if s.is_active else "failed"}">'
        f'{"Active" if s.is_active else "Paused"}</span></td>'
        f"<td>"
        f'<form method="post" action="/dashboard/webhooks/{s.id}/delete" style="display:inline">'
        f'<button class="btn btn-danger btn-sm" onclick="return confirm(\'Delete this subscription?\')">Delete</button>'
        f"</form>"
        f"</td>"
        f"</tr>"
        for s in subs
    )
    if not rows:
        rows = (
            "<tr><td colspan='5' class='muted'>No webhook subscriptions yet.</td></tr>"
        )

    client_options = "".join(
        f'<option value="{c.client_id}">{c.display_name} ({c.client_id[:8]}…)</option>'
        for c in active_clients
    )
    if not client_options:
        client_options = "<option disabled>Create an API key first</option>"

    event_checkboxes = "".join(
        f'<label><input type="checkbox" name="events" value="{e}" checked> {e}</label> '
        for e in _ALL_EVENTS
    )

    html = render_dashboard(
        "dashboard/webhooks.html",
        page_title="Webhooks",
        active="webhooks",
        user_name=user.display_name,
        sub_rows=rows,
        client_options=client_options,
        event_checkboxes=event_checkboxes,
    )
    return HTMLResponse(html)


@router.post("/webhooks", response_class=HTMLResponse, include_in_schema=False)
def create_webhook(
    client_id: str = Form(...),
    target_url: str = Form(...),
    events: list[str] = Form(default=[]),
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> RedirectResponse:
    """Create a new webhook subscription."""
    selected_events = [e for e in events if e in _ALL_EVENTS]
    if not selected_events:
        selected_events = _ALL_EVENTS
    create_webhook_for_user(
        session=db,
        user_id=user.id,
        client_id=client_id,
        target_url=target_url,
        subscribed_events=selected_events,
    )
    return RedirectResponse("/dashboard/webhooks", status_code=303)


@router.post("/webhooks/{subscription_id}/delete", include_in_schema=False)
def delete_webhook(
    subscription_id: str,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> RedirectResponse:
    """Delete a webhook subscription."""
    delete_webhook_for_user(db, subscription_id=subscription_id, user_id=user.id)
    return RedirectResponse("/dashboard/webhooks", status_code=303)
