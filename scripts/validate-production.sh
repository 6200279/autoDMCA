#!/bin/bash

# Production Validation Script for Content Protection Platform
# This script validates the production deployment and configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Logging functions
log() {
    echo -e "${GREEN}[✓] $1${NC}"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

warn() {
    echo -e "${YELLOW}[⚠] WARNING: $1${NC}"
    ((WARNING_CHECKS++))
    ((TOTAL_CHECKS++))
}

fail() {
    echo -e "${RED}[✗] FAILED: $1${NC}"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

info() {
    echo -e "${BLUE}[i] $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is listening
port_listening() {
    ss -tuln | grep -q ":$1 " 2>/dev/null || netstat -tuln | grep -q ":$1 " 2>/dev/null
}

# Function to check HTTP response
check_http() {
    local url="$1"
    local expected_code="${2:-200}"
    local response
    
    response=$(curl -s -w "%{http_code}" -o /dev/null --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [[ "$response" == "$expected_code" ]]; then
        return 0
    else
        return 1
    fi
}

# Check system prerequisites
check_prerequisites() {
    info "Checking system prerequisites..."
    
    # Check Docker
    if command_exists docker; then
        log "Docker is installed"
        docker --version
    else
        fail "Docker is not installed"
    fi
    
    # Check Docker Compose
    if command_exists docker-compose; then
        log "Docker Compose is installed"
        docker-compose --version
    else
        fail "Docker Compose is not installed"
    fi
    
    # Check system resources
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $mem_gb -ge 4 ]]; then
        log "Sufficient memory available: ${mem_gb}GB"
    else
        warn "Low memory: ${mem_gb}GB (4GB+ recommended)"
    fi
    
    # Check disk space
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $disk_usage -lt 80 ]]; then
        log "Sufficient disk space: ${disk_usage}% used"
    else
        warn "High disk usage: ${disk_usage}% used"
    fi
}

# Check environment files
check_environment_files() {
    info "Checking environment configuration files..."
    
    # Check backend environment
    if [[ -f ".env.production" ]]; then
        log "Backend environment file exists"
        
        # Check critical variables
        if grep -q "POSTGRES_PASSWORD=" .env.production; then
            log "Database password configured"
        else
            fail "Database password not configured"
        fi
        
        if grep -q "SECRET_KEY=" .env.production; then
            log "Secret key configured"
        else
            fail "Secret key not configured"
        fi
        
        # Check for placeholder values
        if grep -q "YOUR_.*_HERE" .env.production; then
            warn "Placeholder values found in backend environment"
        else
            log "No placeholder values in backend environment"
        fi
    else
        fail "Backend environment file (.env.production) not found"
    fi
    
    # Check frontend environment
    if [[ -f "frontend/.env.production" ]]; then
        log "Frontend environment file exists"
        
        if grep -q "REACT_APP_API_BASE_URL=" frontend/.env.production; then
            log "Frontend API URL configured"
        else
            fail "Frontend API URL not configured"
        fi
    else
        fail "Frontend environment file not found"
    fi
}

# Check SSL certificates
check_ssl_certificates() {
    info "Checking SSL certificates..."
    
    if [[ -f "nginx/ssl/cert.pem" && -f "nginx/ssl/key.pem" ]]; then
        log "SSL certificate files found"
        
        # Check certificate validity
        if openssl x509 -in nginx/ssl/cert.pem -noout -checkend 86400 >/dev/null 2>&1; then
            log "SSL certificate is valid and not expiring within 24 hours"
        else
            warn "SSL certificate may be expired or expiring soon"
        fi
        
        # Check certificate and key match
        cert_modulus=$(openssl x509 -noout -modulus -in nginx/ssl/cert.pem | openssl md5)
        key_modulus=$(openssl rsa -noout -modulus -in nginx/ssl/key.pem | openssl md5)
        
        if [[ "$cert_modulus" == "$key_modulus" ]]; then
            log "SSL certificate and key match"
        else
            fail "SSL certificate and key do not match"
        fi
    else
        fail "SSL certificate files not found"
    fi
}

