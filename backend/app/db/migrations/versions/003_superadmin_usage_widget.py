"""Add Super Admin role, AI message usage tracking, and chatbot widget config

Revision ID: 003_superadmin_usage_widget
Revises: 002_customer_feedback
Create Date: 2026-11-23 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_superadmin_usage_widget'
down_revision: Union[str, None] = '002_customer_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add SUPER_ADMIN to userrole enum in PostgreSQL
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN';")

    # 2. Add AI message usage tracking & limits to organizations
    op.add_column('organizations', sa.Column('max_ai_messages_per_month', sa.Integer(), nullable=False, server_default='1000'))
    op.add_column('organizations', sa.Column('ai_messages_used_this_month', sa.Integer(), nullable=False, server_default='0'))

    # 3. Add embeddable chatbot widget settings
    op.add_column('organizations', sa.Column('widget_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('organizations', sa.Column('widget_primary_color', sa.String(length=50), nullable=False, server_default='#4F46E5'))
    op.add_column('organizations', sa.Column('widget_greeting', sa.Text(), nullable=True, server_default='Hi there! How can we help you today?'))
    op.add_column('organizations', sa.Column('widget_allowed_domains', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'widget_allowed_domains')
    op.drop_column('organizations', 'widget_greeting')
    op.drop_column('organizations', 'widget_primary_color')
    op.drop_column('organizations', 'widget_enabled')
    op.drop_column('organizations', 'ai_messages_used_this_month')
    op.drop_column('organizations', 'max_ai_messages_per_month')
