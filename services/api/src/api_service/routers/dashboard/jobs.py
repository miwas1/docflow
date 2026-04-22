"""Dashboard job history routes."""

from api_service.dashboard_render import render_dashboard
from api_service.db.models import Job, User
from api_service.dependencies import get_db_session, require_current_user
from api_service.services.dashboard_user import list_jobs_for_user
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")


@router.get("/jobs", response_class=HTMLResponse, include_in_schema=False)
def jobs_page(
    status: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> HTMLResponse:
    """Render the job history list."""
    limit = 25
    offset = (page - 1) * limit
    jobs = list_jobs_for_user(
        db, user.id, status_filter=status, limit=limit, offset=offset
    )

    rows = "".join(
        f"<tr>"
        f'<td><a href="/dashboard/jobs/{j.id}" class="link">{j.id[:8]}…</a></td>'
        f"<td>{j.source_filename}</td>"
        f'<td><span class="badge badge-{j.status}">{j.status}</span></td>'
        f"<td>{j.current_stage}</td>"
        f"<td>{j.failure_code or '—'}</td>"
        f"<td>{j.created_at.strftime('%Y-%m-%d %H:%M')}</td>"
        f"</tr>"
        for j in jobs
    )
    if not rows:
        rows = "<tr><td colspan='6' class='muted'>No jobs found.</td></tr>"

    # Status filter pills
    statuses = ["", "queued", "running", "completed", "failed"]
    labels = ["All", "Queued", "Running", "Completed", "Failed"]
    filter_pills = "".join(
        f'<a href="/dashboard/jobs{"?status=" + s if s else ""}" '
        f'class="pill {"pill-active" if (status or "") == s else ""}">{l}</a>'
        for s, l in zip(statuses, labels)
    )

    prev_link = (
        f'<a href="/dashboard/jobs?{"status=" + status + "&" if status else ""}page={page - 1}" class="btn">← Prev</a>'
        if page > 1
        else ""
    )
    next_link = (
        f'<a href="/dashboard/jobs?{"status=" + status + "&" if status else ""}page={page + 1}" class="btn">Next →</a>'
        if len(jobs) == limit
        else ""
    )

    html = render_dashboard(
        "dashboard/jobs.html",
        page_title="Job History",
        active="jobs",
        user_name=user.display_name,
        job_rows=rows,
        filter_pills=filter_pills,
        prev_link=prev_link,
        next_link=next_link,
        page=page,
    )
    return HTMLResponse(html)


@router.get("/jobs/{job_id}", response_class=HTMLResponse, include_in_schema=False)
def job_detail_page(
    job_id: str,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_current_user),
) -> HTMLResponse:
    """Render job detail: stage timeline, classification, artifacts."""
    from api_service.db.models import APIClient, Artifact, ClassificationRun, JobEvent

    # Verify job belongs to user's clients
    client_ids = [
        c
        for (c,) in db.query(APIClient.client_id)
        .filter(APIClient.user_id == user.id)
        .all()
    ]
    job: Job | None = (
        db.query(Job).filter(Job.id == job_id, Job.client_id.in_(client_ids)).first()
        if client_ids
        else None
    )
    if job is None:
        html = render_dashboard(
            "dashboard/job_detail.html",
            page_title="Job Not Found",
            active="jobs",
            user_name=user.display_name,
            job_id=job_id,
            not_found="<p class='error'>Job not found or does not belong to your account.</p>",
            job_meta="",
            stage_timeline="",
            classification_card="",
            artifacts_list="",
        )
        return HTMLResponse(html, status_code=404)

    # Stage events timeline
    events = (
        db.query(JobEvent)
        .filter(JobEvent.job_id == job_id)
        .order_by(JobEvent.created_at.asc())
        .all()
    )
    timeline_rows = "".join(
        f"<tr><td>{e.created_at.strftime('%H:%M:%S')}</td><td>{e.event_type}</td><td>{e.stage}</td></tr>"
        for e in events
    )
    stage_timeline = (
        f"<table><thead><tr><th>Time</th><th>Event</th><th>Stage</th></tr></thead>"
        f"<tbody>{timeline_rows or '<tr><td colspan=3 class=muted>No events.</td></tr>'}</tbody></table>"
    )

    # Classification result
    cls_run: ClassificationRun | None = (
        db.query(ClassificationRun).filter(ClassificationRun.job_id == job_id).first()
    )
    if cls_run:
        candidates = "".join(
            f"<tr><td>{c.get('label','')}</td><td>{c.get('score', 0):.2%}</td></tr>"
            for c in (cls_run.candidate_labels_json or [])
        )
        classification_card = (
            f"<p><strong>Label:</strong> {cls_run.final_label}</p>"
            f"<p><strong>Confidence:</strong> {cls_run.confidence:.2%}</p>"
            f"<p style='margin-bottom:12px'><strong>Model:</strong> "
            f"{cls_run.trace_json.get('model', '—')} "
            f"v{cls_run.trace_json.get('version', '—')}</p>"
            f"<table><thead><tr><th>Label</th><th>Score</th></tr></thead>"
            f"<tbody>{candidates}</tbody></table>"
        )
    else:
        classification_card = "<p class='muted'>Classification not yet available.</p>"

    # Artifacts
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.job_id == job_id)
        .order_by(Artifact.created_at.asc())
        .all()
    )
    artifact_rows = "".join(
        f"<tr><td>{a.artifact_type}</td><td>{a.stage}</td>"
        f"<td><code>{a.storage_key}</code></td><td>{a.media_type}</td></tr>"
        for a in artifacts
    )
    artifacts_list = (
        f"<table><thead><tr><th>Type</th><th>Stage</th><th>Key</th><th>Media Type</th></tr></thead>"
        f"<tbody>{artifact_rows or '<tr><td colspan=4 class=muted>No artifacts.</td></tr>'}</tbody></table>"
    )

    failure_info = ""
    if job.failure_code:
        failure_info = f"<p class='error'><strong>{job.failure_code}</strong>: {job.failure_message or ''}</p>"

    job_meta = (
        f"<dl>"
        f"<dt>Job ID</dt><dd><code>{job.id}</code></dd>"
        f"<dt>Document ID</dt><dd><code>{job.document_id}</code></dd>"
        f"<dt>File</dt><dd>{job.source_filename}</dd>"
        f"<dt>Status</dt><dd><span class='badge badge-{job.status}'>{job.status}</span></dd>"
        f"<dt>Stage</dt><dd>{job.current_stage}</dd>"
        f"<dt>Created</dt><dd>{job.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</dd>"
        f"<dt>Updated</dt><dd>{job.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</dd>"
        f"</dl>"
        f"{failure_info}"
    )

    html = render_dashboard(
        "dashboard/job_detail.html",
        page_title=f"Job {job.id[:8]}",
        active="jobs",
        user_name=user.display_name,
        job_id=job.id[:16],
        not_found="",
        job_meta=job_meta,
        stage_timeline=stage_timeline,
        classification_card=classification_card,
        artifacts_list=artifacts_list,
    )
    return HTMLResponse(html)
