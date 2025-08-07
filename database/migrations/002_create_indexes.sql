-- Migration: 002_create_indexes.sql
-- Description: Create optimized indexes for high-volume operations
-- Created: 2025-08-07
-- Author: Database Schema Generator

BEGIN;

DO $$
DECLARE
    start_time TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP;
    end_time TIMESTAMP WITH TIME ZONE;
    execution_ms INTEGER;
BEGIN
    RAISE NOTICE 'Creating indexes for high-performance operations...';

    -- Users table indexes
    CREATE UNIQUE INDEX CONCURRENTLY idx_users_email ON users USING btree (email);
    CREATE INDEX CONCURRENTLY idx_users_subscription_tier ON users USING btree (subscription_tier) WHERE is_active = true;
    CREATE INDEX CONCURRENTLY idx_users_active_subscriptions ON users USING btree (subscription_end_date) 
        WHERE is_active = true AND subscription_end_date > CURRENT_TIMESTAMP;
    CREATE INDEX CONCURRENTLY idx_users_last_login ON users USING btree (last_login DESC) WHERE is_active = true;
    CREATE INDEX CONCURRENTLY idx_users_created_at ON users USING btree (created_at DESC);

    -- Protected profiles indexes
    CREATE INDEX CONCURRENTLY idx_profiles_user_id ON protected_profiles USING btree (user_id);
    CREATE INDEX CONCURRENTLY idx_profiles_user_status ON protected_profiles USING btree (user_id, status);
    CREATE INDEX CONCURRENTLY idx_profiles_active ON protected_profiles USING btree (user_id) WHERE status = 'active';
    CREATE INDEX CONCURRENTLY idx_profiles_keywords ON protected_profiles USING gin (keywords);
    CREATE INDEX CONCURRENTLY idx_profiles_last_scanned ON protected_profiles USING btree (last_scanned ASC NULLS FIRST);
    CREATE INDEX CONCURRENTLY idx_profiles_with_face_data ON protected_profiles USING btree (id) 
        WHERE face_encoding_data IS NOT NULL;

    -- Whitelisted URLs indexes
    CREATE INDEX CONCURRENTLY idx_whitelist_user_id ON whitelisted_urls USING btree (user_id);
    CREATE INDEX CONCURRENTLY idx_whitelist_profile_id ON whitelisted_urls USING btree (profile_id) WHERE profile_id IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_whitelist_url_pattern_trgm ON whitelisted_urls USING gin (url_pattern gin_trgm_ops);
    CREATE INDEX CONCURRENTLY idx_whitelist_regex_patterns ON whitelisted_urls USING btree (url_pattern) WHERE is_regex = true;

    -- Scan history indexes (will be applied to partitions)
    CREATE INDEX CONCURRENTLY idx_scan_history_user_id ON scan_history USING btree (user_id, created_date DESC);
    CREATE INDEX CONCURRENTLY idx_scan_history_profile_id ON scan_history USING btree (profile_id, created_date DESC);
    CREATE INDEX CONCURRENTLY idx_scan_history_status ON scan_history USING btree (status, started_at) 
        WHERE status IN ('queued', 'in_progress');
    CREATE INDEX CONCURRENTLY idx_scan_history_performance ON scan_history USING btree (scan_type, completed_at DESC) 
        WHERE completed_at IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_scan_history_results ON scan_history USING btree (results_count DESC, completed_at DESC) 
        WHERE status = 'completed';

    -- Infringements indexes (critical for performance)
    CREATE INDEX CONCURRENTLY idx_infringements_user_status ON infringements USING btree (user_id, status, detected_at DESC);
    CREATE INDEX CONCURRENTLY idx_infringements_profile_status ON infringements USING btree (profile_id, status, detected_at DESC);
    CREATE INDEX CONCURRENTLY idx_infringements_platform ON infringements USING btree (platform, detected_date DESC);
    CREATE INDEX CONCURRENTLY idx_infringements_platform_status ON infringements USING btree (platform, status, detected_at DESC);
    CREATE INDEX CONCURRENTLY idx_infringements_content_type ON infringements USING btree (content_type, confidence_score DESC);
    CREATE INDEX CONCURRENTLY idx_infringements_url_hash ON infringements USING hash (detected_url);
    CREATE INDEX CONCURRENTLY idx_infringements_image_hash ON infringements USING btree (image_hash) WHERE image_hash IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_infringements_high_confidence ON infringements USING btree (confidence_score DESC, detected_at DESC) 
        WHERE confidence_score >= 0.80;
    CREATE INDEX CONCURRENTLY idx_infringements_workflow ON infringements USING btree (status, updated_at ASC) 
        WHERE status IN ('detected', 'verified');
    CREATE INDEX CONCURRENTLY idx_infringements_metadata ON infringements USING gin (metadata);

    -- DMCA requests indexes
    CREATE INDEX CONCURRENTLY idx_dmca_user_id ON dmca_requests USING btree (user_id, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_dmca_infringement_id ON dmca_requests USING btree (infringement_id);
    CREATE INDEX CONCURRENTLY idx_dmca_status ON dmca_requests USING btree (status, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_dmca_pending ON dmca_requests USING btree (sent_at ASC) WHERE status = 'pending';
    CREATE INDEX CONCURRENTLY idx_dmca_compliance_deadline ON dmca_requests USING btree (compliance_deadline ASC) 
        WHERE status IN ('sent', 'acknowledged') AND compliance_deadline > CURRENT_TIMESTAMP;
    CREATE INDEX CONCURRENTLY idx_dmca_platform ON dmca_requests USING btree (platform, status, sent_at DESC);
    CREATE INDEX CONCURRENTLY idx_dmca_recipient ON dmca_requests USING btree (recipient_email, platform);
    CREATE INDEX CONCURRENTLY idx_dmca_response_time ON dmca_requests USING btree (sent_at, response_received_at) 
        WHERE response_received_at IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_dmca_tracking_number ON dmca_requests USING btree (tracking_number) WHERE tracking_number IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_dmca_platform_case_id ON dmca_requests USING btree (platform_case_id) WHERE platform_case_id IS NOT NULL;

    -- Face encodings indexes
    CREATE INDEX CONCURRENTLY idx_face_encodings_profile_id ON face_encodings USING btree (profile_id);
    CREATE INDEX CONCURRENTLY idx_face_encodings_primary ON face_encodings USING btree (profile_id) WHERE is_primary = true;
    CREATE INDEX CONCURRENTLY idx_face_encodings_image_hash ON face_encodings USING btree (image_hash) WHERE image_hash IS NOT NULL;
    CREATE INDEX CONCURRENTLY idx_face_encodings_confidence ON face_encodings USING btree (confidence_threshold DESC);

    -- User activity logs indexes
    CREATE INDEX CONCURRENTLY idx_activity_logs_user_id ON user_activity_logs USING btree (user_id, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_activity_logs_action ON user_activity_logs USING btree (action, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_activity_logs_resource ON user_activity_logs USING btree (resource_type, resource_id, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_activity_logs_ip ON user_activity_logs USING btree (ip_address, created_at DESC);

    -- Notifications indexes
    CREATE INDEX CONCURRENTLY idx_notifications_user_id ON notifications USING btree (user_id, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_notifications_unread ON notifications USING btree (user_id, created_at DESC) WHERE is_read = false;
    CREATE INDEX CONCURRENTLY idx_notifications_type ON notifications USING btree (type, created_at DESC);
    CREATE INDEX CONCURRENTLY idx_notifications_email_pending ON notifications USING btree (created_at ASC) 
        WHERE email_sent = false AND is_read = false;

    -- System config indexes
    CREATE INDEX CONCURRENTLY idx_system_config_updated ON system_config USING btree (updated_at DESC);

    -- Composite indexes for complex queries
    CREATE INDEX CONCURRENTLY idx_user_infringement_summary ON infringements USING btree (user_id, status, detected_date DESC);
    CREATE INDEX CONCURRENTLY idx_profile_infringement_summary ON infringements USING btree (profile_id, status, detected_date DESC);
    CREATE INDEX CONCURRENTLY idx_dmca_effectiveness ON dmca_requests USING btree (user_id, status, sent_at DESC, response_received_at);
    CREATE INDEX CONCURRENTLY idx_scan_efficiency ON scan_history USING btree (scan_type, status, started_at, completed_at) 
        WHERE completed_at IS NOT NULL;

    -- Partial indexes for better performance
    CREATE UNIQUE INDEX CONCURRENTLY idx_users_active_email ON users USING btree (email) WHERE is_active = true;
    CREATE INDEX CONCURRENTLY idx_users_current_subscriptions ON users USING btree (subscription_tier, subscription_end_date) 
        WHERE is_active = true AND (subscription_end_date IS NULL OR subscription_end_date > CURRENT_TIMESTAMP);
    CREATE INDEX CONCURRENTLY idx_recent_infringements ON infringements USING btree (user_id, status, detected_at DESC) 
        WHERE detected_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';
    CREATE INDEX CONCURRENTLY idx_actionable_dmca ON dmca_requests USING btree (user_id, status, compliance_deadline ASC) 
        WHERE status IN ('sent', 'acknowledged') AND compliance_deadline IS NOT NULL;

    -- Calculate execution time and record migration
    end_time := CURRENT_TIMESTAMP;
    execution_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

    INSERT INTO schema_migrations (version, description, execution_time_ms, checksum)
    VALUES (
        '002',
        'Create optimized indexes for high-volume operations',
        execution_ms,
        encode(digest('002_create_indexes', 'sha256'), 'hex')
    );

    RAISE NOTICE 'Migration 002 completed successfully in % ms', execution_ms;

END $$;

COMMIT;