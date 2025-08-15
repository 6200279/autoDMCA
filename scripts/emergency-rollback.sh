#!/bin/bash

# autoDMCA Emergency Rollback Script
# This script provides emergency rollback capabilities for critical situations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-production}"
ROLLBACK_TYPE="${2:-auto}"  # auto, manual, database, full
BACKUP_RESTORE="${3:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Emergency banner
emergency_banner() {
    echo -e "${RED}"
    echo "=========================================="
    echo "    🚨 EMERGENCY ROLLBACK INITIATED 🚨"
    echo "=========================================="
    echo -e "${NC}"
    echo "Environment: $ENVIRONMENT"
    echo "Rollback Type: $ROLLBACK_TYPE"
    echo "Backup Restore: $BACKUP_RESTORE"
    echo "Time: $(date)"
    echo "Operator: $(whoami)"
    echo
}

# Confirmation prompt
confirm_rollback() {
    if [[ "$ROLLBACK_TYPE" != "auto" ]]; then
        echo -e "${YELLOW}WARNING: This will rollback the $ENVIRONMENT environment!${NC}"
        echo "This action may cause temporary service disruption."
        echo
        read -p "Are you sure you want to proceed? (type 'YES' to confirm): " confirmation
        
        if [[ "$confirmation" != "YES" ]]; then
            log_error "Rollback cancelled by user"
            exit 1
        fi
    fi
    
    log_info "Rollback confirmed. Proceeding..."
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl access
    if ! kubectl auth can-i "*" "*" --namespace="$ENVIRONMENT" >/dev/null 2>&1; then
        log_error "Insufficient Kubernetes permissions for namespace: $ENVIRONMENT"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$ENVIRONMENT" >/dev/null 2>&1; then
        log_error "Namespace $ENVIRONMENT does not exist"
        exit 1
    fi
    
    # Check if deployments exist
    local deployments
    deployments=$(kubectl get deployments -n "$ENVIRONMENT" --no-headers | wc -l)
    if [[ "$deployments" -eq 0 ]]; then
        log_error "No deployments found in namespace $ENVIRONMENT"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create rollback snapshot
create_rollback_snapshot() {
    log_info "Creating rollback snapshot..."
    
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local snapshot_file="rollback-snapshot-${ENVIRONMENT}-${timestamp}.yaml"
    
    # Export current state
    kubectl get all,configmaps,secrets,pvc,ingress -n "$ENVIRONMENT" -o yaml > "$snapshot_file" 2>/dev/null || {
        log_warning "Failed to create complete snapshot, continuing with partial snapshot"
        kubectl get deployments,services,configmaps -n "$ENVIRONMENT" -o yaml > "$snapshot_file" 2>/dev/null || true
    }
    
    if [[ -f "$snapshot_file" ]]; then
        log_success "Rollback snapshot created: $snapshot_file"
        echo "$snapshot_file"
    else
        log_warning "Failed to create rollback snapshot"
        echo ""
    fi
}

# Stop traffic flow
stop_traffic() {
    log_info "Stopping traffic flow to prevent further damage..."
    
    # Scale down ingress or redirect to maintenance page
    if kubectl get ingress app-ingress -n "$ENVIRONMENT" >/dev/null 2>&1; then
        # Create maintenance mode ingress
        cat > /tmp/maintenance-ingress.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: maintenance-ingress
  namespace: %NAMESPACE%
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: %HOST%
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: maintenance-service
            port:
              number: 80
EOF
        
        # Get original host from existing ingress
        local host
        host=$(kubectl get ingress app-ingress -n "$ENVIRONMENT" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "localhost")
        
        # Replace placeholders
        sed -i "s/%NAMESPACE%/$ENVIRONMENT/g" /tmp/maintenance-ingress.yaml
        sed -i "s/%HOST%/$host/g" /tmp/maintenance-ingress.yaml
        
        # Create maintenance service if it doesn't exist
        if ! kubectl get service maintenance-service -n "$ENVIRONMENT" >/dev/null 2>&1; then
            kubectl create service clusterip maintenance-service --tcp=80:80 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
            kubectl patch service maintenance-service -n "$ENVIRONMENT" -p '{"spec":{"selector":{"app":"maintenance"}}}' >/dev/null 2>&1 || true
        fi
        
        # Apply maintenance ingress
        kubectl apply -f /tmp/maintenance-ingress.yaml >/dev/null 2>&1 || true
        
        # Delete original ingress
        kubectl delete ingress app-ingress -n "$ENVIRONMENT" >/dev/null 2>&1 || true
        
        log_success "Traffic redirected to maintenance mode"
    else
        log_warning "No ingress found, traffic may still be flowing"
    fi
}

# Rollback deployments
rollback_deployments() {
    log_info "Rolling back deployments..."
    
    local deployments=("backend-prod" "frontend-prod" "worker-prod")
    local rollback_success=true
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$ENVIRONMENT" >/dev/null 2>&1; then
            log_info "Rolling back deployment: $deployment"
            
            # Check rollout history
            local revisions
            revisions=$(kubectl rollout history deployment/"$deployment" -n "$ENVIRONMENT" --no-headers | wc -l)
            
            if [[ "$revisions" -gt 1 ]]; then
                # Rollback to previous revision
                if kubectl rollout undo deployment/"$deployment" -n "$ENVIRONMENT" --timeout=300s >/dev/null 2>&1; then
                    log_success "Rolled back deployment: $deployment"
                else
                    log_error "Failed to rollback deployment: $deployment"
                    rollback_success=false
                fi
            else
                log_warning "No previous revision found for deployment: $deployment"
                rollback_success=false
            fi
        else
            log_warning "Deployment $deployment not found, skipping..."
        fi
    done
    
    if [[ "$rollback_success" == "true" ]]; then
        log_success "All deployments rolled back successfully"
    else
        log_error "Some deployments failed to rollback"
        return 1
    fi
}

# Blue-green rollback
rollback_blue_green() {
    log_info "Performing blue-green rollback..."
    
    # Determine current active environment
    local current_color
    current_color=$(kubectl get service backend-service -n "$ENVIRONMENT" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "unknown")
    
    if [[ "$current_color" == "unknown" ]]; then
        log_warning "Cannot determine current blue-green color, attempting standard rollback"
        rollback_deployments
        return $?
    fi
    
    local previous_color
    if [[ "$current_color" == "blue" ]]; then
        previous_color="green"
    else
        previous_color="blue"
    fi
    
    log_info "Current active: $current_color, switching to: $previous_color"
    
    # Check if previous environment exists and is healthy
    local previous_pods
    previous_pods=$(kubectl get pods -n "$ENVIRONMENT" -l "app=backend,version=$previous_color" --field-selector=status.phase=Running --no-headers | wc -l)
    
    if [[ "$previous_pods" -eq 0 ]]; then
        log_warning "No healthy pods found in $previous_color environment, starting emergency deployment"
        
        # Start previous environment if it exists but is scaled down
        if kubectl get deployment "backend-$previous_color" -n "$ENVIRONMENT" >/dev/null 2>&1; then
            kubectl scale deployment "backend-$previous_color" --replicas=3 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
            kubectl scale deployment "frontend-$previous_color" --replicas=2 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
            
            # Wait for pods to come up
            sleep 30
            
            previous_pods=$(kubectl get pods -n "$ENVIRONMENT" -l "app=backend,version=$previous_color" --field-selector=status.phase=Running --no-headers | wc -l)
        fi
    fi
    
    if [[ "$previous_pods" -gt 0 ]]; then
        # Switch traffic to previous environment
        kubectl patch service backend-service -n "$ENVIRONMENT" -p "{\"spec\":{\"selector\":{\"version\":\"$previous_color\"}}}" >/dev/null 2>&1 || true
        kubectl patch service frontend-service -n "$ENVIRONMENT" -p "{\"spec\":{\"selector\":{\"version\":\"$previous_color\"}}}" >/dev/null 2>&1 || true
        
        log_success "Traffic switched from $current_color to $previous_color"
        
        # Scale down current environment
        kubectl scale deployment "backend-$current_color" --replicas=0 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
        kubectl scale deployment "frontend-$current_color" --replicas=0 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
        
        log_success "Blue-green rollback completed"
    else
        log_error "Cannot perform blue-green rollback: no healthy previous environment"
        return 1
    fi
}

# Database rollback
rollback_database() {
    if [[ "$BACKUP_RESTORE" != "true" ]]; then
        log_info "Database rollback not requested"
        return 0
    fi
    
    log_info "Performing database rollback..."
    
    # Find database pod
    local db_pod
    db_pod=$(kubectl get pods -n "$ENVIRONMENT" -l app=postgres --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$db_pod" ]]; then
        log_error "No running PostgreSQL pod found"
        return 1
    fi
    
    # Stop all application pods to prevent database writes
    log_info "Stopping application pods to prevent database writes..."
    kubectl scale deployment backend-prod --replicas=0 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
    kubectl scale deployment worker-prod --replicas=0 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
    
    sleep 10
    
    # Find most recent backup
    local backup_file
    backup_file=$(ls -t backup-*.sql 2>/dev/null | head -1 || echo "")
    
    if [[ -z "$backup_file" ]]; then
        log_error "No backup file found for database restore"
        return 1
    fi
    
    log_info "Restoring database from backup: $backup_file"
    
    # Create current database backup before restore
    local emergency_backup="emergency-backup-$(date +%Y%m%d_%H%M%S).sql"
    kubectl exec -n "$ENVIRONMENT" "$db_pod" -- pg_dump -U postgres contentprotection > "$emergency_backup" 2>/dev/null || {
        log_warning "Failed to create emergency backup"
    }
    
    # Restore database
    if kubectl exec -n "$ENVIRONMENT" "$db_pod" -- psql -U postgres -d contentprotection < "$backup_file" >/dev/null 2>&1; then
        log_success "Database restored from backup"
    else
        log_error "Failed to restore database from backup"
        return 1
    fi
    
    # Restart application pods
    log_info "Restarting application pods..."
    kubectl scale deployment backend-prod --replicas=3 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
    kubectl scale deployment worker-prod --replicas=2 -n "$ENVIRONMENT" >/dev/null 2>&1 || true
    
    log_success "Database rollback completed"
}

# Restore traffic
restore_traffic() {
    log_info "Restoring traffic flow..."
    
    # Remove maintenance mode if it was set
    kubectl delete ingress maintenance-ingress -n "$ENVIRONMENT" >/dev/null 2>&1 || true
    
    # Restore original ingress
    if [[ -f "ingress-backup.yaml" ]]; then
        kubectl apply -f ingress-backup.yaml >/dev/null 2>&1 || true
        log_success "Original ingress restored"
    else
        log_warning "No ingress backup found, may need manual restoration"
    fi
    
    # Wait for services to stabilize
    sleep 15
    
    # Verify health endpoints
    local health_check_attempts=0
    local max_attempts=12
    
    while [[ $health_check_attempts -lt $max_attempts ]]; do
        local backend_pod
        backend_pod=$(kubectl get pods -n "$ENVIRONMENT" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [[ -n "$backend_pod" ]]; then
            if kubectl exec -n "$ENVIRONMENT" "$backend_pod" -- curl -sf http://localhost:8000/health >/dev/null 2>&1; then
                log_success "Health endpoint responding"
                break
            fi
        fi
        
        ((health_check_attempts++))
        log_info "Waiting for health endpoint... ($health_check_attempts/$max_attempts)"
        sleep 10
    done
    
    if [[ $health_check_attempts -ge $max_attempts ]]; then
        log_warning "Health endpoint not responding after rollback"
    fi
}

# Verify rollback
verify_rollback() {
    log_info "Verifying rollback success..."
    
    local verification_passed=true
    
    # Check pod status
    local running_pods
    running_pods=$(kubectl get pods -n "$ENVIRONMENT" --field-selector=status.phase=Running --no-headers | wc -l)
    
    if [[ "$running_pods" -gt 0 ]]; then
        log_success "Pods are running: $running_pods"
    else
        log_error "No running pods found"
        verification_passed=false
    fi
    
    # Check service endpoints
    local services_with_endpoints=0
    local total_services
    total_services=$(kubectl get services -n "$ENVIRONMENT" --no-headers | wc -l)
    
    for service in $(kubectl get services -n "$ENVIRONMENT" -o jsonpath='{.items[*].metadata.name}'); do
        local endpoints
        endpoints=$(kubectl get endpoints "$service" -n "$ENVIRONMENT" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
        if [[ "$endpoints" -gt 0 ]]; then
            ((services_with_endpoints++))
        fi
    done
    
    if [[ "$services_with_endpoints" -eq "$total_services" ]]; then
        log_success "All services have endpoints"
    else
        log_warning "Some services missing endpoints: $services_with_endpoints/$total_services"
    fi
    
    # Test application endpoints
    local backend_pod
    backend_pod=$(kubectl get pods -n "$ENVIRONMENT" -l app=backend --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$backend_pod" ]]; then
        if kubectl exec -n "$ENVIRONMENT" "$backend_pod" -- curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Backend health check passed"
        else
            log_error "Backend health check failed"
            verification_passed=false
        fi
    else
        log_error "No backend pod available for health check"
        verification_passed=false
    fi
    
    if [[ "$verification_passed" == "true" ]]; then
        log_success "Rollback verification passed"
        return 0
    else
        log_error "Rollback verification failed"
        return 1
    fi
}

# Generate rollback report
generate_rollback_report() {
    local rollback_status="$1"
    local report_file="rollback-report-$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
===============================================
EMERGENCY ROLLBACK REPORT
===============================================
Environment: $ENVIRONMENT
Rollback Type: $ROLLBACK_TYPE
Backup Restore: $BACKUP_RESTORE
Status: $rollback_status
Timestamp: $(date)
Operator: $(whoami)

ROLLBACK SUMMARY:
- Traffic stopped: $(if [[ "$rollback_status" == "SUCCESS" ]]; then echo "✓"; else echo "✗"; fi)
- Deployments rolled back: $(if [[ "$rollback_status" == "SUCCESS" ]]; then echo "✓"; else echo "✗"; fi)
- Database restored: $(if [[ "$BACKUP_RESTORE" == "true" ]]; then echo "✓"; else echo "N/A"; fi)
- Traffic restored: $(if [[ "$rollback_status" == "SUCCESS" ]]; then echo "✓"; else echo "✗"; fi)
- Verification: $(if [[ "$rollback_status" == "SUCCESS" ]]; then echo "PASSED"; else echo "FAILED"; fi)

CURRENT SYSTEM STATE:
$(kubectl get pods -n "$ENVIRONMENT" 2>/dev/null || echo "Unable to get pod status")

SERVICES STATUS:
$(kubectl get services -n "$ENVIRONMENT" 2>/dev/null || echo "Unable to get service status")

INGRESS STATUS:
$(kubectl get ingress -n "$ENVIRONMENT" 2>/dev/null || echo "Unable to get ingress status")

===============================================
EOF
    
    log_info "Rollback report generated: $report_file"
    echo "$report_file"
}

# Send notifications
send_notifications() {
    local status="$1"
    local report_file="$2"
    
    # Slack notification (if webhook configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local emoji
        local color
        
        if [[ "$status" == "SUCCESS" ]]; then
            emoji="✅"
            color="good"
        else
            emoji="❌"
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"text\": \"$emoji Emergency Rollback Completed\",
                \"attachments\": [
                    {
                        \"color\": \"$color\",
                        \"fields\": [
                            {
                                \"title\": \"Environment\",
                                \"value\": \"$ENVIRONMENT\",
                                \"short\": true
                            },
                            {
                                \"title\": \"Status\",
                                \"value\": \"$status\",
                                \"short\": true
                            },
                            {
                                \"title\": \"Operator\",
                                \"value\": \"$(whoami)\",
                                \"short\": true
                            },
                            {
                                \"title\": \"Time\",
                                \"value\": \"$(date)\",
                                \"short\": true
                            }
                        ]
                    }
                ]
            }" \
            "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi
}

# Main rollback function
perform_rollback() {
    local snapshot_file
    snapshot_file=$(create_rollback_snapshot)
    
    stop_traffic
    
    case "$ROLLBACK_TYPE" in
        "auto"|"manual")
            rollback_deployments
            ;;
        "blue-green")
            rollback_blue_green
            ;;
        "database")
            rollback_database
            ;;
        "full")
            rollback_deployments
            rollback_database
            ;;
        *)
            log_error "Unknown rollback type: $ROLLBACK_TYPE"
            exit 1
            ;;
    esac
    
    restore_traffic
    
    if verify_rollback; then
        log_success "Emergency rollback completed successfully"
        return 0
    else
        log_error "Emergency rollback completed with errors"
        return 1
    fi
}

