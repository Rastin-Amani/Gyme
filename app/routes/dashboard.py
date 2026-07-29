from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.dashboard import get_owner_dashboard_stats, get_coach_stats
from ..templates import templates
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
async def owner_dashboard(request: Request, timeframe: str = "all"):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user
    tenant_id = request.state.tenant.id
    print(f"🔴 /dashboard route hit — user.role={user.role} tenant={tenant_id}")

    # Fetch the stats based on the selected timeframe
    stats = get_owner_dashboard_stats(pb, tenant_id, timeframe)
    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    # Determine if we should show coach section
    is_owner_coach = user.role == "coach"
    coach_id = user.id if is_owner_coach else None
    print(f"🔴 is_owner_coach={is_owner_coach} coach_id={coach_id}")

    # Always include owner's stats if they have plans, even if not a coach
    coach_stats = get_coach_stats(
        pb, tenant_id, coach_id=coach_id, owner_id=user.id, timeframe=timeframe
    )
    print(f"🔴 coach_stats count={len(coach_stats)}")

    context = {
        "title": "داشبورد مدیریت",
        "stats": stats,
        "timeframe": timeframe,
        "tenant": tenant,
        "user": user,
        "show_coach_stats": not is_owner_coach,
        "is_owner_coach": is_owner_coach,
        "coach_stats": coach_stats,
    }

    # HTMX: timeframe dropdown → return dashboard content (stats + coach section), not whole page
    if request.headers.get("hx-target") == "dashboard-content":
        return templates.TemplateResponse(
            request=request, name="components/dashboard_content.html", context=context
        )

    # Standard full page load
    return templates.TemplateResponse(
        request=request, name="pages/owner/dashboard.html", context=context
    )


@router.get("/dashboard/debug-coach-stats")
async def debug_coach_stats(request: Request):
    pb = request.state.pb
    tenant_id = request.state.tenant.id
    user = request.state.user

    print(f"🔴 DEBUG: /dashboard/debug-coach-stats called — tenant={tenant_id}")

    # RAW DB DUMP: all plans for owner/coach
    for coach_id, label in [(user.id, "owner")]:
        print(f"\n🔴 Raw plans for {label} (id={coach_id}):")
        try:
            raw_plans = pb.collection("plans").get_full_list(
                query_params={"filter": f'tenant="{tenant_id}" && coach="{coach_id}"'}
            )
            for p in raw_plans:
                pid = getattr(p, "id", "?")
                pstatus = getattr(p, "status", "?")
                ptype = getattr(p, "type", "?")
                ptrainee = getattr(p, "trainee", "?")
                # check progress
                prog = None
                try:
                    prog = pb.collection("plan_progress").get_first_list_item(
                        f'tenant="{tenant_id}" && plan="{pid}"'
                    )
                    prog = "HAS_PROGRESS"
                except:
                    prog = "NO_PROGRESS"
                print(
                    f"    plan={pid} status={pstatus} type={ptype} trainee={ptrainee} progress={prog}"
                )
        except Exception as e:
            print(f"    ERROR: {e}")

    # Test all coaches (without owner)
    all_stats = get_coach_stats(pb, tenant_id, coach_id=None, owner_id=None)
    print(f"🔴 All coaches (role='coach' only): {len(all_stats)}")
    for s in all_stats:
        print(
            f"  → {s['name']} (id={s['id']}) plans={s['plan_count']} active={s.get('active_plans','?')} in_progress={s.get('in_progress','?')}"
        )

    # Test all coaches + owner
    all_with_owner = get_coach_stats(pb, tenant_id, coach_id=None, owner_id=user.id)
    print(f"🔴 All coaches + owner: {len(all_with_owner)}")
    for s in all_with_owner:
        print(
            f"  → {s['name']} (id={s['id']}) plans={s['plan_count']} active={s.get('active_plans','?')} in_progress={s.get('in_progress','?')}"
        )

    # Test single coach (owner)
    single_stats = get_coach_stats(pb, tenant_id, coach_id=user.id, owner_id=None)
    print(f"🔴 Owner only: {len(single_stats)}")
    for s in single_stats:
        print(
            f"  → {s['name']} (id={s['id']}) plans={s['plan_count']} active={s.get('active_plans','?')} in_progress={s.get('in_progress','?')}"
        )

    return {
        "all_coaches": len(all_stats),
        "all_with_owner": len(all_with_owner),
        "owner_only": len(single_stats),
    }


@router.get("/dashboard/coach-stats")
async def coach_stats_fragment(request: Request):
    pb = request.state.pb
    tenant_id = request.state.tenant.id
    user = request.state.user

    print(f"🔍 /dashboard/coach-stats called — user.role={user.role}, tenant={tenant_id}")

    # If owner is also a coach, only show their own stats
    coach_id = user.id if user.role == "coach" else None
    print(f"🔍 coach_id filter: {coach_id}")

    stats = get_coach_stats(pb, tenant_id, coach_id=coach_id, owner_id=user.id)
    print(f"🔍 coach_stats result count: {len(stats)}")
    for s in stats:
        print(
            f"  → coach={s['name']} trainees={s['trainee_count']} plans={s['plan_count']} active={s.get('active_plans','?')}"
        )

    is_owner_coach = user.role == "coach"

    return templates.TemplateResponse(
        request=request,
        name="components/coach_stats.html",
        context={"coach_stats": stats, "is_owner_coach": is_owner_coach, "user": user},
    )
