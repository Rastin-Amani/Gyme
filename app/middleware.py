from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- Tenant detection ----
        host = request.headers.get("host", "").split(":")[0]
        print(f"DEBUG: Checking host: {host}")

        tenant = await get_tenant_by_domain(host)
        request.state.tenant = tenant

        # ---- Auth detection ----
        pb = get_pb()

        request.state.user = None
        request.state.role = None

        token = request.cookies.get("pb_auth")

        if token:
            try:
                # load token
                pb.auth_store.save(token, None)

                # verify token and get user
                pb.collection("users").auth_refresh()

                user = pb.auth_store.model

                request.state.user = user
                request.state.role = getattr(user, "role", "trainee")

            except Exception as e:
                print("Auth error:", e)

        response = await call_next(request)
        return response