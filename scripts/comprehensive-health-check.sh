#!/bin/bash
# Comprehensive Health Check Script for AutoDMCA Platform
# Performs thorough validation of all system components

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-production}"
TIMEOUT="${TIMEOUT:-300}"
ENVIRONMENT="${1:-production}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to run a health check
run_check() {
    local check_name="$1"
    local check_command="$2"
    local critical="${3:-false}"
    
    ((TOTAL_CHECKS++))
    log_info "Running check: $check_name"
    
    if eval "$check_command" >/dev/null 2>&1; then
        log_info "✅ PASSED: $check_name"
        ((PASSED_CHECKS++))
        return 0
    else
        if [[ "$critical" == "true" ]]; then
            log_error "❌ CRITICAL FAILURE: $check_name"
            ((FAILED_CHECKS++))
            return 1
        else
            log_warn "⚠️ WARNING: $check_name"
            ((FAILED_CHECKS++))
            return 0
        fi
    fi
}

# Kubernetes cluster health checks
check_cluster_health() {
    log_header "Kubernetes Cluster Health"
    
    run_check "Cluster connectivity" "kubectl cluster-info" true
    run_check "Node readiness" "kubectl get nodes --no-headers | grep -v NotReady" true
    run_check "System pods running" "kubectl get pods -n kube-system --field-selector=status.phase!=Running | grep -v NAME | wc -l | grep -q '^0$'" false
    run_check "Namespace exists" "kubectl get namespace $NAMESPACE" true
}

# Application deployment health checks
check_deployments() {
    log_header "Application Deployments"
    
    local deployments=("backend-prod" "frontend-prod" "celery-worker-scanning" "celery-worker-dmca" "celery-beat")
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
            local ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
            local desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
            
            if [[ "$ready_replicas" -eq "$desired_replicas" && "$ready_replicas" -gt 0 ]]; then
                run_check "Deployment $deployment readiness" "true"
            else
                run_check "Deployment $deployment readiness ($ready_replicas/$desired_replicas ready)" "false" true
            fi
        else
            log_warn "Deployment $deployment not found, skipping..."
        fi
    done
}

# Service health checks
check_services() {
    log_header "Service Health"
    
    local services=("backend-service" "frontend-service")
    
    for service in "${services[@]}"; do
        run_check "Service $service exists" "kubectl get service $service -n $NAMESPACE"
        
        # Check if service has endpoints
        local endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
        if [[ -n "$endpoints" ]]; then
            run_check "Service $service has endpoints" "true"
        else
            run_check "Service $service has endpoints" "false" true
        fi
    done
}

# Pod health checks
check_pods() {
    log_header "Pod Health"
    
    # Check for failed pods
    local failed_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Failed --no-headers | wc -l)
    run_check "No failed pods" "[[ $failed_pods -eq 0 ]]"
    
    # Check for pending pods
    local pending_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Pending --no-headers | wc -l)
    run_check "No pending pods" "[[ $pending_pods -eq 0 ]]"
    
    # Check pod restart counts
    local high_restart_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | awk '$4 > 5' | wc -l)
    run_check "No pods with high restart count" "[[ $high_restart_pods -eq 0 ]]"
}

# Application-specific health checks
check_application_health() {
    log_header "Application Health Endpoints"
    
    # Function to test HTTP endpoint
    test_endpoint() {
        local service="$1"
        local port="$2"
        local path="$3"
        local expected_status="${4:-200}"
        
        local pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app=$service" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [[ -n "$pod_name" ]]; then
            local response_code=$(kubectl exec -n "$NAMESPACE" "$pod_name" -- curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$path" 2>/dev/null || echo "000")
            
            if [[ "$response_code" == "$expected_status" ]]; then
                run_check "$service health endpoint ($path)" "true"
            else
                run_check "$service health endpoint ($path) - got $response_code, expected $expected_status" "false" true
            fi
        else
            run_check "$service pod availability for health check" "false" true
        fi
    }
    
    # Test backend health endpoint
    test_endpoint "backend" "8000" "/health"
    test_endpoint "backend" "8000" "/api/v1/health"
    test_endpoint "frontend" "8080" "/health"
}

# Database connectivity checks
check_database() {
    log_header "Database Connectivity"
    
    # Test database connection from backend pod
    local backend_pod=$(kubectl get pods -n "$NAMESPACE" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$backend_pod" ]]; then
        run_check "Database connection from backend" "kubectl exec -n $NAMESPACE $backend_pod -- python -c 'import psycopg2; from app.core.config import settings; conn = psycopg2.connect(settings.DATABASE_URL); conn.close()'" true
    else
        log_warn "No running backend pod found for database test"
    fi
}

# Redis connectivity checks
check_redis() {
    log_header "Redis Connectivity"
    
    local backend_pod=$(kubectl get pods -n "$NAMESPACE" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$backend_pod" ]]; then
        run_check "Redis connection from backend" "kubectl exec -n $NAMESPACE $backend_pod -- python -c 'import redis; from app.core.config import settings; r = redis.from_url(settings.REDIS_URL); r.ping()'" true
    else
        log_warn "No running backend pod found for Redis test"
    fi
}

# Storage and persistence checks
check_storage() {
    log_header "Storage and Persistence"
    
    # Check persistent volumes
    run_check "Persistent volumes available" "kubectl get pv | grep Available | wc -l | grep -q '[1-9]'"
    
    # Check persistent volume claims
    local pvc_status=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | awk '$2 != "Bound"' | wc -l)
    run_check "All PVCs bound" "[[ $pvc_status -eq 0 ]]"
}

# Resource utilization checks
check_resources() {
    log_header "Resource Utilization"
    
    # Check node resource usage
    if command -v kubectl &> /dev/null && kubectl top nodes >/dev/null 2>&1; then
        local high_cpu_nodes=$(kubectl top nodes --no-headers | awk '$3 ~ /%/ {gsub(/%/, "", $3); if ($3 > 80) print $1}' | wc -l)
        run_check "No nodes with high CPU usage (>80%)" "[[ $high_cpu_nodes -eq 0 ]]"
        
        local high_memory_nodes=$(kubectl top nodes --no-headers | awk '$5 ~ /%/ {gsub(/%/, "", $5); if ($5 > 80) print $1}' | wc -l)
        run_check "No nodes with high memory usage (>80%)" "[[ $high_memory_nodes -eq 0 ]]"
    else
        log_warn "Metrics server not available, skipping resource checks"
    fi
    
    # Check pod resource requests vs limits
    local pods_without_requests=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.containers[*].resources.requests}{"\n"}{end}' | grep -c "^[^ ]* $" || true)
    run_check "All pods have resource requests" "[[ $pods_without_requests -eq 0 ]]"
}

# Network connectivity checks
check_networking() {
    log_header "Network Connectivity"
    
    # Test internal service communication
    local backend_pod=$(kubectl get pods -n "$NAMESPACE" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$backend_pod" ]]; then
        # Test DNS resolution
        run_check "DNS resolution from backend pod" "kubectl exec -n $NAMESPACE $backend_pod -- nslookup kubernetes.default.svc.cluster.local"
        
        # Test internal service connectivity
        run_check "Internal service connectivity" "kubectl exec -n $NAMESPACE $backend_pod -- wget -q --timeout=10 --tries=1 -O /dev/null http://frontend-service.$NAMESPACE.svc.cluster.local:8080/health"
    else
        log_warn "No running backend pod found for network tests"
    fi
}

# Security checks
check_security() {
    log_header "Security Checks"
    
    # Check for pods running as root
    local root_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.securityContext.runAsUser}{" "}{.spec.containers[*].securityContext.runAsUser}{"\n"}{end}' | grep -c " 0 \| 0$" || true)
    run_check "No pods running as root" "[[ $root_pods -eq 0 ]]"
    
    # Check for privileged containers
    local privileged_containers=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.spec.containers[*].securityContext.privileged}{"\n"}{end}' | grep -c "true" || true)
    run_check "No privileged containers" "[[ $privileged_containers -eq 0 ]]"
    
    # Check secrets exist
    local required_secrets=("database-secret" "redis-secret" "app-secret")
    for secret in "${required_secrets[@]}"; do
        run_check "Secret $secret exists" "kubectl get secret $secret -n $NAMESPACE"
    done
}

