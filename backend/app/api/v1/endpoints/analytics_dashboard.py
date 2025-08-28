"""
Advanced Analytics Dashboard API Endpoints
Implements PRD requirement for comprehensive analytics with removal metrics

PRD Requirements:
- "Comprehensive analytics dashboard with removal metrics"
- "Detailed reports showing removal success rates, response times, etc."
- "Track DMCA success rates, response times, and removal effectiveness"
- "Analytics to help users understand their protection coverage"
"""

import logging
from typing import Any, List, Optional, Dict
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from enum import Enum

from app.db.session import get_async_session
from app.db.models.user import User
from app.api.deps.auth import get_current_verified_user
from app.services.billing.subscription_tier_enforcement import subscription_enforcement

logger = logging.getLogger(__name__)
router = APIRouter()


class TimeRange(str, Enum):
    """Time range options for analytics"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Types of metrics available"""
    SCANS = "scans"
    INFRINGEMENTS = "infringements"
    DMCA_REQUESTS = "dmca_requests"
    REMOVALS = "removals"
    SUCCESS_RATE = "success_rate"
    RESPONSE_TIME = "response_time"
    PLATFORMS = "platforms"
    SITES = "sites"


class DashboardOverviewResponse(BaseModel):
    """Main dashboard overview response"""
    total_scans_performed: int
    total_infringements_found: int
    total_dmca_sent: int
    total_content_removed: int
    overall_success_rate: float
    avg_response_time_hours: float
    active_monitoring_profiles: int
    protection_score: float
    
    # Trends (compared to previous period)
    scans_trend: float
    infringements_trend: float
    dmca_trend: float
    removals_trend: float
    success_rate_trend: float
    
    # Recent activity summary
    last_scan_at: Optional[datetime]
    recent_high_priority_alerts: int
    pending_takedown_requests: int


class DetailedMetricsResponse(BaseModel):
    """Detailed metrics for specific time periods"""
    time_range: TimeRange
    period_start: datetime
    period_end: datetime
    
    # Core metrics
    daily_breakdown: List[Dict[str, Any]]
    platform_breakdown: List[Dict[str, Any]]
    site_breakdown: List[Dict[str, Any]]
    content_type_breakdown: List[Dict[str, Any]]
    
    # Performance metrics
    success_rates_by_platform: List[Dict[str, Any]]
    response_times_by_platform: List[Dict[str, Any]]
    removal_effectiveness: List[Dict[str, Any]]
    
    # Advanced analytics
    detection_patterns: List[Dict[str, Any]]
    cost_savings_estimate: float
    time_saved_hours: float


class PlatformPerformanceResponse(BaseModel):
    """Platform-specific performance metrics"""
    platform_name: str
    total_infringements: int
    successful_removals: int
    success_rate: float
    avg_response_time_hours: float
    fastest_removal_time: float
    slowest_response_time: float
    
    # Trend data
    monthly_trends: List[Dict[str, Any]]
    removal_method_effectiveness: Dict[str, float]
    
    # Risk assessment
    threat_level: str  # low, medium, high, critical
    growth_trend: float
    recommendations: List[str]


