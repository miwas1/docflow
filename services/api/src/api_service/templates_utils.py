"""Robust template path discovery for the API service."""

from pathlib import Path

import api_service

# Always resolve templates relative to the api_service package root
_PKG_PATH = Path(api_service.__file__).parent
TEMPLATES_PATH = _PKG_PATH / "templates"


def get_template_text(relative_path: str) -> str:
    """Read a template file's content from the templates directory."""
    target = TEMPLATES_PATH / relative_path
    return target.read_text(encoding="utf-8")
