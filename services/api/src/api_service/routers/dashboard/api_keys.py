"""Dashboard API key management routes."""

from api_service.dashboard_render import render_dashboard
from api_service.db.models import User
from api_service.dependencies import get_db_session, require_current_user
from api_service.services.dashboard_user import (
    create_api_key,
    get_api_keys_for_user,
    revoke_api_key,
)
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")


@router.get("/api-keys", response_class=HTMLResponse, include_in_schema=False)
def api_keys_page(
    new_key: str = "",
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> HTMLResponse:
    """Render the API keys management page."""
    clients = get_api_keys_for_user(db, user.id)

    rows = "".join(
        f"<tr>"
        f"<td>{c.display_name}</td>"
        f"<td><code>dp_…{c.api_key_hash[-8:]}</code></td>"
        f'<td><span class="badge badge-{"completed" if c.is_active else "failed"}">'
        f'{"Active" if c.is_active else "Revoked"}</span></td>'
        f"<td>{c.created_at.strftime('%Y-%m-%d')}</td>"
        f"<td>"
        + (
            f'<form method="post" action="/dashboard/api-keys/{c.client_id}/revoke" style="display:inline">'
            f'<button class="btn btn-danger btn-sm" onclick="return confirm(\'Revoke this key?\')">Revoke</button>'
            f"</form>"
            if c.is_active
            else "<span class='muted'>—</span>"
        )
        + f"</td>"
        f"</tr>"
        for c in clients
    )
    if not rows:
        rows = "<tr><td colspan='5' class='muted'>No API keys yet.</td></tr>"

    # One-time new key reveal modal
    reveal_modal = ""
    if new_key:
        reveal_modal = f"""
<div id="key-modal" class="modal-overlay">
  <div class="modal">
    <h2>Your new API key</h2>
    <p class="warning">Copy it now — it will <strong>never</strong> be shown again.</p>
    <div class="key-reveal"><code id="new-key-value">{new_key}</code></div>
    <button class="btn btn-primary" onclick="copyKey()">Copy</button>
    <a class="btn" href="/dashboard/api-keys">Done</a>
  </div>
</div>
<script>
function copyKey() {{
  const text = document.getElementById('new-key-value').innerText;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(() => {{
      alert('Copied!');
    }}).catch(err => {{
      console.error('Failed to copy: ', err);
      // Fallback if needed
    }});
  }} else {{
    // Fallback for non-secure contexts (e.g. dev over IP without HTTPS)
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {{
      document.execCommand('copy');
      alert('Copied!');
    }} catch (err) {{
      console.error('Fallback copy failed', err);
    }}
    document.body.removeChild(textArea);
  }}
}}
</script>"""

    html = render_dashboard(
        "dashboard/api_keys.html",
        page_title="API Keys",
        active="keys",
        user_name=user.display_name,
        key_rows=rows,
        reveal_modal=reveal_modal,
    )
    return HTMLResponse(html)


@router.post("/api-keys", response_class=HTMLResponse, include_in_schema=False)
def create_key(
    display_name: str = Form(...),
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> RedirectResponse:
    """Create a new API key and redirect back with the plaintext key in query param."""
    _client, plaintext = create_api_key(db, user_id=user.id, display_name=display_name)
    # Pass the plaintext via query param — only valid for one render, not stored.
    return RedirectResponse(f"/dashboard/api-keys?new_key={plaintext}", status_code=303)


@router.post("/api-keys/{client_id}/revoke", include_in_schema=False)
def revoke_key(
    client_id: str,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> RedirectResponse:
    """Revoke an API key owned by the current user."""
    revoke_api_key(db, client_id=client_id, user_id=user.id)
    return RedirectResponse("/dashboard/api-keys", status_code=303)
