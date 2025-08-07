-- Rollback Migration: 002_create_indexes.sql
-- Description: Drop all performance indexes
-- Created: 2025-08-07

BEGIN;

DO $$
DECLARE
    index_name TEXT;
    index_names TEXT[] := ARRAY[
        'idx_users_email', 'idx_users_subscription_tier', 'idx_users_active_subscriptions',
        'idx_users_last_login', 'idx_users_created_at',
        'idx_profiles_user_id', 'idx_profiles_user_status', 'idx_profiles_active',
        'idx_profiles_keywords', 'idx_profiles_last_scanned', 'idx_profiles_with_face_data',
        'idx_whitelist_user_id', 'idx_whitelist_profile_id', 'idx_whitelist_url_pattern_trgm',
        'idx_whitelist_regex_patterns',
        'idx_scan_history_user_id', 'idx_scan_history_profile_id', 'idx_scan_history_status',
        'idx_scan_history_performance', 'idx_scan_history_results',
        'idx_infringements_user_status', 'idx_infringements_profile_status', 'idx_infringements_platform',
        'idx_infringements_platform_status', 'idx_infringements_content_type', 'idx_infringements_url_hash',
        'idx_infringements_image_hash', 'idx_infringements_high_confidence', 'idx_infringements_workflow',
        'idx_infringements_metadata',
        'idx_dmca_user_id', 'idx_dmca_infringement_id', 'idx_dmca_status', 'idx_dmca_pending',
        'idx_dmca_compliance_deadline', 'idx_dmca_platform', 'idx_dmca_recipient',
        'idx_dmca_response_time', 'idx_dmca_tracking_number', 'idx_dmca_platform_case_id',
        'idx_face_encodings_profile_id', 'idx_face_encodings_primary', 'idx_face_encodings_image_hash',
        'idx_face_encodings_confidence',
        'idx_activity_logs_user_id', 'idx_activity_logs_action', 'idx_activity_logs_resource',
        'idx_activity_logs_ip',
        'idx_notifications_user_id', 'idx_notifications_unread', 'idx_notifications_type',
        'idx_notifications_email_pending',
        'idx_system_config_updated',
        'idx_user_infringement_summary', 'idx_profile_infringement_summary', 'idx_dmca_effectiveness',
        'idx_scan_efficiency',
        'idx_users_active_email', 'idx_users_current_subscriptions', 'idx_recent_infringements',
        'idx_actionable_dmca'
    ];
BEGIN
    RAISE NOTICE 'Rolling back index creation...';

    -- Drop all indexes
    FOREACH index_name IN ARRAY index_names LOOP
        BEGIN
            EXECUTE 'DROP INDEX IF EXISTS ' || index_name;
            RAISE NOTICE 'Dropped index: %', index_name;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Failed to drop index %: %', index_name, SQLERRM;
        END;
    END LOOP;

    -- Remove migration record
    DELETE FROM schema_migrations WHERE version = '002';
    
    RAISE NOTICE 'Rollback of migration 002 completed successfully';

END $$;

COMMIT;