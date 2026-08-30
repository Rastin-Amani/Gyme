import time
import threading

from starlette.concurrency import run_in_threadpool

from app.pb import pb
from app.security import pb_escape, is_valid_host

# ponytail: in-process TTL cache (60s hit / 5s miss); multi-instance deploys get
# per-instance staleness only — tenant rows are near-static, acceptable.
_TENANT_TTL = 60.0
_TENANT_MISS_TTL = 5.0
_tenant_cache: dict = {}
_cache_lock = threading.Lock()


def _lookup_tenant(domain: str):
    safe_domain = pb_escape(domain)
    try:
        return pb.collection("tenants").get_first_list_item(f'domain="{safe_domain}"')
    except Exception:
        return None


async def get_tenant_by_domain(domain: str):
    # Defense: reject invalid/malicious hosts before DB query
    if not domain or not is_valid_host(domain):
        return None
    now = time.monotonic()
    with _cache_lock:
        entry = _tenant_cache.get(domain)
        if entry and entry[0] > now:
            return entry[1]
    tenant = await run_in_threadpool(_lookup_tenant, domain)
    with _cache_lock:
        _tenant_cache[domain] = (
            now + (_TENANT_TTL if tenant is not None else _TENANT_MISS_TTL),
            tenant,
        )
    return tenant
