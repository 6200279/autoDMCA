#!/bin/bash
# Production Rollback Script for AutoDMCA Platform
# Provides safe rollback mechanisms with validation

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-production}"
TIMEOUT="${TIMEOUT:-300}"
ROLLBACK_STEPS="${ROLLBACK_STEPS:-1}"
BACKUP_RESTORE="${BACKUP_RESTORE:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Help function
show_help() {
    cat << EOF
Production Rollback Script for AutoDMCA Platform

Usage: $0 [OPTIONS]

OPTIONS:
    --namespace NAMESPACE       Kubernetes namespace (default: production)
    --timeout SECONDS          Rollback timeout (default: 300)
    --steps NUMBER             Number of rollback steps (default: 1)
    --backup-restore           Also restore from backup
    --list-revisions           List available revisions
    --dry-run                  Show what would be done
    --help                     Show this help message

EXAMPLES:
    $0                         # Rollback 1 step
    $0 --steps 2               # Rollback 2 steps
    $0 --list-revisions        # Show available revisions
    $0 --backup-restore        # Rollback with backup restore

EOF
}

# Parse command line arguments
LIST_REVISIONS=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --steps)
            ROLLBACK_STEPS="$2"
            shift 2
            ;;
        --backup-restore)
            BACKUP_RESTORE=true
            shift
            ;;
        --list-revisions)
            LIST_REVISIONS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Function to execute commands with dry-run support
execute_command() {
    local cmd="$1"
    local description="$2"
    
    log_info "$description"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "[DRY RUN] Would execute: $cmd"
    else
        if ! eval "$cmd"; then
            log_error "Command failed: $cmd"
            return 1
        fi
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"
    
    # Check kubectl connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Check if deployments exist
    local deployments=("backend-prod" "frontend-prod" "celery-worker-scanning" "celery-worker-dmca")
    for deployment in "${deployments[@]}"; do
        if ! kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
            log_error "Deployment $deployment not found"
            exit 1
        fi
    done
    
    log_info "Prerequisites check passed"
}

# Function to list deployment revisions
list_deployment_revisions() {
    local deployment="$1"
    log_info "Revisions for $deployment:"
    kubectl rollout history deployment/"$deployment" -n "$NAMESPACE" || true
}

# Function to list all revisions
list_all_revisions() {
    log_header "Available Deployment Revisions"
    
    local deployments=("backend-prod" "frontend-prod" "celery-worker-scanning" "celery-worker-dmca" "celery-beat")
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
            echo
            list_deployment_revisions "$deployment"
        fi
    done
}

# Function to create pre-rollback snapshot
create_snapshot() {
    log_header "Creating Pre-Rollback Snapshot"
    
    local snapshot_file="rollback-snapshot-$(date +%Y%m%d-%H%M%S).yaml"
    
    execute_command \
        "kubectl get all,configmaps,secrets,pvc -n $NAMESPACE -o yaml > $snapshot_file" \
        "Creating snapshot: $snapshot_file"
    
    # Upload to S3 if configured
    if [[ -n "${BACKUP_BUCKET:-}" ]]; then
        execute_command \
            "aws s3 cp $snapshot_file s3://$BACKUP_BUCKET/rollback-snapshots/" \
            "Uploading snapshot to S3"
    fi
    
    echo "$snapshot_file"
}

# Function to backup current configuration
backup_current_config() {
    log_header "Backing Up Current Configuration"
    
    local backup_dir="rollback-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup deployment configurations
    kubectl get deployments -n "$NAMESPACE" -o yaml > "$backup_dir/deployments.yaml"
    kubectl get services -n "$NAMESPACE" -o yaml > "$backup_dir/services.yaml"
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml"
    kubectl get ingress -n "$NAMESPACE" -o yaml > "$backup_dir/ingress.yaml"
    
    log_info "Configuration backed up to $backup_dir"
    echo "$backup_dir"
}

