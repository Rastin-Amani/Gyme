import copy
import os
from pocketbase import PocketBase
from pocketbase.stores.base_auth_store import BaseAuthStore

# Fetches PB_URL from the environment, defaults to local dev instance if not set.
# In production PB_URL must be provided explicitly; we fail fast rather than
# silently pointing a production deployment at a development database.
_raw_pb_url = os.getenv("PB_URL", "").strip()
if not _raw_pb_url:
    if os.getenv("ENV", "dev").lower() == "production":
        raise RuntimeError("PB_URL must be set in production")
    _raw_pb_url = "http://127.0.0.1:8090"
# If ENV=production and URL still http, warn and prefer https
if os.getenv("ENV", "dev").lower() == "production" and _raw_pb_url.startswith("http://"):
    import logging as _log

    _log.getLogger(__name__).warning("PB_URL is http in production; force https if possible")
PB_URL = _raw_pb_url
pb = PocketBase(PB_URL)

# One keep-alive connection pool for the whole process. Building a fresh
# PocketBase() per request rebuilt the httpx client (SSL context + TCP connect)
# on every PB call: ~14 ms/call locally vs ~0.7 ms pooled. The blueprint below
# is copied per request so auth stores stay isolated.
_client = PocketBase(PB_URL)
_BLUEPRINT = _client
_SERVICES = ("backups", "collections", "files", "health", "logs", "settings", "realtime", "crons")


def get_pb():
    # Fresh instance (own auth store, own record services) sharing one pool.
    instance = copy.copy(_BLUEPRINT)
    instance.auth_store = BaseAuthStore()
    instance.record_services = {}
    for name in _SERVICES:
        getattr(instance, name).client = instance
    return instance
