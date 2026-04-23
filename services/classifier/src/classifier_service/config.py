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
    classifier_strict_taxonomy_validation: bool = Field(
        default=True,
        alias="CLASSIFIER_STRICT_TAXONOMY_VALIDATION",
        description="Fail fast if the loaded model labels do not match the configured taxonomy.",
    )
    classifier_keyword_hints_enabled: bool = Field(
        default=True,
        alias="CLASSIFIER_KEYWORD_HINTS_ENABLED",
        description="Apply lightweight keyword-based logit boosts when the model is uncertain.",
    )
    classifier_keyword_hints_margin: float = Field(
        default=0.05,
        alias="CLASSIFIER_KEYWORD_HINTS_MARGIN",
        description="Only apply keyword hints when top-1 minus top-2 probability is below this margin.",
    )
    classifier_keyword_hints_boost: float = Field(
        default=2.0,
        alias="CLASSIFIER_KEYWORD_HINTS_BOOST",
        description="Logit boost applied per keyword hit (capped by CLASSIFIER_KEYWORD_HINTS_MAX_BOOST).",
    )
    classifier_keyword_hints_max_boost: float = Field(
        default=6.0,
        alias="CLASSIFIER_KEYWORD_HINTS_MAX_BOOST",
        description="Maximum total logit boost applied to a single label from keyword hints.",
    )
    classifier_keyword_hints_min_hits: int = Field(
        default=2,
        alias="CLASSIFIER_KEYWORD_HINTS_MIN_HITS",
        description="Minimum number of keyword hits required before applying any boost to a label.",
    )
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
