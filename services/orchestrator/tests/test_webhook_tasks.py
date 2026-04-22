from datetime import UTC, datetime
from unittest.mock import Mock

from orchestrator_service.tasks import deliver_webhook


def test_deliver_webhook_records_success_for_2xx_callbacks(monkeypatch) -> None:
    webhook_client = Mock()
    webhook_client.fetch_dispatch_payload.return_value = {
        "delivery": {"id": "delivery-1"},
        "target_url": "https://example.com/hooks/doc-platform",
        "signature": "sha256=abc123",
        "payload": {"event_type": "job.completed"},
    }
    webhook_client.deliver.return_value = {"status_code": 204}

    monkeypatch.setattr("orchestrator_service.tasks.build_default_webhook_client", lambda: webhook_client)

    record_outcome = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.record_webhook_delivery_outcome", record_outcome)

    result = deliver_webhook(job_id="job-123")

    assert result["delivery_status"] == "delivered"
    record_outcome.assert_called_once()
    kwargs = record_outcome.call_args.kwargs
    assert kwargs["delivery_status"] == "delivered"
    assert kwargs["attempt_count"] == 1
    assert kwargs["last_http_status"] == 204


def test_deliver_webhook_marks_retrying_before_max_attempts(monkeypatch) -> None:
    webhook_client = Mock()
    webhook_client.fetch_dispatch_payload.return_value = {
        "delivery": {"id": "delivery-1"},
        "target_url": "https://example.com/hooks/doc-platform",
        "signature": "sha256=abc123",
        "payload": {"event_type": "job.failed"},
    }
    webhook_client.deliver.side_effect = TimeoutError("callback timeout")

    monkeypatch.setattr("orchestrator_service.tasks.build_default_webhook_client", lambda: webhook_client)
    monkeypatch.setattr(
        "orchestrator_service.tasks.get_settings",
        lambda: Mock(webhook_max_attempts=4, webhook_retry_backoff_seconds=[30, 120, 600]),
    )

    enqueue_retry = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.enqueue_webhook_delivery", enqueue_retry)
    record_outcome = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.record_webhook_delivery_outcome", record_outcome)

    result = deliver_webhook(job_id="job-123", attempt=1)

    assert result["delivery_status"] == "retrying"
    enqueue_retry.assert_called_once_with("job-123", attempt=2, countdown=30)
    kwargs = record_outcome.call_args.kwargs
    assert kwargs["delivery_status"] == "retrying"
    assert kwargs["attempt_count"] == 1
    assert kwargs["last_error_message"] == "callback timeout"
    assert isinstance(kwargs["next_retry_at"], datetime)
    assert kwargs["next_retry_at"].tzinfo == UTC


def test_deliver_webhook_marks_failed_after_max_attempts(monkeypatch) -> None:
    webhook_client = Mock()
    webhook_client.fetch_dispatch_payload.return_value = {
        "delivery": {"id": "delivery-1"},
        "target_url": "https://example.com/hooks/doc-platform",
        "signature": "sha256=abc123",
        "payload": {"event_type": "job.failed"},
    }
    webhook_client.deliver.side_effect = TimeoutError("callback timeout")

    monkeypatch.setattr("orchestrator_service.tasks.build_default_webhook_client", lambda: webhook_client)
    monkeypatch.setattr(
        "orchestrator_service.tasks.get_settings",
        lambda: Mock(webhook_max_attempts=4, webhook_retry_backoff_seconds=[30, 120, 600]),
    )

    enqueue_retry = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.enqueue_webhook_delivery", enqueue_retry)
    record_outcome = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.record_webhook_delivery_outcome", record_outcome)

    result = deliver_webhook(job_id="job-123", attempt=4)

    assert result["delivery_status"] == "failed"
    enqueue_retry.assert_not_called()
    kwargs = record_outcome.call_args.kwargs
    assert kwargs["delivery_status"] == "failed"
    assert kwargs["attempt_count"] == 4
    assert kwargs["next_retry_at"] is None


def test_deliver_webhook_uses_second_retry_interval_for_second_failure(monkeypatch) -> None:
    webhook_client = Mock()
    webhook_client.fetch_dispatch_payload.return_value = {
        "delivery": {"id": "delivery-1"},
        "target_url": "https://example.com/hooks/doc-platform",
        "signature": "sha256=abc123",
        "payload": {"event_type": "job.failed"},
    }
    webhook_client.deliver.side_effect = TimeoutError("callback timeout")

    monkeypatch.setattr("orchestrator_service.tasks.build_default_webhook_client", lambda: webhook_client)
    monkeypatch.setattr(
        "orchestrator_service.tasks.get_settings",
        lambda: Mock(webhook_max_attempts=4, webhook_retry_backoff_seconds=[30, 120, 600]),
    )

    enqueue_retry = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.enqueue_webhook_delivery", enqueue_retry)
    record_outcome = Mock()
    monkeypatch.setattr("orchestrator_service.tasks.record_webhook_delivery_outcome", record_outcome)

    result = deliver_webhook(job_id="job-123", attempt=2)

    assert result["delivery_status"] == "retrying"
    enqueue_retry.assert_called_once_with("job-123", attempt=3, countdown=120)
