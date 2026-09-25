from fastapi import APIRouter, Request
from ..templates import templates
from fastapi.responses import RedirectResponse
from app.i18n import _

router = APIRouter(tags=["Profile"])


@router.get("/profile")
def plan_list(request: Request):
    tenant = request.state.tenant
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="pages/owner/profile/profile.html",
        context={
            "title": _("پروفایل"),
            "tenant": tenant,
            "user": user,
        },
    )
