-- Database Optimization and Monitoring Queries
-- Use these queries to monitor performance and identify optimization opportunities
-- Created: 2025-08-07

-- ============================================================================
-- TABLE SIZE AND GROWTH MONITORING
-- ============================================================================

-- Check table sizes and row counts
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size,
    (SELECT reltuples::bigint FROM pg_class WHERE relname = tablename) AS estimated_rows
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor partition sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT reltuples::bigint FROM pg_class WHERE relname = tablename) AS estimated_rows
FROM pg_tables 
WHERE schemaname = 'public' 
AND (tablename LIKE 'infringements_%' 
     OR tablename LIKE 'scan_history_%' 
     OR tablename LIKE 'dmca_requests_%' 
     OR tablename LIKE 'user_activity_logs_%')
ORDER BY tablename;

-- ============================================================================
-- INDEX USAGE ANALYSIS
-- ============================================================================

-- Find unused indexes (potential candidates for removal)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_stat_user_indexes 
WHERE idx_tup_read = 0 
AND idx_tup_fetch = 0
AND schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Index hit ratio (should be > 95%)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    CASE 
        WHEN idx_tup_read = 0 THEN 0
        ELSE (idx_tup_fetch::float / idx_tup_read::float * 100)::decimal(5,2)
    END AS hit_ratio_percent
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
AND idx_tup_read > 0
ORDER BY hit_ratio_percent ASC;

-- Most frequently used indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 20;

-- ============================================================================
-- QUERY PERFORMANCE MONITORING
-- ============================================================================

-- Slow queries (requires pg_stat_statements extension)
-- Enable with: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
/*
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE query LIKE '%infringements%' OR query LIKE '%dmca_requests%'
ORDER BY mean_time DESC
LIMIT 10;
*/

-- Long-running queries
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active';

-- ============================================================================
-- SUBSCRIPTION AND USAGE ANALYTICS
-- ============================================================================

-- User distribution by subscription tier
SELECT 
    subscription_tier,
    COUNT(*) AS user_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage
FROM users 
WHERE is_active = true
GROUP BY subscription_tier;

-- Profile usage by subscription tier
SELECT 
    u.subscription_tier,
    COUNT(DISTINCT pp.id) AS total_profiles,
    AVG(profile_count.cnt) AS avg_profiles_per_user,
    MAX(profile_count.cnt) AS max_profiles_per_user
FROM users u
LEFT JOIN (
    SELECT user_id, COUNT(*) as cnt 
    FROM protected_profiles 
    WHERE status = 'active' 
    GROUP BY user_id
) profile_count ON u.id = profile_count.user_id
WHERE u.is_active = true
GROUP BY u.subscription_tier;

-- ============================================================================
-- INFRINGEMENT DETECTION ANALYTICS
-- ============================================================================

-- Infringement detection rates by platform
SELECT 
    platform,
    COUNT(*) AS total_infringements,
    COUNT(*) FILTER (WHERE status = 'verified') AS verified_count,
    COUNT(*) FILTER (WHERE status = 'removed') AS removed_count,
    AVG(confidence_score)::decimal(3,2) AS avg_confidence,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS platform_percentage
FROM infringements 
WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY platform
ORDER BY total_infringements DESC;

-- Daily infringement detection trends
SELECT 
    detected_at::date AS date,
    COUNT(*) AS infringements_detected,
    COUNT(*) FILTER (WHERE confidence_score >= 0.80) AS high_confidence,
    AVG(confidence_score)::decimal(3,2) AS avg_confidence
FROM infringements 
WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY detected_at::date
ORDER BY date DESC;

-- Top users by infringement volume
SELECT 
    u.email,
    u.subscription_tier,
    COUNT(i.id) AS total_infringements,
    COUNT(i.id) FILTER (WHERE i.status = 'verified') AS verified_infringements,
    COUNT(DISTINCT i.platform) AS platforms_affected
FROM users u
JOIN infringements i ON u.id = i.user_id
WHERE i.detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY u.id, u.email, u.subscription_tier
ORDER BY total_infringements DESC
LIMIT 10;

-- ============================================================================
-- DMCA EFFECTIVENESS ANALYTICS
-- ============================================================================

