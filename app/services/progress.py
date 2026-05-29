def get_progress_by_plan (pb, tenant, plan):
    return pb.collection("plan_progress").get_first_list_item(
        f'tenant="{tenant}" && plan="{plan}"'
)

def create_progress(pb, tenant, data: dict):
        payload = {
            **data,
            "tenant": tenant,
        }
        return pb.collection("plan_progress").create(payload)

def update_progress(pb, progress_id, data: dict):
        return pb.collection("plan_progress").update(progress_id, data)