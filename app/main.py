# fast api imports
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# route imports
from .routes import auth
from .routes import dashboard
from .routes import trainee
from app.routes.debug import router as debug_router

# middleware import
from app.middleware import TenantMiddleware


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
app.include_router(debug_router)
app.include_router(auth.router)
app.include_router(trainee.router)






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