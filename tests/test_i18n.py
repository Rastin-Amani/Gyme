"""i18n: locale resolution, catalogs, direction, locale switch endpoint."""

from __future__ import annotations

import re

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
    assert 'lang="en"' in r.text and 'dir="ltr"' in r.text
    for name in ("English", "Español", "Türkçe", "Հայերեն"):
        assert name in r.text

    # Non-default enabled locales are all LTR as well.
    r = client.get("/login", cookies={"locale": "tr"})
    assert 'lang="tr"' in r.text and 'dir="ltr"' in r.text


def test_ui_has_no_persian(client):
    r = client.get("/login")
    # Assert absence using the Arabic/Persian unicode block so no Persian words
    # ever need to appear in the source tree itself.
    assert re.search("[\u0600-\u06ff]", r.text) is None
    assert 'dir="rtl"' not in r.text


def test_locale_switcher_full_reload_attr(client):
    r = client.get("/login")
    assert 'hx-boost="false"' in r.text
    assert "/locale/" in r.text
