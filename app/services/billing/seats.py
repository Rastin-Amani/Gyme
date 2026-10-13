"""Active-trainee seat capacity and server-side enforcement.

The monetized unit is an **active trainee seat** per gym (tenant):

    capacity = BILLING_FREE_SEATS + net purchased seat credits (ledger)
    used     = active trainees in the tenant
    remaining = max(0, capacity - used)

Enforcement runs in the backend on trainee creation and on reactivation, so a
modified browser cannot exceed the allowance. Failed/never-created trainees are
simply not counted (they never became active records).

Concurrency: capacity is granted by holding a per-tenant in-process lock across
the check-and-create. This is correct for the documented single-container
deployment. A future multi-instance deployment would need a DB-level guarantee.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

from app.security import pb_escape
from app.services.billing import store
from app.services.billing.config import get_config

# ponytail: per-tenant in-process lock; single-instance deploy. Swap for a DB
# advisory lock / unique reservation row if this ever runs multi-instance.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(tenant_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(tenant_id)
        if lock is None:
            lock = threading.Lock()
            _locks[tenant_id] = lock
        return lock


@contextmanager
def tenant_seat_lock(tenant_id: str):
    """Serialize seat-consuming operations for one tenant."""
    lock = _lock_for(str(tenant_id))
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def count_active_trainees(pb, tenant_id: str) -> int:
    flt = f'tenant="{pb_escape(tenant_id)}" && status="active"'
    try:
        result = pb.collection("trainees").get_list(
            page=1, per_page=1, query_params={"filter": flt}
        )
        return getattr(result, "total_items", getattr(result, "totalItems", 0))
    except Exception:
        # Fail closed on the *used* side is impossible here; fail open on count
        # would let over-allocation slip through. Return 0 only means "no active
        # trainees seen", so we raise instead to avoid silently allowing a seat.
        raise


def seat_summary(pb, tenant_id: str) -> dict:
    config = get_config()
    purchased = store.ledger_balance(pb, tenant_id)
    capacity = config.free_seats + max(0, purchased)
    used = count_active_trainees(pb, tenant_id)
    return {
        "free_seats": config.free_seats,
        "purchased_seats": max(0, purchased),
        "capacity": capacity,
        "used": used,
        "remaining": max(0, capacity - used),
        "over_capacity": used > capacity,
    }


def has_free_seat(pb, tenant_id: str) -> tuple[bool, dict]:
    summary = seat_summary(pb, tenant_id)
    return summary["used"] < summary["capacity"], summary
