"""
Delisting Status Tracking and Monitoring System
Provides real-time monitoring, status updates, and comprehensive reporting
PRD: "Status tracking for removal requests", "Success/failure monitoring and reporting"
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, Counter
import statistics

from app.services.scanning.delisting_service import DelistingStatus, SearchEngine, DelistingResult
from app.services.scanning.delisting_manager import delisting_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class MonitoringEvent(str, Enum):
    """Types of monitoring events"""
    STATUS_CHANGE = "status_change"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"


@dataclass
class StatusChangeEvent:
    """Delisting status change event"""
    request_id: str
    url: str
    search_engine: SearchEngine
    old_status: DelistingStatus
    new_status: DelistingStatus
    timestamp: datetime
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for delisting operations"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    pending_requests: int = 0
    average_processing_time: float = 0.0
    success_rate: float = 0.0
    search_engine_performance: Dict[SearchEngine, Dict[str, Any]] = field(default_factory=dict)
    hourly_stats: Dict[str, int] = field(default_factory=dict)
    daily_stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class AlertThreshold:
    """Alert threshold configuration"""
    metric: str
    threshold: float
    comparison: str  # 'greater_than', 'less_than', 'equals'
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    cooldown_minutes: int = 60


class DelistingStatusMonitor:
    """
    Comprehensive status tracking and monitoring for delisting requests
    PRD: "Monitor removal request status via APIs", "Real-time notifications"
    """
    
    def __init__(self):
        self.events_history = []  # List of StatusChangeEvent
        self.performance_metrics = PerformanceMetrics()
        self.alert_thresholds = self._setup_default_thresholds()
        self.subscribers = []  # Webhook/callback subscribers
        
        # Real-time tracking
        self.active_monitors = {}  # Request ID -> monitoring task
        self.status_cache = {}  # Request ID -> current status
        self.verification_queue = []  # URLs to verify removal
        
        # Statistics aggregation
        self.stats_window = timedelta(hours=24)
        self.stats_cache = {}
        self.last_stats_update = None
        
        # Background tasks
        self._running = False
        self._monitor_task = None
        self._verification_task = None
        self._stats_task = None
        
    def _setup_default_thresholds(self) -> Dict[str, AlertThreshold]:
        """Setup default alert thresholds"""
        return {
            'success_rate_low': AlertThreshold(
                metric='success_rate',
                threshold=0.8,  # 80%
                comparison='less_than'
            ),
            'failure_rate_high': AlertThreshold(
                metric='failure_rate',
                threshold=0.3,  # 30%
                comparison='greater_than'
            ),
            'processing_time_high': AlertThreshold(
                metric='average_processing_time',
                threshold=300.0,  # 5 minutes
                comparison='greater_than'
            ),
            'queue_size_high': AlertThreshold(
                metric='queue_size',
                threshold=1000,
                comparison='greater_than'
            ),
            'api_errors_high': AlertThreshold(
                metric='api_error_rate',
                threshold=0.1,  # 10%
                comparison='greater_than'
            )
        }

    async def start(self):
        """Start the monitoring system"""
        if self._running:
            return
            
        self._running = True
        
        # Start background tasks
        self._monitor_task = asyncio.create_task(self._monitor_active_requests())
        self._verification_task = asyncio.create_task(self._verify_removals())
        self._stats_task = asyncio.create_task(self._update_statistics())
        
        logger.info("Delisting status monitor started")
        
    async def stop(self):
        """Stop the monitoring system"""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel background tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._verification_task:
            self._verification_task.cancel()
        if self._stats_task:
            self._stats_task.cancel()
            
        # Cancel active monitors
        for task in self.active_monitors.values():
            task.cancel()
        self.active_monitors.clear()
        
        logger.info("Delisting status monitor stopped")

    async def track_request(
        self,
        request_id: str,
        url: str,
        search_engines: List[SearchEngine],
        initial_results: Dict[SearchEngine, DelistingResult]
    ):
        """
        Start tracking a delisting request
        PRD: "Status tracking for removal requests"
        """
        # Record initial status
        for engine, result in initial_results.items():
            self.status_cache[f"{request_id}_{engine.value}"] = result.status
            
            # Log initial event
            event = StatusChangeEvent(
                request_id=request_id,
                url=url,
                search_engine=engine,
                old_status=DelistingStatus.PENDING,
                new_status=result.status,
                timestamp=datetime.utcnow(),
                message=result.message
            )
            self.events_history.append(event)
            
            # Start monitoring if request was submitted
            if result.status in [DelistingStatus.SUBMITTED, DelistingStatus.IN_PROGRESS]:
                if result.request_id:
                    monitor_key = f"{request_id}_{engine.value}"
                    self.active_monitors[monitor_key] = asyncio.create_task(
                        self._monitor_single_request(request_id, url, engine, result.request_id)
                    )
        
        # Update performance metrics
        await self._update_request_metrics(request_id, initial_results)
        
        # Check for alerts
        await self._check_alerts()

    async def update_request_status(
        self,
        request_id: str,
        url: str,
        search_engine: SearchEngine,
        new_status: DelistingStatus,
        message: str = "",
        metadata: Dict[str, Any] = None
    ):
        """Update the status of a tracked request"""
        cache_key = f"{request_id}_{search_engine.value}"
        old_status = self.status_cache.get(cache_key, DelistingStatus.PENDING)
        
        if old_status != new_status:
            # Record status change
            event = StatusChangeEvent(
                request_id=request_id,
                url=url,
                search_engine=search_engine,
                old_status=old_status,
                new_status=new_status,
                timestamp=datetime.utcnow(),
                message=message,
                metadata=metadata or {}
            )
            self.events_history.append(event)
            self.status_cache[cache_key] = new_status
            
            # Notify subscribers
            await self._notify_subscribers(event)
            
            # If request is completed or failed, stop monitoring
            if new_status in [DelistingStatus.REMOVED, DelistingStatus.REJECTED, DelistingStatus.FAILED]:
                monitor_key = cache_key
                if monitor_key in self.active_monitors:
                    self.active_monitors[monitor_key].cancel()
                    del self.active_monitors[monitor_key]
                    
                # Queue for verification if successful
                if new_status == DelistingStatus.REMOVED:
                    self.verification_queue.append((url, search_engine, datetime.utcnow()))
            
            logger.info(f"Status updated for {request_id}/{search_engine.value}: {old_status} -> {new_status}")

    async def get_request_status_history(self, request_id: str) -> List[StatusChangeEvent]:
        """Get the complete status history for a request"""
        return [
            event for event in self.events_history
            if event.request_id == request_id
        ]

    async def get_url_status_summary(self, url: str) -> Dict[str, Any]:
        """Get status summary for all requests related to a URL"""
        url_events = [
            event for event in self.events_history
            if event.url == url
        ]
        
        if not url_events:
            return {'url': url, 'status': 'not_found'}
            
        # Group by search engine
        engine_status = {}
        for engine in SearchEngine:
            engine_events = [e for e in url_events if e.search_engine == engine]
            if engine_events:
                latest_event = max(engine_events, key=lambda e: e.timestamp)
                engine_status[engine.value] = {
                    'status': latest_event.new_status,
                    'last_updated': latest_event.timestamp.isoformat(),
                    'message': latest_event.message
                }
                
        # Overall status
        statuses = [info['status'] for info in engine_status.values()]
        overall_status = self._determine_overall_status(statuses)
        
        return {
            'url': url,
            'overall_status': overall_status,
            'search_engines': engine_status,
            'last_activity': max(url_events, key=lambda e: e.timestamp).timestamp.isoformat()
        }

    async def get_performance_metrics(
        self,
        time_window: Optional[timedelta] = None
    ) -> PerformanceMetrics:
        """
        Get comprehensive performance metrics
        PRD: "Report success rates to users"
        """
        if time_window is None:
            time_window = self.stats_window
            
        cutoff_time = datetime.utcnow() - time_window
        
        # Filter events within time window
        recent_events = [
            event for event in self.events_history
            if event.timestamp >= cutoff_time
        ]
        
        if not recent_events:
            return PerformanceMetrics()
            
        # Calculate metrics
        metrics = PerformanceMetrics()
        
        # Count events by type
        status_counts = Counter(event.new_status for event in recent_events)
        metrics.total_requests = len(set(event.request_id for event in recent_events))
        metrics.successful_requests = status_counts.get(DelistingStatus.REMOVED, 0)
        metrics.failed_requests = sum([
            status_counts.get(DelistingStatus.FAILED, 0),
            status_counts.get(DelistingStatus.REJECTED, 0)
        ])
        metrics.pending_requests = sum([
            status_counts.get(DelistingStatus.PENDING, 0),
            status_counts.get(DelistingStatus.SUBMITTED, 0),
            status_counts.get(DelistingStatus.IN_PROGRESS, 0)
        ])
        
        # Calculate success rate
        if metrics.successful_requests + metrics.failed_requests > 0:
            metrics.success_rate = metrics.successful_requests / (
                metrics.successful_requests + metrics.failed_requests
            )
        
        # Search engine performance
        for engine in SearchEngine:
            engine_events = [e for e in recent_events if e.search_engine == engine]
            if engine_events:
                engine_success = len([e for e in engine_events if e.new_status == DelistingStatus.REMOVED])
                engine_failed = len([e for e in engine_events if e.new_status in [DelistingStatus.FAILED, DelistingStatus.REJECTED]])
                engine_total = engine_success + engine_failed
                
                metrics.search_engine_performance[engine] = {
                    'total_requests': len(set(e.request_id for e in engine_events)),
                    'successful': engine_success,
                    'failed': engine_failed,
                    'success_rate': engine_success / engine_total if engine_total > 0 else 0,
                    'average_time': 0  # Would calculate from request completion times
                }
        
        # Time-based statistics
        metrics.hourly_stats = self._calculate_hourly_stats(recent_events)
        metrics.daily_stats = self._calculate_daily_stats(recent_events)
        
        return metrics

    async def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """
        Get real-time dashboard data for monitoring
        PRD: "Real-time status updates"
        """
        now = datetime.utcnow()
        
        # Recent activity (last hour)
        hour_ago = now - timedelta(hours=1)
        recent_events = [
            event for event in self.events_history
            if event.timestamp >= hour_ago
        ]
        
        # Current queue status from manager
        queue_stats = await delisting_manager.get_queue_stats()
        
        # Active monitoring
        active_count = len(self.active_monitors)
        
        # Recent successes and failures
        recent_successes = len([e for e in recent_events if e.new_status == DelistingStatus.REMOVED])
        recent_failures = len([e for e in recent_events if e.new_status in [DelistingStatus.FAILED, DelistingStatus.REJECTED]])
        
        # Verification queue
        pending_verification = len(self.verification_queue)
        
        return {
            'timestamp': now.isoformat(),
            'queue_status': queue_stats,
            'active_monitoring': active_count,
            'recent_activity': {
                'successes_last_hour': recent_successes,
                'failures_last_hour': recent_failures,
                'total_events_last_hour': len(recent_events)
            },
            'verification': {
                'pending_verification': pending_verification
            },
            'alerts': await self._get_active_alerts()
        }

    async def add_status_subscriber(self, callback):
        """Add a callback for status change notifications"""
        self.subscribers.append(callback)

    async def remove_status_subscriber(self, callback):
        """Remove a status change callback"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def set_alert_threshold(self, name: str, threshold: AlertThreshold):
        """Set or update an alert threshold"""
        self.alert_thresholds[name] = threshold

    async def _monitor_single_request(
        self,
        request_id: str,
        url: str,
        search_engine: SearchEngine,
        api_request_id: str
    ):
        """Monitor a single request until completion"""
        try:
            # Import here to avoid circular imports
            from app.services.scanning.delisting_service import SearchEngineDelistingService
            
            async with SearchEngineDelistingService() as service:
                check_interval = 300  # 5 minutes
                max_checks = 144  # 12 hours max
                check_count = 0
                
                while check_count < max_checks:
                    try:
                        result = await service.check_removal_status(api_request_id, search_engine)
                        
                        if result.success:
                            await self.update_request_status(
                                request_id=request_id,
                                url=url,
                                search_engine=search_engine,
                                new_status=result.status,
                                message=result.message,
                                metadata=result.metadata
                            )
                            
                            # Stop monitoring if completed
                            if result.status in [DelistingStatus.REMOVED, DelistingStatus.REJECTED, DelistingStatus.FAILED]:
                                break
                        else:
                            logger.warning(f"Failed to check status for {request_id}/{search_engine.value}: {result.message}")
                            
                    except Exception as e:
                        logger.error(f"Error monitoring request {request_id}/{search_engine.value}: {e}")
                        
                    await asyncio.sleep(check_interval)
                    check_count += 1
                    
                # If we exit the loop without completion, mark as timeout
                if check_count >= max_checks:
                    await self.update_request_status(
                        request_id=request_id,
                        url=url,
                        search_engine=search_engine,
                        new_status=DelistingStatus.FAILED,
                        message="Monitoring timeout - no status update received"
                    )
                    
        except Exception as e:
            logger.error(f"Error in request monitor for {request_id}: {e}")

    async def _monitor_active_requests(self):
        """Background task to monitor all active requests"""
        while self._running:
            try:
                # Clean up completed monitors
                completed = []
                for key, task in self.active_monitors.items():
                    if task.done():
                        completed.append(key)
                        
                for key in completed:
                    del self.active_monitors[key]
                    
                # Update metrics periodically
                await self._update_aggregate_metrics()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in active request monitor: {e}")
                await asyncio.sleep(60)

    async def _verify_removals(self):
        """Background task to verify successful removals"""
        while self._running:
            try:
                if not self.verification_queue:
                    await asyncio.sleep(300)  # 5 minutes
                    continue
                    
                # Process verification queue
                batch_size = 10
                batch = self.verification_queue[:batch_size]
                self.verification_queue = self.verification_queue[batch_size:]
                
                from app.services.scanning.delisting_service import SearchEngineDelistingService
                
                async with SearchEngineDelistingService() as service:
                    for url, search_engine, timestamp in batch:
                        try:
                            # Only verify if it's been at least 1 hour since removal
                            if datetime.utcnow() - timestamp < timedelta(hours=1):
                                # Put back in queue for later
                                self.verification_queue.append((url, search_engine, timestamp))
                                continue
                                
                            verification_result = await service.verify_url_removal(url)
                            
                            if search_engine in verification_result:
                                is_removed = verification_result[search_engine]
                                logger.info(f"Verification for {url} on {search_engine.value}: {'CONFIRMED' if is_removed else 'STILL_PRESENT'}")
                                
                                # Log verification event
                                event = StatusChangeEvent(
                                    request_id=f"verify_{url}_{search_engine.value}",
                                    url=url,
                                    search_engine=search_engine,
                                    old_status=DelistingStatus.REMOVED,
                                    new_status=DelistingStatus.REMOVED if is_removed else DelistingStatus.FAILED,
                                    timestamp=datetime.utcnow(),
                                    message=f"Verification: {'Confirmed removed' if is_removed else 'Still present in search results'}"
                                )
                                self.events_history.append(event)
                                
                        except Exception as e:
                            logger.error(f"Error verifying removal for {url}: {e}")
                            
                await asyncio.sleep(60)  # Wait between batches
                
            except Exception as e:
                logger.error(f"Error in verification task: {e}")
                await asyncio.sleep(300)

    async def _update_statistics(self):
        """Background task to update aggregated statistics"""
        while self._running:
            try:
                # Update performance metrics cache
                self.performance_metrics = await self.get_performance_metrics()
                self.last_stats_update = datetime.utcnow()
                
                # Check alerts
                await self._check_alerts()
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)

    async def _update_request_metrics(self, request_id: str, results: Dict[SearchEngine, DelistingResult]):
        """Update metrics when a new request is tracked"""
        self.performance_metrics.total_requests += 1
        
        for engine, result in results.items():
            if result.success:
                if result.status == DelistingStatus.REMOVED:
                    self.performance_metrics.successful_requests += 1
                elif result.status in [DelistingStatus.FAILED, DelistingStatus.REJECTED]:
                    self.performance_metrics.failed_requests += 1
                else:
                    self.performance_metrics.pending_requests += 1

    async def _update_aggregate_metrics(self):
        """Update aggregated performance metrics"""
        # This would typically query the database for accurate metrics
        # For now, we calculate from in-memory events
        recent_window = datetime.utcnow() - self.stats_window
        recent_events = [e for e in self.events_history if e.timestamp >= recent_window]
        
        if recent_events:
            success_count = len([e for e in recent_events if e.new_status == DelistingStatus.REMOVED])
            failure_count = len([e for e in recent_events if e.new_status in [DelistingStatus.FAILED, DelistingStatus.REJECTED]])
            total_completed = success_count + failure_count
            
            if total_completed > 0:
                self.performance_metrics.success_rate = success_count / total_completed

    async def _check_alerts(self):
        """Check alert thresholds and trigger notifications"""
        current_metrics = self.performance_metrics
        now = datetime.utcnow()
        
        for name, threshold in self.alert_thresholds.items():
            if not threshold.enabled:
                continue
                
            # Check cooldown
            if threshold.last_triggered:
                if (now - threshold.last_triggered).total_seconds() < threshold.cooldown_minutes * 60:
                    continue
            
            # Get current value for metric
            current_value = self._get_metric_value(threshold.metric, current_metrics)
            if current_value is None:
                continue
                
            # Check threshold
            should_trigger = False
            if threshold.comparison == 'greater_than' and current_value > threshold.threshold:
                should_trigger = True
            elif threshold.comparison == 'less_than' and current_value < threshold.threshold:
                should_trigger = True
            elif threshold.comparison == 'equals' and current_value == threshold.threshold:
                should_trigger = True
                
            if should_trigger:
                await self._trigger_alert(name, threshold, current_value)
                threshold.last_triggered = now

    def _get_metric_value(self, metric: str, metrics: PerformanceMetrics) -> Optional[float]:
        """Get current value for a metric"""
        if metric == 'success_rate':
            return metrics.success_rate
        elif metric == 'failure_rate':
            total = metrics.successful_requests + metrics.failed_requests
            return metrics.failed_requests / total if total > 0 else 0
        elif metric == 'average_processing_time':
            return metrics.average_processing_time
        elif metric == 'queue_size':
            # Would get from delisting_manager
            return 0  # Placeholder
        elif metric == 'api_error_rate':
            # Would calculate from recent API errors
            return 0  # Placeholder
        return None

    async def _trigger_alert(self, name: str, threshold: AlertThreshold, current_value: float):
        """Trigger an alert notification"""
        alert_data = {
            'alert_name': name,
            'metric': threshold.metric,
            'threshold': threshold.threshold,
            'current_value': current_value,
            'comparison': threshold.comparison,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'warning' if 'high' in name else 'critical' if 'low' in name else 'info'
        }
        
        logger.warning(f"Alert triggered: {name} - {threshold.metric} is {current_value} (threshold: {threshold.threshold})")
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                await subscriber('alert', alert_data)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    async def _notify_subscribers(self, event: StatusChangeEvent):
        """Notify all subscribers of a status change"""
        event_data = {
            'type': 'status_change',
            'request_id': event.request_id,
            'url': event.url,
            'search_engine': event.search_engine.value,
            'old_status': event.old_status.value,
            'new_status': event.new_status.value,
            'timestamp': event.timestamp.isoformat(),
            'message': event.message,
            'metadata': event.metadata
        }
        
        for subscriber in self.subscribers:
            try:
                await subscriber('status_change', event_data)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    def _determine_overall_status(self, statuses: List[str]) -> str:
        """Determine overall status from individual search engine statuses"""
        if not statuses:
            return 'unknown'
            
        # Priority order for status determination
        if DelistingStatus.REMOVED in statuses:
            return 'partially_removed' if len(set(statuses)) > 1 else 'removed'
        elif DelistingStatus.IN_PROGRESS in statuses or DelistingStatus.SUBMITTED in statuses:
            return 'in_progress'
        elif DelistingStatus.FAILED in statuses or DelistingStatus.REJECTED in statuses:
            return 'failed'
        else:
            return 'pending'

    def _calculate_hourly_stats(self, events: List[StatusChangeEvent]) -> Dict[str, int]:
        """Calculate hourly statistics from events"""
        hourly_counts = defaultdict(int)
        for event in events:
            hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_counts[hour_key] += 1
        return dict(hourly_counts)

    def _calculate_daily_stats(self, events: List[StatusChangeEvent]) -> Dict[str, int]:
        """Calculate daily statistics from events"""
        daily_counts = defaultdict(int)
        for event in events:
            day_key = event.timestamp.strftime('%Y-%m-%d')
            daily_counts[day_key] += 1
        return dict(daily_counts)

    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        active_alerts = []
        now = datetime.utcnow()
        
        for name, threshold in self.alert_thresholds.items():
            if threshold.last_triggered:
                time_since = (now - threshold.last_triggered).total_seconds()
                if time_since < threshold.cooldown_minutes * 60:
                    active_alerts.append({
                        'name': name,
                        'metric': threshold.metric,
                        'triggered_at': threshold.last_triggered.isoformat(),
                        'time_remaining': threshold.cooldown_minutes * 60 - time_since
                    })
                    
        return active_alerts


# Global instance
delisting_monitor = DelistingStatusMonitor()