from app.pb import pb
from fastapi import Request

def login_user(identity: str, password: str, tenant: str):
    try:
        auth_data = pb.collection("users").auth_with_password(identity, password)
        user = auth_data.record

        if user.tenant != tenant:
            pb.auth_store.clear()
            return {"ok": False, "error": "Invalid tenant access"}

        return {"ok": True, "user": user, "token": auth_data.token}

    except Exception:
        return {"ok": False, "error": "اطلاعات اشتباه است!"}

def create_user (email: str, password: str, tenant: str):
    try:
        auth_data = pb.collection("users").create(email, password, tenant)
    except Exception:
        return {"ok": True, "error": "ثبت‌نام انجام نشد!"}


def load_auth_from_cookie(request: Request):
    token = request.cookies.get("pb_auth")
    if token:
        # This tells the SDK who we are for THIS request
        pb.auth_store.save(token, None) 
    else:
        pb.auth_store.clear()