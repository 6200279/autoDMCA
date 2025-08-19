"""
Production Performance Monitoring and Alerting System
Real-time monitoring with automatic alerting and self-healing capabilities
"""
import asyncio
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import numpy as np

import psutil
import torch
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.config import settings
from app.services.monitoring.performance_monitor import performance_monitor
from app.services.performance.ai_performance_optimizer import ai_optimizer

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class PerformanceAlert:
    """Performance alert data"""
    timestamp: datetime
    severity: AlertSeverity
    component: str
    metric: str
    value: float
    threshold: float
    message: str
    action_taken: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class SLAMetrics:
    """Service Level Agreement metrics"""
    availability_percent: float = 99.9
    response_time_p95_ms: float = 2000.0
    response_time_p99_ms: float = 5000.0
    error_rate_percent: float = 1.0
    concurrent_users: int = 1000
    ai_inference_time_ms: float = 2000.0
    cache_hit_rate_percent: float = 70.0
    
    def is_compliant(self, metrics: Dict[str, float]) -> bool:
        """Check if metrics are SLA compliant"""
        return (
            metrics.get('availability', 0) >= self.availability_percent and
            metrics.get('response_time_p95', float('inf')) <= self.response_time_p95_ms and
            metrics.get('response_time_p99', float('inf')) <= self.response_time_p99_ms and
            metrics.get('error_rate', 100) <= self.error_rate_percent and
            metrics.get('concurrent_users', 0) >= self.concurrent_users and
            metrics.get('ai_inference_time', float('inf')) <= self.ai_inference_time_ms and
            metrics.get('cache_hit_rate', 0) >= self.cache_hit_rate_percent
        )


