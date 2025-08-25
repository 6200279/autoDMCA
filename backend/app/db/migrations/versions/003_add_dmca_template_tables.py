"""Add DMCA template tables

Revision ID: 003_dmca_templates
Revises: 002_add_gift_subscription_tables
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_dmca_templates'
down_revision = '002_add_gift_subscription_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create template type enum
    template_type_enum = postgresql.ENUM(
        'standard', 'copyright', 'trademark', 'custom',
        name='templatetype'
    )
    template_type_enum.create(op.get_bind())
    
    # Create template_categories table
    op.create_table('template_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create indexes for template_categories
    op.create_index('ix_template_categories_id', 'template_categories', ['id'], unique=False)
    op.create_index('ix_template_categories_name', 'template_categories', ['name'], unique=False)
    op.create_index('ix_template_categories_display_order', 'template_categories', ['display_order'], unique=False)
    
    # Create dmca_templates table
    op.create_table('dmca_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', template_type_enum, nullable=False, default='standard'),
        sa.Column('subject_template', sa.String(length=500), nullable=False),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('requires_signature', sa.Boolean(), nullable=False, default=True),
        sa.Column('requires_sworn_statement', sa.Boolean(), nullable=False, default=True),
        sa.Column('requires_contact_info', sa.Boolean(), nullable=False, default=True),
        sa.Column('available_variables', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['template_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for dmca_templates
    op.create_index('ix_dmca_templates_id', 'dmca_templates', ['id'], unique=False)
    op.create_index('ix_dmca_templates_name', 'dmca_templates', ['name'], unique=False)
    op.create_index('ix_dmca_templates_template_type', 'dmca_templates', ['template_type'], unique=False)
    op.create_index('ix_dmca_templates_category_id', 'dmca_templates', ['category_id'], unique=False)
    op.create_index('ix_dmca_templates_is_default', 'dmca_templates', ['is_default'], unique=False)
    op.create_index('ix_dmca_templates_is_active', 'dmca_templates', ['is_active'], unique=False)
    op.create_index('ix_dmca_templates_usage_count', 'dmca_templates', ['usage_count'], unique=False)
    
    # Add template_id foreign key to takedown_requests table
    op.add_column('takedown_requests', sa.Column('template_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_takedown_requests_template_id', 'takedown_requests', 'dmca_templates', ['template_id'], ['id'])
    op.create_index('ix_takedown_requests_template_id', 'takedown_requests', ['template_id'], unique=False)
    
    # Insert default template categories
    op.execute("""
        INSERT INTO template_categories (name, description, display_order, is_active) VALUES
        ('Copyright', 'Templates for copyright infringement notices', 1, true),
        ('Trademark', 'Templates for trademark violation notices', 2, true),
        ('Social Media', 'Templates optimized for social media platforms', 3, true),
        ('General', 'General purpose DMCA templates', 4, true);
    """)
    
    # Insert default templates
    op.execute("""
        INSERT INTO dmca_templates (
            name, description, template_type, subject_template, body_template, 
            category_id, is_default, is_active, requires_signature, requires_sworn_statement, requires_contact_info,
            available_variables
        ) VALUES (
            'Standard Copyright Notice',
            'Standard DMCA takedown notice for copyright infringement',
            'copyright',
            'DMCA Takedown Notice - Copyright Infringement of {original_work_title}',
            'Dear {recipient_name},

I am writing to notify you of copyright infringement occurring on your platform/website. I am the copyright owner (or authorized representative) of the work described below.

**Copyright Owner Information:**
Name: {copyright_holder}
Email: {contact_email}
Phone: {contact_phone}

**Copyrighted Work:**
Title: {original_work_title}
Original Location: {original_work_url}
Description: This is my original copyrighted work.

**Infringing Content:**
Infringing URL: {infringing_url}
Description: The content at the above URL is an unauthorized copy of my copyrighted work.

**Good Faith Statement:**
I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.

**Accuracy Statement:**
The information in this notification is accurate, and under penalty of perjury, I am authorized to act on behalf of the copyright owner.

**Request for Removal:**
I request that you remove or disable access to the infringing content immediately.

Sincerely,
{signature}

Date: {date}',
            1,
            true,
            true,
            true,
            true,
            true,
            '["recipient_name", "copyright_holder", "contact_email", "contact_phone", "original_work_title", "original_work_url", "infringing_url", "signature", "date"]'
        );
    """)


def downgrade() -> None:
    # Remove template_id from takedown_requests
    op.drop_constraint('fk_takedown_requests_template_id', 'takedown_requests', type_='foreignkey')
    op.drop_index('ix_takedown_requests_template_id', 'takedown_requests')
    op.drop_column('takedown_requests', 'template_id')
    
    # Drop tables
    op.drop_table('dmca_templates')
    op.drop_table('template_categories')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS templatetype')