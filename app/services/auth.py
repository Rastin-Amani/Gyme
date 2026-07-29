from app.pb import pb
from fastapi import Request
from structlog import get_logger

logger = get_logger(__name__)


def login_user(identity: str, password: str, tenant: str):
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
        return {"ok": False, "error": "اطلاعات اشتباه است!"}


def create_user(
    pb, tenant_id: str, email: str, first_name: str, last_name: str, phone: str, role: str
):

    # 🟢 Using email as the password and adding phone to the payload
    payload = {
        "email": email,
        "password": email,
        "passwordConfirm": email,
        "first_name": first_name,
        "last_name": last_name,
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
            "error": "ثبت‌نام کاربر انجام نشد. (احتمالا ایمیل تکراری است یا کمتر از ۸ کاراکتر دارد)",
        }


def update_user(pb, user_id: str, data: dict):
    return pb.collection("users").update(user_id, data)


def load_auth_from_cookie(request: Request):
    token = request.cookies.get("pb_auth")
    if token:
        # This tells the SDK who we are for THIS request
        pb.auth_store.save(token, None)
    else:
        pb.auth_store.clear()


def update_user_password(
    pb,
    collection_name: str,
    user_id: str,
    old_password: str,
    new_password: str,
    confirm_password: str,
) -> dict:
    try:
        pb.collection(collection_name).update(
            user_id,
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
        return {"ok": False, "error": "پسورد فعلی اشتباه است یا خطایی رخ داد."}
