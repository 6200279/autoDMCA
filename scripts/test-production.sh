#!/bin/bash

# Production Testing Script for Content Protection Platform
# This script performs end-to-end testing of production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOMAIN="${DOMAIN:-localhost}"
API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TEST_EMAIL="test@example.com"
TEST_PASSWORD="TestPassword123!"

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

# Function to make API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_code="${4:-200}"
    local token="$5"
    
    local curl_cmd="curl -s -w '%{http_code}' -X $method"
    
    if [[ -n "$token" ]]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $token'"
    fi
    
    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    curl_cmd="$curl_cmd '$API_URL$endpoint'"
    
    local response
    response=$(eval "$curl_cmd")
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [[ "$http_code" == "$expected_code" ]]; then
        return 0
    else
        echo "Expected: $expected_code, Got: $http_code"
        echo "Response: $body"
        return 1
    fi
}

# Test database connectivity
test_database() {
    log_test "Testing database connectivity"
    
    if docker-compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d contentprotection -c "SELECT 1;" >/dev/null 2>&1; then
        pass "Database connection successful"
    else
        fail "Database connection failed"
    fi
}

# Test Redis connectivity
test_redis() {
    log_test "Testing Redis connectivity"
    
    if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        pass "Redis connection successful"
    else
        fail "Redis connection failed"
    fi
}

# Test backend health
test_backend_health() {
    log_test "Testing backend health endpoint"
    
    if api_call "GET" "/health" "" "200"; then
        pass "Backend health check passed"
    else
        fail "Backend health check failed"
    fi
}

# Test authentication endpoints
test_authentication() {
    log_test "Testing authentication system"
    
    # Test user registration
    local register_data='{
        "email": "'$TEST_EMAIL'",
        "password": "'$TEST_PASSWORD'",
        "full_name": "Test User"
    }'
    
    if api_call "POST" "/auth/register" "$register_data" "201"; then
        pass "User registration successful"
    else
        warn "User registration failed (user may already exist)"
    fi
    
    # Test user login
    local login_data='{
        "username": "'$TEST_EMAIL'",
        "password": "'$TEST_PASSWORD'"
    }'
    
    local login_response
    login_response=$(curl -s -X POST -H "Content-Type: application/json" -d "$login_data" "$API_URL/auth/login")
    
    if echo "$login_response" | grep -q "access_token"; then
        pass "User login successful"
        # Extract token for authenticated tests
        ACCESS_TOKEN=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    else
        fail "User login failed"
        ACCESS_TOKEN=""
    fi
}

# Test protected endpoints
test_protected_endpoints() {
    log_test "Testing protected endpoints"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping protected endpoint tests"
        return
    fi
    
    # Test user profile endpoint
    if api_call "GET" "/auth/me" "" "200" "$ACCESS_TOKEN"; then
        pass "User profile endpoint accessible"
    else
        fail "User profile endpoint failed"
    fi
    
    # Test profile creation
    local profile_data='{
        "name": "Test Profile",
        "description": "Test profile for automated testing"
    }'
    
    if api_call "POST" "/profiles" "$profile_data" "201" "$ACCESS_TOKEN"; then
        pass "Profile creation successful"
    else
        fail "Profile creation failed"
    fi
}

# Test scanning endpoints
test_scanning_endpoints() {
    log_test "Testing scanning functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping scanning tests"
        return
    fi
    
    # Test manual scan trigger
    local scan_data='{
        "profile_id": 1,
        "urls": ["https://example.com"],
        "scan_type": "manual"
    }'
    
    if api_call "POST" "/scan/manual" "$scan_data" "202" "$ACCESS_TOKEN"; then
        pass "Manual scan trigger successful"
    else
        fail "Manual scan trigger failed"
    fi
    
    # Test scan history
    if api_call "GET" "/scan/history" "" "200" "$ACCESS_TOKEN"; then
        pass "Scan history retrieval successful"
    else
        fail "Scan history retrieval failed"
    fi
}

# Test AI endpoints
test_ai_endpoints() {
    log_test "Testing AI functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping AI tests"
        return
    fi
    
    # Test AI analysis endpoint (with dummy data)
    local ai_data='{
        "content_url": "https://example.com/image.jpg",
        "profile_id": 1,
        "analysis_type": "image"
    }'
    
    if api_call "POST" "/ai/analyze" "$ai_data" "202" "$ACCESS_TOKEN"; then
        pass "AI analysis endpoint accessible"
    else
        warn "AI analysis endpoint failed (may require real image data)"
    fi
}

