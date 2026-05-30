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

def create_user(pb, tenant_id: str, email: str, first_name: str, last_name: str, phone: str, role: str):
    
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
        return {"ok": True, "user": user_record}
    except Exception as e:
        print(f"User creation failed: {e}")
        return {"ok": False, "error": "ثبت‌نام کاربر انجام نشد. (احتمالا ایمیل تکراری است یا کمتر از ۸ کاراکتر دارد)"}

def update_user(pb, user_id: str, data: dict):
    return pb.collection("users").update(user_id, data)

def load_auth_from_cookie(request: Request):
    token = request.cookies.get("pb_auth")
    if token:
        # This tells the SDK who we are for THIS request
        pb.auth_store.save(token, None) 
    else:
        pb.auth_store.clear()