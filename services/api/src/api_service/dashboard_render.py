"""Shared rendering utilities for dashboard pages."""

from api_service.templates_utils import TEMPLATES_PATH, get_template_text


def render_dashboard(
    content_template: str,
    *,
    page_title: str,
    active: str,
    user_name: str,
    **ctx: object,
) -> str:
    """Render a dashboard page by injecting content into the base layout.

    Args:
        content_template: Relative path under templates/ for the content fragment.
        page_title: Title shown in the topbar.
        active: Nav key that should be highlighted ('home', 'keys', 'webhooks', 'jobs').
        user_name: Displayed name of the logged-in user.
        **ctx: Additional substitution variables for the content template.
    """
    # Render inner content
    content_text = get_template_text(content_template)
    for key, value in ctx.items():
        content_text = content_text.replace(f"{{{{{key}}}}}", str(value))

    # Render base with injected content
    base_text = get_template_text("dashboard/_base.html")
    nav_keys = {"home", "keys", "webhooks", "jobs"}
    for nav_key in nav_keys:
        placeholder = f"{{{{active_{nav_key}}}}}"
        base_text = base_text.replace(
            placeholder, "active" if active == nav_key else ""
        )

    base_text = base_text.replace("{{page_title}}", page_title)
    base_text = base_text.replace("{{user_name}}", user_name)
    base_text = base_text.replace("{{page_content}}", content_text)
    return base_text
