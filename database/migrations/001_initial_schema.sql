-- Migration: 001_initial_schema.sql
-- Description: Initial database schema for Content Protection Platform
-- Created: 2025-08-07
-- Author: Database Schema Generator

BEGIN;

-- Create migration tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    checksum VARCHAR(64)
);

-- Record migration start
DO $$
DECLARE
    start_time TIMESTAMP WITH TIME ZONE := CURRENT_TIMESTAMP;
    end_time TIMESTAMP WITH TIME ZONE;
    execution_ms INTEGER;
BEGIN
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    RAISE NOTICE 'Extensions enabled successfully';

    -- Create custom types
    CREATE TYPE subscription_tier AS ENUM ('basic', 'professional');
    CREATE TYPE infringement_status AS ENUM ('detected', 'verified', 'dmca_sent', 'removed', 'ignored', 'failed');
    CREATE TYPE dmca_status AS ENUM ('pending', 'sent', 'acknowledged', 'complied', 'rejected', 'expired');
    CREATE TYPE scan_status AS ENUM ('queued', 'in_progress', 'completed', 'failed');
    CREATE TYPE profile_status AS ENUM ('active', 'inactive', 'suspended');

    RAISE NOTICE 'Custom types created successfully';

    -- Create tables (order matters for foreign keys)
    
    -- Users table
    CREATE TABLE users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        subscription_tier subscription_tier NOT NULL DEFAULT 'basic',
        subscription_price DECIMAL(8,2),
        subscription_start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        subscription_end_date TIMESTAMP WITH TIME ZONE,
        is_active BOOLEAN DEFAULT true,
        email_verified BOOLEAN DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP WITH TIME ZONE,
        
        CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
        CONSTRAINT valid_subscription_price CHECK (
            (subscription_tier = 'basic' AND subscription_price = 49.00) OR 
            (subscription_tier = 'professional' AND subscription_price BETWEEN 89.00 AND 99.00)
        )
    );

    -- Protected profiles
    CREATE TABLE protected_profiles (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        profile_url VARCHAR(500),
        status profile_status DEFAULT 'active',
        face_encoding_data BYTEA,
        keywords TEXT[],
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_scanned TIMESTAMP WITH TIME ZONE,
        
        CONSTRAINT unique_user_profile_name UNIQUE(user_id, name)
    );

    -- Whitelisted URLs
    CREATE TABLE whitelisted_urls (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_id UUID REFERENCES protected_profiles(id) ON DELETE CASCADE,
        url_pattern VARCHAR(1000) NOT NULL,
        is_regex BOOLEAN DEFAULT false,
        reason TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by UUID REFERENCES users(id),
        
        CONSTRAINT unique_user_whitelist UNIQUE(user_id, url_pattern)
    );

    -- Scan history (partitioned table)
    CREATE TABLE scan_history (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_id UUID REFERENCES protected_profiles(id) ON DELETE CASCADE,
        scan_type VARCHAR(50) NOT NULL,
        status scan_status DEFAULT 'queued',
        started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE,
        results_count INTEGER DEFAULT 0,
        error_message TEXT,
        scan_parameters JSONB,
        created_date DATE DEFAULT CURRENT_DATE
    ) PARTITION BY RANGE (created_date);

    -- Infringements (partitioned table)
    CREATE TABLE infringements (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_id UUID NOT NULL REFERENCES protected_profiles(id) ON DELETE CASCADE,
        scan_id UUID REFERENCES scan_history(id) ON DELETE SET NULL,
        detected_url VARCHAR(1000) NOT NULL,
        platform VARCHAR(100),
        content_type VARCHAR(50),
        confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.00 AND 1.00),
        image_hash VARCHAR(64),
        content_description TEXT,
        screenshot_url VARCHAR(500),
        status infringement_status DEFAULT 'detected',
        verified_at TIMESTAMP WITH TIME ZONE,
        verified_by UUID REFERENCES users(id),
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB,
        detected_date DATE DEFAULT CURRENT_DATE,
        
        CONSTRAINT unique_url_profile UNIQUE(profile_id, detected_url)
    ) PARTITION BY RANGE (detected_date);

    -- DMCA requests (partitioned table)
    CREATE TABLE dmca_requests (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        infringement_id UUID NOT NULL REFERENCES infringements(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recipient_email VARCHAR(255) NOT NULL,
        recipient_name VARCHAR(200),
        platform VARCHAR(100) NOT NULL,
        subject_line VARCHAR(500),
        request_body TEXT NOT NULL,
        copyright_work_description TEXT,
        infringing_content_location TEXT NOT NULL,
        status dmca_status DEFAULT 'pending',
        sent_at TIMESTAMP WITH TIME ZONE,
        acknowledged_at TIMESTAMP WITH TIME ZONE,
        response_received_at TIMESTAMP WITH TIME ZONE,
        compliance_deadline TIMESTAMP WITH TIME ZONE,
        response_body TEXT,
        compliance_status VARCHAR(50),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        tracking_number VARCHAR(100),
        platform_case_id VARCHAR(100),
        metadata JSONB
    ) PARTITION BY RANGE (created_at);

    -- Face encodings
    CREATE TABLE face_encodings (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        profile_id UUID NOT NULL REFERENCES protected_profiles(id) ON DELETE CASCADE,
        encoding_vector REAL[128] NOT NULL,
        image_url VARCHAR(500),
        image_hash VARCHAR(64),
        confidence_threshold DECIMAL(3,2) DEFAULT 0.80,
        source_description TEXT,
        is_primary BOOLEAN DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT valid_encoding_dimension CHECK (array_length(encoding_vector, 1) = 128)
    );

    -- User activity logs (partitioned table)
    CREATE TABLE user_activity_logs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(50),
        resource_id UUID,
        ip_address INET,
        user_agent TEXT,
        details JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    ) PARTITION BY RANGE (created_at);

    -- Notifications
    CREATE TABLE notifications (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        type VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT false,
        email_sent BOOLEAN DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP WITH TIME ZONE
    );

    -- System configuration
    CREATE TABLE system_config (
        key VARCHAR(100) PRIMARY KEY,
        value JSONB NOT NULL,
        description TEXT,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_by UUID REFERENCES users(id)
    );

    RAISE NOTICE 'All tables created successfully';

    -- Calculate execution time and record migration
    end_time := CURRENT_TIMESTAMP;
    execution_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

    INSERT INTO schema_migrations (version, description, execution_time_ms, checksum)
    VALUES (
        '001',
        'Initial database schema for Content Protection Platform',
        execution_ms,
        encode(digest('001_initial_schema', 'sha256'), 'hex')
    );

    RAISE NOTICE 'Migration 001 completed successfully in % ms', execution_ms;

END $$;

COMMIT;