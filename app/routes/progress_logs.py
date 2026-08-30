from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from ..templates import templates
from app.utils import hx_toast
from app.services.trainee import get_trainee_by_id, update_trainee
from app.services.progress_logs import (
    create_progress_log,
    get_progress_log_by_id,
    update_progress_log,
    get_progress_log_with_tenant_check,
)
from typing import List
import json, os, uuid, re

router = APIRouter(tags=["Progress Logs"])


# ──────────────────────────────────────────────
#  GET /progress-log/new/{trainee_id}  –  Show Form
# ──────────────────────────────────────────────
@router.get("/progress-log/new/{trainee_id}")
def new_progress_log_form(request: Request, trainee_id: str):
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
    tdee: str = Form(""),
    lbm: str = Form(""),
    whr: str = Form(""),
    progress_photos: List[UploadFile] = File(None),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id
        user = request.state.user
        if getattr(user, "role", None) == "trainee":
            return HTMLResponse(content="", status_code=403, headers=hx_toast("دسترسی غیرمجاز","error"))
        # Verify trainee belongs to tenant
        try:
            get_trainee_by_id(pb, tenant_id, trainee_id)
        except Exception:
            return HTMLResponse(content="", status_code=404, headers=hx_toast("شاگرد یافت نشد","error"))

        # 🟢 Helper function to safely convert strings to floats with bounds
        def safe_float(val: str, min_v=None, max_v=None):
            try:
                f = float(val) if val and val.strip() else None
                if f is not None:
                    if min_v is not None and f < min_v:
                        return min_v
                    if max_v is not None and f > max_v:
                        return max_v
                return f
            except ValueError:
                return None

        # Safely parse the required ones, fallback to 0 if they bypassed HTML validation
        parsed_height = safe_float(height, 30, 300) or 0.0
        parsed_weight = safe_float(weight, 20, 500) or 0.0
        if notes:
            notes = str(notes)[:1000]

        log_data = {
            "tenant": tenant_id,
            "trainee": trainee_id,
            "height": parsed_height,
            "weight": parsed_weight,
            "chest": safe_float(chest, 20, 300),
            "waist": safe_float(waist, 20, 300),
            "hip": safe_float(hip, 20, 300),
            "arms": safe_float(arms, 10, 100),
            "notes": notes,
            "bmi": safe_float(bmi, 5, 100),
            "bfp": safe_float(bfp, 1, 80),
            "bmr": safe_float(bmr, 500, 10000),
            "tdee": safe_float(tdee, 500, 15000),
            "lbm": safe_float(lbm, 10, 300),
            "whr": safe_float(whr, 0.1, 3),
        }

        # 🖼️ Validate + collect files for PocketBase - harden with extension + magic + size before reading fully
        MAX_FILES = 5
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        VALID_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        # Magic bytes for image types
        MAGIC = {
            b"\xff\xd8\xff": "image/jpeg",
            b"\x89PNG": "image/png",
            b"RIFF": "image/webp",  # simplified
            b"GIF8": "image/gif",
        }

        file_uploads = None
        if progress_photos:
            valid_files = [f for f in progress_photos if f.filename and f.filename.strip()]
            if len(valid_files) > MAX_FILES:
                raise HTTPException(status_code=400, detail=f"حداکثر {MAX_FILES} فایل مجاز است")
            file_uploads = []
            for photo in valid_files:
                # Validate extension
                fname = str(photo.filename)[:100]
                # Prevent path traversal
                if "/" in fname or "\\" in fname or ".." in fname:
                    raise HTTPException(status_code=400, detail="نام فایل نامعتبر")
                ext = os.path.splitext(fname)[1].lower()
                if ext not in VALID_EXTS:
                    raise HTTPException(status_code=400, detail=f"پسوند {fname} مجاز نیست")
                if photo.content_type not in VALID_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فرمت {photo.filename} مجاز نیست (JPEG, PNG, WebP, GIF)",
                    )
                # Read with size limit - stream check
                contents = await photo.read()
                if len(contents) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400, detail=f"{photo.filename} بزرگتر از ۵MB است"
                    )
                if len(contents) < 10:
                    raise HTTPException(status_code=400, detail="فایل خراب است")
                # Magic check (basic)
                head = contents[:4]
                is_image = any(head.startswith(m) for m in MAGIC)
                # For webp, also check
                if not is_image and photo.content_type == "image/webp":
                    # allow, as RIFF check above
                    if not contents[:4] == b"RIFF":
                        raise HTTPException(status_code=400, detail="فایل تصویری نامعتبر")
                elif not is_image and photo.content_type != "image/webp":
                    # Require magic for others
                    if not any(contents.startswith(m) for m in [b"\xff\xd8\xff", b"\x89PNG", b"GIF8"]):
                        raise HTTPException(status_code=400, detail="فایل تصویری نامعتبر")
                # Sanitize filename
                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", fname)
                file_uploads.append((safe_name, contents, photo.content_type))

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
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("progress_log.create_failed", error=str(e), trainee_id=trainee_id)
        headers = hx_toast("خطا در ثبت اطلاعات ارزیابی. لطفا مقادیر را بررسی کنید.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)


# ──────────────────────────────────────────────
#  GET /progress-log/{log_id}/edit  –  Edit Form
# ──────────────────────────────────────────────
@router.get("/progress-log/{log_id}/edit")
def edit_progress_log_form(request: Request, log_id: str):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user

    # Only coaches/owners can edit logs
    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    try:
        log = get_progress_log_with_tenant_check(pb, tenant.id, log_id)
        trainee = get_trainee_by_id(pb, tenant.id, log.trainee)
    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("progress_log.fetch_failed", error=str(e), log_id=log_id)
        headers = hx_toast("خطا در بارگذاری اطلاعات ارزیابی.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)

    return templates.TemplateResponse(
        request=request,
        name="modals/progress_log_edit.html",
        context={
            "title": "ویرایش ارزیابی",
            "tenant": tenant,
            "user": user,
            "trainee": trainee,
            "log": log,
        },
    )


# ──────────────────────────────────────────────
#  POST /progress-log/{log_id}  –  Update Log
# ──────────────────────────────────────────────
@router.post("/progress-log/{log_id}")
async def save_progress_log_edit(
    request: Request,
    log_id: str,
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
        user = request.state.user
        if getattr(user, "role", None) == "trainee":
            return HTMLResponse(content="", status_code=403, headers=hx_toast("دسترسی غیرمجاز","error"))
        # Verify log belongs to tenant
        try:
            existing_log = get_progress_log_with_tenant_check(pb, tenant_id, log_id)
        except Exception:
            return HTMLResponse(content="", status_code=404, headers=hx_toast("ارزیابی یافت نشد","error"))

        # 🟢 Helper function to safely convert strings to floats with bounds
        def safe_float(val: str, min_v=None, max_v=None):
            try:
                f = float(val) if val and val.strip() else None
                if f is not None:
                    if min_v is not None and f < min_v:
                        return min_v
                    if max_v is not None and f > max_v:
                        return max_v
                return f
            except ValueError:
                return None

        # Safely parse the required ones, fallback to 0 if they bypassed HTML validation
        parsed_height = safe_float(height, 30, 300) or 0.0
        parsed_weight = safe_float(weight, 20, 500) or 0.0
        if notes:
            notes = str(notes)[:1000]

        log_data = {
            "tenant": tenant_id,
            "height": parsed_height,
            "weight": parsed_weight,
            "chest": safe_float(chest, 20, 300),
            "waist": safe_float(waist, 20, 300),
            "hip": safe_float(hip, 20, 300),
            "arms": safe_float(arms, 10, 100),
            "notes": notes,
            "bmi": safe_float(bmi, 5, 100),
            "bfp": safe_float(bfp, 1, 80),
            "bmr": safe_float(bmr, 500, 10000),
            "tdee": safe_float(tdee, 500, 15000),
            "lbm": safe_float(lbm, 10, 300),
            "whr": safe_float(whr, 0.1, 3),
        }

        # 🖼️ Validate + collect files for PocketBase - harden
        MAX_FILES = 5
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        VALID_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

        file_uploads = None
        if progress_photos:
            valid_files = [f for f in progress_photos if f.filename and f.filename.strip()]
            if len(valid_files) > MAX_FILES:
                raise HTTPException(status_code=400, detail=f"حداکثر {MAX_FILES} فایل مجاز است")
            file_uploads = []
            for photo in valid_files:
                fname = str(photo.filename)[:100]
                if "/" in fname or "\\" in fname or ".." in fname:
                    raise HTTPException(status_code=400, detail="نام فایل نامعتبر")
                ext = os.path.splitext(fname)[1].lower()
                if ext not in VALID_EXTS:
                    raise HTTPException(status_code=400, detail=f"پسوند {fname} مجاز نیست")
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
                if len(contents) < 10:
                    raise HTTPException(status_code=400, detail="فایل خراب است")
                head = contents[:4]
                if not any(head.startswith(m) for m in [b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF"]):
                    raise HTTPException(status_code=400, detail="فایل تصویری نامعتبر")
                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", fname)
                file_uploads.append((safe_name, contents, photo.content_type))

        # 1. Update the log
        update_progress_log(pb, log_id, log_data, file_uploads=file_uploads)

        # 2. Update the Trainee's main profile if height/weight changed
        log = get_progress_log_by_id(pb, log_id)
        # Double check tenant after fetch
        if str(getattr(log, "tenant", tenant_id)) != str(tenant_id):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        update_trainee(pb, log.trainee, {"height": parsed_height, "weight": parsed_weight})

        # 3. Success! Close modal and refresh
        headers = hx_toast("ارزیابی با موفقیت به‌روزرسانی شد.", "success")

        trigger_dict = json.loads(headers.get("HX-Trigger-After-Swap", "{}"))
        trigger_dict["closeModal"] = True
        trigger_dict["performListRefresh"] = True
        headers["HX-Trigger-After-Swap"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("progress_log.update_failed", error=str(e), log_id=log_id)
        headers = hx_toast(
            "خطا در به‌روزرسانی اطلاعات ارزیابی. لطفا مقادیر را بررسی کنید.", "error"
        )
        return HTMLResponse(content="", status_code=200, headers=headers)
