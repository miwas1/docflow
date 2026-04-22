"""Minimal observability hooks for the classifier service."""

from __future__ import annotations

from doc_platform_contracts.observability import SERVICE_NAMES, SPAN_NAMES


def setup_classifier_observability(app) -> None:
    app.state.observability = {
        "service": SERVICE_NAMES["classifier"],
        "span_name": SPAN_NAMES["classifier_run"],
    }
