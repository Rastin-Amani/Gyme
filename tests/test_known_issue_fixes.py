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
    # ASSET_VERSION is APP_VERSION + built-asset stamp, so this is the stronger
    # contract: the SW URL changes on every deploy that touches CSS/JS.
    src = _read("app/templates/base.html")
    assert "sw.js?v={{ asset_version }}" in src


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


# --- Runtime regressions found by role walkthrough (owner/coach/trainee) --


def _function_src(src, name, next_name):
    return src[src.index(f"def {name}") : src.index(f"def {next_name}")]


def test_plan_new_form_passes_tenant_record_not_id():
    src = _read("app/routes/plan.py")
    fn = _function_src(src, "plan_new_form", "show_plan_detail")
    assert '"tenant": request.state.tenant' in fn
    assert '"tenant": tenant,' not in fn


def test_item_confirm_delete_uses_new_template_signature():
    src = _read("app/routes/item.py")
    fn = _function_src(src, "item_confirm_delete", "item_create")
    assert "request=request" in fn
    assert 'TemplateResponse("modals/confirm_delete.html"' not in fn


def test_items_form_delete_modal_passes_plan_type():
    src = _read("app/templates/modals/items_form.html")
    assert "confirm-delete?plan_type={{ plan_type }}" in src


def test_trainee_role_is_blocked_from_staff_mutations():
    plan_src = _read("app/routes/plan.py")
    item_src = _read("app/routes/item.py")
    trainee_src = _read("app/routes/trainee.py")
    for name, next_name in (
        ("plan_create", "plan_update"),
        ("plan_update", "plan_confirm_delete"),
        ("plan_delete", None),
        ("template_apply", "plan_create"),
    ):
        fn = plan_src[plan_src.index(f"def {name}") :]
        if next_name:
            fn = plan_src[plan_src.index(f"def {name}") : plan_src.index(f"def {next_name}")]
        assert "deny_trainee(" in fn, name
    for name in ("item_create", "item_update", "item_delete"):
        fn = item_src[item_src.index(f"def {name}") :]
        assert "deny_trainee(" in fn[:2000], name
    for name in ("trainee_create", "trainee_update", "trainee_delete"):
        fn = trainee_src[trainee_src.index(f"def {name}") :]
        assert "deny_trainee(" in fn[:2000], name


def test_coach_mutations_are_scoped_to_own_plans():
    plan_src = _read("app/routes/plan.py")
    delete_src = plan_src[plan_src.index("def plan_delete") :]
    assert 'getattr(plan, "coach", None) != user.id' in delete_src
    item_src = _read("app/routes/item.py")
    for name in ("item_update", "item_delete"):
        fn = item_src[item_src.index(f"def {name}") :][:2500]
        assert 'getattr(existing_plan, "coach", "")' in fn or 'getattr(plan_obj, "coach", "")' in fn


def test_stale_ids_redirect_instead_of_crashing():
    plan_src = _read("app/routes/plan.py")
    edit_src = plan_src[
        plan_src.index("def plan_edit_form") : plan_src.index("def template_apply_form")
    ]
    assert "except Exception" in edit_src and '"/plans"' in edit_src
    apply_src = plan_src[
        plan_src.index("def template_apply_form") : plan_src.index("def template_apply(")
    ]
    assert "except Exception" in apply_src
    user_plan_src = _read("app/routes/user/plan.py")
    assert "except Exception" in user_plan_src
    trainee_src = _read("app/routes/trainee.py")
    assert (
        "except Exception"
        in trainee_src[
            trainee_src.index("def trainee_edit_form") : trainee_src.index("def trainee_create")
        ]
    )


def test_new_accounts_surface_initial_password_once():
    auth_src = _read("app/services/auth.py")
    assert '"password": random_pwd' in auth_src
    assert 'user_result.get("password", "")' in _read("app/routes/trainee.py")
    assert 'user_result.get("password", "")' in _read("app/routes/coach.py")


def test_layout_exposes_logout():
    assert 'href="/logout"' in _read("app/templates/layouts/dashboard.html")


def test_plan_create_and_update_require_a_trainee():
    src = _read("app/routes/plan.py")
    assert src.count("if not is_template_bool and not trainee:") >= 2


def test_plan_pagination_omits_disabled_links():
    src = _read("app/templates/pages/owner/plan/plans.html")
    assert "{% if page > 1 %}" in src and "{% if page < total_pages %}" in src


def test_data_theme_matches_the_one_built_theme():
    # Only one daisyUI theme is compiled; any other data-theme renders unstyled.
    assert 'data-theme="gyme"' in _read("app/templates/base.html")
    assert "[data-theme=gyme]" in _read("app/static/app.css")


# --- Browser-only regressions found with a real headless browser ----------


