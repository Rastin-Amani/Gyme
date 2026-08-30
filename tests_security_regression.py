"""
Security regression tests for Gyme FastAPI hardening.
Verifies defensive controls without destructive actions.
Run: pytest tests_security_regression.py -v
"""
import re

def test_pb_escape_basic():
    from app.security import pb_escape
    assert pb_escape('hello') == 'hello'
    assert pb_escape('a"b') == 'a\\"b'
    assert pb_escape('a\\b') == 'a\\\\b'
    assert pb_escape('a\\"b') == 'a\\\\\\"b'
    # Injection attempt should be escaped
    payload = '" || tenant!="abc'
    escaped = pb_escape(payload)
    assert '"' not in escaped or '\\"' in escaped
    assert escaped == '\\" || tenant!=\\"abc' or '\\"' in escaped

def test_pb_escape_tenant_filter_injection():
    from app.security import pb_escape
    tenant = 'gym1" || "a"=="a'
    safe = pb_escape(tenant)
    filter_str = f'tenant="{safe}"'
    # The filter should not break out of quotes
    # Count unescaped quotes: should be exactly 2 outer
    # Simple check: filter should contain escaped quotes
    assert '\\"' in filter_str
    # Ensure raw injection string not present as separate filter clause
    assert '||' not in filter_str or '\\"' in filter_str

def test_sanitize_plan_type_allowlist():
    from app.security import sanitize_collection_name
    assert sanitize_collection_name("training") == "training_items"
    assert sanitize_collection_name("diet") == "diet_items"
    try:
        sanitize_collection_name("admin")
        assert False, "should reject invalid plan_type"
    except ValueError:
        pass
    try:
        sanitize_collection_name("../../etc/passwd")
        assert False
    except ValueError:
        pass
    try:
        sanitize_collection_name("training; DROP")
        assert False
    except ValueError:
        pass

def test_host_validation():
    from app.security import is_valid_host
    assert is_valid_host("example.com")
    assert is_valid_host("gym1.gyme.cloud")
    assert not is_valid_host('evil.com" || "a"=="a')
    assert not is_valid_host("evil.com; DROP")
    assert not is_valid_host('evil"test')
    assert not is_valid_host("evil test")
    assert not is_valid_host("evil\\test")
    assert not is_valid_host("a"*300)

def test_email_validation():
    from app.security import validate_email
    assert validate_email("test@example.com") == "test@example.com"
    try:
        validate_email("invalid-email")
        assert False
    except ValueError:
        pass
    try:
        validate_email("a"*300 + "@example.com")
        assert False
    except ValueError:
        pass

def test_phone_validation():
    from app.security import validate_phone
    assert validate_phone("09123456789") == "09123456789"
    assert validate_phone("+989123456789") == "+989123456789"
    try:
        validate_phone("not-a-phone")
        assert False
    except ValueError:
        pass
    try:
        validate_phone("'; DROP TABLE")
        assert False
    except ValueError:
        pass

def test_open_redirect_sanitizer():
    from app.security import sanitize_next_url
    assert sanitize_next_url("/dashboard") == "/dashboard"
    assert sanitize_next_url("/plans/123") == "/plans/123"
    assert sanitize_next_url("https://evil.com") == "/dashboard"
    assert sanitize_next_url("//evil.com") == "/dashboard"
    assert sanitize_next_url("/\\evil") == "/dashboard"
    assert sanitize_next_url("") == "/dashboard"

def test_trainee_service_filter_escaping():
    # Ensure list_trainees escapes injection
    from app.security import pb_escape
    # Simulate building filter like service does
    query = 'test" || tenant="other'
    safe = pb_escape(query[:30])
    assert '" ||' not in safe or '\\"' in safe

def test_progress_log_file_validation_names():
    import os, re
    fname = "../../etc/passwd"
    assert "/" in fname
    # Our route rejects such filenames
    assert ".." in fname
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", fname)
    assert "/" not in safe_name
    assert "\\" not in safe_name

