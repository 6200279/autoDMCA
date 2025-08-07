#!/bin/bash
# Blue-Green Deployment Script for AutoDMCA Platform
# This script implements a safe blue-green deployment strategy with comprehensive validation

set -euo pipefail

# Default values
NAMESPACE="production"
TIMEOUT=600
BACKEND_IMAGE=""
FRONTEND_IMAGE=""
DRY_RUN=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Help function
show_help() {
    cat << EOF
Blue-Green Deployment Script for AutoDMCA Platform

Usage: $0 [OPTIONS]

OPTIONS:
    --backend-image IMAGE       Backend container image (required)
    --frontend-image IMAGE      Frontend container image (required)
    --namespace NAMESPACE       Kubernetes namespace (default: production)
    --timeout SECONDS          Deployment timeout (default: 600)
    --dry-run                   Show what would be done without executing
    --verbose                   Enable verbose logging
    --help                      Show this help message

EXAMPLES:
    $0 --backend-image ghcr.io/org/backend:v1.0.0 --frontend-image ghcr.io/org/frontend:v1.0.0
    $0 --backend-image backend:latest --frontend-image frontend:latest --namespace staging --dry-run

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-image)
            BACKEND_IMAGE="$2"
            shift 2
            ;;
        --frontend-image)
            FRONTEND_IMAGE="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
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

# Validate required parameters
if [[ -z "$BACKEND_IMAGE" || -z "$FRONTEND_IMAGE" ]]; then
    log_error "Backend and frontend images are required"
    show_help
    exit 1
fi

# Enable verbose logging if requested
if [[ "$VERBOSE" == "true" ]]; then
    set -x
fi

log_info "Starting Blue-Green deployment for AutoDMCA platform"
log_info "Backend Image: $BACKEND_IMAGE"
log_info "Frontend Image: $FRONTEND_IMAGE"
log_info "Namespace: $NAMESPACE"
log_info "Timeout: $TIMEOUT seconds"

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

# Function to check if deployment exists
deployment_exists() {
    local deployment_name="$1"
    kubectl get deployment "$deployment_name" -n "$NAMESPACE" &>/dev/null
}

# Function to get current deployment color
get_current_color() {
    local service_name="$1"
    local selector=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "")
    
    if [[ "$selector" == "blue" ]]; then
        echo "blue"
    elif [[ "$selector" == "green" ]]; then
        echo "green"
    else
        echo "blue"  # Default to blue for initial deployment
    fi
}