class ProductionMonitor:
    """
    Production-grade performance monitoring with self-healing
    
    Features:
    - Real-time performance tracking
    - Automatic alerting and escalation
    - Self-healing capabilities
    - SLA compliance monitoring
    - Predictive performance analysis
    - Distributed monitoring support
    """
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.is_running = False
        
        # SLA configuration
        self.sla = SLAMetrics()
        
        # Alert management
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_history: List[PerformanceAlert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Health tracking
        self.health_status = HealthStatus.HEALTHY
        self.health_checks: Dict[str, bool] = {}
        
        # Performance baselines
        self.baselines: Dict[str, float] = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        
        # Self-healing actions
        self.healing_enabled = True
        self.healing_actions: Dict[str, Callable] = {
            'high_memory': self._heal_memory,
            'slow_response': self._heal_slow_response,
            'high_error_rate': self._heal_error_rate,
            'cache_degradation': self._heal_cache
        }
        
        # Monitoring tasks
        self.monitor_tasks: List[asyncio.Task] = []
        
        # Redis for distributed monitoring
        self.redis_client: Optional[redis.Redis] = None
        
        # Webhook configuration for alerts
        self.webhook_url = getattr(settings, 'ALERT_WEBHOOK_URL', None)
        
        logger.info("Production monitor initialized")
    
    async def start(self):
        """Start production monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Initialize Redis
        await self._init_redis()
        
        # Start monitoring tasks
        self.monitor_tasks = [
            asyncio.create_task(self._monitor_performance()),
            asyncio.create_task(self._monitor_health()),
            asyncio.create_task(self._monitor_sla()),
            asyncio.create_task(self._monitor_anomalies()),
            asyncio.create_task(self._process_alerts())
        ]
        
        # Initialize baselines
        await self._establish_baselines()
        
        logger.info("Production monitoring started")
    
    async def stop(self):
        """Stop production monitoring"""
        self.is_running = False
        
        # Cancel monitoring tasks
        for task in self.monitor_tasks:
            task.cancel()
        
        await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        
        # Close Redis
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Production monitoring stopped")
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                getattr(settings, 'REDIS_URL', 'redis://localhost:6379'),
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connected for production monitoring")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def _monitor_performance(self):
        """Monitor performance metrics"""
        while self.is_running:
            try:
                # Get current metrics
                metrics = await self._collect_metrics()
                
                # Check thresholds
                await self._check_thresholds(metrics)
                
                # Store metrics
                await self._store_metrics(metrics)
                
                # Update health status
                self._update_health_status(metrics)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_health(self):
        """Monitor system health"""
        while self.is_running:
            try:
                health_checks = {
                    'api': await self._check_api_health(),
                    'database': await self._check_database_health(),
                    'ai_service': await self._check_ai_health(),
                    'cache': await self._check_cache_health(),
                    'disk_space': self._check_disk_space(),
                    'memory': self._check_memory_health()
                }
                
                self.health_checks = health_checks
                
                # Generate alerts for failed health checks
                for component, is_healthy in health_checks.items():
                    if not is_healthy:
                        await self._create_alert(
                            severity=AlertSeverity.ERROR,
                            component=component,
                            metric='health_check',
                            value=0,
                            threshold=1,
                            message=f"{component} health check failed"
                        )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_sla(self):
        """Monitor SLA compliance"""
        while self.is_running:
            try:
                # Calculate SLA metrics
                sla_metrics = await self._calculate_sla_metrics()
                
                # Check compliance
                is_compliant = self.sla.is_compliant(sla_metrics)
                
                if not is_compliant:
                    # Identify violations
                    violations = []
                    
                    if sla_metrics.get('availability', 0) < self.sla.availability_percent:
                        violations.append(f"Availability: {sla_metrics['availability']:.2f}% < {self.sla.availability_percent}%")
                    
                    if sla_metrics.get('response_time_p95', float('inf')) > self.sla.response_time_p95_ms:
                        violations.append(f"P95 Response: {sla_metrics['response_time_p95']:.0f}ms > {self.sla.response_time_p95_ms}ms")
                    
                    if sla_metrics.get('error_rate', 100) > self.sla.error_rate_percent:
                        violations.append(f"Error Rate: {sla_metrics['error_rate']:.2f}% > {self.sla.error_rate_percent}%")
                    
                    # Create SLA violation alert
                    await self._create_alert(
                        severity=AlertSeverity.CRITICAL,
                        component='sla',
                        metric='compliance',
                        value=0,
                        threshold=1,
                        message=f"SLA violations: {', '.join(violations)}"
                    )
                
                # Store SLA metrics
                if self.redis_client:
                    await self.redis_client.setex(
                        'sla_metrics',
                        300,  # 5 minute TTL
                        json.dumps({
                            **sla_metrics,
                            'is_compliant': is_compliant,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"SLA monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_anomalies(self):
        """Monitor for performance anomalies"""
        while self.is_running:
            try:
                # Get recent metrics
                metrics = await self._collect_metrics()
                
                # Check for anomalies
                anomalies = self._detect_anomalies(metrics)
                
                for anomaly in anomalies:
                    await self._create_alert(
                        severity=AlertSeverity.WARNING,
                        component=anomaly['component'],
                        metric=anomaly['metric'],
                        value=anomaly['value'],
                        threshold=anomaly['expected'],
                        message=f"Anomaly detected: {anomaly['message']}"
                    )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Anomaly monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _process_alerts(self):
        """Process and handle alerts"""
        while self.is_running:
            try:
                # Process active alerts
                for alert in self.active_alerts:
                    if not alert.resolved:
                        # Attempt self-healing
                        if self.healing_enabled:
                            await self._attempt_healing(alert)
                        
                        # Send notifications
                        await self._send_alert_notification(alert)
                        
                        # Check for escalation
                        if self._should_escalate(alert):
                            await self._escalate_alert(alert)
                
                # Clean up resolved alerts
                self.active_alerts = [a for a in self.active_alerts if not a.resolved or 
                                    (datetime.utcnow() - a.resolution_time).seconds < 300]
                
                await asyncio.sleep(10)  # Process every 10 seconds
                
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(10)
    
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect current performance metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Performance metrics from monitor
        perf_summary = performance_monitor.get_performance_summary()
        
        # AI metrics from optimizer
        ai_report = ai_optimizer.get_performance_report()
        
        metrics = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used / (1024**2),
            'response_time_p50': perf_summary.get('performance', {}).get('response_time_p50_ms', 0),
            'response_time_p95': perf_summary.get('performance', {}).get('response_time_p95_ms', 0),
            'response_time_p99': perf_summary.get('performance', {}).get('response_time_p99_ms', 0),
            'error_rate': perf_summary.get('performance', {}).get('error_rate_percent', 0),
            'active_requests': perf_summary.get('system', {}).get('active_requests', 0),
            'ai_inference_time': self._get_avg_ai_inference_time(ai_report),
            'cache_hit_rate': self._get_cache_hit_rate(ai_report),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # GPU metrics if available
        if torch.cuda.is_available():
            metrics['gpu_memory_mb'] = torch.cuda.memory_allocated() / (1024**2)
            metrics['gpu_utilization'] = 0  # Would need nvidia-ml-py for actual utilization
        
        return metrics
    
    async def _check_thresholds(self, metrics: Dict[str, float]):
        """Check metrics against thresholds"""
        thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'response_time_p95': self.sla.response_time_p95_ms,
            'response_time_p99': self.sla.response_time_p99_ms,
            'error_rate': self.sla.error_rate_percent,
            'gpu_memory_mb': 8192  # 8GB
        }
        
        for metric, threshold in thresholds.items():
            if metric in metrics and metrics[metric] > threshold:
                severity = self._determine_severity(metric, metrics[metric], threshold)
                
                await self._create_alert(
                    severity=severity,
                    component='system',
                    metric=metric,
                    value=metrics[metric],
                    threshold=threshold,
                    message=f"{metric} exceeded threshold: {metrics[metric]:.2f} > {threshold}"
                )
    
    async def _create_alert(self, severity: AlertSeverity, component: str, 
                           metric: str, value: float, threshold: float, message: str):
        """Create and register an alert"""
        # Check if similar alert already exists
        for alert in self.active_alerts:
            if (alert.component == component and 
                alert.metric == metric and 
                not alert.resolved):
                return  # Don't duplicate alerts
        
        alert = PerformanceAlert(
            timestamp=datetime.utcnow(),
            severity=severity,
            component=component,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message
        )
        
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        logger.warning(f"ALERT [{severity.value}] {component}/{metric}: {message}")
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    async def _attempt_healing(self, alert: PerformanceAlert):
        """Attempt self-healing for alert"""
        healing_key = None
        
        # Map alerts to healing actions
        if 'memory' in alert.metric:
            healing_key = 'high_memory'
        elif 'response_time' in alert.metric:
            healing_key = 'slow_response'
        elif 'error_rate' in alert.metric:
            healing_key = 'high_error_rate'
        elif 'cache' in alert.metric:
            healing_key = 'cache_degradation'
        
        if healing_key and healing_key in self.healing_actions:
            try:
                logger.info(f"Attempting self-healing for {alert.component}/{alert.metric}")
                action_taken = await self.healing_actions[healing_key](alert)
                alert.action_taken = action_taken
                
                # Check if healing was successful
                await asyncio.sleep(10)  # Wait for effect
                metrics = await self._collect_metrics()
                
                if metrics.get(alert.metric, float('inf')) < alert.threshold:
                    alert.resolved = True
                    alert.resolution_time = datetime.utcnow()
                    logger.info(f"Self-healing successful for {alert.component}/{alert.metric}")
                
            except Exception as e:
                logger.error(f"Self-healing failed: {e}")
    
    async def _heal_memory(self, alert: PerformanceAlert) -> str:
        """Heal high memory usage"""
        # Clear caches
        await ai_optimizer.memory_cleanup(force=True)
        
        # Trigger garbage collection
        import gc
        gc.collect()
        
        # Clear PyTorch cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return "Cleared caches and freed memory"
    
    async def _heal_slow_response(self, alert: PerformanceAlert) -> str:
        """Heal slow response times"""
        # Optimize batch sizes
        for model_type in ai_optimizer.batch_processor.optimal_batch_sizes:
            current = ai_optimizer.batch_processor.optimal_batch_sizes[model_type]
            ai_optimizer.batch_processor.optimal_batch_sizes[model_type] = min(32, current + 4)
        
        # Warm cache
        await performance_matcher.warmup()
        
        return "Optimized batch sizes and warmed cache"
    
    async def _heal_error_rate(self, alert: PerformanceAlert) -> str:
        """Heal high error rate"""
        # Scale up model pools
        for pool in ai_optimizer.model_pools.values():
            if len(pool.models) < pool.max_size:
                pool._scale_up()
        
        return "Scaled up model pools"
    
    async def _heal_cache(self, alert: PerformanceAlert) -> str:
        """Heal cache degradation"""
        # Optimize cache settings
        performance_matcher.cache.l1_max_size = min(2000, performance_matcher.cache.l1_max_size + 200)
        
        return "Increased cache capacity"
    
    async def _send_alert_notification(self, alert: PerformanceAlert):
        """Send alert notification"""
        if not self.webhook_url:
            return
        
        # Only send for error and critical alerts
        if alert.severity not in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'severity': alert.severity.value,
                    'component': alert.component,
                    'metric': alert.metric,
                    'value': alert.value,
                    'threshold': alert.threshold,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'action_taken': alert.action_taken
                }
                
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send alert notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Alert notification error: {e}")
    
    def _determine_severity(self, metric: str, value: float, threshold: float) -> AlertSeverity:
        """Determine alert severity based on how much threshold is exceeded"""
        ratio = value / threshold
        
        if ratio > 2.0:  # More than 2x threshold
            return AlertSeverity.CRITICAL
        elif ratio > 1.5:  # More than 1.5x threshold
            return AlertSeverity.ERROR
        elif ratio > 1.2:  # More than 1.2x threshold
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def _should_escalate(self, alert: PerformanceAlert) -> bool:
        """Check if alert should be escalated"""
        # Escalate if alert has been active for more than 5 minutes
        if (datetime.utcnow() - alert.timestamp).seconds > 300:
            return True
        
        # Escalate if critical severity
        if alert.severity == AlertSeverity.CRITICAL:
            return True
        
        return False
    
    async def _escalate_alert(self, alert: PerformanceAlert):
        """Escalate alert to higher level"""
        logger.critical(f"ESCALATED ALERT: {alert.message}")
        
        # Could implement pager duty, email, SMS, etc.
        # For now, just log critically
    
    async def _establish_baselines(self):
        """Establish performance baselines"""
        logger.info("Establishing performance baselines...")
        
        samples = []
        for _ in range(12):  # Collect 1 minute of samples
            metrics = await self._collect_metrics()
            samples.append(metrics)
            await asyncio.sleep(5)
        
        # Calculate baselines
        for metric in ['cpu_percent', 'memory_percent', 'response_time_p95', 'ai_inference_time']:
            values = [s.get(metric, 0) for s in samples if metric in s]
            if values:
                self.baselines[metric] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0
                }
        
        logger.info(f"Baselines established: {self.baselines}")
    
    def _detect_anomalies(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics"""
        anomalies = []
        
        for metric, value in metrics.items():
            if metric in self.baselines and self.baselines[metric]['std'] > 0:
                baseline = self.baselines[metric]
                z_score = abs((value - baseline['mean']) / baseline['std'])
                
                if z_score > self.anomaly_threshold:
                    anomalies.append({
                        'component': 'system',
                        'metric': metric,
                        'value': value,
                        'expected': baseline['mean'],
                        'z_score': z_score,
                        'message': f"{metric} deviates {z_score:.1f} std from baseline"
                    })
        
        return anomalies
    
    async def _check_api_health(self) -> bool:
        """Check API health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{getattr(settings, 'API_BASE_URL', 'http://localhost:8000')}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _check_database_health(self) -> bool:
        """Check database health"""
        try:
            # Would implement actual database check
            return True
        except Exception:
            return False
    
    async def _check_ai_health(self) -> bool:
        """Check AI service health"""
        try:
            # Quick AI inference test
            test_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            result = await ai_optimizer.optimize_hash_computation(test_image)
            return result is not None
        except Exception:
            return False
    
    async def _check_cache_health(self) -> bool:
        """Check cache health"""
        try:
            if performance_matcher.cache.redis_client:
                await performance_matcher.cache.redis_client.ping()
            return True
        except Exception:
            return False
    
    def _check_disk_space(self) -> bool:
        """Check disk space"""
        disk = psutil.disk_usage('/')
        return disk.percent < 90  # Less than 90% used
    
    def _check_memory_health(self) -> bool:
        """Check memory health"""
        memory = psutil.virtual_memory()
        return memory.percent < 90  # Less than 90% used
    
    def _update_health_status(self, metrics: Dict[str, float]):
        """Update overall health status"""
        # Count failed health checks
        failed_checks = sum(1 for check in self.health_checks.values() if not check)
        
        # Check critical metrics
        critical_issues = (
            metrics.get('cpu_percent', 0) > 95 or
            metrics.get('memory_percent', 0) > 95 or
            metrics.get('error_rate', 0) > 10 or
            metrics.get('response_time_p99', 0) > 10000
        )
        
        if critical_issues or failed_checks >= 3:
            self.health_status = HealthStatus.CRITICAL
        elif failed_checks >= 2 or metrics.get('error_rate', 0) > 5:
            self.health_status = HealthStatus.UNHEALTHY
        elif failed_checks >= 1 or metrics.get('response_time_p95', 0) > 3000:
            self.health_status = HealthStatus.DEGRADED
        else:
            self.health_status = HealthStatus.HEALTHY
    
    async def _calculate_sla_metrics(self) -> Dict[str, float]:
        """Calculate SLA compliance metrics"""
        # Get performance summary
        perf_summary = performance_monitor.get_performance_summary()
        
        # Calculate availability (based on uptime and errors)
        uptime_hours = perf_summary.get('uptime_hours', 0)
        error_rate = perf_summary.get('performance', {}).get('error_rate_percent', 0)
        availability = 100 - error_rate
        
        return {
            'availability': availability,
            'response_time_p95': perf_summary.get('performance', {}).get('response_time_p95_ms', 0),
            'response_time_p99': perf_summary.get('performance', {}).get('response_time_p99_ms', 0),
            'error_rate': error_rate,
            'concurrent_users': perf_summary.get('system', {}).get('active_requests', 0) * 10,  # Estimate
            'ai_inference_time': self._get_avg_ai_inference_time(ai_optimizer.get_performance_report()),
            'cache_hit_rate': self._get_cache_hit_rate(ai_optimizer.get_performance_report()) * 100
        }
    
    def _get_avg_ai_inference_time(self, ai_report: Dict[str, Any]) -> float:
        """Get average AI inference time from report"""
        operations = ai_report.get('operations', {})
        if not operations:
            return 0
        
        times = [op.get('avg_time_ms', 0) for op in operations.values()]
        return statistics.mean(times) if times else 0
    
    def _get_cache_hit_rate(self, ai_report: Dict[str, Any]) -> float:
        """Get cache hit rate from report"""
        operations = ai_report.get('operations', {})
        if not operations:
            return 0
        
        rates = [op.get('cache_hit_rate', 0) for op in operations.values()]
        return statistics.mean(rates) if rates else 0
    
    async def _store_metrics(self, metrics: Dict[str, float]):
        """Store metrics for historical analysis"""
        if not self.redis_client:
            return
        
        try:
            # Store current metrics
            await self.redis_client.setex(
                'current_prod_metrics',
                60,
                json.dumps(metrics)
            )
            
            # Add to time series
            await self.redis_client.lpush('prod_metrics_history', json.dumps(metrics))
            await self.redis_client.ltrim('prod_metrics_history', 0, 8640)  # Keep 24 hours at 10s intervals
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    async def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        metrics = await self._collect_metrics()
        sla_metrics = await self._calculate_sla_metrics()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'health_status': self.health_status.value,
            'health_checks': self.health_checks,
            'current_metrics': metrics,
            'sla_compliance': {
                'is_compliant': self.sla.is_compliant(sla_metrics),
                'metrics': sla_metrics,
                'targets': {
                    'availability': self.sla.availability_percent,
                    'response_time_p95': self.sla.response_time_p95_ms,
                    'error_rate': self.sla.error_rate_percent,
                    'concurrent_users': self.sla.concurrent_users
                }
            },
            'active_alerts': len(self.active_alerts),
            'alert_summary': {
                severity.value: sum(1 for a in self.active_alerts if a.severity == severity and not a.resolved)
                for severity in AlertSeverity
            },
            'baselines': self.baselines,
            'uptime_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600
        }


# Global production monitor instance
production_monitor = ProductionMonitor()


# Convenience functions
async def start_production_monitoring():
    """Start production monitoring"""
    await production_monitor.start()


async def stop_production_monitoring():
    """Stop production monitoring"""
    await production_monitor.stop()


async def get_production_status() -> Dict[str, Any]:
    """Get production status report"""
    return await production_monitor.get_status_report()