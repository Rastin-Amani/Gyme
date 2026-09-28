import time
import uuid
import os
import ipaddress
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from structlog import get_logger

from app.services.tenants import get_tenant_by_domain
from app.pb import get_pb
from app.logging_config import bind_request_context, clear_request_context
from app.security import is_valid_host
from app.i18n import LOCALE_COOKIE, set_request_locale

# Public FastAPI API and infrastructure routes; the browser UI is served by SvelteKit.
PUBLIC_PATHS = [
    "/login",
    "/logout",
    "/static",
    "/docs",
    "/openapi.json",
    "/manifest.json",
    "/favicon.ico",
    "/locale",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/tenant/branding",
    "/api/v1/locale",
]

IS_PROD = os.getenv("ENV", "dev").lower() == "production"

logger = get_logger(__name__)


def _load_auth(pb, token: str):
    """Blocking PocketBase token verification. Runs in threadpool."""
    # Load token into the PocketBase instance
    pb.auth_store.save(token, None)

    # Verify token with the server.
    # If the password was just changed, this will throw a 401 error!
    pb.collection("users").auth_refresh()

    return pb.auth_store.model


def _host_matches(header_value: str, host_header: str) -> bool:
    try:
        parsed = urlparse(header_value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            return False
        return parsed.netloc.lower().rstrip(".") == host_header.lower().rstrip(".")
    except Exception:
        return False


def _is_trusted_proxy(request: Request) -> bool:
    """Trust forwarded host/proto only when the immediate peer is configured."""
    peer = getattr(request.client, "host", "") if request.client else ""
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for entry in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(","):
        try:
            if address in ipaddress.ip_network(entry.strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


def _client_ip(request: Request, trusted_proxy: bool) -> str:
    if trusted_proxy:
        forwarded = request.headers.get("x-real-client-ip", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return getattr(request.client, "host", "unknown") if request.client else "unknown"


def _api_error(request: Request, status_code: int, detail: str):
    response = JSONResponse(status_code=status_code, content={"detail": detail})
    response.headers.update(
        {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-store, private",
        }
    )
    if (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
        or IS_PROD
    ):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
    return response


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ---- Locale resolution (cookie preference, allowlisted, default en) ----
        set_request_locale(request.cookies.get(LOCALE_COOKIE))

        # Liveness probe: must never touch PocketBase, so container healthchecks
        # report the APP's state, not PocketBase's. During a PB outage this keeps
        # the container from being flagged unhealthy and restart-looped.
        path = request.url.path
        if path == "/healthz":
            return JSONResponse({"status": "ok"})

        # ---- Request ID for correlation ----
        req_id = str(uuid.uuid4())[:8]
        request.state.req_id = req_id

        # ---- Tenant detection (with Host validation) ----
        trusted_proxy = _is_trusted_proxy(request)
        request.state.client_ip = _client_ip(request, trusted_proxy)
        # Forwarded host/proto are attacker-controlled unless the direct peer is trusted.
        raw_host = (
            request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
            if trusted_proxy and request.headers.get("x-forwarded-host")
            else request.headers.get("host", "")
        )
        host = (urlparse("//" + raw_host).hostname or "").strip().lower()
        # Validate host to prevent header injection
        if not is_valid_host(host):
            # Do not attempt tenant lookup for clearly invalid hosts
            logger.warning("invalid_host", host=raw_host)
            host = ""
            tenant = None
        elif path.startswith("/static"):
            # StaticFiles never reads the tenant; skip the PB lookup so asset
            # requests stay instant even while PocketBase is degraded.
            tenant = None
        else:
            tenant = await get_tenant_by_domain(host)
        request.state.tenant = tenant
        tenant_id = getattr(tenant, "id", None)

        # Bind request context for all logs in this request
        bind_request_context(req_id=req_id, tenant_id=tenant_id)

        is_api = path == "/api/v1" or path.startswith("/api/v1/")

        # ---- Auth detection ----
        pb = get_pb()
        request.state.pb = pb
        request.state.user = None
        request.state.role = None

        is_authenticated = False
        token = request.cookies.get("pb_auth")

        is_public = any(path == p or path.startswith(p + "/") for p in PUBLIC_PATHS)
        needs_auth = not is_public or path in {
            "/",
            "/login",
            "/logout",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
        }

        if token and needs_auth:
            # Basic token hygiene: limit length to prevent DoS on auth_refresh
            if len(token) > 8192:
                logger.warning("auth_token_too_long")
                pb.auth_store.clear()
            else:
                try:
                    user = await run_in_threadpool(_load_auth, pb, token)
                    if tenant_id and str(getattr(user, "tenant", "")) != str(tenant_id):
                        raise ValueError("Authenticated user belongs to another tenant")
                    request.state.user = user
                    request.state.role = getattr(user, "role", "trainee")
                    is_authenticated = True

                except Exception as e:
                    # If the token is expired, invalid, or revoked, clear the store
                    # and treat them as an anonymous user.
                    logger.warning("auth_refresh_failed", error=str(e))
                    pb.auth_store.clear()

        # ---- CSRF defense for state-changing authenticated requests ----
        method = request.method
        csrf_required = is_authenticated or path == "/api/v1/auth/login"
        if csrf_required and method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            external_host = raw_host.lower()
            scheme = (
                request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
                if trusted_proxy
                else request.url.scheme
            )
            if scheme not in {"http", "https"}:
                scheme = request.url.scheme
            source = origin or referer
            same_origin = bool(
                source
                and _host_matches(source, external_host)
                and urlparse(source).scheme == scheme
            )
            # Only the trusted SvelteKit BFF may omit browser Origin/Referer.
            bff_request = trusted_proxy and is_api and not origin and not referer
            if not same_origin and not bff_request:
                logger.warning(
                    "csrf_blocked",
                    path=path,
                    method=method,
                    origin=origin,
                    referer=referer,
                    host=external_host,
                )
                if is_api:
                    return _api_error(request, 403, "CSRF validation failed")
                return HTMLResponse("Forbidden", status_code=403)

        # ---- 🟢 2. The Global Redirect Logic ----
        # The marketing site lives outside this app; "/" always points into the app.
        if path == "/":
            return RedirectResponse(
                url="/dashboard" if is_authenticated else "/login",
                status_code=303,
            )

        # Unknown host / unresolved tenant on a private route: never let the
        # request reach handlers that dereference request.state.tenant.id.
        if tenant is None and not is_public and path != "/":
            if is_api:
                return _api_error(request, 404, "Tenant not found")
            return RedirectResponse(url="/login", status_code=303)

        # If they aren't logged in AND they are trying to access a private route
        if not is_authenticated and not is_public and path != "/":
            if is_api:
                return _api_error(request, 401, "Authentication required")
            return RedirectResponse(url="/login", status_code=303)

        # ---- Request lifecycle log ----
        start = time.time()
        method = request.method
        url = str(request.url.path)
        role = request.state.role

        logger.info("request.started", method=method, path=url, role=role)

        try:
            response = await call_next(request)
        except Exception:
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
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        # HSTS only when https
        try:
            if (
                request.url.scheme == "https"
                or request.headers.get("x-forwarded-proto") == "https"
                or IS_PROD
            ):
                response.headers.setdefault(
                    "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
                )
        except Exception:
            pass
        # SvelteKit hydration uses inline scripts; no legacy external frontend scripts are allowed.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
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
