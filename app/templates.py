import os
from fastapi.templating import Jinja2Templates
import jdatetime
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "templates")
)

# Define the filter
def to_jalali_year(date_str):
    if not date_str:
        return ""
    try:
        # PocketBase format is usually %Y-%m-%d %H:%M:%S.%fZ
        gregorian_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%fZ")
        jalali_dt = jdatetime.datetime.fromgregorian(datetime=gregorian_dt)
        return jalali_dt.year
    except (ValueError, TypeError):
        return date_str  # Return original if parsing fails

# Register the filter
templates.env.filters["jalali_year"] = to_jalali_year