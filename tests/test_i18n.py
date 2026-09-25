"""i18n: locale resolution, catalogs, direction, locale switch endpoint."""
from __future__ import annotations

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


@pytest.fixture(autouse=True)
def _reset_locale():
    yield
    set_request_locale(None)


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_registry_enabled_languages():
    assert DEFAULT_LOCALE.code == "fa" and DEFAULT_LOCALE.is_rtl
    for code in ("fa", "en", "es", "tr", "hy"):
        assert code in ENABLED_LOCALES
    assert not LOCALES["en"].is_rtl
    assert LOCALES["fa"].is_rtl


def test_unknown_collapses_to_default():
    set_request_locale("nope")
    assert get_locale().code == "fa"


def test_catalog_translations():
    expected = {
        "en": "Log in",
        "es": "Iniciar sesión",
        "tr": "Giriş",
        "hy": "Մուտք",
        "fa": "ورود",
    }
    for code, want in expected.items():
        set_request_locale(code)
        assert _("ورود") == want, (code, _("ورود"))


def test_locale_switch_sets_cookie_and_redirects(client):
    r = client.get("/locale/en?next=/login")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    raw = "; ".join(r.headers.get_list("set-cookie"))
    assert "locale=en" in raw
    # follow-up request uses cookie
    r2 = client.get("/login")
    assert 'lang="en"' in r2.text


def test_locale_switch_rejects_unknown(client):
    r = client.get("/locale/xx")
    assert r.status_code == 404


def test_locale_switch_open_redirect_guard(client):
    r = client.get("/locale/en?next=//evil.com")
    assert r.headers["location"] == "/"


def test_html_lang_dir_follows_cookie(client):
    r = client.get("/login")
    assert 'lang="fa"' in r.text and 'dir="rtl"' in r.text
    for name in ("فارسی", "English", "Español", "Türkçe", "Հայերեն"):
        assert name in r.text

    r = client.get("/login", cookies={"locale": "en"})
    assert 'lang="en"' in r.text and 'dir="ltr"' in r.text
    set_request_locale("en")
    assert _("ورود") in r.text


def test_locale_switcher_full_reload_attr(client):
    r = client.get("/login")
    assert 'hx-boost="false"' in r.text
    assert "/locale/" in r.text
