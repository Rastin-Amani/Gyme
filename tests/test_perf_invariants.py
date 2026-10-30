"""Guards for the page-load performance contracts.

Fails if the pooled PocketBase client stops isolating auth (a security
property, not just a speed one).

Run: pytest -q
"""

from app.pb import get_pb


def test_get_pb_isolates_auth_but_shares_connection_pool():
    a, b = get_pb(), get_pb()
    assert a is not b
    assert a.auth_store is not b.auth_store
    assert a.http_client is b.http_client
    assert a.collection("users").client is a
    a.auth_store.save("token-a", None)
    assert b.auth_store.token == ""
    assert a.auth_store.token == "token-a"
