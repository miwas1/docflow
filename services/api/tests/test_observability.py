from api_service.main import app
from api_service.observability import API_METRIC_DEFINITIONS, API_SPAN_NAMES
from doc_platform_contracts.observability import (
    CORRELATION_FIELDS,
    FORBIDDEN_METRIC_LABELS,
    METRIC_DEFINITIONS,
    SERVICE_NAMES,
    SPAN_NAMES,
)


def test_shared_observability_contract_uses_bounded_metric_labels() -> None:
    assert CORRELATION_FIELDS == ("job_id", "document_id", "tenant_id", "current_stage", "trace_id")
    assert SERVICE_NAMES["api"] == "api"
    assert SPAN_NAMES["api_request"] == "api.request"
    assert SPAN_NAMES["webhook_deliver"] == "webhook.deliver"
    assert "doc_platform_webhook_delivery_attempts_total" in METRIC_DEFINITIONS

    for metric in METRIC_DEFINITIONS.values():
        for label in metric["labels"]:
            assert label not in FORBIDDEN_METRIC_LABELS


def test_api_app_installs_observability_middleware_and_contracts() -> None:
    middleware_names = {middleware.cls.__name__ for middleware in app.user_middleware}

    assert "ObservabilityMiddleware" in middleware_names
    assert "doc_platform_api_requests_total" in API_METRIC_DEFINITIONS
    assert API_METRIC_DEFINITIONS["doc_platform_api_requests_total"]["labels"] == ("route", "method", "status_family")
    assert API_SPAN_NAMES["upload"] == "api.request"
    assert app.state.observability["service"] == "api"
