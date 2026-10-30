import json
from concurrent.futures import ThreadPoolExecutor


def hx_toast(message: str, type: str = "info") -> dict:
    event_data = {"show-toast": {"message": message, "type": type}}
    # 🟢 FIXED: Changed from 'HX-Trigger' to 'HX-Trigger-After-Swap'
    # This guarantees HTMX waits for the new page to load before popping the toast!
    return {"HX-Trigger-After-Swap": json.dumps(event_data)}


def pmap(fn, items, workers: int = 8):
    """Bounded parallel map, results in input order.

    PocketBase calls are independent I/O; running them serially multiplies
    latency by round-trips (one remote RTT each). Order and exceptions are
    preserved, concurrency stays bounded so PB is never hammered.
    """
    items = list(items)
    if len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(fn, items))