# Check Docker services
check_docker_services() {
    info "Checking Docker services..."
    
    if [[ -f "docker-compose.production.yml" ]]; then
        log "Docker Compose production file exists"
        
        # Check if services are running
        local running_services
        running_services=$(docker-compose -f docker-compose.production.yml ps --services --filter "status=running" | wc -l)
        local total_services
        total_services=$(docker-compose -f docker-compose.production.yml config --services | wc -l)
        
        if [[ $running_services -eq $total_services ]]; then
            log "All Docker services are running ($running_services/$total_services)"
        elif [[ $running_services -gt 0 ]]; then
            warn "Some Docker services are running ($running_services/$total_services)"
        else
            fail "No Docker services are running"
        fi
        
        # Check specific critical services
        local critical_services=("backend" "frontend" "postgres" "redis" "nginx")
        for service in "${critical_services[@]}"; do
            if docker-compose -f docker-compose.production.yml ps "$service" | grep -q "Up"; then
                log "Service $service is running"
            else
                fail "Service $service is not running"
            fi
        done
    else
        fail "Docker Compose production file not found"
    fi
}

# Check network connectivity
check_network_connectivity() {
    info "Checking network connectivity..."
    
    # Check if ports are listening
    local ports=(80 443 5432 6379)
    for port in "${ports[@]}"; do
        if port_listening "$port"; then
            log "Port $port is listening"
        else
            warn "Port $port is not listening"
        fi
    done
    
    # Check external connectivity
    if ping -c 1 google.com >/dev/null 2>&1; then
        log "External network connectivity working"
    else
        warn "External network connectivity issues"
    fi
}

# Check application health
check_application_health() {
    info "Checking application health..."
    
    # Load environment variables
    if [[ -f ".env.production" ]]; then
        source .env.production
    fi
    
    # Extract domain from environment or use localhost
    local domain="${FRONTEND_URL#https://}"
    local api_domain="${API_URL#https://}"
    
    if [[ -z "$domain" ]]; then
        domain="localhost"
        api_domain="localhost:8000"
    fi
    
    # Check backend health endpoint
    if check_http "http://${api_domain}/health" 200; then
        log "Backend health endpoint responding"
    elif check_http "http://localhost:8000/health" 200; then
        log "Backend health endpoint responding (localhost)"
    else
        fail "Backend health endpoint not responding"
    fi
    
    # Check frontend
    if check_http "http://${domain}" 200; then
        log "Frontend responding"
    elif check_http "http://localhost:3000" 200; then
        log "Frontend responding (localhost)"
    else
        warn "Frontend not responding"
    fi
    
    # Check database connectivity
    if docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d contentprotection -c "SELECT 1;" >/dev/null 2>&1; then
        log "Database connectivity working"
    else
        fail "Database connectivity issues"
    fi
    
    # Check Redis connectivity
    if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        log "Redis connectivity working"
    else
        fail "Redis connectivity issues"
    fi
}

# Check security configuration
check_security_configuration() {
    info "Checking security configuration..."
    
    # Check file permissions
    if [[ -f "nginx/ssl/key.pem" ]]; then
        local key_perms=$(stat -c "%a" nginx/ssl/key.pem)
        if [[ "$key_perms" == "600" ]]; then
            log "SSL private key has correct permissions (600)"
        else
            warn "SSL private key permissions should be 600 (currently $key_perms)"
        fi
    fi
    
    # Check for sensitive files
    if [[ -f ".env" ]]; then
        warn "Development .env file found in production"
    fi
    
    # Check Docker security
    if docker info | grep -q "Security Options"; then
        log "Docker security options enabled"
    else
        warn "Docker security options not configured"
    fi
    
    # Check firewall status
    if command_exists ufw; then
        if ufw status | grep -q "Status: active"; then
            log "UFW firewall is active"
        else
            warn "UFW firewall is not active"
        fi
    elif command_exists firewall-cmd; then
        if firewall-cmd --state | grep -q "running"; then
            log "Firewall is running"
        else
            warn "Firewall is not running"
        fi
    else
        warn "No firewall detected"
    fi
}