# Monitoring and observability checks
check_monitoring() {
    log_header "Monitoring and Observability"
    
    # Check if monitoring namespace exists
    if kubectl get namespace monitoring >/dev/null 2>&1; then
        run_check "Monitoring namespace exists" "true"
        
        # Check Prometheus
        run_check "Prometheus deployment" "kubectl get deployment prometheus -n monitoring"
        
        # Check Grafana
        run_check "Grafana deployment" "kubectl get deployment grafana -n monitoring"
        
        # Check AlertManager
        run_check "AlertManager deployment" "kubectl get deployment alertmanager -n monitoring"
    else
        log_warn "Monitoring namespace not found, skipping monitoring checks"
    fi
}

# Backup and disaster recovery checks
check_backups() {
    log_header "Backup and Disaster Recovery"
    
    # Check if backup jobs exist
    if kubectl get cronjobs -n "$NAMESPACE" >/dev/null 2>&1; then
        local backup_jobs=$(kubectl get cronjobs -n "$NAMESPACE" --no-headers | wc -l)
        run_check "Backup jobs configured" "[[ $backup_jobs -gt 0 ]]"
    else
        log_warn "No cronjobs found, backup configuration may be missing"
    fi
    
    # Check recent backup success (if using AWS Backup or similar)
    # This would need to be customized based on your backup solution
}

# Performance checks
check_performance() {
    log_header "Performance Checks"
    
    local backend_pod=$(kubectl get pods -n "$NAMESPACE" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$backend_pod" ]]; then
        # Test response times
        local response_time=$(kubectl exec -n "$NAMESPACE" "$backend_pod" -- curl -o /dev/null -s -w "%{time_total}" "http://localhost:8000/health" 2>/dev/null || echo "10")
        local response_time_ms=$(echo "$response_time * 1000" | bc -l 2>/dev/null | cut -d. -f1)
        
        run_check "Backend response time < 1000ms (${response_time_ms}ms)" "[[ $response_time_ms -lt 1000 ]]"
    fi
}

# Generate summary report
generate_summary() {
    log_header "Health Check Summary"
    
    echo -e "Total Checks: ${BLUE}$TOTAL_CHECKS${NC}"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    
    local success_rate=$(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))
    echo -e "Success Rate: ${BLUE}${success_rate}%${NC}"
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All health checks passed! System is healthy.${NC}"
        return 0
    elif [[ $success_rate -ge 90 ]]; then
        echo -e "\n${YELLOW}⚠️ System is mostly healthy with minor issues.${NC}"
        return 0
    elif [[ $success_rate -ge 70 ]]; then
        echo -e "\n${YELLOW}⚠️ System has some issues that need attention.${NC}"
        return 1
    else
        echo -e "\n${RED}❌ System has critical issues that require immediate attention.${NC}"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting comprehensive health check for AutoDMCA platform"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info "Timeout: $TIMEOUT seconds"
    echo
    
    # Run all health checks
    check_cluster_health
    check_deployments
    check_services
    check_pods
    check_application_health
    check_database
    check_redis
    check_storage
    check_resources
    check_networking
    check_security
    check_monitoring
    check_backups
    check_performance
    
    # Generate and display summary
    generate_summary
}

# Run main function
main "$@"