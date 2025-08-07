"""
Pydantic schemas for social media monitoring API.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.db.models.social_media import SocialMediaPlatform, MonitoringStatus, ReportStatus


# Request Models

class MonitoringJobRequest(BaseModel):
    """Request model for starting monitoring job."""
    profile_id: int = Field(..., description="ID of the protected profile")
    platforms: List[SocialMediaPlatform] = Field(..., description="Platforms to monitor")
    monitoring_type: str = Field("comprehensive", description="Type of monitoring to perform")
    
    @validator('monitoring_type')
    def validate_monitoring_type(cls, v):
        valid_types = ["username", "face_recognition", "content_theft", "comprehensive"]
        if v not in valid_types:
            raise ValueError(f"monitoring_type must be one of: {valid_types}")
        return v


class ScheduleTaskRequest(BaseModel):
    """Request model for scheduling monitoring tasks."""
    profile_id: int = Field(..., description="ID of the protected profile")
    platforms: List[SocialMediaPlatform] = Field(..., description="Platforms to monitor")
    schedule_type: str = Field(..., description="Schedule type: hourly, daily, weekly, one_time")
    priority: str = Field("medium", description="Task priority: low, medium, high, urgent")
    custom_schedule: Optional[str] = Field(None, description="Custom cron expression")
    run_at: Optional[datetime] = Field(None, description="Specific time to run (for one_time)")
    
    @validator('schedule_type')
    def validate_schedule_type(cls, v):
        valid_types = ["hourly", "daily", "weekly", "one_time"]
        if v not in valid_types:
            raise ValueError(f"schedule_type must be one of: {valid_types}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ["low", "medium", "high", "urgent"]
        if v not in valid_priorities:
            raise ValueError(f"priority must be one of: {valid_priorities}")
        return v


class EmergencyMonitoringRequest(BaseModel):
    """Request model for emergency monitoring."""
    profile_id: int = Field(..., description="ID of the protected profile")
    platforms: List[SocialMediaPlatform] = Field(..., description="Platforms to monitor")
    reason: str = Field(..., description="Reason for emergency monitoring")


# Response Models

class MonitoringJobResponse(BaseModel):
    """Response model for monitoring job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    profile_id: int = Field(..., description="Profile ID being monitored")
    platforms: List[str] = Field(..., description="Platforms being monitored")
    monitoring_type: str = Field(..., description="Type of monitoring")
    created_at: datetime = Field(..., description="Job creation timestamp")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")


class ScheduleTaskResponse(BaseModel):
    """Response model for scheduled task creation."""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Current task status")
    profile_id: int = Field(..., description="Profile ID being monitored")
    platforms: List[str] = Field(..., description="Platforms being monitored")
    schedule_type: str = Field(..., description="Schedule type")
    next_run: Optional[str] = Field(None, description="Next scheduled run time")
    created_at: datetime = Field(..., description="Task creation timestamp")


class SocialMediaAccountResponse(BaseModel):
    """Response model for social media account data."""
    username: str = Field(..., description="Account username")
    user_id: Optional[str] = Field(None, description="Platform-specific user ID")
    display_name: Optional[str] = Field(None, description="Display name")
    bio: Optional[str] = Field(None, description="Account bio")
    follower_count: Optional[int] = Field(None, description="Number of followers")
    following_count: Optional[int] = Field(None, description="Number of accounts following")
    post_count: Optional[int] = Field(None, description="Number of posts")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    is_verified: bool = Field(False, description="Verification status")
    is_private: bool = Field(False, description="Privacy status")
    url: Optional[str] = Field(None, description="Profile URL")
    platform: str = Field(..., description="Social media platform")


class ImpersonationDetectionResponse(BaseModel):
    """Response model for impersonation detection results."""
    fake_username: str = Field(..., description="Impersonating username")
    fake_url: str = Field(..., description="Impersonating profile URL")
    original_username: str = Field(..., description="Original username")
    original_url: str = Field(..., description="Original profile URL")
    platform: str = Field(..., description="Platform where impersonation was found")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    confidence_score: float = Field(..., description="Confidence in detection (0-1)")
    impersonation_type: str = Field(..., description="Type of impersonation detected")
    detection_method: str = Field(..., description="Method used for detection")
    detected_at: datetime = Field(..., description="Detection timestamp")
    evidence_urls: List[str] = Field(default_factory=list, description="URLs of evidence")


