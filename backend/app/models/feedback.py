"""
SupportPilot AI — Customer Feedback Model
Stores customer CSAT ratings and survey feedback.
"""

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class CustomerFeedback(UUIDMixin, TimestampMixin, Base):
    """
    Stores post-resolution customer satisfaction (CSAT) ratings and comments.
    """

    __tablename__ = "customer_feedback"

    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="CSAT score from 1 (poor) to 5 (excellent)",
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    feedback_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", backref="feedback_entries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<CustomerFeedback id={self.id} ticket_id={self.ticket_id} rating={self.rating}>"
