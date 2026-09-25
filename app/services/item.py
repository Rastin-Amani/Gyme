from app.security import pb_escape


def _validate_collection(collection: str):
    if collection not in {"training_items", "diet_items", "steroid_items"}:
        raise ValueError(f"Invalid collection: {collection}")


def list_items(pb, tenant, collection, page=1, per_page=50):
    _validate_collection(collection)
    return pb.collection(collection).get_list(
        page=page,
        per_page=per_page,
        query_params={
            "filter": f'tenant="{pb_escape(tenant)}"',
            "sort": "+seq,+order",
            "expand": "plan,trainee",
        },
    )


def list_items_by_plan(pb, tenant, collection, plan=None, page=1, per_page=100):
    _validate_collection(collection)
    plan = str(plan) if plan is not None else ""
    return pb.collection(collection).get_list(
        page=page,
        per_page=per_page,
        query_params={
            "filter": f'tenant="{pb_escape(tenant)}" && plan="{pb_escape(plan)}"',
            "sort": "+seq,+order",
        },
    )


def get_item_by_id(pb, tenant, collection, id):
    _validate_collection(collection)
    # Use get_first_list_item with tenant filter to enforce tenant isolation
    # get_one with filter may be ignored by PB, so verify after fetch
    record = pb.collection(collection).get_one(pb_escape(id))
    # Enforce tenant isolation post-fetch
    rec_tenant = getattr(record, "tenant", None)
    if str(rec_tenant) != str(tenant):
        from pocketbase.errors import ClientResponseError

        raise ClientResponseError({"status": 404, "message": "Not found"}, 404, "Not found")
    return record


def get_items_by_plan_seq(pb, tenant, collection, plan, current_seq):
    _validate_collection(collection)
    return pb.collection(collection).get_full_list(
        query_params={
            "filter": f'tenant="{pb_escape(tenant)}" && plan="{pb_escape(plan)}" && seq="{pb_escape(str(current_seq))}"',
            "order": "+seq",
        }
    )


def create_item(pb, tenant, collection, data: dict):
    _validate_collection(collection)
    payload = {
        **data,
        "tenant": tenant,
    }
    return pb.collection(collection).create(payload)


def update_item(pb, id, collection, data: dict):
    _validate_collection(collection)
    return pb.collection(collection).update(pb_escape(id), data)


def delete_item(pb, id, collection: str = "plan_items"):
    _validate_collection(collection)
    return pb.collection(collection).delete(pb_escape(id))
