# Database Setup and Troubleshooting Guide

## Overview

This guide covers the enhanced database configuration for the Content Protection Platform, including PostgreSQL driver compatibility fixes and performance optimizations.

## Fixed Issues

### PostgreSQL Driver Compatibility

**Problem**: `psycopg2-binary` installation fails on Windows with "pg_config executable not found" error.

**Solution**: Replaced with multiple compatible options:
- **Primary**: `asyncpg` for async PostgreSQL operations
- **Fallback**: `psycopg` (v3) with binary package
- **Alternative**: `psycopg2cffi` for Windows compatibility

### Enhanced Features

1. **Async Support**: Full SQLAlchemy 2.0 async support with optimized connection pooling
2. **Health Monitoring**: Comprehensive database health checks and metrics
3. **Connection Management**: Automatic retry logic and connection recovery
4. **Security**: SSL configuration, connection encryption, and query logging
5. **Performance**: Optimized pool settings and query monitoring

## Database Drivers

### Current Configuration

```python
# Primary async driver (best performance)
asyncpg==0.29.0

# Fallback sync driver (v3 - more compatible than psycopg2-binary)
psycopg[binary,pool]==3.1.13

# Windows-compatible alternative
psycopg2cffi==2.9.0
```

### Connection String Examples

```bash
# AsyncPG (Primary - Async)
postgresql+asyncpg://user:password@localhost:5432/dbname

# Psycopg3 (Fallback - Sync/Async)
postgresql+psycopg://user:password@localhost:5432/dbname

# Psycopg2cffi (Windows Alternative)
postgresql+psycopg2cffi://user:password@localhost:5432/dbname
```

## Environment Configuration

### Required Variables

```bash
# Basic Database Configuration
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_DB=autodmca
POSTGRES_PORT=5432

# Security Settings
POSTGRES_SSL_MODE=prefer
POSTGRES_CONNECT_TIMEOUT=30
POSTGRES_COMMAND_TIMEOUT=60

# Performance & Monitoring
DATABASE_QUERY_LOGGING=false
DATABASE_SLOW_QUERY_THRESHOLD=1.0
DATABASE_HEALTH_CHECK_INTERVAL=300
DATABASE_MAX_RETRIES=3
DATABASE_RETRY_DELAY=5
```

### SSL Configuration Options

- `disable`: No SSL connection
- `allow`: SSL preferred but not required
- `prefer`: SSL preferred (default)
- `require`: SSL required
- `verify-ca`: SSL required with CA verification
- `verify-full`: SSL required with full verification

## Database Setup Commands

### Using Python Management Script

```bash
# Check database connection
python -m app.db.startup check

# Initialize development database
python -m app.db.startup init

# Run migrations
python -m app.db.startup migrate

# Create new migration
python -m app.db.startup create-migration --message "Add new table"

# Reset database (WARNING: Deletes all data)
python -m app.db.startup reset
```

### Using Docker Compose

```bash
# Start database services
docker-compose up postgres redis -d

# Check service health
docker-compose ps

# View database logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U contentprotection -d content_protection
```

### Manual Setup

```bash
# Install requirements
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Create migration
alembic revision --autogenerate -m "Migration message"
```

## Health Check Endpoints

### `/health` - System Health

```json
{
  "system": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-01T00:00:00Z",
    "environment": "development"
  },
  "database": {
    "healthy": true,
    "response_time_ms": 12.34,
    "active_connections": 5,
    "pool_info": {
      "size": 20,
      "checked_in": 15,
      "checked_out": 5,
      "overflow": 0,
      "invalid": 0
    },
    "version": "PostgreSQL 15.4"
  }
}
```

### `/metrics` - Database Metrics

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "database_health": {
    "healthy": true,
    "response_time_ms": 12.34,
    "last_check": 1640995200.0
  },
  "connections": {
    "active_connections": 5,
    "connection_states": {
      "active": 5,
      "idle": 10
    },
    "slow_queries": []
  },
  "storage": {
    "database_size": "1.2 GB",
    "database_size_bytes": 1200000000,
    "largest_tables": [
      {
        "schema": "public",
        "table": "takedowns",
        "size": "500 MB",
        "size_bytes": 500000000
      }
    ]
  },
  "pool_status": {
    "size": 20,
    "checked_in": 15,
    "checked_out": 5
  }
}
```

## Connection Pool Configuration

### Default Settings

```python
{
    "pool_size": 20,              # Base connections
    "max_overflow": 30,           # Additional connections
    "pool_timeout": 30,           # Connection checkout timeout
    "pool_recycle": 3600,         # Connection lifetime (1 hour)
    "pool_pre_ping": True,        # Validate before use
    "echo": False,                # SQL logging (debug only)
    "echo_pool": False            # Pool logging (debug only)
}
```

### Environment-Specific Pools

- **Development**: `NullPool` (no pooling for easier debugging)
- **Production**: `QueuePool` (full connection pooling)
- **Testing**: `NullPool` (avoid connection conflicts)

## Troubleshooting

### Common Issues

#### 1. Driver Installation Failures

**Error**: `pg_config executable not found`

**Solutions**:
```bash
# Option 1: Use conda (recommended for Windows)
conda install psycopg2

