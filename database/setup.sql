-- Content Protection Platform Database Setup
-- Complete database initialization script
-- Created: 2025-08-07
-- 
-- Usage:
--   psql -h localhost -U postgres -d content_protection -f setup.sql
--
-- Prerequisites:
--   1. PostgreSQL 13+ installed
--   2. Database 'content_protection' created
--   3. User with appropriate permissions

\echo 'Starting Content Protection Platform database setup...'
\echo ''

-- Set error handling
\set ON_ERROR_STOP on
\timing on

-- Show current database and connection info
SELECT 
    current_database() AS database,
    current_user AS user,
    version() AS postgresql_version;

\echo ''
\echo '================================================='
\echo 'STEP 1: Running initial schema migration (001)'
\echo '================================================='

\i migrations/001_initial_schema.sql

\echo ''
\echo '================================================='
\echo 'STEP 2: Creating performance indexes (002)'
\echo '================================================='

\i migrations/002_create_indexes.sql

\echo ''
\echo '================================================='
\echo 'STEP 3: Setting up table partitions (003)'
\echo '================================================='

\i migrations/003_create_partitions.sql

\echo ''
\echo '================================================='
\echo 'STEP 4: Adding business constraints and triggers'
\echo '================================================='

\i constraints.sql

\echo ''
\echo '================================================='
\echo 'STEP 5: Inserting initial configuration data'
\echo '================================================='

-- Insert system configuration defaults
INSERT INTO system_config (key, value, description) VALUES
('face_recognition_threshold', '0.80', 'Minimum confidence threshold for face recognition matches'),
('max_scan_threads', '4', 'Maximum number of concurrent scanning threads'),
('dmca_response_timeout_days', '14', 'Number of days to wait for DMCA response before marking as expired'),
('notification_email_enabled', 'true', 'Whether to send email notifications'),
('auto_verify_high_confidence', 'true', 'Automatically verify infringements with confidence >= 0.95'),
('partition_retention_months', '12', 'Number of months to retain partitioned data'),
('scan_frequency_hours', '24', 'Default hours between profile scans'),
('max_infringements_per_dmca', '10', 'Maximum number of infringements to include in single DMCA request')
ON CONFLICT (key) DO NOTHING;

\echo 'Inserted system configuration defaults'

-- Create initial admin user (password should be changed immediately)
INSERT INTO users (
    email, 
    password_hash, 
    first_name, 
    last_name, 
    subscription_tier, 
    subscription_price,
    is_active, 
    email_verified
) VALUES (
    'admin@contentprotection.com',
    crypt('admin123!', gen_salt('bf')), -- Use bcrypt hashing
    'System',
    'Administrator',
    'professional',
    99.00,
    true,
    true
) ON CONFLICT (email) DO NOTHING;

\echo 'Created default admin user (email: admin@contentprotection.com, password: admin123!)'
\echo 'WARNING: Change the admin password immediately!'

\echo ''
\echo '================================================='
\echo 'STEP 6: Database setup validation'
\echo '================================================='

-- Verify all tables were created
SELECT 
    COUNT(*) AS table_count,
    string_agg(tablename, ', ' ORDER BY tablename) AS tables
FROM pg_tables 
WHERE schemaname = 'public'
AND tablename NOT LIKE '%_2024_%'
AND tablename NOT LIKE '%_2025_%';

-- Verify all indexes were created
SELECT 
    COUNT(*) AS index_count
FROM pg_indexes 
WHERE schemaname = 'public';

-- Verify partitions were created
SELECT 
    COUNT(*) AS partition_count
FROM pg_tables 
WHERE schemaname = 'public'
AND (tablename LIKE '%_2024_%' OR tablename LIKE '%_2025_%');

-- Check extensions
SELECT 
    extname AS extension_name,
    extversion AS version
FROM pg_extension 
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'pg_trgm');

-- Verify triggers and functions
SELECT 
    COUNT(*) AS trigger_count
FROM information_schema.triggers 
WHERE trigger_schema = 'public';

SELECT 
    COUNT(*) AS function_count
FROM information_schema.routines 
WHERE routine_schema = 'public'
AND routine_type = 'FUNCTION';

\echo ''
\echo '================================================='
\echo 'STEP 7: Performance recommendations'
\echo '================================================='

-- Show PostgreSQL configuration recommendations
\echo 'Current PostgreSQL configuration:'
SELECT name, setting, unit, short_desc 
FROM pg_settings 
WHERE name IN (
    'shared_buffers',
    'work_mem',
    'maintenance_work_mem',
    'effective_cache_size',
    'random_page_cost',
    'checkpoint_completion_target',
    'wal_buffers',
    'default_statistics_target'
)
ORDER BY name;

\echo ''
\echo 'Recommended settings for content protection platform:'
\echo '  shared_buffers = 256MB (or 25% of RAM)'
\echo '  work_mem = 4MB'
\echo '  maintenance_work_mem = 64MB'
\echo '  effective_cache_size = 1GB (or 75% of RAM)'
\echo '  random_page_cost = 1.1 (for SSD storage)'
\echo '  checkpoint_completion_target = 0.9'
\echo '  wal_buffers = 16MB'
\echo '  default_statistics_target = 100'
\echo ''
\echo 'Add these to postgresql.conf and restart PostgreSQL for optimal performance.'

\echo ''
\echo '================================================='
\echo 'SETUP COMPLETE!'
\echo '================================================='
\echo ''
\echo 'Database setup completed successfully!'
\echo ''
\echo 'Next steps:'
\echo '1. Change the admin password: UPDATE users SET password_hash = crypt(''new_password'', gen_salt(''bf'')) WHERE email = ''admin@contentprotection.com'';'
\echo '2. Configure PostgreSQL settings (see recommendations above)'
\echo '3. Set up monitoring and alerting'
\echo '4. Schedule regular maintenance (VACUUM, ANALYZE)'
\echo '5. Implement backup strategy'
\echo ''
\echo 'Useful maintenance commands:'
\echo '  - View table sizes: \\i optimization_queries.sql'
\echo '  - Create new partition: SELECT create_monthly_partition(''infringements'', ''2025-09-01'');'
\echo '  - Drop old partitions: SELECT drop_old_partition(''infringements'', 12);'
\echo ''

-- Show migration status
SELECT 
    version,
    description,
    executed_at,
    execution_time_ms || ' ms' AS execution_time
FROM schema_migrations 
ORDER BY version;

\timing off