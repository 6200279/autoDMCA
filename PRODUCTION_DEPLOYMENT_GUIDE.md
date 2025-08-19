# Production Deployment Guide - Content Protection Platform

## Overview
This guide provides step-by-step instructions for deploying the Content Protection Platform to production. Follow these instructions carefully to ensure a secure and reliable deployment.

## Prerequisites
- Ubuntu 20.04+ or CentOS 8+ server with 4GB+ RAM
- Docker and Docker Compose installed
- Domain name registered and DNS access
- External API accounts (Google, Bing, Stripe, etc.)

---

## 1. Domain and DNS Configuration

### 1.1 Domain Setup
Register a domain for your platform (e.g., `contentprotection.com`)

**Required DNS Records:**
```
# Main domain
A     contentprotection.com          → [YOUR_SERVER_IP]
A     www.contentprotection.com      → [YOUR_SERVER_IP]

# API subdomain  
A     api.contentprotection.com      → [YOUR_SERVER_IP]

# Admin/monitoring subdomains
A     admin.contentprotection.com    → [YOUR_SERVER_IP]
A     grafana.contentprotection.com  → [YOUR_SERVER_IP]
A     kibana.contentprotection.com   → [YOUR_SERVER_IP]

# Email (optional)
MX    contentprotection.com          → mail.contentprotection.com (10)
A     mail.contentprotection.com     → [YOUR_SERVER_IP]

# CAA record for SSL certificate authority
CAA   contentprotection.com          → 0 issue "letsencrypt.org"
```

### 1.2 SSL Certificate Setup

**Option A: Let's Encrypt (Recommended for production)**
```bash
# Install Certbot
sudo apt update
sudo apt install certbot

# Stop any running web services
sudo systemctl stop nginx apache2 || true

# Request SSL certificates for all domains
sudo certbot certonly --standalone \
  -d contentprotection.com \
  -d www.contentprotection.com \
  -d api.contentprotection.com \
  -d admin.contentprotection.com \
  -d grafana.contentprotection.com \
  -d kibana.contentprotection.com \
  --email admin@contentprotection.com \
  --agree-tos \
  --non-interactive

# Set up automatic renewal
echo "0 0,12 * * * root certbot renew --quiet" | sudo tee -a /etc/crontab > /dev/null
```

**Option B: Commercial SSL Certificate**
If using a commercial SSL certificate, place the files in:
```
ssl/
├── cert.pem        # Full certificate chain
├── key.pem         # Private key
└── dhparam.pem     # Diffie-Hellman parameters (generate with: openssl dhparam -out dhparam.pem 2048)
```

---

## 2. Server Setup and Security

### 2.1 Basic Server Hardening
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Create application user
sudo useradd -m -s /bin/bash contentprotection
sudo usermod -aG docker contentprotection

# Configure firewall
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw --force enable

# Disable root SSH login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Install fail2ban for SSH protection
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2.2 Docker Installation
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

---

## 3. Application Deployment

### 3.1 Clone and Setup Repository
```bash
# Switch to application user
sudo su - contentprotection

# Clone repository
git clone https://github.com/yourusername/autoDMCA.git
cd autoDMCA

# Create SSL directory and copy certificates
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/contentprotection.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/contentprotection.com/privkey.pem nginx/ssl/key.pem
sudo chown -R contentprotection:contentprotection nginx/ssl
sudo chmod 600 nginx/ssl/*.pem
```

### 3.2 Environment Configuration
```bash
# Copy environment templates
cp .env.example .env.production
cp frontend/.env.example frontend/.env.production

# Edit backend environment
nano .env.production
```

