from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from ..templates import templates

router = APIRouter(
    tags=["Dashboard"]
)
@router.get("/dashboard")
def dashboard(request: Request):
    user = request.state.user
    tenant = request.state.tenant
    
    if user.role == "trainee":
        return RedirectResponse("/user/dashboard")

    return templates.TemplateResponse(
        request=request, 
        name="pages/dashboard.html", 
        context={
        "user": user,
        "tenant": tenant,
        }
    )

