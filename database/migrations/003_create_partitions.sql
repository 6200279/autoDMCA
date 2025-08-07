-- Migration: 003_create_partitions.sql
-- Description: Create table partitions for high-volume data
-- Created: 2025-08-07
-- Author: Database Schema Generator

BEGIN;

DO $$
DECLARE
    start_time TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP;
    end_time TIMESTAMP WITH TIME ZONE;
    execution_ms INTEGER;
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
    i INTEGER;
BEGIN
    RAISE NOTICE 'Creating table partitions for high-volume data...';

    -- Create partitions for scan_history (6 months: past 3 months + current + future 2 months)
    FOR i IN -3..2 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        start_date := partition_date;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'scan_history_' || TO_CHAR(partition_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE %I PARTITION OF scan_history 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        -- Create indexes on each partition
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_date DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (profile_id, created_date DESC)', 
            'idx_' || partition_name || '_profile_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (status, started_at) WHERE status IN (''queued'', ''in_progress'')', 
            'idx_' || partition_name || '_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (scan_type, completed_at DESC) WHERE completed_at IS NOT NULL', 
            'idx_' || partition_name || '_performance', partition_name);
            
        RAISE NOTICE 'Created partition: %', partition_name;
    END LOOP;

    -- Create partitions for infringements (6 months: past 3 months + current + future 2 months)
    FOR i IN -3..2 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        start_date := partition_date;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'infringements_' || TO_CHAR(partition_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE %I PARTITION OF infringements 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        -- Create critical indexes on each partition
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, status, detected_at DESC)', 
            'idx_' || partition_name || '_user_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (profile_id, status, detected_at DESC)', 
            'idx_' || partition_name || '_profile_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (platform, status, detected_at DESC)', 
            'idx_' || partition_name || '_platform_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (confidence_score DESC, detected_at DESC) WHERE confidence_score >= 0.80', 
            'idx_' || partition_name || '_high_confidence', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (status, updated_at ASC) WHERE status IN (''detected'', ''verified'')', 
            'idx_' || partition_name || '_workflow', partition_name);
        EXECUTE format('CREATE UNIQUE INDEX %I ON %I USING btree (profile_id, detected_url)', 
            'idx_' || partition_name || '_unique_url', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING gin (metadata)', 
            'idx_' || partition_name || '_metadata', partition_name);
            
        RAISE NOTICE 'Created partition: %', partition_name;
    END LOOP;

    -- Create partitions for dmca_requests (6 months: past 3 months + current + future 2 months)
    FOR i IN -3..2 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        start_date := partition_date;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'dmca_requests_' || TO_CHAR(partition_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE %I PARTITION OF dmca_requests 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        -- Create indexes on each partition
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_at DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (infringement_id)', 
            'idx_' || partition_name || '_infringement_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (status, created_at DESC)', 
            'idx_' || partition_name || '_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (platform, status, sent_at DESC)', 
            'idx_' || partition_name || '_platform', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (compliance_deadline ASC) WHERE status IN (''sent'', ''acknowledged'') AND compliance_deadline > CURRENT_TIMESTAMP', 
            'idx_' || partition_name || '_deadline', partition_name);
            
        RAISE NOTICE 'Created partition: %', partition_name;
    END LOOP;

    -- Create partitions for user_activity_logs (6 months: past 3 months + current + future 2 months)
    FOR i IN -3..2 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        start_date := partition_date;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'user_activity_logs_' || TO_CHAR(partition_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE %I PARTITION OF user_activity_logs 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
        
        -- Create indexes on each partition
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_at DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (action, created_at DESC)', 
            'idx_' || partition_name || '_action', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (resource_type, resource_id, created_at DESC)', 
            'idx_' || partition_name || '_resource', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (ip_address, created_at DESC)', 
            'idx_' || partition_name || '_ip', partition_name);
            
        RAISE NOTICE 'Created partition: %', partition_name;
    END LOOP;

    RAISE NOTICE 'All partitions created successfully';

    -- Calculate execution time and record migration
    end_time := CURRENT_TIMESTAMP;
    execution_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

    INSERT INTO schema_migrations (version, description, execution_time_ms, checksum)
    VALUES (
        '003',
        'Create table partitions for high-volume data',
        execution_ms,
        encode(digest('003_create_partitions', 'sha256'), 'hex')
    );

    RAISE NOTICE 'Migration 003 completed successfully in % ms', execution_ms;

END $$;

-- Create function to automatically create new partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(
    parent_table TEXT,
    partition_date DATE DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
    target_date DATE;
BEGIN
    -- Use provided date or next month
    target_date := COALESCE(partition_date, DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month'));
    start_date := DATE_TRUNC('month', target_date);
    end_date := start_date + INTERVAL '1 month';
    partition_name := parent_table || '_' || TO_CHAR(target_date, 'YYYY_MM');
    
    -- Create the partition
    EXECUTE format('
        CREATE TABLE %I PARTITION OF %I 
        FOR VALUES FROM (%L) TO (%L)',
        partition_name, parent_table, start_date, end_date
    );
    
    -- Create appropriate indexes based on parent table
    IF parent_table = 'scan_history' THEN
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_date DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (profile_id, created_date DESC)', 
            'idx_' || partition_name || '_profile_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (status, started_at) WHERE status IN (''queued'', ''in_progress'')', 
            'idx_' || partition_name || '_status', partition_name);
            
    ELSIF parent_table = 'infringements' THEN
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, status, detected_at DESC)', 
            'idx_' || partition_name || '_user_status', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (profile_id, status, detected_at DESC)', 
            'idx_' || partition_name || '_profile_status', partition_name);
        EXECUTE format('CREATE UNIQUE INDEX %I ON %I USING btree (profile_id, detected_url)', 
            'idx_' || partition_name || '_unique_url', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING gin (metadata)', 
            'idx_' || partition_name || '_metadata', partition_name);
            
    ELSIF parent_table = 'dmca_requests' THEN
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_at DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (infringement_id)', 
            'idx_' || partition_name || '_infringement_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (status, created_at DESC)', 
            'idx_' || partition_name || '_status', partition_name);
            
    ELSIF parent_table = 'user_activity_logs' THEN
        EXECUTE format('CREATE INDEX %I ON %I USING btree (user_id, created_at DESC)', 
            'idx_' || partition_name || '_user_id', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I USING btree (action, created_at DESC)', 
            'idx_' || partition_name || '_action', partition_name);
    END IF;
    
    RETURN partition_name;
END;
$$ LANGUAGE plpgsql;

-- Create function to drop old partitions (for data retention)
CREATE OR REPLACE FUNCTION drop_old_partition(
    parent_table TEXT,
    months_to_keep INTEGER DEFAULT 12
) RETURNS TEXT[] AS $$
DECLARE
    partition_name TEXT;
    dropped_partitions TEXT[] := '{}';
    cutoff_date DATE;
BEGIN
    cutoff_date := DATE_TRUNC('month', CURRENT_DATE - (months_to_keep || ' months')::INTERVAL);
    
    -- Find and drop old partitions
    FOR partition_name IN 
        SELECT schemaname||'.'||tablename 
        FROM pg_tables 
        WHERE tablename LIKE parent_table || '_%'
        AND schemaname = 'public'
        AND RIGHT(tablename, 7) < TO_CHAR(cutoff_date, 'YYYY_MM')
    LOOP
        EXECUTE 'DROP TABLE ' || partition_name;
        dropped_partitions := array_append(dropped_partitions, partition_name);
    END LOOP;
    
    RETURN dropped_partitions;
END;
$$ LANGUAGE plpgsql;

COMMIT;