# Check backup configuration
check_backup_configuration() {
    info "Checking backup configuration..."
    
    if [[ -f "scripts/backup.sh" ]]; then
        log "Backup script exists"
        
        if [[ -x "scripts/backup.sh" ]]; then
            log "Backup script is executable"
        else
            warn "Backup script is not executable"
        fi
    else
        warn "Backup script not found"
    fi
    
    if [[ -d "backups" ]]; then
        log "Backup directory exists"
    else
        warn "Backup directory not found"
    fi
    
    # Check cron jobs
    if crontab -l 2>/dev/null | grep -q "backup"; then
        log "Backup cron job configured"
    else
        warn "Backup cron job not configured"
    fi
}

# Check monitoring
check_monitoring() {
    info "Checking monitoring services..."
    
    # Check Grafana
    if check_http "http://localhost:3001" 200; then
        log "Grafana is responding"
    else
        warn "Grafana is not responding"
    fi
    
    # Check Prometheus
    if check_http "http://localhost:9090" 200; then
        log "Prometheus is responding"
    else
        warn "Prometheus is not responding"
    fi
    
    # Check Elasticsearch
    if check_http "http://localhost:9200" 200; then
        log "Elasticsearch is responding"
    else
        warn "Elasticsearch is not responding"
    fi
}

# Check performance
check_performance() {
    info "Checking performance metrics..."
    
    # Check load average
    local load_avg=$(uptime | awk -F'load average:' '{ print $2 }' | awk '{ print $1 }' | sed 's/,//')
    local cpu_cores=$(nproc)
    local load_ratio=$(echo "$load_avg $cpu_cores" | awk '{ printf "%.2f", $1/$2 }')
    
    if (( $(echo "$load_ratio < 0.7" | bc -l) )); then
        log "System load is normal: $load_avg (ratio: $load_ratio)"
    elif (( $(echo "$load_ratio < 1.0" | bc -l) )); then
        warn "System load is elevated: $load_avg (ratio: $load_ratio)"
    else
        warn "System load is high: $load_avg (ratio: $load_ratio)"
    fi
    
    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    if (( $(echo "$mem_usage < 80" | bc -l) )); then
        log "Memory usage is normal: ${mem_usage}%"
    else
        warn "Memory usage is high: ${mem_usage}%"
    fi
    
    # Check disk I/O
    if command_exists iostat; then
        local io_wait=$(iostat 1 2 | tail -1 | awk '{print $4}')
        if (( $(echo "$io_wait < 10" | bc -l) )); then
            log "Disk I/O wait is normal: ${io_wait}%"
        else
            warn "Disk I/O wait is high: ${io_wait}%"
        fi
    fi
}

# Generate report
generate_report() {
    echo
    echo -e "${BLUE}=== PRODUCTION VALIDATION REPORT ===${NC}"
    echo -e "Date: $(date)"
    echo -e "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo
    
    local success_rate=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    
    if [[ $FAILED_CHECKS -eq 0 && $WARNING_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✓ PRODUCTION READY - All checks passed${NC}"
    elif [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${YELLOW}⚠ PRODUCTION READY WITH WARNINGS - Success rate: ${success_rate}%${NC}"
        echo -e "${YELLOW}  Please address warnings before going live${NC}"
    else
        echo -e "${RED}✗ NOT PRODUCTION READY - Critical issues found${NC}"
        echo -e "${RED}  Please fix failed checks before deployment${NC}"
    fi
    
    echo
    echo "Recommendations:"
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        echo "- Fix all failed checks immediately"
    fi
    if [[ $WARNING_CHECKS -gt 0 ]]; then
        echo "- Address warnings to improve security and reliability"
    fi
    echo "- Run this validation script regularly"
    echo "- Monitor application performance and logs"
    echo "- Keep security updates current"
    echo
}

# Main function
main() {
    echo -e "${BLUE}Content Protection Platform - Production Validation${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo
    
    check_prerequisites
    check_environment_files
    check_ssl_certificates
    check_docker_services
    check_network_connectivity
    check_application_health
    check_security_configuration
    check_backup_configuration
    check_monitoring
    check_performance
    
    generate_report
}

# Run validation
main "$@"