from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from app.utils import hx_toast  # Using your awesome toast utility!
from ..templates import templates
from app.security import validate_phone, validate_length
from app.i18n import _
import time
from collections import defaultdict

_lead_attempts = defaultdict(list)
LEAD_MAX = 5
LEAD_WINDOW = 3600

router = APIRouter(tags=["Marketing"])


@router.get("/")
def slash(request: Request):
    tenant = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="pages/marketing/slash.html",
        context={"title": _("اپلیکیشن اختصاصی باشگاه شما"), "tenant": tenant},
    )


@router.post("/lead/submit")
def submit_lead(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    coaches_count: str = Form(...),
    trainees_count: str = Form(...),
    gym_name: str = Form(None),
    note: str = Form(None),
):
    pb = getattr(request.state, "pb", None)
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _lead_attempts[client_ip] = [t for t in _lead_attempts[client_ip] if now - t < LEAD_WINDOW]
    if len(_lead_attempts[client_ip]) >= LEAD_MAX:
        headers = hx_toast(_("تعداد درخواست‌ها بیش از حد مجاز است"), "error")
        return HTMLResponse(status_code=429, headers=headers)
    _lead_attempts[client_ip].append(now)

    # Input validation & sanitization
    try:
        name = validate_length(name, "name", 2, 80)
        phone = validate_phone(phone)
        if not phone:
            raise ValueError("Invalid phone")
        position = validate_length(position, "position", 1, 50) or position[:50]
        coaches_count = str(coaches_count)[:20]
        trainees_count = str(trainees_count)[:20]
        if gym_name:
            gym_name = validate_length(gym_name, "gym_name", 0, 80)
        if note:
            note = validate_length(note, "note", 0, 500)
    except ValueError as ve:
        headers = hx_toast(str(ve), "error")
        return HTMLResponse(status_code=400, headers=headers)

    try:
        payload = {
            "name": name,
            "phone": phone,
            "position": str(position)[:50],
            "coaches_count": str(coaches_count)[:20],
            "trainees_count": str(trainees_count)[:20],
            "gym_name": gym_name[:80] if gym_name else None,
            "note": note[:500] if note else None,
        }

        pb.collection("leads").create(payload)

        headers = hx_toast(_("ممنون {name}! تا ۲۴ ساعت آتی با شما تماس می‌گیریم.").format(name=name), "success")

        # 🟢 FIXED: Swap the header key so it fires immediately without waiting for a DOM swap!
        trigger_data = headers.pop("HX-Trigger-After-Swap")
        headers["HX-Trigger"] = trigger_data

        return HTMLResponse(status_code=204, headers=headers)

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("lead.submit_failed", error=str(e), name=name, phone=phone)
        headers = hx_toast(_("مشکلی پیش اومد. لطفا دوباره تلاش کنید."), "error")

        # We do the same here just to be safe, since the form has hx-swap="none"
        trigger_data = headers.pop("HX-Trigger-After-Swap", None)
        if trigger_data:
            headers["HX-Trigger"] = trigger_data

        return HTMLResponse(status_code=200, headers=headers)
