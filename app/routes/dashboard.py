from fastapi import APIRouter, Request
from ..templates import templates

router = APIRouter()

@router.get("/dashboard")
def dashboard(request: Request):
    user = {"name": "Demo User"}
    return templates.TemplateResponse(
        request=request, 
        name="pages/dashboard.html", 
        context={"user": user}
    )

