"""Billing configuration — environment driven, validated, cached.

Secrets live here (server-side only). Purchasable products live in the
``billing_products`` PocketBase collection, so ordinary price/pack changes do
not require code changes.

Nothing in this module is ever rendered into a template or sent to the browser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUTHY


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # fail fast, never guess a limit
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number, got {raw!r}") from exc


@dataclass(frozen=True)
class BillingConfig:
    enabled: bool
    free_seats: int
    currency: str
    public_app_url: str
    payram_base_url: str
    payram_api_key: str
    payram_webhook_secret: str
    payram_timeout: float
    checkout_ttl_seconds: int
    max_open_invoices: int

    @property
    def payram_configured(self) -> bool:
        return bool(self.payram_base_url and self.payram_api_key)

    @property
    def webhook_ready(self) -> bool:
        return bool(self.payram_webhook_secret)


def _load() -> BillingConfig:
    enabled = _env_bool("BILLING_ENABLED", False)
    base_url = os.getenv("PAYRAM_BASE_URL", "").strip().rstrip("/")
    api_key = os.getenv("PAYRAM_API_KEY", "").strip()
    # PayRam signs webhooks with the project API key; allow an explicit override.
    webhook_secret = os.getenv("PAYRAM_WEBHOOK_SECRET", "").strip() or api_key

    config = BillingConfig(
        enabled=enabled,
        free_seats=max(0, _env_int("BILLING_FREE_SEATS", 5)),
        currency=os.getenv("BILLING_CURRENCY", "USD").strip().upper() or "USD",
        public_app_url=os.getenv("PUBLIC_APP_URL", "").strip().rstrip("/"),
        payram_base_url=base_url,
        payram_api_key=api_key,
        payram_webhook_secret=webhook_secret,
        payram_timeout=_env_float("PAYRAM_TIMEOUT", 15.0),
        checkout_ttl_seconds=max(300, _env_int("BILLING_CHECKOUT_TTL_SECONDS", 86400)),
        max_open_invoices=max(1, _env_int("BILLING_MAX_OPEN_INVOICES", 5)),
    )

    if config.enabled and not config.payram_configured:
        raise RuntimeError(
            "BILLING_ENABLED is set but PayRam is not configured. "
            "Set PAYRAM_BASE_URL and PAYRAM_API_KEY (and PAYRAM_WEBHOOK_SECRET "
            "if it differs from the API key)."
        )
    return config


@lru_cache(maxsize=1)
def get_config() -> BillingConfig:
    """Process-wide billing config (immutable; read env once)."""
    return _load()


def reset_config_cache() -> None:
    """Test helper: drop the cached config so env changes take effect."""
    get_config.cache_clear()
