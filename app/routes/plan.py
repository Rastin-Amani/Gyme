from fastapi import APIRouter, Request, Form
from app.services.plan import (
    create_plan, list_plans, get_plan_by_id, update_plan
    )
from app.services.item import list_items_by_plan
from ..templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import list_trainees
from fastapi.responses import RedirectResponse


router = APIRouter(
    tags=["Plans Management"]
)

# Get Requests
@router.get("/plans")
async def plan_list (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    plans = list_plans(pb, tenant)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/plan/plans.html",
        context={
        "title" : "لیست برنامه‌ها",
        "tenant": tenant_name,
        "user": user,
        "plans": plans.items,
        }
    )

@router.get("/plans/new")
async def plan_new_form (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees (pb, tenant)

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
   
    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
        "title" : "ثبت شاگرد جدید",
        "tenant": tenant,
        "user":user,        
        "plan": None,
        "trainees": trainees.items,
        }
    )

@router.get("/plans/{id}")
async def show_plan_detail (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    plan_data = get_plan_by_id(pb, tenant, id)
    user = request.state.user

    plan_type = plan_data.type 
    collection_name = f"{plan_type}_items"

    item_data = list_items_by_plan(pb, tenant, collection_name, plan=id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
   
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/plan/plan_detail.html",
        context={
        "title" : "جزئیات برنامه",
        "tenant": tenant_name,
        "user": user,
        "plan": plan_data,
        "item": item_data
        }
    )


@router.get("/plans/{id}/edit")
async def plan_edit_form (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees (pb, tenant)
    plan_data = get_plan_by_id(pb, tenant, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
   
    return templates.TemplateResponse(
        request=request,
        name="forms/plans_form.html",
        context={
        "title" : "ویرایش برنامه",
        "tenant": tenant_name,
        "user": user,
        "plan": plan_data,
        "trainees": trainees.items,
        }
    )




# Post Requests
@router.post("/plans")
async def plan_create(
    request: Request,
    title: str = Form(...),
    type: str = Form(...),
    trainee:str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    days_per_week: int = Form(None),
    status: str = Form(None),
    notes: str = Form(None),

):
    pb = request.state.pb
    tenant = request.state.tenant.id # Passing the ID string
    
    data = {
        "title": title,
        "type": type,
        "trainee": trainee,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
        "days_per_week": days_per_week,
        "notes": notes,
    }

    # Use your functional service
    create_plan(pb, tenant, data)
    
    # After creation, HTMX can redirect the whole page back to the list
    # or just return the updated list fragment.
    return HTMLResponse(headers={"HX-Redirect": "/plans"})

@router.post("/plans/{id}")
async def plan_update(
    request: Request,
    id: str,
    title: str = Form(...),
    trainee:str = Form(None),
    type: str = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
    days_per_week: int = Form(None),
    status: str = Form(None),
    notes: str = Form(None),

):
    pb = request.state.pb
    tenant = request.state.tenant.id # Passing the ID string
    
    data = {
        "title": title,
        "type": type,
        "trainee": trainee,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
        "days_per_week": days_per_week,
        "notes": notes,
    }

    # Use your functional service
    update_plan(pb, id, data)
    
    # After creation, HTMX can redirect the whole page back to the list
    # or just return the updated list fragment.
    return HTMLResponse(headers={"HX-Redirect": "/plans"})
