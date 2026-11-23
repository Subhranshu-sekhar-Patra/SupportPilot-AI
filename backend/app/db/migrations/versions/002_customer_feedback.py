"""Add customer feedback table

Revision ID: 002_customer_feedback
Revises: 001_initial_schema
Create Date: 2026-11-23 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_customer_feedback'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'customer_feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ticket_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False, comment='CSAT score from 1 (poor) to 5 (excellent)'),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('customer_email', sa.String(length=255), nullable=True),
        sa.Column('feedback_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_feedback_id'), 'customer_feedback', ['id'], unique=False)
    op.create_index(op.f('ix_customer_feedback_ticket_id'), 'customer_feedback', ['ticket_id'], unique=False)
    op.create_index(op.f('ix_customer_feedback_organization_id'), 'customer_feedback', ['organization_id'], unique=False)
    op.create_index(op.f('ix_customer_feedback_customer_email'), 'customer_feedback', ['customer_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_feedback_customer_email'), table_name='customer_feedback')
    op.drop_index(op.f('ix_customer_feedback_organization_id'), table_name='customer_feedback')
    op.drop_index(op.f('ix_customer_feedback_ticket_id'), table_name='customer_feedback')
    op.drop_index(op.f('ix_customer_feedback_id'), table_name='customer_feedback')
    op.drop_table('customer_feedback')
