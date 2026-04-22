"""Minimal observability hooks for the extractor service."""

from __future__ import annotations

from doc_platform_contracts.observability import SERVICE_NAMES, SPAN_NAMES


def setup_extractor_observability(app) -> None:
    app.state.observability = {
        "service": SERVICE_NAMES["extractor"],
        "span_name": SPAN_NAMES["extractor_run"],
    }
