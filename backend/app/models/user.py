"""
SupportPilot AI — User Model
Supports organization-scoped roles for RBAC.
"""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    """
    Organization-level roles.
    - OWNER:  Can manage org settings, billing, and all resources
    - ADMIN:  Can manage users, agents, and all tickets
    - AGENT:  Can view and respond to assigned tickets
    - VIEWER: Read-only access to dashboards and reports
    """
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"
    VIEWER = "viewer"


class User(UUIDMixin, TimestampMixin, Base):
    """
    Application user, always scoped to exactly one organization.
    """

    __tablename__ = "users"

    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # RBAC
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.AGENT, nullable=False
    )

    # Multi-tenancy
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Relationships ──────────────────────────────────────
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", back_populates="users", lazy="selectin"
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket",
        foreign_keys="Ticket.assigned_to_id",
        back_populates="assigned_to",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
