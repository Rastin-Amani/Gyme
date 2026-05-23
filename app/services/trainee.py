from app.pb import pb

def list_trainees(pb, tenant, page=1, per_page=50):
        return pb.collection("trainees").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": f'tenant="{tenant}"',
                "sort": "-created"
                }
        )

def get_trainee_by_id (pb, tenant, id):
        return pb.collection("trainees").get_one(id,
            query_params={
                "filter": f'tenant="{tenant}"',
                }
        )

def create_trainee(pb, tenant, data: dict):
        payload = {
            **data,
            "tenant": tenant,
        }
        return pb.collection("trainees").create(payload)

def update_trainee(pb, trainee_id, data: dict):
        return pb.collection("trainees").update(trainee_id, data)

def delete_trainee(pb, tenant, trainee_id):
        return pb.collection("trainees").delete(trainee_id, tenant)