class RealTimeActivityResponse(BaseModel):
    """Real-time activity and alerts"""
    current_active_scans: int
    scans_completed_today: int
    new_infringements_today: int
    takedown_requests_sent_today: int
    successful_removals_today: int
    
    # Recent activity feed
    recent_activities: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    
    # Current status
    system_health: str
    last_update: datetime


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    time_range: TimeRange = Query(TimeRange.LAST_30_DAYS),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get main dashboard overview with key metrics
    
    PRD: Main analytics dashboard showing overall protection status
    """
    
    logger.info(f"Getting dashboard overview for user {current_user.id}")
    
    try:
        # Calculate time period
        end_date = datetime.utcnow()
        if time_range == TimeRange.TODAY:
            start_date = datetime.combine(end_date.date(), datetime.min.time())
        elif time_range == TimeRange.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif time_range == TimeRange.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)  # Default
        
        # Mock data - would query actual database in production
        current_metrics = {
            "total_scans_performed": 1247,
            "total_infringements_found": 89,
            "total_dmca_sent": 67,
            "total_content_removed": 52,
            "overall_success_rate": 77.6,
            "avg_response_time_hours": 18.5,
            "active_monitoring_profiles": 3,
            "protection_score": 85.2
        }
        
        # Mock previous period for trends
        previous_metrics = {
            "total_scans_performed": 1156,
            "total_infringements_found": 95,
            "total_dmca_sent": 58,
            "total_content_removed": 41,
            "overall_success_rate": 70.7
        }
        
        # Calculate trends
        trends = {}
        for key in ["total_scans_performed", "total_infringements_found", "total_dmca_sent", "total_content_removed", "overall_success_rate"]:
            if previous_metrics.get(key, 0) > 0:
                trends[f"{key.replace('total_', '').replace('overall_', '')}_trend"] = (
                    (current_metrics[key] - previous_metrics[key]) / previous_metrics[key] * 100
                )
            else:
                trends[f"{key.replace('total_', '').replace('overall_', '')}_trend"] = 0.0
        
        return DashboardOverviewResponse(
            **current_metrics,
            **trends,
            last_scan_at=datetime.utcnow() - timedelta(hours=2),
            recent_high_priority_alerts=3,
            pending_takedown_requests=8
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard overview"
        )


@router.get("/metrics", response_model=DetailedMetricsResponse)
async def get_detailed_metrics(
    time_range: TimeRange = Query(TimeRange.LAST_30_DAYS),
    metric_types: List[MetricType] = Query([MetricType.SCANS, MetricType.INFRINGEMENTS, MetricType.REMOVALS]),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get detailed metrics breakdown for specified time range
    
    PRD: Detailed analytics showing breakdown by platform, time, content type
    """
    
    logger.info(f"Getting detailed metrics for user {current_user.id}, range: {time_range}")
    
    try:
        # Calculate time period
        end_date = datetime.utcnow()
        if time_range == TimeRange.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif time_range == TimeRange.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        elif time_range == TimeRange.LAST_90_DAYS:
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Mock detailed breakdown data
        daily_breakdown = []
        days = (end_date - start_date).days
        for i in range(days):
            day = start_date + timedelta(days=i)
            daily_breakdown.append({
                "date": day.date().isoformat(),
                "scans": 35 + (i % 10) * 3,
                "infringements": 2 + (i % 5),
                "dmca_sent": 1 + (i % 3),
                "removals": 1 if i % 4 == 0 else 0
            })
        
        platform_breakdown = [
            {"platform": "OnlyFans Leaks", "infringements": 34, "success_rate": 82.4},
            {"platform": "File Sharing Sites", "infringements": 22, "success_rate": 68.2},
            {"platform": "Forums", "infringements": 15, "success_rate": 73.3},
            {"platform": "Social Media", "infringements": 12, "success_rate": 91.7},
            {"platform": "Image Boards", "infringements": 6, "success_rate": 50.0}
        ]
        
        site_breakdown = [
            {"site": "ThotHub", "infringements": 18, "success_rate": 77.8},
            {"site": "LeakedModels", "infringements": 16, "success_rate": 87.5},
            {"site": "MEGA", "infringements": 12, "success_rate": 58.3},
            {"site": "Reddit", "infringements": 10, "success_rate": 100.0},
            {"site": "4chan", "infringements": 8, "success_rate": 25.0}
        ]
        
        content_type_breakdown = [
            {"type": "Images", "count": 45, "success_rate": 78.9},
            {"type": "Videos", "count": 28, "success_rate": 75.0},
            {"type": "Profile Content", "count": 16, "success_rate": 87.5}
        ]
        
        success_rates_by_platform = [
            {"platform": "Social Media", "success_rate": 91.7},
            {"platform": "OnlyFans Leaks", "success_rate": 82.4},
            {"platform": "Forums", "success_rate": 73.3},
            {"platform": "File Sharing", "success_rate": 68.2},
            {"platform": "Image Boards", "success_rate": 50.0}
        ]
        
        response_times_by_platform = [
            {"platform": "Social Media", "avg_hours": 6.2},
            {"platform": "Forums", "avg_hours": 12.8},
            {"platform": "OnlyFans Leaks", "avg_hours": 24.5},
            {"platform": "File Sharing", "avg_hours": 36.7},
            {"platform": "Image Boards", "avg_hours": 72.1}
        ]
        
        removal_effectiveness = [
            {"method": "DMCA Takedown", "success_rate": 78.3, "avg_time_hours": 22.1},
            {"method": "Platform Report", "success_rate": 85.7, "avg_time_hours": 8.4},
            {"method": "Legal Notice", "success_rate": 92.1, "avg_time_hours": 48.2}
        ]
        
        detection_patterns = [
            {"pattern": "Peak activity: 2PM-6PM EST", "impact": "35% of infringements detected"},
            {"pattern": "Weekend spikes on leak sites", "impact": "23% higher weekend activity"},
            {"pattern": "New content leaked within 24hrs", "impact": "67% detected same day"}
        ]
        
        return DetailedMetricsResponse(
            time_range=time_range,
            period_start=start_date,
            period_end=end_date,
            daily_breakdown=daily_breakdown,
            platform_breakdown=platform_breakdown,
            site_breakdown=site_breakdown,
            content_type_breakdown=content_type_breakdown,
            success_rates_by_platform=success_rates_by_platform,
            response_times_by_platform=response_times_by_platform,
            removal_effectiveness=removal_effectiveness,
            detection_patterns=detection_patterns,
            cost_savings_estimate=15420.50,
            time_saved_hours=184.5
        )
        
    except Exception as e:
        logger.error(f"Failed to get detailed metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve detailed metrics"
        )


