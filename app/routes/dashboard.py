from fastapi import APIRouter, Request
from ..templates import templates

router = APIRouter(
    tags=["Dashboard"]
)
@router.get("/dashboard")
def dashboard(request: Request):
    user = {"name": "Demo User"}
    tenant = request.state.tenant
    return templates.TemplateResponse(
        request=request, 
        name="pages/dashboard.html", 
        context={
        "user": user,
        "tenant": tenant,
        "role": getattr(getattr(request.state, "user", None), "role", "trainee"),
        }
    )

