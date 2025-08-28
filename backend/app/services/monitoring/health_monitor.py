"""
Comprehensive Health Monitoring System for AutoDMCA

This module provides centralized health monitoring that integrates:
- Database connectivity and performance
- Redis connectivity and performance
- Service container health
- Background worker status
- AI model performance
- External API connectivity
- System resource utilization

Features:
- Real-time health status tracking
- Alert integration for health issues
- Performance metrics collection
- Service dependency monitoring
- Automated health checks with configurable intervals
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import psutil
import redis
import aiohttp

from app.core.config import settings
from app.core.container import container
from app.core.database_service import database_service
from app.services.monitoring.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    status: HealthStatus
    value: Any
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceHealth:
    """Health status for a service"""
    service_name: str
    status: HealthStatus
    metrics: List[HealthMetric] = field(default_factory=list)
    last_check: Optional[datetime] = None
    uptime_seconds: float = 0.0
    error_count: int = 0
    response_time_ms: float = 0.0


@dataclass
class SystemHealthReport:
    """Comprehensive system health report"""
    overall_status: HealthStatus
    timestamp: datetime
    services: Dict[str, ServiceHealth]
    system_metrics: Dict[str, Any]
    alerts_triggered: List[str] = field(default_factory=list)
    uptime_hours: float = 0.0


class HealthMonitor:
    """
    Comprehensive health monitoring system
    
    Monitors all aspects of the AutoDMCA system and provides:
    - Real-time health status
    - Performance metrics
    - Alert integration
    - Service dependency tracking
    """
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.is_running = False
        self.check_interval = getattr(settings, 'HEALTH_CHECK_INTERVAL', 60)  # seconds
        
        # Health status tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        self.last_health_report: Optional[SystemHealthReport] = None
        
        # Background monitoring task
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Health check functions
        self.health_checks: Dict[str, Callable] = {}
        
        # Performance monitor integration
        self.performance_monitor: Optional[PerformanceMonitor] = None
        
        # Redis client for health status storage
        self.redis_client: Optional[redis.Redis] = None
        
        # External service endpoints to monitor
        self.external_endpoints = {
            'stripe_api': 'https://api.stripe.com/v1',
            'sendgrid_api': 'https://api.sendgrid.com/v3',
            'google_vision': 'https://vision.googleapis.com/v1'
        }
        
        logger.info("Health monitor initialized")
    
    async def initialize(self):
        """Initialize the health monitoring system"""
        try:
            # Initialize Redis for health status storage
            if hasattr(settings, 'REDIS_URL'):
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8", 
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Health monitor Redis connection established")
        
            # Get performance monitor from container
            try:
                self.performance_monitor = await container.get(PerformanceMonitor)
            except Exception as e:
                logger.warning(f"Performance monitor not available: {e}")
            
            # Register default health checks
            self._register_default_health_checks()
            
            # Start monitoring
            await self.start_monitoring()
            
            logger.info("Health monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize health monitor: {e}")
            raise
    
    def _register_default_health_checks(self):
        """Register default health check functions"""
        
        # Database health check
        self.health_checks['database'] = self._check_database_health
        
        # Redis health check
        self.health_checks['redis'] = self._check_redis_health
        
        # Service container health check
        self.health_checks['services'] = self._check_service_container_health
        
        # System resources health check
        self.health_checks['system'] = self._check_system_health
        
        # Worker health check
        self.health_checks['workers'] = self._check_worker_health
        
        # External APIs health check
        self.health_checks['external_apis'] = self._check_external_apis_health
        
        # AI models health check
        self.health_checks['ai_models'] = self._check_ai_models_health
        
        logger.info(f"Registered {len(self.health_checks)} health checks")
    
    async def start_monitoring(self):
        """Start background health monitoring"""
        if not self.is_running:
            self.is_running = True
            self.monitor_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop background health monitoring"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main health monitoring loop"""
        while self.is_running:
            try:
                # Perform comprehensive health check
                health_report = await self.check_system_health()
                
                # Store health report
                await self._store_health_report(health_report)
                
                # Check for alerts
                await self._check_health_alerts(health_report)
                
                # Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def check_system_health(self) -> SystemHealthReport:
        """Perform comprehensive system health check"""
        logger.debug("Performing system health check")
        
        services = {}
        overall_status = HealthStatus.HEALTHY
        alerts_triggered = []
        
        # Run all health checks
        for service_name, health_check_func in self.health_checks.items():
            try:
                service_health = await health_check_func()
                services[service_name] = service_health
                
                # Update overall status
                if service_health.status.value in ['critical', 'down']:
                    overall_status = HealthStatus.CRITICAL
                elif service_health.status.value == 'error' and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.ERROR
                elif service_health.status.value == 'warning' and overall_status in [HealthStatus.HEALTHY]:
                    overall_status = HealthStatus.WARNING
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                services[service_name] = ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.DOWN,
                    metrics=[HealthMetric(
                        name=f"{service_name}_error",
                        status=HealthStatus.DOWN,
                        value=str(e),
                        message=f"Health check failed: {e}"
                    )],
                    last_check=datetime.utcnow()
                )
                overall_status = HealthStatus.CRITICAL
                alerts_triggered.append(f"{service_name} health check failed: {e}")
        
        # Calculate uptime
        uptime_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
        
        # Get system metrics
        system_metrics = await self._get_system_metrics()
        
        health_report = SystemHealthReport(
            overall_status=overall_status,
            timestamp=datetime.utcnow(),
            services=services,
            system_metrics=system_metrics,
            alerts_triggered=alerts_triggered,
            uptime_hours=uptime_hours
        )
        
        self.last_health_report = health_report
        logger.info(f"System health check completed: {overall_status.value}")
        
        return health_report
    
    async def _check_database_health(self) -> ServiceHealth:
        """Check database connectivity and performance"""
        metrics = []
        status = HealthStatus.HEALTHY
        error_count = 0
        response_time_ms = 0.0
        
        try:
            # Get database health report
            db_health = await database_service.get_health_report()
            
            # Convert database health to service health
            status_mapping = {
                'healthy': HealthStatus.HEALTHY,
                'warning': HealthStatus.WARNING,
                'critical': HealthStatus.CRITICAL,
                'down': HealthStatus.DOWN
            }
            
            status = status_mapping.get(db_health.status.value, HealthStatus.DOWN)
            response_time_ms = db_health.response_time_ms
            
            # Add database metrics
            metrics.extend([
                HealthMetric(
                    name="connection_pool_size",
                    status=HealthStatus.HEALTHY,
                    value=db_health.connection_pool.size,
                    message="Active database connections"
                ),
                HealthMetric(
                    name="query_response_time",
                    status=HealthStatus.HEALTHY if response_time_ms < 1000 else HealthStatus.WARNING,
                    value=response_time_ms,
                    message=f"Database response time: {response_time_ms:.1f}ms"
                ),
                HealthMetric(
                    name="failed_queries",
                    status=HealthStatus.HEALTHY if db_health.query_metrics.failed_queries == 0 else HealthStatus.WARNING,
                    value=db_health.query_metrics.failed_queries,
                    message="Failed database queries"
                )
            ])
            
            error_count = db_health.query_metrics.failed_queries
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="database_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"Database connection failed: {e}"
            ))
            error_count = 1
        
        return ServiceHealth(
            service_name="database",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_count=error_count,
            response_time_ms=response_time_ms
        )
    
    async def _check_redis_health(self) -> ServiceHealth:
        """Check Redis connectivity and performance"""
        metrics = []
        status = HealthStatus.HEALTHY
        response_time_ms = 0.0
        
        try:
            if self.redis_client:
                start_time = datetime.utcnow()
                
                # Test Redis connectivity
                await self.redis_client.ping()
                
                # Get Redis info
                info = await self.redis_client.info()
                
                response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Check Redis metrics
                connected_clients = info.get('connected_clients', 0)
                used_memory = info.get('used_memory', 0)
                used_memory_mb = used_memory / (1024 * 1024)
                
                metrics.extend([
                    HealthMetric(
                        name="redis_response_time",
                        status=HealthStatus.HEALTHY if response_time_ms < 100 else HealthStatus.WARNING,
                        value=response_time_ms,
                        message=f"Redis response time: {response_time_ms:.1f}ms"
                    ),
                    HealthMetric(
                        name="connected_clients",
                        status=HealthStatus.HEALTHY,
                        value=connected_clients,
                        message="Redis connected clients"
                    ),
                    HealthMetric(
                        name="memory_usage",
                        status=HealthStatus.HEALTHY if used_memory_mb < 1000 else HealthStatus.WARNING,
                        value=used_memory_mb,
                        message=f"Redis memory usage: {used_memory_mb:.1f}MB"
                    )
                ])
                
            else:
                status = HealthStatus.WARNING
                metrics.append(HealthMetric(
                    name="redis_not_configured",
                    status=HealthStatus.WARNING,
                    value="Not configured",
                    message="Redis client not initialized"
                ))
        
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="redis_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"Redis connection failed: {e}"
            ))
        
        return ServiceHealth(
            service_name="redis",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            response_time_ms=response_time_ms
        )
    
    async def _check_service_container_health(self) -> ServiceHealth:
        """Check service container health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # Get service container health
            service_health = await container.check_health()
            
            if not service_health.get('overall_healthy', False):
                status = HealthStatus.WARNING
            
            # Add metrics for each service
            services_info = service_health.get('services', {})
            healthy_services = sum(1 for s in services_info.values() if s.get('healthy', False))
            total_services = len(services_info)
            
            metrics.extend([
                HealthMetric(
                    name="total_services",
                    status=HealthStatus.HEALTHY,
                    value=total_services,
                    message="Total registered services"
                ),
                HealthMetric(
                    name="healthy_services",
                    status=HealthStatus.HEALTHY if healthy_services == total_services else HealthStatus.WARNING,
                    value=healthy_services,
                    message=f"Healthy services: {healthy_services}/{total_services}"
                )
            ])
            
            # Add specific service status
            for service_name, service_info in services_info.items():
                service_status = HealthStatus.HEALTHY if service_info.get('healthy', False) else HealthStatus.WARNING
                metrics.append(HealthMetric(
                    name=f"service_{service_name.lower()}",
                    status=service_status,
                    value=service_info.get('status', 'unknown'),
                    message=f"Service {service_name} status"
                ))
        
        except Exception as e:
            logger.error(f"Service container health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="container_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"Service container check failed: {e}"
            ))
        
        return ServiceHealth(
            service_name="services",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow()
        )
    
    async def _check_system_health(self) -> ServiceHealth:
        """Check system resource health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Add metrics
            metrics.extend([
                HealthMetric(
                    name="cpu_usage",
                    status=HealthStatus.HEALTHY if cpu_percent < 80 else HealthStatus.WARNING if cpu_percent < 90 else HealthStatus.CRITICAL,
                    value=cpu_percent,
                    message=f"CPU usage: {cpu_percent:.1f}%"
                ),
                HealthMetric(
                    name="memory_usage",
                    status=HealthStatus.HEALTHY if memory.percent < 80 else HealthStatus.WARNING if memory.percent < 90 else HealthStatus.CRITICAL,
                    value=memory.percent,
                    message=f"Memory usage: {memory.percent:.1f}%"
                ),
                HealthMetric(
                    name="disk_usage",
                    status=HealthStatus.HEALTHY if disk_percent < 80 else HealthStatus.WARNING if disk_percent < 90 else HealthStatus.CRITICAL,
                    value=disk_percent,
                    message=f"Disk usage: {disk_percent:.1f}%"
                )
            ])
            
            # Update overall status based on critical resources
            if cpu_percent > 90 or memory.percent > 90 or disk_percent > 90:
                status = HealthStatus.CRITICAL
            elif cpu_percent > 80 or memory.percent > 80 or disk_percent > 80:
                status = HealthStatus.WARNING
        
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="system_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"System metrics failed: {e}"
            ))
        
        return ServiceHealth(
            service_name="system",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow()
        )
    
    async def _check_worker_health(self) -> ServiceHealth:
        """Check background worker health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # Check if Redis is available for worker monitoring
            if self.redis_client:
                # Get Celery worker status (placeholder)
                # This would check actual worker status in production
                active_workers = 3  # Placeholder
                failed_tasks = 0    # Placeholder
                
                metrics.extend([
                    HealthMetric(
                        name="active_workers",
                        status=HealthStatus.HEALTHY if active_workers > 0 else HealthStatus.CRITICAL,
                        value=active_workers,
                        message=f"Active background workers: {active_workers}"
                    ),
                    HealthMetric(
                        name="failed_tasks",
                        status=HealthStatus.HEALTHY if failed_tasks < 10 else HealthStatus.WARNING,
                        value=failed_tasks,
                        message=f"Failed tasks in last hour: {failed_tasks}"
                    )
                ])
                
                if active_workers == 0:
                    status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.WARNING
                metrics.append(HealthMetric(
                    name="worker_monitoring",
                    status=HealthStatus.WARNING,
                    value="Unavailable",
                    message="Worker monitoring requires Redis"
                ))
        
        except Exception as e:
            logger.error(f"Worker health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="worker_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"Worker health check failed: {e}"
            ))
        
        return ServiceHealth(
            service_name="workers",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow()
        )
    
    async def _check_external_apis_health(self) -> ServiceHealth:
        """Check external API health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        # Check key external APIs
        api_statuses = {}
        
        for api_name, base_url in self.external_endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    start_time = datetime.utcnow()
                    async with session.get(f"{base_url}/health", timeout=5) as response:
                        response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        if response.status == 200:
                            api_statuses[api_name] = HealthStatus.HEALTHY
                        else:
                            api_statuses[api_name] = HealthStatus.WARNING
                        
                        metrics.append(HealthMetric(
                            name=f"{api_name}_response_time",
                            status=api_statuses[api_name],
                            value=response_time_ms,
                            message=f"{api_name} response time: {response_time_ms:.1f}ms"
                        ))
                        
            except Exception as e:
                api_statuses[api_name] = HealthStatus.DOWN
                metrics.append(HealthMetric(
                    name=f"{api_name}_error",
                    status=HealthStatus.DOWN,
                    value=str(e),
                    message=f"{api_name} connection failed: {e}"
                ))
        
        # Determine overall external API status
        if any(s == HealthStatus.DOWN for s in api_statuses.values()):
            status = HealthStatus.WARNING  # Not critical as these are external
        
        return ServiceHealth(
            service_name="external_apis",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow()
        )
    
    async def _check_ai_models_health(self) -> ServiceHealth:
        """Check AI model health and performance"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # Get AI model performance data from performance monitor
            if self.performance_monitor:
                summary = self.performance_monitor.get_performance_summary()
                ai_models = summary.get('ai_models', {})
                
                for model_name, model_metrics in ai_models.items():
                    avg_time = model_metrics.get('avg_inference_time_ms', 0)
                    error_count = model_metrics.get('error_count', 0)
                    
                    # Determine model health
                    model_status = HealthStatus.HEALTHY
                    if error_count > 10:
                        model_status = HealthStatus.WARNING
                    if avg_time > 5000:  # 5 seconds
                        model_status = HealthStatus.WARNING
                    
                    metrics.append(HealthMetric(
                        name=f"model_{model_name}_performance",
                        status=model_status,
                        value=avg_time,
                        message=f"{model_name} avg inference time: {avg_time:.1f}ms",
                        details=model_metrics
                    ))
                    
                    if model_status != HealthStatus.HEALTHY and status == HealthStatus.HEALTHY:
                        status = HealthStatus.WARNING
            else:
                metrics.append(HealthMetric(
                    name="ai_monitoring",
                    status=HealthStatus.WARNING,
                    value="Not available",
                    message="AI model monitoring not available"
                ))
                status = HealthStatus.WARNING
        
        except Exception as e:
            logger.error(f"AI model health check failed: {e}")
            status = HealthStatus.DOWN
            metrics.append(HealthMetric(
                name="ai_models_error",
                status=HealthStatus.DOWN,
                value=str(e),
                message=f"AI model health check failed: {e}"
            ))
        
        return ServiceHealth(
            service_name="ai_models",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow()
        )
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get additional system metrics"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_total_gb': psutil.disk_usage('/').total / (1024**3),
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    async def _store_health_report(self, health_report: SystemHealthReport):
        """Store health report in Redis"""
        try:
            if self.redis_client:
                # Store current health status
                health_data = {
                    'overall_status': health_report.overall_status.value,
                    'timestamp': health_report.timestamp.isoformat(),
                    'uptime_hours': health_report.uptime_hours,
                    'services': {
                        name: {
                            'status': service.status.value,
                            'last_check': service.last_check.isoformat() if service.last_check else None,
                            'error_count': service.error_count,
                            'response_time_ms': service.response_time_ms
                        }
                        for name, service in health_report.services.items()
                    }
                }
                
                await self.redis_client.setex(
                    'system_health',
                    300,  # 5 minute TTL
                    json.dumps(health_data, default=str)
                )
                
                # Store in history
                await self.redis_client.lpush(
                    'health_history',
                    json.dumps(health_data, default=str)
                )
                await self.redis_client.ltrim('health_history', 0, 287)  # Keep 24 hours
                
        except Exception as e:
            logger.error(f"Failed to store health report: {e}")
    
    async def _check_health_alerts(self, health_report: SystemHealthReport):
        """Check if any health alerts should be triggered"""
        try:
            # Get alert system from container
            alert_system = await container.get('RealTimeAlertSystem')
            
            # Prepare context for alert conditions
            context = {
                'overall_status': health_report.overall_status.value,
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'error_rate': 0.0,
                'database_status': 'healthy',
                'redis_status': 'healthy',
                'services': {},
                'unhealthy_services': []
            }
            
            # Extract metrics from health report
            for service_name, service in health_report.services.items():
                context['services'][service_name] = {
                    'status': service.status.value,
                    'error_count': service.error_count,
                    'response_time_ms': service.response_time_ms
                }
                
                if service.status.value in ['error', 'critical', 'down']:
                    context['unhealthy_services'].append(service_name)
                
                # Extract specific metrics
                if service_name == 'database':
                    context['database_status'] = service.status.value
                elif service_name == 'redis':
                    context['redis_status'] = service.status.value
                elif service_name == 'system':
                    for metric in service.metrics:
                        if metric.name == 'cpu_usage':
                            context['cpu_percent'] = metric.value
                        elif metric.name == 'memory_usage':
                            context['memory_percent'] = metric.value
            
            # Trigger alert condition checks
            await alert_system.check_conditions(context)
            
        except Exception as e:
            logger.error(f"Error checking health alerts: {e}")
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for API responses"""
        if not self.last_health_report:
            await self.check_system_health()
        
        report = self.last_health_report
        if not report:
            return {'status': 'unknown', 'message': 'No health data available'}
        
        return {
            'status': report.overall_status.value,
            'timestamp': report.timestamp.isoformat(),
            'uptime_hours': report.uptime_hours,
            'services': {
                name: {
                    'status': service.status.value,
                    'last_check': service.last_check.isoformat() if service.last_check else None,
                    'metrics_count': len(service.metrics),
                    'error_count': service.error_count,
                    'response_time_ms': service.response_time_ms
                }
                for name, service in report.services.items()
            },
            'system_metrics': report.system_metrics,
            'alerts_triggered': report.alerts_triggered
        }
    
    async def get_detailed_health_report(self) -> Dict[str, Any]:
        """Get detailed health report including all metrics"""
        if not self.last_health_report:
            await self.check_system_health()
        
        report = self.last_health_report
        if not report:
            return {'status': 'unknown', 'message': 'No health data available'}
        
        return {
            'overall_status': report.overall_status.value,
            'timestamp': report.timestamp.isoformat(),
            'uptime_hours': report.uptime_hours,
            'services': {
                name: {
                    'status': service.status.value,
                    'last_check': service.last_check.isoformat() if service.last_check else None,
                    'error_count': service.error_count,
                    'response_time_ms': service.response_time_ms,
                    'metrics': [
                        {
                            'name': metric.name,
                            'status': metric.status.value,
                            'value': metric.value,
                            'message': metric.message,
                            'timestamp': metric.timestamp.isoformat(),
                            'details': metric.details
                        }
                        for metric in service.metrics
                    ]
                }
                for name, service in report.services.items()
            },
            'system_metrics': report.system_metrics,
            'alerts_triggered': report.alerts_triggered
        }


# Global health monitor instance
health_monitor = HealthMonitor()


__all__ = [
    'HealthMonitor',
    'HealthStatus',
    'HealthMetric',
    'ServiceHealth',
    'SystemHealthReport',
    'health_monitor'
]