**Backend Environment (.env.production):**
```bash
# Database Configuration
POSTGRES_PASSWORD=YOUR_SECURE_DB_PASSWORD_HERE
DATABASE_URL=postgresql://postgres:YOUR_SECURE_DB_PASSWORD_HERE@postgres:5432/contentprotection

# Redis Configuration
REDIS_PASSWORD=YOUR_SECURE_REDIS_PASSWORD_HERE
REDIS_URL=redis://:YOUR_SECURE_REDIS_PASSWORD_HERE@redis:6379

# Application Security
SECRET_KEY=YOUR_256_BIT_SECRET_KEY_HERE
WATERMARK_KEY=YOUR_WATERMARK_ENCRYPTION_KEY_HERE
ENVIRONMENT=production

# Domain Configuration
FRONTEND_URL=https://contentprotection.com
API_URL=https://api.contentprotection.com
WEBSOCKET_URL=wss://api.contentprotection.com/ws

# Email/SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@contentprotection.com
SMTP_PASSWORD=YOUR_SMTP_APP_PASSWORD_HERE
EMAIL_FROM_NAME=Content Protection Platform
EMAIL_FROM_ADDRESS=noreply@contentprotection.com

# API Keys for Search Engines
GOOGLE_API_KEY=YOUR_GOOGLE_CUSTOM_SEARCH_API_KEY
GOOGLE_CUSTOM_SEARCH_ID=YOUR_GOOGLE_CUSTOM_SEARCH_ENGINE_ID
BING_API_KEY=YOUR_BING_WEB_SEARCH_API_KEY

# Payment Processing (Stripe)
STRIPE_SECRET_KEY=sk_live_YOUR_STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET

# Social Media API Keys
TWITTER_API_KEY=YOUR_TWITTER_API_KEY
TWITTER_API_SECRET=YOUR_TWITTER_API_SECRET
FACEBOOK_APP_ID=YOUR_FACEBOOK_APP_ID
FACEBOOK_APP_SECRET=YOUR_FACEBOOK_APP_SECRET
INSTAGRAM_ACCESS_TOKEN=YOUR_INSTAGRAM_ACCESS_TOKEN

# Monitoring & Logging
GRAFANA_PASSWORD=YOUR_GRAFANA_ADMIN_PASSWORD
LOG_LEVEL=INFO
ENABLE_METRICS=true

# Security Settings
ALLOWED_HOSTS=contentprotection.com,api.contentprotection.com,www.contentprotection.com
CORS_ORIGINS=https://contentprotection.com,https://www.contentprotection.com
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# External Services
WHOIS_API_KEY=YOUR_WHOIS_API_KEY
CLOUDFLARE_API_KEY=YOUR_CLOUDFLARE_API_KEY
CLOUDFLARE_ZONE_ID=YOUR_CLOUDFLARE_ZONE_ID
```

**Frontend Environment (frontend/.env.production):**
```bash
# API Configuration
REACT_APP_API_BASE_URL=https://api.contentprotection.com/api/v1
REACT_APP_WS_URL=wss://api.contentprotection.com/ws

# Environment
NODE_ENV=production

# App Configuration
REACT_APP_APP_NAME=Content Protection Platform
REACT_APP_VERSION=1.0.0

# Payment Integration
REACT_APP_STRIPE_PUBLIC_KEY=pk_live_YOUR_STRIPE_PUBLISHABLE_KEY

# External Services
REACT_APP_GOOGLE_ANALYTICS_ID=GA-XXXXXXXXX
REACT_APP_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Security
REACT_APP_ENABLE_HTTPS_ONLY=true
REACT_APP_ENABLE_CSP=true
```

### 3.3 Update Nginx Configuration
```bash
# Edit nginx configuration with your domain
nano nginx/nginx.conf
```

Update the server_name directives:
```nginx
server_name contentprotection.com www.contentprotection.com;
server_name api.contentprotection.com;
server_name grafana.contentprotection.com;
server_name kibana.contentprotection.com;
```

### 3.4 Update Docker Compose
```bash
# Edit production docker-compose file
nano docker-compose.production.yml
```

Ensure environment variables are correctly referenced and ports are configured for production.

---

## 4. Database Setup

### 4.1 Initialize Database
```bash
# Build and start database services first
docker-compose -f docker-compose.production.yml up -d postgres redis

# Wait for database to be ready
sleep 30

# Run database migrations
docker-compose -f docker-compose.production.yml exec backend python -m alembic upgrade head

# Create initial admin user
docker-compose -f docker-compose.production.yml exec backend python -c "
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.config import settings

# Initialize database with default admin user
init_db(SessionLocal())
print('Database initialized successfully')
print(f'Default admin email: admin@{settings.DOMAIN}')
print('Default admin password: changeme123!')
print('IMPORTANT: Change the default password immediately after first login')
"
```

---

## 5. Full Application Deployment

### 5.1 Build and Deploy
```bash
# Build all images
docker-compose -f docker-compose.production.yml build --no-cache

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Verify all services are running
docker-compose -f docker-compose.production.yml ps

# Check logs for any errors
docker-compose -f docker-compose.production.yml logs backend
docker-compose -f docker-compose.production.yml logs frontend
docker-compose -f docker-compose.production.yml logs nginx
```

