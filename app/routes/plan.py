from fastapi import APIRouter, Request, Form, Query
from app.services.plan import (
    create_plan,
    list_plans,
    get_plan_by_id,
    update_plan,
    list_templates,
    apply_template,
    get_template_by_id,
    delete_plan,
)
from app.services.item import list_items_by_plan
from ..templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.trainee import list_trainees
from app.utils import hx_toast
import json
from structlog import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Plans Management"])


# ──────────────────────────────────────────────
#  GET /plans  –  list plans (owner / coach view)
# ──────────────────────────────────────────────
@router.get("/plans")
async def plan_list(
    request: Request,
    page: int = Query(1, ge=1),
    query: str = Query(""),
    type: str = Query(None),
    coach_id: str = Query(None),
    is_template: str = Query("false"),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    is_template_bool = str(is_template).lower() in ["true", "1", "yes"]

    # Force coach filter: coach sees only their assigned plans
    if user.role == "coach":
        coach_id = user.id

    per_page = 5
    plans = list_plans(
        pb,
        tenant,
        page=page,
        per_page=per_page,
        query=query,
        type=type,
        coach_id=coach_id,
        is_template=is_template_bool,
    )

    tenant_name = request.state.tenant

    try:
        coaches = (
            pb.collection("coaches")
            .get_list(
                page=1,
                per_page=100,
                query_params={
                    "filter": f'tenant="{tenant}"',
                    "sort": "-created",
                },
            )
            .items
        )
    except Exception:
        coaches = []

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    total = plans.total_items if hasattr(plans, "total_items") else 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    logger.info(
        "plan.list_pagination", total=total, per_page=per_page, page=page, total_pages=total_pages
    )

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/plan/plans.html",
        context={
            "title": "قالب‌های برنامه" if is_template_bool else "لیست برنامه‌ها",
            "tenant": tenant_name,
            "user": user,
            "plans": plans.items if hasattr(plans, "items") else plans,
            "coaches": coaches,
            "is_search_result": bool(query or type or coach_id),
            "search_query": query,
            "filter_params": {
                "type": type,
                "coach_id": coach_id,
            },
            "show_empty_state": len(plans.items if hasattr(plans, "items") else plans) == 0
            and bool(query or type or coach_id),
            "empty_message": "هیچ برنامه‌ای با این مشخصات پیدا نشد",
            "is_template": is_template_bool,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "per_page": per_page,
        },
    )


# ──────────────────────────────────────────────
#  GET /plans/new  –  create plan form
# ──────────────────────────────────────────────
@router.get("/plans/new")
async def plan_new_form(request: Request, template: str = Query("false")):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees(pb, tenant)
    is_template = str(template).lower() in ["true", "1", "yes"]

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    # Fetch coaches (users with role="coach") for this tenant
    try:
        coaches = (
            pb.collection("users")
            .get_list(
                page=1,
                per_page=100,
                query_params={"filter": f'tenant="{tenant}" && role="coach"', "sort": "first_name"},
            )
            .items
        )
    except Exception:
        coaches = []

    # Prepend current user as first option, deduplicate
    coach_list = [user] + [c for c in coaches if c.id != user.id]

    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
            "title": "قالب برنامه جدید" if is_template else "برنامه جدید",
            "tenant": tenant,
            "user": user,
            "plan": None,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "coaches": coach_list,
            "is_template": is_template,
        },
    )


# ──────────────────────────────────────────────
#  GET /plans/{id}  –  plan detail
# ──────────────────────────────────────────────
@router.get("/plans/{id}")
async def show_plan_detail(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    try:
        plan_data = get_plan_by_id(pb, tenant, id)
    except Exception:
        return RedirectResponse(url="/plans")

    if not hasattr(plan_data, "is_template") or plan_data.is_template is None:
        plan_data.is_template = False

    plan_type = plan_data.type
    collection_name = f"{plan_type}_items"

    try:
        item_data = list_items_by_plan(pb, tenant, collection_name, plan=id)
    except Exception:
        item_data = {"items": []}

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/plan/plan_detail.html",
        context={
            "title": "جزئیات برنامه",
            "tenant": request.state.tenant,
            "user": user,
            "plan": plan_data,
            "item": item_data,
        },
    )


# ──────────────────────────────────────────────
#  GET /plans/{id}/edit  –  edit plan form
# ──────────────────────────────────────────────
@router.get("/plans/{id}/edit")
async def plan_edit_form(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees(pb, tenant)
    plan_data = get_plan_by_id(pb, tenant, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    # Fetch coaches (users with role="coach") for this tenant
    try:
        coaches = (
            pb.collection("users")
            .get_list(
                page=1,
                per_page=100,
                query_params={"filter": f'tenant="{tenant}" && role="coach"', "sort": "first_name"},
            )
            .items
        )
    except Exception:
        coaches = []

    # Prepend current user as first option, deduplicate
    coach_list = [user] + [c for c in coaches if c.id != user.id]

    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
            "title": "ویرایش برنامه",
            "tenant": tenant_name,
            "user": user,
            "plan": plan_data,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "coaches": coach_list,
            "is_template": getattr(plan_data, "is_template", False),
        },
    )


