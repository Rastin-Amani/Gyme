# fast api imports
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import structlog

from app.routes import marketing

# route imports
from .routes import auth
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

# swagger/docs only in dev
IS_PROD = os.getenv("ENV", "dev").lower() == "production"

app = FastAPI(
    title="Gyme",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if not IS_PROD else None,
)

APP_VERSION = "0.8.0"
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
app.include_router(marketing.router)


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
