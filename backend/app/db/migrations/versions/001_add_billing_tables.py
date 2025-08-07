"""Add comprehensive billing tables

Revision ID: 001_billing_tables
Revises: 
Create Date: 2025-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_billing_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    subscription_plan_enum = postgresql.ENUM(
        'free', 'basic', 'professional', 'enterprise',
        name='subscriptionplan'
    )
    subscription_plan_enum.create(op.get_bind())
    
    subscription_status_enum = postgresql.ENUM(
        'active', 'canceled', 'past_due', 'incomplete', 'incomplete_expired', 'trialing', 'unpaid',
        name='subscriptionstatus'
    )
    subscription_status_enum.create(op.get_bind())
    
    billing_interval_enum = postgresql.ENUM(
        'month', 'year',
        name='billinginterval'
    )
    billing_interval_enum.create(op.get_bind())
    
    invoice_status_enum = postgresql.ENUM(
        'draft', 'open', 'paid', 'uncollectible', 'void',
        name='invoicestatus'
    )
    invoice_status_enum.create(op.get_bind())
    
    payment_status_enum = postgresql.ENUM(
        'succeeded', 'pending', 'failed', 'canceled', 'requires_action',
        name='paymentstatus'
    )
    payment_status_enum.create(op.get_bind())
    
    # Update subscriptions table
    op.create_table('subscriptions_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan', subscription_plan_enum, nullable=False, default='free'),
        sa.Column('status', subscription_status_enum, nullable=False, default='active'),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('currency', sa.String(length=3), nullable=False, default='USD'),
        sa.Column('interval', billing_interval_enum, nullable=False, default='month'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_protected_profiles', sa.Integer(), nullable=False, default=1),
        sa.Column('max_monthly_scans', sa.Integer(), nullable=False, default=100),
        sa.Column('max_takedown_requests', sa.Integer(), nullable=False, default=5),
        sa.Column('ai_face_recognition', sa.Boolean(), nullable=False, default=False),
        sa.Column('priority_support', sa.Boolean(), nullable=False, default=False),
        sa.Column('custom_branding', sa.Boolean(), nullable=False, default=False),
        sa.Column('api_access', sa.Boolean(), nullable=False, default=False),
        sa.Column('previous_plan', subscription_plan_enum, nullable=True),
        sa.Column('next_plan', subscription_plan_enum, nullable=True),
        sa.Column('plan_change_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('stripe_subscription_id')
    )
    
    # Create indexes for subscriptions
    op.create_index('ix_subscriptions_new_id', 'subscriptions_new', ['id'], unique=False)
    op.create_index('ix_subscriptions_new_stripe_customer_id', 'subscriptions_new', ['stripe_customer_id'], unique=False)
    op.create_index('ix_subscriptions_new_stripe_subscription_id', 'subscriptions_new', ['stripe_subscription_id'], unique=False)
    
    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_invoice_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('invoice_number', sa.String(length=100), nullable=True),
        sa.Column('status', invoice_status_enum, nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tax', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('amount_due', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, default='USD'),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invoice_pdf_url', sa.String(length=500), nullable=True),
        sa.Column('hosted_invoice_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions_new.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_invoice_id')
    )
    
    # Create indexes for invoices
    op.create_index('ix_invoices_id', 'invoices', ['id'], unique=False)
    op.create_index('ix_invoices_stripe_invoice_id', 'invoices', ['stripe_invoice_id'], unique=False)
    
    # Create invoice_line_items table
    op.create_table('invoice_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('unit_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, default='USD'),
        sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create payment_methods table
    op.create_table('payment_methods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_payment_method_id', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('card_brand', sa.String(length=50), nullable=True),
        sa.Column('card_last4', sa.String(length=4), nullable=True),
        sa.Column('card_exp_month', sa.Integer(), nullable=True),
        sa.Column('card_exp_year', sa.Integer(), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('bank_last4', sa.String(length=4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_payment_method_id')
    )
    
    # Create indexes for payment_methods
    op.create_index('ix_payment_methods_id', 'payment_methods', ['id'], unique=False)
    op.create_index('ix_payment_methods_stripe_payment_method_id', 'payment_methods', ['stripe_payment_method_id'], unique=False)
    
    # Create usage_records table
    op.create_table('usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions_new.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create billing_addresses table
    op.create_table('billing_addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('line1', sa.String(length=255), nullable=False),
        sa.Column('line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('tax_id_type', sa.String(length=50), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Migrate existing subscription data if the table exists
    try:
        # Check if old subscriptions table exists and has data
        conn = op.get_bind()
        result = conn.execute(sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'subscriptions')"))
        table_exists = result.scalar()
        
        if table_exists:
            # Migrate existing data
            conn.execute(sa.text("""
                INSERT INTO subscriptions_new (
                    id, user_id, plan, status, stripe_customer_id, stripe_subscription_id, 
                    stripe_price_id, amount, currency, current_period_start, current_period_end,
                    trial_start, trial_end, canceled_at, max_protected_profiles, max_monthly_scans,
                    max_takedown_requests, ai_face_recognition, priority_support, custom_branding,
                    api_access, created_at, updated_at
                )
                SELECT 
                    id, user_id, plan::text::subscriptionplan, status::text::subscriptionstatus,
                    stripe_customer_id, stripe_subscription_id, stripe_price_id,
                    amount, currency, current_period_start, current_period_end,
                    trial_start, trial_end, canceled_at, max_protected_profiles, max_monthly_scans,
                    max_takedown_requests, ai_face_recognition, priority_support, custom_branding,
                    api_access, created_at, updated_at
                FROM subscriptions
            """))
            
            # Drop old table
            op.drop_table('subscriptions')
    except Exception:
        # If table doesn't exist or migration fails, continue
        pass
    
    # Rename new table to subscriptions
    op.rename_table('subscriptions_new', 'subscriptions')


def downgrade() -> None:
    # Drop all new tables
    op.drop_table('billing_addresses')
    op.drop_table('usage_records')
    op.drop_table('payment_methods')
    op.drop_table('invoice_line_items')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS invoicestatus')
    op.execute('DROP TYPE IF EXISTS billinginterval')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionplan')