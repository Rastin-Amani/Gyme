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

def get_trainee(pb, tenant, trainee_id):
        return pb.collection("trainees").get_first_list_item(
            f'id="{trainee_id}" && tenant="{tenant}"'
        )

def update_trainee(pb, tenant, trainee_id, data: dict):
        # Optional safety check: ensure tenant match before update
        return pb.collection("trainees").update(trainee_id, data, tenant)

def delete_trainee(pb, tenant, trainee_id):
        return pb.collection("trainees").delete(trainee_id, tenant)
