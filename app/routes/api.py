"""Cookie-authenticated JSON API used by the SvelteKit application."""

from datetime import date
from enum import Enum
import math
import os
import re

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pocketbase.errors import ClientResponseError
from starlette.datastructures import UploadFile

from app.i18n import ENABLED_LOCALES, LOCALE_COOKIE
from app.security import (
    ALLOWED_BLOOD_TYPES,
    ALLOWED_GENDERS,
    ALLOWED_PLAN_STATUS,
    ALLOWED_PLAN_TYPES,
    ALLOWED_TRAINEE_STATUS,
    clear_auth_cookie,
    sanitize_collection_name,
    set_auth_cookie,
    validate_email,
    validate_length,
    validate_phone,
)
from app.services.auth import (
    create_user,
    is_login_rate_limited,
    login_user,
    record_login_attempt,
    update_user,
    update_user_password,
    _login_attempts,
)
from app.services.coach import delete_coach, get_coach_by_id, list_coaches
from app.services.dashboard import get_coach_stats, get_owner_dashboard_stats
from app.services.item import (
    create_item,
    delete_item,
    get_item_by_id,
    list_items_by_plan,
    update_item,
)
from app.services.plan import (
    apply_template,
    create_plan,
    delete_plan,
    get_plan_by_id,
    get_plans_by_trainee,
    list_plans,
    update_plan,
)
from app.services.progress import get_progress_by_plan
from app.services.progress_logs import (
    create_progress_log,
    get_progress_log_with_tenant_check,
    get_progress_logs_by_trainee,
    update_progress_log,
)
from app.services.trainee import (
    create_trainee,
    delete_trainee,
    get_trainee_by_id,
    get_trainee_by_user,
    list_trainees,
    update_trainee,
)

router = APIRouter(prefix="/api/v1", tags=["Svelte JSON API"])
_SECRET_KEYS = re.compile(r"(?:token|password|secret|auth_store)", re.I)
_ITEM_FIELDS = {
    "training": (
        "name",
        "seq",
        "order",
        "sets",
        "reps",
        "weight",
        "rest_seconds",
        "category",
        "notes",
    ),
    "diet": ("name", "meal_name", "quantity", "seq", "order", "notes"),
    "steroid": ("name", "type", "dosage", "frequency", "seq", "order", "notes"),
}
_LOG_RANGES = {
    "height": (30, 300),
    "weight": (20, 500),
    "chest": (20, 300),
    "waist": (20, 300),
    "hip": (20, 300),
    "arms": (10, 100),
    "bmi": (5, 100),
    "bfp": (1, 80),
    "bmr": (500, 10000),
    "tdee": (500, 15000),
    "lbm": (10, 300),
    "whr": (0.1, 3),
}


def _plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _plain(value.value)
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _plain(item)
            for key, item in value.items()
            if not _SECRET_KEYS.search(str(key))
        }
    data = getattr(value, "__dict__", None)
    if isinstance(data, dict):
        return {
            str(key): _plain(item)
            for key, item in data.items()
            if not key.startswith("_") and not _SECRET_KEYS.search(str(key))
        }
    return str(value)


def _user(value):
    source = _plain(value)
    return {
        key: source[key]
        for key in ("id", "role", "first_name", "last_name", "email", "phone")
        if key in source
    }


def _value(value):
    return value.value if isinstance(value, Enum) else value


def _record(value):
    data = _plain(value)
    if not isinstance(data, dict):
        return data
    expand = data.get("expand")
    if isinstance(expand, dict):
        for key, relation in expand.items():
            if key == "user" and isinstance(relation, dict):
                data["expand"][key] = _user(relation)
    return data


def _page(result, page: int, per_page: int):
    items = getattr(result, "items", result)
    items = [_record(item) for item in (items or [])]
    total = int(getattr(result, "total_items", getattr(result, "totalItems", len(items))))
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, math.ceil(total / per_page)),
    }


def _pb_error(error: Exception):
    status = getattr(error, "status", None)
    if status == 404:
        raise HTTPException(404, "Record not found") from error
    if status in (400, 422):
        raise HTTPException(422, "Invalid record data") from error
    if status == 401:
        raise HTTPException(401, "Authentication required") from error
    if status == 403:
        raise HTTPException(403, "Forbidden") from error
    if status == 409:
        raise HTTPException(409, "Record conflict") from error
    raise HTTPException(503, "PocketBase is unavailable") from error


