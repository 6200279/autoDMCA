#!/bin/bash

# Production Setup Script for Content Protection Platform
# This script automates the production deployment setup process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root. Please run as a regular user with sudo privileges."
fi

# Configuration variables
DOMAIN=""
EMAIL=""
ENVIRONMENT_FILE=".env.production"
FRONTEND_ENV_FILE="frontend/.env.production"

# Function to prompt for required configuration
prompt_config() {
    log "Starting production deployment configuration..."
    
    # Domain configuration
    read -p "Enter your domain name (e.g., contentprotection.com): " DOMAIN
    if [[ -z "$DOMAIN" ]]; then
        error "Domain name is required"
    fi
    
    # Email configuration
    read -p "Enter admin email address: " EMAIL
    if [[ -z "$EMAIL" ]]; then
        error "Email address is required"
    fi
    
    # Confirm configuration
    echo
    log "Configuration Summary:"
    echo "Domain: $DOMAIN"
    echo "Email: $EMAIL"
    echo
    read -p "Is this configuration correct? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Configuration cancelled by user"
    fi
}

# Function to generate secure passwords and keys
generate_secrets() {
    log "Generating secure passwords and keys..."
    
    # Generate random passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
    SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')
    WATERMARK_KEY=$(openssl rand -base64 32 | tr -d '\n')
    GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
    
    log "Generated secure passwords and encryption keys"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if OpenSSL is installed
    if ! command -v openssl &> /dev/null; then
        error "OpenSSL is not installed. Please install OpenSSL first."
    fi
    
    # Check if Certbot is available for SSL
    if ! command -v certbot &> /dev/null; then
        warn "Certbot is not installed. You will need to manually configure SSL certificates."
    fi
    
    log "Prerequisites check completed"
}