@router.get("/platform/{platform_name}", response_model=PlatformPerformanceResponse)
async def get_platform_performance(
    platform_name: str,
    time_range: TimeRange = Query(TimeRange.LAST_30_DAYS),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get detailed performance metrics for specific platform
    
    PRD: Platform-specific analytics with success rates and response times
    """
    
    logger.info(f"Getting platform performance for {platform_name}, user {current_user.id}")
    
    try:
        # Mock platform-specific data
        platform_data = {
            "onlyfans": {
                "platform_name": "OnlyFans Leak Sites",
                "total_infringements": 34,
                "successful_removals": 28,
                "success_rate": 82.4,
                "avg_response_time_hours": 24.5,
                "fastest_removal_time": 4.2,
                "slowest_response_time": 96.8,
                "threat_level": "high",
                "growth_trend": 15.3
            },
            "social_media": {
                "platform_name": "Social Media Platforms",
                "total_infringements": 12,
                "successful_removals": 11,
                "success_rate": 91.7,
                "avg_response_time_hours": 6.2,
                "fastest_removal_time": 1.5,
                "slowest_response_time": 18.3,
                "threat_level": "medium",
                "growth_trend": -2.1
            },
            "file_sharing": {
                "platform_name": "File Sharing Sites",
                "total_infringements": 22,
                "successful_removals": 15,
                "success_rate": 68.2,
                "avg_response_time_hours": 36.7,
                "fastest_removal_time": 8.5,
                "slowest_response_time": 168.2,
                "threat_level": "high",
                "growth_trend": 8.7
            }
        }
        
        platform_key = platform_name.lower().replace(" ", "_").replace("-", "_")
        if platform_key not in platform_data:
            platform_key = "onlyfans"  # Default
        
        data = platform_data[platform_key]
        
        # Mock monthly trends
        monthly_trends = [
            {"month": "Jan", "infringements": 25, "success_rate": 76.0},
            {"month": "Feb", "infringements": 28, "success_rate": 78.6},
            {"month": "Mar", "infringements": 32, "success_rate": 81.2},
            {"month": "Apr", "infringements": 34, "success_rate": 82.4}
        ]
        
        removal_method_effectiveness = {
            "dmca_takedown": 78.3,
            "platform_report": 85.7,
            "legal_notice": 92.1,
            "direct_contact": 45.2
        }
        
        # Generate recommendations based on performance
        recommendations = []
        if data["success_rate"] < 70:
            recommendations.append(f"Success rate below 70% - consider alternative takedown methods")
        if data["avg_response_time_hours"] > 48:
            recommendations.append("Response times are slow - prioritize this platform for optimization")
        if data["growth_trend"] > 10:
            recommendations.append("Growing threat detected - increase monitoring frequency")
        if data["success_rate"] > 90:
            recommendations.append("Excellent performance - use this strategy as a template for other platforms")
        
        return PlatformPerformanceResponse(
            **data,
            monthly_trends=monthly_trends,
            removal_method_effectiveness=removal_method_effectiveness,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get platform performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform performance data"
        )


@router.get("/realtime", response_model=RealTimeActivityResponse)
async def get_realtime_activity(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get real-time activity and current status
    
    PRD: Real-time dashboard updates and activity monitoring
    """
    
    logger.info(f"Getting real-time activity for user {current_user.id}")
    
    try:
        # Mock real-time activity data
        recent_activities = [
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "type": "infringement_detected",
                "title": "New infringement detected on ThotHub",
                "details": "High confidence match (87%) found for Profile Content",
                "priority": "high"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "type": "content_removed",
                "title": "Content successfully removed from Reddit",
                "details": "DMCA takedown successful in 4.2 hours",
                "priority": "medium"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "type": "scan_completed",
                "title": "Daily content scan completed",
                "details": "Scanned 45 sites, found 3 potential matches",
                "priority": "low"
            }
        ]
        
        active_alerts = [
            {
                "alert_id": "alert_001",
                "type": "high_confidence_match",
                "title": "High confidence match requires review",
                "site": "LeakedModels",
                "confidence": 94,
                "created_at": (datetime.utcnow() - timedelta(minutes=45)).isoformat()
            },
            {
                "alert_id": "alert_002", 
                "type": "dmca_response_overdue",
                "title": "DMCA response overdue",
                "site": "MEGA",
                "days_overdue": 3,
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
            }
        ]
        
        return RealTimeActivityResponse(
            current_active_scans=2,
            scans_completed_today=8,
            new_infringements_today=3,
            takedown_requests_sent_today=2,
            successful_removals_today=1,
            recent_activities=recent_activities,
            active_alerts=active_alerts,
            system_health="healthy",
            last_update=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get real-time activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve real-time activity"
        )


