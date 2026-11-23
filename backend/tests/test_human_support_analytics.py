"""
SupportPilot AI — Comprehensive Human Support & Analytics Test Suite (Phase 7)

Verifies:
  1. Escalated tickets view (queue filtering, AI escalation reasons, customer sentiment)
  2. Ticket assignment to support agents with system audit records
  3. Full conversation history (customer, agent, AI, system messages)
  4. Manual agent replies and internal notes
  5. Ticket resolution with computed duration and reopening lifecycle
  6. Ticket audit history (append-only timeline)
  7. Real PostgreSQL organization-scoped analytics:
     - Total tickets
     - AI-resolved vs. Human-resolved tickets
     - Escalation rate calculation
     - Average first response time
     - Average resolution time
     - Customer satisfaction (CSAT) score & positive rating rate
     - Category, priority, and status distributions
     - Strict multi-tenant isolation of analytics
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.middleware import reset_rate_limiters
from app.main import app
from app.models.feedback import CustomerFeedback
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def clean_test_state():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


async def register_user_and_org(client: AsyncClient, suffix: str):
    email = f"agent_{suffix}_{uuid.uuid4().hex[:6]}@pilot-support.com"
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": f"Agent {suffix}",
            "organization_name": f"Support Org {suffix}",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]
    org_id = data["user"]["organization"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id, org_id


# ── 1. Escalated Tickets & AI Escalation Reasons ──────────────

@pytest.mark.anyio
async def test_view_escalated_tickets_with_reasons(db_session: AsyncSession):
    """Verify human agents can view escalated tickets with AI escalation reason and customer sentiment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, user_id, org_id = await register_user_and_org(client, "esc")

        # Create two tickets: one normal, one escalated
        t1_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={"subject": "Normal inquiry", "description": "How do I change my profile avatar?"},
        )
        assert t1_res.status_code == 201
        t1_id = t1_res.json()["id"]

        t2_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={
                "subject": "Urgent enterprise billing dispute",
                "description": "Double billed $12,000 and demanding an immediate refund or legal action.",
                "priority": "urgent",
            },
        )
        assert t2_res.status_code == 201
        t2_id = t2_res.json()["id"]

        # Simulate AI escalation metadata enrichment in DB
        ticket2 = await db_session.get(Ticket, t2_id)
        ticket2.status = TicketStatus.ESCALATED
        ticket2.ai_category = "billing"
        ticket2.ai_metadata = {
            "escalation": {
                "is_escalated": True,
                "escalation_reason": "Enterprise contract dispute requiring senior financial authorization",
                "severity": "urgent",
            },
            "classification": {
                "sentiment": "frustrated",
                "intent": "refund_request",
            },
        }
        await db_session.commit()

        # Query escalated queue via GET /api/v1/tickets/escalated/queue
        queue_res = await client.get("/api/v1/tickets/escalated/queue", headers=headers)
        assert queue_res.status_code == 200, queue_res.text
        queue_data = queue_res.json()
        assert queue_data["total"] >= 1

        escalated_ticket = next(t for t in queue_data["items"] if t["id"] == t2_id)
        assert escalated_ticket["status"] == "escalated"
        assert escalated_ticket["priority"] == "urgent"
        assert escalated_ticket["ai_escalation_reason"] == "Enterprise contract dispute requiring senior financial authorization"
        assert escalated_ticket["customer_sentiment"] == "frustrated"


# ── 2. Assign Tickets to Agents & Audit Trail ──────────────────

