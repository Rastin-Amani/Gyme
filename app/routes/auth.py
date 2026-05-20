from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from ..templates import templates
from app.services.auth import login_user

router = APIRouter()

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/login.html",
        context={}
    )

@router.post("/login")
def login(request: Request, identity: str = Form(...), password: str = Form(...)):
    tenant = request.state.tenant
    result = login_user(identity, password, tenant.id)

    if not result["ok"]:
        return templates.TemplateResponse(
            request=request,
            name="pages/login.html",
            context={"error": result["error"]}
        )

    user = result["user"]

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("pb_auth", result["token"], httponly=True, secure=True)
    return response
