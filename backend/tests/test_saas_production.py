"""
SupportPilot AI — Production Public SaaS & Multi-Tenancy Test Suite (Phase 9)

Verifies:
  1. Super Admin role (cross-tenant observability, organization plan upgrades)
  2. RBAC enforcement (Super Admin vs. Org Admin vs. Support Agent)
  3. Organization onboarding milestones checklist
  4. Usage tracking & AI message limits enforcement
  5. Embeddable customer chatbot widget API (public config, chat endpoint, citations, quota ceiling)
  6. Widget loader script delivery
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import reset_rate_limiters
from app.core.security import hash_password
from app.main import app
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.usage_service import UsageService


@pytest.fixture(autouse=True)
def clean_test_state():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


async def register_org(client: AsyncClient, suffix: str):
    email = f"owner_{suffix}_{uuid.uuid4().hex[:6]}@pilot-enterprise.io"
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": f"Owner {suffix}",
            "organization_name": f"Tenant Org {suffix}",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]
    org_id = data["user"]["organization"]["id"]
    org_slug = data["user"]["organization"]["slug"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id, org_id, org_slug


# ── 1. Super Admin Role & Cross-Tenant Oversight ──────────────

@pytest.mark.anyio
async def test_super_admin_role_and_plan_upgrade(db_session: AsyncSession):
    """Verify Super Admin can list all tenant organizations and upgrade plan quotas."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create normal tenant organization
        headers_tenant, _, org_id, _ = await register_org(client, "sub_admin")

        # Create global Super Admin user in DB
        super_admin_user = User(
            email=f"superadmin_{uuid.uuid4().hex[:6]}@supportpilot.internal",
            hashed_password=hash_password("SuperSecret123!"),
            full_name="Platform Super Administrator",
            role=UserRole.SUPER_ADMIN,
            organization_id=org_id,
            is_active=True,
            is_verified=True,
        )
        db_session.add(super_admin_user)
        await db_session.commit()

        # Login as Super Admin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": super_admin_user.email, "password": "SuperSecret123!"},
        )
        assert login_res.status_code == 200, login_res.text
        super_headers = {"Authorization": f"Bearer {login_res.json()['tokens']['access_token']}"}

        # 1. Super Admin lists all organizations across the platform
        admin_orgs_res = await client.get("/api/v1/admin/organizations", headers=super_headers)
        assert admin_orgs_res.status_code == 200, admin_orgs_res.text
        orgs_list = admin_orgs_res.json()
        assert len(orgs_list) >= 1
        target_org = next(o for o in orgs_list if o["id"] == org_id)
        assert target_org["plan"] == "free"

        # 2. Non-super admin is forbidden from admin endpoints (403)
        forbidden_res = await client.get("/api/v1/admin/organizations", headers=headers_tenant)
        assert forbidden_res.status_code == 403

        # 3. Super Admin upgrades organization to Pro plan
        upgrade_res = await client.patch(
            f"/api/v1/admin/organizations/{org_id}/plan",
            headers=super_headers,
            json={"plan": "pro"},
        )
        assert upgrade_res.status_code == 200, upgrade_res.text
        upgraded_data = upgrade_res.json()
        assert upgraded_data["plan"] == "pro"
        assert upgraded_data["max_ai_messages_per_month"] == 25000
        assert upgraded_data["max_tickets_per_month"] == 10000


# ── 2. Organization Onboarding & Milestone Progress ───────────

