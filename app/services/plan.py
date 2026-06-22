def list_plans(pb, tenant, page=1, per_page=50, query="", type=None, coach_id=None):
        filter_conditions = [f'tenant="{tenant}"']
        if query:
            # Search in trainee's first/last name or coach's first/last name
            # We'll use a filter that expands trainee.user and coach and then searches on those fields
            # However, PocketBase does not support searching on expanded fields directly in the filter.
            # Instead, we can use the `filter` with `~` (contains) on the expanded fields if we expand them.
            # But note: we are already expanding coach and trainee.user.
            # We can do: (trainee.user.first_name ~ "query" || trainee.user.last_name ~ "query" || coach.first_name ~ "query" || coach.last_name ~ "query")
            # However, note that the expand fields are not directly queryable in the filter unless we use the expanded field's name.
            # In PocketBase, when you expand a field, you can refer to its subfields in the filter by using the expanded field's name and the subfield.
            # Example: expand=trainee.user -> then we can use trainee.user.first_name in filter.
            filter_conditions.append(f'(trainee.user.first_name ~ "{query}" || trainee.user.last_name ~ "{query}" || coach.first_name ~ "{query}" || coach.last_name ~ "{query}")')
        if type:
            filter_conditions.append(f'type="{type}"')
        if coach_id:
            filter_conditions.append(f'coach="{coach_id}"')
        
        return pb.collection("plans").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": " && ".join(filter_conditions),
                "sort": "-created",
                "expand": "coach,trainee.user",
                }
        )

def get_plan_by_id (pb, tenant, id):
        return pb.collection("plans").get_one(id,
            query_params={
                "filter": f'tenant="{tenant}"',
                "expand": "coach,trainee.user",
                }
        )

def get_plans_by_trainee (pb, tenant, trainee):
        return pb.collection("plans").get_full_list(
            query_params={
                "filter":
                f'tenant="{tenant}" && trainee="{trainee}"',
                "sort": "status,-updated",                
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
