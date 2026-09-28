"""i18n: locale resolution, catalogs, direction, locale switch endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.i18n import (
    DEFAULT_LOCALE,
    ENABLED_LOCALES,
    LOCALES,
    _,
    get_locale,
    set_request_locale,
)
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _reset_locale():
    yield
    set_request_locale(None)


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_registry_enabled_languages():
    assert DEFAULT_LOCALE.code == "en" and not DEFAULT_LOCALE.is_rtl
    for code in ("en", "es", "tr", "hy"):
        assert code in ENABLED_LOCALES
    # Every supported locale is LTR — the app is English-only and LTR.
    for code, loc in LOCALES.items():
        assert not loc.is_rtl, code


def test_unknown_collapses_to_default():
    set_request_locale("nope")
    assert get_locale().code == "en"


def test_catalog_english_source():
    # English is the source language; the default catalog is identity.
    set_request_locale("en")
    assert _("Log in") == "Log in"


def test_locale_switch_sets_cookie_and_redirects(client):
    r = client.get("/locale/en?next=/login")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    raw = "; ".join(r.headers.get_list("set-cookie"))
    assert "locale=en" in raw


def test_locale_switch_rejects_unknown(client):
    r = client.get("/locale/xx")
    assert r.status_code == 404


def test_locale_switch_open_redirect_guard(client):
    r = client.get("/locale/en?next=//evil.com")
    assert r.headers["location"] == "/"


def test_svelte_document_language_uses_allowlisted_locale():
    src = (ROOT / "frontend/src/hooks.server.ts").read_text(encoding="utf-8")
    assert "new Set(['en', 'es', 'tr', 'hy'])" in src
    assert "event.url.searchParams.get('locale')" in src
    assert "event.cookies.get('gyme_locale')" in src
    assert "html.replace('<html lang=\"en\">'" in src


def test_svelte_ui_has_no_rtl_locale_content():
    sources = list((ROOT / "frontend/src").rglob("*.svelte")) + list(
        (ROOT / "frontend/src").rglob("*.ts")
    )
    content = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    assert not any("\u0600" <= char <= "\u06ff" for char in content)


def test_svelte_locale_switcher_is_not_htmx():
    src = (ROOT / "frontend/src/routes/+layout.svelte").read_text(encoding="utf-8")
    assert "locale" in src.lower()
    assert "hx-boost" not in src.lower()
