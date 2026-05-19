from fastapi import APIRouter, Request
from ..main import templates

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request):
    user = {"name": "Demo User"}  # temporary
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
