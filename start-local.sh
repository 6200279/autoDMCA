#!/bin/bash

# Quick Start Script for Local Testing
# Content Protection Platform

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# Main function
main() {
    echo -e "${BLUE}Content Protection Platform - Local Quick Start${NC}"
    echo -e "${BLUE}==============================================${NC}"
    echo
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        warn "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    
    # Check environment files
    if [[ ! -f ".env.local" ]]; then
        warn "Local environment file not found. Please ensure .env.local exists."
        exit 1
    fi
    
    info "Starting Content Protection Platform locally..."
    echo
    
    # Step 1: Start core services
    info "Step 1/5: Starting core services (PostgreSQL, Redis)..."
    docker-compose -f docker-compose.production.yml --env-file .env.local up -d postgres redis
    
    echo "Waiting for databases to initialize..."
    sleep 30
    
    # Step 2: Initialize database
    info "Step 2/5: Initializing database..."
    docker-compose -f docker-compose.production.yml --env-file .env.local exec -T backend python -m alembic upgrade head 2>/dev/null || {
        warn "Database migration failed. Backend may not be ready yet."
        info "Starting backend first..."
        docker-compose -f docker-compose.production.yml --env-file .env.local up -d backend
        sleep 30
        docker-compose -f docker-compose.production.yml --env-file .env.local exec -T backend python -m alembic upgrade head
    }
    
    # Step 3: Start application services
    info "Step 3/5: Starting application services..."
    docker-compose -f docker-compose.production.yml --env-file .env.local up -d backend frontend celery-worker
    
    echo "Waiting for application services to start..."
    sleep 30
    
    # Step 4: Start monitoring (optional)
    info "Step 4/5: Starting monitoring services (optional)..."
    docker-compose -f docker-compose.production.yml --env-file .env.local up -d grafana prometheus || {
        warn "Monitoring services failed to start (this is optional for testing)"
    }
    
    # Step 5: Validate deployment
    info "Step 5/5: Validating deployment..."
    sleep 15
    
    # Quick health checks
    echo
    info "Checking service health..."
    
    # Check backend
    if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
        success "✓ Backend API is responding (http://localhost:8000)"
    else
        warn "✗ Backend API not responding yet (may need more time)"
    fi
    
    # Check frontend
    if curl -s -f http://localhost:3000 >/dev/null 2>&1; then
        success "✓ Frontend is accessible (http://localhost:3000)"
    else
        warn "✗ Frontend not accessible yet (may need more time)"
    fi
    
    # Check database
    if docker-compose -f docker-compose.production.yml --env-file .env.local exec -T postgres psql -U postgres -d contentprotection -c "SELECT 1;" >/dev/null 2>&1; then
        success "✓ Database connection working"
    else
        warn "✗ Database connection issues"
    fi
    
    echo
    success "Local deployment started!"
    echo
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000"
    echo "  API Docs:     http://localhost:8000/docs"
    echo "  Grafana:      http://localhost:3001 (admin/localadmin123)"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Open http://localhost:3000 in your browser"
    echo "  2. Test user registration and login"
    echo "  3. Run full validation: ./scripts/test-local.sh"
    echo "  4. Check service logs: docker-compose logs [service-name]"
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  View all services:  docker-compose -f docker-compose.production.yml ps"
    echo "  View logs:          docker-compose -f docker-compose.production.yml logs -f [service]"
    echo "  Stop all:           docker-compose -f docker-compose.production.yml down"
    echo "  Full validation:    ./scripts/test-local.sh"
    echo
}

# Handle command line arguments
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Local Quick Start Script"
    echo "Usage: $0"
    echo
    echo "This script starts all services for local testing:"
    echo "  - PostgreSQL and Redis databases"
    echo "  - Backend API and Frontend"
    echo "  - Background workers"
    echo "  - Monitoring services (optional)"
    echo
    echo "Prerequisites:"
    echo "  - Docker Desktop running"
    echo "  - .env.local file configured"
    echo "  - Ports 3000, 8000, 5432, 6379 available"
    echo
    exit 0
fi

# Run main function
main "$@"