import os
from datetime import datetime

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.i18n import _, get_locale, locale_proxy, ngettext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# i18n globals — `_`/`ngettext` read the request-scoped locale (contextvar,
# set by middleware); `locale` exposes metadata (code/direction/native_name).
templates.env.globals["_"] = _
templates.env.globals["ngettext"] = ngettext
templates.env.globals["locale"] = locale_proxy


def _parse_dt(date_str):
    """Normalize PB timestamps (str or datetime) to a naive datetime; None on failure."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        value = date_str
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value
    try:
        clean = str(date_str).replace("Z", "").strip().split("+")[0]
        if "." in clean:
            return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S.%f")
        return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.warning("date_parse_error", raw_string=date_str)
        return None


def to_locale_year(date_str):
    """Gregorian year (LTR/Gregorian rendering)."""
    parsed = _parse_dt(date_str)
    if not parsed:
        return date_str or ""
    return parsed.year


def to_locale_date(date_str):
    """Gregorian date (medium format via Babel when available, else ISO)."""
    parsed = _parse_dt(date_str)
    if not parsed:
        return date_str or ""
    try:
        from babel.dates import format_date

        return format_date(parsed, format="medium", locale=get_locale().code.replace("-", "_"))
    except Exception:
        return parsed.strftime("%Y-%m-%d")


# Register the filters (names kept for template compatibility; always Gregorian)
templates.env.filters["jalali_year"] = to_locale_year
templates.env.filters["jalali_date"] = to_locale_date
# Aliases for clarity in templates
templates.env.filters["loc_year"] = to_locale_year
templates.env.filters["loc_date"] = to_locale_date


# --- Icons -----------------------------------------------------------------
# One outline set for the whole app: every glyph shares the same 24x24 grid,
# stroke width and caps, so nothing looks hand-drawn or out of place. Paths are
# Heroicons v2 (24x24 outline), plus a dumbbell and an apple drawn on the same
# grid. Templates call {{ icon("name", "size-5") }}.
_ICONS = {
    "dashboard": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
    "plans": "M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25",
    "users": "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    "profile": "M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "today": "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "logout": "M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9",
    "chevron-left": "M15.75 19.5 8.25 12l7.5-7.5",
    "chevron-right": "m8.25 4.5 7.5 7.5-7.5 7.5",
    "plus": "M12 4.5v15m7.5-7.5h-15",
    "arrow-right": "M13.5 4.5 21 12l-7.5 7.5M21 12H3",
    "pencil": "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125",
    "camera": "M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316ZM16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z",
    "dumbbell": "M6.75 6.75v10.5M17.25 6.75v10.5M3.75 9v6M20.25 9v6M6.75 12h10.5M10.5 8.25v7.5M13.5 8.25v7.5",
    "apple": "M12 7.5c-1.1-1.4-2.8-2.1-4.4-1.6C5.6 6.5 4.5 8.3 4.5 10.4c0 4.3 3.4 9.1 5.4 9.1 1 0 1.5-.5 2.1-.5s1.1.5 2.1.5c2 0 5.4-4.8 5.4-9.1 0-2.1-1.1-3.9-3.1-4.5-1.6-.5-3.3.2-4.4 1.6ZM12 7.5c0-1.6.8-2.9 2.2-3.5",
    "tag": "M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3ZM6 6h.008v.008H6V6Z",
    "eye": "M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "eye-slash": "M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88",
    "document": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "check": "m4.5 12.75 6 6 9-13.5",
    "info": "m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z",
    "success": "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "error": "m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "warning": "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
    "language": "m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802",
}


def icon(name, cls="size-5"):
    """Render one icon from the shared set (unknown names render nothing)."""
    d = _ICONS.get(name)
    if not d:
        return Markup("")
    return Markup(
        '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"'
        f' stroke-width="1.7" stroke="currentColor" class="{cls}" aria-hidden="true">'
        f'<path stroke-linecap="round" stroke-linejoin="round" d="{d}" /></svg>'
    )


templates.env.globals["icon"] = icon