def test_toast_container_does_not_swallow_clicks():
    src = _read("app/templates/base.html")
    container = src[src.index('id="toast-container"') : src.index('role="status"')]
    assert "pointer-events-none" in container


def test_modal_close_is_deferred_so_followup_events_bubble():
    src = _read("app/static/main.js")
    clear_modal = src[
        src.index("function clearModal()") : src.index("document.addEventListener('closeModal'")
    ]
    assert "setTimeout(" in clear_modal


def test_shell_navigation_pushes_the_url():
    src = _read("app/static/main.js")
    nav = src[src.index("window.gymeNav") : src.index("function clearModal()")]
    assert "pushUrl" not in nav
    assert "push: 'true'" in nav


def test_dashboard_timeframe_has_no_form_sync_without_a_form():
    src = _read("app/templates/pages/owner/dashboard.html")
    assert "hx-sync" not in src or 'hx-sync="this:replace"' in src


def test_filter_panels_survive_result_swaps():
    assert 'hx-preserve="true"' in _read("app/templates/pages/owner/plan/plans.html")
    assert 'hx-preserve="true"' in _read("app/templates/pages/owner/trainee/trainees.html")


def test_csp_allows_pocketbase_images():
    src = _read("app/middleware.py")
    assert "PB_ORIGIN" in src
    assert "img-src 'self' data: https: blob:" in src


def test_service_worker_ignores_cross_origin_assets():
    src = _read("app/static/sw.js")
    assert "url.origin !== self.location.origin" in src


def test_progress_log_refresh_targets_its_own_fragment():
    src = _read("app/templates/pages/owner/trainee/trainee_detail.html")
    assert 'id="progress-logs-content"' in src
    assert 'hx-select="#progress-logs-content"' in src
    assert 'hx-select="unset"' in src  # nested edit button must not inherit it


def test_duplicate_trainee_error_uses_immediate_toast():
    src = _read("app/routes/trainee.py")
    fn = src[src.index("def trainee_create") : src.index("def trainee_update")]
    assert "hx_toast_now(error_msg" in fn


def test_progress_log_edit_refresh_has_a_listener():
    # The edit handler emits performListRefresh; the trainee detail must listen.
    assert "performListRefresh" in _read("app/templates/pages/owner/trainee/trainee_detail.html")
    assert "performListRefresh" in _read("app/routes/progress_logs.py")


# --- UI polish regressions (phone field, dock, icons) ---------------------


def test_phone_field_uses_inset_label_and_dial_codes_only():
    src = _read("app/templates/components/phone_field.html")
    # Same inset-label structure as the date field, so the two align in a grid.
    assert '<label class="input w-full">' in src
    # Plain dial codes: emoji flags render as letter pairs/tofu on Windows.
    assert "x-text=\"'+' + c.dial\"" in src
    assert "c.flag" not in src
    # Native arrow is suppressed; the DaisyUI select chevron remains.
    assert "appearance-none" in src
    assert 'x-init="$nextTick(() => { $el.value = dialCode; })"' in src


def test_dock_active_item_is_primary_filled_not_underlined():
    src = _read("app/templates/layouts/dashboard.html")
    assert "link.classList.add('menu-active');" in src
    assert "classList.add('menu-active', 'dock-active')" not in src  # no underline bar
    assert "'bg-primary', 'text-primary-content', 'rounded-field'" in src


def test_dashboard_plan_icons_match_the_plan_list():
    stats = _read("app/templates/components/dashboard_stats.html")
    plans = _read("app/templates/pages/owner/plan/plans.html")
    dumbbell = "M6.75 6.75v10.5M17.25 6.75v10.5M3.75 9v6M20.25 9v6M6.75 12h10.5"
    diet = "M12 21a9 9 0 0 0 9-9c0-1.5-.5-3-1.5-4.5S17 4 15 4c-1 0-2 .5-3 1S10 6 9 6"
    assert dumbbell in plans and dumbbell in stats
    assert diet in plans and diet in stats


def test_nav_icons_use_users_and_user_circle():
    src = _read("app/templates/layouts/dashboard.html")
    assert "M15 19.128a9.38 9.38 0 0 0 2.625.372" in src  # users (Trainees)
    assert "M17.982 18.725A7.488 7.488 0 0 0 12 15.75" in src  # user-circle (Profile)
    assert "M9.594 3.94" not in src  # old gear icon is gone


def test_favicon_fallback_is_a_real_file():
    src = _read("app/templates/base.html")
    assert 'href="/static/icons/favicon.ico"' in src
    assert "data:image/svg+xml,%3Csvg xmlns=http://" not in src


def test_trainee_status_dot_is_a_plain_circle():
    src = _read("app/templates/pages/owner/trainee/trainees.html")
    dot = src[src.index("indicator-item") : src.index("indicator-item") + 160]
    assert "badge" not in dot
    assert "rounded-full" in dot
