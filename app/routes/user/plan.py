from fastapi import APIRouter, Request, Form
from app.services.plan import (
     get_plan_by_id, get_plans_by_trainee
    )
from app.services.item import list_items_by_plan
from ...templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import get_trainee_by_user
from fastapi.responses import RedirectResponse


router = APIRouter(
    tags=["Trainee Plans Management"]
)

# Get Requests
@router.get("/user/plans")
async def plan_list (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainee = get_trainee_by_user(pb, tenant, user.id)
    plans = get_plans_by_trainee(pb, tenant, trainee.id)
    tenant_name = request.state.tenant

    if user.role != "trainee":
        return RedirectResponse(url="/dashboard")
    
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

