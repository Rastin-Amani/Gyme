from fastapi import APIRouter, Request, Form, Query
from app.services.plan import (
    create_plan,
    list_plans,
    get_plan_by_id,
    update_plan,
    apply_template,
    get_template_by_id,
    delete_plan,
)
from app.services.item import list_items_by_plan
from ..templates import templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.trainee import list_trainees, get_trainee_by_id
from app.utils import hx_toast
import json
from structlog import get_logger
from app.security import (
    pb_escape,
    ALLOWED_PLAN_TYPES,
    sanitize_collection_name,
    ALLOWED_PLAN_STATUS,
)
from app.i18n import _

logger = get_logger(__name__)

router = APIRouter(tags=["Plans Management"])


# ──────────────────────────────────────────────
#  GET /plans  –  list plans (owner / coach view)
# ──────────────────────────────────────────────
@router.get("/plans")
def plan_list(
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
            pb.collection("users")
            .get_list(
                page=1,
                per_page=100,
                query_params={
                    "filter": f'tenant="{pb_escape(tenant)}" && role="coach"',
                    "sort": "first_name",
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
            "title": _("Plan templates") if is_template_bool else _("Plans"),
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
            "empty_message": _("No plan found with these criteria"),
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
def plan_new_form(request: Request, template: str = Query("false")):
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
                query_params={
                    "filter": f'tenant="{pb_escape(tenant)}" && role="coach"',
                    "sort": "first_name",
                },
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
            "title": _("New plan template") if is_template else _("New plan"),
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
def show_plan_detail(request: Request, id: str):
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

    plan_type = str(getattr(plan_data, "type", ""))
    if plan_type not in ALLOWED_PLAN_TYPES:
        logger.warning("plan.invalid_type", plan_id=id, plan_type=plan_type)
        return RedirectResponse(url="/plans")
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        return RedirectResponse(url="/plans")

    try:
        item_data = list_items_by_plan(pb, tenant, collection_name, plan=id)
    except Exception:
        item_data = {"items": []}

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/plan/plan_detail.html",
        context={
            "title": _("Plan details"),
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
def plan_edit_form(request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    # Enforce ownership; get_plan_by_id will raise if not in tenant
    plan_data = get_plan_by_id(pb, tenant, id)
    trainees = list_trainees(pb, tenant)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    # Coach can only edit own plans
    if user.role == "coach" and getattr(plan_data, "coach", None) != user.id:
        return RedirectResponse(url="/plans")

    # Fetch coaches (users with role="coach") for this tenant
    try:
        coaches = (
            pb.collection("users")
            .get_list(
                page=1,
                per_page=100,
                query_params={
                    "filter": f'tenant="{pb_escape(tenant)}" && role="coach"',
                    "sort": "first_name",
                },
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
            "title": _("Edit plan"),
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
def template_apply_form(request: Request, id: str):
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
                query_params={
                    "filter": f'tenant="{pb_escape(tenant)}" && role="coach"',
                    "sort": "first_name",
                },
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
def template_apply(
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
            "show-toast": {
                "message": _("Plan created from template successfully"),
                "type": "success",
            },
            "delayed-redirect": {"url": f"/plans/{new_plan.id}"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        error_msg = str(e)
        logger.error("template.apply_failed", error=error_msg, template_id=id, tenant=tenant)
        user_message = _("Error connecting to the database.")
        if "404" in error_msg:
            user_message = _("Template or trainee not found!")
        elif "400" in error_msg:
            user_message = _("Invalid input. Please check the dates.")

        # 🔴 ERROR: Modal stays open, Toast shows
        trigger_data = {"show-toast": {"message": user_message, "type": "error"}}
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# ──────────────────────────────────────────────
#  POST /plans  –  create plan / template
# ──────────────────────────────────────────────
@router.post("/plans")
def plan_create(
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
    user = request.state.user

    # --- Input validation ---
    if type not in ALLOWED_PLAN_TYPES:
        trigger_data = {"show-toast": {"message": _("Invalid plan type"), "type": "error"}}
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    if status and status not in ALLOWED_PLAN_STATUS:
        status = "active"
    if days_per_week is not None and not (1 <= days_per_week <= 7):
        trigger_data = {
            "show-toast": {"message": _("Days per week must be between 1 and 7"), "type": "error"}
        }
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    if trainee and not is_template_bool:
        try:
            get_trainee_by_id(pb, tenant, trainee)
        except Exception:
            trigger_data = {"show-toast": {"message": _("Trainee not found"), "type": "error"}}
            return HTMLResponse(status_code=404, headers={"HX-Trigger": json.dumps(trigger_data)})
    if coach:
        # Verify coach belongs to tenant
        try:
            from app.services.coach import get_coach_by_id

            get_coach_by_id(pb, tenant, coach)
        except Exception:
            coach = user.id  # fallback to self
    else:
        coach = user.id
    # Enforce coach isolation: coach role can only create plans with themselves as coach
    if getattr(user, "role", None) == "coach":
        coach = user.id
    if notes:
        notes = str(notes)[:1000]
    if template_name:
        template_name = str(template_name)[:100]

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
            _("New template saved successfully")
            if is_template_bool
            else _("New plan created successfully")
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
            "show-toast": {
                "message": _("Error creating. Please check the fields."),
                "type": "error",
            }
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# ──────────────────────────────────────────────
#  POST /plans/{id}  –  update plan / template
# ──────────────────────────────────────────────
@router.post("/plans/{id}")
def plan_update(
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
    user = request.state.user

    # Verify ownership and role before update
    try:
        existing = get_plan_by_id(pb, tenant, id)
    except Exception:
        trigger_data = {"show-toast": {"message": _("Plan not found"), "type": "error"}}
        return HTMLResponse(status_code=404, headers={"HX-Trigger": json.dumps(trigger_data)})
    if getattr(user, "role", None) == "coach" and getattr(existing, "coach", None) != user.id:
        trigger_data = {"show-toast": {"message": _("Access denied"), "type": "error"}}
        return HTMLResponse(status_code=403, headers={"HX-Trigger": json.dumps(trigger_data)})
    if type not in ALLOWED_PLAN_TYPES:
        trigger_data = {"show-toast": {"message": _("Invalid plan type"), "type": "error"}}
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    if status and status not in ALLOWED_PLAN_STATUS:
        status = getattr(existing, "status", "active")
    if days_per_week is not None and not (1 <= days_per_week <= 7):
        trigger_data = {
            "show-toast": {"message": _("Invalid number of days per week"), "type": "error"}
        }
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    if trainee and not is_template_bool:
        try:
            get_trainee_by_id(pb, tenant, trainee)
        except Exception:
            trigger_data = {"show-toast": {"message": _("Trainee not found"), "type": "error"}}
            return HTMLResponse(status_code=404, headers={"HX-Trigger": json.dumps(trigger_data)})
    if coach:
        try:
            from app.services.coach import get_coach_by_id

            get_coach_by_id(pb, tenant, coach)
        except Exception:
            coach = getattr(existing, "coach", user.id)
    if getattr(user, "role", None) == "coach":
        coach = user.id
    if notes:
        notes = str(notes)[:1000]
    if template_name:
        template_name = str(template_name)[:100]

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
        update_plan(pb, tenant, id, data)

        # 🟢 SUCCESS: Toast shows, Browser waits 1.2s, then Navigates
        trigger_data = {
            "show-toast": {"message": _("Changes saved successfully"), "type": "success"},
            "delayed-redirect": {"url": f"/plans/{id}"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error("plan.update_failed", error=str(e), plan_id=id, tenant=tenant)
        # 🔴 ERROR: Stays on page, Toast shows
        trigger_data = {
            "show-toast": {"message": _("Error updating information."), "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


@router.get("/plans/{id}/confirm-delete")
def plan_confirm_delete(request: Request, id: str):
    return templates.TemplateResponse(
        request=request,
        name="modals/confirm_delete.html",
        context={"delete_url": f"/plans/{id}", "title": _("Delete plan")},
    )


@router.delete("/plans/{id}")
def plan_delete(request: Request, id: str):
    try:
        pb = request.state.pb
        tenant_id = request.state.tenant.id
        delete_plan(pb, tenant_id, id)
        headers = hx_toast(_("Plan deleted successfully."), "success")
        trigger_dict = json.loads(headers.get("HX-Trigger", "{}"))
        trigger_dict["delayed-redirect"] = {"url": "/plans"}
        headers["HX-Trigger"] = json.dumps(trigger_dict)
        return HTMLResponse(content="", status_code=200, headers=headers)
    except Exception as e:
        logger.error("plan.delete_failed", error=str(e), plan_id=id)
        headers = hx_toast(_("Error deleting plan."), "error")
        return HTMLResponse(content="", status_code=200, headers=headers)
