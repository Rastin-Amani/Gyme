from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import dashboard, clients

app = FastAPI()

# static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# template engine
templates = Jinja2Templates(directory="app/templates")

# include routers
app.include_router(dashboard.router)
app.include_router(clients.router)
