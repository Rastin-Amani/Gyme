import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.routes import api


class _AuthStore:
    model = None

    def clear(self):
        self.model = None


class _PB:
    def __init__(self):
        self.auth_store = _AuthStore()


def _request(path, method="GET", headers=(), body=b"", client=("203.0.113.5", 1234), cookies=""):
    raw_headers = [(b"host", b"gym.test"), *headers]
    if cookies:
        raw_headers.append((b"cookie", cookies.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": client,
        "server": ("gym.test", 80),
    }
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


def test_api_router_covers_frontend_operations():
    routes = {
        (method, route.path)
        for route in api.router.routes
        for method in getattr(route, "methods", ())
    }
    expected = {
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/change-password"),
        ("PATCH", "/api/v1/auth/profile"),
        ("GET", "/api/v1/dashboard"),
        ("GET", "/api/v1/dashboard/coach-stats"),
        ("GET", "/api/v1/trainees"),
        ("POST", "/api/v1/trainees"),
        ("PATCH", "/api/v1/trainees/{trainee_id}"),
        ("GET", "/api/v1/trainees/{trainee_id}"),
        ("DELETE", "/api/v1/trainees/{trainee_id}"),
        ("GET", "/api/v1/coaches"),
        ("GET", "/api/v1/coaches/{coach_id}"),
        ("POST", "/api/v1/coaches"),
        ("PATCH", "/api/v1/coaches/{coach_id}"),
        ("DELETE", "/api/v1/coaches/{coach_id}"),
        ("GET", "/api/v1/plans"),
        ("POST", "/api/v1/plans"),
        ("GET", "/api/v1/plans/{plan_id}"),
        ("PATCH", "/api/v1/plans/{plan_id}"),
        ("DELETE", "/api/v1/plans/{plan_id}"),
        ("POST", "/api/v1/templates/{template_id}/apply"),
        ("GET", "/api/v1/items"),
        ("GET", "/api/v1/items/{item_id}"),
        ("POST", "/api/v1/items"),
        ("PATCH", "/api/v1/items/{item_id}"),
        ("DELETE", "/api/v1/items/{item_id}"),
        ("GET", "/api/v1/progress-logs/{log_id}"),
        ("POST", "/api/v1/progress-logs"),
        ("PATCH", "/api/v1/progress-logs/{log_id}"),
        ("GET", "/api/v1/user/dashboard"),
        ("GET", "/api/v1/user/plans"),
        ("GET", "/api/v1/user/plans/{plan_id}"),
        ("POST", "/api/v1/user/plans/{plan_id}/done"),
    }
    assert expected <= routes


def test_response_serialization_strips_secrets_recursively():
    value = {
        "id": "record",
        "password": "pw",
        "expand": {
            "user": {
                "id": "user",
                "email": "a@example.test",
                "token": "secret",
                "auth_store": "secret",
            }
        },
    }
    assert api._record(value) == {
        "id": "record",
        "expand": {"user": {"id": "user", "email": "a@example.test"}},
    }


@pytest.mark.parametrize(
    "user",
    [
        SimpleNamespace(role="trainee"),
        SimpleNamespace(),
        SimpleNamespace(role=""),
        SimpleNamespace(role="admin"),
    ],
)
def test_api_role_guard_fails_closed_with_http_403(user):
    with pytest.raises(HTTPException) as error:
        api._require(user, "owner", "coach")
    assert error.value.status_code == 403


def test_coach_progress_log_context_checks_trainee_assignment(monkeypatch):
    coach = SimpleNamespace(id="coach-1", role="coach")
    monkeypatch.setattr(
        api,
        "get_progress_log_with_tenant_check",
        lambda *_: SimpleNamespace(id="log-1", trainee="trainee-1"),
    )

    def deny_assignment(_pb, _tenant_id, user, trainee_id):
        assert user is coach
        assert trainee_id == "trainee-1"
        raise HTTPException(403, "Trainee is not assigned to this coach")

    monkeypatch.setattr(api, "_trainee_for_user", deny_assignment)
    with pytest.raises(HTTPException) as error:
        api._log_with_context(None, "tenant-a", coach, "log-1")
    assert error.value.status_code == 403


def test_owner_may_assign_a_plan_to_themselves_without_coach_lookup():
    owner = SimpleNamespace(id="owner-1", role="owner")
    api._verify_plan_relations(None, "tenant-a", owner, {"coach": owner.id})


def test_coach_trainee_filter_has_no_200_record_cutoff():
    from app.services.trainee import list_trainees

    captured = {}

    class Collection:
        def __init__(self, name):
            self.name = name

        def get_full_list(self, query_params):
            return [SimpleNamespace(trainee=f"trainee-{index}") for index in range(250)]

        def get_list(self, *, page, per_page, query_params):
            captured.update(query_params)
            return SimpleNamespace(items=[], total_items=0)

    class PB:
        def collection(self, name):
            return Collection(name)

    list_trainees(PB(), "tenant-a", coach_id="coach-a")
    assert 'id="trainee-249"' in captured["filter"]


def test_login_sets_httponly_cookie_and_returns_no_token(monkeypatch):
    request = _request(
        "/api/v1/auth/login",
        "POST",
        headers=[(b"content-type", b"application/json")],
        body=json.dumps({"identity": "coach@example.test", "password": "StrongPass123"}).encode(),
    )
    request.state.tenant = _tenant()
    request.state.pb = _PB()
    monkeypatch.setattr(
        api,
        "login_user",
        lambda *_args, **_kwargs: {
            "ok": True,
            "user": SimpleNamespace(
                id="user-1", role="coach", email="coach@example.test", first_name="Sam"
            ),
            "token": "never-return-this",
        },
    )

    response = asyncio.run(api.auth_login(request))
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "user": {
            "id": "user-1",
            "role": "coach",
            "first_name": "Sam",
            "email": "coach@example.test",
        }
    }
    cookie = response.headers["set-cookie"]
    assert "pb_auth=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "never-return-this" not in response.body.decode()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, 1.25])
