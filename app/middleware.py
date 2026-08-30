import time
import uuid
import os
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from structlog import get_logger

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb
from app.logging_config import bind_request_context, clear_request_context
from app.security import is_valid_host, cookie_secure_flag

# 🟢 1. Define routes that anyone can access without a token.
# Notice "/" is REMOVED from this list so .startswith() doesn't match everything.
PUBLIC_PATHS = [
    "/login",
    "/logout",
    "/static",  # Required so your CSS/JS loads on the login page!
    "/manifest.json",  # Required for your PWA
    "/sw.js",  # Required for offline caching
    "/favicon.ico",
    "/lead/submit",  # public marketing form
]

IS_PROD = os.getenv("ENV", "dev").lower() == "production"

CSRF_EXEMPT_PATHS = [
    "/login",
    "/lead/submit",
    "/logout",
]

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # ---- Request ID for correlation ----
        req_id = str(uuid.uuid4())[:8]
        request.state.req_id = req_id

        # ---- Tenant detection (with Host validation) ----
        # Use X-Forwarded-Host when behind trusted proxy, fallback to Host
        raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        host = raw_host.split(":")[0].strip().lower()
        # Validate host to prevent header injection
        if not is_valid_host(host):
            # Do not attempt tenant lookup for clearly invalid hosts
            logger.warning("invalid_host", host=raw_host)
            host = ""
            tenant = None
        else:
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
            # Basic token hygiene: limit length to prevent DoS on auth_refresh
            if len(token) > 8192:
                logger.warning("auth_token_too_long")
                pb.auth_store.clear()
            else:
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

        # ---- CSRF defense for state-changing authenticated requests ----
        path = request.url.path
        method = request.method
        if is_authenticated and method in ("POST", "PUT", "PATCH", "DELETE"):
            is_exempt = any(path == p or path.startswith(p) for p in CSRF_EXEMPT_PATHS)
            if not is_exempt:
                # Defense 1: custom header (HTMX sends HX-Request, fetch callers must send X-Requested-With)
                has_custom_header = (
                    request.headers.get("hx-request") == "true"
                    or request.headers.get("x-requested-with") == "XMLHttpRequest"
                    or request.headers.get("hx-boosted") is not None
                )
                # Defense 2: Origin / Referer must match Host when present
                origin = request.headers.get("origin", "")
                referer = request.headers.get("referer", "")
                host_header = request.headers.get("host", "").split(":")[0].lower()
                origin_ok = True
                referer_ok = True
                if origin:
                    try:
                        from urllib.parse import urlparse
                        origin_host = urlparse(origin).hostname or ""
                        origin_ok = origin_host.lower() == host_header
                    except Exception:
                        origin_ok = False
                elif referer:
                    try:
                        from urllib.parse import urlparse
                        referer_host = urlparse(referer).hostname or ""
                        referer_ok = referer_host.lower() == host_header
                    except Exception:
                        referer_ok = False
                # Block if neither custom header nor valid origin/referer
                # Allow if either custom header present OR origin/referer matches
                if not has_custom_header and not (origin_ok and referer_ok):
                    # If both origin and referer missing and no custom header, treat as potential CSRF
                    # Still allow same-origin form POST without HX header if Origin matches Host (browser sends Origin for POST)
                    # If browser didn't send Origin/Referer, we require custom header
                    if not origin and not referer and not has_custom_header:
                        logger.warning("csrf_blocked_missing_headers", path=path, method=method)
                        # For HTMX requests, return toast error; for normal, 403
                        if request.headers.get("hx-request"):
                            from fastapi.responses import HTMLResponse
                            import json
                            headers = {"HX-Trigger": json.dumps({"show-toast": {"message": "درخواست نامعتبر (CSRF)", "type": "error"}})}
                            return HTMLResponse(content="", status_code=403, headers=headers)
                        return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
                if not origin_ok or not referer_ok:
                    logger.warning("csrf_blocked_origin_mismatch", path=path, origin=origin, referer=referer, host=host_header)
                    if request.headers.get("hx-request"):
                        from fastapi.responses import HTMLResponse
                        import json
                        headers = {"HX-Trigger": json.dumps({"show-toast": {"message": "درخواست نامعتبر (CSRF)", "type": "error"}})}
                        return HTMLResponse(content="", status_code=403, headers=headers)
                    return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

        # ---- 🟢 2. The Global Redirect Logic ----
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

        # Tenant not found: for private tenants, do not leak existence; treat as main?
        # If tenant is None and host is non-empty, we still allow public paths but block private?
        # Already handled via tenant_id bound to None

        # Explicitly allow the exact root path "/", THEN check the subfolders
        is_public = (path == "/") or any(path.startswith(p) for p in PUBLIC_PATHS)

        # If they aren't logged in AND they are trying to access a private route
        if not is_authenticated and not is_public:
            # 303 (See Other) is the standard for redirecting state changes safely
            if request.headers.get("hx-request") == "true":
                # For HTMX, instruct client to redirect via header rather than 303 HTML
                resp = HTMLResponse(content="", status_code=401)
                resp.headers["HX-Redirect"] = "/login"
                return resp
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

        # ---- Security headers ----
        # Align with OWASP ASVS 14.4.7 / Cheat Sheets
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # HSTS only when https
        try:
            if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https" or IS_PROD:
                response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        except Exception:
            pass
        # Minimal CSP that allows current stack: HTMX, Alpine, Tailwind CDN not needed but allow self + inline styles/scripts hashed? Keep permissive but block object-src
        # Current app uses inline scripts for toasts etc., so unsafe-inline required temporarily. Harden gradually via nonces.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        # Clear auth cookie on 401/403 if stale token was used? Handled elsewhere, but ensure no caching of private pages
        response.headers.setdefault("Cache-Control", "no-store")
        # Ensure tenant-less requests don't cache
        if tenant_id is None and path not in PUBLIC_PATHS and path != "/":
            response.headers["Cache-Control"] = "no-store, private"

        clear_request_context()
        return response
