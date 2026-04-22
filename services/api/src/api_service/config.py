"""Configuration for the API service."""

from functools import lru_cache

from doc_platform_contracts.settings import BasePlatformSettings
from pydantic import Field


class APISettings(BasePlatformSettings):
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    api_key_header_name: str = Field(default="X-API-Key", alias="API_KEY_HEADER_NAME")
    api_keys_json: dict[str, str] = Field(default_factory=dict, alias="API_KEYS_JSON")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")
    input_signature_validation_enabled: bool = Field(
        default=True, alias="INPUT_SIGNATURE_VALIDATION_ENABLED"
    )
    unsafe_input_reject_mismatch: bool = Field(
        default=True, alias="UNSAFE_INPUT_REJECT_MISMATCH"
    )
    internal_service_token: str = Field(
        default="internal-secret", alias="INTERNAL_SERVICE_TOKEN"
    )
    operator_bearer_token: str = Field(
        default="operator-secret", alias="OPERATOR_BEARER_TOKEN"
    )
    operator_dashboard_enabled: bool = Field(
        default=True, alias="OPERATOR_DASHBOARD_ENABLED"
    )
    session_secret_key: str = Field(
        default="dev-session-secret-change-me", alias="SESSION_SECRET_KEY"
    )
    session_expire_seconds: int = Field(
        default=2_592_000, alias="SESSION_EXPIRE_SECONDS"
    )
    # ---------------------------------------------------------------------------
    # Synchronous fast-path settings
    # Eligible types: text/plain, application/json, application/pdf, docx.
    # Images (png, jpeg) always use the async OCR path.
    # If the sync call exceeds the timeout, the job falls back to the async queue.
    # ---------------------------------------------------------------------------
    sync_classification_enabled: bool = Field(
        default=True, alias="SYNC_CLASSIFICATION_ENABLED"
    )
    sync_classification_timeout_seconds: float = Field(
        default=20.0, alias="SYNC_CLASSIFICATION_TIMEOUT_SECONDS"
    )
    extractor_base_url: str = Field(
        default="http://localhost:8001", alias="EXTRACTOR_BASE_URL"
    )
    classifier_base_url: str = Field(
        default="http://localhost:8002", alias="CLASSIFIER_BASE_URL"
    )


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    return APISettings()
