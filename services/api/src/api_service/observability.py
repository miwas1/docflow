"""Minimal observability hooks for the API service."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

from doc_platform_contracts.observability import METRIC_DEFINITIONS, SERVICE_NAMES, SPAN_NAMES

API_METRIC_DEFINITIONS = {
    "doc_platform_api_requests_total": METRIC_DEFINITIONS["doc_platform_api_requests_total"],
}
API_SPAN_NAMES = {
    "upload": SPAN_NAMES["api_request"],
    "status": SPAN_NAMES["api_request"],
    "results": SPAN_NAMES["api_request"],
}


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)


def setup_api_observability(app) -> None:
    app.add_middleware(ObservabilityMiddleware)
    app.state.observability = {
        "service": SERVICE_NAMES["api"],
        "metrics": API_METRIC_DEFINITIONS,
        "spans": API_SPAN_NAMES,
    }
