"""Internal API and outbound HTTP client for webhook delivery."""

from __future__ import annotations

import json
from urllib import error, request


class WebhookClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        internal_service_token: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.internal_service_token = internal_service_token
        self.timeout_seconds = timeout_seconds

    def fetch_dispatch_payload(self, job_id: str) -> dict:
        http_request = request.Request(
            url=f"{self.api_base_url}/internal/webhooks/jobs/{job_id}/dispatch",
            headers={"Authorization": f"Bearer {self.internal_service_token}"},
            method="GET",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise RuntimeError(str(exc)) from exc

    def record_delivery_outcome(self, job_id: str, delivery_id: str, payload: dict) -> dict:
        http_request = request.Request(
            url=f"{self.api_base_url}/internal/webhooks/jobs/{job_id}/deliveries/{delivery_id}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.internal_service_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.HTTPError, error.URLError) as exc:
            raise RuntimeError(str(exc)) from exc

    def deliver(self, payload: dict, target_url: str, signature: str) -> dict:
        http_request = request.Request(
            url=target_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-DocPlatform-Signature": signature,
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return {"status_code": response.status}
        except error.HTTPError as exc:
            return {"status_code": exc.code}
        except (TimeoutError, error.URLError) as exc:
            raise TimeoutError(str(exc)) from exc
