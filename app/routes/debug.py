from fastapi import APIRouter, Request
from app.services.plan import list_plans, get_plan_by_id, get_plans_by_trainee
from app.services.item import list_items_by_plan, get_items_by_plan_seq
from app.services.trainee import list_trainees, get_trainee_by_user
from app.services.progress import get_progress_by_plan


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
@router.get("/usertest")
def debug_expand(request: Request):
    pb = request.state.pb
    # 🟢 Extract the string ID explicitly for your database filters
    tenant_id = request.state.tenant.id 
    user = request.state.user
    
    trainee = get_trainee_by_user(pb, tenant_id, user.id)
    plans = get_plans_by_trainee(pb, tenant_id, trainee.id)

    categorized = {"training": [], "diet": [], "steroid": []}

    for p in plans:
        plan_type = p.type.value if hasattr(p.type, 'value') else str(p.type)
        
        try:
            progress = get_progress_by_plan(pb, tenant_id, p.id)
            current_seq = progress.current_seq if progress else 1
        except Exception as e:
            progress = None
            current_seq = 1

        coll_name = f'{plan_type}_items'
        try:
            # 🟢 Passing tenant_id (string) and current_seq dynamically!
            items = get_items_by_plan_seq(pb, tenant_id, coll_name, p.id, current_seq)
        except Exception as e:
            items = []

        # 🟢 Map to native dict to keep Jinja2 templates happy
        plan_dict = {
            "id": getattr(p, 'id', None),
            "title": getattr(p, 'title', None),
            "start_date": getattr(p, 'start_date', None),
            "end_date": getattr(p, 'end_date', None),
            "progress": progress,
            "items": items 
        }

        if plan_type in categorized:
            categorized[plan_type].append(plan_dict)


    return {
        "title": "داشبورد کاربر",
        "user": user,
        "tenant": request.state.tenant, # Frontend might still want the object
        "trainee": trainee,
        "plans": categorized
        }   




@router.get("/test")
def debug_expand(request: Request):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user


    return {
        "user": user.id,
        "tenant_id": tenant.id,
    }