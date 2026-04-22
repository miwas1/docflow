"""Celery app scaffold for the control plane."""

from celery import Celery
from kombu import Queue

from orchestrator_service.config import get_settings

QUEUE_NAMES = (
    "document.preprocess",
    "document.extract",
    "document.classify",
    "document.persist",
    "document.webhook",
)

settings = get_settings()
celery_app = Celery("doc_platform_orchestrator", broker=settings.rabbitmq_url)
celery_app.conf.update(
    task_default_queue=QUEUE_NAMES[0],
    task_queues=tuple(Queue(name) for name in QUEUE_NAMES),
    task_create_missing_queues=False,
    include=("orchestrator_service.tasks",),
)


def enqueue_preprocess_job(job_id: str, document_id: str) -> None:
    celery_app.send_task(
        "document.preprocess.accepted",
        kwargs={"job_id": job_id, "document_id": document_id},
        queue=QUEUE_NAMES[0],
    )


def enqueue_extract_job(payload: dict, *, attempt: int = 1, countdown: int | None = None) -> None:
    celery_app.send_task(
        "document.extract.run",
        kwargs={"payload": payload, "attempt": attempt},
        queue="document.extract",
        countdown=countdown,
    )


def enqueue_classify_job(payload: dict, *, attempt: int = 1, countdown: int | None = None) -> None:
    celery_app.send_task(
        "document.classify.run",
        kwargs={"payload": payload, "attempt": attempt},
        queue="document.classify",
        countdown=countdown,
    )


def enqueue_webhook_delivery(job_id: str, *, attempt: int = 1, countdown: int | None = None) -> None:
    celery_app.send_task(
        "document.webhook.deliver",
        kwargs={"job_id": job_id, "attempt": attempt},
        queue="document.webhook",
        countdown=countdown,
    )


from orchestrator_service import tasks as _registered_tasks  # noqa: F401,E402
