def list_coaches(pb, tenant, page=1, per_page=20):
    query_params = {
        "sort": "-created",
        "filter": f'tenant="{tenant}" && role="coach"',
    }
    print(f"🔍 list_coaches — tenant={tenant} filter={query_params['filter']}")
    result = pb.collection("users").get_list(
        page=page, per_page=per_page, query_params=query_params
    )
    items = getattr(result, "items", result)
    print(f"🔍 list_coaches found: {len(items)} coaches")
    for i, coach in enumerate(items):
        coach_id = getattr(coach, "id", "?")
        coach_tenant = getattr(coach, "tenant", "?")
        coach_role = getattr(coach, "role", "?")
        print(f"🔍   coach[{i}]: id={coach_id} tenant={coach_tenant} role={coach_role}")
    return result


def get_coach_by_id(pb, tenant, id):
    return pb.collection("users").get_first_list_item(
        f'tenant="{tenant}" && id="{id}" && role="coach"'
    )


def delete_coach(pb, coach_id):
    return pb.collection("users").delete(coach_id)
