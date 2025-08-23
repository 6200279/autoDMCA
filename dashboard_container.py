from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, extract
from datetime import datetime, timedelta

from app.db.session import get_db
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

router = APIRouter()


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
    # Total profiles
    total_profiles = db.query(func.count(ProtectedProfile.id))\
        .filter(ProtectedProfile.user_id == user.id).scalar()
    
    # Active infringements
    active_infringements = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.status.in_(["pending", "confirmed"])
            )
        ).scalar()
    
    # Pending takedowns
    pending_takedowns = db.query(func.count(TakedownRequest.id))\
        .filter(
            and_(
                TakedownRequest.user_id == user.id,
                TakedownRequest.status.in_(["sent", "acknowledged", "compliance_review"])
            )
        ).scalar()
    
    # Resolved this month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resolved_this_month = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.status == "resolved",
                Infringement.updated_at >= start_of_month
            )
        ).scalar()
    
    # Calculate protection score (0-100)
    total_infringements = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == user.id).scalar()
    
    resolved_infringements = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.status == "resolved"
            )
        ).scalar()
    
    protection_score = 100.0
    if total_infringements > 0:
        protection_score = (resolved_infringements / total_infringements) * 100
    
    # Scan success rate (placeholder)
    scan_success_rate = 95.0
    
    # Takedown success rate
    total_takedowns = db.query(func.count(TakedownRequest.id))\
        .filter(TakedownRequest.user_id == user.id).scalar()
    
    successful_takedowns = db.query(func.count(TakedownRequest.id))\
        .filter(
            and_(
                TakedownRequest.user_id == user.id,
                TakedownRequest.status == "content_removed"
            )
        ).scalar()
    
    takedown_success_rate = 0.0
    if total_takedowns > 0:
        takedown_success_rate = (successful_takedowns / total_takedowns) * 100
    
    # Last scan (placeholder)
    last_scan = None  # This would come from scan_results table
    
    return DashboardStats(
        total_profiles=total_profiles,
        active_infringements=active_infringements,
        pending_takedowns=pending_takedowns,
        resolved_this_month=resolved_this_month,
        protection_score=protection_score,
        scan_success_rate=scan_success_rate,
        takedown_success_rate=takedown_success_rate,
        last_scan=last_scan
    )


async def get_infringement_trend_data(user: User, db: Session, period: str, days: int) -> InfringementTrend:
    """Get infringement trend data."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query infringements by date
    if period == "daily":
        data = db.query(
            func.date(Infringement.discovered_at).label('date'),
            func.count(Infringement.id).label('count')
        ).join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.discovered_at >= start_date
            )
        ).group_by(func.date(Infringement.discovered_at)).all()
    elif period == "weekly":
        data = db.query(
            func.date_trunc('week', Infringement.discovered_at).label('date'),
            func.count(Infringement.id).label('count')
        ).join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.discovered_at >= start_date
            )
        ).group_by(func.date_trunc('week', Infringement.discovered_at)).all()
    else:  # monthly
        data = db.query(
            func.date_trunc('month', Infringement.discovered_at).label('date'),
            func.count(Infringement.id).label('count')
        ).join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.discovered_at >= start_date
            )
        ).group_by(func.date_trunc('month', Infringement.discovered_at)).all()
    
    # Convert to time series data
    time_series = [TimeSeriesData(date=row.date, value=row.count) for row in data]
    
    # Calculate total change
    total_change = sum(point.value for point in time_series)
    
    # Calculate percentage change (placeholder logic)
    percentage_change = 0.0
    if len(time_series) > 1:
        first_half = sum(point.value for point in time_series[:len(time_series)//2])
        second_half = sum(point.value for point in time_series[len(time_series)//2:])
        if first_half > 0:
            percentage_change = ((second_half - first_half) / first_half) * 100
    
    return InfringementTrend(
        period=period,
        data=time_series,
        total_change=total_change,
        percentage_change=percentage_change
    )


async def get_platform_distribution_data(user: User, db: Session, days: int = 30) -> List[PlatformDistribution]:
    """Get platform distribution data."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get platform counts
    platform_counts = db.query(
        Infringement.platform,
        func.count(Infringement.id).label('count')
    ).join(ProtectedProfile)\
    .filter(
        and_(
            ProtectedProfile.user_id == user.id,
            Infringement.discovered_at >= start_date
        )
    ).group_by(Infringement.platform).all()
    
    total_count = sum(count for _, count in platform_counts)
    
    distributions = []
    for platform, count in platform_counts:
        percentage = (count / total_count * 100) if total_count > 0 else 0
        
        # Simple trend calculation (placeholder)
        trend = "stable"
        if percentage > 30:
            trend = "up"
        elif percentage < 10:
            trend = "down"
        
        distributions.append(PlatformDistribution(
            platform=platform,
            count=count,
            percentage=percentage,
            trend=trend
        ))
    
    return sorted(distributions, key=lambda x: x.count, reverse=True)


