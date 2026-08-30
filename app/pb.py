import os
from pocketbase import PocketBase

# Fetches PB_URL from the environment, defaults to local if not set
# Use https in production; default dev remains http but encourage env override
_raw_pb_url = os.getenv("PB_URL", "http://db.dev.gyme.cloud")
# If ENV=production and URL still http, warn and prefer https
if os.getenv("ENV", "dev").lower() == "production" and _raw_pb_url.startswith("http://"):
    import logging as _log
    _log.getLogger(__name__).warning("PB_URL is http in production; force https if possible")
PB_URL = _raw_pb_url
pb = PocketBase(PB_URL)

def get_pb():
    # Always return a fresh instance to avoid cross-request auth leakage
    return PocketBase(PB_URL)