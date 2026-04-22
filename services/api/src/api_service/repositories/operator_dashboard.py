"""Operator dashboard aggregation queries."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from api_service.db.models import ClassificationRun, ExtractionRun, Job, JobEvent, WebhookDelivery


def get_job_status_counts(session: Session) -> dict[str, int]:
    statement = select(Job.status, func.count()).group_by(Job.status)
    counts = {status: count for status, count in session.execute(statement)}
    return {
        "queued": counts.get("queued", 0),
        "running": counts.get("running", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
    }


def list_jobs(
    session: Session,
    *,
    status: str | None,
    client_id: str | None,
    q: str | None,
    limit: int,
) -> list[tuple[Job, str | None]]:
    latest_delivery = (
        select(WebhookDelivery.job_id, func.max(WebhookDelivery.updated_at).label("latest_updated_at"))
        .group_by(WebhookDelivery.job_id)
        .subquery()
    )
    latest_delivery_status = (
        select(WebhookDelivery.job_id, WebhookDelivery.delivery_status)
        .join(
            latest_delivery,
            (WebhookDelivery.job_id == latest_delivery.c.job_id)
            & (WebhookDelivery.updated_at == latest_delivery.c.latest_updated_at),
        )
        .subquery()
    )
    statement = (
        select(Job, latest_delivery_status.c.delivery_status)
        .outerjoin(latest_delivery_status, latest_delivery_status.c.job_id == Job.id)
        .order_by(Job.updated_at.desc())
        .limit(limit)
    )
    if status:
        statement = statement.where(Job.status == status)
    if client_id:
        statement = statement.where(Job.client_id == client_id)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Job.id.ilike(pattern),
                Job.document_id.ilike(pattern),
                Job.failure_message.ilike(pattern),
                Job.source_filename.ilike(pattern),
            )
        )
    return list(session.execute(statement).all())


def get_job_detail(session: Session, *, job_id: str) -> Job | None:
    return session.get(Job, job_id)


def list_stage_events(session: Session, *, job_id: str) -> list[JobEvent]:
    statement = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc())
    return list(session.scalars(statement))


def get_latest_extraction_run(session: Session, *, job_id: str) -> ExtractionRun | None:
    statement = select(ExtractionRun).where(ExtractionRun.job_id == job_id).order_by(ExtractionRun.created_at.desc())
    return session.scalars(statement).first()


def get_latest_classification_run(session: Session, *, job_id: str) -> ClassificationRun | None:
    statement = (
        select(ClassificationRun)
        .where(ClassificationRun.job_id == job_id)
        .order_by(ClassificationRun.created_at.desc())
    )
    return session.scalars(statement).first()


def list_webhook_deliveries(session: Session, *, job_id: str) -> list[WebhookDelivery]:
    statement = select(WebhookDelivery).where(WebhookDelivery.job_id == job_id).order_by(WebhookDelivery.updated_at.desc())
    return list(session.scalars(statement))
