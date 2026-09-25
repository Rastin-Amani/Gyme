import os
from fastapi.templating import Jinja2Templates
import jdatetime
from datetime import datetime

from app.i18n import _, get_locale, locale_proxy, ngettext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# i18n globals — `_`/`ngettext` read the request-scoped locale (contextvar,
# set by middleware); `locale` exposes metadata (code/direction/native_name).
templates.env.globals["_"] = _
templates.env.globals["ngettext"] = ngettext
templates.env.globals["locale"] = locale_proxy


# Define the filter
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


def to_jalali_year(date_str):
    parsed = _parse_dt(date_str)
    if not parsed:
        return date_str or ""
    # Locale-aware: Jalali only for fa; others use Gregorian year
    if get_locale().code == "fa":
        return jdatetime.datetime.fromgregorian(datetime=parsed).year
    return parsed.year


def to_jalali_date(date_str):
    parsed = _parse_dt(date_str)
    if not parsed:
        return date_str or ""
    if get_locale().code == "fa":
        return jdatetime.datetime.fromgregorian(datetime=parsed).strftime("%Y/%m/%d")
    # Gregorian fallback for LTR locales (medium format via Babel if available)
    try:
        from babel.dates import format_date

        return format_date(parsed, format="medium", locale=get_locale().code.replace("-", "_"))
    except Exception:
        return parsed.strftime("%Y-%m-%d")


# Register the filters (names kept for template compatibility; behavior is locale-aware)
templates.env.filters["jalali_year"] = to_jalali_year
templates.env.filters["jalali_date"] = to_jalali_date
# Alias for clarity in new templates
templates.env.filters["loc_year"] = to_jalali_year
templates.env.filters["loc_date"] = to_jalali_date
