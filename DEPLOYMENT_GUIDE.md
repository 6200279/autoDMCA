# Production Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the Content Protection Platform to production using Docker containers, with comprehensive monitoring, security, and scalability.

## Prerequisites

### System Requirements
- **Server**: Linux-based system (Ubuntu 22.04 LTS recommended)
- **RAM**: Minimum 8GB, Recommended 16GB+
- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Storage**: Minimum 100GB SSD, Recommended 500GB+ SSD
- **Network**: High-speed internet connection with static IP

### Required Software
- Docker (v24.0+)
- Docker Compose (v2.20+)
- Git
- OpenSSL for SSL certificates
- Domain name with DNS access

## Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/autoDMCA.git
cd autoDMCA
```

### 2. Create Environment Variables
Copy the example environment file and configure:
```bash
cp .env.example .env.production
```

Edit `.env.production` with your production values:
```bash
# Database
POSTGRES_PASSWORD=your-secure-database-password

# Redis
REDIS_PASSWORD=your-secure-redis-password

# Application Security
SECRET_KEY=your-256-bit-secret-key
WATERMARK_KEY=your-watermark-encryption-key

# Email/SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# API Keys
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CUSTOM_SEARCH_ID=your-custom-search-id
BING_API_KEY=your-bing-search-api-key

# Payment Processing
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable-key

# Monitoring
GRAFANA_PASSWORD=your-grafana-admin-password

# Domain Configuration
FRONTEND_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com
```

### 3. SSL Certificate Setup
Generate SSL certificates using Let's Encrypt:
```bash
# Install certbot
sudo apt update
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com

# Copy certificates to nginx directory
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

### 4. Update Domain Configuration
Edit the following files to replace placeholder domains:
- `nginx/nginx.conf`
- `docker-compose.production.yml`
- Frontend environment variables

## Database Migration

### 1. Create Initial Database
```bash
# Start only PostgreSQL for initial setup
docker-compose -f docker-compose.production.yml up -d postgres

# Wait for database to be ready
sleep 30

# Run database migrations
docker-compose -f docker-compose.production.yml run --rm backend python -m alembic upgrade head
```

### 2. Create Superuser Account
```bash
docker-compose -f docker-compose.production.yml run --rm backend python -c "
from app.db.init_db import init_db
from app.db.session import SessionLocal
init_db(SessionLocal())
"
```

## Production Deployment

### 1. Build and Start All Services
```bash
# Build production images
docker-compose -f docker-compose.production.yml build

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Verify all services are running
docker-compose -f docker-compose.production.yml ps
```

### 2. Verify Service Health
```bash
# Check backend health
curl https://api.yourdomain.com/health

# Check frontend accessibility
curl https://yourdomain.com

# Check database connection
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected:', result.fetchone())
"
```

### 3. Initialize Scanning Services
```bash
# Start the scanning scheduler
docker-compose -f docker-compose.production.yml exec backend python -c "
import asyncio
from app.services.scanning.scheduler import ScanningScheduler
async def init():
    scheduler = ScanningScheduler()
    await scheduler.initialize()
    print('Scheduler initialized')
asyncio.run(init())
"
```

## Monitoring Setup

### 1. Access Monitoring Dashboards
- **Grafana**: https://yourdomain.com:3001 (admin / your-grafana-password)
- **Prometheus**: https://yourdomain.com:9090
- **Kibana**: https://yourdomain.com:5601

### 2. Configure Alerting
Edit `monitoring/prometheus.yml` to add alerting rules:
```yaml
rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 3. Set Up Log Aggregation
Logs are automatically collected by the ELK stack:
- Application logs → Logstash → Elasticsearch → Kibana
- Access monitoring through Kibana dashboard

## Security Hardening

### 1. Firewall Configuration
```bash
# Install UFW
sudo apt install ufw

# Allow essential ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Deny all other traffic
sudo ufw --force enable
```

### 2. Docker Security
```bash
# Create non-root user for docker
sudo groupadd docker
sudo usermod -aG docker $USER

# Set proper permissions
sudo chown -R $USER:$USER nginx/ssl
sudo chmod 600 nginx/ssl/key.pem
sudo chmod 644 nginx/ssl/cert.pem
```

### 3. Database Security
```bash
# Connect to database and create read-only user
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d contentprotection -c "
CREATE USER readonly WITH PASSWORD 'readonly-password';
GRANT CONNECT ON DATABASE contentprotection TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
"
```

## Backup Strategy

### 1. Database Backups
Create automated backup script:
```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="contentprotection"

