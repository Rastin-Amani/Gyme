import os
from pocketbase import PocketBase

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


def get_pb():
    # Always return a fresh instance to avoid cross-request auth leakage
    return PocketBase(PB_URL)
