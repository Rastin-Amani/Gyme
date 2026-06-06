from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb

# 🟢 1. Define routes that anyone can access without a token
PUBLIC_PATHS = [
    "/login",
    "/static",          # Required so your CSS/JS loads on the login page!
    "/manifest.json",   # Required for your PWA
    "/sw.js",           # Required for offline caching
    "/favicon.ico",
    "/"
]

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- Tenant detection ----
        host = request.headers.get("host", "").split(":")[0]
        # print(f"DEBUG: Checking host: {host}") # You can comment this out in production

        tenant = await get_tenant_by_domain(host)
        request.state.tenant = tenant

        # ---- Auth detection ----
        pb = get_pb()
        request.state.pb = pb 
        request.state.user = None
        request.state.role = None
        
        is_authenticated = False
        token = request.cookies.get("pb_auth")

        if token:
            try:
                # Load token
                pb.auth_store.save(token, None)
                # Verify token and get user
                pb.collection("users").auth_refresh()

                user = pb.auth_store.model
                request.state.user = user
                request.state.role = getattr(user, "role", "trainee")
                is_authenticated = True

            except Exception as e:
                print("Auth error:", e)
                # If the token is expired/invalid, they are treated as anonymous
                pb.auth_store.clear()

        # ---- 🟢 2. The Global Redirect Logic ----
        path = request.url.path
        
        # Check if the current URL starts with any of the public paths
        is_public = any(path.startswith(p) for p in PUBLIC_PATHS)

        if not is_authenticated and not is_public:
            # Instantly bounce them to the login page.
            # Using status_code=303 (See Other) is the standard for redirecting after state changes.
            return RedirectResponse(url="/login", status_code=303)

        # Proceed normally if they are authenticated OR visiting a public page
        response = await call_next(request)
        return response