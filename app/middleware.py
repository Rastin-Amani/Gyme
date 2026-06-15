from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb

# 🟢 1. Define routes that anyone can access without a token.
# Notice "/" is REMOVED from this list so .startswith() doesn't match everything.
PUBLIC_PATHS = [
    "/login",
    "/static",          # Required so your CSS/JS loads on the login page!
    "/manifest.json",   # Required for your PWA
    "/sw.js",           # Required for offline caching
    "/favicon.ico"
]

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- Tenant detection ----
        host = request.headers.get("host", "").split(":")[0]

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
                # Load token into the PocketBase instance
                pb.auth_store.save(token, None)
                
                # Verify token with the server. 
                # If the password was just changed, this will throw a 401 error!
                pb.collection("users").auth_refresh()

                user = pb.auth_store.model
                request.state.user = user
                request.state.role = getattr(user, "role", "trainee")
                is_authenticated = True

            except Exception as e:
                # If the token is expired, invalid, or revoked, clear the store
                # and treat them as an anonymous user.
                print("Auth error:", e)
                pb.auth_store.clear()

        # ---- 🟢 2. The Global Redirect Logic ----
        path = request.url.path
        
        # Explicitly allow the exact root path "/", THEN check the subfolders
        is_public = (path == "/") or any(path.startswith(p) for p in PUBLIC_PATHS)

        # If they aren't logged in AND they are trying to access a private route
        if not is_authenticated and not is_public:
            # 303 (See Other) is the standard for redirecting state changes safely
            return RedirectResponse(url="/login", status_code=303)

        # Proceed normally if they are authenticated OR visiting a public page
        response = await call_next(request)
        return response