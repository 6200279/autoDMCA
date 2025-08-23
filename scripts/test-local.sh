#!/bin/bash

# Local Testing Validation Script for Content Protection Platform
# This script validates the local Docker deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
GRAFANA_URL="http://localhost:3001"
PROMETHEUS_URL="http://localhost:9090"

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log_test() {
    echo -e "${BLUE}[TEST] $1${NC}"
    ((TOTAL_TESTS++))
}

pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((PASSED_TESTS++))
}

fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((FAILED_TESTS++))
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Function to check HTTP response
check_http() {
    local url="$1"
    local expected_code="${2:-200}"
    local timeout="${3:-10}"
    
    local response
    response=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$timeout" "$url" 2>/dev/null || echo "000")
    
    if [[ "$response" == "$expected_code" ]]; then
        return 0
    else
        return 1
    fi
}

# Function to check if container is running
check_container() {
    local service_name="$1"
    if docker-compose -f docker-compose.production.yml ps "$service_name" | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Test Docker prerequisites
test_docker_setup() {
    log_test "Checking Docker setup"
    
    if command -v docker >/dev/null 2>&1; then
        pass "Docker is installed"
    else
        fail "Docker is not installed"
        return 1
    fi
    
    if command -v docker-compose >/dev/null 2>&1; then
        pass "Docker Compose is installed"
    else
        fail "Docker Compose is not installed"
        return 1
    fi
    
    if docker info >/dev/null 2>&1; then
        pass "Docker daemon is running"
    else
        fail "Docker daemon is not running"
        return 1
    fi
}

# Test environment files
test_environment_files() {
    log_test "Checking environment configuration"
    
    if [[ -f ".env.local" ]]; then
        pass "Backend environment file exists"
    else
        fail "Backend environment file (.env.local) not found"
    fi
    
    if [[ -f "frontend/.env.local" ]]; then
        pass "Frontend environment file exists"
    else
        fail "Frontend environment file (frontend/.env.local) not found"
    fi
    
    # Check for critical environment variables
    if grep -q "DATABASE_URL" .env.local 2>/dev/null; then
        pass "Database URL configured"
    else
        fail "Database URL not configured"
    fi
    
    if grep -q "REDIS_URL" .env.local 2>/dev/null; then
        pass "Redis URL configured"
    else
        fail "Redis URL not configured"
    fi
}

# Test container status
test_container_status() {
    log_test "Checking container status"
    
    local critical_services=("postgres" "redis" "backend" "frontend")
    local optional_services=("grafana" "prometheus" "elasticsearch")
    
    for service in "${critical_services[@]}"; do
        if check_container "$service"; then
            pass "Service $service is running"
        else
            fail "Service $service is not running"
        fi
    done
    
    for service in "${optional_services[@]}"; do
        if check_container "$service"; then
            pass "Optional service $service is running"
        else
            warn "Optional service $service is not running"
        fi
    done
}

# Test database connectivity
test_database_connectivity() {
    log_test "Testing database connectivity"
    
    # Test PostgreSQL
    if docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d contentprotection -c "SELECT 1;" >/dev/null 2>&1; then
        pass "PostgreSQL connection successful"
    else
        fail "PostgreSQL connection failed"
    fi
    
    # Test Redis
    if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        pass "Redis connection successful"
    else
        fail "Redis connection failed"
    fi
}

# Test API endpoints
test_api_endpoints() {
    log_test "Testing API endpoints"
    
    # Test health endpoint
    if check_http "$API_URL/health" 200 10; then
        pass "Backend health endpoint responding"
    else
        fail "Backend health endpoint not responding"
    fi
    
    # Test API documentation
    if check_http "$API_URL/docs" 200 10; then
        pass "API documentation accessible"
    else
        warn "API documentation not accessible"
    fi
    
    # Test OpenAPI spec
    if check_http "$API_URL/openapi.json" 200 10; then
        pass "OpenAPI specification accessible"
    else
        warn "OpenAPI specification not accessible"
    fi
}

# Test frontend
test_frontend() {
    log_test "Testing frontend application"
    
    # Test main page
    if check_http "$FRONTEND_URL" 200 15; then
        pass "Frontend main page accessible"
    else
        fail "Frontend main page not accessible"
    fi
    
    # Check if build artifacts exist
    if [[ -d "frontend/dist" ]]; then
        if [[ -f "frontend/dist/index.html" ]]; then
            pass "Frontend build artifacts present"
        else
            fail "Frontend index.html not found"
        fi
    else
        warn "Frontend dist directory not found (may be served from container)"
    fi
}

# Test authentication
test_authentication() {
    log_test "Testing authentication system"
    
    # Test registration endpoint
    local register_response
    register_response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@local.com","password":"testpass123","full_name":"Test User"}' \
        "$API_URL/api/v1/auth/register" 2>/dev/null || echo "000")
    
    local register_code="${register_response: -3}"
    if [[ "$register_code" == "201" ]] || [[ "$register_code" == "400" ]]; then
        pass "Authentication registration endpoint accessible"
    else
        warn "Authentication registration endpoint issues (code: $register_code)"
    fi
    
    # Test login endpoint
    local login_response
    login_response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"admin@contentprotection.com","password":"changeme123!"}' \
        "$API_URL/api/v1/auth/login" 2>/dev/null || echo "000")
    
    local login_code="${login_response: -3}"
    if [[ "$login_code" == "200" ]] || [[ "$login_code" == "401" ]]; then
        pass "Authentication login endpoint accessible"
    else
        warn "Authentication login endpoint issues (code: $login_code)"
    fi
}

