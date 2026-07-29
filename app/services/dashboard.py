from datetime import datetime, timedelta, timezone
from app.services.coach import list_coaches


def get_owner_dashboard_stats(pb, tenant_id: str, timeframe: str = "all"):
    # Base filter ensures we only get this specific owner's data
    base_filter = f'tenant="{tenant_id}"'

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
            print(f"Error fetching count for {collection}: {e}")
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
        days = 7 if timeframe == "week" else 30 if timeframe == "month" else 0
        if days:
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S.000Z"
            )
            return f' && created >= "{start}"'
    return ""


def _coach_stats_single(pb, tenant_id: str, coach_id: str, coach_name: str, timeframe: str = "all"):
    """Compute stats for one coach."""
    print(f"🔍 _coach_stats_single — coach_id={coach_id} name={coach_name} timeframe={timeframe}")
    tf = _time_filter(timeframe)
    try:
        plans = pb.collection("plans").get_full_list(
            query_params={"filter": f'tenant="{tenant_id}" && coach="{coach_id}"{tf}'}
        )
        print(f"🔍   plans found: {len(plans)}")
    except Exception as e:
        print(f"🔍   plans fetch failed: {e}")
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
                f'tenant="{tenant_id}" && plan="{pid}"'
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
    print(f"🔍 get_coach_stats — coach_id={coach_id} owner_id={owner_id} timeframe={timeframe}")

    # Single coach mode
    if coach_id:
        try:
            coach = pb.collection("users").get_one(coach_id)
        except Exception as e:
            print(f"🔍 get_coach_stats: coach fetch failed {e}")
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
    # PocketBase result has .items; fallback to whole result if not
    print(f"🔍 get_coach_stats: coaches type={type(coaches).__name__}")
    raw = getattr(coaches, "items", coaches)
    print(f"🔍 get_coach_stats: raw type={type(raw).__name__} has_len={hasattr(raw, '__len__')}")
    coach_list = list(raw) if raw else []
    print(f"🔍 list_coaches found: {len(coach_list)}")

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
            owner_coach = pb.collection("users").get_one(owner_id)
            name = f"{getattr(owner_coach, 'first_name', '')} {getattr(owner_coach, 'last_name', '')}".strip() or getattr(
                owner_coach, "email", "?"
            )
            result.append(_coach_stats_single(pb, tenant_id, owner_id, name, timeframe))
            print(f"🔍 Added owner as coach: {name}")
        except Exception as e:
            print(f"🔍 Owner fetch failed: {e}")

    print(f"🔍 get_coach_stats returning: {len(result)} coaches")
    return result
