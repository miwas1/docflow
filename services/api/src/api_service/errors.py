"""Structured API errors for the external ingestion contract."""


class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details

    def to_payload(self) -> dict:
        payload = {"error_code": self.error_code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload
