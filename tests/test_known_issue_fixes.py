"""
Regression tests for the v0.9.1 fix batch (known issues #2, #4, #6, #7,
#8, #10, #11, #12, #13, #15, #16 and release configuration).

Like tests/test_security_regression.py these are static source-inspection
tests: they verify contracts without booting the app (TenantMiddleware
would otherwise hit a live PocketBase instance).

Run: pytest -q
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path):
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _does_not_contain(rel_path, needle):
    return needle not in _read(rel_path)


# --- Issue #2: training item category is persisted -----------------------


def test_item_create_declares_category_param():
    src = _read("app/routes/item.py")
    create_src = src[src.index("def item_create") : src.index("def item_update")]
    assert r"category: str = Form(None)" in create_src


def test_item_update_declares_category_param():
    src = _read("app/routes/item.py")
    update_src = src[src.index("def item_update") :]
    assert r"category: str = Form(None)" in update_src


def test_training_payload_includes_category():
    src = _read("app/routes/item.py")
    # The training branch of both create and update must store category
    assert '"category": category,' in src
    assert src.count('"category": category,') >= 2


def test_category_only_in_training_branch():
    src = _read("app/routes/item.py")
    # slice out the create handler only
    create_src = src[src.index("def item_create") : src.index("def item_update")]
    # every occurrence must sit after the training branch begins
    training_branch = create_src.index('if plan_type == "training":')
    for m in re.finditer(r'"category": category,', create_src):
        assert m.start() > training_branch


# --- Issue #4: plan list coach filter reads users, not coaches -----------


def test_plan_list_filters_users_by_role_coach():
    src = _read("app/routes/plan.py")
    plan_list_fn = src[src.index("def plan_list") : src.index("def plan_new_form")]
    assert 'pb.collection("users")' in plan_list_fn
    assert 'role="coach"' in plan_list_fn
    # legacy coaches-collection query removed from the list handler
    assert 'pb.collection("coaches")' not in plan_list_fn


# --- Issue #6: owner profile links to /change-password -------------------


def test_profile_has_no_plans_edit_link():
    assert _does_not_contain("app/templates/pages/owner/profile/profile.html", "/plans/edit")


def test_profile_links_to_change_password():
    src = _read("app/templates/pages/owner/profile/profile.html")
    assert 'href="/change-password"' in src


# --- Issue #7: app version is a single source of truth -------------------


def test_app_version_matches_version_text():
    main_src = _read("app/main.py")
    m = re.search(r'APP_VERSION = "([^"]+)"', main_src)
    assert m, "APP_VERSION constant missing in app/main.py"
    # app/version.text stores the version wrapped in quotes (e.g. "0.9.1")
    version_text = _read("app/version.text").strip().strip('"')
    assert m.group(1) == version_text


def test_sw_register_uses_app_version():
    src = _read("app/templates/base.html")
    assert "/sw.js?v={{ app_version }}" in src


def test_no_hardcoded_old_sw_version():
    assert _does_not_contain("app/templates/base.html", "sw.js?v=0.8.1")


# --- Issue #10: list_items sorts by seq, order ---------------------------


def test_list_items_sorts_by_seq_order():
    src = _read("app/services/item.py")
    list_src = src[src.index("def list_items") : src.index("def list_items_by_plan")]
    assert "+seq,+order" in list_src
    assert "+day,+order" not in list_src


# --- Issue #11: auth/tenant services use get_pb() ------------------------


def test_login_user_defaults_to_get_pb():
    src = _read("app/services/auth.py")
    login_src = src[src.index("def login_user") : src.index("def create_user")]
    assert "pb=None" in login_src
    assert "get_pb()" in login_src


def test_auth_service_no_module_pb_singleton():
    src = _read("app/services/auth.py")
    assert "from app.pb import pb" not in src
    assert "from app.pb import get_pb" in src


def test_tenants_lookup_uses_get_pb_and_keeps_escape():
    src = _read("app/services/tenants.py")
    lookup_src = src[src.index("def _lookup_tenant") :]
    assert "get_pb()" in lookup_src
    assert "pb_escape(domain)" in lookup_src
    # keeps is_valid_host guard used from get_tenant_by_domain
    assert "is_valid_host" in src


# --- Issue #12: debug-coach-stats is dev-only ----------------------------


def test_debug_coach_stats_has_no_route_decorator():
    src = _read("app/routes/dashboard.py")
    idx = src.index("def debug_coach_stats")
    decorator_block = src[max(0, idx - 200) : idx]
    assert "@router.get" not in decorator_block


def test_debug_coach_stats_registered_only_outside_prod():
    main_src = _read("app/main.py")
    # anchor on the router-registration block (there is an earlier
    # `if not IS_PROD:` for ALLOWED_HOSTS handling)
    idx = main_src.index("app.include_router(debug.router)")
    block = main_src[idx : idx + 300]
    assert "dashboard.router.add_api_route" in block
    assert '"/dashboard/debug-coach-stats"' in block


# --- Issue #13: delayed-redirect comment matches 500ms -------------------


def test_delayed_redirect_comment_matches_delay():
    src = _read("app/templates/base.html")
    assert "}, 500);" in src
    # No stale "1.2 seconds" comment may remain next to the delay
    assert "1.2 seconds" not in src


# --- Issue #15: unknown tenant on private routes redirects to login ------


def test_middleware_tenant_none_redirect():
    src = _read("app/middleware.py")
    dispatch_src = src[src.index("async def dispatch") :]
    assert "tenant is None" in dispatch_src
    assert 'HX-Redirect"] = "/login"' in dispatch_src
    # the redirect must apply to non-public paths other than "/"
    assert "not is_public" in dispatch_src
    assert 'path != "/"' in dispatch_src


# --- Issue #8: PB_URL defaults to local dev and fails fast in prod -------


def test_pb_url_defaults_to_localhost():
    src = _read("app/pb.py")
    assert "http://127.0.0.1:8090" in src


def test_pb_url_required_in_production():
    src = _read("app/pb.py")
    assert 'os.getenv("ENV", "dev").lower() == "production"' in src
    assert "RuntimeError" in src
    assert "PB_URL must be set in production" in src


# --- Issue #16: deleting a trainee cascades to the linked user -----------


def test_delete_trainee_cascades_to_user():
    src = _read("app/services/trainee.py")
    delete_src = src[src.index("def delete_trainee") :]
    assert 'pb.collection("trainees").delete' in delete_src
    assert 'pb.collection("users").delete' in delete_src


def test_delete_trainee_keeps_tenant_ownership_check():
    src = _read("app/services/trainee.py")
    delete_src = src[src.index("def delete_trainee") :]
    assert "get_trainee_by_id" in delete_src


# --- Release configuration: CI workflow + license ------------------------


def test_ci_workflow_checks_lint_format_and_tests():
    src = _read(".github/workflows/ci.yml")
    assert "ruff check" in src
    assert "black --check" in src
    assert "pytest" in src


def test_license_file_present():
    license_text = _read("LICENSE")
    assert "Permission to use, copy, modify, and/or distribute" in license_text