class FakeAccountDetectionResponse(BaseModel):
    """Response model for fake account detection results."""
    username: str = Field(..., description="Account username")
    platform: str = Field(..., description="Social media platform")
    fake_score: float = Field(..., description="Fake account probability (0-1)")
    risk_category: str = Field(..., description="Risk category")
    confidence_level: str = Field(..., description="Confidence in assessment")
    reasons: List[str] = Field(..., description="Reasons for fake account assessment")
    features_analyzed: List[Dict[str, Any]] = Field(default_factory=list, description="Analyzed features")


class ReportSubmissionResponse(BaseModel):
    """Response model for report submissions."""
    report_id: str = Field(..., description="Unique report identifier")
    platform: str = Field(..., description="Platform where report was submitted")
    status: str = Field(..., description="Report status")
    target_username: str = Field(..., description="Reported username")
    target_url: str = Field(..., description="Reported profile URL")
    report_type: str = Field(..., description="Type of report")
    platform_report_id: Optional[str] = Field(None, description="Platform-assigned report ID")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    estimated_review_time: Optional[str] = Field(None, description="Estimated review time")


class MonitoringSessionResponse(BaseModel):
    """Response model for monitoring session details."""
    session_id: str = Field(..., description="Unique session identifier")
    profile_id: int = Field(..., description="Profile ID")
    platforms: List[str] = Field(..., description="Monitored platforms")
    session_type: str = Field(..., description="Type of monitoring session")
    status: str = Field(..., description="Session status")
    started_at: datetime = Field(..., description="Session start time")
    completed_at: Optional[datetime] = Field(None, description="Session completion time")
    duration_seconds: Optional[int] = Field(None, description="Session duration")
    results_summary: Dict[str, Any] = Field(default_factory=dict, description="Results summary")


class PlatformStatsResponse(BaseModel):
    """Response model for platform statistics."""
    platform: str = Field(..., description="Platform name")
    total_accounts_monitored: int = Field(..., description="Total accounts monitored")
    impersonations_found: int = Field(..., description="Impersonations detected")
    fake_accounts_detected: int = Field(..., description="Fake accounts detected")
    reports_submitted: int = Field(..., description="Reports submitted")
    success_rate: float = Field(..., description="Detection success rate")
    average_response_time: float = Field(..., description="Average API response time")
    last_monitored: Optional[datetime] = Field(None, description="Last monitoring timestamp")


class MonitoringStatisticsResponse(BaseModel):
    """Response model for overall monitoring statistics."""
    total_profiles_monitored: int = Field(..., description="Total profiles being monitored")
    total_platforms: int = Field(..., description="Number of platforms supported")
    active_monitoring_jobs: int = Field(..., description="Currently active jobs")
    completed_jobs_today: int = Field(..., description="Jobs completed today")
    impersonations_found_today: int = Field(..., description="Impersonations found today")
    reports_submitted_today: int = Field(..., description="Reports submitted today")
    platform_stats: List[PlatformStatsResponse] = Field(..., description="Per-platform statistics")
    system_health: Dict[str, Any] = Field(default_factory=dict, description="System health metrics")
    last_updated: datetime = Field(..., description="Statistics last updated")


