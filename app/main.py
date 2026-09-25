# fast api imports
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.routes import auth
from .routes import dashboard
from .routes import trainee
from .routes import debug
from .routes import plan
from .routes import item
from .routes import coach
from app.routes import progress_logs
from .routes import profile
from .routes.user import dashboard as user_dashboard
from .routes.user import profile as user_profile
from .routes.user import plan as user_plan
from .routes import pwa
from .templates import templates

# logging config
try:
    from app.logging_config import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("structlog not available — falling back to stdlib logging")

# middleware import
from app.middleware import TenantMiddleware

# i18n: locale switch endpoint (cookie + redirect)
from app.i18n import ENABLED_LOCALES, LOCALE_COOKIE

# swagger/docs only in dev
IS_PROD = os.getenv("ENV", "dev").lower() == "production"

app = FastAPI(
    title="Gyme",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if not IS_PROD else None,
    # Security: hide server header via docs? Starlette adds server header by default; we remove later via middleware
)

# Trusted hosts & proxy headers are handled in TenantMiddleware + uvicorn proxy_headers; add explicit trusted hosts if configured
from starlette.middleware.trustedhost import TrustedHostMiddleware
allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "")
if allowed_hosts_env:
    allowed = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
    # Always allow health checks / localhost for dev
    if not IS_PROD:
        allowed += ["localhost", "127.0.0.1", "testserver"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)
else:
    # Default: allow any in dev, restrict in prod would need env
    if IS_PROD:
        # In prod without ALLOWED_HOSTS, log warning but still enforce via TenantMiddleware host validation
        import logging as _logging

        _logging.getLogger(__name__).warning(
            "ALLOWED_HOSTS not set in production - relying on tenant host validation only"
        )

APP_VERSION = "0.9.1"
templates.env.globals["app_version"] = APP_VERSION

# static folder
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# middleware
app.add_middleware(TenantMiddleware)

# include routers
app.include_router(dashboard.router)
if not IS_PROD:
    app.include_router(debug.router)
app.include_router(auth.router)
app.include_router(trainee.router)
app.include_router(plan.router)
app.include_router(item.router)
app.include_router(coach.router)
app.include_router(progress_logs.router)
app.include_router(profile.router)
app.include_router(user_dashboard.router)
app.include_router(user_profile.router)
app.include_router(user_plan.router)
app.include_router(pwa.router)


@app.get("/locale/{code}", include_in_schema=False)
def switch_locale(code: str, next: str = "/"):
    """Persist an explicit language choice (allowlisted) and return to the page.

    GET with a cookie side effect on purpose: a UI preference, not a data
    mutation — keeps the switcher plain links (keyboard accessible, no JS).
    """
    if code not in ENABLED_LOCALES:
        return JSONResponse({"error": {"code": "unsupported_locale"}}, status_code=404)
    next_url = next
    if not next_url.startswith("/") or next_url.startswith("//") or "://" in next_url:
        next_url = "/"  # open-redirect guard
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        LOCALE_COOKIE,
        code,
        max_age=365 * 24 * 3600,
        samesite="lax",
        path="/",
    )
    return response


# swagger ui
if not IS_PROD:

    @app.get("/docs", include_in_schema=False)
    def custom_docs():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gyme API Docs</title>
            <link rel="stylesheet" type="text/css" href="/static/swagger/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>

            <script src="/static/swagger/swagger-ui-bundle.js"></script>
            <script src="/static/swagger/swagger-ui-standalone-preset.js"></script>
            <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "StandaloneLayout"
                });
            };
            </script>
        </body>
        </html>
        """)