# Test DMCA endpoints
test_dmca_endpoints() {
    log_test "Testing DMCA functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping DMCA tests"
        return
    fi
    
    # Test DMCA submission
    local dmca_data='{
        "infringing_url": "https://example.com/infringing-content",
        "original_content": "Original content description",
        "profile_id": 1
    }'
    
    if api_call "POST" "/dmca/submit" "$dmca_data" "201" "$ACCESS_TOKEN"; then
        pass "DMCA submission successful"
    else
        fail "DMCA submission failed"
    fi
    
    # Test DMCA history
    if api_call "GET" "/dmca/history" "" "200" "$ACCESS_TOKEN"; then
        pass "DMCA history retrieval successful"
    else
        fail "DMCA history retrieval failed"
    fi
}

# Test billing endpoints
test_billing_endpoints() {
    log_test "Testing billing functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping billing tests"
        return
    fi
    
    # Test subscription status
    if api_call "GET" "/billing/subscription" "" "200" "$ACCESS_TOKEN"; then
        pass "Billing subscription endpoint accessible"
    else
        fail "Billing subscription endpoint failed"
    fi
    
    # Test invoice history
    if api_call "GET" "/billing/invoices" "" "200" "$ACCESS_TOKEN"; then
        pass "Invoice history endpoint accessible"
    else
        fail "Invoice history endpoint failed"
    fi
}

