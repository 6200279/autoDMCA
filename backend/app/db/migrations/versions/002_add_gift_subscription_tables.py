"""Add gift subscription tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create gift subscription related tables."""
    
    # Create gift_subscriptions table
    op.create_table(
        'gift_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('giver_user_id', sa.Integer(), nullable=False),
        sa.Column('giver_email', sa.String(255), nullable=False),
        sa.Column('giver_name', sa.String(255), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=True),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('plan', sa.Enum('FREE', 'BASIC', 'PROFESSIONAL', 'ENTERPRISE', name='subscriptionplan'), nullable=False),
        sa.Column('billing_interval', sa.Enum('MONTH', 'YEAR', name='billinginterval'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('status', sa.Enum('PENDING', 'REDEEMED', 'EXPIRED', 'CANCELLED', name='giftstatus'), nullable=False, default='PENDING'),
        sa.Column('gift_code', sa.String(32), nullable=False, unique=True),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=False),
        sa.Column('personal_message', sa.Text(), nullable=True),
        sa.Column('custom_sender_name', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_subscription_id', sa.Integer(), nullable=True),
        sa.Column('gift_email_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_emails_sent', sa.Integer(), nullable=False, default=0),
        sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['giver_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_subscription_id'], ['subscriptions.id'], ),
    )
    
    # Create indexes for gift_subscriptions
    op.create_index(op.f('ix_gift_subscriptions_id'), 'gift_subscriptions', ['id'])
    op.create_index(op.f('ix_gift_subscriptions_gift_code'), 'gift_subscriptions', ['gift_code'])
    op.create_index(op.f('ix_gift_subscriptions_giver_user_id'), 'gift_subscriptions', ['giver_user_id'])
    op.create_index(op.f('ix_gift_subscriptions_recipient_user_id'), 'gift_subscriptions', ['recipient_user_id'])
    op.create_index(op.f('ix_gift_subscriptions_status'), 'gift_subscriptions', ['status'])
    op.create_index(op.f('ix_gift_subscriptions_expires_at'), 'gift_subscriptions', ['expires_at'])
    
    # Create gift_transactions table
    op.create_table(
        'gift_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gift_subscription_id', sa.Integer(), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=False, unique=True),
        sa.Column('stripe_charge_id', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='gifttransactionstatus'), nullable=False, default='PENDING'),
        sa.Column('payment_method_type', sa.String(50), nullable=True),
        sa.Column('payment_method_last4', sa.String(4), nullable=True),
        sa.Column('payment_method_brand', sa.String(50), nullable=True),
        sa.Column('stripe_fee', sa.Numeric(10, 2), nullable=False, default=0.00),
        sa.Column('net_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.Column('refunded_amount', sa.Numeric(10, 2), nullable=False, default=0.00),
        sa.Column('refund_reason', sa.String(255), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('invoice_pdf_url', sa.String(500), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['gift_subscription_id'], ['gift_subscriptions.id'], ),
    )
    
    # Create indexes for gift_transactions
    op.create_index(op.f('ix_gift_transactions_id'), 'gift_transactions', ['id'])
    op.create_index(op.f('ix_gift_transactions_stripe_payment_intent_id'), 'gift_transactions', ['stripe_payment_intent_id'])
    op.create_index(op.f('ix_gift_transactions_status'), 'gift_transactions', ['status'])
    
    # Create gift_codes table
    op.create_table(
        'gift_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(32), nullable=False, unique=True),
        sa.Column('gift_subscription_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_redemptions', sa.Integer(), nullable=False, default=1),
        sa.Column('current_redemptions', sa.Integer(), nullable=False, default=0),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('redemption_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempt_ip', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['gift_subscription_id'], ['gift_subscriptions.id'], ),
    )
    
    # Create indexes for gift_codes
    op.create_index(op.f('ix_gift_codes_id'), 'gift_codes', ['id'])
    op.create_index(op.f('ix_gift_codes_code'), 'gift_codes', ['code'])
    op.create_index(op.f('ix_gift_codes_is_active'), 'gift_codes', ['is_active'])
    
    # Create gift_email_logs table
    op.create_table(
        'gift_email_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gift_subscription_id', sa.Integer(), nullable=False),
        sa.Column('email_type', sa.String(50), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('email_provider', sa.String(50), nullable=True),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('template_version', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['gift_subscription_id'], ['gift_subscriptions.id'], ),
    )
    
    # Create indexes for gift_email_logs
    op.create_index(op.f('ix_gift_email_logs_id'), 'gift_email_logs', ['id'])
    op.create_index(op.f('ix_gift_email_logs_email_type'), 'gift_email_logs', ['email_type'])
    op.create_index(op.f('ix_gift_email_logs_recipient_email'), 'gift_email_logs', ['recipient_email'])


def downgrade() -> None:
    """Drop gift subscription related tables."""
    
    # Drop tables in reverse order
    op.drop_table('gift_email_logs')
    op.drop_table('gift_codes')
    op.drop_table('gift_transactions')
    op.drop_table('gift_subscriptions')
    
    # Drop custom enums
    op.execute("DROP TYPE IF EXISTS giftstatus")
    op.execute("DROP TYPE IF EXISTS gifttransactionstatus")