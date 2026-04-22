"""Dashboard home page — job stats overview."""

from api_service.dashboard_render import render_dashboard
from api_service.db.models import Job, User
from api_service.dependencies import get_db_session, require_current_user
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/home", response_class=HTMLResponse, include_in_schema=False)
def dashboard_home(
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> HTMLResponse:
    """Render the dashboard home with per-user job stats."""
    from api_service.db.models import APIClient

    client_ids = [
        c
        for (c,) in db.query(APIClient.client_id)
        .filter(APIClient.user_id == user.id)
        .all()
    ]

    def count(status: str) -> int:
        if not client_ids:
            return 0
        return (
            db.query(Job)
            .filter(Job.client_id.in_(client_ids), Job.status == status)
            .count()
        )

    queued = count("queued")
    running = count("running")
    completed = count("completed")
    failed = count("failed")

    recent_jobs = (
        db.query(Job)
        .filter(Job.client_id.in_(client_ids))
        .order_by(Job.created_at.desc())
        .limit(10)
        .all()
        if client_ids
        else []
    )

    rows = "".join(
        f"<tr>"
        f'<td><a href="/dashboard/jobs/{j.id}" class="link">{j.id[:8]}…</a></td>'
        f"<td>{j.source_filename}</td>"
        f'<td><span class="badge badge-{j.status}">{j.status}</span></td>'
        f"<td>{j.current_stage}</td>"
        f"<td>{j.created_at.strftime('%Y-%m-%d %H:%M')}</td>"
        f"</tr>"
        for j in recent_jobs
    )
    if not rows:
        rows = "<tr><td colspan='5' class='muted'>No jobs yet. Upload your first document via the API.</td></tr>"

    html = render_dashboard(
        "dashboard/home.html",
        page_title="Overview",
        active="home",
        user_name=user.display_name,
        queued=queued,
        running=running,
        completed=completed,
        failed=failed,
        job_rows=rows,
    )
    return HTMLResponse(html)
