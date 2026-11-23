"""
SupportPilot AI — Database Seed Script
Creates demo organization, users, and sample tickets for development.

Usage: python -m app.db.seed
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority, TicketChannel, MessageAuthorType
from app.models.user import User, UserRole


SAMPLE_TICKETS = [
    {
        "subject": "Cannot access my account after password reset",
        "description": "I reset my password yesterday but now I'm getting 'Invalid credentials' even with the new password. I've tried multiple times. My account email is john.doe@example.com",
        "priority": TicketPriority.HIGH,
        "customer_name": "John Doe",
        "customer_email": "john.doe@example.com",
    },
    {
        "subject": "Billing charge not matching subscription plan",
        "description": "I'm on the Pro plan ($49/month) but was charged $99 this month. Please investigate and issue a refund for the difference.",
        "priority": TicketPriority.URGENT,
        "customer_name": "Sarah Johnson",
        "customer_email": "sarah.j@acme.com",
    },
    {
        "subject": "API rate limit errors during peak hours",
        "description": "We're experiencing 429 Too Many Requests errors between 9 AM - 11 AM UTC every day. Our usage is well within the documented limits of 1000 req/min.",
        "priority": TicketPriority.HIGH,
        "customer_name": "Dev Team",
        "customer_email": "dev@techcorp.com",
    },
    {
        "subject": "Feature request: dark mode support",
        "description": "Would love to have a dark mode option in the dashboard. Many of our agents work night shifts and the bright interface is tiring.",
        "priority": TicketPriority.LOW,
        "customer_name": "Mike Chen",
        "customer_email": "mike@startup.io",
    },
    {
        "subject": "Data export not working for large datasets",
        "description": "When I try to export more than 10,000 records to CSV, the download never completes. It just shows a loading spinner indefinitely.",
        "priority": TicketPriority.MEDIUM,
        "customer_name": "Emma Wilson",
        "customer_email": "emma@analytics.co",
    },
]


async def seed(db: AsyncSession) -> None:
    print("🌱 Seeding database...")

    # Create demo organization
    org = Organization(
        id=str(uuid.uuid4()),
        name="Demo Organization",
        slug="demo-org",
        plan="pro",
    )
    db.add(org)
    await db.flush()

    # Create owner user
    owner = User(
        email="admin@supportpilot.dev",
        full_name="Admin User",
        hashed_password=hash_password("Admin123!"),
        role=UserRole.OWNER,
        organization_id=org.id,
        is_verified=True,
    )
    db.add(owner)

    # Create agent user
    agent = User(
        email="agent@supportpilot.dev",
        full_name="Support Agent",
        hashed_password=hash_password("Agent123!"),
        role=UserRole.AGENT,
        organization_id=org.id,
        is_verified=True,
    )
    db.add(agent)
    await db.flush()

    # Create sample tickets
    for t_data in SAMPLE_TICKETS:
        ticket = Ticket(
            subject=t_data["subject"],
            description=t_data["description"],
            priority=t_data["priority"],
            channel=TicketChannel.PORTAL,
            customer_name=t_data["customer_name"],
            customer_email=t_data["customer_email"],
            organization_id=org.id,
            created_by_id=owner.id,
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        await db.flush()

        # Add initial customer message
        db.add(TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.CUSTOMER,
            content=t_data["description"],
        ))

    await db.commit()
    print("✅ Seed complete!")
    print("   📧 Admin:  admin@supportpilot.dev / Admin123!")
    print("   📧 Agent:  agent@supportpilot.dev / Agent123!")
    print(f"   🏢 Org:    Demo Organization ({org.slug})")
    print(f"   🎫 Tickets: {len(SAMPLE_TICKETS)} sample tickets created")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