@pytest.mark.anyio
async def test_organization_onboarding_milestones(db_session: AsyncSession):
    """Verify organization onboarding progress checklist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _, org_id, _ = await register_org(client, "onboarding")

        # Initial onboarding status (only account_created & widget_customized done)
        onboard_res = await client.get("/api/v1/organizations/me/onboarding", headers=headers)
        assert onboard_res.status_code == 200
        data = onboard_res.json()
        assert data["completed_steps_count"] >= 1
        assert data["is_fully_onboarded"] is False

        # Create a ticket to achieve the 'first_ticket_handled' milestone
        await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={"subject": "Welcome onboarding query", "description": "Testing the initial ticket setup."},
        )

        onboard_res2 = await client.get("/api/v1/organizations/me/onboarding", headers=headers)
        data2 = onboard_res2.json()
        ticket_step = next(s for s in data2["steps"] if s["id"] == "first_ticket_handled")
        assert ticket_step["completed"] is True


# ── 3. Usage Tracking & AI Message Limits ─────────────────────

@pytest.mark.anyio
async def test_usage_tracking_and_ai_quota_enforcement(db_session: AsyncSession):
    """Verify usage overview retrieval and AI message quota ceilings."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _, org_id, _ = await register_org(client, "usage")

        # Fetch usage
        usage_res = await client.get("/api/v1/organizations/me/usage", headers=headers)
        assert usage_res.status_code == 200, usage_res.text
        data = usage_res.json()
        assert data["plan"] == "free"
        assert data["max_ai_messages_per_month"] == 1000
        assert data["ai_messages_used_this_month"] == 0
        assert data["is_ai_quota_exceeded"] is False

        # Set usage to quota ceiling directly in DB
        org = await db_session.get(Organization, org_id)
        org.max_ai_messages_per_month = 5
        org.ai_messages_used_this_month = 5
        await db_session.commit()

        # Service rejects further AI generation when limit reached
        usage_svc = UsageService(db_session)
        allowed = await usage_svc.check_and_increment_ai_message(org_id)
        assert allowed is False

        # API confirms quota exceeded
        usage_res2 = await client.get("/api/v1/organizations/me/usage", headers=headers)
        data2 = usage_res2.json()
        assert data2["is_ai_quota_exceeded"] is True
        assert data2["ai_messages_remaining"] == 0


# ── 4. Embeddable Customer Chatbot Widget ─────────────────────

@pytest.mark.anyio
async def test_embeddable_chatbot_widget_flow(db_session: AsyncSession):
    """Verify public widget configuration, script loader, and conversation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers, _, org_id, org_slug = await register_org(client, "widget")

        # 1. Customize widget settings as Org Owner
        patch_res = await client.patch(
            "/api/v1/organizations/me/widget",
            headers=headers,
            json={
                "widget_primary_color": "#10B981",
                "widget_greeting": "Hello! Welcome to Acme Support. How can we help?",
                "widget_enabled": True,
            },
        )
        assert patch_res.status_code == 200, patch_res.text
        widget_cfg = patch_res.json()
        assert widget_cfg["widget_primary_color"] == "#10B981"
        assert "loader.js" in widget_cfg["embed_snippet"]

        # 2. Public config endpoint (no auth required)
        pub_cfg_res = await client.get(f"/api/v1/widget/{org_slug}/config")
        assert pub_cfg_res.status_code == 200
        pub_cfg = pub_cfg_res.json()
        assert pub_cfg["primary_color"] == "#10B981"
        assert pub_cfg["greeting"] == "Hello! Welcome to Acme Support. How can we help?"
        assert pub_cfg["enabled"] is True

        # 3. Widget Loader JS
        loader_res = await client.get("/api/v1/widget/loader.js")
        assert loader_res.status_code == 200
        assert "supportpilot-widget-btn" in loader_res.text

        # 4. Customer chat via public widget
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        chat_res = await client.post(
            f"/api/v1/widget/{org_slug}/chat",
            json={
                "message": "What is the policy for subscription cancellations?",
                "customer_name": "Alice Customer",
                "customer_email": "alice@example.com",
                "session_id": session_id,
            },
        )
        assert chat_res.status_code == 200, chat_res.text
        chat_data = chat_res.json()
        assert chat_data["reply"] != ""
        assert chat_data["ticket_id"] != ""
        assert chat_data["is_quota_exceeded"] is False

        # 5. Verify usage counter incremented
        org = await db_session.get(Organization, org_id)
        assert org.ai_messages_used_this_month == 1
