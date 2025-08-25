"""Add content fingerprinting tables

Revision ID: 004_content_fingerprinting
Revises: 003_dmca_templates
Create Date: 2025-01-24 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_content_fingerprinting'
down_revision = '003_dmca_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create fingerprint type enum
    fingerprint_type_enum = postgresql.ENUM(
        'audio', 'video', 'image', 'text',
        name='fingerprinttype'
    )
    fingerprint_type_enum.create(op.get_bind())
    
    # Create content_fingerprints table
    op.create_table('content_fingerprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),  # SHA256 hash
        sa.Column('fingerprint_type', fingerprint_type_enum, nullable=False),
        sa.Column('fingerprint_data', postgresql.JSONB(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('source_url', sa.String(length=2048), nullable=True),
        sa.Column('profile_id', sa.Integer(), nullable=True),  # Link to creator profile
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),  # For audio/video content
        sa.Column('width', sa.Integer(), nullable=True),  # For image/video content
        sa.Column('height', sa.Integer(), nullable=True),  # For image/video content
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash')
    )
    
    # Create indexes for content_fingerprints
    op.create_index('ix_content_fingerprints_id', 'content_fingerprints', ['id'], unique=False)
    op.create_index('ix_content_fingerprints_content_hash', 'content_fingerprints', ['content_hash'], unique=True)
    op.create_index('ix_content_fingerprints_fingerprint_type', 'content_fingerprints', ['fingerprint_type'], unique=False)
    op.create_index('ix_content_fingerprints_profile_id', 'content_fingerprints', ['profile_id'], unique=False)
    op.create_index('ix_content_fingerprints_confidence', 'content_fingerprints', ['confidence'], unique=False)
    op.create_index('ix_content_fingerprints_created_at', 'content_fingerprints', ['created_at'], unique=False)
    
    # Create GIN index for JSONB fingerprint_data for fast similarity queries
    op.create_index('ix_content_fingerprints_fingerprint_data_gin', 'content_fingerprints', ['fingerprint_data'], 
                   unique=False, postgresql_using='gin')
    
    # Create fingerprint_matches table for storing match results
    op.create_table('fingerprint_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('matched_fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('match_confidence', sa.Float(), nullable=False),
        sa.Column('comparison_method', sa.String(length=50), nullable=False),
        sa.Column('match_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('is_confirmed_match', sa.Boolean(), nullable=False, default=False),
        sa.Column('reviewed_by_human', sa.Boolean(), nullable=False, default=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['query_fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matched_fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query_fingerprint_id', 'matched_fingerprint_id', name='uq_fingerprint_match_pair')
    )
    
    # Create indexes for fingerprint_matches
    op.create_index('ix_fingerprint_matches_id', 'fingerprint_matches', ['id'], unique=False)
    op.create_index('ix_fingerprint_matches_query_fingerprint_id', 'fingerprint_matches', ['query_fingerprint_id'], unique=False)
    op.create_index('ix_fingerprint_matches_matched_fingerprint_id', 'fingerprint_matches', ['matched_fingerprint_id'], unique=False)
    op.create_index('ix_fingerprint_matches_similarity_score', 'fingerprint_matches', ['similarity_score'], unique=False)
    op.create_index('ix_fingerprint_matches_match_confidence', 'fingerprint_matches', ['match_confidence'], unique=False)
    op.create_index('ix_fingerprint_matches_is_confirmed_match', 'fingerprint_matches', ['is_confirmed_match'], unique=False)
    op.create_index('ix_fingerprint_matches_created_at', 'fingerprint_matches', ['created_at'], unique=False)
    
    # Create audio_signatures table for specialized audio fingerprinting
    op.create_table('audio_signatures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('mfcc_signature', postgresql.ARRAY(sa.Float()), nullable=True),  # MFCC coefficients
        sa.Column('chroma_signature', postgresql.ARRAY(sa.Float()), nullable=True),  # Chroma features
        sa.Column('spectral_signature', postgresql.ARRAY(sa.Float()), nullable=True),  # Spectral features
        sa.Column('tempo', sa.Float(), nullable=True),
        sa.Column('zero_crossing_rate', sa.Float(), nullable=True),
        sa.Column('rms_energy', sa.Float(), nullable=True),
        sa.Column('signature_vector', postgresql.ARRAY(sa.Float()), nullable=True),  # Compact signature for fast comparison
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fingerprint_id')
    )
    
    # Create indexes for audio_signatures
    op.create_index('ix_audio_signatures_fingerprint_id', 'audio_signatures', ['fingerprint_id'], unique=True)
    op.create_index('ix_audio_signatures_tempo', 'audio_signatures', ['tempo'], unique=False)
    
    # Create video_signatures table for specialized video fingerprinting
    op.create_table('video_signatures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('frame_count', sa.Integer(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('aspect_ratio', sa.Float(), nullable=True),
        sa.Column('avg_brightness', sa.Float(), nullable=True),
        sa.Column('avg_contrast', sa.Float(), nullable=True),
        sa.Column('motion_intensity', sa.Float(), nullable=True),
        sa.Column('motion_variance', sa.Float(), nullable=True),
        sa.Column('dominant_colors', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('scene_change_indices', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('signature_vector', postgresql.ARRAY(sa.Float()), nullable=True),  # Compact signature
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fingerprint_id')
    )
    
    # Create indexes for video_signatures
    op.create_index('ix_video_signatures_fingerprint_id', 'video_signatures', ['fingerprint_id'], unique=True)
    op.create_index('ix_video_signatures_fps', 'video_signatures', ['fps'], unique=False)
    op.create_index('ix_video_signatures_aspect_ratio', 'video_signatures', ['aspect_ratio'], unique=False)
    op.create_index('ix_video_signatures_motion_intensity', 'video_signatures', ['motion_intensity'], unique=False)
    
    # Create image_hashes table for specialized image fingerprinting
    op.create_table('image_hashes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('phash', sa.String(length=64), nullable=True),  # Perceptual hash
        sa.Column('ahash', sa.String(length=64), nullable=True),  # Average hash
        sa.Column('dhash', sa.String(length=64), nullable=True),  # Difference hash
        sa.Column('whash', sa.String(length=64), nullable=True),  # Wavelet hash
        sa.Column('colorhash', sa.String(length=64), nullable=True),  # Color hash
        sa.Column('crop_resistant_hash', sa.String(length=64), nullable=True),  # Crop resistant hash
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fingerprint_id')
    )
    
    # Create indexes for image_hashes - these are crucial for fast similarity matching
    op.create_index('ix_image_hashes_fingerprint_id', 'image_hashes', ['fingerprint_id'], unique=True)
    op.create_index('ix_image_hashes_phash', 'image_hashes', ['phash'], unique=False)
    op.create_index('ix_image_hashes_ahash', 'image_hashes', ['ahash'], unique=False)
    op.create_index('ix_image_hashes_dhash', 'image_hashes', ['dhash'], unique=False)
    op.create_index('ix_image_hashes_whash', 'image_hashes', ['whash'], unique=False)
    op.create_index('ix_image_hashes_colorhash', 'image_hashes', ['colorhash'], unique=False)
    op.create_index('ix_image_hashes_crop_resistant_hash', 'image_hashes', ['crop_resistant_hash'], unique=False)
    
    # Create piracy_patterns table for ML pattern recognition
    op.create_table('piracy_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),  # Link to creator profile
        sa.Column('pattern_type', sa.String(length=50), nullable=False),  # 'temporal', 'platform', 'behavioral'
        sa.Column('pattern_data', postgresql.JSONB(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('incidents_analyzed', sa.Integer(), nullable=False, default=0),
        sa.Column('risk_score', sa.Float(), nullable=False, default=0.5),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for piracy_patterns
    op.create_index('ix_piracy_patterns_profile_id', 'piracy_patterns', ['profile_id'], unique=False)
    op.create_index('ix_piracy_patterns_pattern_type', 'piracy_patterns', ['pattern_type'], unique=False)
    op.create_index('ix_piracy_patterns_risk_score', 'piracy_patterns', ['risk_score'], unique=False)
    op.create_index('ix_piracy_patterns_is_active', 'piracy_patterns', ['is_active'], unique=False)
    op.create_index('ix_piracy_patterns_last_updated', 'piracy_patterns', ['last_updated'], unique=False)
    
    # Create GIN index for pattern_data JSONB queries
    op.create_index('ix_piracy_patterns_pattern_data_gin', 'piracy_patterns', ['pattern_data'], 
                   unique=False, postgresql_using='gin')
    
    # Create content_risk_assessments table for storing risk predictions
    op.create_table('content_risk_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('content_fingerprint_id', sa.Integer(), nullable=True),
        sa.Column('content_metadata', postgresql.JSONB(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),  # 'LOW', 'MEDIUM', 'HIGH'
        sa.Column('risk_factors', postgresql.JSONB(), nullable=False),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True),
        sa.Column('prediction_confidence', sa.Float(), nullable=False, default=0.5),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['content_fingerprint_id'], ['content_fingerprints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for content_risk_assessments
    op.create_index('ix_content_risk_assessments_profile_id', 'content_risk_assessments', ['profile_id'], unique=False)
    op.create_index('ix_content_risk_assessments_fingerprint_id', 'content_risk_assessments', ['content_fingerprint_id'], unique=False)
    op.create_index('ix_content_risk_assessments_risk_score', 'content_risk_assessments', ['risk_score'], unique=False)
    op.create_index('ix_content_risk_assessments_risk_level', 'content_risk_assessments', ['risk_level'], unique=False)
    op.create_index('ix_content_risk_assessments_created_at', 'content_risk_assessments', ['created_at'], unique=False)
    
    # Create GIN indexes for JSONB columns
    op.create_index('ix_content_risk_assessments_content_metadata_gin', 'content_risk_assessments', ['content_metadata'], 
                   unique=False, postgresql_using='gin')
    op.create_index('ix_content_risk_assessments_risk_factors_gin', 'content_risk_assessments', ['risk_factors'], 
                   unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('content_risk_assessments')
    op.drop_table('piracy_patterns')
    op.drop_table('image_hashes')
    op.drop_table('video_signatures')
    op.drop_table('audio_signatures')
    op.drop_table('fingerprint_matches')
    op.drop_table('content_fingerprints')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS fingerprinttype')