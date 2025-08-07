# Content Protection Platform Database

A high-performance PostgreSQL database schema optimized for content protection and DMCA takedown management.

## 🏗️ Architecture Overview

### Core Tables
- **users** - User accounts with subscription tiers (Basic $49, Professional $89-99)
- **protected_profiles** - Profiles to monitor (1 for Basic, 5 for Professional)
- **infringements** - Detected content violations with confidence scoring
- **dmca_requests** - DMCA takedown requests and responses
- **face_encodings** - Face recognition data for matching
- **whitelisted_urls** - URLs to skip during scanning
- **scan_history** - Scanning operations log
- **notifications** - User notification system
- **user_activity_logs** - Audit trail for user actions

### Partitioning Strategy
High-volume tables are partitioned by date for optimal performance:
- `infringements` - Partitioned by `detected_date`
- `scan_history` - Partitioned by `created_date`
- `dmca_requests` - Partitioned by `created_at`
- `user_activity_logs` - Partitioned by `created_at`

## 🚀 Quick Start

### Prerequisites
- PostgreSQL 13+
- Database created: `CREATE DATABASE content_protection;`

### Installation
```bash
# Navigate to database directory
cd database/

# Run complete setup
psql -h localhost -U postgres -d content_protection -f setup.sql
```

### Manual Step-by-Step
```bash
# 1. Initial schema
psql -d content_protection -f migrations/001_initial_schema.sql

# 2. Create indexes
psql -d content_protection -f migrations/002_create_indexes.sql

# 3. Set up partitions
psql -d content_protection -f migrations/003_create_partitions.sql

# 4. Add constraints
psql -d content_protection -f constraints.sql
```

## 📊 Performance Optimizations

### Indexes
- **B-tree indexes** for exact matches and range queries
- **GIN indexes** for JSONB metadata and array columns
- **Hash indexes** for URL deduplication
- **Partial indexes** for filtered queries (active users, recent data)
- **Composite indexes** for complex dashboard queries

### Query Performance Features
- Partitioning eliminates scanning old data
- Constraint exclusion on partition keys
- Statistics targets optimized for query patterns
- Trigram indexes for fuzzy text matching

### Expected Performance
- User dashboard queries: < 50ms
- Infringement searches: < 100ms
- DMCA status updates: < 25ms
- Face similarity matching: < 200ms

## 🔧 Database Maintenance

### Partition Management
```sql
-- Create new monthly partition
SELECT create_monthly_partition('infringements', '2025-09-01');

-- Drop old partitions (keep 12 months)
SELECT drop_old_partition('infringements', 12);
```

### Monitoring
```bash
# Run optimization queries
psql -d content_protection -f optimization_queries.sql
```

Key metrics to monitor:
- Table sizes and growth rates
- Index usage statistics
- Query performance (pg_stat_statements)
- Partition maintenance schedules

### Regular Maintenance
```sql
-- Update statistics (weekly)
ANALYZE users, protected_profiles, infringements, dmca_requests;

-- Vacuum high-traffic tables (as needed)
VACUUM ANALYZE infringements;
VACUUM ANALYZE dmca_requests;

-- Reindex if fragmentation > 20% (during maintenance window)
REINDEX INDEX CONCURRENTLY idx_infringements_user_status;
```

## 🛡️ Security Features

### Data Protection
- Password hashing with bcrypt
- Email validation constraints
- Subscription tier validation
- Profile limit enforcement

### Business Rules (Triggers)
- Automatic subscription limit checking
- DMCA request deduplication
- Face encoding validation
- Activity logging for audit

### Optional Row-Level Security
Enable RLS policies in `constraints.sql` for multi-tenant isolation.

## 📈 Scaling Considerations

### Current Capacity
- **Basic users**: 10,000+ concurrent users
- **Infringements**: 1M+ records per month
- **Scans**: 100K+ operations per day
- **DMCA requests**: 50K+ per month

### Horizontal Scaling Options
1. **Read replicas** for reporting and analytics
2. **Connection pooling** (PgBouncer recommended)
3. **Partition pruning** for time-based queries
4. **Archival strategy** for old partitions

### Monitoring Thresholds
- Disk usage > 80%
- Cache hit ratio < 95%
- Average query time > 100ms
- Connection count > 80% of max

## 🔄 Migration System

### Current Migrations
1. `001_initial_schema.sql` - Core table structure
2. `002_create_indexes.sql` - Performance indexes
3. `003_create_partitions.sql` - Table partitioning

### Rollback Support
```bash
# Rollback specific migration
psql -d content_protection -f rollbacks/rollback_003.sql
psql -d content_protection -f rollbacks/rollback_002.sql
psql -d content_protection -f rollbacks/rollback_001.sql  # ⚠️ Destroys all data
```

### Adding New Migrations
1. Create migration file: `004_new_feature.sql`
2. Add rollback file: `rollbacks/rollback_004.sql`
3. Update migration tracking in schema_migrations table

## 📋 Configuration

### System Settings
Key configuration values in `system_config` table:
- `face_recognition_threshold`: 0.80
- `max_scan_threads`: 4
- `dmca_response_timeout_days`: 14
- `auto_verify_high_confidence`: true
- `partition_retention_months`: 12

### PostgreSQL Recommendations
```ini
# postgresql.conf optimizations
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB
random_page_cost = 1.1
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## 🐛 Troubleshooting

### Common Issues

**Slow queries**
```sql
-- Check query performance
SELECT query, mean_time, calls FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
```

**High disk usage**
```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Lock contention**
```sql
-- Check for blocking queries
SELECT pid, query, state, wait_event 
FROM pg_stat_activity WHERE wait_event IS NOT NULL;
```

### Performance Tuning
1. **Identify slow queries** with `pg_stat_statements`
2. **Analyze execution plans** with `EXPLAIN ANALYZE`
3. **Check index usage** with optimization queries
4. **Monitor partition pruning** effectiveness
5. **Validate constraint exclusion** is working

## 📞 Support

### Database Files
- `schema.sql` - Complete schema definition
- `indexes.sql` - All performance indexes
- `constraints.sql` - Business rules and triggers
- `optimization_queries.sql` - Monitoring and analysis queries
- `setup.sql` - Complete installation script

### Migration Files
- `migrations/` - Forward migrations
- `rollbacks/` - Rollback scripts

For additional support, refer to the optimization queries for performance monitoring and maintenance recommendations.