# Test monitoring services
test_monitoring() {
    log_test "Testing monitoring services"
    
    # Test Grafana
    if check_http "$GRAFANA_URL" 200 10; then
        pass "Grafana accessible"
    else
        warn "Grafana not accessible"
    fi
    
    # Test Prometheus
    if check_http "$PROMETHEUS_URL" 200 10; then
        pass "Prometheus accessible"
    else
        warn "Prometheus not accessible"
    fi
    
    # Test Elasticsearch (if running)
    if check_http "http://localhost:9200" 200 5; then
        pass "Elasticsearch accessible"
    else
        warn "Elasticsearch not accessible"
    fi
}

# Test resource usage
test_resource_usage() {
    log_test "Checking resource usage"
    
    # Check Docker system status
    local disk_usage
    disk_usage=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | tail -n +2 | awk '{sum+=$3} END {print sum}' || echo "0")
    
    info "Docker disk usage: ${disk_usage} (estimated)"
    
    # Check running containers
    local container_count
    container_count=$(docker ps -q | wc -l)
    
    if [[ $container_count -gt 0 ]]; then
        pass "Running containers: $container_count"
    else
        warn "No running containers found"
    fi
    
    # Check memory usage (if available)
    if command -v free >/dev/null 2>&1; then
        local mem_usage
        mem_usage=$(free -h | grep "Mem:" | awk '{print $3 "/" $2}')
        info "System memory usage: $mem_usage"
    fi
}

# Test log output
test_logs() {
    log_test "Checking service logs for errors"
    
    local services=("backend" "frontend" "postgres" "redis")
    local error_count=0
    
    for service in "${services[@]}"; do
        if check_container "$service"; then
            local errors
            errors=$(docker-compose -f docker-compose.production.yml logs --tail=50 "$service" 2>/dev/null | grep -i -E "(error|failed|exception)" | wc -l)
            
            if [[ $errors -eq 0 ]]; then
                pass "Service $service: No errors in recent logs"
            elif [[ $errors -lt 5 ]]; then
                warn "Service $service: $errors errors found in logs"
                ((error_count++))
            else
                fail "Service $service: $errors errors found in logs"
                ((error_count++))
            fi
        fi
    done
    
    if [[ $error_count -eq 0 ]]; then
        pass "Overall log analysis: Clean"
    else
        warn "Overall log analysis: $error_count services with errors"
    fi
}

# Generate test report
generate_report() {
    echo
    echo -e "${BLUE}=== LOCAL TESTING REPORT ===${NC}"
    echo -e "Date: $(date)"
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo
    
    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}✓ LOCAL TESTING SUCCESSFUL (${success_rate}%)${NC}"
        echo -e "${GREEN}  Platform is ready for production deployment!${NC}"
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "${YELLOW}⚠ MOSTLY SUCCESSFUL (${success_rate}%)${NC}"
        echo -e "${YELLOW}  Review failed tests before production deployment${NC}"
    else
        echo -e "${RED}✗ TESTING ISSUES FOUND (${success_rate}%)${NC}"
        echo -e "${RED}  Fix critical issues before proceeding${NC}"
    fi
    
    echo
    echo "Next Steps:"
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo "- ✅ Proceed with Dokploy production deployment"
        echo "- 📋 Follow production deployment guide"
        echo "- 🔍 Set up production monitoring"
    else
        echo "- 🔧 Fix failed tests and re-run validation"
        echo "- 📝 Check troubleshooting section in LOCAL_TESTING_GUIDE.md"
        echo "- 🔍 Review service logs for error details"
    fi
    echo
}

# Main testing function
main() {
    echo -e "${BLUE}Content Protection Platform - Local Testing Validation${NC}"
    echo -e "${BLUE}===================================================${NC}"
    echo
    
    test_docker_setup
    test_environment_files
    test_container_status
    test_database_connectivity
    test_api_endpoints
    test_frontend
    test_authentication
    test_monitoring
    test_resource_usage
    test_logs
    
    generate_report
}

# Check command line arguments
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Local Testing Validation Script"
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo "  --quick       Run only critical tests"
    echo "  --full        Run all tests (default)"
    echo
    exit 0
fi

if [[ "$1" == "--quick" ]]; then
    echo "Running quick validation..."
    test_docker_setup
    test_container_status
    test_api_endpoints
    test_frontend
    generate_report
else
    # Run full test suite
    main
fi