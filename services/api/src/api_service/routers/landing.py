"""Landing page router — public, no auth required."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_PATH = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_PATH))

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing_page() -> HTMLResponse:
    """Render the public landing page."""
    html = (Path(_TEMPLATES_PATH) / "landing.html").read_text(encoding="utf-8")
    return HTMLResponse(html)
