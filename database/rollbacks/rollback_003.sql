-- Rollback Migration: 003_create_partitions.sql
-- Description: Remove table partitions and utility functions
-- Created: 2025-08-07

BEGIN;

DO $$
DECLARE
    partition_name TEXT;
    parent_tables TEXT[] := ARRAY['scan_history', 'infringements', 'dmca_requests', 'user_activity_logs'];
    parent_table TEXT;
BEGIN
    RAISE NOTICE 'Rolling back partition creation...';

    -- Drop partition management functions
    DROP FUNCTION IF EXISTS create_monthly_partition(TEXT, DATE);
    DROP FUNCTION IF EXISTS drop_old_partition(TEXT, INTEGER);
    
    -- Drop all partitions for each parent table
    FOREACH parent_table IN ARRAY parent_tables LOOP
        -- Find all partitions for this parent table
        FOR partition_name IN 
            SELECT schemaname||'.'||tablename 
            FROM pg_tables 
            WHERE tablename LIKE parent_table || '_%'
            AND schemaname = 'public'
        LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || partition_name;
            RAISE NOTICE 'Dropped partition: %', partition_name;
        END LOOP;
    END LOOP;

    -- Remove migration record
    DELETE FROM schema_migrations WHERE version = '003';
    
    RAISE NOTICE 'Rollback of migration 003 completed successfully';

END $$;

COMMIT;