from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, extract
from datetime import datetime, timedelta

from app.db.session import get_db, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.models.profile import ProtectedProfile
from app.db.models.infringement import Infringement
from app.db.models.takedown import TakedownRequest
from app.schemas.dashboard import (
    DashboardOverview,
    DashboardStats,
    InfringementTrend,
    PlatformDistribution,
    RecentActivity,
    AlertSummary,
    ProtectionMetrics,
    QuickAction,
    TimeSeriesData,
    AlertPreferences,
    CustomWidget,
    WidgetCreate,
    WidgetUpdate,
    ReportRequest,
    ScheduledReport
)
from app.schemas.common import StatusResponse
from app.api.deps.auth import get_current_verified_user
from app.core.container import container

router = APIRouter()


# =============================================================================
# Real-time Dashboard Endpoints (Frontend Compatible)
# =============================================================================

@router.get("/stats")
async def get_dashboard_stats_v2(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get dashboard statistics (compatible with frontend expectations)"""
    try:
        dashboard_service = await container.get('DashboardService')
        stats = await dashboard_service.get_dashboard_stats(current_user.id, db)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard stats: {str(e)}"
        )


@router.get("/activity")
async def get_dashboard_activity_v2(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get recent activity (compatible with frontend expectations)"""
    try:
        dashboard_service = await container.get('DashboardService')
        activity = await dashboard_service.get_recent_activity(current_user.id, db, limit)
        return activity
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard activity: {str(e)}"
        )