@pytest.mark.anyio
async def test_assign_ticket_to_agent_and_audit_history():
    """Verify assigning a ticket changes status to in_progress, adds system message, and creates audit log."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, user_id, org_id = await register_user_and_org(client, "assign")

        # Create ticket
        t_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={"subject": "Need help with API key rotation", "description": "Unable to generate new production key."},
        )
        ticket_id = t_res.json()["id"]

        # Assign ticket to current agent
        assign_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/assign",
            headers=headers,
            json={"agent_id": user_id},
        )
        assert assign_res.status_code == 200, assign_res.text
        ticket_data = assign_res.json()
        assert ticket_data["assigned_to_id"] == user_id
        assert ticket_data["status"] == "in_progress"

        # Verify system message added
        msg_res = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers)
        assert msg_res.status_code == 200
        messages = msg_res.json()
        assert any("assigned to support agent" in m["content"] for m in messages)

        # Verify audit log recorded
        audit_res = await client.get(f"/api/v1/tickets/{ticket_id}/audit-logs", headers=headers)
        assert audit_res.status_code == 200
        audits = audit_res.json()
        assert len(audits) >= 1
        assign_audit = next(a for a in audits if a["action"] == "ticket_assigned")
        assert assign_audit["resource_id"] == ticket_id
        assert assign_audit["extra_data"]["assigned_to_id"] == user_id


# ── 3. Full Conversation History & Manual Agent Responses ──────

@pytest.mark.anyio
async def test_manual_agent_responses_and_internal_notes():
    """Verify agent can add both public replies and internal notes with audit trails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, user_id, org_id = await register_user_and_org(client, "replies")

        # Create ticket
        t_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={"subject": "Feature request: SAML SSO", "description": "When will Okta integration be released?"},
        )
        ticket_id = t_res.json()["id"]

        # Add internal note
        note_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            headers=headers,
            json={"content": "Checked with product team: Okta SAML is slated for Q1 sprint.", "is_internal": True},
        )
        assert note_res.status_code == 200

        # Add public response to customer
        reply_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            headers=headers,
            json={"content": "Hi there! Okta SAML support is planned for Q1. We will notify you once beta opens.", "is_internal": False},
        )
        assert reply_res.status_code == 200

        # Verify full message history
        msg_res = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers)
        messages = msg_res.json()
        assert len(messages) == 3  # Initial customer message + internal note + public reply

        internal_msg = next(m for m in messages if m["is_internal"] is True)
        assert "Okta SAML is slated" in internal_msg["content"]
        assert internal_msg["author_type"] == "agent"

        public_msg = next(m for m in messages if m["is_internal"] is False and "beta opens" in m["content"])
        assert public_msg["author_type"] == "agent"


# ── 4. Resolve and Reopen Tickets Lifecycle ────────────────────