-- DMCA request success rates by platform
SELECT 
    platform,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE status = 'complied') AS complied_count,
    COUNT(*) FILTER (WHERE status = 'rejected') AS rejected_count,
    COUNT(*) FILTER (WHERE status = 'expired') AS expired_count,
    (COUNT(*) FILTER (WHERE status = 'complied')::float / COUNT(*)::float * 100)::decimal(5,2) AS success_rate_percent
FROM dmca_requests 
WHERE sent_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY platform
ORDER BY success_rate_percent DESC;

-- Average response times by platform
SELECT 
    platform,
    COUNT(*) FILTER (WHERE response_received_at IS NOT NULL) AS responses_received,
    AVG(EXTRACT(EPOCH FROM (response_received_at - sent_at)) / 3600)::decimal(5,2) AS avg_response_hours,
    MIN(EXTRACT(EPOCH FROM (response_received_at - sent_at)) / 3600)::decimal(5,2) AS min_response_hours,
    MAX(EXTRACT(EPOCH FROM (response_received_at - sent_at)) / 3600)::decimal(5,2) AS max_response_hours
FROM dmca_requests 
WHERE sent_at IS NOT NULL 
AND response_received_at IS NOT NULL
AND sent_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY platform
ORDER BY avg_response_hours ASC;

-- ============================================================================
-- SYSTEM PERFORMANCE MONITORING
-- ============================================================================

-- Table bloat analysis
SELECT 
    schemaname,
    tablename,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    CASE 
        WHEN n_live_tup = 0 THEN 0
        ELSE (n_dead_tup::float / n_live_tup::float * 100)::decimal(5,2)
    END AS bloat_percentage
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;

-- Vacuum and analyze recommendations
SELECT 
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    n_tup_ins + n_tup_upd + n_tup_del AS total_modifications,
    CASE 
        WHEN last_autovacuum IS NULL AND last_vacuum IS NULL THEN 'URGENT: Never vacuumed'
        WHEN COALESCE(last_autovacuum, last_vacuum) < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'HIGH: Vacuum overdue'
        WHEN COALESCE(last_autoanalyze, last_analyze) < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'MEDIUM: Analyze recommended'
        ELSE 'LOW: Recently maintained'
    END AS maintenance_priority
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY 
    CASE 
        WHEN last_autovacuum IS NULL AND last_vacuum IS NULL THEN 1
        WHEN COALESCE(last_autovacuum, last_vacuum) < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 2
        WHEN COALESCE(last_autoanalyze, last_analyze) < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 3
        ELSE 4
    END,
    total_modifications DESC;

-- Connection and lock monitoring
SELECT 
    datname,
    numbackends AS connections,
    xact_commit AS transactions_committed,
    xact_rollback AS transactions_rolled_back,
    blks_read AS disk_blocks_read,
    blks_hit AS buffer_hits,
    (blks_hit::float / (blks_hit + blks_read)::float * 100)::decimal(5,2) AS cache_hit_ratio
FROM pg_stat_database 
WHERE datname = current_database();

-- Active locks (potential blocking queries)
SELECT 
    pg_stat_activity.pid,
    pg_stat_activity.query,
    pg_locks.mode,
    pg_locks.locktype,
    pg_locks.relation::regclass AS relation
FROM pg_locks
JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
WHERE NOT pg_locks.granted
ORDER BY pg_stat_activity.query_start;

-- ============================================================================
-- MAINTENANCE SCRIPTS
-- ============================================================================

-- Manual vacuum and analyze for high-traffic tables
/*
VACUUM ANALYZE infringements;
VACUUM ANALYZE dmca_requests;
VACUUM ANALYZE scan_history;
VACUUM ANALYZE user_activity_logs;
*/

-- Reindex heavily used indexes (during maintenance window)
/*
REINDEX INDEX CONCURRENTLY idx_infringements_user_status;
REINDEX INDEX CONCURRENTLY idx_infringements_profile_status;
REINDEX INDEX CONCURRENTLY idx_dmca_user_id;
*/

-- Update table statistics
/*
ANALYZE users;
ANALYZE protected_profiles;
ANALYZE infringements;
ANALYZE dmca_requests;
*/