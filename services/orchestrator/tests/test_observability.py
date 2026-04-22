import inspect

from orchestrator_service import tasks
from orchestrator_service.observability import ORCHESTRATOR_METRIC_DEFINITIONS, TASK_OBSERVABILITY


def test_orchestrator_observability_defines_webhook_metrics_without_high_cardinality_labels() -> None:
    assert "doc_platform_queue_tasks_total" in ORCHESTRATOR_METRIC_DEFINITIONS
    assert "doc_platform_job_stage_failures_total" in ORCHESTRATOR_METRIC_DEFINITIONS
    assert ORCHESTRATOR_METRIC_DEFINITIONS["doc_platform_queue_tasks_total"]["labels"] == (
        "service",
        "stage",
        "outcome",
        "event_type",
    )
    assert "job_id" not in ORCHESTRATOR_METRIC_DEFINITIONS["doc_platform_queue_tasks_total"]["labels"]


def test_orchestrator_tasks_reference_webhook_observability_contract() -> None:
    source = inspect.getsource(tasks)

    assert TASK_OBSERVABILITY["document.webhook"]["span_name"] == "webhook.deliver"
    assert "document.webhook" in TASK_OBSERVABILITY
    assert "observe_task_start" in source
    assert "observe_task_finish" in source
    assert 'name="document.webhook.deliver"' in source
