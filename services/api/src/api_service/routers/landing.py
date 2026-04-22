"""Landing page router — public, no auth required."""

from pathlib import Path

from api_service.templates_utils import get_template_text
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import api_service
_TEMPLATES_PATH = Path(api_service.__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_PATH))

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing_page() -> HTMLResponse:
    """Render the public landing page."""
    html = get_template_text("landing.html")
    return HTMLResponse(html)
