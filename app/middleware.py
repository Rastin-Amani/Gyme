from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- 🏠 1. Tenant Detection ----
        host = request.headers.get("host", "").split(":")[0]

        tenant = await get_tenant_by_domain(host)
        request.state.tenant = tenant

        # ---- 🔐 2. Auth Context Injection ----
        pb = get_pb()
        request.state.pb = pb
        request.state.user = None

        # Changed the default fallback role from "trainee" to "member" for generic SaaS compatibility!
        request.state.role = None

        token = request.cookies.get("pb_auth")

        if token:
            try:
                # Load token into the PocketBase instance
                pb.auth_store.save(token, None)

                # Verify token with the server.
                pb.collection("users").auth_refresh()

                user = pb.auth_store.model
                request.state.user = user

                # Fetching role (generic boilerplate standard)
                request.state.role = getattr(user, "role", "member")

            except Exception as e:
                # If the token is expired, invalid, or revoked, clear the store
                print("Auth error:", e)
                pb.auth_store.clear()

        # ---- 🚦 3. Proceed Without Blocking ----
        # The global redirect logic and PUBLIC_PATHS have been removed.
        # Now, anyone can access the routes, and FastAPI will handle specific
        # protections at the route level via Dependencies if needed.
        response = await call_next(request)
        return response
