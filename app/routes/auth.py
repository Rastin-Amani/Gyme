from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from ..templates import templates
from app.services.auth import login_user
from app.utils import hx_toast

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
async def login(request: Request, identity: str = Form(...), password: str = Form(...)):
    
    # 1. Safe Tenant Extraction 🏢
    tenant = getattr(request.state, 'tenant', None)
    if not tenant:
        headers = hx_toast("خطای سیستم: باشگاه یافت نشد!", "error")
        return HTMLResponse(content="", headers=headers)

    # 2. Attempt Authentication 🔐
    result = login_user(identity, password, tenant.id)

    # 3. Handle Failure with HTMX Toasts 🚨
    if not result.get("ok"):
        error_msg = result.get("error", "ایمیل یا رمز عبور اشتباه است.")
        
        # Attach the beautiful DaisyUI toast to the response headers!
        headers = hx_toast(error_msg, "error")

        return templates.TemplateResponse(
            request=request,
            name="pages/auth/login.html",
            # 🟢 FIXED: We must pass 'tenant' so base.html can render the theme!
            context={
                "error": error_msg,
                "tenant": tenant
            },
            headers=headers
        )
    # 4. Handle Success & Role Routing 🧭
    user = result["user"]
    
    # Updated to point to your new owner dashboard path!
    target_url = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"

    # 5. Execute Redirect & Issue Cookie 🍪
    response = RedirectResponse(url=target_url, status_code=303)
    
    # WARNING: secure=True will silently fail on http://127.0.0.1!
    # Keep it False for local dev, and switch to True in production (HTTPS).
    response.set_cookie(
        key="pb_auth", 
        value=result["token"], 
        httponly=True, 
        secure=False, 
        samesite="lax"
    )
    
    return response