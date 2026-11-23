"""Initial database migration for SupportPilot AI

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Organizations ──────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('max_users', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_tickets_per_month', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # ── Users ──────────────────────────────────────────────────
    userrole_enum = sa.Enum('OWNER', 'ADMIN', 'AGENT', 'VIEWER', name='userrole')
    userrole_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('role', sa.Enum('OWNER', 'ADMIN', 'AGENT', 'VIEWER', name='userrole'), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)

    # ── Tickets ────────────────────────────────────────────────
    ticketstatus_enum = sa.Enum('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_REVIEW', 'ESCALATED', 'RESOLVED', 'CLOSED', name='ticketstatus')
    ticketstatus_enum.create(op.get_bind(), checkfirst=True)

    ticketpriority_enum = sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='ticketpriority')
    ticketpriority_enum.create(op.get_bind(), checkfirst=True)

    ticketchannel_enum = sa.Enum('EMAIL', 'CHAT', 'API', 'WEBHOOK', 'PORTAL', name='ticketchannel')
    ticketchannel_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'tickets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_REVIEW', 'ESCALATED', 'RESOLVED', 'CLOSED', name='ticketstatus'), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='ticketpriority'), nullable=False),
        sa.Column('channel', sa.Enum('EMAIL', 'CHAT', 'API', 'WEBHOOK', 'PORTAL', name='ticketchannel'), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=True),
        sa.Column('customer_email', sa.String(length=255), nullable=True),
        sa.Column('ai_category', sa.String(length=100), nullable=True),
        sa.Column('ai_suggested_response', sa.Text(), nullable=True),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('ai_quality_score', sa.Float(), nullable=True),
        sa.Column('ai_metadata', sa.JSON(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolution_time_seconds', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('assigned_to_id', sa.String(length=36), nullable=True),
        sa.Column('created_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickets_ai_category'), 'tickets', ['ai_category'], unique=False)
    op.create_index(op.f('ix_tickets_assigned_to_id'), 'tickets', ['assigned_to_id'], unique=False)
    op.create_index(op.f('ix_tickets_customer_email'), 'tickets', ['customer_email'], unique=False)
    op.create_index(op.f('ix_tickets_id'), 'tickets', ['id'], unique=False)
    op.create_index(op.f('ix_tickets_organization_id'), 'tickets', ['organization_id'], unique=False)
    op.create_index(op.f('ix_tickets_priority'), 'tickets', ['priority'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)

    # ── Ticket Messages ────────────────────────────────────────
    messageauthortype_enum = sa.Enum('CUSTOMER', 'AGENT', 'AI', 'SYSTEM', name='messageauthortype')
    messageauthortype_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'ticket_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ticket_id', sa.String(length=36), nullable=False),
        sa.Column('author_type', sa.Enum('CUSTOMER', 'AGENT', 'AI', 'SYSTEM', name='messageauthortype'), nullable=False),
        sa.Column('author_id', sa.String(length=36), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_messages_id'), 'ticket_messages', ['id'], unique=False)
    op.create_index(op.f('ix_ticket_messages_ticket_id'), 'ticket_messages', ['ticket_id'], unique=False)

    # ── Knowledge Documents ────────────────────────────────────
    documentstatus_enum = sa.Enum('PENDING', 'PROCESSING', 'INDEXED', 'FAILED', name='documentstatus')
    documentstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'INDEXED', 'FAILED', name='documentstatus'), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('chroma_ids', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('uploaded_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_documents_id'), 'knowledge_documents', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_organization_id'), 'knowledge_documents', ['organization_id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_status'), 'knowledge_documents', ['status'], unique=False)

    # ── Audit Logs ─────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_organization_id'), 'audit_logs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('knowledge_documents')
    op.drop_table('ticket_messages')
    op.drop_table('tickets')
    op.drop_table('users')
    op.drop_table('organizations')
    
    sa.Enum(name='documentstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='messageauthortype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ticketchannel').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ticketpriority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ticketstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
