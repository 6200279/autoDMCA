"""
Comprehensive Scanning Monitoring and Real-time Updates
Provides detailed monitoring, logging, and real-time progress updates for the scanning system
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import logging
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis

from app.core.config import settings
from app.api.websocket import notify_scan_progress, notify_infringement_found, notify_scan_completed

logger = logging.getLogger(__name__)


class MonitoringEvent(str, Enum):
    SCAN_STARTED = "scan_started"
    SCAN_PROGRESS = "scan_progress" 
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    PLATFORM_SCANNED = "platform_scanned"
    INFRINGEMENT_FOUND = "infringement_found"
    DMCA_INITIATED = "dmca_initiated"
    ERROR_OCCURRED = "error_occurred"
    HEALTH_CHECK = "health_check"


@dataclass
class ScanMetrics:
    """Scanning performance metrics"""
    scan_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Platform metrics
    platforms_attempted: int = 0
    platforms_successful: int = 0
    platforms_failed: int = 0
    
    # Content metrics
    urls_discovered: int = 0
    images_analyzed: int = 0
    videos_analyzed: int = 0
    total_matches_found: int = 0
    high_confidence_matches: int = 0
    
    # Performance metrics
    requests_made: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    average_response_time: float = 0.0
    
    # DMCA metrics
    dmca_notices_generated: int = 0
    automated_takedowns: int = 0
    
    # Error tracking
    error_count: int = 0
    errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ScanningMonitor:
    """
    Comprehensive monitoring system for scanning operations
    Provides real-time updates, performance tracking, and detailed logging
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.active_scans: Dict[str, ScanMetrics] = {}
        self.performance_history: List[ScanMetrics] = []
        self.max_history_size = 1000
        
        # Real-time tracking
        self.scan_events: Dict[str, List[Dict[str, Any]]] = {}
        self.platform_health: Dict[str, Dict[str, Any]] = {}
        
        # Performance thresholds
        self.performance_thresholds = {
            'max_scan_duration': timedelta(hours=2),
            'min_success_rate': 0.8,
            'max_error_rate': 0.1,
            'max_response_time': 30.0
        }
    
    async def initialize(self):
        """Initialize monitoring system"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Scanning monitor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize scanning monitor: {e}")
    
    async def start_scan_monitoring(
        self,
        scan_id: str,
        user_id: int,
        profile_id: int,
        scan_type: str,
        platforms: List[str]
    ) -> ScanMetrics:
        """Start monitoring a new scan"""
        metrics = ScanMetrics(
            scan_id=scan_id,
            start_time=datetime.utcnow(),
            platforms_attempted=len(platforms)
        )
        
        self.active_scans[scan_id] = metrics
        self.scan_events[scan_id] = []
        
        # Log scan start
        await self._log_event(scan_id, MonitoringEvent.SCAN_STARTED, {
            "user_id": user_id,
            "profile_id": profile_id,
            "scan_type": scan_type,
            "platforms": platforms,
            "started_at": metrics.start_time.isoformat()
        })
        
        # Send real-time notification
        await notify_scan_progress(user_id, {
            "scan_id": scan_id,
            "status": "started",
            "progress": 0,
            "message": f"Starting {scan_type} scan across {len(platforms)} platforms",
            "platforms": platforms
        })
        
        logger.info(f"Started monitoring scan {scan_id}")
        return metrics
    
    async def update_scan_progress(
        self,
        scan_id: str,
        progress_data: Dict[str, Any]
    ):
        """Update scan progress with real-time notifications"""
        if scan_id not in self.active_scans:
            logger.warning(f"Scan {scan_id} not found in active scans")
            return
        
        metrics = self.active_scans[scan_id]
        
        # Update metrics based on progress data
        if 'platforms_completed' in progress_data:
            metrics.platforms_successful = progress_data['platforms_completed']
        
        if 'urls_discovered' in progress_data:
            metrics.urls_discovered = progress_data['urls_discovered']
        
        if 'matches_found' in progress_data:
            metrics.total_matches_found = progress_data['matches_found']
        
        if 'requests_made' in progress_data:
            metrics.requests_made = progress_data['requests_made']
        
        # Calculate progress percentage
        progress_percent = 0
        if metrics.platforms_attempted > 0:
            progress_percent = int((metrics.platforms_successful / metrics.platforms_attempted) * 100)
        
        # Log progress event
        await self._log_event(scan_id, MonitoringEvent.SCAN_PROGRESS, {
            "progress_percent": progress_percent,
            "platforms_completed": metrics.platforms_successful,
            "urls_discovered": metrics.urls_discovered,
            "matches_found": metrics.total_matches_found,
            **progress_data
        })
        
        # Send real-time update
        user_id = progress_data.get('user_id')
        if user_id:
            await notify_scan_progress(user_id, {
                "scan_id": scan_id,
                "status": "running",
                "progress": progress_percent,
                "message": f"Scanning in progress - {metrics.platforms_successful}/{metrics.platforms_attempted} platforms completed",
                "urls_discovered": metrics.urls_discovered,
                "matches_found": metrics.total_matches_found
            })
    
    async def report_platform_completion(
        self,
        scan_id: str,
        platform: str,
        success: bool,
        results: Dict[str, Any]
    ):
        """Report completion of platform scanning"""
        if scan_id not in self.active_scans:
            return
        
        metrics = self.active_scans[scan_id]
        
        if success:
            metrics.platforms_successful += 1
            metrics.urls_discovered += results.get('urls_found', 0)
            metrics.requests_successful += results.get('requests_made', 0)
        else:
            metrics.platforms_failed += 1
            metrics.error_count += 1
            metrics.errors.append({
                "platform": platform,
                "error": results.get('error', 'Unknown error'),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Update platform health tracking
        self._update_platform_health(platform, success, results)
        
        # Log platform completion
        await self._log_event(scan_id, MonitoringEvent.PLATFORM_SCANNED, {
            "platform": platform,
            "success": success,
            "urls_found": results.get('urls_found', 0),
            "matches_found": results.get('matches_found', 0),
            "duration_seconds": results.get('duration', 0),
            "error": results.get('error') if not success else None
        })
    
    async def report_infringement_found(
        self,
        scan_id: str,
        user_id: int,
        infringement_data: Dict[str, Any]
    ):
        """Report discovery of potential infringement"""
        if scan_id not in self.active_scans:
            return
        
        metrics = self.active_scans[scan_id]
        metrics.total_matches_found += 1
        
        confidence = infringement_data.get('confidence', 0)
        if confidence > 0.8:
            metrics.high_confidence_matches += 1
        
        # Log infringement discovery
        await self._log_event(scan_id, MonitoringEvent.INFRINGEMENT_FOUND, {
            "url": infringement_data.get('url'),
            "platform": infringement_data.get('platform'),
            "confidence": confidence,
            "match_type": infringement_data.get('match_type'),
            "automated_dmca": confidence > 0.85
        })
        
        # Send real-time notification
        await notify_infringement_found(user_id, {
            "scan_id": scan_id,
            "url": infringement_data.get('url'),
            "platform": infringement_data.get('platform'),
            "confidence": confidence,
            "match_type": infringement_data.get('match_type'),
            "discovered_at": datetime.utcnow().isoformat()
        })
        
        # If high confidence, report DMCA initiation
        if confidence > 0.85:
            metrics.dmca_notices_generated += 1
            metrics.automated_takedowns += 1
            
            await self._log_event(scan_id, MonitoringEvent.DMCA_INITIATED, {
                "url": infringement_data.get('url'),
                "platform": infringement_data.get('platform'),
                "confidence": confidence,
                "automated": True
            })
    
    async def complete_scan_monitoring(
        self,
        scan_id: str,
        user_id: int,
        success: bool,
        results: Optional[Dict[str, Any]] = None
    ):
        """Complete scan monitoring and generate final metrics"""
        if scan_id not in self.active_scans:
            logger.warning(f"Scan {scan_id} not found in active scans")
            return
        
        metrics = self.active_scans[scan_id]
        metrics.end_time = datetime.utcnow()
        metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
        
        if results:
            metrics.total_matches_found = results.get('total_matches_found', metrics.total_matches_found)
            metrics.urls_discovered = results.get('total_urls_scanned', metrics.urls_discovered)
            metrics.dmca_notices_generated = results.get('dmca_notices_generated', metrics.dmca_notices_generated)
        
        # Calculate performance metrics
        if metrics.requests_made > 0:
            metrics.average_response_time = results.get('total_response_time', 0) / metrics.requests_made
        
        # Log completion
        event_type = MonitoringEvent.SCAN_COMPLETED if success else MonitoringEvent.SCAN_FAILED
        await self._log_event(scan_id, event_type, {
            "success": success,
            "duration_seconds": metrics.duration_seconds,
            "platforms_successful": metrics.platforms_successful,
            "platforms_failed": metrics.platforms_failed,
            "total_matches": metrics.total_matches_found,
            "high_confidence_matches": metrics.high_confidence_matches,
            "dmca_notices": metrics.dmca_notices_generated,
            "error_count": metrics.error_count
        })
        
        # Send completion notification
        await notify_scan_completed(user_id, {
            "scan_id": scan_id,
            "success": success,
            "duration_minutes": round(metrics.duration_seconds / 60, 1),
            "platforms_scanned": metrics.platforms_successful,
            "matches_found": metrics.total_matches_found,
            "high_confidence_matches": metrics.high_confidence_matches,
            "dmca_notices_generated": metrics.dmca_notices_generated,
            "completed_at": metrics.end_time.isoformat()
        })
        
        # Archive metrics and cleanup
        await self._archive_scan_metrics(metrics)
        
        # Move to history
        self.performance_history.append(metrics)
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)
        
        # Remove from active scans
        del self.active_scans[scan_id]
        if scan_id in self.scan_events:
            del self.scan_events[scan_id]
        
        logger.info(f"Completed monitoring scan {scan_id} - {metrics.total_matches_found} matches found")
    
    async def report_error(
        self,
        scan_id: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Report an error during scanning"""
        if scan_id in self.active_scans:
            metrics = self.active_scans[scan_id]
            metrics.error_count += 1
            metrics.errors.append({
                "type": error_type,
                "message": error_message,
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            })
        
        await self._log_event(scan_id, MonitoringEvent.ERROR_OCCURRED, {
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        })
    
    def _update_platform_health(
        self,
        platform: str,
        success: bool,
        results: Dict[str, Any]
    ):
        """Update platform health tracking"""
        if platform not in self.platform_health:
            self.platform_health[platform] = {
                "success_count": 0,
                "failure_count": 0,
                "total_requests": 0,
                "average_response_time": 0.0,
                "last_success": None,
                "last_failure": None
            }
        
        health = self.platform_health[platform]
        
        if success:
            health["success_count"] += 1
            health["last_success"] = datetime.utcnow().isoformat()
        else:
            health["failure_count"] += 1
            health["last_failure"] = datetime.utcnow().isoformat()
        
        health["total_requests"] += results.get('requests_made', 0)
        
        # Update average response time
        if results.get('response_time'):
            current_avg = health["average_response_time"]
            total_responses = health["success_count"] + health["failure_count"]
            health["average_response_time"] = (current_avg * (total_responses - 1) + results['response_time']) / total_responses
    
    async def _log_event(
        self,
        scan_id: str,
        event_type: MonitoringEvent,
        data: Dict[str, Any]
    ):
        """Log monitoring event"""
        event = {
            "scan_id": scan_id,
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Store in Redis for real-time access
        if self.redis_client:
            try:
                await self.redis_client.lpush(
                    f"scan_events:{scan_id}",
                    json.dumps(event)
                )
                # Keep only last 100 events per scan
                await self.redis_client.ltrim(f"scan_events:{scan_id}", 0, 99)
                
                # Store in general events stream
                await self.redis_client.lpush("scanning_events", json.dumps(event))
                await self.redis_client.ltrim("scanning_events", 0, 999)
                
            except Exception as e:
                logger.error(f"Error storing event in Redis: {e}")
        
        # Store in memory for active scans
        if scan_id in self.scan_events:
            self.scan_events[scan_id].append(event)
            # Keep only last 50 events in memory
            if len(self.scan_events[scan_id]) > 50:
                self.scan_events[scan_id].pop(0)
        
        # Log to file
        logger.info(f"SCAN_EVENT [{event_type.value}] {scan_id}: {json.dumps(data, default=str)}")
    
    async def _archive_scan_metrics(self, metrics: ScanMetrics):
        """Archive completed scan metrics"""
        if self.redis_client:
            try:
                metrics_data = asdict(metrics)
                # Convert datetime objects to strings
                for key, value in metrics_data.items():
                    if isinstance(value, datetime):
                        metrics_data[key] = value.isoformat()
                
                await self.redis_client.hset(
                    f"scan_metrics:{metrics.scan_id}",
                    mapping={
                        "data": json.dumps(metrics_data, default=str),
                        "completed_at": metrics.end_time.isoformat()
                    }
                )
                
                # Set expiration (30 days)
                await self.redis_client.expire(f"scan_metrics:{metrics.scan_id}", 30 * 24 * 3600)
                
            except Exception as e:
                logger.error(f"Error archiving metrics: {e}")
    
    async def get_scan_events(self, scan_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events for a specific scan"""
        events = []
        
        if self.redis_client:
            try:
                event_data = await self.redis_client.lrange(f"scan_events:{scan_id}", 0, limit - 1)
                events = [json.loads(event) for event in event_data]
            except Exception as e:
                logger.error(f"Error retrieving scan events: {e}")
        
        # Fallback to memory
        if not events and scan_id in self.scan_events:
            events = self.scan_events[scan_id][-limit:]
        
        return events
    
    async def get_platform_health_stats(self) -> Dict[str, Any]:
        """Get platform health statistics"""
        health_stats = {}
        
        for platform, health in self.platform_health.items():
            total_requests = health["success_count"] + health["failure_count"]
            success_rate = health["success_count"] / total_requests if total_requests > 0 else 0
            
            health_stats[platform] = {
                "success_rate": round(success_rate, 3),
                "total_requests": total_requests,
                "average_response_time": round(health["average_response_time"], 2),
                "last_success": health["last_success"],
                "last_failure": health["last_failure"],
                "status": "healthy" if success_rate > 0.8 else "degraded" if success_rate > 0.5 else "unhealthy"
            }
        
        return health_stats
    
    async def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_scans = [
            scan for scan in self.performance_history
            if scan.start_time >= cutoff_time
        ]
        
        if not recent_scans:
            return {
                "period_hours": hours,
                "total_scans": 0,
                "message": "No scans in the specified period"
            }
        
        total_scans = len(recent_scans)
        successful_scans = len([s for s in recent_scans if s.platforms_successful > 0])
        total_matches = sum(s.total_matches_found for s in recent_scans)
        total_dmca_notices = sum(s.dmca_notices_generated for s in recent_scans)
        average_duration = sum(s.duration_seconds for s in recent_scans) / total_scans
        
        return {
            "period_hours": hours,
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "success_rate": round(successful_scans / total_scans, 3),
            "total_matches_found": total_matches,
            "total_dmca_notices": total_dmca_notices,
            "average_scan_duration_minutes": round(average_duration / 60, 1),
            "scans_per_hour": round(total_scans / hours, 1),
            "matches_per_scan": round(total_matches / total_scans, 1) if total_scans > 0 else 0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_data = {
            "status": "healthy",
            "active_scans": len(self.active_scans),
            "redis_connected": self.redis_client is not None,
            "platform_health": await self.get_platform_health_stats(),
            "performance": await self.get_performance_summary(1),  # Last hour
            "check_timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine overall health status
        active_scan_count = len(self.active_scans)
        if active_scan_count > 10:
            health_data["status"] = "overloaded"
        
        platform_health = health_data["platform_health"]
        unhealthy_platforms = [p for p, h in platform_health.items() if h["status"] == "unhealthy"]
        if len(unhealthy_platforms) > len(platform_health) / 2:
            health_data["status"] = "degraded"
        
        await self._log_event("system", MonitoringEvent.HEALTH_CHECK, health_data)
        
        return health_data


# Global monitoring instance
scanning_monitor = ScanningMonitor()