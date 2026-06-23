from fastapi import APIRouter, Request, Form, Query
from app.services.trainee import create_trainee, list_trainees, get_trainee_by_id, update_trainee
from app.services.auth import create_user, update_user
from ..templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.plan import get_plans_by_trainee
from app.services.progress_logs import get_progress_logs_by_trainee
import json
from app.utils import hx_toast

router = APIRouter(tags=["Trainees Management"])


# ──────────────────────────────────────────────
#  GET Requests
# ──────────────────────────────────────────────
@router.get("/trainees")
async def trainees_list(request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees(pb, tenant)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
            "title": "لیست شاگردان",
            "tenant": tenant_name,
            "user": user,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
        },
    )


@router.get("/trainees/search")
async def search_trainees(request: Request, query: str = ""):
    """Search trainees by name, phone, or email"""
    pb = request.state.pb
    tenant = request.state.tenant.id

    trainees = list_trainees(pb, tenant, query=query)

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
            "title": "لیست شاگردان",
            "tenant": request.state.tenant,
            "user": request.state.user,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "is_search_result": True,
            "search_query": query,
            "show_empty_state": len(trainees.items if hasattr(trainees, "items") else trainees) == 0
            and len(query) > 0,
            "empty_message": "هیچ شاگردی با این مشخصات پیدا نشد",
        },
    )


@router.get("/trainees/filter")
async def filter_trainees(
    request: Request,
    gender: str = None,
    status: str = None,
    min_birthdate: str = None,
    max_birthdate: str = None,
):
    """Filter trainees by criteria"""
    pb = request.state.pb
    tenant = request.state.tenant.id

    trainees = list_trainees(
        pb,
        tenant,
        gender=gender,
        status=status,
        min_birthdate=min_birthdate,
        max_birthdate=max_birthdate,
    )

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
            "title": "لیست شاگردان",
            "tenant": request.state.tenant,
            "user": request.state.user,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "is_search_result": True,
            "search_query": request.query_params.get("query", ""),
            "filter_params": {
                "gender": gender,
                "status": status,
                "min_birthdate": min_birthdate,
                "max_birthdate": max_birthdate,
            },
            "show_empty_state": len(trainees.items if hasattr(trainees, "items") else trainees)
            == 0,
            "empty_message": "هیچ شاگردی با این فیلتر پیدا نشد",
        },
    )


@router.get("/trainees/new")
async def trainees_new_form(request: Request):
    user = request.state.user
    tenant = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
            "title": "ثبت شاگرد جدید",
            "tenant": tenant,
            "user": user,
            "trainee": None,
        },
    )


@router.get("/trainees/{id}")
async def show_trainee_detail(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user
    trainee_data = get_trainee_by_id(pb, tenant.id, id)
    tenant_name = request.state.tenant
    plans = get_plans_by_trainee(pb, tenant.id, id)
    progress_logs = get_progress_logs_by_trainee(pb, tenant.id, id)

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainee_detail.html",
        context={
            "title": "اطلاعات شاگرد",
            "tenant": tenant_name,
            "user": user,
            "trainee": trainee_data,
            "plans": plans,
            "progress_logs": progress_logs,
        },
    )


@router.get("/trainees/{id}/edit")
async def trainee_edit_form(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainee_data = get_trainee_by_id(pb, tenant, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
            "title": "ویرایش شاگرد",
            "tenant": tenant_name,
            "user": user,
            "trainee": trainee_data,
        },
    )


# ──────────────────────────────────────────────
#  POST Requests (Mutations)
# ──────────────────────────────────────────────
@router.post("/trainees/new")
async def trainee_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    status: str = Form("active"),
    training_history: str = Form(None),
    steroid_history: str = Form(None),
    supplement_history: str = Form(None),
    notes: str = Form(None),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id

        # --- STEP 1: Create the Auth User ---
        user_result = create_user(
            pb=pb,
            tenant_id=tenant_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="trainee",
        )

        if not user_result.get("ok"):
            error_msg = user_result.get("error", "خطا در ثبت کاربر.")
            headers = hx_toast(error_msg, "error")
            return HTMLResponse(content="", status_code=200, headers=headers)

        new_user = user_result["user"]

        # --- STEP 2: Create the Trainee Profile ---
        trainee_data = {
            "tenant": tenant_id,
            "user": new_user.id,
            "status": status,
            "gender": gender,
            "birthdate": birthdate,
            "training_history": training_history,
            "steroid_history": steroid_history,
            "supplement_history": supplement_history,
            "notes": notes,
        }

        created_trainee = create_trainee(pb, tenant_id, trainee_data)
        new_trainee_id = created_trainee.id

        # --- STEP 3: Success! Delayed Redirect to Progress Logs ---
        headers = hx_toast("شاگرد با موفقیت ثبت شد. در حال انتقال...", "success")

        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["delayed-redirect"] = {"url": f"/progress-log/new/{new_trainee_id}"}
        headers["HX-Trigger"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        # 🟢 BULLETPROOF ERROR CATCHING: Shows exact error in a toast!
        print(f"🔥 Server Crash in trainee_create: {e}")
        headers = hx_toast("خطای سرور: اطلاعات وارد شده را بررسی کنید.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)


@router.post("/trainees/{id}")
async def trainee_update(
    request: Request,
    id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    status: str = Form(None),
    training_history: str = Form(None),
    steroid_history: str = Form(None),
    supplement_history: str = Form(None),
    notes: str = Form(None),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id

        # --- STEP 1: Fetch existing trainee ---
        try:
            trainee = get_trainee_by_id(pb, tenant_id, id)
            user_id = trainee.user
        except Exception:
            headers = hx_toast("شاگرد مورد نظر یافت نشد.", "error")
            return HTMLResponse(content="", status_code=200, headers=headers)

        # --- STEP 2: Update Auth User ---
        user_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
        }
        update_user(pb, user_id, user_data)

        # --- STEP 3: Update Trainee Profile ---
        trainee_data = {
            "gender": gender,
            "birthdate": birthdate,
            "status": status,
            "training_history": training_history,
            "steroid_history": steroid_history,
            "supplement_history": supplement_history,
            "notes": notes,
        }
        update_trainee(pb, id, trainee_data)

        # --- STEP 4: Success! Delayed Redirect to Trainee Details ---
        headers = hx_toast("اطلاعات شاگرد با موفقیت بروزرسانی شد.", "success")

        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["delayed-redirect"] = {"url": f"/trainees/{id}"}
        headers["HX-Trigger"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        # 🟢 BULLETPROOF ERROR CATCHING
        print(f"🔥 Server Crash in trainee_update: {e}")
        headers = hx_toast("خطا در بروزرسانی اطلاعات.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)
