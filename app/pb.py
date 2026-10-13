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


# ---------------------------------------------------------------------------
# Server-side admin client (superuser) — used ONLY by trusted billing code.
# ---------------------------------------------------------------------------
# Billing collections have no public API rules; only this privileged client may
# read/write them. Credentials stay in the environment and never reach routes
# or templates directly.
def _auth_admin(pb: PocketBase) -> None:
    email = os.getenv("PB_ADMIN_EMAIL", "").strip()
    password = os.getenv("PB_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        raise RuntimeError(
            "PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD are required for billing operations"
        )
    try:
        # PocketBase >= 0.23 uses the _superusers auth collection.
        pb.collection("_superusers").auth_with_password(email, password)
        return
    except Exception as superuser_exc:
        # PocketBase <= 0.22 exposes admins under pb.admins.
        try:
            pb.admins.auth_with_password(email, password)
            return
        except Exception:
            raise superuser_exc


def get_admin_pb() -> PocketBase:
    """Return a PocketBase client authenticated as a superuser.

    Authenticated fresh per call: simpler and immune to stale-token failures
    after a PocketBase restart. Billing traffic is low-volume (owner pages,
    checkout, webhooks), so the extra auth roundtrip is acceptable.
    """
    pb = PocketBase(PB_URL)
    _auth_admin(pb)
    return pb
