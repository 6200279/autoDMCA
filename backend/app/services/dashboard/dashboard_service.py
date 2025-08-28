"""
Real-time Dashboard Service for AutoDMCA

This service provides real-time dashboard data by integrating:
- Database queries for actual metrics
- Health monitoring systems
- Performance metrics
- Alert system data
- User activity tracking
- Business intelligence aggregations

Replaces mock API with actual data from the system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from collections import defaultdict

from app.core.container import container
from app.core.database_service import database_service
from app.services.monitoring.health_monitor import health_monitor
from app.services.monitoring.performance_monitor import PerformanceMonitor
from app.services.notifications.alert_system import alert_system

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Comprehensive dashboard service providing real-time data
    
    Features:
    - Real-time statistics from database
    - Health and performance metrics integration
    - Alert system data aggregation
    - Trend analysis and predictions
    - Platform-specific analytics
    - User activity tracking
    """
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache
        self._cached_data = {}
        self._cache_timestamps = {}
    
    async def get_dashboard_overview(self, user_id: int) -> Dict[str, Any]:
        """Get complete dashboard overview with all widgets"""
        logger.info(f"Getting dashboard overview for user {user_id}")
        
        try:
            # Get all dashboard components in parallel
            async with database_service.get_session() as db:
                stats = await self.get_dashboard_stats(user_id, db)
                analytics = await self.get_analytics_data(user_id, db)
                activity = await self.get_recent_activity(user_id, db)
                alerts = await self.get_alert_summary(user_id)
                protection_metrics = await self.get_protection_metrics(user_id, db)
                platform_distribution = await self.get_platform_distribution(user_id, db)
                
            return {
                "stats": stats,
                "analytics": analytics,
                "activity": activity,
                "alerts": alerts,
                "protection_metrics": protection_metrics,
                "platform_distribution": platform_distribution,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard overview for user {user_id}: {e}")
            raise
    
    async def get_dashboard_stats(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get real-time dashboard statistics"""
        cache_key = f"dashboard_stats_{user_id}"
        
        # Check cache
        if self._is_cached(cache_key):
            return self._cached_data[cache_key]
        
        try:
            # Current period (last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            previous_start = start_date - timedelta(days=30)
            
            # Get profile count
            # Note: Using text() for complex queries that may not map directly to models
            profile_result = await db.execute(
                text("SELECT COUNT(*) FROM profiles WHERE user_id = :user_id AND created_at >= :start_date"),
                {"user_id": user_id, "start_date": start_date}
            )
            total_profiles = profile_result.scalar() or 0
            
            # Get active scans
            scan_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM scanning_jobs 
                WHERE user_id = :user_id AND status IN ('running', 'pending') 
                AND created_at >= :start_date
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            active_scans = scan_result.scalar() or 0
            
            # Get infringements found
            infringement_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM infringements 
                WHERE user_id = :user_id AND created_at >= :start_date
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            infringements_found = infringement_result.scalar() or 0
            
            # Get takedowns sent
            takedown_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM takedown_requests 
                WHERE user_id = :user_id AND sent_at >= :start_date
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            takedowns_sent = takedown_result.scalar() or 0
            
            # Get success rate (successful takedowns / total takedowns)
            success_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM takedown_requests 
                WHERE user_id = :user_id AND sent_at >= :start_date 
                AND status = 'successful'
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            successful_takedowns = success_result.scalar() or 0
            success_rate = (successful_takedowns / takedowns_sent * 100) if takedowns_sent > 0 else 0.0
            
            # Get scan coverage (profiles with recent scans / total profiles)
            coverage_result = await db.execute(
                text("""
                SELECT COUNT(DISTINCT profile_id) FROM scanning_jobs 
                WHERE user_id = :user_id AND created_at >= :start_date
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            scanned_profiles = coverage_result.scalar() or 0
            
            total_user_profiles = await db.execute(
                text("SELECT COUNT(*) FROM profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            total_user_profiles = total_user_profiles.scalar() or 1
            scan_coverage = (scanned_profiles / total_user_profiles * 100) if total_user_profiles > 0 else 0.0
            
            # Calculate change percentages (compare with previous period)
            prev_infringement_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM infringements 
                WHERE user_id = :user_id AND created_at >= :prev_start AND created_at < :start_date
                """),
                {"user_id": user_id, "prev_start": previous_start, "start_date": start_date}
            )
            prev_infringements = prev_infringement_result.scalar() or 0
            
            infringements_change = self._calculate_percentage_change(prev_infringements, infringements_found)
            
            prev_takedown_result = await db.execute(
                text("""
                SELECT COUNT(*) FROM takedown_requests 
                WHERE user_id = :user_id AND sent_at >= :prev_start AND sent_at < :start_date
                """),
                {"user_id": user_id, "prev_start": previous_start, "start_date": start_date}
            )
            prev_takedowns = prev_takedown_result.scalar() or 0
            takedowns_change = self._calculate_percentage_change(prev_takedowns, takedowns_sent)
            
            stats = {
                "period": {
                    "start": start_date.isoformat() + "Z",
                    "end": end_date.isoformat() + "Z"
                },
                "totalProfiles": total_profiles,
                "activeScans": active_scans,
                "infringementsFound": infringements_found,
                "takedownsSent": takedowns_sent,
                "successRate": round(success_rate, 1),
                "scanCoverage": round(scan_coverage, 1),
                "profilesChange": 0.0,  # Would need historical data
                "scansChange": 0.0,     # Would need historical data
                "infringementsChange": round(infringements_change, 1),
                "takedownsChange": round(takedowns_change, 1),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self._cache_data(cache_key, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats for user {user_id}: {e}")
            # Return fallback data
            return {
                "period": {
                    "start": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z",
                    "end": datetime.utcnow().isoformat() + "Z"
                },
                "totalProfiles": 0,
                "activeScans": 0,
                "infringementsFound": 0,
                "takedownsSent": 0,
                "successRate": 0.0,
                "scanCoverage": 0.0,
                "profilesChange": 0.0,
                "scansChange": 0.0,
                "infringementsChange": 0.0,
                "takedownsChange": 0.0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_analytics_data(self, user_id: int, db: AsyncSession, granularity: str = "day") -> Dict[str, Any]:
        """Get analytics data for charts and visualizations"""
        cache_key = f"analytics_{user_id}_{granularity}"
        
        if self._is_cached(cache_key):
            return self._cached_data[cache_key]
        
        try:
            # Get data for the last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            # Get daily aggregated data
            daily_data = []
            date_labels = []
            infringement_data = []
            takedown_data = []
            removal_data = []
            
            for i in range(30):
                day = start_date + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                # Count infringements for this day
                inf_result = await db.execute(
                    text("""
                    SELECT COUNT(*) FROM infringements 
                    WHERE user_id = :user_id AND created_at >= :day_start AND created_at < :day_end
                    """),
                    {"user_id": user_id, "day_start": day_start, "day_end": day_end}
                )
                infringements = inf_result.scalar() or 0
                
                # Count takedowns for this day
                takedown_result = await db.execute(
                    text("""
                    SELECT COUNT(*) FROM takedown_requests 
                    WHERE user_id = :user_id AND sent_at >= :day_start AND sent_at < :day_end
                    """),
                    {"user_id": user_id, "day_start": day_start, "day_end": day_end}
                )
                takedowns = takedown_result.scalar() or 0
                
                # Count successful removals for this day
                removal_result = await db.execute(
                    text("""
                    SELECT COUNT(*) FROM takedown_requests 
                    WHERE user_id = :user_id AND updated_at >= :day_start AND updated_at < :day_end
                    AND status = 'successful'
                    """),
                    {"user_id": user_id, "day_start": day_start, "day_end": day_end}
                )
                removals = removal_result.scalar() or 0
                
                date_labels.append(day.strftime("%Y-%m-%d"))
                infringement_data.append(infringements)
                takedown_data.append(takedowns)
                removal_data.append(removals)
                
                daily_data.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "infringements": infringements,
                    "takedowns": takedowns,
                    "removals": removals
                })
            
            # Get platform distribution
            platform_result = await db.execute(
                text("""
                SELECT platform, COUNT(*) as count 
                FROM infringements 
                WHERE user_id = :user_id AND created_at >= :start_date
                GROUP BY platform
                ORDER BY count DESC
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            platform_rows = platform_result.fetchall()
            
            platform_labels = []
            platform_data = []
            platform_colors = {
                "instagram": "#E1306C",
                "tiktok": "#000000",
                "youtube": "#FF0000",
                "facebook": "#1877F2",
                "twitter": "#1DA1F2",
                "onlyfans": "#00AFF0",
                "reddit": "#FF4500",
                "default": "#6B7280"
            }
            
            for row in platform_rows:
                platform, count = row
                platform_labels.append(platform.title() if platform else "Unknown")
                platform_data.append(count)
            
            # Get colors for platforms
            colors = [platform_colors.get(label.lower(), platform_colors["default"]) for label in platform_labels]
            
            # Calculate success rates by platform
            success_rates = []
            for platform_label in platform_labels:
                platform_lower = platform_label.lower()
                
                success_result = await db.execute(
                    text("""
                    SELECT 
                        COUNT(CASE WHEN tr.status = 'successful' THEN 1 END) as successful,
                        COUNT(*) as total
                    FROM takedown_requests tr
                    JOIN infringements i ON tr.infringement_id = i.id
                    WHERE tr.user_id = :user_id AND tr.sent_at >= :start_date
                    AND LOWER(i.platform) = :platform
                    """),
                    {"user_id": user_id, "start_date": start_date, "platform": platform_lower}
                )
                success_row = success_result.fetchone()
                
                if success_row and success_row[1] > 0:
                    success_rate = (success_row[0] / success_row[1]) * 100
                else:
                    success_rate = 0.0
                
                success_rates.append(round(success_rate, 1))
            
            analytics = {
                "granularity": granularity,
                "data": daily_data,
                "monthlyTrends": {
                    "labels": date_labels,
                    "datasets": [
                        {
                            "label": "Threats Detected",
                            "data": infringement_data,
                            "borderColor": "#ff6384",
                            "backgroundColor": "rgba(255, 99, 132, 0.2)",
                            "tension": 0.4
                        },
                        {
                            "label": "Actions Taken", 
                            "data": takedown_data,
                            "borderColor": "#36a2eb",
                            "backgroundColor": "rgba(54, 162, 235, 0.2)",
                            "tension": 0.4
                        },
                        {
                            "label": "Content Removed",
                            "data": removal_data,
                            "borderColor": "#4bc0c0", 
                            "backgroundColor": "rgba(75, 192, 192, 0.2)",
                            "tension": 0.4
                        }
                    ]
                },
                "platformDistribution": {
                    "labels": platform_labels,
                    "datasets": [{
                        "data": platform_data,
                        "backgroundColor": colors,
                        "borderColor": colors,
                        "borderWidth": 1
                    }]
                },
                "successRateByPlatform": {
                    "labels": platform_labels,
                    "datasets": [{
                        "label": "Success Rate (%)",
                        "data": success_rates,
                        "backgroundColor": "rgba(34, 197, 94, 0.8)",
                        "borderColor": "rgba(34, 197, 94, 1)",
                        "borderWidth": 1
                    }]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._cache_data(cache_key, analytics)
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics data for user {user_id}: {e}")
            return {
                "granularity": granularity,
                "data": [],
                "monthlyTrends": {"labels": [], "datasets": []},
                "platformDistribution": {"labels": [], "datasets": []},
                "successRateByPlatform": {"labels": [], "datasets": []},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_recent_activity(self, user_id: int, db: AsyncSession, limit: int = 10) -> Dict[str, Any]:
        """Get recent activity for the user"""
        try:
            activities = []
            
            # Get recent infringements
            inf_result = await db.execute(
                text("""
                SELECT id, platform, url, created_at, confidence_score
                FROM infringements 
                WHERE user_id = :user_id 
                ORDER BY created_at DESC 
                LIMIT 5
                """),
                {"user_id": user_id}
            )
            
            for row in inf_result.fetchall():
                inf_id, platform, url, created_at, confidence = row
                activities.append({
                    "id": f"inf_{inf_id}",
                    "type": "infringement",
                    "title": f"New infringement detected on {platform or 'Unknown'}",
                    "description": f"High-confidence match found: {url or 'URL not available'}",
                    "timestamp": created_at.isoformat() + "Z" if created_at else datetime.utcnow().isoformat() + "Z",
                    "status": "completed",
                    "confidence": confidence,
                    "platform": platform
                })
            
            # Get recent takedowns
            takedown_result = await db.execute(
                text("""
                SELECT tr.id, tr.status, tr.sent_at, i.platform, i.url
                FROM takedown_requests tr
                JOIN infringements i ON tr.infringement_id = i.id
                WHERE tr.user_id = :user_id 
                ORDER BY tr.sent_at DESC 
                LIMIT 5
                """),
                {"user_id": user_id}
            )
            
            for row in takedown_result.fetchall():
                td_id, status, sent_at, platform, url = row
                activities.append({
                    "id": f"td_{td_id}",
                    "type": "takedown",
                    "title": f"DMCA takedown sent to {platform or 'Unknown'}",
                    "description": f"Takedown notice sent for {url or 'content'}",
                    "timestamp": sent_at.isoformat() + "Z" if sent_at else datetime.utcnow().isoformat() + "Z",
                    "status": status or "pending",
                    "platform": platform
                })
            
            # Sort all activities by timestamp
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "activities": activities[:limit],
                "total": len(activities),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent activity for user {user_id}: {e}")
            return {
                "activities": [],
                "total": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_alert_summary(self, user_id: int) -> Dict[str, Any]:
        """Get alert summary from the alert system"""
        try:
            # Get active alerts for user (this would need to be implemented in the alert system)
            active_alerts = []  # Placeholder - alert_system.get_active_alerts_for_user(user_id)
            
            # Get alert preferences (placeholder)
            alert_preferences = {
                "email_enabled": True,
                "sms_enabled": False,
                "push_enabled": True,
                "webhook_enabled": False
            }
            
            return {
                "active_alerts": len(active_alerts),
                "unread_alerts": len([a for a in active_alerts if not a.get("read", False)]),
                "alert_types": {
                    "critical": len([a for a in active_alerts if a.get("severity") == "critical"]),
                    "warning": len([a for a in active_alerts if a.get("severity") == "warning"]),
                    "info": len([a for a in active_alerts if a.get("severity") == "info"])
                },
                "preferences": alert_preferences,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get alert summary for user {user_id}: {e}")
            return {
                "active_alerts": 0,
                "unread_alerts": 0,
                "alert_types": {"critical": 0, "warning": 0, "info": 0},
                "preferences": {"email_enabled": True, "sms_enabled": False, "push_enabled": True, "webhook_enabled": False},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_protection_metrics(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get protection effectiveness metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            # Get protection score components
            response_time_result = await db.execute(
                text("""
                SELECT AVG(EXTRACT(EPOCH FROM (sent_at - created_at))) / 3600 as avg_response_hours
                FROM takedown_requests tr
                JOIN infringements i ON tr.infringement_id = i.id
                WHERE tr.user_id = :user_id AND tr.sent_at >= :start_date
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            avg_response_hours = response_time_result.scalar() or 24.0
            
            # Calculate protection score (based on success rate, response time, coverage)
            stats = await self.get_dashboard_stats(user_id, db)
            success_rate = stats.get("successRate", 0.0)
            scan_coverage = stats.get("scanCoverage", 0.0)
            
            # Response time score (24 hours = 100%, decreases linearly)
            response_score = max(0, 100 - (avg_response_hours - 1) * 10)
            
            # Overall protection score (weighted average)
            protection_score = (success_rate * 0.4 + scan_coverage * 0.3 + response_score * 0.3)
            
            return {
                "protection_score": round(protection_score, 1),
                "success_rate": success_rate,
                "response_time_hours": round(avg_response_hours, 1),
                "scan_coverage": scan_coverage,
                "threat_level": "Low" if protection_score > 80 else "Medium" if protection_score > 60 else "High",
                "recommendations": self._get_protection_recommendations(protection_score, success_rate, avg_response_hours, scan_coverage),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get protection metrics for user {user_id}: {e}")
            return {
                "protection_score": 0.0,
                "success_rate": 0.0,
                "response_time_hours": 0.0,
                "scan_coverage": 0.0,
                "threat_level": "Unknown",
                "recommendations": [],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_platform_distribution(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get platform-specific metrics and distribution"""
        try:
            start_date = datetime.utcnow() - timedelta(days=30)
            
            platform_result = await db.execute(
                text("""
                SELECT 
                    COALESCE(i.platform, 'unknown') as platform,
                    COUNT(i.id) as infringement_count,
                    COUNT(tr.id) as takedown_count,
                    COUNT(CASE WHEN tr.status = 'successful' THEN 1 END) as success_count,
                    AVG(i.confidence_score) as avg_confidence
                FROM infringements i
                LEFT JOIN takedown_requests tr ON i.id = tr.infringement_id
                WHERE i.user_id = :user_id AND i.created_at >= :start_date
                GROUP BY i.platform
                ORDER BY infringement_count DESC
                """),
                {"user_id": user_id, "start_date": start_date}
            )
            
            platforms = []
            for row in platform_result.fetchall():
                platform, inf_count, td_count, success_count, avg_confidence = row
                
                success_rate = (success_count / td_count * 100) if td_count > 0 else 0.0
                
                platforms.append({
                    "platform": platform.title() if platform else "Unknown",
                    "infringement_count": inf_count,
                    "takedown_count": td_count,
                    "success_count": success_count,
                    "success_rate": round(success_rate, 1),
                    "average_confidence": round(avg_confidence or 0.0, 2),
                    "risk_level": "High" if avg_confidence and avg_confidence > 0.8 else "Medium" if avg_confidence and avg_confidence > 0.6 else "Low"
                })
            
            return {
                "platforms": platforms,
                "total_platforms": len(platforms),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get platform distribution for user {user_id}: {e}")
            return {
                "platforms": [],
                "total_platforms": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_system_health_for_dashboard(self) -> Dict[str, Any]:
        """Get system health metrics for dashboard display"""
        try:
            health_summary = await health_monitor.get_health_summary()
            
            return {
                "system_status": health_summary.get("status", "unknown"),
                "uptime_hours": health_summary.get("uptime_hours", 0),
                "services": health_summary.get("services", {}),
                "alerts_count": len(health_summary.get("alerts_triggered", [])),
                "timestamp": health_summary.get("timestamp", datetime.utcnow().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health for dashboard: {e}")
            return {
                "system_status": "unknown",
                "uptime_hours": 0,
                "services": {},
                "alerts_count": 0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_percentage_change(self, old_value: int, new_value: int) -> float:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        
        return ((new_value - old_value) / old_value) * 100
    
    def _get_protection_recommendations(self, protection_score: float, success_rate: float, response_time: float, coverage: float) -> List[str]:
        """Get recommendations based on protection metrics"""
        recommendations = []
        
        if success_rate < 70:
            recommendations.append("Consider optimizing DMCA templates for better success rates")
        
        if response_time > 6:
            recommendations.append("Enable automated takedown processing to reduce response time")
        
        if coverage < 80:
            recommendations.append("Increase scan frequency or add more platforms to improve coverage")
        
        if protection_score < 60:
            recommendations.append("Review and update content protection strategy")
        
        return recommendations
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and still valid"""
        if cache_key not in self._cached_data:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False
        
        return (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl
    
    def _cache_data(self, cache_key: str, data: Any):
        """Cache data with timestamp"""
        self._cached_data[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.utcnow()


# Global dashboard service instance
dashboard_service = DashboardService()


__all__ = [
    'DashboardService',
    'dashboard_service'
]