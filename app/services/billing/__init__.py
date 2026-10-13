"""Billing: free seat allowance, PayRam credit packs, server-side enforcement.

Monetized resource: **active trainee seats per gym (tenant)**.

- Every tenant gets ``BILLING_FREE_SEATS`` active trainees free, forever.
- Seat packs (``billing_products``) are one-time PayRam purchases that add
  permanent seat capacity, recorded append-only in ``credit_transactions``.
- Enforcement happens in the backend on trainee creation/reactivation.

PocketBase billing collections are superuser-only; all access goes through the
dedicated server-side admin client (``app.pb.get_admin_pb``). The browser never
reads or writes billing records directly.
"""