@router.get("/analytics")
async def get_dashboard_analytics_v2(
    granularity: str = Query("day", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get analytics data for charts (compatible with frontend expectations)"""
    try:
        dashboard_service = await container.get('DashboardService')
        analytics = await dashboard_service.get_analytics_data(current_user.id, db, granularity)
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard analytics: {str(e)}"
        )


@router.get("/platform-distribution")
async def get_platform_distribution_v2(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get platform distribution metrics"""
    try:
        dashboard_service = await container.get('DashboardService')
        platforms = await dashboard_service.get_platform_distribution(current_user.id, db)
        return platforms
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get platform distribution: {str(e)}"
        )


@router.get("/protection-metrics")
async def get_protection_metrics_v2(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get protection effectiveness metrics"""
    try:
        dashboard_service = await container.get('DashboardService')
        metrics = await dashboard_service.get_protection_metrics(current_user.id, db)
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get protection metrics: {str(e)}"
        )


@router.get("/alerts")
async def get_alert_summary_v2(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """Get alert summary"""
    try:
        dashboard_service = await container.get('DashboardService')
        alerts = await dashboard_service.get_alert_summary(current_user.id)
        
        return alerts
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alert summary: {str(e)}"
        )


@router.get("/system-health")
async def get_system_health_v2(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """Get system health metrics for dashboard"""
    try:
        dashboard_service = await container.get('DashboardService')
        health = await dashboard_service.get_system_health_for_dashboard()
        
        return health
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/overview-v2")
async def get_dashboard_overview_v2(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """Get complete dashboard overview (real-time version)"""
    try:
        dashboard_service = await container.get('DashboardService')
        overview = await dashboard_service.get_dashboard_overview(current_user.id)
        
        return overview
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )


# =============================================================================
# Legacy Dashboard Endpoints (for backward compatibility)
# =============================================================================

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get complete dashboard overview."""
    
    # Get basic statistics
    stats = await get_dashboard_statistics(current_user, db)
    
    # Get infringement trend (last 30 days)
    trend = await get_infringement_trend_data(current_user, db, "daily", 30)
    
    # Get platform distribution
    platform_dist = await get_platform_distribution_data(current_user, db)
    
    # Get recent activity
    recent_activity = await get_recent_activity_data(current_user, db)
    
    # Get alert summary
    alerts = await get_alert_summary_data(current_user, db)
    
    # Get protection metrics
    protection_metrics = await get_protection_metrics_data(current_user, db)
    
    # Get quick actions
    quick_actions = await get_quick_actions_data(current_user, db)
    
    return DashboardOverview(
        stats=stats,
        infringement_trend=trend,
        platform_distribution=platform_dist,
        recent_activity=recent_activity,
        alerts=alerts,
        protection_metrics=protection_metrics,
        quick_actions=quick_actions
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start: Optional[str] = Query(None, description="Start date"),
    end: Optional[str] = Query(None, description="End date"), 
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get dashboard statistics."""
    return await get_dashboard_statistics(current_user, db)


@router.get("/trends", response_model=InfringementTrend)
async def get_infringement_trends(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Time period"),
    days: int = Query(30, ge=7, le=365, description="Number of days"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get infringement trend data."""
    return await get_infringement_trend_data(current_user, db, period, days)


@router.get("/platforms", response_model=List[PlatformDistribution])
async def get_platform_distribution(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get platform distribution data."""
    return await get_platform_distribution_data(current_user, db, days)


@router.get("/activity", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of activities"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get recent activity data."""
    return await get_recent_activity_data(current_user, db, limit)


@router.get("/alerts", response_model=AlertSummary)
async def get_alert_summary(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get alert summary."""
    return await get_alert_summary_data(current_user, db)


@router.get("/metrics", response_model=ProtectionMetrics)
async def get_protection_metrics(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get protection metrics."""
    return await get_protection_metrics_data(current_user, db)


@router.get("/quick-actions", response_model=List[QuickAction])
async def get_quick_actions(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get quick actions."""
    return await get_quick_actions_data(current_user, db)


@router.get("/alert-preferences", response_model=AlertPreferences)
async def get_alert_preferences(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """Get user alert preferences."""
    # In a real implementation, this would come from user_settings table
    return AlertPreferences(
        email_alerts=True,
        sms_alerts=False,
        push_alerts=True,
        alert_threshold="medium",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00"
    )


@router.put("/alert-preferences", response_model=AlertPreferences)
async def update_alert_preferences(
    preferences: AlertPreferences,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user alert preferences."""
    # In a real implementation, this would update the user_settings table
    return preferences


@router.get("/widgets", response_model=List[CustomWidget])
async def get_dashboard_widgets(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's dashboard widgets."""
    # In a real implementation, this would query custom_widgets table
    return []


@router.post("/widgets", response_model=CustomWidget, status_code=status.HTTP_201_CREATED)
async def create_dashboard_widget(
    widget_data: WidgetCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create custom dashboard widget."""
    # In a real implementation, this would create a widget in custom_widgets table
    widget = CustomWidget(
        id=1,
        user_id=current_user.id,
        widget_type=widget_data.widget_type,
        title=widget_data.title,
        configuration=widget_data.configuration,
        position=widget_data.position,
        is_visible=True,
        created_at=datetime.utcnow()
    )
    
    return widget


@router.put("/widgets/{widget_id}", response_model=CustomWidget)
async def update_dashboard_widget(
    widget_id: int,
    widget_update: WidgetUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update dashboard widget."""
    # In a real implementation, this would update the widget in custom_widgets table
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Widget not found"
    )


@router.delete("/widgets/{widget_id}", response_model=StatusResponse)
async def delete_dashboard_widget(
    widget_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete dashboard widget."""
    # In a real implementation, this would delete the widget from custom_widgets table
    return StatusResponse(success=True, message="Widget deleted successfully")


@router.post("/reports/generate", response_model=StatusResponse)
async def generate_report(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Generate and send report."""
    # Schedule report generation
    background_tasks.add_task(
        generate_user_report,
        current_user.id,
        report_request.dict()
    )
    
    return StatusResponse(success=True, message="Report generation scheduled")


@router.get("/reports/scheduled", response_model=List[ScheduledReport])
async def get_scheduled_reports(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's scheduled reports."""
    # In a real implementation, this would query scheduled_reports table
    return []


# Helper functions
async def get_dashboard_statistics(user: User, db: Session) -> DashboardStats:
    """Get dashboard statistics for user."""
    # Mock data for local testing (avoiding async db issues)
    return DashboardStats(
        total_profiles=5,
        active_infringements=12,
        pending_takedowns=3,
        resolved_this_month=28,
        protection_score=94.5,
        scan_success_rate=96.8,
        takedown_success_rate=89.2,
        last_scan=datetime.utcnow() - timedelta(hours=2)
    )


async def get_infringement_trend_data(user: User, db: Session, period: str, days: int) -> InfringementTrend:
    """Get infringement trend data."""
    # Mock trend data for local testing
    from app.schemas.dashboard import InfringementTrend, TimeSeriesData
    
    # Generate mock time series data
    end_date = datetime.utcnow().date()
    time_series = []
    
    if period == "daily":
        for i in range(days):
            date = end_date - timedelta(days=i)
            value = max(0, 15 + (i % 7) - 3 + (i % 3))  # Mock pattern
            time_series.append(TimeSeriesData(date=date, value=value))
    elif period == "weekly":
        weeks = days // 7
        for i in range(weeks):
            date = end_date - timedelta(weeks=i)
            value = max(0, 45 + (i % 4) * 10 - 15)
            time_series.append(TimeSeriesData(date=date, value=value))
    else:  # monthly
        months = days // 30
        for i in range(months):
            date = end_date.replace(day=1) - timedelta(days=i * 30)
            value = max(0, 120 + (i % 3) * 20 - 30)
            time_series.append(TimeSeriesData(date=date, value=value))
    
    time_series.reverse()  # Chronological order
    
    # Calculate changes
    total_change = sum(point.value for point in time_series)
    percentage_change = 12.5  # Mock positive change
    
    return InfringementTrend(
        period=period,
        data=time_series,
        total_change=total_change,
        percentage_change=percentage_change
    )


async def get_platform_distribution_data(user: User, db: Session, days: int = 30) -> List[PlatformDistribution]:
    """Get platform distribution data."""
    # Mock platform distribution data for local testing
    from app.schemas.dashboard import PlatformDistribution
    
    distributions = [
        PlatformDistribution(
            platform="Instagram",
            count=45,
            percentage=35.7,
            trend="up"
        ),
        PlatformDistribution(
            platform="TikTok", 
            count=32,
            percentage=25.4,
            trend="stable"
        ),
        PlatformDistribution(
            platform="YouTube",
            count=23,
            percentage=18.3,
            trend="down"
        ),
        PlatformDistribution(
            platform="Twitter",
            count=18,
            percentage=14.3,
            trend="stable"
        ),
        PlatformDistribution(
            platform="Others",
            count=8,
            percentage=6.3,
            trend="up"
        )
    ]
    
    return distributions


async def get_recent_activity_data(user: User, db: Session, limit: int = 20) -> List[RecentActivity]:
    """Get recent activity data."""
    # Mock activity data for local testing
    from app.schemas.dashboard import RecentActivity
    
    activities = [
        RecentActivity(
            id=1,
            type="infringement_found",
            title="New infringement detected",
            description="Found on Instagram: https://instagram.com/fake-account...",
            platform="instagram",
            profile_name="Content Creator Pro",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            severity="high"
        ),
        RecentActivity(
            id=2,
            type="content_removed",
            title="Content successfully removed",
            description="Takedown successful via DMCA notice",
            platform="tiktok",
            profile_name="Artistic Content",
            timestamp=datetime.utcnow() - timedelta(hours=3),
            severity="high"
        ),
        RecentActivity(
            id=3,
            type="takedown_sent",
            title="Takedown notice sent",
            description="Notice sent to legal@youtube.com",
            platform="youtube",
            profile_name="Video Content",
            timestamp=datetime.utcnow() - timedelta(hours=5),
            severity="medium"
        )
    ]
    
    return activities[:limit]


async def get_alert_summary_data(user: User, db: Session) -> AlertSummary:
    """Get alert summary data."""
    # In a real implementation, this would query alerts/notifications table
    return AlertSummary(
        total_alerts=0,
        high_priority=0,
        medium_priority=0,
        low_priority=0,
        unread_count=0
    )


async def get_protection_metrics_data(user: User, db: Session) -> ProtectionMetrics:
    """Get protection metrics data."""
    # Mock protection metrics for local testing
    from app.schemas.dashboard import ProtectionMetrics
    
    return ProtectionMetrics(
        profiles_monitored=5,
        content_pieces_protected=47,
        platforms_monitored=8,
        average_detection_time=2.3,
        average_removal_time=36.2,
        proactive_removals=28,
        reactive_removals=12
    )


async def get_quick_actions_data(user: User, db: Session) -> List[QuickAction]:
    """Get quick actions data."""
    # Mock data for local testing
    from app.schemas.dashboard import QuickAction
    
    actions = [
        QuickAction(
            action="scan_profiles",
            label="Start New Scan",
            icon="search",
            url="/api/v1/profiles/scan",
            count=None,
            enabled=True
        ),
        QuickAction(
            action="review_infringements",
            label="Review Pending",
            icon="alert-triangle",
            url="/api/v1/infringements?status=pending",
            count=8,
            enabled=True
        ),
        QuickAction(
            action="send_takedowns",
            label="Send Takedowns",
            icon="send",
            url="/api/v1/takedowns?status=draft",
            count=3,
            enabled=True
        ),
        QuickAction(
            action="add_profile",
            label="Add Profile",
            icon="plus",
            url="/api/v1/profiles",
            count=None,
            enabled=True
        ),
        QuickAction(
            action="generate_report",
            label="Generate Report",
            icon="file-text",
            url="/api/v1/dashboard/reports/generate",
            count=None,
            enabled=True
        )
    ]
    
    return actions


@router.get("/usage")
async def get_usage_metrics(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get usage metrics."""
    # Mock usage data for local testing
    return {
        "total_scans": 150,
        "total_takedowns": 45,
        "bandwidth_used": "2.3 GB",
        "storage_used": "500 MB",
        "api_calls": 1250,
        "monthly_limit": 5000,
        "usage_percentage": 25.0
    }


@router.get("/analytics")
async def get_analytics_data(
    granularity: str = Query("month", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get analytics data."""
    # Mock analytics data for local testing
    return {
        "infringement_count": [
            {"date": "2025-01", "value": 12},
            {"date": "2025-02", "value": 18},
            {"date": "2025-03", "value": 8}
        ],
        "takedown_success": [
            {"date": "2025-01", "value": 85},
            {"date": "2025-02", "value": 92},
            {"date": "2025-03", "value": 78}
        ],
        "platform_activity": {
            "instagram": 45,
            "tiktok": 32,
            "youtube": 23,
            "twitter": 18
        }
    }


@router.get("/platform-distribution")
async def get_platform_distribution_endpoint(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get platform distribution data (specific endpoint for frontend calls)."""
    # Mock platform distribution data for local testing  
    return [
        {"platform": "Instagram", "count": 45, "percentage": 35.7, "trend": "up"},
        {"platform": "TikTok", "count": 32, "percentage": 25.4, "trend": "stable"},
        {"platform": "YouTube", "count": 23, "percentage": 18.3, "trend": "down"},
        {"platform": "Twitter", "count": 18, "percentage": 14.3, "trend": "stable"},
        {"platform": "Others", "count": 8, "percentage": 6.3, "trend": "up"}
    ]


@router.get("/preferences")
async def get_dashboard_preferences(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """Get dashboard preferences."""
    # Mock preferences for local testing
    return {
        "theme": "light",
        "refresh_interval": 300,
        "show_notifications": True,
        "default_date_range": "30days",
        "chart_type": "line",
        "widgets_enabled": ["stats", "activity", "charts"]
    }


@router.put("/preferences")
async def update_dashboard_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update dashboard preferences."""
    # Mock update for local testing
    return preferences


async def generate_user_report(user_id: int, report_config: dict):
    """Generate user report (background task)."""
    from app.services.reporting.report_generator import generate_report
    await generate_report(user_id, report_config)