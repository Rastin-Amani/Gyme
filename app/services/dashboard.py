from datetime import datetime, timedelta, timezone
from app.services.coach import list_coaches
from structlog import get_logger
from app.security import pb_escape

logger = get_logger(__name__)

ALLOWED_TIMEFRAMES = {"all", "week", "month"}

def get_owner_dashboard_stats(pb, tenant_id: str, timeframe: str = "all"):
    # Validate timeframe against allowlist
    if timeframe not in ALLOWED_TIMEFRAMES:
        timeframe = "all"
    # Base filter ensures we only get this specific owner's data
    base_filter = f'tenant="{pb_escape(tenant_id)}"'

    # Calculate timeframes based on PocketBase's required UTC format
    if timeframe == "week":
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
            "%Y-%m-%d %H:%M:%S.000Z"
        )
        base_filter += f' && created >= "{start_date}"'
    elif timeframe == "month":
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%d %H:%M:%S.000Z"
        )
        base_filter += f' && created >= "{start_date}"'

    # Helper function to get the count efficiently
    def get_count(collection: str, extra_filter: str = ""):
        final_filter = base_filter
        if extra_filter:
            final_filter += f" && {extra_filter}"
        try:
            # We fetch 1 item per page just to read the 'total_items' metadata!
            result = pb.collection(collection).get_list(
                page=1, per_page=1, query_params={"filter": final_filter}
            )
            # Depending on your python sdk version, it might be total_items or totalItems
            return getattr(result, "total_items", getattr(result, "totalItems", 0))
        except Exception as e:
            logger.error("dashboard.count_error", collection=collection, error=str(e))
            return 0

    return {
        "active_trainees": get_count("trainees", 'status="active"'),
        "inactive_trainees": get_count("trainees", 'status="inactive"'),
        "diet_plans": get_count("plans", 'type="diet"'),
        "training_plans": get_count("plans", 'type="training"'),
        "steroid_plans": get_count("plans", 'type="steroid"'),
    }


def _time_filter(timeframe: str) -> str:
    """Return a PocketBase date filter snippet for the given timeframe."""
    if timeframe and timeframe != "all":
        if timeframe not in ALLOWED_TIMEFRAMES:
            return ""
        days = 7 if timeframe == "week" else 30 if timeframe == "month" else 0
        if days:
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S.000Z"
            )
            return f' && created >= "{pb_escape(start)}"'
    return ""


def _coach_stats_single(pb, tenant_id: str, coach_id: str, coach_name: str, timeframe: str = "all"):
    """Compute stats for one coach."""
    tf = _time_filter(timeframe)
    try:
        plans = pb.collection("plans").get_full_list(
            query_params={"filter": f'tenant="{pb_escape(tenant_id)}" && coach="{pb_escape(coach_id)}"{tf}'}
        )
        logger.debug("coach_stats.plans_fetched", coach_id=coach_id, count=len(plans))
    except Exception as e:
        logger.warning("coach_stats.plans_fetch_failed", coach_id=coach_id, error=str(e))
        plans = []

    trainee_ids = set()
    total = active = draft = inactive = 0
    diet = training = steroid = 0
    for p in plans:
        tid = getattr(p, "trainee", None)
        if tid:
            trainee_ids.add(tid)
        total += 1
        st = getattr(p, "status", "") or ""
        if st == "active":
            active += 1
        elif st == "draft":
            draft += 1
        elif st == "inactive":
            inactive += 1
        ptype = getattr(p, "type", "") or ""
        if ptype == "diet":
            diet += 1
        elif ptype == "training":
            training += 1
        elif ptype == "steroid":
            steroid += 1

    in_progress = 0
    for p in plans:
        pid = getattr(p, "id", None)
        if not pid:
            continue
        try:
            progress = pb.collection("plan_progress").get_first_list_item(
                f'tenant="{pb_escape(tenant_id)}" && plan="{pb_escape(pid)}"'
            )
            if progress:
                in_progress += 1
        except Exception:
            pass

    return {
        "id": coach_id,
        "name": coach_name,
        "trainee_count": len(trainee_ids),
        "plan_count": total,
        "active_plans": active,
        "in_progress": in_progress,
        "diet_count": diet,
        "training_count": training,
        "steroid_count": steroid,
    }


def get_coach_stats(
    pb, tenant_id: str, coach_id: str = None, owner_id: str = None, timeframe: str = "all"
):
    """Per-coach aggregated stats for owner dashboard.

    If coach_id is given, returns only that coach's stats (single-item list).
    If owner_id is given, includes owner's stats even if not a coach.
    Otherwise returns all coaches' stats.
    timeframe filters plans by creation date.
    """
    # Single coach mode
    if coach_id:
        try:
            coach = pb.collection("users").get_one(pb_escape(coach_id))
            # Verify coach belongs to tenant if role is coach
            rec_tenant = getattr(coach, "tenant", None)
            if rec_tenant and str(rec_tenant) != str(tenant_id):
                logger.warning("get_coach_stats.tenant_mismatch", coach_id=coach_id, tenant=tenant_id)
                return []
        except Exception as e:
            logger.warning("get_coach_stats.coach_fetch_failed", coach_id=coach_id, error=str(e))
            return []
        name = (
            f"{getattr(coach, 'first_name', '')} {getattr(coach, 'last_name', '')}".strip()
            or getattr(coach, "email", "?")
        )
        return [_coach_stats_single(pb, tenant_id, coach_id, name, timeframe)]

    # Multi-coach mode: include all coaches + owner if specified
    result = []

    # Add all coaches (users with role="coach")
    coaches = list_coaches(pb, tenant_id, per_page=200)
    raw = getattr(coaches, "items", coaches)
    coach_list = list(raw) if raw else []
    logger.info("get_coach_stats.coaches_fetched", count=len(coach_list))

    for coach in coach_list:
        coach_id = getattr(coach, "id", None)
        if not coach_id:
            continue
        name = (
            f"{getattr(coach, 'first_name', '')} {getattr(coach, 'last_name', '')}".strip()
            or getattr(coach, "email", "?")
        )
        result.append(_coach_stats_single(pb, tenant_id, coach_id, name, timeframe))

    # Add owner's stats if requested and not already included
    if owner_id and owner_id not in [c["id"] for c in result]:
        try:
            owner_coach = pb.collection("users").get_one(pb_escape(owner_id))
            rec_tenant = getattr(owner_coach, "tenant", None)
            if rec_tenant and str(rec_tenant) != str(tenant_id):
                logger.warning("get_coach_stats.owner_tenant_mismatch", owner_id=owner_id)
            else:
                name = f"{getattr(owner_coach, 'first_name', '')} {getattr(owner_coach, 'last_name', '')}".strip() or getattr(
                    owner_coach, "email", "?"
                )
                result.append(_coach_stats_single(pb, tenant_id, owner_id, name, timeframe))
        except Exception as e:
            logger.warning("get_coach_stats.owner_fetch_failed", owner_id=owner_id, error=str(e))

    return result
