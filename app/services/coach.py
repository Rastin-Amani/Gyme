def list_coaches(pb, tenant, page=1, per_page=20):
    query_params = {
        "sort": "-created",
        "filter": f'tenant="{tenant}" && role="coach"',
    }
    return pb.collection("users").get_list(page=page, per_page=per_page, query_params=query_params)


def get_coach_by_id(pb, tenant, id):
    return pb.collection("users").get_first_list_item(
        f'tenant="{tenant}" && id="{id}" && role="coach"'
    )


def delete_coach(pb, coach_id):
    return pb.collection("users").delete(coach_id)
