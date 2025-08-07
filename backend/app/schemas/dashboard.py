from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from .common import BaseSchema


class DashboardStats(BaseSchema):
    """Dashboard statistics schema."""
    total_profiles: int
    active_infringements: int
    pending_takedowns: int
    resolved_this_month: int
    protection_score: float
    scan_success_rate: float
    takedown_success_rate: float
    last_scan: Optional[datetime]


class TimeSeriesData(BaseModel):
    """Time series data point."""
    date: datetime
    value: int


class InfringementTrend(BaseSchema):
    """Infringement trend data."""
    period: str  # daily, weekly, monthly
    data: List[TimeSeriesData]
    total_change: int
    percentage_change: float


class PlatformDistribution(BaseSchema):
    """Platform distribution data."""
    platform: str
    count: int
    percentage: float
    trend: str  # up, down, stable


class RecentActivity(BaseSchema):
    """Recent activity item."""
    id: int
    type: str  # infringement_found, takedown_sent, content_removed
    title: str
    description: str
    platform: Optional[str]
    profile_name: Optional[str]
    timestamp: datetime
    severity: Optional[str]


class AlertSummary(BaseSchema):
    """Alert summary schema."""
    total_alerts: int
    high_priority: int
    medium_priority: int
    low_priority: int
    unread_count: int


class ProtectionMetrics(BaseSchema):
    """Protection metrics schema."""
    profiles_monitored: int
    content_pieces_protected: int
    platforms_monitored: int
    average_detection_time: float  # in hours
    average_removal_time: float  # in hours
    proactive_removals: int
    reactive_removals: int


class QuickAction(BaseSchema):
    """Quick action schema."""
    action: str
    label: str
    icon: str
    url: str
    count: Optional[int]
    enabled: bool


class DashboardOverview(BaseSchema):
    """Complete dashboard overview."""
    stats: DashboardStats
    infringement_trend: InfringementTrend
    platform_distribution: List[PlatformDistribution]
    recent_activity: List[RecentActivity]
    alerts: AlertSummary
    protection_metrics: ProtectionMetrics
    quick_actions: List[QuickAction]


class AlertPreferences(BaseModel):
    """Alert preferences schema."""
    email_alerts: bool = True
    sms_alerts: bool = False
    push_alerts: bool = True
    alert_threshold: str = "medium"  # low, medium, high
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None


class CustomWidget(BaseSchema):
    """Custom dashboard widget."""
    id: int
    user_id: int
    widget_type: str
    title: str
    configuration: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    is_visible: bool
    created_at: datetime


class WidgetCreate(BaseModel):
    """Widget creation schema."""
    widget_type: str
    title: str
    configuration: Dict[str, Any]
    position: Dict[str, int]


class WidgetUpdate(BaseModel):
    """Widget update schema."""
    title: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, int]] = None
    is_visible: Optional[bool] = None


class ReportRequest(BaseModel):
    """Report generation request."""
    report_type: str  # summary, detailed, platform_analysis
    date_range: str  # last_7_days, last_30_days, last_90_days, custom
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    profile_ids: Optional[List[int]] = None
    platforms: Optional[List[str]] = None
    include_charts: bool = True
    format: str = "pdf"  # pdf, excel, json


class ScheduledReport(BaseSchema):
    """Scheduled report schema."""
    id: int
    user_id: int
    name: str
    report_type: str
    schedule: str  # daily, weekly, monthly
    next_run: datetime
    recipients: List[str]
    configuration: Dict[str, Any]
    is_active: bool
    created_at: datetime