def test_integer_validation_rejects_non_integers_and_non_finite_values(value):
    with pytest.raises(HTTPException) as error:
        api._number(value, "seq", minimum=1, integer=True)
    assert error.value.status_code == 422


def test_middleware_returns_json_401_for_private_api(monkeypatch):
    from app import middleware

    async def lookup(_):
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    request = _request("/api/v1/auth/me")

    async def call_next(_request):
        return Response()

    response = asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert response.status_code == 401
    assert json.loads(response.body) == {"detail": "Authentication required"}
    assert response.headers["cache-control"] == "no-store, private"


def _tenant():
    return SimpleNamespace(id="tenant-a")


def test_middleware_blocks_cross_origin_api_mutation(monkeypatch):
    from app import middleware

    async def lookup(_):
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    monkeypatch.setattr(
        middleware,
        "_load_auth",
        lambda _pb, _token: SimpleNamespace(id="u1", role="owner", tenant="tenant-a"),
    )
    request = _request(
        "/api/v1/auth/logout",
        "POST",
        headers=[(b"origin", b"https://evil.test")],
        cookies="pb_auth=valid-token",
    )

    async def call_next(_request):
        return Response()

    response = asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert response.status_code == 403
    assert json.loads(response.body) == {"detail": "CSRF validation failed"}


def test_middleware_checks_csrf_for_login_too(monkeypatch):
    from app import middleware

    async def lookup(_):
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    request = _request("/api/v1/auth/login", "POST", headers=[(b"origin", b"https://evil.test")])

    async def call_next(_request):
        return Response()

    response = asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert response.status_code == 403
    assert json.loads(response.body) == {"detail": "CSRF validation failed"}


def test_cookie_from_another_tenant_is_not_authenticated(monkeypatch):
    from app import middleware

    async def lookup(_):
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    monkeypatch.setattr(
        middleware,
        "_load_auth",
        lambda _pb, _token: SimpleNamespace(id="u1", role="owner", tenant="tenant-b"),
    )
    request = _request("/api/v1/auth/me", cookies="pb_auth=valid-token")

    async def call_next(_request):
        return Response()

    response = asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert response.status_code == 401
    assert json.loads(response.body) == {"detail": "Authentication required"}


def test_untrusted_forwarded_host_does_not_change_tenant_lookup(monkeypatch):
    from app import middleware

    requested_hosts = []

    async def lookup(host):
        requested_hosts.append(host)
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    request = _request("/api/v1/auth/login", headers=[(b"x-forwarded-host", b"attacker.test")])

    async def call_next(_request):
        return Response()

    asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert requested_hosts == ["gym.test"]


def test_trusted_proxy_forwarded_host_is_used(monkeypatch):
    from app import middleware

    requested_hosts = []

    async def lookup(host):
        requested_hosts.append(host)
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    monkeypatch.setenv("TRUSTED_PROXIES", "203.0.113.0/24")
    request = _request(
        "/login", headers=[(b"x-forwarded-host", b"gym.test"), (b"x-forwarded-proto", b"https")]
    )

    async def call_next(_request):
        return Response()

    asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
    assert requested_hosts == ["gym.test"]


def test_trusted_proxy_client_ip_is_used_for_rate_limits(monkeypatch):
    from app import middleware

    async def lookup(_):
        return _tenant()

    monkeypatch.setattr(middleware, "get_tenant_by_domain", lookup)
    monkeypatch.setattr(middleware, "get_pb", _PB)
    monkeypatch.setenv("TRUSTED_PROXIES", "172.28.0.2/32")
    request = _request(
        "/login",
        headers=[
            (b"x-forwarded-host", b"gym.test"),
            (b"x-real-client-ip", b"203.0.113.42"),
        ],
        client=("172.28.0.2", 1234),
    )

    async def call_next(request):
        assert request.state.client_ip == "203.0.113.42"
        return Response()

    asyncio.run(middleware.TenantMiddleware(None).dispatch(request, call_next))
