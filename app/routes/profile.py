from fastapi import APIRouter, Request, Form
from ..templates import templates
from fastapi.responses import RedirectResponse

router = APIRouter(
    tags=["Profile"]
)

@router.get("/profile")
async def plan_list (request: Request):
    tenant = request.state.tenant
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/profile/profile.html",
        context={
        "title" : "پروفایل",
        "tenant": tenant,
        "user": user,
        }
    )