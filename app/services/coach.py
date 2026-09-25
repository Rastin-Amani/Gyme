import structlog
from app.security import pb_escape


def list_coaches(pb, tenant, page=1, per_page=20):
    logger = structlog.get_logger(__name__)
    query_params = {
        "sort": "-created",
        "filter": f'tenant="{pb_escape(tenant)}" && role="coach"',
    }
    logger.debug("list_coaches", tenant=pb_escape(tenant), filter=query_params["filter"])
    result = pb.collection("users").get_list(
        page=page, per_page=per_page, query_params=query_params
    )
    items = getattr(result, "items", result)
    logger.debug("list_coaches.found", count=len(items))
    for i, coach in enumerate(items):
        coach_id = getattr(coach, "id", "?")
        coach_tenant = getattr(coach, "tenant", "?")
        coach_role = getattr(coach, "role", "?")
        logger.debug(
            "list_coaches.coach", index=i, id=coach_id, tenant=coach_tenant, role=coach_role
        )
    return result


def get_coach_by_id(pb, tenant, id):
    return pb.collection("users").get_first_list_item(
        f'tenant="{pb_escape(tenant)}" && id="{pb_escape(id)}" && role="coach"'
    )


def delete_coach(pb, tenant, coach_id):
    # Verify tenant ownership before delete
    get_coach_by_id(pb, tenant, coach_id)
    return pb.collection("users").delete(pb_escape(coach_id))
