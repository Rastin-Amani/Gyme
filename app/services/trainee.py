from pocketbase.errors import ClientResponseError
from datetime import datetime


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
    # Build the base filter
    filters = [f'tenant="{tenant}"']

    # Search filter (name, phone, email)
    if query:
        search_terms = query.split()
        search_conditions = []
        for term in search_terms:
            search_conditions.append(
                f'user.first_name ~ "{term}" || user.last_name ~ "{term}" || user.phone ~ "{term}" || user.email ~ "{term}"'
            )
        if search_conditions:
            filters.append("(" + " || ".join(search_conditions) + ")")

    # Gender filter
    if gender:
        filters.append(f'gender="{gender}"')

    # Status filter
    if status:
        filters.append(f'status="{status}"')

    # Date range filters
    if min_birthdate:
        filters.append(f'birthdate >= "{min_birthdate}"')
    if max_birthdate:
        filters.append(f'birthdate <= "{max_birthdate}"')

    # Join all filters
    filter_str = " && ".join(filters)

    # Coach filter: only show trainees assigned to this coach via plans
    if coach_id:
        # Get all trainee IDs assigned to this coach via plans
        try:
            plans = pb.collection("plans").get_full_list(
                query_params={
                    "filter": f'tenant="{tenant}" && coach="{coach_id}"',
                    "fields": "trainee",
                }
            )
            trainee_ids = [p.trainee for p in plans if hasattr(p, "trainee") and p.trainee]
            if trainee_ids:
                trainee_ids_str = " || ".join([f'id="{tid}"' for tid in trainee_ids])
                filter_str = (
                    f"({filter_str}) && ({trainee_ids_str})" if filter_str else f"{trainee_ids_str}"
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
    return pb.collection("trainees").get_first_list_item(
        f'tenant="{tenant}" && id="{id}"', query_params={"expand": "user"}
    )


def get_trainee_by_user(pb, tenant, user):
    try:
        return pb.collection("trainees").get_first_list_item(
            f'tenant="{tenant}" && user="{user}"', query_params={"expand": "user"}
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
    return pb.collection("trainees").update(trainee_id, data)


def delete_trainee(pb, tenant, trainee_id):
    # Note: PocketBase Python SDK usually just takes (id) for delete, but if you have a custom wrapper, keep as is.
    return pb.collection("trainees").delete(trainee_id)
