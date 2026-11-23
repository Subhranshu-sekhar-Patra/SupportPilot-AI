"""
SupportPilot AI — Webhook Security & Idempotency Store
Provides HMAC-SHA256 signature verification and duplicate-event suppression.
"""

import hashlib
import hmac
import time
from typing import Set

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logger import get_logger

logger = get_logger(__name__)

# Sliding-window in-memory store for idempotency keys (event_id -> timestamp)
_processed_events: dict[str, float] = {}
_DEDUPLICATION_WINDOW_SECONDS = 900  # 15 minutes


def verify_webhook_auth(
    raw_body: bytes,
    signature: str | None = None,
    api_key: str | None = None,
) -> bool:
    """
    Authenticate incoming webhooks:
      1. Via HMAC-SHA256 header (X-N8N-Signature)
      2. Via shared secret API Key header (X-API-Key)
    """
    secret = settings.n8n_api_key or "default-n8n-secret-key"

    # 1. Check API Key header
    if api_key and (api_key == secret or api_key == settings.secret_key):
        return True

    # 2. Check HMAC-SHA256 signature
    if signature:
        expected = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected, signature):
            return True

    # In non-production testing, allow if no key is enforced
    if not settings.is_production and not signature and not api_key:
        return True

    return False


def is_duplicate_event(event_id: str | None) -> bool:
    """
    Check if an event_id was already processed within the deduplication window.
    If not seen, registers it and returns False. If seen, returns True.
    """
    if not event_id:
        return False

    now = time.time()
    cutoff = now - _DEDUPLICATION_WINDOW_SECONDS

    # Evict expired events
    expired_keys = [k for k, ts in _processed_events.items() if ts < cutoff]
    for k in expired_keys:
        _processed_events.pop(k, None)

    if event_id in _processed_events:
        logger.warning("duplicate_webhook_event_detected", event_id=event_id)
        return True

    _processed_events[event_id] = now
    return False


def reset_idempotency_store() -> None:
    """Clear idempotency cache (used for test isolation)."""
    _processed_events.clear()
