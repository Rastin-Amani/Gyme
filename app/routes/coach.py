from fastapi import APIRouter, Request, Form, Query
from app.services.coach import list_coaches, get_coach_by_id, delete_coach
from app.services.auth import create_user, update_user
from ..templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
import json
from app.utils import hx_toast

router = APIRouter(tags=["Coaches Management"])


# ──────────────────────────────────────────────
#  GET Requests
# ──────────────────────────────────────────────
@router.get("/coaches")
async def coaches_list(request: Request, page: int = Query(1, ge=1)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    per_page = 20
    coaches = list_coaches(pb, tenant, page=page, per_page=per_page)

    total = coaches.total_items if hasattr(coaches, "total_items") else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/coach/coaches.html",
        context={
            "title": "مربی‌ها",
            "tenant": request.state.tenant,
            "user": user,
            "coaches": coaches.items if hasattr(coaches, "items") else coaches,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/coaches/new")
async def coaches_new_form(request: Request):
    user = request.state.user
    tenant = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="forms/coaches_form.html",
        context={
            "title": "ثبت مربی جدید",
            "tenant": tenant,
            "user": user,
            "coach": None,
        },
    )


@router.get("/coaches/{id}")
async def coach_detail(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    coach = get_coach_by_id(pb, tenant, id)

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/coach/coach_detail.html",
        context={
            "title": "اطلاعات مربی",
            "tenant": request.state.tenant,
            "user": user,
            "coach": coach,
        },
    )


@router.get("/coaches/{id}/edit")
async def coach_edit_form(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    coach = get_coach_by_id(pb, tenant, id)

    return templates.TemplateResponse(
        request=request,
        name="forms/coaches_form.html",
        context={
            "title": "ویرایش مربی",
            "tenant": request.state.tenant,
            "user": user,
            "coach": coach,
        },
    )


@router.get("/coaches/{id}/confirm-delete")
async def coach_confirm_delete(request: Request, id: str):
    return templates.TemplateResponse(
        request=request,
        name="modals/confirm_delete.html",
        context={"delete_url": f"/coaches/{id}", "title": "حذف مربی"},
    )


@router.delete("/coaches/{id}")
async def coach_delete(request: Request, id: str):
    try:
        pb = request.state.pb
        delete_coach(pb, id)
        headers = hx_toast("مربی با موفقیت حذف شد.", "success")
        trigger_dict = json.loads(headers.get("HX-Trigger-After-Swap", "{}"))
        trigger_dict["delayed-redirect"] = {"url": "/coaches"}
        headers["HX-Trigger-After-Swap"] = json.dumps(trigger_dict)
        return HTMLResponse(content="", status_code=200, headers=headers)
    except Exception as e:
        print(f"🔥 Server Crash in coach_delete: {e}")
        headers = hx_toast("خطا در حذف مربی.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)


# ──────────────────────────────────────────────
#  POST Requests (Mutations)
# ──────────────────────────────────────────────
@router.post("/coaches/new")
async def coach_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id

        user_result = create_user(
            pb=pb,
            tenant_id=tenant_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="coach",
        )

        if not user_result.get("ok"):
            error_msg = user_result.get("error", "خطا در ثبت کاربر.")
            headers = hx_toast(error_msg, "error")
            return HTMLResponse(content="", status_code=200, headers=headers)

        headers = hx_toast("مربی با موفقیت ثبت شد.", "success")
        trigger_dict = json.loads(headers.get("HX-Trigger-After-Swap", "{}"))
        trigger_dict["delayed-redirect"] = {"url": "/coaches"}
        headers["HX-Trigger-After-Swap"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        print(f"🔥 Server Crash in coach_create: {e}")
        headers = hx_toast("خطای سرور: اطلاعات وارد شده را بررسی کنید.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)


@router.post("/coaches/{id}")
async def coach_update(
    request: Request,
    id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id

        # Verify coach exists under this tenant
        get_coach_by_id(pb, tenant_id, id)

        update_user(
            pb,
            id,
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
            },
        )

        headers = hx_toast("اطلاعات مربی با موفقیت بروزرسانی شد.", "success")
        trigger_dict = json.loads(headers.get("HX-Trigger-After-Swap", "{}"))
        trigger_dict["delayed-redirect"] = {"url": f"/coaches/{id}"}
        headers["HX-Trigger-After-Swap"] = json.dumps(trigger_dict)

        return HTMLResponse(content="", status_code=200, headers=headers)

    except Exception as e:
        print(f"🔥 Server Crash in coach_update: {e}")
        headers = hx_toast("خطا در بروزرسانی اطلاعات.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)
