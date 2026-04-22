"""HTTP client wrapper for the classifier service."""

from __future__ import annotations

import json
from urllib import error, request

from doc_platform_contracts.classification import DocumentClassificationResult


class ClassifierClientError(Exception):
    """Raised when classifier requests fail."""


class ClassifierClient:
    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def run_classification_request(self, payload: dict) -> DocumentClassificationResult:
        http_request = request.Request(
            url=f"{self.base_url}/v1/classifications:run",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise ClassifierClientError(str(exc)) from exc
        return DocumentClassificationResult.model_validate(response_payload)
