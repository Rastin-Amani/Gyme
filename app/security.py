"""
Central security helpers for Gyme FastAPI.

Defensive controls:
- PB filter escaping to prevent NoSQL / filter injection
- Allowlist validation for plan types, genders, statuses
- Secure cookie configuration
- Tenant/host validation
- Authorization helpers
- Input sanitization
"""
import os
import re
from typing import Optional

# ---------------------------------------------------------------------------
# PocketBase filter escaping
# ---------------------------------------------------------------------------
# PB filters use  "value" quoting. Escape \ and " inside values.
# Reference: https://pocketbase.io/docs/api-rules-and-filters/#filter-syntax

def pb_escape(value: Optional[str]) -> str:
    """Escape a string for safe inclusion inside PB filter double quotes."""
    if value is None:
        return ""
    s = str(value)
    # Must escape backslash first, then double-quote
    return s.replace("\\", "\\\\").replace('"', '\\"')

def pb_escape_like(value: str) -> str:
    """Escape for ~ (like) filters – same escaping, plus escape % and _ if needed."""
    return pb_escape(value)

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------
ALLOWED_PLAN_TYPES = {"training", "diet", "steroid"}
ALLOWED_PLAN_TYPES_ITEMS = {"training_items", "diet_items", "steroid_items"}
ALLOWED_GENDERS = {"male", "female"}
ALLOWED_BLOOD_TYPES = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", ""}
ALLOWED_TRAINEE_STATUS = {"active", "inactive"}
ALLOWED_PLAN_STATUS = {"active", "inactive", "draft"}
ALLOWED_ROLES = {"owner", "coach", "trainee"}  # owner may be absent role

# Tenant domain validation: allow hostname with port stripped, alphanumeric + hyphen + dot
_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9.-]{1,253}$")

def is_valid_host(host: str) -> bool:
    if not host or len(host) > 253:
        return False
    # Strip port already expected, but double-check no colon
    if ":" in host:
        return False
    # Prevent injection characters
    if '"' in host or "'" in host or "\\" in host or " " in host:
        return False
    return bool(_DOMAIN_RE.match(host))

def sanitize_plan_type(plan_type: str) -> str:
    """Validate and return plan_type or raise ValueError."""
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise ValueError(f"Invalid plan_type: {plan_type}")
    return plan_type

def sanitize_collection_name(plan_type: str) -> str:
    """Convert validated plan_type to collection name."""
    sanitize_plan_type(plan_type)
    name = f"{plan_type}_items"
    if name not in ALLOWED_PLAN_TYPES_ITEMS:
        raise ValueError("Invalid collection")
    return name

def sanitize_gender(gender: Optional[str]) -> Optional[str]:
    if gender is None or gender == "":
        return None
    g = str(gender).lower()
    if g not in ALLOWED_GENDERS:
        raise ValueError("Invalid gender")
    return g

def sanitize_blood_type(bt: Optional[str]) -> Optional[str]:
    if bt is None or bt == "":
        return None
    if bt not in ALLOWED_BLOOD_TYPES:
        raise ValueError("Invalid blood_type")
    return bt

def sanitize_status(status: Optional[str], allowed: set) -> Optional[str]:
    if status is None or status == "":
        return None
    s = str(status).lower()
    if s not in allowed:
        raise ValueError(f"Invalid status: {status}")
    return s

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
IS_PROD = os.getenv("ENV", "dev").lower() == "production"

def cookie_secure_flag(request=None) -> bool:
    """Return True when cookies should be marked Secure.
    In production always True. In dev, True only if request is https."""
    if IS_PROD:
        return True
    if request is not None:
        # If behind proxy, trust x-forwarded-proto or url scheme
        try:
            if getattr(request.url, "scheme", "http") == "https":
                return True
            if request.headers.get("x-forwarded-proto", "") == "https":
                return True
        except Exception:
            pass
    return False

def set_auth_cookie(response, token: str, request=None):
    """Set pb_auth cookie with hardened attributes."""
    secure = cookie_secure_flag(request)
    # HttpOnly, SameSite=Lax, Path=/, Secure conditional, Max-Age 7 days (PocketBase default 7d)
    response.set_cookie(
        key="pb_auth",
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 7,
    )
    return response

def clear_auth_cookie(response):
    response.delete_cookie(key="pb_auth", path="/", samesite="lax")
    return response

# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------
def is_owner_or_coach(user) -> bool:
    role = getattr(user, "role", None)
    return role in ("owner", "coach") or role is None and False  # explicit

def is_trainee(user) -> bool:
    return getattr(user, "role", None) == "trainee"

def require_owner_or_coach(user):
    if is_trainee(user):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")

def verify_tenant_ownership(record, tenant_id: str) -> bool:
    """Check record.tenant == tenant_id . Record may have .tenant attribute or dict."""
    rec_tenant = getattr(record, "tenant", None)
    if rec_tenant is None and isinstance(record, dict):
        rec_tenant = record.get("tenant")
    return str(rec_tenant) == str(tenant_id)

# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate_email(email: str, max_len: int = 254) -> str:
    email = str(email).strip().lower()
    if len(email) > max_len or len(email) < 5:
        raise ValueError("Invalid email length")
    if not _EMAIL_RE.match(email):
        raise ValueError("Invalid email")
    return email

def validate_phone(phone: Optional[str]) -> Optional[str]:
    if phone is None or phone == "":
        return None
    p = str(phone).strip()
    # Allow 10-15 digits, optional leading +
    if not re.fullmatch(r"\+?[0-9]{10,15}", p):
        raise ValueError("Invalid phone")
    return p

def validate_length(value: Optional[str], field: str, min_len=0, max_len=500) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    if len(s) < min_len:
        raise ValueError(f"{field} too short")
    if len(s) > max_len:
        raise ValueError(f"{field} too long")
    return s

def sanitize_next_url(url: str) -> str:
    """Prevent open redirect: only allow internal relative paths starting with / and not //"""
    if not url:
        return "/dashboard"
    u = str(url).strip()
    if not u.startswith("/") or u.startswith("//"):
        return "/dashboard"
    if "://" in u or "\\" in u:
        return "/dashboard"
    return u

# ---------------------------------------------------------------------------
# PB filter builders (safe)
# ---------------------------------------------------------------------------
def build_tenant_filter(tenant_id: str) -> str:
    return f'tenant="{pb_escape(tenant_id)}"'

def build_id_filter(record_id: str) -> str:
    return f'id="{pb_escape(record_id)}"'

def build_tenant_id_filter(tenant_id: str, record_id: str) -> str:
    return f'tenant="{pb_escape(tenant_id)}" && id="{pb_escape(record_id)}"'