class TaskDetailsResponse(BaseModel):
    """Response model for detailed task information."""
    task_id: str = Field(..., description="Task identifier")
    profile_id: int = Field(..., description="Profile ID")
    platforms: List[str] = Field(..., description="Monitored platforms")
    task_type: str = Field(..., description="Task type")
    priority: str = Field(..., description="Task priority")
    status: str = Field(..., description="Current status")
    enabled: bool = Field(..., description="Whether task is enabled")
    schedule_expression: Optional[str] = Field(None, description="Cron schedule expression")
    interval_minutes: Optional[int] = Field(None, description="Interval in minutes")
    next_run: Optional[datetime] = Field(None, description="Next scheduled run")
    created_at: datetime = Field(..., description="Task creation time")
    last_run: Optional[datetime] = Field(None, description="Last execution time")
    last_success: Optional[datetime] = Field(None, description="Last successful run")
    last_error: Optional[str] = Field(None, description="Last error message")
    total_runs: int = Field(..., description="Total number of runs")
    successful_runs: int = Field(..., description="Number of successful runs")
    failed_runs: int = Field(..., description="Number of failed runs")
    retry_count: int = Field(..., description="Current retry count")
    max_retries: int = Field(..., description="Maximum retry attempts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ComprehensiveReportResponse(BaseModel):
    """Response model for comprehensive monitoring reports."""
    profile_id: int = Field(..., description="Profile ID")
    report_period: Dict[str, str] = Field(..., description="Report date range")
    summary: Dict[str, Any] = Field(..., description="Overall summary statistics")
    platform_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="Per-platform breakdown")
    infringement_analysis: Dict[str, Any] = Field(default_factory=dict, description="Infringement analysis")
    takedown_effectiveness: Dict[str, Any] = Field(default_factory=dict, description="Takedown effectiveness metrics")
    recommendations: List[str] = Field(..., description="Recommendations for improvement")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation timestamp")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Overall health status")
    monitoring_service: Dict[str, Any] = Field(..., description="Monitoring service health")
    scheduler: Dict[str, Any] = Field(..., description="Scheduler health")
    timestamp: datetime = Field(..., description="Health check timestamp")
    errors: List[str] = Field(default_factory=list, description="Any health check errors")


# Utility Models

class ProfileSearchRequest(BaseModel):
    """Request model for profile search."""
    query: str = Field(..., description="Search query")
    platforms: List[SocialMediaPlatform] = Field(..., description="Platforms to search")
    limit: int = Field(20, ge=1, le=100, description="Maximum results per platform")


class BulkMonitoringRequest(BaseModel):
    """Request model for bulk monitoring setup."""
    profile_ids: List[int] = Field(..., description="List of profile IDs")
    platforms: List[SocialMediaPlatform] = Field(..., description="Platforms to monitor")
    schedule_type: str = Field("daily", description="Schedule type")
    priority: str = Field("medium", description="Task priority")


class ReportStatusSyncResponse(BaseModel):
    """Response model for report status synchronization."""
    reports_checked: int = Field(..., description="Number of reports checked")
    status_updates: int = Field(..., description="Number of status updates")
    updated_reports: List[Dict[str, Any]] = Field(..., description="Details of updated reports")
    errors: List[str] = Field(default_factory=list, description="Synchronization errors")
    sync_timestamp: datetime = Field(default_factory=datetime.now, description="Sync completion timestamp")


# Configuration Models

class PlatformConfigResponse(BaseModel):
    """Response model for platform configuration."""
    platform: str = Field(..., description="Platform name")
    api_available: bool = Field(..., description="Whether API access is available")
    scraping_supported: bool = Field(..., description="Whether scraping is supported")
    rate_limits: Dict[str, int] = Field(..., description="Rate limit information")
    supported_features: List[str] = Field(..., description="Supported monitoring features")
    authentication_required: bool = Field(..., description="Whether authentication is required")


class MonitoringConfigResponse(BaseModel):
    """Response model for monitoring configuration."""
    supported_platforms: List[str] = Field(..., description="Supported platforms")
    platform_configs: List[PlatformConfigResponse] = Field(..., description="Platform-specific configurations")
    default_settings: Dict[str, Any] = Field(..., description="Default monitoring settings")
    detection_methods: List[str] = Field(..., description="Available detection methods")
    report_types: List[str] = Field(..., description="Available report types")


# Error Models

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    error: str = Field(..., description="Validation error message")
    field_errors: Dict[str, List[str]] = Field(..., description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Export all models
__all__ = [
    # Request models
    "MonitoringJobRequest",
    "ScheduleTaskRequest", 
    "EmergencyMonitoringRequest",
    "ProfileSearchRequest",
    "BulkMonitoringRequest",
    
    # Response models
    "MonitoringJobResponse",
    "ScheduleTaskResponse",
    "SocialMediaAccountResponse",
    "ImpersonationDetectionResponse",
    "FakeAccountDetectionResponse", 
    "ReportSubmissionResponse",
    "MonitoringSessionResponse",
    "PlatformStatsResponse",
    "MonitoringStatisticsResponse",
    "TaskDetailsResponse",
    "ComprehensiveReportResponse",
    "HealthCheckResponse",
    "ReportStatusSyncResponse",
    "PlatformConfigResponse",
    "MonitoringConfigResponse",
    
    # Error models
    "ErrorResponse",
    "ValidationErrorResponse"
]