### 5.2 Health Check Verification
```bash
# Wait for services to fully start
sleep 60

# Check API health
curl -k https://api.contentprotection.com/health

# Check frontend
curl -k https://contentprotection.com

# Check individual service health
docker-compose -f docker-compose.production.yml exec backend python -c "
import asyncio
import aiohttp
async def health_check():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/health') as resp:
            print(f'Backend health: {resp.status}')
            print(await resp.text())
asyncio.run(health_check())
"
```

---

## 6. Monitoring and Maintenance

### 6.1 Access Monitoring Dashboards
- **Grafana**: https://grafana.contentprotection.com (admin / your-grafana-password)
- **Kibana**: https://kibana.contentprotection.com
- **Application**: https://contentprotection.com

### 6.2 Backup Configuration
```bash
# Create backup script
cat > /home/contentprotection/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/contentprotection/backups"
mkdir -p $BACKUP_DIR

# Database backup
docker-compose -f /home/contentprotection/autoDMCA/docker-compose.production.yml exec -T postgres pg_dump -U postgres contentprotection > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz /home/contentprotection/autoDMCA

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /home/contentprotection/backup.sh

# Schedule daily backups
echo "0 2 * * * /home/contentprotection/backup.sh" | crontab -
```

### 6.3 Log Rotation
```bash
# Configure log rotation
sudo cat > /etc/logrotate.d/docker-containers << 'EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size 10M
    missingok
    delaycompress
    copytruncate
}
EOF
```

---

## 7. Security Hardening

### 7.1 SSL Security Test
```bash
# Test SSL configuration
curl -I https://contentprotection.com
openssl s_client -connect contentprotection.com:443 -servername contentprotection.com
```

### 7.2 Security Headers Verification
```bash
# Test security headers
curl -I https://contentprotection.com | grep -i security
curl -I https://api.contentprotection.com | grep -i security
```

### 7.3 Performance Testing
```bash
# Test application performance
curl -w "@curl-format.txt" -o /dev/null -s "https://contentprotection.com"

# Create curl format file
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

---

## 8. Troubleshooting

### 8.1 Common Issues
**Services not starting:**
```bash
# Check service logs
docker-compose -f docker-compose.production.yml logs [service-name]

# Check system resources
df -h
free -h
docker system df
```

**SSL certificate issues:**
```bash
# Verify certificate files
sudo ls -la /etc/letsencrypt/live/contentprotection.com/
sudo ls -la nginx/ssl/

# Test certificate renewal
sudo certbot renew --dry-run
```

**Database connection issues:**
```bash
# Check database status
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -c "SELECT version();"

# Check database logs
docker-compose -f docker-compose.production.yml logs postgres
```

### 8.2 Performance Monitoring
```bash
# Monitor resource usage
docker stats

# Check application logs
docker-compose -f docker-compose.production.yml logs -f backend
docker-compose -f docker-compose.production.yml logs -f frontend

# Monitor disk usage
df -h
du -sh /var/lib/docker/
```

---

## 9. Post-Deployment Checklist

### 9.1 Immediate Tasks (Day 1)
- [ ] Verify all services are running
- [ ] Test user registration and login
- [ ] Verify payment processing (test mode first)
- [ ] Test DMCA submission workflow
- [ ] Verify email notifications work
- [ ] Check monitoring dashboards
- [ ] Change default admin password
- [ ] Test SSL certificate and security headers

### 9.2 First Week Tasks
- [ ] Monitor error logs daily
- [ ] Test backup and restore procedures
- [ ] Load test with realistic traffic
- [ ] Monitor performance metrics
- [ ] Set up alerting thresholds
- [ ] Document any custom configurations
- [ ] Train support team
- [ ] Create incident response procedures

### 9.3 Ongoing Maintenance
- [ ] Weekly security updates
- [ ] Monthly dependency updates
- [ ] Quarterly SSL certificate checks
- [ ] Regular backup testing
- [ ] Performance monitoring and optimization
- [ ] Security audit reviews

---

## Support and Contacts

**Technical Support:**
- Email: support@contentprotection.com
- Documentation: https://docs.contentprotection.com
- Status Page: https://status.contentprotection.com

**Emergency Contacts:**
- Technical Lead: [contact information]
- System Administrator: [contact information]
- Security Team: security@contentprotection.com

---

**Deployment Status:** Ready for production deployment
**Last Updated:** $(date)
**Version:** 1.0.0