# ──────────────────────────────────────────────
#  GET /templates/{id}/apply  –  show apply form (modal)
# ──────────────────────────────────────────────
@router.get("/templates/{id}/apply")
async def template_apply_form(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    template = get_template_by_id(pb, tenant, id)
    trainees = list_trainees(pb, tenant)

    # Fetch coaches (users with role="coach") for this tenant
    try:
        coaches = (
            pb.collection("users")
            .get_list(
                page=1,
                per_page=100,
                query_params={"filter": f'tenant="{tenant}" && role="coach"', "sort": "first_name"},
            )
            .items
        )
    except Exception:
        coaches = []

    # Prepend current user as first option, deduplicate
    coach_list = [user] + [c for c in coaches if c.id != user.id]

    return templates.TemplateResponse(
        request=request,
        name="modals/apply_template.html",
        context={
            "template": template,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "user": user,
            "coaches": coach_list,
        },
    )


# ──────────────────────────────────────────────
#  POST /templates/{id}/apply  –  apply template
# ──────────────────────────────────────────────
@router.post("/templates/{id}/apply")
async def template_apply(
    request: Request,
    id: str,
    trainee: str = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
    notes: str = Form(None),
    coach: str = Form(None),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    try:
        new_plan = apply_template(
            pb,
            tenant,
            id,
            trainee_id=trainee,
            coach_id=coach or user.id,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )

        # 🟢 SUCCESS: Modal closes, Toast shows, Browser waits 1.2s, then Navigates
        trigger_data = {
            "closeModal": True,
            "show-toast": {"message": "برنامه با موفقیت از قالب ایجاد شد", "type": "success"},
            "delayed-redirect": {"url": f"/plans/{new_plan.id}"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        error_msg = str(e)
        logger.error("template.apply_failed", error=error_msg, template_id=id, tenant=tenant)
        user_message = "خطا در برقراری ارتباط با پایگاه داده."
        if "404" in error_msg:
            user_message = "قالب یا شاگرد مورد نظر یافت نشد!"
        elif "400" in error_msg:
            user_message = "اطلاعات وارد شده نامعتبر است. تاریخ‌ها را بررسی کنید."

        # 🔴 ERROR: Modal stays open, Toast shows
        trigger_data = {"show-toast": {"message": user_message, "type": "error"}}
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# ──────────────────────────────────────────────
#  POST /plans  –  create plan / template
# ──────────────────────────────────────────────
@router.post("/plans")
async def plan_create(
    request: Request,
    type: str = Form(...),
    trainee: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    days_per_week: int = Form(None),
    status: str = Form(None),
    notes: str = Form(None),
    is_template: str = Form("false"),
    template_name: str = Form(None),
    coach: str = Form(None),
):
    is_template_bool = str(is_template).lower() in ["true", "on", "1", "yes"]
    pb = request.state.pb
    tenant = request.state.tenant.id

    data = {
        "type": type,
        "trainee": trainee if not is_template_bool else None,
        "start_date": start_date,
        "end_date": end_date,
        "status": status or "active",
        "days_per_week": days_per_week,
        "notes": notes,
        "is_template": is_template_bool,
        "template_name": template_name if is_template_bool else None,
        "coach": coach,
    }

    try:
        create_plan(pb, tenant, data)

        # 🟢 SUCCESS: Toast shows, Browser waits 1.2s, then Navigates
        success_msg = (
            "قالب جدید با موفقیت ذخیره شد" if is_template_bool else "برنامه جدید با موفقیت ایجاد شد"
        )
        redirect_url = "/plans?is_template=true" if is_template_bool else "/plans"

        trigger_data = {
            "show-toast": {"message": success_msg, "type": "success"},
            "delayed-redirect": {"url": redirect_url},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error(
            "plan.create_failed", error=str(e), tenant=tenant, is_template=is_template_bool
        )
        # 🔴 ERROR: Stays on page, Toast shows
        trigger_data = {
            "show-toast": {"message": "خطا در ایجاد. لطفا فیلدها را بررسی کنید.", "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# ──────────────────────────────────────────────
#  POST /plans/{id}  –  update plan / template
# ──────────────────────────────────────────────
@router.post("/plans/{id}")
async def plan_update(
    request: Request,
    id: str,
    trainee: str = Form(None),
    type: str = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
    days_per_week: int = Form(None),
    status: str = Form(None),
    notes: str = Form(None),
    is_template: str = Form("false"),
    template_name: str = Form(None),
    coach: str = Form(None),
):
    is_template_bool = str(is_template).lower() in ["true", "on", "1", "yes"]
    pb = request.state.pb
    tenant = request.state.tenant.id

    data = {
        "type": type,
        "trainee": trainee if not is_template_bool else None,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
        "days_per_week": days_per_week,
        "notes": notes,
        "is_template": is_template_bool,
        "template_name": template_name if is_template_bool else None,
        "coach": coach,
    }

    try:
        update_plan(pb, id, data)

        # 🟢 SUCCESS: Toast shows, Browser waits 1.2s, then Navigates
        trigger_data = {
            "show-toast": {"message": "تغییرات با موفقیت ذخیره شد", "type": "success"},
            "delayed-redirect": {"url": f"/plans/{id}"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error("plan.update_failed", error=str(e), plan_id=id, tenant=tenant)
        # 🔴 ERROR: Stays on page, Toast shows
        trigger_data = {"show-toast": {"message": "خطا در بروزرسانی اطلاعات.", "type": "error"}}
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


@router.get("/plans/{id}/confirm-delete")
async def plan_confirm_delete(request: Request, id: str):
    return templates.TemplateResponse(
        request=request,
        name="modals/confirm_delete.html",
        context={"delete_url": f"/plans/{id}", "title": "حذف برنامه"},
    )


@router.delete("/plans/{id}")
async def plan_delete(request: Request, id: str):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id
        delete_plan(pb, tenant_id, id)
        headers = hx_toast("برنامه با موفقیت حذف شد.", "success")
        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["delayed-redirect"] = {"url": "/plans"}
        headers["HX-Trigger"] = json.dumps(trigger_dict)
        return HTMLResponse(content="", status_code=200, headers=headers)
    except Exception as e:
        logger.error("plan.delete_failed", error=str(e), plan_id=id)
        headers = hx_toast("خطا در حذف برنامه.", "error")
        return HTMLResponse(content="", status_code=200, headers=headers)
