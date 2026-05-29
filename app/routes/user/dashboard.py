from fastapi import APIRouter, Request, Depends
from ...templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import get_trainee_by_user
from app.services.plan import get_plans_by_trainee
from app.services.progress import get_progress_by_plan
from app.services.item import get_items_by_plan_seq


router = APIRouter()

@router.get("/user/dashboard", response_class=HTMLResponse)
async def trainee_dashboard(request: Request):
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

    return templates.TemplateResponse(
        request=request,
        name="pages/user/dashboard.html",
        context={
            "request": request,
            "title": "داشبورد کاربر",
            "user": user,
            "tenant": request.state.tenant, # Frontend might still want the object
            "trainee": trainee,
            "plans": categorized
        }
    )