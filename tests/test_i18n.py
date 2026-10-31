"""i18n: locale resolution, catalogs, direction, locale switch endpoint."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from babel.messages.pofile import read_po
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
    for code in ("en", "es", "tr", "hy", "ru"):
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
    for name in ("English", "Español", "Türkçe", "Հայերեն", "Русский"):
        assert name in r.text
    # One shared language icon; no flags (emoji and hand-drawn flags look
    # broken at 16px and the language names already say which is which).
    assert "m10.5 21 5.25-11.25" in r.text
    assert 'viewBox="0 0 20 15"' not in r.text

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


def test_russian_catalog_renders(client):
    r = client.get("/login", cookies={"locale": "ru"})
    assert 'lang="ru"' in r.text
    assert "Войти" in r.text


def test_every_enabled_catalog_is_complete():
    """An unmaintained empty catalog silently looks like English on switch."""
    pot = read_po(open(Path("app/locales/messages.pot"), "rb"))
    ids = {m.id for m in pot if m.id}
    for code in ENABLED_LOCALES:
        if code == DEFAULT_LOCALE.code:
            continue
        po = read_po(open(Path(f"app/locales/{code}/LC_MESSAGES/messages.po"), "rb"))
        missing = [
            m.id for m in po if m.id in ids and not m.string and not getattr(m, "obsolete", False)
        ]
        assert not missing, (code, missing[:5])


def test_switcher_placement_is_scoped():
    """`up` must not leak from the sidebar include into the header include."""
    src = Path("app/templates/layouts/dashboard.html").read_text(encoding="utf-8")
    includes = [line for line in src.splitlines() if "components/locale_switcher.html" in line]
    assert includes
    assert all("{% with" in line for line in includes), includes
