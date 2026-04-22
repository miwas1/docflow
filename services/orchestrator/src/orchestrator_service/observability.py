"""Minimal observability helpers for orchestrator tasks."""

from __future__ import annotations

from doc_platform_contracts.observability import METRIC_DEFINITIONS, SERVICE_NAMES, SPAN_NAMES

ORCHESTRATOR_METRIC_DEFINITIONS = {
    "doc_platform_queue_tasks_total": METRIC_DEFINITIONS["doc_platform_queue_tasks_total"],
    "doc_platform_job_stage_failures_total": METRIC_DEFINITIONS["doc_platform_job_stage_failures_total"],
}

TASK_OBSERVABILITY = {
    "document.extract": {"span_name": SPAN_NAMES["orchestrator_task"], "service": SERVICE_NAMES["orchestrator"]},
    "document.classify": {"span_name": SPAN_NAMES["orchestrator_task"], "service": SERVICE_NAMES["orchestrator"]},
    "document.webhook": {"span_name": SPAN_NAMES["webhook_deliver"], "service": SERVICE_NAMES["orchestrator"]},
}


def observe_task_start(task_name: str, **context) -> dict:
    return {"task_name": task_name, "context": context}


def observe_task_finish(task_name: str, *, outcome: str, **context) -> dict:
    return {"task_name": task_name, "outcome": outcome, "context": context}