# Function to setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    # Create SSL directory
    mkdir -p nginx/ssl
    
    if command -v certbot &> /dev/null; then
        log "Attempting to get SSL certificate from Let's Encrypt..."
        
        # Stop any running web services
        sudo systemctl stop nginx apache2 2>/dev/null || true
        
        # Request SSL certificate
        sudo certbot certonly --standalone \
            -d "$DOMAIN" \
            -d "www.$DOMAIN" \
            -d "api.$DOMAIN" \
            -d "admin.$DOMAIN" \
            -d "grafana.$DOMAIN" \
            -d "kibana.$DOMAIN" \
            --email "$EMAIL" \
            --agree-tos \
            --non-interactive || warn "SSL certificate generation failed. You may need to configure manually."
        
        # Copy certificates to application directory
        if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
            sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" nginx/ssl/cert.pem
            sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" nginx/ssl/key.pem
            sudo chown $USER:$USER nginx/ssl/*.pem
            sudo chmod 600 nginx/ssl/*.pem
            log "SSL certificates configured successfully"
        else
            warn "SSL certificate files not found. Please configure manually."
        fi
    else
        warn "Certbot not available. Please install SSL certificates manually in nginx/ssl/"
        # Create placeholder files
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
        log "Created self-signed certificate (replace with valid certificate for production)"
    fi
}

# Function to create environment files
create_environment_files() {
    log "Creating production environment files..."
    
    # Create backend environment file
    cat > "$ENVIRONMENT_FILE" << EOF
# Database Configuration
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql://postgres:$DB_PASSWORD@postgres:5432/contentprotection

# Redis Configuration
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379

# Application Security
SECRET_KEY=$SECRET_KEY
WATERMARK_KEY=$WATERMARK_KEY
ENVIRONMENT=production

# Domain Configuration
FRONTEND_URL=https://$DOMAIN
API_URL=https://api.$DOMAIN
WEBSOCKET_URL=wss://api.$DOMAIN/ws

# Email/SMTP Configuration (UPDATE THESE)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@$DOMAIN
SMTP_PASSWORD=YOUR_SMTP_APP_PASSWORD_HERE
EMAIL_FROM_NAME=Content Protection Platform
EMAIL_FROM_ADDRESS=noreply@$DOMAIN

# API Keys for Search Engines (UPDATE THESE)
GOOGLE_API_KEY=YOUR_GOOGLE_CUSTOM_SEARCH_API_KEY
GOOGLE_CUSTOM_SEARCH_ID=YOUR_GOOGLE_CUSTOM_SEARCH_ENGINE_ID
BING_API_KEY=YOUR_BING_WEB_SEARCH_API_KEY

# Payment Processing - Stripe (UPDATE THESE)
STRIPE_SECRET_KEY=sk_live_YOUR_STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET

# Social Media API Keys (UPDATE THESE)
TWITTER_API_KEY=YOUR_TWITTER_API_KEY
TWITTER_API_SECRET=YOUR_TWITTER_API_SECRET
FACEBOOK_APP_ID=YOUR_FACEBOOK_APP_ID
FACEBOOK_APP_SECRET=YOUR_FACEBOOK_APP_SECRET
INSTAGRAM_ACCESS_TOKEN=YOUR_INSTAGRAM_ACCESS_TOKEN

# Monitoring & Logging
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
LOG_LEVEL=INFO
ENABLE_METRICS=true

# Security Settings
ALLOWED_HOSTS=$DOMAIN,api.$DOMAIN,www.$DOMAIN
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# File Upload Settings
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx,txt

# Rate Limiting
API_RATE_LIMIT_PER_MINUTE=100
LOGIN_RATE_LIMIT_PER_MINUTE=5

# Background Job Settings
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_WORKER_CONCURRENCY=4

# AI/ML Configuration
FACE_RECOGNITION_TOLERANCE=0.6
CONTENT_SIMILARITY_THRESHOLD=0.8
AI_MODEL_PATH=/app/models

# Backup Configuration
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *

# External Services (UPDATE THESE)
WHOIS_API_KEY=YOUR_WHOIS_API_KEY
CLOUDFLARE_API_KEY=YOUR_CLOUDFLARE_API_KEY
CLOUDFLARE_ZONE_ID=YOUR_CLOUDFLARE_ZONE_ID
EOF

    # Create frontend environment file
    cat > "$FRONTEND_ENV_FILE" << EOF
# API Configuration
REACT_APP_API_BASE_URL=https://api.$DOMAIN/api/v1
REACT_APP_WS_URL=wss://api.$DOMAIN/ws

# Environment
NODE_ENV=production

# App Configuration
REACT_APP_APP_NAME=Content Protection Platform
REACT_APP_VERSION=1.0.0

# Features
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_ENABLE_WEBSOCKET=true
REACT_APP_DEBUG_MODE=false

# Payment Integration (UPDATE THIS)
REACT_APP_STRIPE_PUBLIC_KEY=pk_live_YOUR_STRIPE_PUBLISHABLE_KEY

# External Services (UPDATE THESE)
REACT_APP_GOOGLE_ANALYTICS_ID=GA-XXXXXXXXX
REACT_APP_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Security
REACT_APP_ENABLE_HTTPS_ONLY=true
REACT_APP_ENABLE_CSP=true

# Performance
REACT_APP_ENABLE_LAZY_LOADING=true
REACT_APP_ENABLE_SERVICE_WORKER=true
EOF

    log "Environment files created successfully"
}

# Function to update nginx configuration
update_nginx_config() {
    log "Updating nginx configuration with domain..."
    
    # Backup original nginx config
    if [[ -f "nginx/nginx.conf" ]]; then
        cp nginx/nginx.conf nginx/nginx.conf.backup
    fi
    
    # Update server_name directives in nginx config
    sed -i "s/yourdomain.com/$DOMAIN/g" nginx/nginx.conf 2>/dev/null || warn "Could not update nginx config automatically"
    sed -i "s/api.yourdomain.com/api.$DOMAIN/g" nginx/nginx.conf 2>/dev/null || true
    sed -i "s/grafana.yourdomain.com/grafana.$DOMAIN/g" nginx/nginx.conf 2>/dev/null || true
    sed -i "s/kibana.yourdomain.com/kibana.$DOMAIN/g" nginx/nginx.conf 2>/dev/null || true
    
    log "Nginx configuration updated"
}

# Function to setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        sudo ufw --force reset
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        sudo ufw allow 22/tcp comment 'SSH'
        sudo ufw allow 80/tcp comment 'HTTP'
        sudo ufw allow 443/tcp comment 'HTTPS'
        sudo ufw --force enable
        log "Firewall configured successfully"
    else
        warn "UFW not available. Please configure firewall manually."
    fi
}

# Function to create backup script
create_backup_script() {
    log "Creating backup script..."
    
    mkdir -p scripts
    
    cat > scripts/backup.sh << 'EOF'
#!/bin/bash
# Automated backup script for Content Protection Platform

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

echo "Starting backup at $DATE"

# Database backup
echo "Backing up database..."
docker-compose -f docker-compose.production.yml exec -T postgres pg_dump -U postgres contentprotection > $BACKUP_DIR/db_backup_$DATE.sql

# Application files backup
echo "Backing up application files..."
tar --exclude='node_modules' --exclude='dist' --exclude='backups' --exclude='.git' -czf $BACKUP_DIR/app_backup_$DATE.tar.gz .

# Clean old backups (keep 30 days)
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

    chmod +x scripts/backup.sh
    log "Backup script created at scripts/backup.sh"
}

# Function to build and test
build_and_test() {
    log "Building and testing the application..."
    
    # Build frontend
    log "Building frontend..."
    cd frontend
    npm install --production
    npm run build
    cd ..
    
    # Build Docker images
    log "Building Docker images..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    log "Build completed successfully"
}

# Function to display next steps
display_next_steps() {
    log "Production setup completed successfully!"
    
    echo
    echo -e "${BLUE}=== NEXT STEPS ===${NC}"
    echo
    echo "1. Update API Keys and External Services:"
    echo "   Edit $ENVIRONMENT_FILE and $FRONTEND_ENV_FILE"
    echo "   - Add real API keys for Google, Bing, Stripe"
    echo "   - Configure SMTP settings for email"
    echo "   - Add social media API keys"
    echo
    echo "2. DNS Configuration:"
    echo "   Point these domains to your server IP:"
    echo "   - $DOMAIN"
    echo "   - www.$DOMAIN"
    echo "   - api.$DOMAIN"
    echo "   - admin.$DOMAIN"
    echo "   - grafana.$DOMAIN"
    echo "   - kibana.$DOMAIN"
    echo
    echo "3. Deploy the application:"
    echo "   docker-compose -f docker-compose.production.yml up -d"
    echo
    echo "4. Initialize the database:"
    echo "   docker-compose -f docker-compose.production.yml exec backend python -m alembic upgrade head"
    echo
    echo "5. Create admin user:"
    echo "   docker-compose -f docker-compose.production.yml exec backend python scripts/create_admin.py"
    echo
    echo "6. Test the deployment:"
    echo "   - Frontend: https://$DOMAIN"
    echo "   - API: https://api.$DOMAIN/health"
    echo "   - Grafana: https://grafana.$DOMAIN (admin / $GRAFANA_PASSWORD)"
    echo
    echo "7. Set up automated backups:"
    echo "   crontab -e"
    echo "   Add: 0 2 * * * /path/to/scripts/backup.sh"
    echo
    echo -e "${GREEN}Environment passwords generated:${NC}"
    echo "Database: $DB_PASSWORD"
    echo "Redis: $REDIS_PASSWORD" 
    echo "Grafana: $GRAFANA_PASSWORD"
    echo
    echo -e "${YELLOW}IMPORTANT: Save these passwords securely!${NC}"
    echo
}

# Main execution
main() {
    log "Content Protection Platform - Production Setup"
    log "============================================="
    
    prompt_config
    check_prerequisites
    generate_secrets
    setup_ssl
    create_environment_files
    update_nginx_config
    setup_firewall
    create_backup_script
    build_and_test
    display_next_steps
    
    log "Production setup script completed successfully!"
}

# Run main function
main "$@"