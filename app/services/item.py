def list_items (pb, tenant, collection, page=1, per_page=50):

    return pb.collection({collection}).get_list(
        page=page,
        per_page=per_page,
        query_params={
            "filter": f'tenant="{tenant}"',
            "sort": "+day,+order",
            "expand": "plan,trainee"
        }
    )

def list_items_by_plan (pb, tenant, collection, plan=None, page=1, per_page=100):
    return pb.collection(collection).get_list(
        page=page,
        per_page=per_page,
        query_params={
            "filter": f'tenant="{tenant}"',
            "sort": "+seq,+order"
        }
    )

def get_item_by_id (pb, tenant, collection, id):
        return pb.collection(collection).get_one(id,
            query_params={
                "filter": f'tenant="{tenant}"',
                }
        )


def create_item (pb, tenant, collection, data: dict):
    payload = {
        **data,
        "tenant": tenant,
    }
    return pb.collection(collection).create(payload)


def update_item (pb, id, collection, data: dict):
    return pb.collection(collection).update(id, data)


def delete_item (pb, id):
    return pb.collection("plan_items").delete(id)
