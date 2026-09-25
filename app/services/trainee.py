from pocketbase.errors import ClientResponseError
from structlog import get_logger
from app.security import pb_escape, ALLOWED_GENDERS, ALLOWED_TRAINEE_STATUS

logger = get_logger(__name__)


def _valid_date(s):
    if not s:
        return False
    # Allow YYYY-MM-DD only
    import re

    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(s)))


def list_trainees(
    pb,
    tenant,
    page=1,
    per_page=50,
    query=None,
    gender=None,
    status=None,
    min_birthdate=None,
    max_birthdate=None,
    coach_id=None,
):
    # Build the base filter with escaping
    filters = [f'tenant="{pb_escape(tenant)}"']

    # Search filter (name, phone, email) - escape each term
    if query:
        # Limit query length to prevent DoS
        query = str(query)[:100]
        search_terms = query.split()
        search_conditions = []
        for term in search_terms[:5]:  # max 5 terms
            safe = pb_escape(term[:30])
            if not safe:
                continue
            search_conditions.append(
                f'user.first_name ~ "{safe}" || user.last_name ~ "{safe}" || user.phone ~ "{safe}" || user.email ~ "{safe}"'
            )
        if search_conditions:
            filters.append("(" + " || ".join(search_conditions) + ")")

    # Gender filter - allowlist
    if gender:
        if str(gender) in ALLOWED_GENDERS:
            filters.append(f'gender="{pb_escape(gender)}"')

    # Status filter - allowlist
    if status:
        if str(status) in ALLOWED_TRAINEE_STATUS:
            filters.append(f'status="{pb_escape(status)}"')

    # Date range filters - strict format
    if min_birthdate and _valid_date(min_birthdate):
        filters.append(f'birthdate >= "{pb_escape(min_birthdate)}"')
    if max_birthdate and _valid_date(max_birthdate):
        filters.append(f'birthdate <= "{pb_escape(max_birthdate)}"')

    # Join all filters
    filter_str = " && ".join(filters)

    # Coach filter: only show trainees assigned to this coach via plans
    if coach_id:
        # Validate coach_id is plausible (15 char PB id)
        safe_coach = pb_escape(str(coach_id)[:30])
        try:
            plans = pb.collection("plans").get_full_list(
                query_params={
                    "filter": f'tenant="{pb_escape(tenant)}" && coach="{safe_coach}"',
                    "fields": "trainee",
                }
            )
            trainee_ids = [p.trainee for p in plans if hasattr(p, "trainee") and p.trainee]
            if trainee_ids:
                # Escape each id
                trainee_ids_str = " || ".join(
                    [f'id="{pb_escape(tid)}"' for tid in trainee_ids[:200]]
                )
                filter_str = (
                    f"({filter_str}) && ({trainee_ids_str})" if filter_str else f"{trainee_ids_str}"
                )
            else:
                # No trainees for coach -> force empty result
                filter_str = (
                    f'({filter_str}) && id="__no_match__"' if filter_str else 'id="__no_match__"'
                )
        except Exception as e:
            from structlog import get_logger

            logger = get_logger(__name__)
            logger.warning("trainee.plans_fetch_failed", coach_id=coach_id, error=str(e))

    # Build query params
    query_params = {"sort": "-created", "expand": "user"}

    # Add filter if not empty
    if filter_str:
        query_params["filter"] = filter_str

    return pb.collection("trainees").get_list(
        page=page, per_page=per_page, query_params=query_params
    )


def get_trainee_by_id(pb, tenant, id):
    from app.security import pb_escape

    return pb.collection("trainees").get_first_list_item(
        f'tenant="{pb_escape(tenant)}" && id="{pb_escape(id)}"', query_params={"expand": "user"}
    )


def get_trainee_by_user(pb, tenant, user):
    from app.security import pb_escape

    try:
        return pb.collection("trainees").get_first_list_item(
            f'tenant="{pb_escape(tenant)}" && user="{pb_escape(user)}"',
            query_params={"expand": "user"},
        )
    except ClientResponseError as e:
        if e.status == 404:
            return None
        raise


def create_trainee(pb, tenant, data: dict):
    payload = {
        **data,
        "tenant": tenant,
        "status": "active",
    }
    return pb.collection("trainees").create(payload)


def update_trainee(pb, trainee_id, data: dict):
    from app.security import pb_escape

    # Allow only safe fields, strip tenant/user changes
    safe_data = {}
    allowed = {
        "gender",
        "birthdate",
        "blood_type",
        "training_history",
        "steroid_history",
        "supplement_history",
        "limitations",
        "notes",
        "height",
        "weight",
        "status",
    }
    for k, v in (data or {}).items():
        if k not in allowed:
            continue
        safe_data[k] = v
    return pb.collection("trainees").update(pb_escape(trainee_id), safe_data)


def delete_trainee(pb, tenant, trainee_id):
    # Enforce tenant ownership before delete to prevent IDOR
    trainee = get_trainee_by_id(pb, tenant, trainee_id)
    from app.security import pb_escape

    # Resolve the linked auth user (id string or expanded record) before removal
    user_id = getattr(trainee, "user", None)
    if not isinstance(user_id, str):
        user_id = getattr(user_id, "id", None)
    result = pb.collection("trainees").delete(pb_escape(trainee_id))
    # Cascade: remove the auth user too, matching coach deletion semantics
    if user_id:
        try:
            pb.collection("users").delete(pb_escape(user_id))
        except Exception:
            logger.warning("trainee_user_cascade_failed", trainee_id=trainee_id, user_id=user_id)
    return result


def verify_trainee_in_tenant(pb, tenant, trainee_id):
    """Helper to verify trainee belongs to tenant, raises 404 if not."""
    return get_trainee_by_id(pb, tenant, trainee_id)
