"""Configuration for the classifier service."""

from functools import lru_cache

from pydantic import Field

from doc_platform_contracts.settings import BasePlatformSettings


class ClassifierSettings(BasePlatformSettings):
    host: str = Field(default="0.0.0.0", alias="CLASSIFIER_HOST")
    port: int = Field(default=8002, alias="CLASSIFIER_PORT")
    classifier_model_name: str = Field(default="baseline-keyword", alias="CLASSIFIER_MODEL_NAME")
    classifier_model_version: str = Field(default="0.1.0", alias="CLASSIFIER_MODEL_VERSION")
    classifier_confidence_threshold: float = Field(default=0.6, alias="CLASSIFIER_CONFIDENCE_THRESHOLD")


@lru_cache(maxsize=1)
def get_settings() -> ClassifierSettings:
    return ClassifierSettings()
