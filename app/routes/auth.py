from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from ..templates import templates
from app.services.auth import login_user, update_user_password
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

@router.get("/change-password")
def change_password_page(request: Request):
    tenant = getattr(request.state, 'tenant', None)
    user = getattr(request.state, 'user', None)

    # 1. Protect the route - only logged-in users can change their password
    if not user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        request=request,
        name="pages/auth/change_password.html",
        context={
            "title": "",
            "tenant": tenant,
            "user": user
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

@router.post("/change-password")
async def handle_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    user = getattr(request.state, 'user', None)
    pb = getattr(request.state, 'pb', None)
    tenant = getattr(request.state, 'tenant', None)

    if not user or not pb:
        headers = hx_toast("شما وارد نشده‌اید!", "error")
        headers["HX-Redirect"] = "/login"
        return HTMLResponse(content="", headers=headers)

    if new_password != confirm_password:
        headers = hx_toast("رمز عبور جدید و تکرار آن یکسان نیستند.", "warning")
        return HTMLResponse(content="", headers=headers)
        
    if len(new_password) < 8:
        headers = hx_toast("رمز عبور باید حداقل ۸ کاراکتر باشد.", "warning")
        return HTMLResponse(content="", headers=headers)

    collection_name = getattr(user, 'collectionName', 'users') 
    
    # 1. Update the password
    result = update_user_password(
        pb=pb,
        collection_name=collection_name,
        user_id=user.id,
        old_password=old_password,
        new_password=new_password,
        confirm_password=confirm_password
    )

    if not result.get("ok"):
        headers = hx_toast(result.get("error"), "error")
        return HTMLResponse(content="", headers=headers)

    # 🟢 2. Seamlessly re-authenticate with the NEW password to get a fresh token
    # Note: Ensure user.email (or username) is available on the user model
    identity = getattr(user, 'email', '') 
    login_result = login_user(identity, new_password, tenant.id)

    # 3. Setup Success Response & Redirect
    headers = hx_toast("رمز عبور با موفقیت تغییر کرد! 🔒", "success")
    target_url = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"
    headers["HX-Redirect"] = target_url
    
    response = HTMLResponse(content="", headers=headers)

    # 🟢 4. Inject the new cookie so they don't get kicked out!
    if login_result.get("ok"):
        response.set_cookie(
            key="pb_auth", 
            value=login_result["token"], 
            httponly=True, 
            secure=False, # Set to True in production!
            samesite="lax"
        )
        
    return response