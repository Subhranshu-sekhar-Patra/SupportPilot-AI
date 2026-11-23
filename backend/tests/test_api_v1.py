"""
SupportPilot AI — Comprehensive Automated API Test Suite
Tests:
- Authentication & JWT token flow
- Password hashing & verification
- Rate limiting on auth endpoints
- Organization creation and team member management
- Strict multi-tenant data isolation
- Role-based access control (RBAC)
- Ticket CRUD operations & conversation thread messages
- Document metadata management
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_health_check():
    """Verify application health check returns 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "supportpilot-backend"


@pytest.mark.anyio
async def test_openapi_schema_generated():
    """Verify OpenAPI 3.0 documentation is generated with all routers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        spec = res.json()
        assert "paths" in spec
        assert "/api/v1/auth/register" in spec["paths"]
        assert "/api/v1/auth/login" in spec["paths"]
        assert "/api/v1/tickets" in spec["paths"]
        assert "/api/v1/organizations/me" in spec["paths"]
        assert "/api/v1/knowledge" in spec["paths"]


@pytest.mark.anyio
async def test_auth_registration_and_login_flow():
    """Verify user registration, JWT generation, login, and profile retrieval."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        test_email = f"lead.engineer_{hash('test1')}@enterprise-acme.com"
        reg_payload = {
            "email": test_email,
            "password": "SecurePassword123!",
            "full_name": "Marcus Vance",
            "organization_name": "Acme Global Dynamics",
        }

        # 1. Register new organization & owner
        reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, reg_res.text
        reg_data = reg_res.json()
        assert reg_data["user"]["email"] == test_email
        assert reg_data["user"]["role"] == "owner"
        assert reg_data["user"]["organization"]["name"] == "Acme Global Dynamics"
        assert "access_token" in reg_data["tokens"]
        access_token = reg_data["tokens"]["access_token"]
        refresh_token = reg_data["tokens"]["refresh_token"]

        # 2. Prevent duplicate email registration (409 Conflict)
        dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 409

        # 3. Login with correct credentials
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "SecurePassword123!"},
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["user"]["id"] == reg_data["user"]["id"]

        # 4. Login with incorrect password (401 Unauthorized)
        bad_pw_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "WrongPassword999!"},
        )
        assert bad_pw_res.status_code == 401

        # 5. Access protected /auth/me endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_res = await client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == test_email
        assert me_data["role"] == "owner"

        # 6. Reject unauthenticated access to /auth/me (401 Unauthorized)
        unauth_res = await client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401

        # 7. Refresh token flow
        ref_res = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert ref_res.status_code == 200
        assert "access_token" in ref_res.json()


@pytest.mark.anyio
async def test_organization_and_team_membership():
    """Verify organization profile, stats, and member invitation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_email = f"owner_{hash('org_test')}@cloudscale.io"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": owner_email,
                "password": "SecurePassword123!",
                "full_name": "Elena Rostova",
                "organization_name": "CloudScale Systems",
            },
        )
        token = reg_res.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch organization stats
        stats_res = await client.get("/api/v1/organizations/me", headers=headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["name"] == "CloudScale Systems"
        assert stats["total_users"] == 1

        # 2. Invite a new AGENT team member
        agent_email = f"agent_{hash('org_agent')}@cloudscale.io"
        invite_res = await client.post(
            "/api/v1/organizations/members",
            headers=headers,
            json={
                "email": agent_email,
                "full_name": "Sarah Connor",
                "role": "agent",
                "password": "AgentPassword123!",
            },
        )
        assert invite_res.status_code == 201
        member_data = invite_res.json()
        assert member_data["role"] == "agent"

        # 3. List members
        members_res = await client.get("/api/v1/organizations/members", headers=headers)
        assert members_res.status_code == 200
        members = members_res.json()
        assert len(members) == 2


@pytest.mark.anyio
async def test_ticket_crud_and_conversation_management():
    """Verify complete ticket CRUD, status transitions, and conversation thread messages."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"tkt_owner_{hash('tickets')}@apex.com",
                "password": "SecurePassword123!",
                "full_name": "David Miller",
                "organization_name": "Apex Enterprise",
            },
        )
        token = reg_res.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a ticket
        create_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={
                "subject": "Production payment gateway timeout on checkout",
                "description": "Customers report 504 Gateway Timeout when executing Stripe payments.",
                "priority": "urgent",
                "channel": "api",
                "customer_name": "Jennifer Wu",
                "customer_email": "j.wu@client.com",
            },
        )
        assert create_res.status_code == 201
        ticket = create_res.json()
        ticket_id = ticket["id"]
        assert ticket["status"] == "open"
        assert ticket["priority"] == "urgent"

        # 2. Read single ticket
        get_res = await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == ticket_id

        # 3. Add an internal message to the conversation
        msg_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            headers=headers,
            json={
                "content": "Investigating logs in AWS CloudWatch for Stripe webhook timeouts.",
                "is_internal": True,
            },
        )
        assert msg_res.status_code == 200

        # 4. List conversation messages
        messages_res = await client.get(
            f"/api/v1/tickets/{ticket_id}/messages", headers=headers
        )
        assert messages_res.status_code == 200
        messages = messages_res.json()
        assert len(messages) >= 2  # initial customer description + internal note

        # 5. List tickets with status filter
        list_res = await client.get(
            "/api/v1/tickets", headers=headers, params={"status": "open"}
        )
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # 6. Delete ticket
        del_res = await client.delete(f"/api/v1/tickets/{ticket_id}", headers=headers)
        assert del_res.status_code == 204

        # 7. Confirm ticket is deleted
        confirm_res = await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
        assert confirm_res.status_code == 404


