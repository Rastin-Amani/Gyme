from app.pb import pb

def list_plans(pb, tenant, page=1, per_page=50):
        return pb.collection("plans").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": f'tenant="{tenant}"',
                "sort": "-created",
                "expand": "coach",
                }
        )

def get_plan_by_id (pb, tenant, id):
        return pb.collection("plans").get_one(id,
            query_params={
                "filter": f'tenant="{tenant}"',
                "expand": "coach",
                }
        )

def create_plan(pb, tenant, data: dict):
        payload = {
            **data,
            "tenant": tenant,
        }
        return pb.collection("plans").create(payload)

def update_plan(pb, plan_id, data: dict):
        return pb.collection("plans").update(plan_id, data)

def delete_plan(pb, tenant, plan_id):
        return pb.collection("plans").delete(plan_id, tenant)
