"""
SupportPilot AI — Outgoing n8n Webhook Dispatcher
Dispatches ticket lifecycle events (created, escalated, resolved, updated)
to n8n with HMAC-SHA256 signatures, deduplication IDs, and exponential backoff retries.
"""

import hashlib
import hmac
import json
import uuid
from typing import Any
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def generate_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate hex-encoded HMAC-SHA256 signature for payload."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class WebhookDispatcher:
    """
    Sends signed events to n8n workflows with automatic retries and error isolation.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or settings.n8n_webhook_url).rstrip("/")
        self.api_key = api_key or settings.n8n_api_key or "default-n8n-secret-key"

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=False,
    )
    async def _post_with_retry(
        self,
        endpoint_url: str,
        payload_bytes: bytes,
        headers: dict[str, str],
    ) -> httpx.Response | None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(endpoint_url, content=payload_bytes, headers=headers)
            # Raise status for 5xx to trigger retry; 4xx are client errors so don't retry
            if response.status_code >= 500:
                response.raise_for_status()
            return response

    async def dispatch(
        self,
        event_type: str,
        ticket_id: str,
        payload: dict[str, Any],
        event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch a signed event to n8n.
        """
        if not self.base_url:
            logger.debug("n8n_dispatcher_skipped_no_url", event_name=event_type)
            return {"status": "skipped", "reason": "n8n_webhook_url_not_configured"}

        ev_id = event_id or str(uuid.uuid4())
        full_payload = {
            "event_id": ev_id,
            "event_type": event_type,
            "ticket_id": ticket_id,
            "data": payload,
        }

        payload_bytes = json.dumps(full_payload).encode("utf-8")
        signature = generate_hmac_signature(payload_bytes, self.api_key)

        headers = {
            "Content-Type": "application/json",
            "X-N8N-Signature": signature,
            "X-API-Key": self.api_key,
            "X-Event-ID": ev_id,
        }

        # Normalize path e.g. ticket.escalated -> ticket-escalated
        endpoint_path = event_type.replace(".", "-")
        target_url = f"{self.base_url}/{endpoint_path}"

        try:
            res = await self._post_with_retry(target_url, payload_bytes, headers)
            if res and res.status_code < 400:
                logger.info(
                    "n8n_event_dispatched_success",
                    event_type=event_type,
                    ticket_id=ticket_id,
                    status_code=res.status_code,
                )
                return {"status": "dispatched", "event_id": ev_id, "status_code": res.status_code}
            else:
                code = res.status_code if res else "no_response"
                logger.warning(
                    "n8n_event_dispatch_warning",
                    event_type=event_type,
                    status_code=code,
                )
                return {"status": "failed", "event_id": ev_id, "status_code": code}

        except Exception as e:
            logger.error("n8n_event_dispatch_error", event_type=event_type, error=str(e))
            return {"status": "error", "event_id": ev_id, "error": str(e)}


# Singleton helper
dispatcher = WebhookDispatcher()