def _user_context(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(401, "Authentication required")
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(404, "Tenant not found")
    return request.state.pb, tenant.id, user


def _role(user):
    role = getattr(user, "role", None)
    return role if role in {"owner", "coach", "trainee"} else None


def _require(user, *roles):
    if _role(user) not in roles:
        raise HTTPException(403, "Forbidden")


async def _payload(request: Request):
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            value = await request.json()
            if not isinstance(value, dict):
                raise HTTPException(422, "Expected a JSON object")
            return value
        form = await request.form()
        values = {}
        for key, value in form.multi_items():
            if isinstance(value, UploadFile):
                values.setdefault("_files", []).append(value)
            else:
                values[key] = value
        return values
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(400, "Malformed request body") from error


def _required_text(data, field, maximum=500):
    value = data.get(field)
    if not isinstance(value, str):
        raise HTTPException(422, f"{field} is required")
    try:
        result = validate_length(value, field, 1, maximum)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if result is None:
        raise HTTPException(422, f"{field} is required")
    return result


def _optional_text(data, field, maximum=2000):
    value = data.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        value = str(value)
    try:
        return validate_length(value, field, 0, maximum)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def _date(value, field):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as error:
        raise HTTPException(422, f"{field} must be an ISO date") from error


def _number(value, field, minimum=None, maximum=None, integer=False):
    if value in (None, ""):
        return None
    try:
        if isinstance(value, bool):
            raise ValueError
        numeric = float(value)
        if integer and not numeric.is_integer():
            raise ValueError
        result = int(numeric) if integer else numeric
    except (TypeError, ValueError) as error:
        raise HTTPException(422, f"{field} must be a number") from error
    if (
        not math.isfinite(result)
        or minimum is not None
        and result < minimum
        or maximum is not None
        and result > maximum
    ):
        raise HTTPException(422, f"{field} is outside the allowed range")
    return result


def _assert_coach_trainee(pb, tenant_id, user, trainee_id):
    if _role(user) != "coach":
        return
    try:
        result = pb.collection("plans").get_list(
            page=1,
            per_page=1,
            query_params={
                "filter": f'tenant="{_escape(tenant_id)}" && coach="{_escape(user.id)}" && trainee="{_escape(trainee_id)}"'
            },
        )
        if not getattr(result, "items", []):
            raise HTTPException(403, "Trainee is not assigned to this coach")
    except HTTPException:
        raise
    except ClientResponseError as error:
        _pb_error(error)


def _escape(value):
    from app.security import pb_escape

    return pb_escape(str(value))


def _plan_for_user(pb, tenant_id, user, plan_id):
    try:
        plan = get_plan_by_id(pb, tenant_id, plan_id)
    except ClientResponseError as error:
        _pb_error(error)
    if _role(user) == "coach" and str(getattr(plan, "coach", "")) != str(user.id):
        raise HTTPException(403, "Plan is not assigned to this coach")
    return plan


def _trainee_for_user(pb, tenant_id, user, trainee_id):
    try:
        trainee = get_trainee_by_id(pb, tenant_id, trainee_id)
    except ClientResponseError as error:
        _pb_error(error)
    _assert_coach_trainee(pb, tenant_id, user, trainee_id)
    return trainee


def _profile_payload(data, include_email=False, partial=False):
    try:
        result = {}
        for field in ("first_name", "last_name"):
            if field in data or not partial:
                value = validate_length(data.get(field), field, 1, 50)
                if value is None:
                    raise ValueError(f"{field} is required")
                result[field] = value
        if "phone" in data or not partial:
            result["phone"] = validate_phone(data.get("phone")) or ""
        if include_email and ("email" in data or not partial):
            result["email"] = validate_email(data.get("email", ""))
        if partial and not result:
            raise ValueError("At least one profile field is required")
        return result
    except (ValueError, TypeError) as error:
        raise HTTPException(422, str(error)) from error


def _trainee_payload(data, partial=False):
    user = _profile_payload(data, include_email=True, partial=partial)
    gender = data.get("gender") or None
    blood_type = data.get("blood_type") or None
    if gender and gender not in ALLOWED_GENDERS:
        raise HTTPException(422, "Invalid gender")
    if blood_type and blood_type not in ALLOWED_BLOOD_TYPES:
        raise HTTPException(422, "Invalid blood_type")
    fields = {}
    values = {
        "gender": gender,
        "blood_type": blood_type,
        "birthdate": _date(data.get("birthdate"), "birthdate"),
    }
    fields.update({key: value for key, value in values.items() if key in data or not partial})
    for field in ("training_history", "steroid_history", "supplement_history", "limitations"):
        if field in data or not partial:
            fields[field] = _optional_text(data, field)
    if "notes" in data or not partial:
        fields["notes"] = _optional_text(data, "notes", 1000)
    if partial and not user and not fields:
        raise HTTPException(422, "At least one trainee field is required")
    return user, fields


def _plan_payload(data, user, existing=None):
    plan_type = data.get("type", _value(getattr(existing, "type", None)))
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise HTTPException(422, "Invalid plan type")
    status = data.get("status", getattr(existing, "status", "active")) or "active"
    if status not in ALLOWED_PLAN_STATUS:
        raise HTTPException(422, "Invalid plan status")
    days = _number(
        data.get("days_per_week", getattr(existing, "days_per_week", None)),
        "days_per_week",
        1,
        7,
        True,
    )
    is_template = data.get("is_template", getattr(existing, "is_template", False))
    if isinstance(is_template, str):
        is_template = is_template.lower() in {"true", "1", "yes", "on"}
    if not isinstance(is_template, bool):
        raise HTTPException(422, "is_template must be a boolean")
    trainee = data.get("trainee", getattr(existing, "trainee", None))
    coach_id = data.get("coach", getattr(existing, "coach", None)) or user.id
    if _role(user) == "coach":
        coach_id = user.id
    return {
        "type": plan_type,
        "trainee": None if is_template else trainee,
        "coach": coach_id,
        "start_date": _date(
            data.get("start_date", getattr(existing, "start_date", None)), "start_date"
        ),
        "end_date": _date(data.get("end_date", getattr(existing, "end_date", None)), "end_date"),
        "days_per_week": days,
        "status": status,
        "notes": (
            _optional_text(data, "notes", 1000)
            if "notes" in data or existing is None
            else getattr(existing, "notes", None)
        ),
        "is_template": is_template,
        "template_name": _optional_text(data, "template_name", 100) if is_template else None,
    }


def _verify_plan_relations(pb, tenant_id, user, data):
    trainee_id = data.get("trainee")
    if trainee_id:
        _trainee_for_user(pb, tenant_id, user, trainee_id)
    coach_id = data.get("coach")
    if coach_id and _role(user) != "coach" and str(coach_id) != str(user.id):
        try:
            get_coach_by_id(pb, tenant_id, coach_id)
        except ClientResponseError as error:
            _pb_error(error)


def _item_payload(data, plan_type, partial=False):
    if plan_type not in _ITEM_FIELDS:
        raise HTTPException(422, "Invalid plan type")
    result = {}
    input_name = (
        data.get("item_name")
        if plan_type == "training"
        else data.get("food_name") if plan_type == "diet" else data.get("name")
    )
    name_key = (
        "item_name" if plan_type == "training" else "food_name" if plan_type == "diet" else "name"
    )
    if name_key in data or not partial:
        result["name"] = _required_text({"name": input_name}, "name", 200)
    for field in _ITEM_FIELDS[plan_type]:
        if field == "name":
            continue
        if partial and field not in data:
            continue
        value = data.get(field)
        if field in {"seq", "order", "sets", "reps", "rest_seconds"}:
            value = _number(value, field, 0, 10000, True)
        elif field == "weight":
            value = _number(value, field, 0, 10000)
        elif value is not None:
            value = _optional_text(data, field, 1000 if field == "notes" else 200)
        result[field] = value
    if plan_type == "diet" and ("meal_name" in data or not partial):
        result["meal_name"] = _required_text(data, "meal_name", 100)
    return result


def _progress_payload(data, required=True):
    result = {}
    for field, (minimum, maximum) in _LOG_RANGES.items():
        result[field] = _number(data.get(field), field, minimum, maximum)
        if required and field in {"height", "weight"} and result[field] is None:
            raise HTTPException(422, f"{field} is required")
    result["notes"] = _optional_text(data, "notes", 1000)
    return result


async def _photo_uploads(data):
    files = data.get("_files", [])
    if len(files) > 5:
        raise HTTPException(422, "A maximum of 5 progress photos is allowed")
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    magic = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG", "image/png"), (b"GIF8", "image/gif"))
    uploads = []
    for photo in files:
        name = str(photo.filename or "")[:100]
        if not name or any(c in name for c in ("/", "\\")) or ".." in name:
            raise HTTPException(422, "Invalid progress photo filename")
        if (
            os.path.splitext(name)[1].lower() not in allowed_exts
            or photo.content_type not in allowed_types
        ):
            raise HTTPException(422, "Progress photos must be JPEG, PNG, WebP, or GIF images")
        content = await photo.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024 or len(content) < 10:
            raise HTTPException(422, "Progress photos must be between 10 bytes and 5 MB")
        expected = next(
            (content_type for prefix, content_type in magic if content.startswith(prefix)), None
        )
        if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            expected = "image/webp"
        if expected != photo.content_type:
            raise HTTPException(422, "Progress photo content does not match its type")
        uploads.append((re.sub(r"[^a-zA-Z0-9._-]", "_", name), content, photo.content_type))
    return uploads or None


@router.get("/auth/me")
def auth_me(request: Request):
    _, tenant_id, user = _user_context(request)
    return {"user": _user(user), "tenant_id": tenant_id}


@router.get("/tenant/branding")
def tenant_branding(request: Request):
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    logo_url = None
    logo = getattr(tenant, "logo", None)
    if logo:
        from urllib.parse import quote

        pb = request.state.pb
        collection = str(getattr(tenant, "collection_id", "tenants") or "tenants")
        logo_url = (
            f"{pb.base_url.rstrip('/')}/api/files/{quote(collection, safe='')}/"
            f"{quote(str(tenant.id), safe='')}/{quote(str(logo), safe='')}?thumb=512x512f"
        )

    return {
        "name": str(getattr(tenant, "name", None) or "Gyme"),
        "logo_url": logo_url,
        "theme": str(getattr(tenant, "theme", None) or "gyme"),
        "brand_theme": _plain(getattr(tenant, "brand_theme", {}) or {}),
        "brand_colors": _plain(getattr(tenant, "brand_colors", {}) or {}),
        "primary_color": str(getattr(tenant, "primary_color", None) or ""),
    }


@router.post("/auth/login")
async def auth_login(request: Request):
    data = await _payload(request)
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(404, "Tenant not found")
    identity = str(data.get("identity", "")).strip()[:254]
    password = str(data.get("password", ""))[:128]
    if not identity or not password:
        raise HTTPException(422, "Email and password are required")
    if "@" in identity:
        try:
            identity = validate_email(identity)
        except ValueError as error:
            raise HTTPException(422, "Invalid email format") from error
    ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )
    key = f"{ip}:{identity.casefold()}:{tenant.id}"
    if is_login_rate_limited(key):
        raise HTTPException(429, "Too many login attempts. Please wait a few minutes.")
    record_login_attempt(key)
    result = login_user(identity, password, tenant.id, pb=request.state.pb)
    if not result.get("ok"):
        raise HTTPException(401, "Invalid credentials")
    _login_attempts.pop(key, None)
    response = JSONResponse({"user": _user(result["user"])})
    set_auth_cookie(response, result["token"], request)
    return response


