from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templaets = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index (request : Request):
    return templaets.TemplateResponse("index.html", {"request": request})