@router.get("/export")
async def export_analytics_data(
    time_range: TimeRange = Query(TimeRange.LAST_30_DAYS),
    format: str = Query("csv", regex="^(csv|json|xlsx)$"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Export analytics data in various formats
    
    PRD: Data export capabilities for external analysis
    """
    
    logger.info(f"Exporting analytics data for user {current_user.id}, format: {format}")
    
    try:
        # Check subscription tier for export limits
        tier, metadata = await subscription_enforcement.get_user_subscription_tier(
            db, current_user.id
        )
        
        if tier.value == "basic" and format in ["xlsx"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "upgrade_required",
                    "message": "Excel export requires Professional tier",
                    "current_tier": tier.value,
                    "required_tier": "professional"
                }
            )
        
        # Generate export data (mock)
        export_data = {
            "export_generated_at": datetime.utcnow().isoformat(),
            "time_range": time_range.value,
            "user_id": current_user.id,
            "summary_metrics": {
                "total_scans": 1247,
                "total_infringements": 89,
                "success_rate": 77.6
            },
            "detailed_records": [
                {
                    "date": "2025-01-15",
                    "site": "ThotHub", 
                    "infringement_type": "Profile Content",
                    "confidence": 87,
                    "action_taken": "DMCA Sent",
                    "status": "Pending",
                    "response_time_hours": None
                }
            ]
        }
        
        if format == "csv":
            # Would generate CSV format
            return {"message": "CSV export generated", "download_url": "/downloads/analytics.csv"}
        elif format == "xlsx":
            # Would generate Excel format
            return {"message": "Excel export generated", "download_url": "/downloads/analytics.xlsx"}
        else:
            return export_data
            
    except Exception as e:
        logger.error(f"Failed to export analytics data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export analytics data"
        )


@router.get("/protection-score")
async def get_protection_score(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get comprehensive protection score and recommendations
    
    PRD: Overall protection effectiveness scoring
    """
    
    logger.info(f"Getting protection score for user {current_user.id}")
    
    try:
        # Calculate comprehensive protection score
        # Mock calculation based on various factors
        
        score_factors = {
            "detection_coverage": 85.2,  # How much of the web is being monitored
            "response_speed": 78.6,      # How quickly takedowns are processed
            "success_rate": 82.4,        # DMCA success rate
            "monitoring_frequency": 90.0, # How often scans are performed
            "false_positive_rate": 92.3   # Accuracy of detection (inverted)
        }
        
        # Weighted average (customize weights based on importance)
        weights = {
            "detection_coverage": 0.25,
            "response_speed": 0.20,
            "success_rate": 0.25,
            "monitoring_frequency": 0.15,
            "false_positive_rate": 0.15
        }
        
        overall_score = sum(score_factors[factor] * weights[factor] for factor in score_factors)
        
        # Generate recommendations based on weakest areas
        recommendations = []
        for factor, score in score_factors.items():
            if score < 80:
                if factor == "detection_coverage":
                    recommendations.append("Expand monitoring to additional platforms and leak sites")
                elif factor == "response_speed":
                    recommendations.append("Optimize DMCA template generation and submission process")
                elif factor == "success_rate":
                    recommendations.append("Review and improve takedown request templates and approach")
                elif factor == "monitoring_frequency":
                    recommendations.append("Upgrade to Professional tier for continuous monitoring")
                elif factor == "false_positive_rate":
                    recommendations.append("Fine-tune content matching algorithms to reduce false positives")
        
        return {
            "overall_protection_score": round(overall_score, 1),
            "score_factors": score_factors,
            "factor_explanations": {
                "detection_coverage": "Percentage of relevant sites and platforms being monitored",
                "response_speed": "How quickly we respond to detected infringements",
                "success_rate": "Percentage of takedown requests that result in content removal",
                "monitoring_frequency": "How often your content is scanned for infringements",
                "false_positive_rate": "Accuracy of infringement detection (100% - false positive rate)"
            },
            "grade": "A" if overall_score >= 90 else "B" if overall_score >= 80 else "C" if overall_score >= 70 else "D",
            "recommendations": recommendations,
            "benchmark_comparison": {
                "your_score": round(overall_score, 1),
                "industry_average": 72.3,
                "top_10_percent": 91.2
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get protection score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate protection score"
        )


__all__ = ['router']