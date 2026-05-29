from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from ..templates import templates
from app.services.auth import login_user

router = APIRouter(
    tags=["Authentication"]
)

@router.get("/login")
def login_page(request: Request):
    tenant = request.state.tenant
    user = request.state.user

    if user:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="pages/auth/login.html",
        context={"title":"ورود",
        "tenant": tenant,
        }
    )

@router.post("/login")
def login(request: Request, identity: str = Form(...), password: str = Form(...)):
    tenant = request.state.tenant
    result = login_user(identity, password, tenant.id)

    if not result["ok"]:
        return templates.TemplateResponse(
            request=request,
            name="pages/auth/login.html",
            context={
                "error": result["error"]
            } 
        )

    user = result["user"]
    target_url = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"

    response = RedirectResponse(url=target_url, status_code=303)
    response.set_cookie("pb_auth", result["token"], httponly=True, secure=False)
    return response
