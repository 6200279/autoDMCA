# Local Testing Guide - Content Protection Platform

## Overview
This guide provides step-by-step instructions for testing the Content Protection Platform locally using Docker Compose before production deployment.

## Prerequisites
- Docker Desktop installed and running
- Git repository cloned locally
- 8GB+ RAM available
- Ports 3000, 8000, 5432, 6379, 3001, 9090, 9200 available

---

## 🚀 **Quick Start**

### 1. Prepare Environment
```bash
# Navigate to project directory
cd C:\Users\stijn\autoDMCA

# Copy local environment files (already created)
# .env.local (backend configuration)
# frontend/.env.local (frontend configuration)

# Verify Docker is running
docker --version
docker-compose --version
```

### 2. Start Core Services
```bash
# Start databases first
docker-compose -f docker-compose.production.yml --env-file .env.local up -d postgres redis

# Wait for databases to initialize
timeout 30

# Check database status
docker-compose -f docker-compose.production.yml logs postgres
docker-compose -f docker-compose.production.yml logs redis
```

### 3. Initialize Database
```bash
# Run database migrations
docker-compose -f docker-compose.production.yml --env-file .env.local exec backend python -m alembic upgrade head

# Create test admin user
docker-compose -f docker-compose.production.yml --env-file .env.local exec backend python -c "
from app.db.init_db import init_db
from app.db.session import SessionLocal
init_db(SessionLocal())
print('Database initialized with test admin user')
"
```

### 4. Start Application Services
```bash
# Start backend API
docker-compose -f docker-compose.production.yml --env-file .env.local up -d backend

# Wait for backend to be ready
timeout 30

# Start frontend
docker-compose -f docker-compose.production.yml --env-file .env.local up -d frontend

# Start Celery workers (background tasks)
docker-compose -f docker-compose.production.yml --env-file .env.local up -d celery-worker celery-scheduler
```

### 5. Start Monitoring (Optional)
```bash
# Start monitoring stack
docker-compose -f docker-compose.production.yml --env-file .env.local up -d grafana prometheus elasticsearch kibana

# Wait for services to start
timeout 60
```

---

## 🧪 **Testing Checklist**

### Core Infrastructure Tests
- [ ] **Database Connection**: `docker-compose exec postgres psql -U postgres -d contentprotection -c "SELECT 1;"`
- [ ] **Redis Connection**: `docker-compose exec redis redis-cli ping`
- [ ] **Backend Health**: `curl http://localhost:8000/health`
- [ ] **Frontend Loading**: `curl http://localhost:3000`

### Application Functionality Tests
- [ ] **User Registration**: Test via frontend UI
- [ ] **User Login**: Test authentication flow
- [ ] **Profile Creation**: Create a test profile
- [ ] **File Upload**: Test image upload functionality
- [ ] **DMCA Submission**: Submit a test DMCA request
- [ ] **API Endpoints**: Test key API endpoints

### Integration Tests
- [ ] **WebSocket Connection**: Test real-time notifications
- [ ] **Background Jobs**: Test Celery task processing
- [ ] **Database Persistence**: Restart services and verify data
- [ ] **Error Handling**: Test error scenarios

### Performance Tests
- [ ] **Response Times**: API responses < 2 seconds
- [ ] **Memory Usage**: Monitor Docker container memory
- [ ] **Concurrent Users**: Test multiple browser sessions

---

## 🔍 **Validation Commands**

### Quick Health Check
```bash
# Check all service status
docker-compose -f docker-compose.production.yml ps

# Test key endpoints
curl -f http://localhost:8000/health || echo "Backend health check failed"
curl -f http://localhost:3000 || echo "Frontend not accessible"

# Check logs for errors
docker-compose -f docker-compose.production.yml logs --tail=50 backend
docker-compose -f docker-compose.production.yml logs --tail=50 frontend
```

### Database Validation
```bash
# Test database connection
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d contentprotection -c "
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
"

# Check for test data
docker-compose -f docker-compose.production.yml exec postgres psql -U postgres -d contentprotection -c "
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as profile_count FROM profiles;
"
```

### API Testing
```bash
# Test authentication endpoint
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@contentprotection.com","password":"changeme123!"}'

# Test protected endpoint (replace TOKEN with actual token)
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/auth/me

# Test scanning endpoint
curl -X GET http://localhost:8000/api/v1/scan/history \
  -H "Authorization: Bearer TOKEN"
```

---

## 🐛 **Troubleshooting**

### Common Issues

**Services Won't Start**
```bash
# Check port conflicts
netstat -tuln | grep -E "(3000|8000|5432|6379)"

# Check Docker resources
docker system df
docker system prune -f

# Restart Docker Desktop if needed
```

**Database Connection Errors**
```bash
# Reset database volume
docker-compose -f docker-compose.production.yml down -v
docker volume rm autoDMCA_postgres-data

# Restart with fresh database
docker-compose -f docker-compose.production.yml --env-file .env.local up -d postgres
```

**Frontend Build Issues**
```bash
# Clear frontend cache
cd frontend
npm run clean
npm install
npm run build

# Restart frontend container
docker-compose -f docker-compose.production.yml restart frontend
```

**Memory Issues**
```bash
# Increase Docker Desktop memory allocation to 8GB+
# Stop unnecessary containers
docker stop $(docker ps -q)

# Start only essential services
docker-compose -f docker-compose.production.yml --env-file .env.local up -d postgres redis backend frontend
```

### Log Analysis
```bash
# View real-time logs
docker-compose -f docker-compose.production.yml logs -f backend

# Search for specific errors
docker-compose -f docker-compose.production.yml logs backend | grep -i error

# Check startup sequence
docker-compose -f docker-compose.production.yml logs --timestamps backend | head -50
```

---

## 📊 **Monitoring Access**

### Local Monitoring URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (admin/localadmin123)
- **Prometheus**: http://localhost:9090
- **Kibana**: http://localhost:5601

### Service Status Dashboard
```bash
# Create simple status check script
cat > check_services.sh << 'EOF'
#!/bin/bash
echo "=== Service Status ==="
echo "Frontend (3000): $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)"
echo "Backend (8000): $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)"
echo "Grafana (3001): $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)"
echo "Prometheus (9090): $(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090)"
echo ""
echo "=== Container Status ==="
docker-compose -f docker-compose.production.yml ps
EOF

chmod +x check_services.sh
```

---

## 🎯 **Success Criteria**

### ✅ Local Testing Complete When:
1. **All Core Services Running**: postgres, redis, backend, frontend
2. **Health Checks Passing**: All endpoints return 200 status
3. **User Authentication Working**: Login/register functionality
4. **Basic Workflows Functional**: Profile creation, DMCA submission
5. **No Critical Errors**: Clean logs with no blocking errors
6. **Data Persistence Confirmed**: Data survives service restarts

### ⚡ Quick Success Test
```bash
# One-command validation
./check_services.sh && echo "✅ Local testing ready for production deployment!"
```

---

## 🚀 **Next Steps**

After successful local testing:
1. **Document any issues found and resolved**
2. **Create production deployment plan**
3. **Prepare Dokploy configuration files**
4. **Schedule production deployment**

---

**Testing Time Estimate**: 2-4 hours
**Prerequisites**: Docker Desktop, 8GB+ RAM
**Support**: Check logs and troubleshooting section for common issues