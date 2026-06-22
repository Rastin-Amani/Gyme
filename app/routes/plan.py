from fastapi import APIRouter, Request, Form, Query
from app.services.plan import (
    create_plan,
    list_plans,
    get_plan_by_id,
    update_plan,
    list_templates,
    apply_template,
    get_template_by_id,
)
from app.services.item import list_items_by_plan
from ..templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import list_trainees
from fastapi.responses import RedirectResponse
import json
from app.utils import hx_toast

router = APIRouter(tags=["Plans Management"])


# ──────────────────────────────────────────────
#  GET /plans  –  list plans (owner / coach view)
# ──────────────────────────────────────────────
@router.get("/plans")
async def plan_list(
    request: Request,
    query: str = Query(""),
    type: str = Query(None),
    coach_id: str = Query(None),
    is_template: str = Query("false"),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    # Safely convert to boolean
    is_template_bool = str(is_template).lower() in ["true", "1", "yes"]

    plans = list_plans(
        pb, tenant, query=query, type=type, coach_id=coach_id, is_template=is_template_bool
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

    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
            "title": "قالب برنامه جدید" if is_template else "برنامه جدید",
            "tenant": tenant,
            "user": user,
            "plan": None,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "is_template": is_template,
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
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    try:
        # 1. Attempt to build the plan from the template
        new_plan = apply_template(
            pb,
            tenant,
            id,
            trainee_id=trainee,
            coach_id=user.id,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )

        # 2. Success! Use hx_toast to trigger the success message.
        # We also need to close the modal.
        headers = hx_toast("برنامه با موفقیت از قالب ایجاد شد 🚀", "success")

        # Add the modal close command to the existing HX-Trigger JSON
        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["closeModal"] = True
        headers["HX-Trigger"] = json.dumps(trigger_dict)

        # Redirect to the new plan
        headers["HX-Redirect"] = f"/plans/{new_plan.id}"

        return HTMLResponse(content="", headers=headers)

    except Exception as e:
        # 3. Handle Errors
        error_msg = str(e)
        print(f"❌ Error applying template: {error_msg}")

        # Determine a user-friendly error message
        user_message = "خطا در برقراری ارتباط با پایگاه داده."
        if "404" in error_msg:
            user_message = "قالب یا شاگرد مورد نظر یافت نشد!"
        elif "400" in error_msg:
            user_message = "اطلاعات وارد شده نامعتبر است. تاریخ‌ها را بررسی کنید."

        # 4. Error! Use hx_toast.
        # Modal stays open (hx-swap="none" handles this) so they can fix errors.
        headers = hx_toast(user_message, "error")

        return HTMLResponse(content="", headers=headers)


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

    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
            "title": "ویرایش برنامه",
            "tenant": tenant_name,
            "user": user,
            "plan": plan_data,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
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

    return templates.TemplateResponse(
        request=request,
        name="modals/apply_template.html",
        context={
            "template": template,
            "trainees": trainees.items if hasattr(trainees, "items") else trainees,
            "user": user,
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
            coach_id=user.id,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )
        trigger_data = {
            "closeModal": True,
            "show-toast": {
                "message": "برنامه با موفقیت از قالب ایجاد شد.",
                "type": "success",
            },
        }
        return HTMLResponse(
            status_code=200,
            headers={
                "HX-Redirect": f"/plans/{new_plan.id}",
                "HX-Trigger": json.dumps(trigger_data),
            },
        )
    except Exception as e:
        trigger_data = {
            "show-toast": {
                "message": "مشکلی پیش آمد. لطفا دوباره تلاش کنید.",
                "type": "error",
            },
        }
        return HTMLResponse(
            status_code=200,
            headers={"HX-Trigger": json.dumps(trigger_data)},
        )


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
):
    # Convert form string to native boolean
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
        "is_template": is_template_bool,  # Passed cleanly to PB as boolean
        "template_name": template_name if is_template_bool else None,
    }

    create_plan(pb, tenant, data)

    redirect_url = "/plans?is_template=true" if is_template_bool else "/plans"
    return HTMLResponse(headers={"HX-Redirect": redirect_url})


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
        "is_template": is_template_bool,  # Passed cleanly to PB as boolean
        "template_name": template_name if is_template_bool else None,
    }

    update_plan(pb, id, data)

    return HTMLResponse(headers={"HX-Redirect": f"/plans/{id}"})
