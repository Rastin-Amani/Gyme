from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.services.tenants import get_tenant_by_domain

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        print(f"DEBUG: Checking host: {host}") 
        tenant = await get_tenant_by_domain(host)

        request.state.tenant = tenant

        return await call_next(request)
