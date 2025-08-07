-- Content Protection Platform Database Schema
-- PostgreSQL optimized for high-volume operations
-- Created: 2025-08-07

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE subscription_tier AS ENUM ('basic', 'professional');
CREATE TYPE infringement_status AS ENUM ('detected', 'verified', 'dmca_sent', 'removed', 'ignored', 'failed');
CREATE TYPE dmca_status AS ENUM ('pending', 'sent', 'acknowledged', 'complied', 'rejected', 'expired');
CREATE TYPE scan_status AS ENUM ('queued', 'in_progress', 'completed', 'failed');
CREATE TYPE profile_status AS ENUM ('active', 'inactive', 'suspended');

-- Users table with subscription management
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
    
    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_subscription_price CHECK (
        (subscription_tier = 'basic' AND subscription_price = 49.00) OR 
        (subscription_tier = 'professional' AND subscription_price BETWEEN 89.00 AND 99.00)
    )
);

-- Protected profiles (1 for Basic, 5 for Professional)
CREATE TABLE protected_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    profile_url VARCHAR(500),
    status profile_status DEFAULT 'active',
    face_encoding_data BYTEA, -- Stores face recognition embeddings
    keywords TEXT[], -- Array of keywords for content matching
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_scanned TIMESTAMP WITH TIME ZONE,
    
    -- Ensure profile limits based on subscription
    CONSTRAINT unique_user_profile_name UNIQUE(user_id, name)
);

-- Whitelisted URLs to skip during scanning
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

-- Scanning history with partitioning for performance
CREATE TABLE scan_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES protected_profiles(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL, -- 'face_recognition', 'keyword', 'image_hash'
    status scan_status DEFAULT 'queued',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    results_count INTEGER DEFAULT 0,
    error_message TEXT,
    scan_parameters JSONB, -- Store scan configuration
    
    -- Partitioning key
    created_date DATE DEFAULT CURRENT_DATE
) PARTITION BY RANGE (created_date);

-- Infringements tracking with high-volume optimization
CREATE TABLE infringements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES protected_profiles(id) ON DELETE CASCADE,
    scan_id UUID REFERENCES scan_history(id) ON DELETE SET NULL,
    
    -- Infringement details
    detected_url VARCHAR(1000) NOT NULL,
    platform VARCHAR(100), -- e.g., 'twitter', 'instagram', 'onlyfans'
    content_type VARCHAR(50), -- 'image', 'video', 'profile'
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.00 AND 1.00),
    
    -- Content analysis
    image_hash VARCHAR(64), -- perceptual hash for image comparison
    content_description TEXT,
    screenshot_url VARCHAR(500),
    
    -- Status tracking
    status infringement_status DEFAULT 'detected',
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by UUID REFERENCES users(id),
    
    -- Timestamps
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    metadata JSONB, -- Store additional platform-specific data
    
    -- Partitioning key for performance
    detected_date DATE DEFAULT CURRENT_DATE,
    
    CONSTRAINT unique_url_profile UNIQUE(profile_id, detected_url)
) PARTITION BY RANGE (detected_date);

-- DMCA takedown requests and outcomes
CREATE TABLE dmca_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    infringement_id UUID NOT NULL REFERENCES infringements(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Request details
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(200),
    platform VARCHAR(100) NOT NULL,
    
    -- DMCA content
    subject_line VARCHAR(500),
    request_body TEXT NOT NULL,
    copyright_work_description TEXT,
    infringing_content_location TEXT NOT NULL,
    
    -- Status and tracking
    status dmca_status DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    response_received_at TIMESTAMP WITH TIME ZONE,
    compliance_deadline TIMESTAMP WITH TIME ZONE,
    
    -- Response details
    response_body TEXT,
    compliance_status VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    tracking_number VARCHAR(100),
    platform_case_id VARCHAR(100),
    metadata JSONB
) PARTITION BY RANGE (created_at);

-- Face recognition data storage (optimized for similarity searches)
CREATE TABLE face_encodings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES protected_profiles(id) ON DELETE CASCADE,
    
    -- Face data
    encoding_vector REAL[128] NOT NULL, -- 128-dimensional face encoding
    image_url VARCHAR(500),
    image_hash VARCHAR(64),
    confidence_threshold DECIMAL(3,2) DEFAULT 0.80,
    
    -- Metadata
    source_description TEXT,
    is_primary BOOLEAN DEFAULT false, -- Primary reference image
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure vector dimension
    CONSTRAINT valid_encoding_dimension CHECK (array_length(encoding_vector, 1) = 128)
);

-- User activity logs for audit trail
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

-- Notification preferences and delivery
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'infringement_detected', 'dmca_sent', 'dmca_responded'
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    email_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

-- System configuration and feature flags
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);