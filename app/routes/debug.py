from fastapi import APIRouter, Request
from app.services.plan import list_plans

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


