"""
SupportPilot AI — Ticket Model
Implements a full state machine with AI enrichment fields.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class TicketStatus(str, enum.Enum):
    """
    Ticket lifecycle states.
    Valid transitions:
        OPEN → ASSIGNED → IN_PROGRESS → PENDING_REVIEW → RESOLVED → CLOSED
        ASSIGNED/IN_PROGRESS → ESCALATED → IN_PROGRESS
    """
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketChannel(str, enum.Enum):
    EMAIL = "email"
    CHAT = "chat"
    API = "api"
    WEBHOOK = "webhook"
    PORTAL = "portal"


class Ticket(UUIDMixin, TimestampMixin, Base):
    """
    Customer support ticket with AI enrichment metadata.
    """

    __tablename__ = "tickets"

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # State machine
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False, index=True
    )
    channel: Mapped[TicketChannel] = mapped_column(
        Enum(TicketChannel), default=TicketChannel.PORTAL, nullable=False
    )

    # Customer info (may not be a registered user)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # AI-generated enrichment
    ai_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ai_suggested_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    ai_quality_score: Mapped[float | None] = mapped_column(nullable=True)
    ai_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Resolution info
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Multi-tenancy
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assignments
    assigned_to_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", back_populates="tickets"
    )
    assigned_to: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tickets",
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status} priority={self.priority}>"


class MessageAuthorType(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    AI = "ai"
    SYSTEM = "system"


class TicketMessage(UUIDMixin, TimestampMixin, Base):
    """A single message within a ticket conversation thread."""

    __tablename__ = "ticket_messages"

    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_type: Mapped[MessageAuthorType] = mapped_column(
        Enum(MessageAuthorType), nullable=False
    )
    author_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(default=False, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Relationships ──────────────────────────────────────
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")

    def __repr__(self) -> str:
        return f"<TicketMessage id={self.id} author={self.author_type}>"
