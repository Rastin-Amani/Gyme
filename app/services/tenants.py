from app.pb import pb
from app.security import pb_escape, is_valid_host


async def get_tenant_by_domain(domain: str):
    # Defense: reject invalid/malicious hosts before DB query
    if not domain or not is_valid_host(domain):
        return None
    safe_domain = pb_escape(domain)
    try:
        return pb.collection("tenants").get_first_list_item(f'domain="{safe_domain}"')
    except Exception:
        return None
