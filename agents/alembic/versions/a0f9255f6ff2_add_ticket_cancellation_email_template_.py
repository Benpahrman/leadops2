"""add ticket cancellation email_template tables + lead lifecycle fields

Revision ID: a0f9255f6ff2
Revises: d69d3b3ea6c8
Create Date: 2026-08-28 01:22:07.869288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0f9255f6ff2'
down_revision: Union[str, Sequence[str], None] = 'd69d3b3ea6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    existing_columns = {col['name'] for col in inspector.get_columns('leads')}

    # Add new columns to leads table for automation workflow (if not exist)
    new_lead_columns = [
        ('niche', sa.Text(), ''),
        ('last_login_at', sa.Text(), ''),
        ('created_at', sa.Text(), ''),
        ('delivery_count', sa.Integer(), 0),
        ('upsell_sent', sa.Integer(), 0),
        ('referral_sent', sa.Integer(), 0),
        ('winback_stage', sa.Integer(), 0),
        ('heartbeat_count', sa.Integer(), 0),
    ]
    for col_name, col_type, default in new_lead_columns:
        if col_name not in existing_columns:
            op.add_column('leads', sa.Column(col_name, col_type, nullable=True, default=default))

    # Create tickets table (if not exists)
    if 'tickets' not in existing_tables:
        op.create_table(
            'tickets',
            sa.Column('ticket_id', sa.String(length=255), nullable=False),
            sa.Column('lead_id', sa.String(length=255), nullable=False),
            sa.Column('ticket_type', sa.String(length=50), nullable=False, default='general'),
            sa.Column('status', sa.String(length=50), nullable=False, default='open'),
            sa.Column('priority', sa.String(length=50), nullable=False, default='medium'),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True, default=''),
            sa.Column('assignee', sa.String(length=255), nullable=True),
            sa.Column('sla_deadline', sa.Text(), nullable=True),
            sa.Column('sla_breached', sa.Integer(), nullable=False, default=0),
            sa.Column('created_at', sa.Text(), nullable=False),
            sa.Column('updated_at', sa.Text(), nullable=False),
            sa.Column('resolved_at', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id']),
            sa.PrimaryKeyConstraint('ticket_id')
        )
        op.create_index('ix_tickets_lead_id', 'tickets', ['lead_id'])

    # Create cancellation_requests table (if not exists)
    if 'cancellation_requests' not in existing_tables:
        op.create_table(
            'cancellation_requests',
            sa.Column('request_id', sa.String(length=255), nullable=False),
            sa.Column('lead_id', sa.String(length=255), nullable=False),
            sa.Column('user_email', sa.String(length=255), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True, default=''),
            sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
            sa.Column('refund_amount', sa.Float(), nullable=True),
            sa.Column('processed_by', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.Text(), nullable=False),
            sa.Column('updated_at', sa.Text(), nullable=False),
            sa.Column('processed_at', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id']),
            sa.PrimaryKeyConstraint('request_id')
        )
        op.create_index('ix_cancellation_requests_lead_id', 'cancellation_requests', ['lead_id'])

    # Create email_templates table (if not exists)
    if 'email_templates' not in existing_tables:
        op.create_table(
            'email_templates',
            sa.Column('template_id', sa.String(length=255), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False, unique=True),
            sa.Column('subject_a', sa.Text(), nullable=False),
            sa.Column('subject_b', sa.Text(), nullable=False),
            sa.Column('body_text', sa.Text(), nullable=False),
            sa.Column('body_html', sa.Text(), nullable=False),
            sa.Column('variant', sa.String(length=10), nullable=False, default='A'),
            sa.Column('active', sa.Integer(), nullable=False, default=1),
            sa.Column('created_at', sa.Text(), nullable=False),
            sa.Column('updated_at', sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint('template_id')
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('email_templates')
    op.drop_index('ix_cancellation_requests_lead_id', table_name='cancellation_requests')
    op.drop_table('cancellation_requests')
    op.drop_index('ix_tickets_lead_id', table_name='tickets')
    op.drop_table('tickets')
    op.drop_column('leads', 'heartbeat_count')
    op.drop_column('leads', 'winback_stage')
    op.drop_column('leads', 'referral_sent')
    op.drop_column('leads', 'upsell_sent')
    op.drop_column('leads', 'delivery_count')
    op.drop_column('leads', 'created_at')
    op.drop_column('leads', 'last_login_at')
    op.drop_column('leads', 'niche')