# Function to get next color
get_next_color() {
    local current_color="$1"
    if [[ "$current_color" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Function to wait for deployment rollout
wait_for_rollout() {
    local deployment_name="$1"
    local timeout="$2"
    
    log_info "Waiting for deployment $deployment_name to complete (timeout: ${timeout}s)"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! kubectl rollout status deployment/"$deployment_name" -n "$NAMESPACE" --timeout="${timeout}s"; then
            log_error "Deployment $deployment_name failed to complete within $timeout seconds"
            return 1
        fi
    fi
}

# Function to validate deployment health
validate_deployment_health() {
    local deployment_name="$1"
    local expected_replicas="$2"
    
    log_info "Validating health of deployment $deployment_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "[DRY RUN] Would validate health of $deployment_name"
        return 0
    fi
    
    # Check if all replicas are ready
    local ready_replicas=$(kubectl get deployment "$deployment_name" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    
    if [[ "$ready_replicas" -lt "$expected_replicas" ]]; then
        log_error "Deployment $deployment_name has only $ready_replicas ready replicas, expected $expected_replicas"
        return 1
    fi
    
    # Additional health checks
    local pods=$(kubectl get pods -n "$NAMESPACE" -l app="$deployment_name" --field-selector=status.phase=Running -o name | wc -l)
    
    if [[ "$pods" -lt "$expected_replicas" ]]; then
        log_error "Deployment $deployment_name has only $pods running pods, expected $expected_replicas"
        return 1
    fi
    
    log_info "Deployment $deployment_name is healthy with $ready_replicas/$expected_replicas replicas ready"
    return 0
}

# Function to run health checks
run_health_checks() {
    local service_name="$1"
    local health_endpoint="$2"
    local max_attempts=30
    local attempt=1
    
    log_info "Running health checks for $service_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "[DRY RUN] Would run health checks for $service_name"
        return 0
    fi
    
    # Get service endpoint
    local service_ip=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
    local service_port=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
    
    if [[ -z "$service_ip" || -z "$service_port" ]]; then
        log_error "Could not get service endpoint for $service_name"
        return 1
    fi
    
    local health_url="http://$service_ip:$service_port$health_endpoint"
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts for $health_url"
        
        if kubectl run health-check-$RANDOM --rm -i --restart=Never --image=curlimages/curl:8.1.0 -- \
           curl -f --connect-timeout 5 --max-time 10 "$health_url" >/dev/null 2>&1; then
            log_info "Health check passed for $service_name"
            return 0
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Health check failed for $service_name after $max_attempts attempts"
            return 1
        fi
        
        sleep 10
        ((attempt++))
    done
}

# Function to switch traffic
switch_traffic() {
    local service_name="$1"
    local target_color="$2"
    
    log_info "Switching traffic for $service_name to $target_color"
    
    execute_command \
        "kubectl patch service $service_name -n $NAMESPACE -p '{\"spec\":{\"selector\":{\"version\":\"$target_color\"}}}'" \
        "Updating service selector for $service_name to $target_color"
}

# Function to cleanup old deployment
cleanup_old_deployment() {
    local deployment_name="$1"
    local color_to_remove="$2"
    
    local old_deployment="${deployment_name}-${color_to_remove}"
    
    if deployment_exists "$old_deployment"; then
        log_info "Cleaning up old deployment: $old_deployment"
        
        execute_command \
            "kubectl scale deployment $old_deployment -n $NAMESPACE --replicas=0" \
            "Scaling down old deployment $old_deployment"
        
        # Wait a bit before deletion
        if [[ "$DRY_RUN" == "false" ]]; then
            sleep 30
        fi
        
        execute_command \
            "kubectl delete deployment $old_deployment -n $NAMESPACE --ignore-not-found=true" \
            "Deleting old deployment $old_deployment"
    fi
}

# Main deployment function
main() {
    log_info "=== Starting Blue-Green Deployment ==="
    
    # Pre-deployment validations
    log_info "Running pre-deployment validations..."
    
    # Check if kubectl is configured
    if ! kubectl cluster-info &>/dev/null; then
        log_error "kubectl is not configured or cluster is not accessible"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Determine current and next colors
    local backend_current_color=$(get_current_color "backend-service")
    local frontend_current_color=$(get_current_color "frontend-service")
    local next_color=$(get_next_color "$backend_current_color")
    
    log_info "Current backend color: $backend_current_color"
    log_info "Current frontend color: $frontend_current_color"
    log_info "Next deployment color: $next_color"
    
    # Create deployment manifests for the new color
    local backend_deployment="backend-prod-${next_color}"
    local frontend_deployment="frontend-prod-${next_color}"
    
    # Deploy backend
    log_info "=== Deploying Backend ($next_color) ==="
    
    cat <<EOF | kubectl apply -f - || exit 1
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $backend_deployment
  namespace: $NAMESPACE
  labels:
    app: backend
    version: $next_color
    environment: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: $next_color
  template:
    metadata:
      labels:
        app: backend
        version: $next_color
        environment: production
    spec:
      containers:
      - name: backend
        image: $BACKEND_IMAGE
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
EOF
    
    # Deploy frontend
    log_info "=== Deploying Frontend ($next_color) ==="
    
    cat <<EOF | kubectl apply -f - || exit 1
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $frontend_deployment
  namespace: $NAMESPACE
  labels:
    app: frontend
    version: $next_color
    environment: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
      version: $next_color
  template:
    metadata:
      labels:
        app: frontend
        version: $next_color
        environment: production
    spec:
      containers:
      - name: frontend
        image: $FRONTEND_IMAGE
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
EOF
    
    # Wait for deployments to be ready
    wait_for_rollout "$backend_deployment" "$TIMEOUT"
    wait_for_rollout "$frontend_deployment" "$TIMEOUT"
    
    # Validate deployment health
    validate_deployment_health "$backend_deployment" 3
    validate_deployment_health "$frontend_deployment" 3
    
    # Run health checks
    run_health_checks "backend-service" "/health"
    
    # Switch traffic to new deployments
    log_info "=== Switching Traffic ==="
    switch_traffic "backend-service" "$next_color"
    switch_traffic "frontend-service" "$next_color"
    
    # Wait and monitor for a bit
    log_info "Monitoring new deployment for 60 seconds..."
    if [[ "$DRY_RUN" == "false" ]]; then
        sleep 60
    fi
    
    # Run post-switch health checks
    run_health_checks "backend-service" "/health"
    
    # Clean up old deployments
    log_info "=== Cleaning Up Old Deployments ==="
    cleanup_old_deployment "backend-prod" "$backend_current_color"
    cleanup_old_deployment "frontend-prod" "$frontend_current_color"
    
    log_info "=== Blue-Green Deployment Completed Successfully ==="
    log_info "New deployment color: $next_color"
    log_info "Backend Image: $BACKEND_IMAGE"
    log_info "Frontend Image: $FRONTEND_IMAGE"
}

# Trap to handle script interruption
trap 'log_error "Deployment interrupted. Manual cleanup may be required."; exit 1' INT TERM

# Run main function
main "$@"