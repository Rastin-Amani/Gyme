def list_plans(pb, tenant, page=1, per_page=50):
        return pb.collection("plans").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": f'tenant="{tenant}"',
                "sort": "-created",
                "expand": "coach,trainee",
                }
        )

def get_plan_by_id (pb, tenant, id):
        return pb.collection("plans").get_one(id,
            query_params={
                "filter": f'tenant="{tenant}"',
                "expand": "coach,trainee",
                }
        )

def get_plans_by_trainee (pb, tenant, trainee):
        return pb.collection("plans").get_full_list(
            query_params={
                "filter":
                f'tenant="{tenant}" && trainee="{trainee}"',
                }
        )

def create_plan(pb, tenant, data: dict):
        payload = {
            **data,
            "tenant": tenant,
        }
        return pb.collection("plans").create(payload)

def update_plan(pb, id, data: dict):
        return pb.collection("plans").update(id, data)

def delete_plan(pb, tenant, plan_id):
        return pb.collection("plans").delete(plan_id, tenant)