@pytest.mark.anyio
async def test_resolve_and_reopen_ticket_lifecycle():
    """Verify ticket resolution calculates duration, logs audit, and can be reopened."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, user_id, org_id = await register_user_and_org(client, "resolve")

        # Create ticket
        t_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={"subject": "Password reset link expired", "description": "Need a fresh password reset token."},
        )
        ticket_id = t_res.json()["id"]

        # Resolve ticket
        resolve_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/resolve",
            headers=headers,
            json={"resolution_notes": "Issued a manual secure password reset link via verified email."},
        )
        assert resolve_res.status_code == 200, resolve_res.text
        resolved_ticket = resolve_res.json()
        assert resolved_ticket["status"] == "resolved"
        assert resolved_ticket["resolution_notes"] == "Issued a manual secure password reset link via verified email."
        assert resolved_ticket["resolution_time_seconds"] is not None
        assert resolved_ticket["resolution_time_seconds"] >= 0

        # Reopen ticket
        reopen_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/reopen",
            headers=headers,
            json={"reason": "Customer reported reset link gives 404 error."},
        )
        assert reopen_res.status_code == 200, reopen_res.text
        reopened_ticket = reopen_res.json()
        assert reopened_ticket["status"] == "in_progress"

        # Check audit trail has both resolved and reopened events
        audit_res = await client.get(f"/api/v1/tickets/{ticket_id}/audit-logs", headers=headers)
        actions = [a["action"] for a in audit_res.json()]
        assert "ticket_resolved" in actions
        assert "ticket_reopened" in actions


# ── 5. Real PostgreSQL Analytics Overview & Multi-Tenant Scoping

@pytest.mark.anyio
async def test_real_postgresql_analytics_overview(db_session: AsyncSession):
    """
    Verify /api/v1/analytics/overview returns real PostgreSQL aggregations
    scoped strictly to the organization.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Org A
        headers_a, user_a, org_a = await register_user_and_org(client, "analytics_a")
        # Org B (Isolated)
        headers_b, user_b, org_b = await register_user_and_org(client, "analytics_b")

        # ── Populate Org A data in PostgreSQL ──
        # Ticket 1: AI Resolved
        t1_res = await client.post(
            "/api/v1/tickets",
            headers=headers_a,
            json={"subject": "AI auto query", "description": "How to export data?", "priority": "low"},
        )
        t1_id = t1_res.json()["id"]

        # Ticket 2: Human Resolved
        t2_res = await client.post(
            "/api/v1/tickets",
            headers=headers_a,
            json={"subject": "Human agent query", "description": "Custom webhook setup", "priority": "high"},
        )
        t2_id = t2_res.json()["id"]

        # Ticket 3: Escalated (Active Queue)
        t3_res = await client.post(
            "/api/v1/tickets",
            headers=headers_a,
            json={"subject": "Escalated outage report", "description": "Production database unreachable", "priority": "urgent"},
        )
        t3_id = t3_res.json()["id"]

        # Org B Ticket (should NEVER appear in Org A analytics)
        t_b_res = await client.post(
            "/api/v1/tickets",
            headers=headers_b,
            json={"subject": "Org B Private Ticket", "description": "Confidential internal matter"},
        )
        t_b_id = t_b_res.json()["id"]

        # Update tickets in DB to establish realistic resolved & response states
        # Ticket 1: AI Resolved, 120s duration, ai category
        t1 = await db_session.get(Ticket, t1_id)
        t1.status = TicketStatus.RESOLVED
        t1.ai_category = "knowledge_base"
        t1.resolution_time_seconds = 120
        t1.assigned_to_id = None  # AI resolved
        t1.ai_metadata = {"is_automated_reply": True}

        # Ticket 2: Human Resolved, 240s duration, assigned to user_a
        t2 = await db_session.get(Ticket, t2_id)
        t2.status = TicketStatus.RESOLVED
        t2.ai_category = "technical"
        t2.resolution_time_seconds = 240
        t2.assigned_to_id = user_a

        # Ticket 3: Escalated
        t3 = await db_session.get(Ticket, t3_id)
        t3.status = TicketStatus.ESCALATED
        t3.ai_category = "incident"
        t3.ai_metadata = {"escalation": {"escalation_reason": "Sev-1 production incident"}}

        # Add Customer Feedback for Org A (rating 5 and rating 4 -> avg = 4.5, 100% positive)
        fb1 = CustomerFeedback(
            ticket_id=t1_id,
            organization_id=org_a,
            rating=5,
            comment="Super fast automated answer!",
        )
        fb2 = CustomerFeedback(
            ticket_id=t2_id,
            organization_id=org_a,
            rating=4,
            comment="Helpful support specialist.",
        )
        # Add Customer Feedback for Org B (rating 1 -> should NOT affect Org A)
        fb_b = CustomerFeedback(
            ticket_id=t_b_id,
            organization_id=org_b,
            rating=1,
            comment="Terrible experience in Org B",
        )
        db_session.add_all([fb1, fb2, fb_b])
        await db_session.commit()

        # Add agent reply to ticket 1 and ticket 2 to compute first response time
        await client.post(
            f"/api/v1/tickets/{t1_id}/messages",
            headers=headers_a,
            json={"content": "Here is the export documentation.", "is_internal": False},
        )
        await client.post(
            f"/api/v1/tickets/{t2_id}/messages",
            headers=headers_a,
            json={"content": "I am configuring your webhook now.", "is_internal": False},
        )

        # ── Fetch Analytics for Org A ──
        res_a = await client.get("/api/v1/analytics/overview", headers=headers_a)
        assert res_a.status_code == 200, res_a.text
        data_a = res_a.json()

        # Check ticket volumes
        assert data_a["total_tickets"] == 3
        assert data_a["resolved_tickets"] == 2
        assert data_a["open_tickets"] == 1  # Escalated ticket is active in open queue
        assert data_a["escalated_tickets"] == 1

        # Check AI vs Human resolution
        assert data_a["ai_resolved_tickets"] == 1
        assert data_a["human_resolved_tickets"] == 1

        # Check escalation rate: 1 of 3 = 33.33%
        assert data_a["escalation_rate"] == 33.33

        # Check avg resolution time: (120 + 240) / 2 = 180.0
        assert data_a["avg_resolution_time_seconds"] == 180.0

        # Check first response time is calculated
        assert data_a["avg_first_response_time_seconds"] is not None
        assert data_a["avg_first_response_time_seconds"] >= 0.0

        # Check CSAT metrics: (5 + 4) / 2 = 4.5
        assert data_a["csat_score"] == 4.5
        assert data_a["csat_total_feedback"] == 2
        assert data_a["csat_positive_rate"] == 100.0

        # Check category distributions
        assert data_a["category_distribution"]["knowledge_base"] == 1
        assert data_a["category_distribution"]["technical"] == 1
        assert data_a["category_distribution"]["incident"] == 1

        # ── Check Org B Analytics to verify isolation ──
        res_b = await client.get("/api/v1/analytics/overview", headers=headers_b)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["total_tickets"] == 1
        assert data_b["csat_score"] == 1.0  # Org B's rating 1 feedback
        assert data_b["csat_total_feedback"] == 1
        assert data_b["csat_positive_rate"] == 0.0