@router.post("/auth/logout", status_code=204)
def auth_logout(request: Request):
    pb = getattr(request.state, "pb", None)
    if pb is not None:
        pb.auth_store.clear()
    response = Response(status_code=204)
    clear_auth_cookie(response)
    return response


@router.post("/auth/change-password")
async def auth_change_password(request: Request):
    pb, tenant_id, user = _user_context(request)
    data = await _payload(request)
    old_password = str(data.get("old_password", ""))
    new_password = str(data.get("new_password", ""))
    confirm = str(data.get("confirm_password", ""))
    if new_password != confirm:
        raise HTTPException(422, "New password and its confirmation do not match")
    if not 8 <= len(new_password) <= 72:
        raise HTTPException(422, "Password must be between 8 and 72 characters")
    if new_password.lower() in str(getattr(user, "email", "")).lower():
        raise HTTPException(422, "Password must not be similar to the email")
    result = update_user_password(
        pb, getattr(user, "collectionName", "users"), user.id, old_password, new_password, confirm
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Password change failed"))
    identity = getattr(user, "email", "")
    login_result = login_user(identity, new_password, tenant_id)
    response = JSONResponse({"user": _user(user)})
    if login_result.get("ok"):
        set_auth_cookie(response, login_result["token"], request)
    else:
        clear_auth_cookie(response)
    return response


@router.patch("/auth/profile")
async def auth_update_profile(request: Request):
    pb, tenant_id, user = _user_context(request)
    data = await _payload(request)
    profile = _profile_payload(data, partial=True)
    try:
        updated = update_user(pb, user.id, profile)
    except ClientResponseError as error:
        _pb_error(error)
    if str(getattr(updated, "tenant", tenant_id)) != str(tenant_id):
        raise HTTPException(404, "User not found")
    return {"user": _user(updated)}


@router.get("/locale/{code}")
def api_locale(code: str):
    if code not in ENABLED_LOCALES:
        raise HTTPException(404, "Unsupported locale")
    response = JSONResponse({"locale": code})
    response.set_cookie(LOCALE_COOKIE, code, max_age=365 * 24 * 3600, samesite="lax", path="/")
    return response


@router.get("/dashboard")
def api_dashboard(request: Request, timeframe: str = "all"):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    if timeframe not in {"all", "month", "week"}:
        raise HTTPException(422, "Invalid timeframe")
    role = _role(user)
    if role == "owner":
        stats = get_owner_dashboard_stats(pb, tenant_id, timeframe)
        coach_stats = get_coach_stats(pb, tenant_id, owner_id=user.id, timeframe=timeframe)
    else:
        active_trainees = list_trainees(
            pb, tenant_id, per_page=1, status="active", coach_id=user.id
        )
        inactive_trainees = list_trainees(
            pb, tenant_id, per_page=1, status="inactive", coach_id=user.id
        )
        coach_stats = get_coach_stats(pb, tenant_id, coach_id=user.id, timeframe=timeframe)
        personal = coach_stats[0] if coach_stats else {}
        stats = {
            "active_trainees": getattr(active_trainees, "total_items", 0),
            "inactive_trainees": getattr(inactive_trainees, "total_items", 0),
            "diet_plans": personal.get("diet_count", 0),
            "training_plans": personal.get("training_count", 0),
            "steroid_plans": personal.get("steroid_count", 0),
        }
    return {"stats": stats, "coach_stats": _plain(coach_stats), "timeframe": timeframe}


@router.get("/dashboard/coach-stats")
def api_coach_stats(request: Request, timeframe: str = "all"):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    if timeframe not in {"all", "month", "week"}:
        raise HTTPException(422, "Invalid timeframe")
    stats = get_coach_stats(
        pb,
        tenant_id,
        coach_id=user.id if _role(user) == "coach" else None,
        owner_id=user.id if _role(user) == "owner" else None,
        timeframe=timeframe,
    )
    return [_plain(item) for item in stats]


@router.get("/trainees")
def api_trainees(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    query: str = "",
    gender: str | None = None,
    status: str | None = None,
    min_birthdate: str | None = None,
    max_birthdate: str | None = None,
):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    if gender and gender not in ALLOWED_GENDERS:
        raise HTTPException(422, "Invalid gender")
    if status and status not in ALLOWED_TRAINEE_STATUS:
        raise HTTPException(422, "Invalid trainee status")
    minimum = _date(min_birthdate, "min_birthdate")
    maximum = _date(max_birthdate, "max_birthdate")
    if minimum and maximum and minimum > maximum:
        raise HTTPException(422, "min_birthdate must not be after max_birthdate")
    try:
        results = list_trainees(
            pb,
            tenant_id,
            page=page,
            per_page=per_page,
            query=query,
            gender=gender,
            status=status,
            min_birthdate=minimum,
            max_birthdate=maximum,
            coach_id=user.id if _role(user) == "coach" else None,
        )
    except ClientResponseError as error:
        _pb_error(error)
    return _page(results, page, per_page)


@router.post("/trainees", status_code=201)
async def api_create_trainee(request: Request):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    data = await _payload(request)
    user_data, trainee_data = _trainee_payload(data)
    result = create_user(pb, tenant_id, **user_data, role="trainee")
    if not result.get("ok"):
        raise HTTPException(409, result.get("error", "Could not create trainee"))
    linked_user = result["user"]
    try:
        trainee = create_trainee(pb, tenant_id, {"user": linked_user.id, **trainee_data})
    except Exception as error:
        try:
            pb.collection("users").delete(linked_user.id)
        except Exception:
            pass
        if isinstance(error, ClientResponseError):
            _pb_error(error)
        raise HTTPException(503, "Could not create trainee profile") from error
    return _record(trainee)


@router.get("/trainees/{trainee_id}")
def api_trainee_detail(request: Request, trainee_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    trainee = _trainee_for_user(pb, tenant_id, user, trainee_id)
    result = _record(trainee)
    result["plans"] = [_record(plan) for plan in get_plans_by_trainee(pb, tenant_id, trainee_id)]
    result["progress_logs"] = [
        _record(log) for log in get_progress_logs_by_trainee(pb, tenant_id, trainee_id)
    ]
    return result


@router.patch("/trainees/{trainee_id}")
async def api_update_trainee(request: Request, trainee_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    trainee = _trainee_for_user(pb, tenant_id, user, trainee_id)
    data = await _payload(request)
    user_data, trainee_data = _trainee_payload(data, partial=True)
    linked_user = getattr(trainee, "user", None)
    linked_id = getattr(linked_user, "id", linked_user)
    if not linked_id:
        raise HTTPException(409, "Trainee profile has no linked user")
    try:
        if user_data:
            update_user(pb, linked_id, user_data)
        updated = update_trainee(pb, trainee_id, trainee_data) if trainee_data else trainee
    except ClientResponseError as error:
        _pb_error(error)
    return _record(updated)


@router.delete("/trainees/{trainee_id}", status_code=204)
def api_delete_trainee(request: Request, trainee_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    _trainee_for_user(pb, tenant_id, user, trainee_id)
    try:
        delete_trainee(pb, tenant_id, trainee_id)
    except ClientResponseError as error:
        _pb_error(error)
    return Response(status_code=204)


def _coach_trainees(pb, tenant_id, coach_id):
    result = pb.collection("plans").get_full_list(
        query_params={
            "filter": f'tenant="{_escape(tenant_id)}" && coach="{_escape(coach_id)}" && is_template=false',
            "fields": "trainee",
        }
    )
    ids = dict.fromkeys(
        getattr(plan, "trainee", None) for plan in result if getattr(plan, "trainee", None)
    )
    trainees = []
    for trainee_id in ids:
        try:
            trainees.append(_record(get_trainee_by_id(pb, tenant_id, trainee_id)))
        except ClientResponseError as error:
            if getattr(error, "status", None) != 404:
                raise
    return trainees


@router.get("/coaches")
def api_coaches(
    request: Request, page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)
):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner")
    try:
        return _page(list_coaches(pb, tenant_id, page=page, per_page=per_page), page, per_page)
    except ClientResponseError as error:
        _pb_error(error)


@router.post("/coaches", status_code=201)
async def api_create_coach(request: Request):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner")
    data = await _payload(request)
    profile = _profile_payload(data, include_email=True)
    result = create_user(pb, tenant_id, **profile, role="coach")
    if not result.get("ok"):
        raise HTTPException(409, result.get("error", "Could not create coach"))
    return _record(result["user"])


@router.get("/coaches/{coach_id}")
def api_coach_detail(request: Request, coach_id: str):
    pb, tenant_id, user = _user_context(request)
    role = _role(user)
    if role not in {"owner", "coach"}:
        raise HTTPException(403, "Forbidden")
    if role == "coach" and str(user.id) != str(coach_id):
        raise HTTPException(403, "Forbidden")
    try:
        coach = get_coach_by_id(pb, tenant_id, coach_id)
        result = _record(coach)
        result["trainees"] = _coach_trainees(pb, tenant_id, coach_id)
        return result
    except ClientResponseError as error:
        _pb_error(error)


@router.patch("/coaches/{coach_id}")
async def api_update_coach(request: Request, coach_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner")
    try:
        get_coach_by_id(pb, tenant_id, coach_id)
    except ClientResponseError as error:
        _pb_error(error)
    profile = _profile_payload(await _payload(request), include_email=True, partial=True)
    try:
        return _record(update_user(pb, coach_id, profile))
    except ClientResponseError as error:
        _pb_error(error)


@router.delete("/coaches/{coach_id}", status_code=204)
def api_delete_coach(request: Request, coach_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner")
    try:
        delete_coach(pb, tenant_id, coach_id)
    except ClientResponseError as error:
        _pb_error(error)
    return Response(status_code=204)


@router.get("/plans")
def api_plans(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    query: str = "",
    type: str | None = None,
    coach_id: str | None = None,
    trainee: str | None = None,
    status: str | None = None,
    is_template: bool = False,
):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    if type and type not in ALLOWED_PLAN_TYPES:
        raise HTTPException(422, "Invalid plan type")
    if status and status not in ALLOWED_PLAN_STATUS:
        raise HTTPException(422, "Invalid plan status")
    if _role(user) == "coach":
        coach_id = user.id
    elif coach_id:
        try:
            get_coach_by_id(pb, tenant_id, coach_id)
        except ClientResponseError as error:
            _pb_error(error)
    try:
        result = list_plans(
            pb,
            tenant_id,
            page=page,
            per_page=per_page,
            query=query[:100],
            type=type,
            coach_id=coach_id,
            is_template=is_template,
            status=status,
            trainee=trainee,
        )
        return _page(result, page, per_page)
    except ClientResponseError as error:
        _pb_error(error)


@router.post("/plans", status_code=201)
async def api_create_plan(request: Request):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    data = await _payload(request)
    clean = _plan_payload(data, user)
    _verify_plan_relations(pb, tenant_id, user, clean)
    try:
        return _record(create_plan(pb, tenant_id, clean))
    except ClientResponseError as error:
        _pb_error(error)


@router.get("/plans/{plan_id}")
def api_plan_detail(request: Request, plan_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    plan = _plan_for_user(pb, tenant_id, user, plan_id)
    if _value(getattr(plan, "type", None)) not in ALLOWED_PLAN_TYPES:
        raise HTTPException(409, "Invalid plan type")
    return _record(plan)


@router.patch("/plans/{plan_id}")
async def api_update_plan(request: Request, plan_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    existing = _plan_for_user(pb, tenant_id, user, plan_id)
    clean = _plan_payload(await _payload(request), user, existing)
    _verify_plan_relations(pb, tenant_id, user, clean)
    try:
        return _record(update_plan(pb, tenant_id, plan_id, clean))
    except ClientResponseError as error:
        _pb_error(error)


@router.delete("/plans/{plan_id}", status_code=204)
def api_delete_plan(request: Request, plan_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    _plan_for_user(pb, tenant_id, user, plan_id)
    try:
        delete_plan(pb, tenant_id, plan_id)
    except ClientResponseError as error:
        _pb_error(error)
    return Response(status_code=204)


@router.post("/templates/{template_id}/apply", status_code=201)
async def api_apply_template(request: Request, template_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    data = await _payload(request)
    trainee_id = data.get("trainee")
    if not trainee_id:
        raise HTTPException(422, "trainee is required")
    _trainee_for_user(pb, tenant_id, user, trainee_id)
    coach_id = user.id if _role(user) == "coach" else data.get("coach") or user.id
    if _role(user) == "owner" and coach_id != user.id:
        try:
            get_coach_by_id(pb, tenant_id, coach_id)
        except ClientResponseError as error:
            _pb_error(error)
    try:
        plan = apply_template(
            pb,
            tenant_id,
            template_id,
            trainee_id,
            coach_id=coach_id,
            start_date=_date(data.get("start_date"), "start_date"),
            end_date=_date(data.get("end_date"), "end_date"),
            notes=_optional_text(data, "notes", 1000),
        )
        return _record(plan)
    except ClientResponseError as error:
        _pb_error(error)


@router.get("/items")
def api_items(
    request: Request,
    plan_id: str,
    plan_type: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    try:
        plan = _plan_for_user(pb, tenant_id, user, plan_id)
    except ClientResponseError as error:
        _pb_error(error)
    if plan_type not in ALLOWED_PLAN_TYPES or _value(getattr(plan, "type", None)) != plan_type:
        raise HTTPException(422, "Plan type does not match")
    try:
        return _page(
            list_items_by_plan(
                pb,
                tenant_id,
                sanitize_collection_name(plan_type),
                plan=plan_id,
                page=page,
                per_page=per_page,
            ),
            page,
            per_page,
        )
    except ClientResponseError as error:
        _pb_error(error)


@router.post("/items", status_code=201)
async def api_create_item(request: Request):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    data = await _payload(request)
    plan_type = data.get("plan_type")
    plan = _plan_for_user(pb, tenant_id, user, data.get("plan", ""))
    if _value(getattr(plan, "type", None)) != plan_type:
        raise HTTPException(422, "Plan type does not match")
    clean = _item_payload(data, plan_type)
    try:
        return _record(
            create_item(
                pb, tenant_id, sanitize_collection_name(plan_type), {"plan": plan.id, **clean}
            )
        )
    except ClientResponseError as error:
        _pb_error(error)


@router.get("/items/{item_id}")
def api_item_detail(request: Request, item_id: str, plan_type: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    try:
        item = get_item_by_id(pb, tenant_id, sanitize_collection_name(plan_type), item_id)
        _plan_for_user(pb, tenant_id, user, getattr(item, "plan", ""))
        return _record(item)
    except ClientResponseError as error:
        _pb_error(error)
    except ValueError as error:
        raise HTTPException(422, "Invalid plan type") from error


@router.patch("/items/{item_id}")
async def api_update_item(request: Request, item_id: str, plan_type: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    try:
        collection = sanitize_collection_name(plan_type)
        item = get_item_by_id(pb, tenant_id, collection, item_id)
        _plan_for_user(pb, tenant_id, user, getattr(item, "plan", ""))
        data = await _payload(request)
        if data.get("plan") and data["plan"] != getattr(item, "plan", None):
            raise HTTPException(422, "Items cannot be moved to another plan")
        clean = _item_payload(data, plan_type, partial=True)
        if not clean:
            raise HTTPException(422, "At least one item field is required")
        return _record(update_item(pb, item_id, collection, clean))
    except ClientResponseError as error:
        _pb_error(error)
    except ValueError as error:
        raise HTTPException(422, "Invalid plan type") from error


@router.delete("/items/{item_id}", status_code=204)
def api_delete_item(request: Request, item_id: str, plan_type: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    try:
        collection = sanitize_collection_name(plan_type)
        item = get_item_by_id(pb, tenant_id, collection, item_id)
        _plan_for_user(pb, tenant_id, user, getattr(item, "plan", ""))
        delete_item(pb, item_id, collection)
    except ClientResponseError as error:
        _pb_error(error)
    except ValueError as error:
        raise HTTPException(422, "Invalid plan type") from error
    return Response(status_code=204)


def _log_with_context(pb, tenant_id, user, log_id):
    try:
        log = get_progress_log_with_tenant_check(pb, tenant_id, log_id)
        trainee_id = getattr(log, "trainee", "")
        trainee = _trainee_for_user(pb, tenant_id, user, trainee_id)
    except ClientResponseError as error:
        _pb_error(error)
    result = _record(log)
    result["trainee_record"] = _record(trainee)
    result["expand"] = {**(result.get("expand") or {}), "trainee": _record(trainee)}
    return result


@router.get("/progress-logs/{log_id}")
def api_progress_log_detail(request: Request, log_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    return _log_with_context(pb, tenant_id, user, log_id)


@router.post("/progress-logs", status_code=201)
async def api_create_progress_log(request: Request):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    data = await _payload(request)
    trainee_id = data.get("trainee")
    if not trainee_id:
        raise HTTPException(422, "trainee is required")
    _trainee_for_user(pb, tenant_id, user, trainee_id)
    clean = _progress_payload(data)
    uploads = await _photo_uploads(data)
    clean.update({"tenant": tenant_id, "trainee": trainee_id})
    try:
        record = create_progress_log(pb, clean, file_uploads=uploads)
        update_trainee(pb, trainee_id, {"height": clean["height"], "weight": clean["weight"]})
    except ClientResponseError as error:
        _pb_error(error)
    return _record(record)


@router.patch("/progress-logs/{log_id}")
async def api_update_progress_log(request: Request, log_id: str):
    pb, tenant_id, user = _user_context(request)
    _require(user, "owner", "coach")
    _log_with_context(pb, tenant_id, user, log_id)
    data = await _payload(request)
    clean = _progress_payload(data)
    uploads = await _photo_uploads(data)
    try:
        updated = update_progress_log(
            pb, log_id, {"tenant": tenant_id, **clean}, file_uploads=uploads
        )
        log = get_progress_log_with_tenant_check(pb, tenant_id, log_id)
        update_trainee(
            pb, getattr(log, "trainee"), {"height": clean["height"], "weight": clean["weight"]}
        )
    except ClientResponseError as error:
        _pb_error(error)
    return _record(updated)


def _user_trainee(pb, tenant_id, user):
    if _role(user) != "trainee":
        raise HTTPException(403, "Trainee access required")
    try:
        trainee = get_trainee_by_user(pb, tenant_id, user.id)
    except ClientResponseError as error:
        _pb_error(error)
    if trainee is None:
        raise HTTPException(404, "Trainee profile not found")
    return trainee


def _user_plan(pb, tenant_id, user, plan_id):
    trainee = _user_trainee(pb, tenant_id, user)
    try:
        plan = get_plan_by_id(pb, tenant_id, plan_id)
    except ClientResponseError as error:
        _pb_error(error)
    if str(getattr(plan, "trainee", "")) != str(trainee.id):
        raise HTTPException(404, "Plan not found")
    return trainee, plan


@router.get("/user/dashboard")
def api_user_dashboard(request: Request):
    pb, tenant_id, user = _user_context(request)
    trainee = _user_trainee(pb, tenant_id, user)
    try:
        plans = get_plans_by_trainee(pb, tenant_id, trainee.id)
    except ClientResponseError as error:
        _pb_error(error)
    categorized = {plan_type: [] for plan_type in ALLOWED_PLAN_TYPES}
    for plan in plans:
        plan_type = getattr(plan, "type", None)
        if isinstance(plan_type, Enum):
            plan_type = plan_type.value
        if plan_type not in categorized:
            continue
        progress = None
        try:
            progress = get_progress_by_plan(pb, tenant_id, plan.id)
        except ClientResponseError as error:
            if getattr(error, "status", None) != 404:
                _pb_error(error)
        seq = getattr(progress, "current_seq", 1) if progress else 1
        try:
            items = list_items_by_plan(
                pb, tenant_id, sanitize_collection_name(plan_type), plan=plan.id, per_page=500
            )
            items = [
                item for item in getattr(items, "items", items) if getattr(item, "seq", 1) == seq
            ]
        except ClientResponseError as error:
            _pb_error(error)
        row = _record(plan)
        row["progress"] = _record(progress)
        row["items"] = [_record(item) for item in items]
        categorized[plan_type].append(row)
    return {"trainee": _record(trainee), "plans": categorized}


@router.get("/user/plans")
def api_user_plans(request: Request):
    pb, tenant_id, user = _user_context(request)
    trainee = _user_trainee(pb, tenant_id, user)
    try:
        return [_record(plan) for plan in get_plans_by_trainee(pb, tenant_id, trainee.id)]
    except ClientResponseError as error:
        _pb_error(error)


@router.get("/user/plans/{plan_id}")
def api_user_plan_detail(request: Request, plan_id: str):
    pb, tenant_id, user = _user_context(request)
    _, plan = _user_plan(pb, tenant_id, user, plan_id)
    plan_type = getattr(plan, "type", None)
    if isinstance(plan_type, Enum):
        plan_type = plan_type.value
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise HTTPException(409, "Invalid plan type")
    try:
        result = _record(plan)
        items = list_items_by_plan(
            pb, tenant_id, sanitize_collection_name(plan_type), plan=plan_id, per_page=500
        )
        result["items"] = [_record(item) for item in getattr(items, "items", items)]
        return result
    except ClientResponseError as error:
        _pb_error(error)


@router.post("/user/plans/{plan_id}/done")
def api_mark_plan_done(request: Request, plan_id: str):
    pb, tenant_id, user = _user_context(request)
    _, plan = _user_plan(pb, tenant_id, user, plan_id)
    plan_type = getattr(plan, "type", None)
    if isinstance(plan_type, Enum):
        plan_type = plan_type.value
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise HTTPException(409, "Invalid plan type")
    try:
        progress = get_progress_by_plan(pb, tenant_id, plan_id)
    except ClientResponseError as error:
        if getattr(error, "status", None) == 404:
            progress = None
        else:
            _pb_error(error)
    try:
        items = list_items_by_plan(
            pb, tenant_id, sanitize_collection_name(plan_type), plan=plan_id, per_page=500
        )
        sequences = sorted(
            {int(getattr(item, "seq", 1) or 1) for item in getattr(items, "items", items)}
        ) or [1]
    except ClientResponseError as error:
        _pb_error(error)
    current = getattr(progress, "current_seq", sequences[0]) if progress else sequences[0]
    try:
        next_seq = sequences[(sequences.index(int(current)) + 1) % len(sequences)]
    except (ValueError, TypeError):
        next_seq = sequences[0]
    try:
        if progress:
            pb.collection("plan_progress").update(progress.id, {"current_seq": next_seq})
        else:
            pb.collection("plan_progress").create(
                {"tenant": tenant_id, "plan": plan_id, "current_seq": next_seq}
            )
    except ClientResponseError as error:
        _pb_error(error)
    return {"plan_id": plan_id, "current_seq": next_seq}