# Cleanup function
cleanup() {
    # Remove temporary files
    rm -f /tmp/maintenance-ingress.yaml >/dev/null 2>&1 || true
}

# Main execution
main() {
    # Set trap for cleanup
    trap cleanup EXIT
    
    emergency_banner
    confirm_rollback
    check_prerequisites
    
    local start_time
    start_time=$(date +%s)
    
    if perform_rollback; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Emergency rollback completed in ${duration} seconds"
        
        local report_file
        report_file=$(generate_rollback_report "SUCCESS")
        send_notifications "SUCCESS" "$report_file"
        
        echo
        echo -e "${GREEN}✅ EMERGENCY ROLLBACK SUCCESSFUL${NC}"
        echo "Duration: ${duration} seconds"
        echo "Report: $report_file"
        echo
        echo "Next steps:"
        echo "1. Monitor system stability"
        echo "2. Investigate root cause"
        echo "3. Plan proper fix and deployment"
        echo "4. Update incident documentation"
        
        exit 0
    else
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_error "Emergency rollback failed after ${duration} seconds"
        
        local report_file
        report_file=$(generate_rollback_report "FAILED")
        send_notifications "FAILED" "$report_file"
        
        echo
        echo -e "${RED}❌ EMERGENCY ROLLBACK FAILED${NC}"
        echo "Duration: ${duration} seconds"
        echo "Report: $report_file"
        echo
        echo "IMMEDIATE ACTIONS REQUIRED:"
        echo "1. Escalate to senior engineering team"
        echo "2. Consider manual intervention"
        echo "3. Contact infrastructure team"
        echo "4. Prepare for potential downtime"
        
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
Emergency Rollback Script for autoDMCA Platform

Usage: $0 [ENVIRONMENT] [ROLLBACK_TYPE] [BACKUP_RESTORE]

Parameters:
  ENVIRONMENT    Target environment (default: production)
  ROLLBACK_TYPE  Type of rollback to perform:
                 - auto: Automatic deployment rollback (default)
                 - manual: Manual deployment rollback with confirmation
                 - blue-green: Blue-green environment switch
                 - database: Database restore only
                 - full: Full rollback including database
  BACKUP_RESTORE Whether to restore database backup (true/false, default: false)

Examples:
  $0 production auto false          # Quick deployment rollback
  $0 production blue-green false    # Switch blue-green environments
  $0 production full true           # Full rollback with database restore
  $0 staging manual false           # Manual staging rollback

Prerequisites:
  - kubectl configured and authenticated
  - Sufficient permissions for target namespace
  - Database backups available (if BACKUP_RESTORE=true)

Emergency Contacts:
  - On-call Engineer: +1-XXX-XXX-XXXX
  - Platform Team: platform@company.com
  - DevOps Escalation: devops-emergency@company.com
EOF
}

# Script execution
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi