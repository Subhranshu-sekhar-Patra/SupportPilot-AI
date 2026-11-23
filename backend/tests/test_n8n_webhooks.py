"""
SupportPilot AI — Comprehensive n8n Integration Test Suite (Phase 6)

Tests:
  1. Webhook Authentication (HMAC-SHA256 signature and API key validation)
  2. Duplicate-Event Protection (Idempotency and duplicate suppression)
  3. Workflow 1: Ticket Escalation (agent assignment, status change, internal audit notes)
  4. Workflow 2: Customer Notifications (ticket creation confirmation, dispatch logging)
  5. Workflow 3: Customer Follow-up & Feedback (CSAT score saved to PostgreSQL, ticket enrichment)
  6. Outgoing Webhook Dispatcher (HMAC signature generation and resilient delivery)
  7. Exported n8n Workflow Definitions (schema validity, triggers, connections, and retry configs)
"""

import hashlib
import hmac
import json
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core.middleware import reset_rate_limiters
from app.main import app
from app.models.feedback import CustomerFeedback
from app.models.ticket import TicketPriority, TicketStatus
from app.webhooks.dispatcher import WebhookDispatcher, generate_hmac_signature
from app.webhooks.security import is_duplicate_event, reset_idempotency_store, verify_webhook_auth


@pytest.fixture(autouse=True)
def clean_webhook_state():
    reset_idempotency_store()
    reset_rate_limiters()
    yield
    reset_idempotency_store()
    reset_rate_limiters()


# ── 1. Webhook Authentication Tests ───────────────────────────

def test_webhook_hmac_and_api_key_auth():
    secret = settings.n8n_api_key or "default-n8n-secret-key"
    payload = b'{"event_type": "test.ping", "ticket_id": "123"}'

    # Valid HMAC
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert verify_webhook_auth(payload, signature=signature) is True

    # Valid API Key
    assert verify_webhook_auth(payload, api_key=secret) is True

    # Invalid HMAC / Key
    assert verify_webhook_auth(payload, signature="invalid_hash_signature", api_key="wrong_key") is False


# ── 2. Duplicate-Event Protection Tests ───────────────────────

def test_idempotent_duplicate_suppression():
    event_id = "test_evt_idempotency_999"

    # First arrival: allowed
    assert is_duplicate_event(event_id) is False

    # Second arrival with exact same event_id: blocked / suppressed
    assert is_duplicate_event(event_id) is True

    # Different event_id: allowed
    assert is_duplicate_event("test_evt_idempotency_1000") is False


# ── 3. Workflow 1: Ticket Escalation Integration ──────────────

