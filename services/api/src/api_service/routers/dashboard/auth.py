"""Dashboard auth routes: signup, login, logout."""

from pathlib import Path

from api_service.config import APISettings
from api_service.dependencies import (
    get_db_session,
    get_optional_current_user,
    get_settings_dependency,
)
from api_service.services.dashboard_auth import login_user, logout_user, signup_user
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")

_TEMPLATES_PATH = Path(__file__).resolve().parents[3] / "templates"
_SESSION_COOKIE = "session_id"


def _tmpl(name: str) -> str:
    """Read a template file as raw HTML."""
    return (_TEMPLATES_PATH / name).read_text(encoding="utf-8")


def _flash(
    response: RedirectResponse, message: str, level: str = "error"
) -> RedirectResponse:
    """Attach a flash-style cookie that templates consume once."""
    response.set_cookie(
        "_flash_msg", message, max_age=10, httponly=False, samesite="lax"
    )
    response.set_cookie(
        "_flash_level", level, max_age=10, httponly=False, samesite="lax"
    )
    return response


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


@router.get("/signup", response_class=HTMLResponse, include_in_schema=False)
def signup_page(
    user=Depends(get_optional_current_user),
) -> HTMLResponse:
    """Render the signup page (redirect to dashboard if already logged in)."""
    if user:
        return RedirectResponse("/dashboard/home", status_code=302)
    return HTMLResponse(_tmpl("dashboard/signup.html"))


@router.post("/signup", response_class=HTMLResponse, include_in_schema=False)
def handle_signup(
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Create a new account and redirect to login."""
    try:
        signup_user(
            session=db, email=email, password=password, display_name=display_name
        )
    except ValueError as exc:
        resp = RedirectResponse("/dashboard/signup", status_code=303)
        return _flash(resp, str(exc))
    resp = RedirectResponse("/dashboard/login", status_code=303)
    return _flash(resp, "Account created — please log in.", "success")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(
    user=Depends(get_optional_current_user),
) -> HTMLResponse:
    """Render the login page (redirect to dashboard if already logged in)."""
    if user:
        return RedirectResponse("/dashboard/home", status_code=302)
    return HTMLResponse(_tmpl("dashboard/login.html"))


@router.post("/login", response_class=HTMLResponse, include_in_schema=False)
def handle_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db_session),
    settings: APISettings = Depends(get_settings_dependency),
) -> RedirectResponse:
    """Authenticate and set a session cookie."""
    try:
        _user, token = login_user(
            session=db, email=email, password=password, settings=settings
        )
    except ValueError:
        resp = RedirectResponse("/dashboard/login", status_code=303)
        return _flash(resp, "Invalid email or password.")
    resp = RedirectResponse("/dashboard/home", status_code=303)
    resp.set_cookie(
        _SESSION_COOKIE,
        token,
        max_age=settings.session_expire_seconds,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production behind HTTPS
    )
    return resp


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post("/logout", include_in_schema=False)
def handle_logout(
    request: Request,
    db: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Clear the session and redirect to login."""
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        logout_user(session=db, session_token=token)
    resp = RedirectResponse("/dashboard/login", status_code=303)
    resp.delete_cookie(_SESSION_COOKIE)
    return resp