# Function to drain traffic before rollback
drain_traffic() {
    log_header "Draining Traffic"
    
    # Scale down new deployment to prevent new traffic
    local deployments=("backend-prod" "frontend-prod")
    
    for deployment in "${deployments[@]}"; do
        local current_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        
        # Store original replica count for later restoration
        kubectl annotate deployment "$deployment" -n "$NAMESPACE" \
            rollback.autodmca.com/original-replicas="$current_replicas" --overwrite
        
        # Gradually scale down
        local target_replicas=$((current_replicas / 2))
        if [[ $target_replicas -lt 1 ]]; then
            target_replicas=1
        fi
        
        execute_command \
            "kubectl scale deployment $deployment -n $NAMESPACE --replicas=$target_replicas" \
            "Scaling down $deployment to $target_replicas replicas"
        
        # Wait for scale down
        kubectl wait --for=jsonpath='{.status.readyReplicas}'="$target_replicas" \
            deployment/"$deployment" -n "$NAMESPACE" --timeout=60s
    done
    
    log_info "Traffic drained, waiting 30 seconds for connections to close..."
    if [[ "$DRY_RUN" == "false" ]]; then
        sleep 30
    fi
}

# Function to rollback deployment
rollback_deployment() {
    local deployment="$1"
    local steps="$2"
    
    log_info "Rolling back $deployment by $steps step(s)"
    
    # Get current revision
    local current_revision=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')
    log_info "Current revision for $deployment: $current_revision"
    
    # Calculate target revision
    local target_revision=$((current_revision - steps))
    if [[ $target_revision -lt 1 ]]; then
        target_revision=1
        log_warn "Target revision adjusted to 1 (minimum)"
    fi
    
    # Perform rollback
    if [[ "$steps" -eq 1 ]]; then
        execute_command \
            "kubectl rollout undo deployment/$deployment -n $NAMESPACE" \
            "Rolling back $deployment to previous revision"
    else
        execute_command \
            "kubectl rollout undo deployment/$deployment -n $NAMESPACE --to-revision=$target_revision" \
            "Rolling back $deployment to revision $target_revision"
    fi
    
    # Wait for rollback to complete
    log_info "Waiting for $deployment rollback to complete..."
    if [[ "$DRY_RUN" == "false" ]]; then
        kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout="${TIMEOUT}s"
    fi
}

# Function to rollback all deployments
rollback_all_deployments() {
    log_header "Rolling Back All Deployments"
    
    local deployments=("backend-prod" "frontend-prod" "celery-worker-scanning" "celery-worker-dmca" "celery-beat")
    
    # Rollback critical deployments first
    local critical_deployments=("backend-prod" "frontend-prod")
    
    for deployment in "${critical_deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
            rollback_deployment "$deployment" "$ROLLBACK_STEPS"
        fi
    done
    
    # Wait a bit before rolling back workers
    if [[ "$DRY_RUN" == "false" ]]; then
        sleep 30
    fi
    
    # Rollback worker deployments
    local worker_deployments=("celery-worker-scanning" "celery-worker-dmca" "celery-beat")
    
    for deployment in "${worker_deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
            rollback_deployment "$deployment" "$ROLLBACK_STEPS" &
        fi
    done
    
    # Wait for all background rollbacks to complete
    wait
}

# Function to restore from backup
restore_from_backup() {
    log_header "Restoring from Backup"
    
    if [[ "$BACKUP_RESTORE" != "true" ]]; then
        log_info "Backup restore not requested, skipping..."
        return 0
    fi
    
    # This would depend on your backup solution
    # Example for AWS RDS Point-in-Time Recovery
    if [[ -n "${RDS_INSTANCE_ID:-}" ]]; then
        log_info "Initiating RDS point-in-time recovery..."
        
        local restore_time=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%S.000Z')
        
        execute_command \
            "aws rds restore-db-instance-to-point-in-time \
                --source-db-instance-identifier $RDS_INSTANCE_ID \
                --target-db-instance-identifier $RDS_INSTANCE_ID-rollback-$(date +%s) \
                --restore-time $restore_time" \
            "Creating RDS point-in-time recovery"
    fi
    
    # Example for S3 backup restore
    if [[ -n "${BACKUP_BUCKET:-}" ]]; then
        log_info "Restoring from S3 backup..."
        # Implementation would depend on your backup strategy
    fi
}