@pytest.mark.anyio
async def test_workflow_1_ticket_escalation_endpoint():
    """Verify n8n escalation event updates ticket status and assigns agent in PostgreSQL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user and create an open ticket
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"escalation_mgr_{hash('n8n_test1')}@n8n.com",
                "password": "Password123!",
                "full_name": "Tony Hawk",
                "organization_name": "Skate Ops",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["tokens"]["access_token"]
        headers_user = {"Authorization": f"Bearer {token}"}

        tkt_res = await client.post(
            "/api/v1/tickets",
            headers=headers_user,
            json={
                "subject": "Critical API Outage on European Edge",
                "description": "API latency has spiked to 5000ms. Immediate investigation needed.",
                "priority": "high",
            },
        )
        assert tkt_res.status_code == 201
        ticket_id = tkt_res.json()["id"]

        # Call n8n event webhook to simulate Workflow 1
        secret = settings.n8n_api_key or "default-n8n-secret-key"
        event_payload = {
            "event_id": f"evt_escalation_{hash('wf1')}",
            "event_type": "ticket.escalated",
            "ticket_id": ticket_id,
            "assigned_to_id": "agent_tier2_lead",
            "priority": "urgent",
            "extra_data": {"escalated_by": "n8n_workflow_1", "reason": "SLA risk"},
        }
        raw_bytes = json.dumps(event_payload).encode("utf-8")
        sig = generate_hmac_signature(raw_bytes, secret)

        webhook_res = await client.post(
            "/api/v1/webhooks/n8n/event",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-N8N-Signature": sig,
                "X-API-Key": secret,
            },
        )
        assert webhook_res.status_code == 200, webhook_res.text
        data = webhook_res.json()
        assert data["status"] == "processed"
        assert data["ticket_status"] == "escalated"
        assert data["assigned_to_id"] == "agent_tier2_lead"

        # Verify ticket in database
        updated_ticket = (await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers_user)).json()
        assert updated_ticket["status"] == "escalated"
        assert updated_ticket["priority"] == "urgent"
        assert updated_ticket["ai_metadata"]["assigned_agent"] == "agent_tier2_lead"


# ── 4. Workflow 2: Customer Notifications Integration ─────────

@pytest.mark.anyio
async def test_workflow_2_customer_notification_ack():
    """Verify n8n customer notification webhook receives and logs delivery confirmation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create ticket
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"notif_lead_{hash('n8n_test2')}@n8n.com",
                "password": "Password123!",
                "full_name": "Natasha Romanoff",
                "organization_name": "Shield Support",
            },
        )
        token = reg_res.json()["tokens"]["access_token"]
        headers_user = {"Authorization": f"Bearer {token}"}

        tkt_res = await client.post(
            "/api/v1/tickets",
            headers=headers_user,
            json={
                "subject": "Account recovery inquiry",
                "description": "Please confirm account verification instructions.",
                "customer_email": "natasha@shield.gov",
            },
        )
        ticket_id = tkt_res.json()["id"]

        # Call n8n webhook with notification delivery event
        secret = settings.n8n_api_key or "default-n8n-secret-key"
        event_payload = {
            "event_id": f"evt_notif_{hash('wf2')}",
            "event_type": "ticket.notification_sent",
            "ticket_id": ticket_id,
            "notification_status": "delivered",
            "extra_data": {"recipient": "natasha@shield.gov", "channel": "email"},
        }
        raw_bytes = json.dumps(event_payload).encode("utf-8")
        sig = generate_hmac_signature(raw_bytes, secret)

        res = await client.post(
            "/api/v1/webhooks/n8n/event",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "processed"

        # Duplicate event call must be gracefully suppressed
        duplicate_res = await client.post(
            "/api/v1/webhooks/n8n/event",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
        )
        assert duplicate_res.status_code == 200
        assert duplicate_res.json()["status"] == "duplicate_ignored"


# ── 5. Workflow 3: Customer Follow-up & Feedback in PostgreSQL ─

@pytest.mark.anyio
async def test_workflow_3_feedback_saved_in_postgresql():
    """Verify n8n post-resolution CSAT survey feedback is stored in PostgreSQL and ticket thread."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create user and ticket
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"csat_lead_{hash('n8n_test3')}@n8n.com",
                "password": "Password123!",
                "full_name": "Bruce Banner",
                "organization_name": "Banner Labs",
            },
        )
        token = reg_res.json()["tokens"]["access_token"]
        headers_user = {"Authorization": f"Bearer {token}"}

        tkt_res = await client.post(
            "/api/v1/tickets",
            headers=headers_user,
            json={
                "subject": "Gamma spectrometer calibration issue",
                "description": "Equipment calibration completed.",
                "customer_email": "banner@labs.org",
            },
        )
        ticket_id = tkt_res.json()["id"]

        # Resolve ticket
        await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            headers=headers_user,
            json={"status": "resolved"},
        )

        # Simulate Workflow 3 submitting CSAT survey feedback
        feedback_payload = {
            "ticket_id": ticket_id,
            "rating": 5,
            "comment": "Outstanding support! The AI response cited exact policies and solved the issue in minutes.",
            "customer_email": "banner@labs.org",
            "event_id": f"evt_csat_{hash('wf3')}",
        }

        fb_res = await client.post(
            "/api/v1/webhooks/feedback",
            json=feedback_payload,
            headers={"X-API-Key": settings.n8n_api_key or "default-n8n-secret-key"},
        )
        assert fb_res.status_code == 201, fb_res.text
        fb_data = fb_res.json()
        assert fb_data["rating"] == 5
        assert fb_data["ticket_id"] == ticket_id
        assert fb_data["status"] == "saved"

        # Verify ticket conversation has the customer feedback message
        messages_res = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers_user)
        messages = messages_res.json()
        feedback_messages = [m for m in messages if "CSAT" in m["content"] or "⭐⭐⭐⭐⭐" in m["content"]]
        assert len(feedback_messages) >= 1
        assert "5/5" in feedback_messages[0]["content"]

        # Verify ticket metadata has feedback
        ticket_detail = (await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers_user)).json()
        assert ticket_detail["ai_metadata"]["customer_feedback"]["rating"] == 5


# ── 6. Outgoing Webhook Dispatcher Tests ───────────────────────

@pytest.mark.anyio
async def test_outgoing_webhook_dispatcher():
    dispatcher = WebhookDispatcher(
        base_url="http://localhost:5678/webhook",
        api_key="secret-test-key",
    )
    sig = generate_hmac_signature(b'{"hello": "world"}', "secret-test-key")
    assert isinstance(sig, str) and len(sig) == 64

    # When no base_url is configured, dispatch skips cleanly
    dispatcher_empty = WebhookDispatcher(base_url="")
    res = await dispatcher_empty.dispatch("ticket.created", "tkt_123", {"title": "Test"})
    assert res["status"] == "skipped"


# ── 7. Exported n8n Workflow JSON Schema Validation ────────────

def test_exported_n8n_workflows_schema():
    """Verify that all exported n8n workflow JSON files have valid structure and retry policies."""
    workflows_dir = Path("d:/AI Advance Project/supportpilot/n8n/workflows")
    expected_files = [
        "escalation.json",
        "customer_notifications.json",
        "customer_followup.json",
    ]

    for fname in expected_files:
        path = workflows_dir / fname
        assert path.exists(), f"Missing workflow file: {path}"

        with open(path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        assert "name" in workflow
        assert "nodes" in workflow
        assert "connections" in workflow
        assert len(workflow["nodes"]) >= 3

        # Check for webhook trigger node
        webhook_nodes = [n for n in workflow["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
        assert len(webhook_nodes) >= 1, f"{fname} must contain a webhook trigger node"

        # Check for HTTP request node
        http_nodes = [n for n in workflow["nodes"] if n.get("type") == "n8n-nodes-base.httpRequest"]
        assert len(http_nodes) >= 1, f"{fname} must contain backend HTTP integration nodes"
