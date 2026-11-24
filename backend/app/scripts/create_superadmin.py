"""
SupportPilot AI — Create / Promote Super Admin CLI Script
Creates a new Super Admin account or elevates an existing user account.

Usage inside Docker container or virtualenv:
    python -m app.scripts.create_superadmin --email admin@example.com --password YourSecret123! --name "System Superadmin"
"""

import argparse
import asyncio
import os
import sys
import uuid
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.core.security import hash_password


async def create_or_elevate_superadmin(email: str, password: str | None = None, name: str = "Platform Super Admin") -> None:
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if user:
            print(f"[*] User '{email}' found (current role: {user.role}). Elevating to SUPER_ADMIN...")
            user.role = UserRole.SUPER_ADMIN
            if password:
                user.hashed_password = hash_password(password)
                print("[*] Password updated successfully.")
            await session.commit()
            print(f"[+] Successfully promoted '{email}' to SUPER_ADMIN!")
            return

        # If user does not exist, check or create system platform organization
        if not password:
            print("[-] Error: Password is required to create a new Super Admin account.")
            sys.exit(1)

        result = await session.execute(select(Organization).where(Organization.slug == "platform-admin"))
        org = result.scalars().first()
        if not org:
            org = Organization(
                id=str(uuid.uuid4()),
                name="Platform Administration",
                slug="platform-admin",
                plan="enterprise",
                max_ai_messages_per_month=1000000,
            )
            session.add(org)
            await session.flush()

        new_user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=name,
            hashed_password=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            organization_id=org.id,
            is_verified=True,
            is_active=True,
        )
        session.add(new_user)
        await session.commit()
        print(f"[+] Successfully created Super Admin account '{email}' (ID: {new_user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or elevate a SupportPilot AI Super Admin.")
    parser.add_argument("--email", default=os.getenv("SUPERADMIN_EMAIL"), help="Super admin email address")
    parser.add_argument("--password", default=os.getenv("SUPERADMIN_PASSWORD"), help="Super admin password")
    parser.add_argument("--name", default=os.getenv("SUPERADMIN_NAME", "Platform Super Admin"), help="Full name")

    args = parser.parse_args()

    if not args.email:
        parser.error("--email is required (or set SUPERADMIN_EMAIL environment variable)")

    asyncio.run(create_or_elevate_superadmin(email=args.email, password=args.password, name=args.name))


if __name__ == "__main__":
    main()
