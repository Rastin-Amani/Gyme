from fastapi import APIRouter, Request, Depends, Response
from ...templates import templates
from fastapi.responses import HTMLResponse
from app.services.trainee import get_trainee_by_user
from app.services.plan import get_plans_by_trainee, get_plan_by_id
from app.services.progress import get_progress_by_plan
from app.services.item import get_items_by_plan_seq, list_items_by_plan
from app.security import pb_escape, ALLOWED_PLAN_TYPES, sanitize_collection_name

router = APIRouter()


@router.get("/user/dashboard", response_class=HTMLResponse)
async def trainee_dashboard(request: Request):
    pb = request.state.pb
    # 🟢 Extract the string ID explicitly for your database filters
    tenant_id = request.state.tenant.id
    user = request.state.user
    if getattr(user, "role", None) != "trainee":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard")

    trainee = get_trainee_by_user(pb, tenant_id, user.id)
    if not trainee:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    plans = get_plans_by_trainee(pb, tenant_id, trainee.id)

    categorized = {"training": [], "diet": [], "steroid": []}

    for p in plans:
        plan_type = p.type.value if hasattr(p.type, "value") else str(p.type)
        if plan_type not in ALLOWED_PLAN_TYPES:
            continue

        try:
            progress = get_progress_by_plan(pb, tenant_id, p.id)
            current_seq = progress.current_seq if progress else 1
        except Exception as e:
            progress = None
            current_seq = 1

        try:
            coll_name = sanitize_collection_name(plan_type)
        except ValueError:
            continue
        try:
            # 🟢 Passing tenant_id (string) and current_seq dynamically!
            items = get_items_by_plan_seq(pb, tenant_id, coll_name, p.id, current_seq)
        except Exception as e:
            items = []

        # 🟢 Map to native dict to keep Jinja2 templates happy
        plan_dict = {
            "id": getattr(p, "id", None),
            "title": getattr(p, "title", None),
            "start_date": getattr(p, "start_date", None),
            "end_date": getattr(p, "end_date", None),
            "progress": progress,
            "items": items,
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
            "tenant": request.state.tenant,  # Frontend might still want the object
            "trainee": trainee,
            "plans": categorized,
        },
    )


@router.post("/user/plans/{plan_id}/done")
async def mark_plan_done(plan_id: str, request: Request):
    pb = request.state.pb
    tenant_id = request.state.tenant.id
    user = request.state.user
    if getattr(user, "role", None) != "trainee":
        return Response(status_code=403)
    # Verify plan belongs to this trainee
    trainee = get_trainee_by_user(pb, tenant_id, user.id)
    if not trainee:
        return Response(status_code=403)
    # Ensure plan is assigned to this trainee and tenant
    plan_check = get_plan_by_id(pb, tenant_id, plan_id)
    if str(getattr(plan_check, "trainee", "")) != str(trainee.id):
        return Response(status_code=403)

    # 1. Try to fetch existing progress
    try:
        records = pb.collection("plan_progress").get_full_list(
            query_params={"filter": f'plan="{pb_escape(plan_id)}" && tenant="{pb_escape(tenant_id)}"'}
        )
        progress = records[0] if records else None
    except Exception:
        progress = None

    # 2. Logic: Update existing OR Create new
    plan = get_plan_by_id(pb, tenant_id, plan_id)
    plan_type = plan.type.value if hasattr(plan.type, "value") else str(plan.type)
    if plan_type not in ALLOWED_PLAN_TYPES:
        return Response(status_code=400)
    coll = sanitize_collection_name(plan_type)
    all_items = list_items_by_plan(pb, tenant_id, coll, plan=plan_id, per_page=500)
    seqs = sorted({int(getattr(item, "seq", 1)) for item in all_items.items}) or [1]

    # 3. Find next seq with wrap
    current_seq = getattr(progress, "current_seq", seqs[0]) if progress else seqs[0]
    try:
        idx = seqs.index(current_seq)
        next_seq = seqs[(idx + 1) % len(seqs)]
    except ValueError:
        next_seq = seqs[0]

    if progress:
        pb.collection("plan_progress").update(progress.id, {"current_seq": next_seq})
    else:
        pb.collection("plan_progress").create(
            {"tenant": tenant_id, "plan": plan_id, "current_seq": next_seq}
        )

    # 3. Return an HTMX response to trigger the UI update ⚡
    response = Response(status_code=200)

    # Use HX-Refresh to smoothly reload the current dashboard page
    response.headers["HX-Refresh"] = "true"

    # OR, if you strictly want to use HX-Redirect to a specific URL:
    # response.headers["HX-Redirect"] = "/user/dashboard"

    return response
