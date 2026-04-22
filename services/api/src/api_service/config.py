"""Configuration for the API service."""

from functools import lru_cache

from pydantic import Field

from doc_platform_contracts.settings import BasePlatformSettings


class APISettings(BasePlatformSettings):
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    api_key_header_name: str = Field(default="X-API-Key", alias="API_KEY_HEADER_NAME")
    api_keys_json: dict[str, str] = Field(default_factory=dict, alias="API_KEYS_JSON")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")
    input_signature_validation_enabled: bool = Field(default=True, alias="INPUT_SIGNATURE_VALIDATION_ENABLED")
    unsafe_input_reject_mismatch: bool = Field(default=True, alias="UNSAFE_INPUT_REJECT_MISMATCH")
    internal_service_token: str = Field(default="internal-secret", alias="INTERNAL_SERVICE_TOKEN")
    operator_bearer_token: str = Field(default="operator-secret", alias="OPERATOR_BEARER_TOKEN")
    operator_dashboard_enabled: bool = Field(default=True, alias="OPERATOR_DASHBOARD_ENABLED")


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    return APISettings()
