import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.responses import HTMLResponse

from app.i18n import _


def _toast_payload(message: str, type: str, duration: int | None = None) -> dict:
    event_data = {"show-toast": {"message": message, "type": type}}
    if duration:
        event_data["show-toast"]["duration"] = duration
    return event_data


def hx_toast(message: str, type: str = "info", duration: int | None = None) -> dict:
    # 🟢 FIXED: Changed from 'HX-Trigger' to 'HX-Trigger-After-Swap'
    # This guarantees HTMX waits for the new page to load before popping the toast!
    return {"HX-Trigger-After-Swap": json.dumps(_toast_payload(message, type, duration))}


def hx_toast_now(message: str, type: str = "info", duration: int | None = None) -> dict:
    """Toast for responses that must not swap (4xx errors, disallowed actions)."""
    return {"HX-Trigger": json.dumps(_toast_payload(message, type, duration))}


def deny_trainee(user):
    """Guard for staff-only mutations: trainees only advance their own plans."""
    if getattr(user, "role", None) == "trainee":
        return HTMLResponse(status_code=403, headers=hx_toast_now(_("Access denied"), "error"))
    return None


def pmap(fn, items, workers: int = 8):
    """Bounded parallel map, results in input order.

    PocketBase calls are independent I/O; running them serially multiplies
    latency by round-trips (one remote RTT each). Order and exceptions are
    preserved, concurrency stays bounded so PB is never hammered.
    """
    items = list(items)
    if len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(fn, items))
