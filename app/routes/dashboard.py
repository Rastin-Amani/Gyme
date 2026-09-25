from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.dashboard import get_owner_dashboard_stats, get_coach_stats
from ..templates import templates
from fastapi.responses import RedirectResponse
from structlog import get_logger
from app.i18n import _

logger = get_logger(__name__)

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
def owner_dashboard(request: Request, timeframe: str = "all"):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user
    tenant_id = request.state.tenant.id
    logger.info("dashboard.hit", role=user.role, tenant=tenant_id)

    # Fetch the stats based on the selected timeframe
    stats = get_owner_dashboard_stats(pb, tenant_id, timeframe)
    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    # Determine if we should show coach section
    is_owner_coach = user.role == "coach"
    coach_id = user.id if is_owner_coach else None

    # Always include owner's stats if they have plans, even if not a coach
    coach_stats = get_coach_stats(
        pb, tenant_id, coach_id=coach_id, owner_id=user.id, timeframe=timeframe
    )

    context = {
        "title": _("داشبورد مدیریت"),
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
def debug_coach_stats(request: Request):
    pb = request.state.pb
    tenant_id = request.state.tenant.id
    user = request.state.user

    logger.info("debug.coach_stats_hit", tenant=tenant_id)

    # RAW DB DUMP: all plans for owner/coach
    for coach_id, label in [(user.id, "owner")]:
        logger.info("debug.raw_plans", label=label, coach_id=coach_id)
        try:
            raw_plans = pb.collection("plans").get_full_list(
                query_params={"filter": f'tenant="{tenant_id}" && coach="{coach_id}"'}
            )
            for p in raw_plans:
                pid = getattr(p, "id", "?")
                pstatus = getattr(p, "status", "?")
                ptype = getattr(p, "type", "?")
                ptrainee = getattr(p, "trainee", "?")
                prog = None
                try:
                    prog = pb.collection("plan_progress").get_first_list_item(
                        f'tenant="{tenant_id}" && plan="{pid}"'
                    )
                    prog = "HAS_PROGRESS"
                except:
                    prog = "NO_PROGRESS"
                logger.info(
                    "debug.plan_row",
                    id=pid,
                    status=pstatus,
                    type=ptype,
                    trainee=ptrainee,
                    progress=prog,
                )
        except Exception as e:
            logger.error("debug.raw_plans_error", label=label, error=str(e))

    # Test all coaches (without owner)
    all_stats = get_coach_stats(pb, tenant_id, coach_id=None, owner_id=None)
    logger.info("debug.all_coaches_only", count=len(all_stats))
    for s in all_stats:
        logger.info(
            "debug.coach_row",
            name=s["name"],
            id=s["id"],
            plans=s["plan_count"],
            active=s.get("active_plans", "?"),
            in_progress=s.get("in_progress", "?"),
        )

    # Test all coaches + owner
    all_with_owner = get_coach_stats(pb, tenant_id, coach_id=None, owner_id=user.id)
    logger.info("debug.all_with_owner", count=len(all_with_owner))
    for s in all_with_owner:
        logger.info(
            "debug.coach_owner_row",
            name=s["name"],
            id=s["id"],
            plans=s["plan_count"],
            active=s.get("active_plans", "?"),
            in_progress=s.get("in_progress", "?"),
        )

    # Test single coach (owner)
    single_stats = get_coach_stats(pb, tenant_id, coach_id=user.id, owner_id=None)
    logger.info("debug.owner_only", count=len(single_stats))
    for s in single_stats:
        logger.info(
            "debug.owner_row",
            name=s["name"],
            id=s["id"],
            plans=s["plan_count"],
            active=s.get("active_plans", "?"),
            in_progress=s.get("in_progress", "?"),
        )

    return {
        "all_coaches": len(all_stats),
        "all_with_owner": len(all_with_owner),
        "owner_only": len(single_stats),
    }


@router.get("/dashboard/coach-stats")
def coach_stats_fragment(request: Request):
    pb = request.state.pb
    tenant_id = request.state.tenant.id
    user = request.state.user

    # If owner is also a coach, only show their own stats
    coach_id = user.id if user.role == "coach" else None

    stats = get_coach_stats(pb, tenant_id, coach_id=coach_id, owner_id=user.id)

    is_owner_coach = user.role == "coach"

    return templates.TemplateResponse(
        request=request,
        name="components/coach_stats.html",
        context={"coach_stats": stats, "is_owner_coach": is_owner_coach, "user": user},
    )
