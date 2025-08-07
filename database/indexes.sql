-- High-Performance Indexes for Content Protection Platform
-- Optimized for query patterns and high-volume operations

-- ============================================================================
-- USERS TABLE INDEXES
-- ============================================================================

-- Primary lookup indexes
CREATE UNIQUE INDEX idx_users_email ON users USING btree (email);
CREATE INDEX idx_users_subscription_tier ON users USING btree (subscription_tier) WHERE is_active = true;
CREATE INDEX idx_users_active_subscriptions ON users USING btree (subscription_end_date) 
    WHERE is_active = true AND subscription_end_date > CURRENT_TIMESTAMP;

-- Activity tracking
CREATE INDEX idx_users_last_login ON users USING btree (last_login DESC) WHERE is_active = true;
CREATE INDEX idx_users_created_at ON users USING btree (created_at DESC);

-- ============================================================================
-- PROTECTED PROFILES TABLE INDEXES
-- ============================================================================

-- User profile lookups (enforce subscription limits)
CREATE INDEX idx_profiles_user_id ON protected_profiles USING btree (user_id);
CREATE INDEX idx_profiles_user_status ON protected_profiles USING btree (user_id, status);
CREATE INDEX idx_profiles_active ON protected_profiles USING btree (user_id) WHERE status = 'active';

-- Content matching
CREATE INDEX idx_profiles_keywords ON protected_profiles USING gin (keywords);
CREATE INDEX idx_profiles_last_scanned ON protected_profiles USING btree (last_scanned ASC NULLS FIRST);

-- Face recognition optimization
CREATE INDEX idx_profiles_with_face_data ON protected_profiles USING btree (id) 
    WHERE face_encoding_data IS NOT NULL;

-- ============================================================================
-- WHITELISTED URLS TABLE INDEXES
-- ============================================================================

-- Fast whitelist checking during scanning
CREATE INDEX idx_whitelist_user_id ON whitelisted_urls USING btree (user_id);
CREATE INDEX idx_whitelist_profile_id ON whitelisted_urls USING btree (profile_id) WHERE profile_id IS NOT NULL;

-- URL pattern matching (use trigram for fuzzy matching)
CREATE INDEX idx_whitelist_url_pattern_trgm ON whitelisted_urls USING gin (url_pattern gin_trgm_ops);
CREATE INDEX idx_whitelist_regex_patterns ON whitelisted_urls USING btree (url_pattern) WHERE is_regex = true;

-- ============================================================================
-- SCAN HISTORY TABLE INDEXES
-- ============================================================================

-- Note: This table is partitioned by created_date
-- Indexes will be created on each partition

-- Template for partition indexes
-- User activity tracking
CREATE INDEX idx_scan_history_user_id ON scan_history USING btree (user_id, created_date DESC);
CREATE INDEX idx_scan_history_profile_id ON scan_history USING btree (profile_id, created_date DESC);

-- Status monitoring
CREATE INDEX idx_scan_history_status ON scan_history USING btree (status, started_at) 
    WHERE status IN ('queued', 'in_progress');

-- Performance monitoring
CREATE INDEX idx_scan_history_performance ON scan_history USING btree (scan_type, completed_at DESC) 
    WHERE completed_at IS NOT NULL;

-- Scan results analysis
CREATE INDEX idx_scan_history_results ON scan_history USING btree (results_count DESC, completed_at DESC) 
    WHERE status = 'completed';

-- ============================================================================
-- INFRINGEMENTS TABLE INDEXES (High-Volume Optimized)
-- ============================================================================

-- Note: This table is partitioned by detected_date
-- Critical indexes for high-volume operations

-- User dashboard queries
CREATE INDEX idx_infringements_user_status ON infringements USING btree (user_id, status, detected_at DESC);
CREATE INDEX idx_infringements_profile_status ON infringements USING btree (profile_id, status, detected_at DESC);

-- Platform analysis
CREATE INDEX idx_infringements_platform ON infringements USING btree (platform, detected_date DESC);
CREATE INDEX idx_infringements_platform_status ON infringements USING btree (platform, status, detected_at DESC);

-- Content type analysis
CREATE INDEX idx_infringements_content_type ON infringements USING btree (content_type, confidence_score DESC);

-- URL deduplication (partial index for performance)
CREATE INDEX idx_infringements_url_hash ON infringements USING hash (detected_url);

-- Image similarity searches
CREATE INDEX idx_infringements_image_hash ON infringements USING btree (image_hash) WHERE image_hash IS NOT NULL;

-- High confidence detections
CREATE INDEX idx_infringements_high_confidence ON infringements USING btree (confidence_score DESC, detected_at DESC) 
    WHERE confidence_score >= 0.80;

-- Status workflow tracking
CREATE INDEX idx_infringements_workflow ON infringements USING btree (status, updated_at ASC) 
    WHERE status IN ('detected', 'verified');

-- Metadata queries (using GIN for JSONB)
CREATE INDEX idx_infringements_metadata ON infringements USING gin (metadata);

-- ============================================================================
-- DMCA REQUESTS TABLE INDEXES
-- ============================================================================

