"""Configuration for the extractor service."""

from functools import lru_cache

from pydantic import Field

from doc_platform_contracts.settings import BasePlatformSettings


class ExtractorSettings(BasePlatformSettings):
    host: str = Field(default="0.0.0.0", alias="EXTRACTOR_HOST")
    port: int = Field(default=8001, alias="EXTRACTOR_PORT")
    pdf_text_min_chars: int = Field(default=5, alias="PDF_TEXT_MIN_CHARS")


@lru_cache(maxsize=1)
def get_settings() -> ExtractorSettings:
    return ExtractorSettings()
