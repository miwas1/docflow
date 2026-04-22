"""Internal API client for reporting pipeline stage completions back to the API service."""

from __future__ import annotations

import json
from urllib import error, request


class PipelineClientError(Exception):
    """Raised when a pipeline callback to the API service fails."""


class PipelineClient:
    """HTTP client that calls the API service's internal pipeline endpoints.

    The orchestrator does not own the database; all state mutations (job status,
    artifact persistence, classification runs) are delegated back to the API service
    through these endpoints so the API remains the single source of truth.
    """

    def __init__(
        self,
        *,
        api_base_url: str,
        internal_service_token: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialise the client with API coordinates and credentials.

        Args:
            api_base_url: Base URL of the API service (e.g. ``http://api:8000``).
            internal_service_token: Bearer token accepted by internal endpoints.
            timeout_seconds: Per-request HTTP timeout.
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.internal_service_token = internal_service_token
        self.timeout_seconds = timeout_seconds

    def _auth_headers(self) -> dict[str, str]:
        """Return the Authorization header dict for internal service calls."""
        return {
            "Authorization": f"Bearer {self.internal_service_token}",
            "Content-Type": "application/json",
        }

    def record_extraction_complete(self, job_id: str, payload: dict) -> dict:
        """Persist an extraction result and advance the job stage in the API.

        Args:
            job_id: The job whose extraction just completed.
            payload: Serialised ``ExtractedTextArtifact`` dict.

        Returns:
            API response body (includes ``extracted_text_artifact_id``).

        Raises:
            PipelineClientError: On any HTTP or network failure.
        """
        http_request = request.Request(
            url=f"{self.api_base_url}/internal/pipeline/jobs/{job_id}/extraction-complete",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._auth_headers(),
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise PipelineClientError(str(exc)) from exc

    def record_classification_complete(self, job_id: str, payload: dict) -> dict:
        """Persist a classification result and mark the job completed in the API.

        Args:
            job_id: The job whose classification just completed.
            payload: Serialised ``DocumentClassificationResult`` dict.

        Returns:
            API response body.

        Raises:
            PipelineClientError: On any HTTP or network failure.
        """
        http_request = request.Request(
            url=f"{self.api_base_url}/internal/pipeline/jobs/{job_id}/classification-complete",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._auth_headers(),
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise PipelineClientError(str(exc)) from exc