# Create backup
docker-compose -f docker-compose.production.yml exec -T postgres pg_dump -U postgres $DB_NAME > "$BACKUP_DIR/db_backup_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# Remove backups older than 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
```

### 2. File System Backups
```bash
# Backup uploads and logs
tar -czf backups/files_backup_$(date +%Y%m%d).tar.gz uploads logs

# Upload to cloud storage (example with AWS S3)
aws s3 cp backups/ s3://your-backup-bucket/content-protection/ --recursive
```

### 3. Schedule Backups
```bash
# Add to crontab
crontab -e

# Add these lines:
0 2 * * * /path/to/scripts/backup.sh
0 3 * * 0 /path/to/scripts/backup_files.sh
```

## Performance Optimization

### 1. Database Optimization
```sql
-- Connect to database and optimize
-- docker-compose exec postgres psql -U postgres -d contentprotection

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_infringements_created_at ON infringements(created_at DESC);
CREATE INDEX CONCURRENTLY idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX CONCURRENTLY idx_takedown_notices_status ON takedown_notices(status);

-- Analyze tables
ANALYZE;
```

### 2. Redis Configuration
Add to redis configuration:
```bash
# In docker-compose.production.yml, add to redis service:
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru --save 900 1
```

### 3. Application Performance
```bash
# Enable production optimizations in backend
export PYTHONOPTIMIZE=2
export PYTHONDONTWRITEBYTECODE=1

# Use multiple workers
# Already configured in Dockerfile.production with --workers 4
```

## Scaling Configuration

### 1. Horizontal Scaling
To scale the backend service:
```bash
docker-compose -f docker-compose.production.yml up -d --scale backend=3 --scale celery-worker=6
```

### 2. Load Balancer Configuration
Nginx is already configured for load balancing multiple backend instances.

### 3. Database Scaling
For high-traffic scenarios, consider:
- Read replicas for PostgreSQL
- Connection pooling with PgBouncer
- Partitioning large tables

## Troubleshooting

### 1. Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs backend
docker-compose -f docker-compose.production.yml logs frontend

# Check resource usage
docker stats
```

**Database connection issues:**
```bash
# Test database connectivity
docker-compose -f docker-compose.production.yml exec postgres pg_isready

# Check database logs
docker-compose -f docker-compose.production.yml logs postgres
```

**SSL certificate issues:**
```bash
# Verify certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect yourdomain.com:443
```

### 2. Performance Issues
```bash
# Monitor resource usage
htop
docker stats

# Check application performance
docker-compose -f docker-compose.production.yml exec backend python -c "
import psutil
print(f'CPU: {psutil.cpu_percent()}%')
print(f'RAM: {psutil.virtual_memory().percent}%')
"
```

### 3. Log Analysis
```bash
# View application logs
docker-compose -f docker-compose.production.yml logs -f backend

# Access Kibana for advanced log analysis
# Navigate to https://yourdomain.com:5601
```

## Maintenance

### 1. Regular Updates
```bash
# Update Docker images
docker-compose -f docker-compose.production.yml pull

# Rebuild and restart services
docker-compose -f docker-compose.production.yml up -d --build
```

### 2. SSL Certificate Renewal
```bash
# Renew certificates (set up cron job)
certbot renew --quiet

# Update nginx certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# Restart nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### 3. Database Maintenance
```bash
# Monthly database maintenance
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d contentprotection -c "
VACUUM ANALYZE;
REINDEX DATABASE contentprotection;
"
```

## Monitoring and Alerts

### 1. Health Checks
Set up external monitoring services to check:
- API endpoint health: `https://api.yourdomain.com/health`
- Frontend accessibility: `https://yourdomain.com`
- Database connectivity
- SSL certificate expiration

### 2. Performance Metrics
Monitor these key metrics:
- Response times
- Error rates
- Database query performance
- Queue sizes
- Memory and CPU usage

### 3. Business Metrics
Track application-specific metrics:
- Number of scans completed
- Takedowns sent
- Content removed
- User activity

## Security Maintenance

### 1. Regular Security Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Docker images
docker-compose -f docker-compose.production.yml pull
```

### 2. Security Scanning
```bash
# Scan Docker images for vulnerabilities
docker scout quickview
docker scout cves
```

### 3. Access Control Review
- Regularly review user permissions
- Rotate API keys and passwords
- Monitor access logs for suspicious activity

## Support and Maintenance Contacts

**Emergency Contacts:**
- System Administrator: [contact info]
- Database Administrator: [contact info]
- Security Team: [contact info]

**Vendor Support:**
- Cloud Provider Support
- Certificate Authority Support
- Third-party API Support (Google, Bing, Stripe)

---

This deployment guide provides a comprehensive setup for production use. Always test deployments in a staging environment before applying to production.