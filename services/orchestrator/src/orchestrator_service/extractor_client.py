"""HTTP client wrapper for the extractor service."""

from __future__ import annotations

import json
from urllib import error, request

from doc_platform_contracts.extraction import ExtractedTextArtifact


class ExtractorClientError(Exception):
    """Raised when extractor requests fail."""


class ExtractorClient:
    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def run_extraction_request(self, payload: dict) -> ExtractedTextArtifact:
        http_request = request.Request(
            url=f"{self.base_url}/v1/extractions:run",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise ExtractorClientError(str(exc)) from exc
        return ExtractedTextArtifact.model_validate(response_payload)
