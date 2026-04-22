from orchestrator_service.celery_app import QUEUE_NAMES, celery_app


def test_celery_app_uses_expected_name_and_queues() -> None:
    queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert celery_app.main == "doc_platform_orchestrator"
    assert queue_names == set(QUEUE_NAMES)
