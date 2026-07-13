from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from ..templates import templates
from app.utils import hx_toast
from app.services.trainee import get_trainee_by_id, update_trainee
from app.services.progress_logs import create_progress_log
from typing import List
import json, os, uuid

router = APIRouter(tags=["Progress Logs"])


# ──────────────────────────────────────────────
#  GET /progress-log/new/{trainee_id}  –  Show Form
# ──────────────────────────────────────────────
@router.get("/progress-log/new/{trainee_id}")
async def new_progress_log_form(request: Request, trainee_id: str):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user

    # Only coaches/owners can create logs
    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    try:
        trainee = get_trainee_by_id(pb, tenant.id, trainee_id)
    except Exception:
        return RedirectResponse(url="/trainees")

    return templates.TemplateResponse(
        request=request,
        name="forms/progress_logs.html",
        context={"title": "ثبت ارزیابی اولیه", "tenant": tenant, "user": user, "trainee": trainee},
    )


# ──────────────────────────────────────────────
#  POST /trainees/{trainee_id}/progress-log  –  Save Log
# ──────────────────────────────────────────────
@router.post("/trainees/{trainee_id}/progress-log")
async def save_progress_log(
    request: Request,
    trainee_id: str,
    # 🟢 Accept everything as strings first to prevent 422 crashes!
    height: str = Form(""),
    weight: str = Form(""),
    chest: str = Form(""),
    waist: str = Form(""),
    hip: str = Form(""),
    arms: str = Form(""),
    notes: str = Form(""),
    bmi: str = Form(""),
    bfp: str = Form(""),
    bmr: str = Form(""),
    tdee: str = Form(""),
    lbm: str = Form(""),
    whr: str = Form(""),
    progress_photos: List[UploadFile] = File(None),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id

        # 🟢 Helper function to safely convert strings to floats
        def safe_float(val: str):
            try:
                return float(val) if val and val.strip() else None
            except ValueError:
                return None

        # Safely parse the required ones, fallback to 0 if they bypassed HTML validation
        parsed_height = safe_float(height) or 0.0
        parsed_weight = safe_float(weight) or 0.0

        log_data = {
            "tenant": tenant_id,
            "trainee": trainee_id,
            "height": parsed_height,
            "weight": parsed_weight,
            "chest": safe_float(chest),
            "waist": safe_float(waist),
            "hip": safe_float(hip),
            "arms": safe_float(arms),
            "notes": notes,
            "bmi": safe_float(bmi),
            "bfp": safe_float(bfp),
            "bmr": safe_float(bmr),
            "tdee": safe_float(tdee),
            "lbm": safe_float(lbm),
            "whr": safe_float(whr),
        }

        # 🖼️ Validate + collect files for PocketBase
        MAX_FILES = 5
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        VALID_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

        file_uploads = None
        if progress_photos:
            valid_files = [f for f in progress_photos if f.filename]
            if len(valid_files) > MAX_FILES:
                raise HTTPException(status_code=400, detail=f"حداکثر {MAX_FILES} فایل مجاز است")
            file_uploads = []
            for photo in valid_files:
                if photo.content_type not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فرمت {photo.filename} مجاز نیست (JPEG, PNG, WebP, GIF)",
                    )
                contents = await photo.read()
                if len(contents) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400, detail=f"{photo.filename} بزرگتر از ۵MB است"
                    )
                file_uploads.append((photo.filename, contents, photo.content_type))

        # 1. Save the new log
        create_progress_log(pb, log_data, file_uploads=file_uploads)

        # 2. Update the Trainee's main profile
        update_trainee(pb, trainee_id, {"height": parsed_height, "weight": parsed_weight})

        # 3. Success! Delayed Redirect to Trainee Details
        headers = hx_toast("ارزیابی با موفقیت ثبت شد. در حال انتقال...", "success")

        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["delayed-redirect"] = {"url": f"/trainees/{trainee_id}"}
        headers["HX-Trigger"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        print(f"🔥 Server Crash in save_progress_log: {e}")
        headers = hx_toast("خطا در ثبت اطلاعات ارزیابی. لطفا مقادیر را بررسی کنید.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)
