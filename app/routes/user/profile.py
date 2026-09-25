from fastapi import APIRouter, Request
from ...templates import templates
from fastapi.responses import RedirectResponse
from app.i18n import _

router = APIRouter(tags=["Trainee Profile"])


@router.get("/user/profile")
def plan_list(request: Request):
    tenant = request.state.tenant
    user = request.state.user

    if user.role != "trainee":
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="pages/user/profile/profile.html",
        context={
            "title": _("پروفایل"),
            "tenant": tenant,
            "user": user,
        },
    )
