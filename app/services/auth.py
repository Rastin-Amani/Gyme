from app.pb import get_pb
from fastapi import Request
from structlog import get_logger
from app.i18n import _

logger = get_logger(__name__)


def login_user(identity: str, password: str, tenant: str, pb=None):
    if pb is None:
        pb = get_pb()
    try:
        auth_data = pb.collection("users").auth_with_password(identity, password)
        user = auth_data.record

        if user.tenant != tenant:
            pb.auth_store.clear()
            logger.warning("login_cross_tenant_denied", identity=identity, tenant=tenant)
            return {"ok": False, "error": "Invalid tenant access"}

        logger.info("login_success", role=getattr(user, "role", None), tenant=tenant)
        return {"ok": True, "user": user, "token": auth_data.token}

    except Exception as e:
        logger.warning("login_failed", identity=identity, tenant=tenant, error=str(e))
        return {"ok": False, "error": _("اطلاعات اشتباه است!")}


def create_user(
    pb, tenant_id: str, email: str, first_name: str, last_name: str, phone: str, role: str
):
    import secrets
    import string
    from app.security import validate_email, validate_phone

    # Validate inputs
    try:
        email = validate_email(email)
        phone = validate_phone(phone) or ""
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    if role not in {"trainee", "coach"}:
        return {"ok": False, "error": "Invalid role"}

    # Generate strong random password instead of using email
    alphabet = string.ascii_letters + string.digits
    random_pwd = "".join(secrets.choice(alphabet) for _ in range(12)) + "A1!"
    # Ensure at least 12 chars with complexity; email not used as password

    payload = {
        "email": email,
        "password": random_pwd,
        "passwordConfirm": random_pwd,
        "first_name": str(first_name)[:50].strip(),
        "last_name": str(last_name)[:50].strip(),
        "phone": phone,
        "tenant": tenant_id,
        "role": role,
        "emailVisibility": True,
    }

    try:
        user_record = pb.collection("users").create(payload)
        logger.info("user_created", user_id=user_record.id, role=role, tenant=tenant_id)
        return {"ok": True, "user": user_record}
    except Exception as e:
        logger.error("user_creation_failed", email=email, role=role, tenant=tenant_id, error=str(e))
        return {
            "ok": False,
            "error": _(
                "ثبت‌نام کاربر انجام نشد. (احتمالا ایمیل تکراری است یا کمتر از ۸ کاراکتر دارد)"
            ),
        }


def update_user(pb, user_id: str, data: dict):
    from app.security import pb_escape, validate_email, validate_phone

    safe_id = pb_escape(user_id)
    # Sanitize allowed fields only
    allowed = {"first_name", "last_name", "email", "phone"}
    safe_data = {}
    for k, v in (data or {}).items():
        if k not in allowed:
            continue
        if k == "email":
            try:
                safe_data[k] = validate_email(str(v))
            except ValueError:
                continue
        elif k == "phone":
            try:
                safe_data[k] = validate_phone(str(v)) or ""
            except ValueError:
                continue
        else:
            safe_data[k] = str(v)[:100].strip()
    if not safe_data:
        return pb.collection("users").get_one(safe_id)
    return pb.collection("users").update(safe_id, safe_data)


def load_auth_from_cookie(request: Request):
    client = get_pb()
    token = request.cookies.get("pb_auth")
    if token:
        # This tells the SDK who we are for THIS request
        client.auth_store.save(token, None)
    else:
        client.auth_store.clear()


def update_user_password(
    pb,
    collection_name: str,
    user_id: str,
    old_password: str,
    new_password: str,
    confirm_password: str,
) -> dict:
    from app.security import pb_escape

    # Validate collection name allowlist
    if collection_name not in {"users", "tenants"}:
        collection_name = "users"
    try:
        pb.collection(collection_name).update(
            pb_escape(user_id),
            {
                "oldPassword": old_password,
                "password": new_password,
                "passwordConfirm": confirm_password,
            },
        )
        logger.info("password_changed", user_id=user_id)
        return {"ok": True}

    except Exception as e:
        logger.warning("password_change_failed", user_id=user_id, error=str(e))
        return {"ok": False, "error": _("پسورد فعلی اشتباه است یا خطایی رخ داد.")}
