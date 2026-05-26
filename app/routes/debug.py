from fastapi import APIRouter, Request
from app.services.plan import list_plans, get_plan_by_id
from app.services.item import list_items_by_plan
from app.services.trainee import list_trainees

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/tenant")
def debug_tenant(request: Request):
    tenant = getattr(request.state, "tenant", None)

    if not tenant:
        return {"tenant": None}

    return {
        "id": tenant.id,
        "domain": tenant.domain,
        "name": tenant.name,
    }

@router.get("/planexpand")
def debug_expand(request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    plans_data = list_plans(pb, tenant)

    return {
        "total_items": plans_data.total_items,
        "first_plan_record": plans_data.items[0],
        # This shows the raw dictionary PocketBase constructed
        "first_plan_dict": plans_data.items[0]
    }

@router.get("/planitems")
def debug_expand(request: Request):
    pb = request.state.pb
    id = "guhobjjzu2jt2kv"
    tenant = request.state.tenant.id
    plan_data = get_plan_by_id(pb, tenant, id)

    plan_type = plan_data.type 
    collection_name = f"{plan_type}_items"

    item_data = list_items_by_plan(pb, tenant, collection_name, plan=id)
    return {
        "plan": plan_data,
        "items": item_data
    }

@router.get("/traineeitems")
def debug_expand(request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    trainees = list_trainees (pb, tenant)
    return {
        "trainees": trainees
    }

@router.get("/useritems")
def debug_expand(request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees (pb, tenant)
    return {
        "user": user,
    }



