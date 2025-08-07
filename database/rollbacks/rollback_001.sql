-- Rollback Migration: 001_initial_schema.sql
-- Description: Drop all tables, types, and extensions
-- Created: 2025-08-07
-- WARNING: This will destroy all data in the content protection platform

BEGIN;

DO $$
BEGIN
    RAISE NOTICE 'WARNING: Rolling back initial schema - this will destroy all data!';

    -- Drop all tables (order matters due to foreign key constraints)
    DROP TABLE IF EXISTS notifications CASCADE;
    DROP TABLE IF EXISTS user_activity_logs CASCADE;
    DROP TABLE IF EXISTS face_encodings CASCADE;
    DROP TABLE IF EXISTS dmca_requests CASCADE;
    DROP TABLE IF EXISTS infringements CASCADE;
    DROP TABLE IF EXISTS scan_history CASCADE;
    DROP TABLE IF EXISTS whitelisted_urls CASCADE;
    DROP TABLE IF EXISTS protected_profiles CASCADE;
    DROP TABLE IF EXISTS system_config CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    
    -- Drop the migration tracking table
    DROP TABLE IF EXISTS schema_migrations CASCADE;

    -- Drop custom types
    DROP TYPE IF EXISTS profile_status CASCADE;
    DROP TYPE IF EXISTS scan_status CASCADE;
    DROP TYPE IF EXISTS dmca_status CASCADE;
    DROP TYPE IF EXISTS infringement_status CASCADE;
    DROP TYPE IF EXISTS subscription_tier CASCADE;

    -- Note: We don't drop extensions as they might be used by other databases
    -- Extensions: uuid-ossp, pgcrypto, pg_trgm will remain installed

    RAISE NOTICE 'Rollback of migration 001 completed successfully - all data destroyed!';

END $$;

COMMIT;