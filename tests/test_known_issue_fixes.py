"""Regression checks for current FastAPI services and release configuration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path):
    return (ROOT / rel_path).read_text(encoding="utf-8")


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
