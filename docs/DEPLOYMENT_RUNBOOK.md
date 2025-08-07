# AutoDMCA Platform Deployment Runbook

## Overview

This runbook provides comprehensive procedures for deploying, monitoring, and maintaining the AutoDMCA content protection platform in production environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Post-Deployment Validation](#post-deployment-validation)
4. [Rollback Procedures](#rollback-procedures)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Procedures](#emergency-procedures)
8. [Maintenance Tasks](#maintenance-tasks)

---

## Pre-Deployment Checklist

### Infrastructure Validation

- [ ] **Kubernetes Cluster Health**
  ```bash
  kubectl cluster-info
  kubectl get nodes
  kubectl top nodes  # Check resource usage
  ```

- [ ] **Namespace and RBAC**
  ```bash
  kubectl get namespace production
  kubectl auth can-i create deployments --namespace=production
  ```

- [ ] **Storage and Persistence**
  ```bash
  kubectl get pv
  kubectl get pvc -n production
  ```

- [ ] **Secrets and ConfigMaps**
  ```bash
  kubectl get secrets -n production
  kubectl get configmaps -n production
  ```

### Application Readiness

- [ ] **Container Images Built and Pushed**
  - Backend image: `ghcr.io/org/autodmca-backend:tag`
  - Frontend image: `ghcr.io/org/autodmca-frontend:tag`
  
- [ ] **Database Migration Status**
  ```bash
  # Check current migration status
  kubectl exec -n production deployment/backend-prod -- alembic current
  ```

- [ ] **External Dependencies**
  - [ ] Database connectivity (PostgreSQL)
  - [ ] Redis connectivity
  - [ ] S3 bucket accessibility
  - [ ] External API endpoints (Stripe, OpenAI, etc.)

### Security Checks

- [ ] **SSL Certificates Valid**
  ```bash
  curl -I https://api.autodmca.com
  openssl s_client -connect api.autodmca.com:443 -servername api.autodmca.com
  ```

- [ ] **Secrets Rotation** (if required)
- [ ] **WAF Rules Active**
- [ ] **Network Policies Applied**

---

## Deployment Procedures

### Standard Blue-Green Deployment

#### 1. Pre-Deployment Backup

```bash
# Create deployment snapshot
kubectl get all,configmaps,secrets,pvc -n production -o yaml > backup-$(date +%s).yaml

# Upload to S3
aws s3 cp backup-*.yaml s3://autodmca-backups/deployments/
```

#### 2. Deploy New Version

```bash
# Using the blue-green deployment script
./scripts/blue-green-deployment.sh \
  --backend-image ghcr.io/org/autodmca-backend:v1.2.0 \
  --frontend-image ghcr.io/org/autodmca-frontend:v1.2.0 \
  --namespace production \
  --timeout 900
```

#### 3. Manual Deployment Steps (if script unavailable)

```bash
# 1. Determine current color
CURRENT_COLOR=$(kubectl get service backend-service -n production -o jsonpath='{.spec.selector.version}')
NEXT_COLOR=$([ "$CURRENT_COLOR" = "blue" ] && echo "green" || echo "blue")

# 2. Update deployment manifests
sed -i "s/IMAGE_TAG_BACKEND/ghcr.io\/org\/autodmca-backend:v1.2.0/g" k8s/production/backend-deployment.yaml
sed -i "s/IMAGE_TAG_FRONTEND/ghcr.io\/org\/autodmca-frontend:v1.2.0/g" k8s/production/frontend-deployment.yaml
sed -i "s/version: blue/version: $NEXT_COLOR/g" k8s/production/*-deployment.yaml

# 3. Apply new deployments
kubectl apply -f k8s/production/backend-deployment.yaml
kubectl apply -f k8s/production/frontend-deployment.yaml

# 4. Wait for rollout
kubectl rollout status deployment/backend-prod -n production --timeout=600s
kubectl rollout status deployment/frontend-prod -n production --timeout=600s

# 5. Run health checks
./scripts/comprehensive-health-check.sh production

# 6. Switch traffic
kubectl patch service backend-service -n production -p '{"spec":{"selector":{"version":"'$NEXT_COLOR'"}}}'
kubectl patch service frontend-service -n production -p '{"spec":{"selector":{"version":"'$NEXT_COLOR'"}}}'
```

### Canary Deployment (Advanced)

#### 1. Deploy Canary Version

```bash
# Create canary deployments with 10% traffic
kubectl apply -f k8s/production/canary/
kubectl annotate service backend-service -n production nginx.ingress.kubernetes.io/canary-weight="10"
```

#### 2. Monitor Canary Metrics

```bash
# Monitor for 15 minutes
./scripts/canary-analysis.sh 900

# Check error rates
kubectl exec -n monitoring deployment/prometheus -- \
  promtool query instant 'rate(http_requests_total{deployment="backend-canary",status=~"5.."}[5m])'
```

#### 3. Promote or Rollback Canary

```bash
# If metrics are good, promote to full deployment
./scripts/promote-canary.sh

# If issues detected, rollback
kubectl delete -f k8s/production/canary/
kubectl annotate service backend-service -n production nginx.ingress.kubernetes.io/canary-weight-
```

---

## Post-Deployment Validation

### Automated Health Checks

```bash
# Comprehensive health check
./scripts/comprehensive-health-check.sh production

# Performance validation
./scripts/performance-validation.sh
```

### Manual Validation Steps

#### 1. Application Health

- [ ] **Health Endpoints**
  ```bash
  curl -f https://api.autodmca.com/health
  curl -f https://api.autodmca.com/api/v1/health
  curl -f https://autodmca.com/health
  ```

- [ ] **Database Connectivity**
  ```bash
  kubectl exec -n production deployment/backend-prod -- \
    python -c "from app.db.session import engine; print(engine.execute('SELECT 1').scalar())"
  ```

- [ ] **Redis Connectivity**
  ```bash
  kubectl exec -n production deployment/backend-prod -- \
    python -c "import redis; from app.core.config import settings; redis.from_url(settings.REDIS_URL).ping()"
  ```

#### 2. Critical User Flows

- [ ] **User Registration/Login**
- [ ] **File Upload**
- [ ] **DMCA Takedown Submission**
- [ ] **Payment Processing** (if applicable)
- [ ] **API Authentication**

#### 3. Integration Tests

```bash
# Run API integration tests
kubectl run api-test --rm -i --restart=Never --image=curlimages/curl:8.1.0 -- \
  curl -X POST https://api.autodmca.com/api/v1/auth/test
```

#### 4. Monitoring Validation

- [ ] **Metrics Collection**
  - Check Prometheus targets: `https://prometheus.autodmca.com/targets`
  - Verify Grafana dashboards: `https://grafana.autodmca.com`

- [ ] **Log Aggregation**
  - Check Kibana: `https://logs.autodmca.com`
  - Verify log ingestion rates

- [ ] **Alerting**
  - Test alert rules
  - Verify notification channels

---

## Rollback Procedures

### Automatic Rollback (in CI/CD)

The GitHub Actions pipeline includes automatic rollback triggers:

- Health check failures
- High error rates (>5%)
- Response time degradation (>2s average)

### Manual Rollback

#### 1. Quick Rollback (Last Known Good)

```bash
./scripts/rollback-production.sh --steps 1
```

#### 2. Rollback to Specific Version

```bash
# List available revisions
kubectl rollout history deployment/backend-prod -n production

# Rollback to specific revision
kubectl rollout undo deployment/backend-prod -n production --to-revision=5
kubectl rollout undo deployment/frontend-prod -n production --to-revision=3
```

#### 3. Emergency Rollback with Database Restore

```bash
./scripts/rollback-production.sh --steps 2 --backup-restore
```

#### 4. Traffic Switching Rollback

```bash
# Switch traffic back to blue deployment
kubectl patch service backend-service -n production -p '{"spec":{"selector":{"version":"blue"}}}'
kubectl patch service frontend-service -n production -p '{"spec":{"selector":{"version":"blue"}}}'
```

---

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics

- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Response Time**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **Active Users**: `active_users_count`

#### Infrastructure Metrics

- **CPU Usage**: `rate(container_cpu_usage_seconds_total[5m])`
- **Memory Usage**: `container_memory_usage_bytes`
- **Disk Usage**: `node_filesystem_avail_bytes`
- **Network I/O**: `rate(container_network_receive_bytes_total[5m])`

#### Business Metrics

- **DMCA Submissions**: `dmca_submissions_total`
- **Success Rate**: `dmca_success_rate`
- **Processing Time**: `dmca_processing_duration_seconds`

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error Rate | >1% | >5% |
| Response Time (95th) | >1s | >2s |
| CPU Usage | >70% | >90% |
| Memory Usage | >80% | >95% |
| Disk Usage | >80% | >90% |

### Alert Response Procedures

#### High Error Rate Alert

1. Check application logs
2. Verify database connectivity
3. Check external service status
4. Consider rollback if errors persist

#### High Response Time Alert

1. Check resource utilization
2. Review database performance
3. Check for traffic spikes
4. Scale horizontally if needed

#### Infrastructure Alert

1. Check node health
2. Verify resource availability
3. Review recent deployments
4. Scale cluster if necessary

---

## Troubleshooting

### Common Issues and Solutions

#### Deployment Stuck in Pending

```bash
# Check pod events
kubectl describe pod <pod-name> -n production

# Common causes:
# - Resource constraints
# - ImagePullBackOff
# - Node selector issues
# - PVC mounting problems
```

#### Service Unavailable (503)

```bash
# Check service endpoints
kubectl get endpoints -n production

# Check pod readiness
kubectl get pods -n production -o wide

# Check ingress configuration
kubectl describe ingress -n production
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -n production deployment/backend-prod -- \
  pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER

# Check connection pool
kubectl logs -n production deployment/backend-prod | grep "connection"
```

#### High Memory Usage

```bash
# Check memory metrics
kubectl top pods -n production --sort-by=memory

# Check for memory leaks
kubectl exec -n production <pod-name> -- ps aux --sort=-%mem
```

### Log Analysis

#### Application Logs

```bash
# Backend logs
kubectl logs -n production deployment/backend-prod -f

# Filter for errors
kubectl logs -n production deployment/backend-prod | grep ERROR

# Celery worker logs
kubectl logs -n production deployment/celery-worker-scanning -f
```

#### System Logs

```bash
# Kubernetes events
kubectl get events -n production --sort-by='.lastTimestamp'

# Node logs
kubectl describe node <node-name>
```

---

## Emergency Procedures

### Incident Response Checklist

#### Severity 1 (Critical - Service Down)

1. **Immediate Actions** (0-15 minutes)
   - [ ] Acknowledge incident
   - [ ] Start incident bridge
   - [ ] Check system status page
   - [ ] Begin rollback if recent deployment

2. **Assessment** (15-30 minutes)
   - [ ] Identify root cause
   - [ ] Determine impact scope
   - [ ] Estimate recovery time
   - [ ] Update stakeholders

3. **Mitigation** (30+ minutes)
   - [ ] Execute fix or rollback
   - [ ] Monitor recovery
   - [ ] Validate functionality
   - [ ] Update status page

#### Severity 2 (High - Degraded Service)

1. **Initial Response** (0-30 minutes)
   - [ ] Assess impact
   - [ ] Determine urgency
   - [ ] Start investigation
   - [ ] Monitor metrics

2. **Resolution** (30+ minutes)
   - [ ] Implement fix
   - [ ] Test solution
   - [ ] Monitor improvement
   - [ ] Document resolution

### Emergency Contacts

- **On-Call Engineer**: +1-xxx-xxx-xxxx
- **Platform Team Lead**: email@company.com
- **DevOps Manager**: email@company.com
- **CTO**: email@company.com

### Communication Templates

#### Incident Start

```
🚨 INCIDENT ALERT - AutoDMCA Platform
Status: Investigating
Impact: [Description]
Started: [Time]
Updates: Every 15 minutes
```

#### Incident Update

```
📝 INCIDENT UPDATE - AutoDMCA Platform
Status: [Investigating/Mitigating/Resolved]
Root Cause: [Description or "Still investigating"]
ETA: [If known]
Next Update: [Time]
```

#### Incident Resolution

```
✅ INCIDENT RESOLVED - AutoDMCA Platform
Duration: [Time]
Root Cause: [Summary]
Resolution: [Actions taken]
Post-Incident Review: [Date/Time]
```

---

## Maintenance Tasks

### Daily Tasks

- [ ] Check system health dashboard
- [ ] Review error logs for anomalies
- [ ] Monitor resource utilization
- [ ] Verify backup completion

### Weekly Tasks

- [ ] Review performance metrics trends
- [ ] Check security alerts
- [ ] Update dependency vulnerabilities
- [ ] Test disaster recovery procedures

### Monthly Tasks

- [ ] Review and update runbooks
- [ ] Conduct security assessment
- [ ] Capacity planning review
- [ ] Team knowledge sharing session

### Quarterly Tasks

- [ ] Disaster recovery drill
- [ ] Security penetration testing
- [ ] Performance baseline review
- [ ] Infrastructure cost optimization

---

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Monitoring Guide](https://prometheus.io/docs/)
- [Grafana Dashboard Configuration](https://grafana.com/docs/)
- [AWS EKS Best Practices](https://docs.aws.amazon.com/eks/latest/userguide/best-practices.html)

---

*Last Updated: 2024-08-07*  
*Version: 1.0*  
*Owner: Platform Engineering Team*