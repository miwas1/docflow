"""Configuration for the classifier service."""

import json
from functools import lru_cache

from pydantic import Field
from pydantic import field_validator

from doc_platform_contracts.settings import BasePlatformSettings


DEFAULT_LABEL_DESCRIPTIONS: dict[str, str] = {}


class ClassifierSettings(BasePlatformSettings):
    host: str = Field(default="0.0.0.0", alias="CLASSIFIER_HOST")
    port: int = Field(default=8002, alias="CLASSIFIER_PORT")
    classifier_model_name: str = Field(default="/models/finetuned/current", alias="CLASSIFIER_MODEL_NAME")
    classifier_model_version: str = Field(default="modernbert-finetuned-local", alias="CLASSIFIER_MODEL_VERSION")
    classifier_model_provider: str = Field(default="huggingface", alias="CLASSIFIER_MODEL_PROVIDER")
    classifier_model_cache_dir: str = Field(default="/models/huggingface", alias="CLASSIFIER_MODEL_CACHE_DIR")
    classifier_model_local_files_only: bool = Field(default=True, alias="CLASSIFIER_MODEL_LOCAL_FILES_ONLY")
    classifier_device: str = Field(default="cpu", alias="CLASSIFIER_DEVICE")
    classifier_max_length: int = Field(default=1024, alias="CLASSIFIER_MAX_LENGTH")
    classifier_confidence_threshold: float = Field(default=0.6, alias="CLASSIFIER_CONFIDENCE_THRESHOLD")
    classifier_label_descriptions: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_LABEL_DESCRIPTIONS),
        alias="CLASSIFIER_LABEL_DESCRIPTIONS_JSON",
    )

    @field_validator("classifier_label_descriptions", mode="before")
    @classmethod
    def parse_classifier_label_descriptions(cls, value: object) -> object:
        if isinstance(value, str):
            return json.loads(value)
        return value


@lru_cache(maxsize=1)
def get_settings() -> ClassifierSettings:
    return ClassifierSettings()
