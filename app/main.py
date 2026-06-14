# fast api imports
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.routes import marketing

# route imports
from .routes import auth
from .routes import dashboard
from .routes import trainee
from .routes import debug
from .routes import plan
from .routes import item
from .routes import profile
from .routes.user import dashboard as user_dashboard
from .routes import pwa

# middleware import
from app.middleware import TenantMiddleware

APP_VERSION = "0.1.0"
@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}

def get_current_version():
    with open("version.txt", "r") as f:
        return f.read().strip()

###disable default swagger ui
app = FastAPI(
    title="Gyme",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

# static folder
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# middleware
app.add_middleware(TenantMiddleware)

# include routers
app.include_router(dashboard.router)
app.include_router(debug.router)
app.include_router(auth.router)
app.include_router(trainee.router)
app.include_router(plan.router)
app.include_router(item.router)
app.include_router(profile.router)
app.include_router(user_dashboard.router)
app.include_router(pwa.router)
app.include_router(marketing.router)



# swagger ui
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