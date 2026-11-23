"""
SupportPilot AI — Organization Model
Top-level multi-tenant entity. All resources belong to an organization.
"""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    """
    Represents a customer organization (tenant).
    Every resource in the system is scoped to an organization.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Subscription / plan info
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_tickets_per_month: Mapped[int] = mapped_column(Integer, default=500, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ──────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="organization", lazy="select"
    )
    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket", back_populates="organization", lazy="select"
    )
    knowledge_documents: Mapped[list["KnowledgeDocument"]] = relationship(  # noqa: F821
        "KnowledgeDocument", back_populates="organization", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug}>"