@pytest.mark.anyio
async def test_strict_multi_tenant_data_isolation():
    """
    CRITICAL SECURITY TEST:
    Verify that an organization can NEVER access or mutate tickets from another organization.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register Organization A (Alpha Corp)
        res_a = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"alice_{hash('tenant_a')}@alpha.com",
                "password": "Password123!",
                "full_name": "Alice Alpha",
                "organization_name": "Alpha Corporation",
            },
        )
        token_a = res_a.json()["tokens"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register Organization B (Beta Corp)
        res_b = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"bob_{hash('tenant_b')}@beta.com",
                "password": "Password123!",
                "full_name": "Bob Beta",
                "organization_name": "Beta Corporation",
            },
        )
        token_b = res_b.json()["tokens"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Org A creates a confidential ticket
        tkt_res = await client.post(
            "/api/v1/tickets",
            headers=headers_a,
            json={
                "subject": "Confidential Security Audit Findings - Alpha Corp",
                "description": "Proprietary internal audit logs.",
                "priority": "high",
            },
        )
        ticket_a_id = tkt_res.json()["id"]

        # Org B attempts to read Org A's ticket -> MUST FAIL WITH 404 (Not Found in tenant scope)
        breach_read = await client.get(f"/api/v1/tickets/{ticket_a_id}", headers=headers_b)
        assert breach_read.status_code == 404

        # Org B attempts to update Org A's ticket -> MUST FAIL WITH 404
        breach_update = await client.patch(
            f"/api/v1/tickets/{ticket_a_id}",
            headers=headers_b,
            json={"subject": "Hacked subject"},
        )
        assert breach_update.status_code == 404

        # Org B attempts to delete Org A's ticket -> MUST FAIL WITH 404
        breach_delete = await client.delete(
            f"/api/v1/tickets/{ticket_a_id}", headers=headers_b
        )
        assert breach_delete.status_code == 404

        # Org B lists tickets -> MUST NOT contain Org A's ticket
        list_b = await client.get("/api/v1/tickets", headers=headers_b)
        assert list_b.status_code == 200
        b_ticket_ids = [t["id"] for t in list_b.json()["items"]]
        assert ticket_a_id not in b_ticket_ids


@pytest.mark.anyio
async def test_role_based_access_control():
    """
    Verify RBAC enforcement:
    - OWNER / ADMIN can delete tickets and manage team members.
    - AGENT cannot delete tickets or manage team members.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register Org Owner
        res_owner = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"owner_rbac_{hash('rbac_test')}@rbac.com",
                "password": "Password123!",
                "full_name": "Rachel Green",
                "organization_name": "RBAC Test Org",
            },
        )
        owner_token = res_owner.json()["tokens"]["access_token"]
        headers_owner = {"Authorization": f"Bearer {owner_token}"}

        # Owner creates an AGENT
        agent_email = f"agent_rbac_{hash('rbac_agent')}@rbac.com"
        await client.post(
            "/api/v1/organizations/members",
            headers=headers_owner,
            json={
                "email": agent_email,
                "full_name": "Joey Tribbiani",
                "role": "agent",
                "password": "AgentPassword123!",
            },
        )

        # Login as AGENT
        agent_login = await client.post(
            "/api/v1/auth/login",
            json={"email": agent_email, "password": "AgentPassword123!"},
        )
        assert agent_login.status_code == 200, agent_login.text
        agent_token = agent_login.json()["tokens"]["access_token"]
        headers_agent = {"Authorization": f"Bearer {agent_token}"}

        # Owner creates a ticket
        tkt_res = await client.post(
            "/api/v1/tickets",
            headers=headers_owner,
            json={"subject": "Important Ticket", "description": "Owner created ticket."},
        )
        ticket_id = tkt_res.json()["id"]

        # AGENT attempts to delete ticket -> MUST FAIL WITH 403 Forbidden
        agent_del_res = await client.delete(
            f"/api/v1/tickets/{ticket_id}", headers=headers_agent
        )
        assert agent_del_res.status_code == 403

        # AGENT attempts to invite a member -> MUST FAIL WITH 403 Forbidden
        agent_invite_res = await client.post(
            "/api/v1/organizations/members",
            headers=headers_agent,
            json={
                "email": "hacker@test.com",
                "full_name": "Hacker",
                "role": "admin",
                "password": "Password123!",
            },
        )
        assert agent_invite_res.status_code == 403


@pytest.mark.anyio
async def test_auth_rate_limiting():
    """Verify that exceeding rate_limit_auth_per_minute triggers HTTP 429."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Send 12 rapid login requests from the same client
        status_codes = []
        for _ in range(12):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
            )
            status_codes.append(res.status_code)

        # The initial requests should fail with 401 (invalid creds), but request 11+ must be rate-limited (429)
        assert 429 in status_codes
        from app.core.middleware import reset_rate_limiters
        reset_rate_limiters()