# Function to validate rollback
validate_rollback() {
    log_header "Validating Rollback"
    
    # Run health checks
    if [[ -f "scripts/comprehensive-health-check.sh" ]]; then
        log_info "Running comprehensive health checks..."
        ./scripts/comprehensive-health-check.sh "$NAMESPACE"
    else
        log_warn "Health check script not found, running basic validation"
        
        # Basic validation
        local deployments=("backend-prod" "frontend-prod")
        
        for deployment in "${deployments[@]}"; do
            if kubectl get deployment "$deployment" -n "$NAMESPACE" >/dev/null 2>&1; then
                local ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
                local desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
                
                if [[ "$ready_replicas" -eq "$desired_replicas" ]]; then
                    log_info "✅ $deployment: $ready_replicas/$desired_replicas replicas ready"
                else
                    log_error "❌ $deployment: $ready_replicas/$desired_replicas replicas ready"
                    return 1
                fi
            fi
        done
    fi
}

# Function to restore traffic
restore_traffic() {
    log_header "Restoring Traffic"
    
    local deployments=("backend-prod" "frontend-prod")
    
    for deployment in "${deployments[@]}"; do
        # Get original replica count
        local original_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" \
            -o jsonpath='{.metadata.annotations.rollback\.autodmca\.com/original-replicas}' 2>/dev/null || echo "3")
        
        execute_command \
            "kubectl scale deployment $deployment -n $NAMESPACE --replicas=$original_replicas" \
            "Restoring $deployment to $original_replicas replicas"
        
        # Wait for scale up
        if [[ "$DRY_RUN" == "false" ]]; then
            kubectl wait --for=jsonpath='{.status.readyReplicas}'="$original_replicas" \
                deployment/"$deployment" -n "$NAMESPACE" --timeout=300s
        fi
        
        # Remove annotation
        execute_command \
            "kubectl annotate deployment $deployment -n $NAMESPACE rollback.autodmca.com/original-replicas-" \
            "Cleaning up rollback annotations"
    done
}

# Function to notify about rollback
notify_rollback() {
    log_header "Sending Notifications"
    
    local message="🔄 Production rollback completed for AutoDMCA platform"
    message+="\n• Namespace: $NAMESPACE"
    message+="\n• Rollback Steps: $ROLLBACK_STEPS"
    message+="\n• Backup Restore: $BACKUP_RESTORE"
    message+="\n• Time: $(date)"
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        execute_command \
            "curl -X POST -H 'Content-type: application/json' \
                --data '{\"text\":\"$message\"}' \
                $SLACK_WEBHOOK_URL" \
            "Sending Slack notification"
    fi
    
    # Email notification (if configured)
    if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        execute_command \
            "echo '$message' | mail -s 'AutoDMCA Production Rollback Completed' $NOTIFICATION_EMAIL" \
            "Sending email notification"
    fi
    
    log_info "Notifications sent"
}

# Main rollback function
main() {
    log_info "Starting production rollback for AutoDMCA platform"
    log_info "Namespace: $NAMESPACE"
    log_info "Rollback Steps: $ROLLBACK_STEPS"
    log_info "Backup Restore: $BACKUP_RESTORE"
    log_info "Dry Run: $DRY_RUN"
    
    # Handle list revisions request
    if [[ "$LIST_REVISIONS" == "true" ]]; then
        list_all_revisions
        exit 0
    fi
    
    # Pre-rollback checks
    check_prerequisites
    
    # Create snapshot
    local snapshot_file
    snapshot_file=$(create_snapshot)
    
    # Backup current config
    local backup_dir
    backup_dir=$(backup_current_config)
    
    # Drain traffic
    drain_traffic
    
    # Perform rollback
    rollback_all_deployments
    
    # Restore from backup if requested
    restore_from_backup
    
    # Validate rollback
    if ! validate_rollback; then
        log_error "Rollback validation failed!"
        exit 1
    fi
    
    # Restore traffic
    restore_traffic
    
    # Final validation
    if ! validate_rollback; then
        log_error "Final validation failed after traffic restoration!"
        exit 1
    fi
    
    # Send notifications
    notify_rollback
    
    log_info "=== Production Rollback Completed Successfully ==="
    log_info "Snapshot saved: $snapshot_file"
    log_info "Configuration backed up: $backup_dir"
    
    # Cleanup recommendations
    echo
    log_info "Post-rollback recommendations:"
    log_info "1. Monitor application metrics for 30 minutes"
    log_info "2. Check error logs for any issues"
    log_info "3. Verify all integrations are working"
    log_info "4. Update incident documentation"
    log_info "5. Schedule post-incident review"
}

# Trap to handle interruption
trap 'log_error "Rollback interrupted! Manual intervention may be required."; exit 1' INT TERM

# Run main function
main "$@"