# Test frontend accessibility
test_frontend() {
    log_test "Testing frontend accessibility"
    
    # Test main page
    local frontend_response
    frontend_response=$(curl -s -w "%{http_code}" -o /dev/null --max-time 10 "$FRONTEND_URL" 2>/dev/null || echo "000")
    
    if [[ "$frontend_response" == "200" ]]; then
        pass "Frontend main page accessible"
    else
        fail "Frontend main page not accessible (HTTP: $frontend_response)"
    fi
    
    # Test frontend build artifacts
    if [[ -d "frontend/dist" ]]; then
        if [[ -f "frontend/dist/index.html" ]]; then
            pass "Frontend build artifacts present"
        else
            fail "Frontend index.html not found"
        fi
        
        # Check for critical assets
        if ls frontend/dist/assets/*.js >/dev/null 2>&1; then
            pass "Frontend JavaScript assets found"
        else
            fail "Frontend JavaScript assets not found"
        fi
        
        if ls frontend/dist/assets/*.css >/dev/null 2>&1; then
            pass "Frontend CSS assets found"
        else
            fail "Frontend CSS assets not found"
        fi
    else
        fail "Frontend dist directory not found"
    fi
}

# Test WebSocket connectivity
test_websocket() {
    log_test "Testing WebSocket connectivity"
    
    # Basic WebSocket test using curl (if available)
    if command -v websocat >/dev/null 2>&1; then
        # Test WebSocket connection
        timeout 5 websocat "ws://localhost:8000/ws" <<<'{"type":"ping"}' >/dev/null 2>&1
        if [[ $? -eq 0 ]]; then
            pass "WebSocket connection successful"
        else
            warn "WebSocket connection failed or timeout"
        fi
    else
        warn "websocat not available, skipping WebSocket test"
    fi
}

# Test monitoring services
test_monitoring() {
    log_test "Testing monitoring services"
    
    # Test Grafana
    local grafana_response
    grafana_response=$(curl -s -w "%{http_code}" -o /dev/null --max-time 5 "http://localhost:3001" 2>/dev/null || echo "000")
    
    if [[ "$grafana_response" == "200" ]]; then
        pass "Grafana accessible"
    else
        warn "Grafana not accessible (HTTP: $grafana_response)"
    fi
    
    # Test Prometheus
    local prometheus_response
    prometheus_response=$(curl -s -w "%{http_code}" -o /dev/null --max-time 5 "http://localhost:9090" 2>/dev/null || echo "000")
    
    if [[ "$prometheus_response" == "200" ]]; then
        pass "Prometheus accessible"
    else
        warn "Prometheus not accessible (HTTP: $prometheus_response)"
    fi
    
    # Test Elasticsearch
    local elastic_response
    elastic_response=$(curl -s -w "%{http_code}" -o /dev/null --max-time 5 "http://localhost:9200" 2>/dev/null || echo "000")
    
    if [[ "$elastic_response" == "200" ]]; then
        pass "Elasticsearch accessible"
    else
        warn "Elasticsearch not accessible (HTTP: $elastic_response)"
    fi
}

# Test email functionality
test_email() {
    log_test "Testing email functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping email tests"
        return
    fi
    
    # Test email sending endpoint
    local email_data='{
        "to": "'$TEST_EMAIL'",
        "subject": "Production Test Email",
        "body": "This is a test email from the production testing script."
    }'
    
    if api_call "POST" "/test/email" "$email_data" "200" "$ACCESS_TOKEN"; then
        pass "Email sending test successful"
    else
        warn "Email sending test failed (endpoint may not be available)"
    fi
}

# Test file upload functionality
test_file_upload() {
    log_test "Testing file upload functionality"
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        fail "No access token available, skipping file upload tests"
        return
    fi
    
    # Create a test file
    echo "Test content for upload" > /tmp/test_upload.txt
    
    # Test file upload
    local upload_response
    upload_response=$(curl -s -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -F "file=@/tmp/test_upload.txt" \
        "$API_URL/upload" 2>/dev/null || echo "000")
    
    local http_code="${upload_response: -3}"
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        pass "File upload test successful"
    else
        warn "File upload test failed (HTTP: $http_code)"
    fi
    
    # Clean up
    rm -f /tmp/test_upload.txt
}

# Test security headers
test_security_headers() {
    log_test "Testing security headers"
    
    local headers
    headers=$(curl -I -s "$FRONTEND_URL" 2>/dev/null)
    
    if echo "$headers" | grep -i "x-frame-options" >/dev/null; then
        pass "X-Frame-Options header present"
    else
        warn "X-Frame-Options header missing"
    fi
    
    if echo "$headers" | grep -i "x-content-type-options" >/dev/null; then
        pass "X-Content-Type-Options header present"
    else
        warn "X-Content-Type-Options header missing"
    fi
    
    if echo "$headers" | grep -i "content-security-policy" >/dev/null; then
        pass "Content-Security-Policy header present"
    else
        warn "Content-Security-Policy header missing"
    fi
}

# Performance test
test_performance() {
    log_test "Testing performance metrics"
    
    # Test API response time
    local start_time=$(date +%s%N)
    api_call "GET" "/health" "" "200" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $response_time -lt 2000 ]]; then
        pass "API response time acceptable: ${response_time}ms"
    else
        warn "API response time slow: ${response_time}ms"
    fi
    
    # Test frontend load time
    start_time=$(date +%s%N)
    curl -s -o /dev/null "$FRONTEND_URL" >/dev/null 2>&1
    end_time=$(date +%s%N)
    local frontend_time=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $frontend_time -lt 3000 ]]; then
        pass "Frontend load time acceptable: ${frontend_time}ms"
    else
        warn "Frontend load time slow: ${frontend_time}ms"
    fi
}

# Load environment variables
load_environment() {
    if [[ -f ".env.production" ]]; then
        set -a
        source .env.production
        set +a
        
        # Update URLs from environment
        API_URL="${API_URL:-$API_URL}"
        FRONTEND_URL="${FRONTEND_URL:-$FRONTEND_URL}"
        DOMAIN="${FRONTEND_URL#https://}"
    fi
}

# Generate test report
generate_report() {
    echo
    echo -e "${BLUE}=== PRODUCTION TEST REPORT ===${NC}"
    echo -e "Date: $(date)"
    echo -e "Domain: $DOMAIN"
    echo -e "API URL: $API_URL"
    echo -e "Frontend URL: $FRONTEND_URL"
    echo
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo
    
    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED - Production ready! (${success_rate}%)${NC}"
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "${YELLOW}⚠ MOSTLY PASSING - Review failures (${success_rate}%)${NC}"
    else
        echo -e "${RED}✗ MULTIPLE FAILURES - Fix issues before production (${success_rate}%)${NC}"
    fi
    
    echo
    echo "Recommendations:"
    if [[ $FAILED_TESTS -gt 0 ]]; then
        echo "- Fix all critical test failures"
        echo "- Verify all services are running correctly"
        echo "- Check API key configurations"
    fi
    echo "- Monitor application logs for errors"
    echo "- Test with real user scenarios"
    echo "- Verify external integrations work properly"
    echo
}

# Main testing function
main() {
    echo -e "${BLUE}Content Protection Platform - Production Testing${NC}"
    echo -e "${BLUE}===============================================${NC}"
    echo
    
    load_environment
    
    # Infrastructure tests
    test_database
    test_redis
    
    # Backend API tests
    test_backend_health
    test_authentication
    test_protected_endpoints
    test_scanning_endpoints
    test_ai_endpoints
    test_dmca_endpoints
    test_billing_endpoints
    
    # Frontend tests
    test_frontend
    
    # Integration tests
    test_websocket
    test_email
    test_file_upload
    
    # Security tests
    test_security_headers
    
    # Performance tests
    test_performance
    
    # Monitoring tests
    test_monitoring
    
    generate_report
}

# Check if script should run cleanup
if [[ "$1" == "--cleanup" ]]; then
    echo "Cleaning up test data..."
    # Add cleanup commands here if needed
    exit 0
fi

# Run tests
main "$@"