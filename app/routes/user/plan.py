from fastapi import APIRouter, Request, Form
from app.services.plan import (
      get_plan_by_id, get_plans_by_trainee
     )
from app.services.item import list_items_by_plan
from ...templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import get_trainee_by_user
from fastapi.responses import RedirectResponse
from app.security import sanitize_collection_name, ALLOWED_PLAN_TYPES


router = APIRouter(
    tags=["Trainee Plans Management"]
)

# Get Requests
@router.get("/user/plans")
def plan_list (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    if user.role != "trainee":
        return RedirectResponse(url="/dashboard")
    trainee = get_trainee_by_user(pb, tenant, user.id)
    if not trainee:
        return RedirectResponse(url="/login")
    plans = get_plans_by_trainee(pb, tenant, trainee.id)
    tenant_name = request.state.tenant
    
    return templates.TemplateResponse(
        request=request,
        name="pages/user/plan/plans.html",
        context={
        "title" : "لیست برنامه‌ها",
        "tenant": tenant_name,
        "user": user,
        "plans": plans
        }
    )


@router.get("/user/plans/{id}")
def show_plan_detail (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user

    if user.role != "trainee":
        return RedirectResponse(url="/dashboard")
    trainee = get_trainee_by_user(pb, tenant, user.id)
    if not trainee:
        return RedirectResponse(url="/login")
    plan_data = get_plan_by_id(pb, tenant, id)
    # Ensure plan belongs to this trainee
    if str(getattr(plan_data, "trainee", "")) != str(trainee.id):
        return RedirectResponse(url="/user/plans")
    plan_type = str(getattr(plan_data, "type", ""))
    if plan_type not in ALLOWED_PLAN_TYPES:
        return RedirectResponse(url="/user/plans")
    collection_name = sanitize_collection_name(plan_type)

    item_data = list_items_by_plan(pb, tenant, collection_name, plan=id)
    tenant_name = request.state.tenant
   
    return templates.TemplateResponse(
        request=request,
        name="pages/user/plan/plan_detail.html",
        context={
        "title" : "جزئیات برنامه",
        "tenant": tenant_name,
        "user": user,
        "plan": plan_data,
        "item": item_data
        }
    )
