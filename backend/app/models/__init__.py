"""
SupportPilot AI — Models Package
Import all models here so Alembic can discover them for autogenerate.
"""

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority, TicketChannel
from app.models.knowledge import KnowledgeDocument, DocumentStatus
from app.models.audit_log import AuditLog

__all__ = [
    "Organization",
    "User",
    "UserRole",
    "Ticket",
    "TicketMessage",
    "TicketStatus",
    "TicketPriority",
    "TicketChannel",
    "KnowledgeDocument",
    "DocumentStatus",
    "AuditLog",
]
