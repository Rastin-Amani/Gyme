from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from ..templates import templates
from app.services.auth import login_user, update_user_password
from app.utils import hx_toast, hx_toast_now
from app.security import set_auth_cookie, clear_auth_cookie, validate_email
from app.i18n import _
import time
from collections import defaultdict

# Simple in-memory rate limiter for login (per IP + identity)
_login_attempts = defaultdict(list)  # key -> list[timestamps]
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SEC = 300  # 5 min


def _is_rate_limited(key: str) -> bool:
    now = time.time()
    attempts = _login_attempts[key]
    # prune old
    _login_attempts[key] = [t for t in attempts if now - t < LOGIN_WINDOW_SEC]
    return len(_login_attempts[key]) >= LOGIN_MAX_ATTEMPTS


def _record_attempt(key: str):
    _login_attempts[key].append(time.time())


router = APIRouter(tags=["Authentication"])


def _login_error(request: Request, tenant, message: str, status_code: int = 200):
    """Re-render the login page with a visible error (the form is not HTMX)."""
    return templates.TemplateResponse(
        request=request,
        name="pages/auth/login.html",
        context={"title": _("Log in"), "tenant": tenant, "error": message},
        headers=hx_toast(message, "error"),
        status_code=status_code,
    )


@router.get("/login")
def login_page(request: Request):
    tenant = request.state.tenant
    user = request.state.user

    if user:
        # Use role-based redirect, trainee goes to user dashboard
        target = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"
        return RedirectResponse(url=target)

    return templates.TemplateResponse(
        request=request,
        name="pages/auth/login.html",
        context={
            "title": _("Log in"),
            "tenant": tenant,
        },
    )


@router.get("/logout")
@router.post("/logout")
def logout(request: Request):
    # Clear server-side auth_store if present
    pb = getattr(request.state, "pb", None)
    if pb:
        try:
            pb.auth_store.clear()
        except Exception:
            pass
    # Build redirect response and clear cookie hardened
    resp = RedirectResponse(url="/login", status_code=303)
    clear_auth_cookie(resp)
    # Also instruct HTMX clients
    resp.headers["HX-Redirect"] = "/login"
    return resp


@router.get("/change-password")
def change_password_page(request: Request):
    tenant = getattr(request.state, "tenant", None)
    user = getattr(request.state, "user", None)

    # 1. Protect the route - only logged-in users can change their password
    if not user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        request=request,
        name="pages/auth/change_password.html",
        context={"title": "", "tenant": tenant, "user": user},
    )


@router.post("/login")
def login(request: Request, identity: str = Form(...), password: str = Form(...)):

    # 1. Safe Tenant Extraction 🏢
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        return _login_error(request, None, _("System error: Gym not found!"))

    # Rate limiting per IP + identity
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{identity}:{tenant.id}"
    if _is_rate_limited(rate_key):
        return _login_error(
            request, tenant, _("Too many login attempts. Please wait a few minutes."), 429
        )
    _record_attempt(rate_key)

    # Input trimming and basic validation
    identity = str(identity).strip()[:254]
    password = str(password)[:128]
    if not identity or not password:
        return _login_error(request, tenant, _("Email and password are required"))
    # Optional email format check, but allow username if needed
    if "@" in identity:
        try:
            identity = validate_email(identity)
        except ValueError:
            return _login_error(request, tenant, _("Invalid email format"))

    # 2. Attempt Authentication 🔐
    result = login_user(identity, password, tenant.id)

    # 3. Handle Failure: re-render the form with a visible error message
    if not result.get("ok"):
        error_msg = result.get("error", _("Wrong email or password."))
        return _login_error(request, tenant, error_msg)
    # 4. Handle Success & Role Routing 🧭
    user = result["user"]

    # Updated to point to your new owner dashboard path!
    target_url = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"

    # 5. Execute Redirect & Issue Cookie 🍪
    response = RedirectResponse(url=target_url, status_code=303)
    # Clear rate limit on success
    _login_attempts.pop(rate_key, None)
    set_auth_cookie(response, result["token"], request)

    return response


@router.post("/change-password")
def handle_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    user = getattr(request.state, "user", None)
    pb = getattr(request.state, "pb", None)
    tenant = getattr(request.state, "tenant", None)

    if not user or not pb:
        headers = hx_toast_now(_("You are not logged in!"), "error")
        headers["HX-Redirect"] = "/login"
        return HTMLResponse(content="", headers=headers)

    if new_password != confirm_password:
        headers = hx_toast_now(_("New password and its confirmation do not match."), "warning")
        return HTMLResponse(content="", headers=headers, status_code=400)

    if len(new_password) < 8:
        headers = hx_toast_now(_("Password must be at least 8 characters."), "warning")
        return HTMLResponse(content="", headers=headers, status_code=400)
    if len(new_password) > 72:
        headers = hx_toast_now(_("Password is too long"), "warning")
        return HTMLResponse(content="", headers=headers, status_code=400)
    # Password complexity: at least one upper/lower/digit optional but enforce not common
    # Prevent reusing same as old is handled by PB; also prevent identity reuse
    if new_password.lower() in str(getattr(user, "email", "")).lower():
        headers = hx_toast_now(_("Password must not be similar to the email"), "warning")
        return HTMLResponse(content="", headers=headers, status_code=400)

    collection_name = getattr(user, "collectionName", "users")

    # 1. Update the password
    result = update_user_password(
        pb=pb,
        collection_name=collection_name,
        user_id=user.id,
        old_password=old_password,
        new_password=new_password,
        confirm_password=confirm_password,
    )

    if not result.get("ok"):
        headers = hx_toast(result.get("error"), "error")
        return HTMLResponse(content="", headers=headers)

    # 🟢 2. Seamlessly re-authenticate with the NEW password to get a fresh token
    # Note: Ensure user.email (or username) is available on the user model
    identity = getattr(user, "email", "")
    login_result = login_user(identity, new_password, tenant.id)

    # 3. Setup Success Response & Redirect
    headers = hx_toast(_("Password changed successfully! 🔒"), "success")
    target_url = "/user/dashboard" if getattr(user, "role", None) == "trainee" else "/dashboard"
    headers["HX-Redirect"] = target_url

    response = HTMLResponse(content="", headers=headers)

    # 🟢 4. Inject the new cookie so they don't get kicked out!
    if login_result.get("ok"):
        set_auth_cookie(response, login_result["token"], request)
    else:
        # If re-auth fails, clear stale cookie and force login
        clear_auth_cookie(response)
        headers["HX-Redirect"] = "/login"

    return response