async def get_recent_activity_data(user: User, db: Session, limit: int = 20) -> List[RecentActivity]:
    """Get recent activity data."""
    activities = []
    
    # Get recent infringements
    recent_infringements = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == user.id)\
        .order_by(desc(Infringement.discovered_at))\
        .limit(limit//2).all()
    
    for infringement in recent_infringements:
        activities.append(RecentActivity(
            id=infringement.id,
            type="infringement_found",
            title="New infringement detected",
            description=f"Found on {infringement.platform}: {infringement.url[:50]}...",
            platform=infringement.platform,
            profile_name=infringement.profile.name,
            timestamp=infringement.discovered_at,
            severity=infringement.severity
        ))
    
    # Get recent takedowns
    recent_takedowns = db.query(TakedownRequest)\
        .filter(TakedownRequest.user_id == user.id)\
        .order_by(desc(TakedownRequest.created_at))\
        .limit(limit//2).all()
    
    for takedown in recent_takedowns:
        if takedown.status == "content_removed":
            activities.append(RecentActivity(
                id=takedown.id,
                type="content_removed",
                title="Content successfully removed",
                description=f"Takedown successful via {takedown.method}",
                platform=takedown.infringement.platform if takedown.infringement else "",
                profile_name="",
                timestamp=takedown.resolved_at or takedown.created_at,
                severity="high"
            ))
        elif takedown.sent_at:
            activities.append(RecentActivity(
                id=takedown.id,
                type="takedown_sent",
                title="Takedown notice sent",
                description=f"Notice sent to {takedown.recipient_email}",
                platform=takedown.infringement.platform if takedown.infringement else "",
                profile_name="",
                timestamp=takedown.sent_at,
                severity="medium"
            ))
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
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
    # Profiles monitored
    profiles_monitored = db.query(func.count(ProtectedProfile.id))\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                ProtectedProfile.is_active == True
            )
        ).scalar()
    
    # Content pieces protected (placeholder)
    content_pieces_protected = profiles_monitored * 10  # Rough estimate
    
    # Platforms monitored (unique platforms from infringements)
    platforms_monitored = db.query(func.count(func.distinct(Infringement.platform)))\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == user.id).scalar()
    
    # Average detection/removal times (placeholder)
    average_detection_time = 2.5  # hours
    average_removal_time = 48.0  # hours
    
    # Proactive vs reactive removals (placeholder)
    total_removed = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.status == "resolved"
            )
        ).scalar()
    
    proactive_removals = int(total_removed * 0.7)  # 70% proactive
    reactive_removals = total_removed - proactive_removals
    
    return ProtectionMetrics(
        profiles_monitored=profiles_monitored,
        content_pieces_protected=content_pieces_protected,
        platforms_monitored=platforms_monitored,
        average_detection_time=average_detection_time,
        average_removal_time=average_removal_time,
        proactive_removals=proactive_removals,
        reactive_removals=reactive_removals
    )


async def get_quick_actions_data(user: User, db: Session) -> List[QuickAction]:
    """Get quick actions data."""
    # Get pending counts for action buttons
    pending_infringements = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(
            and_(
                ProtectedProfile.user_id == user.id,
                Infringement.status == "pending"
            )
        ).scalar()
    
    draft_takedowns = db.query(func.count(TakedownRequest.id))\
        .filter(
            and_(
                TakedownRequest.user_id == user.id,
                TakedownRequest.status == "draft"
            )
        ).scalar()
    
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
            count=pending_infringements,
            enabled=pending_infringements > 0
        ),
        QuickAction(
            action="send_takedowns",
            label="Send Takedowns",
            icon="send",
            url="/api/v1/takedowns?status=draft",
            count=draft_takedowns,
            enabled=draft_takedowns > 0
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


async def generate_user_report(user_id: int, report_config: dict):
    """Generate user report (background task)."""
    from app.services.reporting.report_generator import generate_report
    await generate_report(user_id, report_config)