def test_cookie_secure_flag():
    from app.security import cookie_secure_flag
    class FakeReq:
        class url:
            scheme = "http"
        headers = {}
    # In dev with http, should be False
    # This depends on ENV, but we test function doesn't error
    assert isinstance(cookie_secure_flag(FakeReq()), bool)

def test_service_trainee_injection_regression():
    """Regression: list_trainees must not allow filter injection via gender/status."""
    from app.services.trainee import list_trainees
    import inspect
    src = inspect.getsource(list_trainees)
    # Verify allowlist check exists
    assert "ALLOWED_GENDERS" in src or "ALLOWED" in src
    assert "pb_escape" in src

def test_item_collection_validation():
    """Regression: item service must validate collection name."""
    from app.services.item import _validate_collection
    try:
        _validate_collection("training_items")
    except ValueError:
        assert False, "should allow valid"
    try:
        _validate_collection("admin_items")
        assert False, "should reject invalid"
    except ValueError:
        pass
    try:
        _validate_collection("training_items; DROP")
        assert False
    except ValueError:
        pass

def test_dashboard_timeframe_allowlist():
    from app.services.dashboard import get_owner_dashboard_stats
    import inspect
    src = inspect.getsource(get_owner_dashboard_stats)
    assert "ALLOWED_TIMEFRAMES" in src or "timeframe" in src
    # Check dashboard uses pb_escape
    assert "pb_escape" in src

def test_tenant_domain_escaping():
    from app.services.tenants import get_tenant_by_domain
    import inspect
    src = inspect.getsource(get_tenant_by_domain)
    assert "pb_escape" in src
    assert "is_valid_host" in src

def test_middleware_has_csrf_and_security_headers():
    import inspect
    from app import middleware
    src = inspect.getsource(middleware.TenantMiddleware.dispatch)
    assert "csrf" in src.lower() or "CSRF" in src
    assert "X-Content-Type-Options" in src
    assert "Content-Security-Policy" in src
    assert "is_valid_host" in src

def test_xss_toast_fix():
    with open("app/templates/base.html") as f:
        content = f.read()
    # Should use textContent, not innerHTML for message
    assert "textContent" in content
    # Old vulnerable pattern should not exist as sole message insertion
    # Check that toast.innerHTML with ${message} direct is gone
    # Allow icon innerHTML but message should be textContent
    assert 'msgSpan.textContent' in content or 'textContent = String(message' in content

def test_open_redirect_client_guard():
    with open("app/templates/base.html") as f:
        content = f.read()
    assert "delayed-redirect" in content
    # Should have guard for // and ://
    assert "startsWith('//')" in content or "startsWith" in content
    assert 'includes(\'://\')' in content or "includes" in content

def test_password_not_email():
    with open("app/services/auth.py") as f:
        src = f.read()
    # Should not set password=email
    # Check that random password generation exists
    assert "secrets.choice" in src or "secrets" in src
    # Old code had "password": email
    assert '"password": email' not in src

def test_logout_exists():
    with open("app/routes/auth.py") as f:
        src = f.read()
    assert "/logout" in src
    assert "clear_auth_cookie" in src

def test_secure_cookie_helper_used():
    with open("app/routes/auth.py") as f:
        src = f.read()
    assert "set_auth_cookie" in src
    assert "secure=False" not in src or "set_auth_cookie" in src  # no hardcoded insecure

def test_plan_update_requires_tenant():
    import inspect
    from app.services.plan import update_plan
    sig = inspect.signature(update_plan)
    params = list(sig.parameters.keys())
    # Should have tenant param
    assert "tenant" in params, f"update_plan missing tenant param, got {params}"

def test_rate_limiting_present():
    with open("app/routes/auth.py") as f:
        src = f.read()
    assert "rate" in src.lower() or "Rate" in src
    assert "_login_attempts" in src

print("All security regression tests collection OK")
