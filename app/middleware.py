import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import RedirectResponse
from structlog import get_logger

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb
from app.logging_config import bind_request_context, clear_request_context

# 🟢 1. Define routes that anyone can access without a token.
# Notice "/" is REMOVED from this list so .startswith() doesn't match everything.
PUBLIC_PATHS = [
    "/login",
    "/static",  # Required so your CSS/JS loads on the login page!
    "/manifest.json",  # Required for your PWA
    "/sw.js",  # Required for offline caching
    "/favicon.ico",
]

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- Request ID for correlation ----
        req_id = str(uuid.uuid4())[:8]
        request.state.req_id = req_id

        # ---- Tenant detection ----
        host = request.headers.get("host", "").split(":")[0]

        tenant = await get_tenant_by_domain(host)
        request.state.tenant = tenant
        tenant_id = getattr(tenant, "id", None)

        # Bind request context for all logs in this request
        bind_request_context(req_id=req_id, tenant_id=tenant_id)

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
                logger.warning("auth_refresh_failed", error=str(e))
                pb.auth_store.clear()

        # ---- 🟢 2. The Global Redirect Logic ----
        path = request.url.path

        # Root path: main-tenant → public landing; sub-tenant → redirect
        if path == "/":
            is_main = (
                getattr(request.state.tenant, "is_main", False) if request.state.tenant else False
            )
            if not is_main:
                return RedirectResponse(
                    url="/dashboard" if is_authenticated else "/login",
                    status_code=303,
                )

        # Explicitly allow the exact root path "/", THEN check the subfolders
        is_public = (path == "/") or any(path.startswith(p) for p in PUBLIC_PATHS)

        # If they aren't logged in AND they are trying to access a private route
        if not is_authenticated and not is_public:
            # 303 (See Other) is the standard for redirecting state changes safely
            return RedirectResponse(url="/login", status_code=303)

        # ---- Request lifecycle log ----
        start = time.time()
        method = request.method
        url = str(request.url.path)
        role = request.state.role

        logger.info("request.started", method=method, path=url, role=role)

        try:
            response = await call_next(request)
        except Exception as e:
            elapsed = time.time() - start
            logger.exception(
                "request.error",
                method=method,
                path=url,
                role=role,
                duration_ms=round(elapsed * 1000),
            )
            raise

        elapsed = time.time() - start
        status = response.status_code
        logger.info(
            "request.completed",
            method=method,
            path=url,
            role=role,
            status=status,
            duration_ms=round(elapsed * 1000),
        )

        clear_request_context()
        return response
