from app.pb import pb

async def get_tenant_by_domain(domain: str):
    try:
        return pb.collection("tenants").get_first_list_item(
            f'domain="{domain}"'
        )
    except Exception:
        return None