# Option 2: Install PostgreSQL client tools
# Windows: Download from postgresql.org
# Ubuntu: apt-get install libpq-dev
# macOS: brew install postgresql

# Option 3: Use our fallback drivers
pip install psycopg[binary] psycopg2cffi
```

#### 2. Connection Timeout Issues

**Error**: `Connection timeout` or `Could not connect to server`

**Solutions**:
```bash
# Increase timeout values
POSTGRES_CONNECT_TIMEOUT=60
POSTGRES_COMMAND_TIMEOUT=120

# Check network connectivity
ping your-postgres-server

# Check PostgreSQL server status
docker-compose ps postgres
```

#### 3. SSL Certificate Issues

**Error**: `SSL certificate verify failed`

**Solutions**:
```bash
# Use less strict SSL mode
POSTGRES_SSL_MODE=prefer  # or 'allow' or 'disable'

# For development only - disable SSL
POSTGRES_SSL_MODE=disable
```

#### 4. Pool Exhaustion

**Error**: `QueuePool limit of size X overflow Y reached`

**Solutions**:
```python
# Increase pool settings in config
"pool_size": 30,
"max_overflow": 50,
"pool_timeout": 60
```

#### 5. Slow Query Performance

**Monitoring**:
```bash
# Check slow queries via API
curl http://localhost:8000/metrics

# Enable query logging (development only)
DATABASE_QUERY_LOGGING=true
DATABASE_SLOW_QUERY_THRESHOLD=0.5
```

### Database Performance Tips

1. **Indexing**: Create indexes for frequently queried columns
2. **Connection Pooling**: Use appropriate pool sizes for your workload
3. **Query Optimization**: Monitor slow queries via `/metrics` endpoint
4. **Regular Maintenance**: Run `VACUUM` and `ANALYZE` periodically
5. **Monitoring**: Use health check endpoints for continuous monitoring

### Recovery Procedures

#### Database Connection Lost

```python
# Automatic retry is built-in, but manual recovery:
from app.db.utils import wait_for_database, initialize_database

# Wait for database to become available
await wait_for_database(timeout=120)

# Re-initialize connection
await initialize_database()
```

#### Corrupted Connection Pool

```python
# Reset connection pool
from app.db.session import engine

await engine.dispose()
# Pool will be recreated on next request
```

## Performance Monitoring

### Key Metrics to Watch

1. **Response Time**: Database query response times
2. **Connection Count**: Active and idle connections
3. **Pool Usage**: Connection pool utilization
4. **Slow Queries**: Queries exceeding threshold
5. **Error Rate**: Connection and query failures

### Alerting Thresholds

- Response time > 1000ms (warning)
- Response time > 5000ms (critical)
- Active connections > 80% of pool size (warning)
- Pool exhaustion events (critical)
- Health check failures (critical)

## Migration Best Practices

1. **Backup First**: Always backup before migrations
2. **Test Migrations**: Run on development environment first
3. **Rollback Plan**: Prepare downgrade scripts for complex changes
4. **Monitor Performance**: Check query performance after schema changes
5. **Incremental Changes**: Make small, focused migrations

## Security Considerations

1. **SSL Connections**: Use SSL in production environments
2. **Credential Management**: Use environment variables, not hardcoded passwords
3. **Network Security**: Restrict database access to application servers only
4. **Query Logging**: Be careful with query logging in production (may log sensitive data)
5. **Connection Limits**: Set appropriate connection limits to prevent DoS

## Support and Debugging

### Enable Debug Logging

```bash
# Set in environment
LOG_LEVEL=DEBUG
DATABASE_QUERY_LOGGING=true

# Or in Python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Useful Database Queries

```sql
-- Check active connections
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Check database sizes
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check slow queries
SELECT query, query_start, state 
FROM pg_stat_activity 
WHERE state != 'idle' 
AND query_start < now() - interval '5 seconds';
```

For additional support, check the application logs and use the built-in health check endpoints.