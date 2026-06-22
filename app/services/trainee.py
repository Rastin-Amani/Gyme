from pocketbase.errors import ClientResponseError
from datetime import datetime

def list_trainees(pb, tenant, page=1, per_page=50, query=None, gender=None, status=None,
                  min_birthdate=None, max_birthdate=None):
    # Build the base filter
    filters = [f'tenant="{tenant}"']
    
    # Search filter (name, phone, email)
    if query:
        search_terms = query.split()
        search_conditions = []
        for term in search_terms:
            search_conditions.append(f'user.first_name ~ "{term}" || user.last_name ~ "{term}" || user.phone ~ "{term}" || user.email ~ "{term}"')
        if search_conditions:
            filters.append('(' + ' || '.join(search_conditions) + ')')
            
    # Gender filter
    if gender:
        filters.append(f'gender="{gender}"')
    
    # Status filter
    if status:
        filters.append(f'status="{status}"')
    
    # Date range filters
    if min_birthdate:
        filters.append(f'birthdate >= "{min_birthdate}"')
    if max_birthdate:
        filters.append(f'birthdate <= "{max_birthdate}"')
    
    # Join all filters
    filter_str = ' && '.join(filters)
    
    # Build query params
    query_params = {
        "sort": "-created",
        "expand": "user"
    }
    
    # Add filter if not empty
    if filter_str:
        query_params["filter"] = filter_str
    
    return pb.collection("trainees").get_list(
        page=page,
        per_page=per_page,
        query_params=query_params
    )

def get_trainee_by_id(pb, tenant, id):
    return pb.collection("trainees").get_first_list_item(
        f'tenant="{tenant}" && id="{id}"',
        query_params={
            "expand": "user"
        }
    )

def get_trainee_by_user(pb, tenant, user):
    try:
        return pb.collection("trainees").get_first_list_item(
            f'tenant="{tenant}" && user="{user}"',
            query_params={
                "expand": "user"
            }
        )
    except ClientResponseError as e:
        if e.status == 404:
            return None
        raise

def create_trainee(pb, tenant, data: dict):
    payload = {
        **data,
        "tenant": tenant,
    }
    # Optional: If you return this directly to a template, you might want to fetch it again with expand="user"
    return pb.collection("trainees").create(payload)

def update_trainee(pb, trainee_id, data: dict):
    return pb.collection("trainees").update(trainee_id, data)

def delete_trainee(pb, tenant, trainee_id):
    # Note: PocketBase Python SDK usually just takes (id) for delete, but if you have a custom wrapper, keep as is.
    return pb.collection("trainees").delete(trainee_id)