-- User request tracking
CREATE INDEX idx_dmca_user_id ON dmca_requests USING btree (user_id, created_at DESC);
CREATE INDEX idx_dmca_infringement_id ON dmca_requests USING btree (infringement_id);

-- Status monitoring and workflows
CREATE INDEX idx_dmca_status ON dmca_requests USING btree (status, created_at DESC);
CREATE INDEX idx_dmca_pending ON dmca_requests USING btree (sent_at ASC) WHERE status = 'pending';
CREATE INDEX idx_dmca_compliance_deadline ON dmca_requests USING btree (compliance_deadline ASC) 
    WHERE status IN ('sent', 'acknowledged') AND compliance_deadline > CURRENT_TIMESTAMP;

-- Platform tracking
CREATE INDEX idx_dmca_platform ON dmca_requests USING btree (platform, status, sent_at DESC);
CREATE INDEX idx_dmca_recipient ON dmca_requests USING btree (recipient_email, platform);

-- Response time analysis
CREATE INDEX idx_dmca_response_time ON dmca_requests USING btree (sent_at, response_received_at) 
    WHERE response_received_at IS NOT NULL;

-- External tracking
CREATE INDEX idx_dmca_tracking_number ON dmca_requests USING btree (tracking_number) WHERE tracking_number IS NOT NULL;
CREATE INDEX idx_dmca_platform_case_id ON dmca_requests USING btree (platform_case_id) WHERE platform_case_id IS NOT NULL;

-- ============================================================================
-- FACE ENCODINGS TABLE INDEXES
-- ============================================================================

-- Profile face data
CREATE INDEX idx_face_encodings_profile_id ON face_encodings USING btree (profile_id);
CREATE INDEX idx_face_encodings_primary ON face_encodings USING btree (profile_id) WHERE is_primary = true;

-- Image deduplication
CREATE INDEX idx_face_encodings_image_hash ON face_encodings USING btree (image_hash) WHERE image_hash IS NOT NULL;

-- Confidence-based filtering
CREATE INDEX idx_face_encodings_confidence ON face_encodings USING btree (confidence_threshold DESC);

-- For similarity searches (will need additional extensions for vector similarity)
-- Note: Consider using pgvector extension for cosine similarity searches on encoding_vector

-- ============================================================================
-- USER ACTIVITY LOGS INDEXES
-- ============================================================================

-- User activity tracking
CREATE INDEX idx_activity_logs_user_id ON user_activity_logs USING btree (user_id, created_at DESC);
CREATE INDEX idx_activity_logs_action ON user_activity_logs USING btree (action, created_at DESC);

-- Resource access patterns
CREATE INDEX idx_activity_logs_resource ON user_activity_logs USING btree (resource_type, resource_id, created_at DESC);

-- Security monitoring
CREATE INDEX idx_activity_logs_ip ON user_activity_logs USING btree (ip_address, created_at DESC);

-- ============================================================================
-- NOTIFICATIONS TABLE INDEXES
-- ============================================================================

-- User notification queries
CREATE INDEX idx_notifications_user_id ON notifications USING btree (user_id, created_at DESC);
CREATE INDEX idx_notifications_unread ON notifications USING btree (user_id, created_at DESC) WHERE is_read = false;

-- Notification type analysis
CREATE INDEX idx_notifications_type ON notifications USING btree (type, created_at DESC);

-- Email delivery tracking
CREATE INDEX idx_notifications_email_pending ON notifications USING btree (created_at ASC) 
    WHERE email_sent = false AND is_read = false;

-- ============================================================================
-- SYSTEM CONFIG INDEXES
-- ============================================================================

-- Fast config lookups
CREATE INDEX idx_system_config_updated ON system_config USING btree (updated_at DESC);

-- ============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Dashboard summary queries
CREATE INDEX idx_user_infringement_summary ON infringements USING btree (user_id, status, detected_date DESC);
CREATE INDEX idx_profile_infringement_summary ON infringements USING btree (profile_id, status, detected_date DESC);

-- DMCA effectiveness tracking
CREATE INDEX idx_dmca_effectiveness ON dmca_requests USING btree (user_id, status, sent_at DESC, response_received_at);

-- Scanning efficiency analysis
CREATE INDEX idx_scan_efficiency ON scan_history USING btree (scan_type, status, started_at, completed_at) 
    WHERE completed_at IS NOT NULL;

-- ============================================================================
-- PARTIAL INDEXES FOR BETTER PERFORMANCE
-- ============================================================================

-- Active user sessions only
CREATE UNIQUE INDEX idx_users_active_email ON users USING btree (email) WHERE is_active = true;

-- Current subscription tracking
CREATE INDEX idx_users_current_subscriptions ON users USING btree (subscription_tier, subscription_end_date) 
    WHERE is_active = true AND (subscription_end_date IS NULL OR subscription_end_date > CURRENT_TIMESTAMP);

-- Recent infringements (last 30 days)
CREATE INDEX idx_recent_infringements ON infringements USING btree (user_id, status, detected_at DESC) 
    WHERE detected_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Pending DMCA requests requiring action
CREATE INDEX idx_actionable_dmca ON dmca_requests USING btree (user_id, status, compliance_deadline ASC) 
    WHERE status IN ('sent', 'acknowledged') AND compliance_deadline IS NOT NULL;