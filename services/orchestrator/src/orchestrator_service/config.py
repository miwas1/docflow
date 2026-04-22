"""Configuration for the orchestrator service."""

from functools import lru_cache
import json

from pydantic import Field
from pydantic import field_validator

from doc_platform_contracts.settings import BasePlatformSettings


class OrchestratorSettings(BasePlatformSettings):
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    internal_service_token: str = Field(default="internal-secret", alias="INTERNAL_SERVICE_TOKEN")
    extractor_base_url: str = Field(default="http://localhost:8001", alias="EXTRACTOR_BASE_URL")
    extractor_timeout_seconds: float = Field(default=10.0, alias="EXTRACTOR_TIMEOUT_SECONDS")
    extract_max_attempts: int = Field(default=3, alias="EXTRACT_MAX_ATTEMPTS")
    extract_retry_backoff_seconds: list[int] = Field(default_factory=lambda: [30, 120], alias="EXTRACT_RETRY_BACKOFF_SECONDS_JSON")
    classifier_base_url: str = Field(default="http://localhost:8002", alias="CLASSIFIER_BASE_URL")
    classifier_timeout_seconds: float = Field(default=10.0, alias="CLASSIFIER_TIMEOUT_SECONDS")
    classify_max_attempts: int = Field(default=3, alias="CLASSIFY_MAX_ATTEMPTS")
    classify_retry_backoff_seconds: list[int] = Field(default_factory=lambda: [30, 120], alias="CLASSIFY_RETRY_BACKOFF_SECONDS_JSON")
    webhook_timeout_seconds: float = Field(default=5.0, alias="WEBHOOK_TIMEOUT_SECONDS")
    webhook_max_attempts: int = Field(default=4, alias="WEBHOOK_MAX_ATTEMPTS")
    webhook_retry_backoff_seconds: list[int] = Field(default_factory=lambda: [30, 120, 600], alias="WEBHOOK_RETRY_BACKOFF_SECONDS_JSON")

    @field_validator(
        "extract_retry_backoff_seconds",
        "classify_retry_backoff_seconds",
        "webhook_retry_backoff_seconds",
        mode="before",
    )
    @classmethod
    def parse_backoff_json(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value)
        return value


@lru_cache(maxsize=1)
def get_settings() -> OrchestratorSettings:
    return OrchestratorSettings()
