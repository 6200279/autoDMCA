"""
Performance Monitoring and Profiling System
Real-time monitoring of AI inference, API responses, and system resources
"""
import asyncio
import time
import psutil
import threading
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging
import json

import torch
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class PerformanceSnapshot:
    """System performance snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    gpu_memory_used_mb: float = 0.0
    gpu_utilization_percent: float = 0.0
    active_requests: int = 0
    queue_size: int = 0
    response_time_p50: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    error_rate: float = 0.0


@dataclass
class AIModelMetrics:
    """AI model performance metrics"""
    model_name: str
    inference_count: int = 0
    total_inference_time_ms: float = 0.0
    avg_inference_time_ms: float = 0.0
    batch_size_avg: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    gpu_memory_usage_mb: float = 0.0
    error_count: int = 0


class CircularBuffer:
    """Thread-safe circular buffer for metric storage"""
    
    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.buffer = deque(maxlen=maxsize)
        self.lock = threading.Lock()
    
    def append(self, item: Any):
        with self.lock:
            self.buffer.append(item)
    
    def get_all(self) -> List[Any]:
        with self.lock:
            return list(self.buffer)
    
    def get_recent(self, count: int) -> List[Any]:
        with self.lock:
            return list(self.buffer)[-count:] if count < len(self.buffer) else list(self.buffer)


class ResponseTimeTracker:
    """Track response times with percentile calculations"""
    
    def __init__(self, window_size: int = 1000):
        self.times = CircularBuffer(window_size)
    
    def add_time(self, response_time_ms: float):
        self.times.append(response_time_ms)
    
    def get_percentiles(self) -> Dict[str, float]:
        times = self.times.get_all()
        if not times:
            return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
        
        times.sort()
        n = len(times)
        
        return {
            'p50': times[int(n * 0.5)] if n > 0 else 0.0,
            'p95': times[int(n * 0.95)] if n > 0 else 0.0,
            'p99': times[int(n * 0.99)] if n > 0 else 0.0
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    
    Features:
    - Real-time system metrics (CPU, memory, GPU)
    - AI model performance tracking
    - API response time monitoring
    - Resource usage alerts
    - Performance SLA validation
    - Automatic profiling and bottleneck detection
    """
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.is_running = False
        self.monitor_interval = getattr(settings, 'MONITOR_INTERVAL', 5)  # seconds
        
        # Metric storage
        self.metrics: Dict[str, CircularBuffer] = defaultdict(lambda: CircularBuffer(1000))
        self.snapshots = CircularBuffer(288)  # 24 hours at 5-minute intervals
        
        # Response time tracking
        self.response_trackers: Dict[str, ResponseTimeTracker] = defaultdict(ResponseTimeTracker)
        
        # AI model metrics
        self.ai_metrics: Dict[str, AIModelMetrics] = defaultdict(AIModelMetrics)
        
        # Active request tracking
        self.active_requests = 0
        self.request_queue_size = 0
        
        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.last_error_reset = datetime.utcnow()
        
        # Alert thresholds
        self.thresholds = {
            'cpu_percent': getattr(settings, 'ALERT_CPU_THRESHOLD', 80.0),
            'memory_percent': getattr(settings, 'ALERT_MEMORY_THRESHOLD', 85.0),
            'response_time_p95_ms': getattr(settings, 'ALERT_RESPONSE_TIME_THRESHOLD', 2000.0),
            'error_rate_percent': getattr(settings, 'ALERT_ERROR_RATE_THRESHOLD', 5.0),
            'gpu_memory_percent': getattr(settings, 'ALERT_GPU_MEMORY_THRESHOLD', 90.0)
        }
        
        # Redis for distributed monitoring
        self.redis_client: Optional[redis.Redis] = None
        
        # Background monitoring task
        self.monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Performance monitor initialized")
    
    async def initialize(self):
        """Initialize monitoring system"""
        try:
            # Initialize Redis for distributed monitoring
            if hasattr(settings, 'REDIS_URL'):
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Performance monitor Redis connection established")
        
        except Exception as e:
            logger.warning(f"Redis connection failed for monitoring: {e}")
            self.redis_client = None
        
        # Start background monitoring
        await self.start_monitoring()
    
    async def start_monitoring(self):
        """Start background monitoring task"""
        if not self.is_running:
            self.is_running = True
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect system metrics
                snapshot = await self._collect_system_metrics()
                self.snapshots.append(snapshot)
                
                # Check thresholds and generate alerts
                await self._check_alerts(snapshot)
                
                # Store metrics in Redis for distributed monitoring
                if self.redis_client:
                    await self._store_metrics_redis(snapshot)
                
                # Sleep until next collection
                await asyncio.sleep(self.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.monitor_interval)
    
    async def _collect_system_metrics(self) -> PerformanceSnapshot:
        """Collect comprehensive system metrics"""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # GPU metrics (if available)
        gpu_memory_used = 0.0
        gpu_utilization = 0.0
        
        if torch.cuda.is_available():
            try:
                gpu_memory_used = torch.cuda.memory_allocated() / 1024**2  # MB
                # GPU utilization would require nvidia-ml-py
                # gpu_utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            except Exception:
                pass
        
        # Response time percentiles
        api_tracker = self.response_trackers.get('api', ResponseTimeTracker())
        percentiles = api_tracker.get_percentiles()
        
        # Error rate calculation
        total_errors = sum(self.error_counts.values())
        total_requests = sum(tracker.times.buffer for tracker in self.response_trackers.values()) or 1
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0.0
        
        return PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024**2,
            gpu_memory_used_mb=gpu_memory_used,
            gpu_utilization_percent=gpu_utilization,
            active_requests=self.active_requests,
            queue_size=self.request_queue_size,
            response_time_p50=percentiles['p50'],
            response_time_p95=percentiles['p95'],
            response_time_p99=percentiles['p99'],
            error_rate=error_rate
        )
    
    async def _check_alerts(self, snapshot: PerformanceSnapshot):
        """Check thresholds and generate alerts"""
        alerts = []
        
        # CPU alert
        if snapshot.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
        
        # Memory alert
        if snapshot.memory_percent > self.thresholds['memory_percent']:
            alerts.append(f"High memory usage: {snapshot.memory_percent:.1f}%")
        
        # Response time alert
        if snapshot.response_time_p95 > self.thresholds['response_time_p95_ms']:
            alerts.append(f"High response time P95: {snapshot.response_time_p95:.1f}ms")
        
        # Error rate alert
        if snapshot.error_rate > self.thresholds['error_rate_percent']:
            alerts.append(f"High error rate: {snapshot.error_rate:.1f}%")
        
        # GPU memory alert
        if torch.cuda.is_available() and snapshot.gpu_memory_used_mb > 0:
            gpu_total = torch.cuda.get_device_properties(0).total_memory / 1024**2
            gpu_percent = (snapshot.gpu_memory_used_mb / gpu_total) * 100
            if gpu_percent > self.thresholds['gpu_memory_percent']:
                alerts.append(f"High GPU memory usage: {gpu_percent:.1f}%")
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"PERFORMANCE ALERT: {alert}")
            await self._send_alert(alert, snapshot)
    
    async def _send_alert(self, message: str, snapshot: PerformanceSnapshot):
        """Send performance alert"""
        # Store alert in Redis for external monitoring systems
        if self.redis_client:
            try:
                alert_data = {
                    'message': message,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'severity': 'warning',
                    'metrics': {
                        'cpu_percent': snapshot.cpu_percent,
                        'memory_percent': snapshot.memory_percent,
                        'response_time_p95': snapshot.response_time_p95
                    }
                }
                await self.redis_client.lpush('performance_alerts', json.dumps(alert_data))
                await self.redis_client.ltrim('performance_alerts', 0, 99)  # Keep last 100 alerts
            except Exception as e:
                logger.error(f"Failed to store alert in Redis: {e}")
    
    async def _store_metrics_redis(self, snapshot: PerformanceSnapshot):
        """Store metrics in Redis for distributed monitoring"""
        if not self.redis_client:
            return
        
        try:
            metrics_data = {
                'timestamp': snapshot.timestamp.isoformat(),
                'cpu_percent': snapshot.cpu_percent,
                'memory_percent': snapshot.memory_percent,
                'gpu_memory_mb': snapshot.gpu_memory_used_mb,
                'active_requests': snapshot.active_requests,
                'response_time_p95': snapshot.response_time_p95,
                'error_rate': snapshot.error_rate
            }
            
            # Store current metrics
            await self.redis_client.setex(
                'current_metrics',
                60,  # 1 minute TTL
                json.dumps(metrics_data)
            )
            
            # Store in time series
            await self.redis_client.lpush('metrics_history', json.dumps(metrics_data))
            await self.redis_client.ltrim('metrics_history', 0, 1439)  # Keep 24 hours at 1-min intervals
            
        except Exception as e:
            logger.error(f"Failed to store metrics in Redis: {e}")
    
    @asynccontextmanager
    async def track_request(self, endpoint: str = "api"):
        """Context manager to track request performance"""
        start_time = time.time()
        self.active_requests += 1
        
        try:
            yield
        except Exception as e:
            self.error_counts[endpoint] += 1
            logger.error(f"Request error in {endpoint}: {e}")
            raise
        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            self.response_trackers[endpoint].add_time(response_time_ms)
            self.active_requests -= 1
    
    def track_ai_inference(
        self,
        model_name: str,
        inference_time_ms: float,
        batch_size: int = 1,
        cache_hit: bool = False,
        memory_usage_mb: float = 0.0,
        error: bool = False
    ):
        """Track AI model inference metrics"""
        metrics = self.ai_metrics[model_name]
        
        # Update counters
        if not error:
            metrics.inference_count += 1
            metrics.total_inference_time_ms += inference_time_ms
            metrics.avg_inference_time_ms = metrics.total_inference_time_ms / metrics.inference_count
            
            # Update batch size average
            total_batches = metrics.inference_count
            metrics.batch_size_avg = ((metrics.batch_size_avg * (total_batches - 1)) + batch_size) / total_batches
            
            # Update cache hit rate
            cache_hits = metrics.cache_hit_rate * (total_batches - 1) + (1 if cache_hit else 0)
            metrics.cache_hit_rate = cache_hits / total_batches
        else:
            metrics.error_count += 1
        
        # Update memory usage
        if memory_usage_mb > 0:
            metrics.memory_usage_mb = memory_usage_mb
        
        # GPU memory
        if torch.cuda.is_available():
            try:
                metrics.gpu_memory_usage_mb = torch.cuda.memory_allocated() / 1024**2
            except Exception:
                pass
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        recent_snapshots = self.snapshots.get_recent(12)  # Last hour
        
        if not recent_snapshots:
            return {'status': 'no_data'}
        
        # Calculate averages
        avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_memory = sum(s.memory_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_response_time = sum(s.response_time_p95 for s in recent_snapshots) / len(recent_snapshots)
        
        # Current values
        latest = recent_snapshots[-1]
        
        # AI model summary
        ai_summary = {}
        for model_name, metrics in self.ai_metrics.items():
            ai_summary[model_name] = {
                'inference_count': metrics.inference_count,
                'avg_inference_time_ms': metrics.avg_inference_time_ms,
                'avg_batch_size': metrics.batch_size_avg,
                'cache_hit_rate': metrics.cache_hit_rate,
                'error_count': metrics.error_count,
                'memory_usage_mb': metrics.memory_usage_mb
            }
        
        # SLA status
        sla_status = self._check_sla_compliance(recent_snapshots)
        
        return {
            'status': 'healthy',
            'timestamp': latest.timestamp.isoformat(),
            'uptime_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600,
            'system': {
                'cpu_percent': latest.cpu_percent,
                'cpu_avg_1h': avg_cpu,
                'memory_percent': latest.memory_percent,
                'memory_avg_1h': avg_memory,
                'gpu_memory_mb': latest.gpu_memory_used_mb,
                'active_requests': latest.active_requests
            },
            'performance': {
                'response_time_p50_ms': latest.response_time_p50,
                'response_time_p95_ms': latest.response_time_p95,
                'response_time_p99_ms': latest.response_time_p99,
                'response_time_avg_1h': avg_response_time,
                'error_rate_percent': latest.error_rate
            },
            'ai_models': ai_summary,
            'sla_compliance': sla_status,
            'thresholds': self.thresholds
        }
    
    def _check_sla_compliance(self, snapshots: List[PerformanceSnapshot]) -> Dict[str, Any]:
        """Check SLA compliance based on recent performance"""
        if not snapshots:
            return {'status': 'unknown'}
        
        # Define SLA targets
        sla_targets = {
            'response_time_p95_ms': 2000,  # 2 seconds
            'uptime_percent': 99.9,
            'error_rate_percent': 1.0
        }
        
        # Calculate compliance
        violations = []
        
        # Response time SLA
        p95_violations = sum(1 for s in snapshots if s.response_time_p95 > sla_targets['response_time_p95_ms'])
        p95_compliance = (len(snapshots) - p95_violations) / len(snapshots) * 100
        
        if p95_compliance < 95:  # 95% of requests should meet SLA
            violations.append(f"Response time SLA: {p95_compliance:.1f}% compliance")
        
        # Error rate SLA
        high_error_snapshots = sum(1 for s in snapshots if s.error_rate > sla_targets['error_rate_percent'])
        error_compliance = (len(snapshots) - high_error_snapshots) / len(snapshots) * 100
        
        if error_compliance < 95:
            violations.append(f"Error rate SLA: {error_compliance:.1f}% compliance")
        
        return {
            'status': 'compliant' if not violations else 'violations',
            'violations': violations,
            'response_time_compliance_percent': p95_compliance,
            'error_rate_compliance_percent': error_compliance,
            'targets': sla_targets
        }
    
    async def get_detailed_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get detailed metrics for analysis"""
        # Calculate how many snapshots to retrieve
        snapshots_needed = min(int(hours * 60 / self.monitor_interval), len(self.snapshots.buffer))
        recent_snapshots = self.snapshots.get_recent(snapshots_needed)
        
        if not recent_snapshots:
            return {'error': 'No data available'}
        
        # Time series data
        timestamps = [s.timestamp.isoformat() for s in recent_snapshots]
        cpu_data = [s.cpu_percent for s in recent_snapshots]
        memory_data = [s.memory_percent for s in recent_snapshots]
        response_time_data = [s.response_time_p95 for s in recent_snapshots]
        error_rate_data = [s.error_rate for s in recent_snapshots]
        
        return {
            'time_range_hours': hours,
            'data_points': len(recent_snapshots),
            'timestamps': timestamps,
            'metrics': {
                'cpu_percent': cpu_data,
                'memory_percent': memory_data,
                'response_time_p95_ms': response_time_data,
                'error_rate_percent': error_rate_data
            },
            'ai_models': dict(self.ai_metrics),
            'summary': self.get_performance_summary()
        }
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        summary = self.get_performance_summary()
        detailed = await self.get_detailed_metrics(24)
        
        # Performance insights
        insights = []
        
        # Check for performance degradation
        if len(self.snapshots.buffer) >= 12:  # At least 1 hour of data
            recent_avg = sum(s.response_time_p95 for s in self.snapshots.get_recent(12)) / 12
            older_avg = sum(s.response_time_p95 for s in self.snapshots.get_recent(24)[:12]) / 12
            
            if recent_avg > older_avg * 1.2:  # 20% degradation
                insights.append("Response time has degraded by >20% in the last hour")
        
        # Check AI model performance
        for model_name, metrics in self.ai_metrics.items():
            if metrics.avg_inference_time_ms > 2000:  # 2 seconds
                insights.append(f"AI model '{model_name}' has high inference time: {metrics.avg_inference_time_ms:.1f}ms")
            
            if metrics.cache_hit_rate < 0.5:  # Less than 50%
                insights.append(f"AI model '{model_name}' has low cache hit rate: {metrics.cache_hit_rate:.1%}")
        
        return {
            'generated_at': datetime.utcnow().isoformat(),
            'summary': summary,
            'detailed_metrics': detailed,
            'insights': insights,
            'recommendations': self._generate_recommendations(summary, insights)
        }
    
    def _generate_recommendations(self, summary: Dict[str, Any], insights: List[str]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # System resource recommendations
        if summary.get('system', {}).get('cpu_avg_1h', 0) > 70:
            recommendations.append("Consider scaling CPU resources or optimizing CPU-intensive operations")
        
        if summary.get('system', {}).get('memory_avg_1h', 0) > 80:
            recommendations.append("Memory usage is high - consider memory optimization or scaling")
        
        # Response time recommendations
        if summary.get('performance', {}).get('response_time_p95_ms', 0) > 1500:
            recommendations.append("Response times are high - consider caching, database optimization, or load balancing")
        
        # AI model recommendations
        for model_name, ai_metrics in summary.get('ai_models', {}).items():
            if ai_metrics.get('avg_inference_time_ms', 0) > 1500:
                recommendations.append(f"Optimize {model_name} inference time through batching or model optimization")
            
            if ai_metrics.get('cache_hit_rate', 1.0) < 0.6:
                recommendations.append(f"Improve {model_name} cache hit rate by tuning cache TTL or warming")
        
        return recommendations


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for automatic performance tracking
def track_performance(endpoint: str = "api"):
    """Decorator to automatically track function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with performance_monitor.track_request(endpoint):
                return await func(*args, **kwargs)
        return wrapper
    return decorator