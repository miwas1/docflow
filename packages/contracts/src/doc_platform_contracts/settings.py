"""Shared settings contracts used across all platform services."""

import json

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BasePlatformSettings(BaseSettings):
    """Shared environment contract for the platform foundation."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    postgres_dsn: str = Field(alias="POSTGRES_DSN")
    rabbitmq_url: str = Field(alias="RABBITMQ_URL")
    object_storage_endpoint: str = Field(alias="OBJECT_STORAGE_ENDPOINT")
    object_storage_bucket: str = Field(alias="OBJECT_STORAGE_BUCKET")
    object_storage_access_key: str = Field(alias="OBJECT_STORAGE_ACCESS_KEY")
    object_storage_secret_key: str = Field(alias="OBJECT_STORAGE_SECRET_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_key_header_name: str = Field(default="X-API-Key", alias="API_KEY_HEADER_NAME")
    api_keys_json: dict[str, str] = Field(default_factory=dict, alias="API_KEYS_JSON")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")

    @field_validator("api_keys_json", mode="before")
    @classmethod
    def parse_api_keys_json(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value)
        return value
