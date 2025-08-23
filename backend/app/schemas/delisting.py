"""
Pydantic schemas for Search Engine Delisting API
Provides request/response models for delisting endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.models.delisting import (
    DelistingRequestStatus, SearchEngineType, DelistingRequestPriority
)

class SearchEngineEnum(str, Enum):
    """Search engine options for API"""
    GOOGLE = "google"
    BING = "bing"
    YANDEX = "yandex"
    DUCKDUCKGO = "duckduckgo"
    BAIDU = "baidu"

class DelistingRequestCreate(BaseModel):
    """Schema for creating a new delisting request"""
    url: str = Field(..., description="URL to be delisted from search engines")
    original_content_url: Optional[str] = Field(None, description="Original authorized content URL")
    reason: str = Field("Copyright infringement", description="Reason for delisting")
    evidence_url: Optional[str] = Field(None, description="URL containing evidence of ownership")
    priority: DelistingRequestPriority = Field(DelistingRequestPriority.NORMAL, description="Request priority level")
    search_engines: List[SearchEngineEnum] = Field(
        [SearchEngineEnum.GOOGLE, SearchEngineEnum.BING], 
        description="Search engines to target"
    )
    profile_id: Optional[str] = Field(None, description="Associated profile ID")
    
    @validator("url")
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @validator("search_engines")
    def validate_search_engines(cls, v):
        if len(v) == 0:
            raise ValueError("At least one search engine must be specified")
        return v

    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/infringing-content",
                "original_content_url": "https://onlyfans.com/creator/original-post",
                "reason": "Copyright infringement - unauthorized distribution",
                "evidence_url": "https://evidence.example.com/proof",
                "priority": "high",
                "search_engines": ["google", "bing"],
                "profile_id": "profile_123"
            }
        }

class DelistingRequestResponse(BaseModel):
    """Schema for delisting request response"""
    id: str = Field(..., description="Unique request identifier")
    url: str = Field(..., description="URL being delisted")
    status: DelistingRequestStatus = Field(..., description="Current request status")
    search_engines: List[str] = Field(..., description="Target search engines")
    submitted_at: datetime = Field(..., description="When request was submitted")
    updated_at: Optional[datetime] = Field(None, description="Last status update")
    engine_statuses: Optional[Dict[str, Any]] = Field(None, description="Per-engine status details")
    retry_count: int = Field(0, description="Number of retry attempts")
    message: Optional[str] = Field(None, description="Status message")

    class Config:
        schema_extra = {
            "example": {
                "id": "req_123456",
                "url": "https://example.com/infringing-content",
                "status": "submitted",
                "search_engines": ["google", "bing"],
                "submitted_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
                "engine_statuses": {
                    "google": {"status": "in_progress", "submitted_at": "2024-01-15T10:30:00Z"},
                    "bing": {"status": "submitted", "submitted_at": "2024-01-15T10:30:00Z"}
                },
                "retry_count": 0,
                "message": "Request processing"
            }
        }

class DelistingBatchCreate(BaseModel):
    """Schema for creating a batch delisting request"""
    name: Optional[str] = Field(None, description="Batch name for identification")
    description: Optional[str] = Field(None, description="Batch description")
    urls: List[str] = Field(..., description="List of URLs to be delisted")
    reason: str = Field("Copyright infringement", description="Reason for delisting")
    evidence_url: Optional[str] = Field(None, description="URL containing evidence of ownership")
    priority: DelistingRequestPriority = Field(DelistingRequestPriority.NORMAL, description="Batch priority level")
    search_engines: List[SearchEngineEnum] = Field(
        [SearchEngineEnum.GOOGLE, SearchEngineEnum.BING], 
        description="Search engines to target"
    )
    batch_size: int = Field(10, ge=1, le=50, description="Processing batch size")
    
    @validator("urls")
    def validate_urls(cls, v):
        if len(v) == 0:
            raise ValueError("At least one URL must be provided")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 URLs allowed per batch")
        
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL: {url}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "January 2024 Infringement Cleanup",
                "description": "Batch removal of unauthorized content found in January",
                "urls": [
                    "https://example1.com/content",
                    "https://example2.com/content",
                    "https://example3.com/content"
                ],
                "reason": "Copyright infringement",
                "priority": "normal",
                "search_engines": ["google", "bing"],
                "batch_size": 10
            }
        }

class DelistingBatchResponse(BaseModel):
    """Schema for batch delisting response"""
    id: str = Field(..., description="Unique batch identifier")
    name: Optional[str] = Field(None, description="Batch name")
    description: Optional[str] = Field(None, description="Batch description")
    total_requests: int = Field(..., description="Total URLs in batch")
    completed_requests: int = Field(0, description="Number of completed requests")
    failed_requests: int = Field(0, description="Number of failed requests")
    success_rate: float = Field(0.0, description="Success rate (0.0 to 1.0)")
    submitted_at: datetime = Field(..., description="When batch was submitted")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When batch completed")
    status: str = Field(..., description="Batch status")
    message: Optional[str] = Field(None, description="Status message")

    class Config:
        schema_extra = {
            "example": {
                "id": "batch_789",
                "name": "January 2024 Infringement Cleanup",
                "total_requests": 50,
                "completed_requests": 35,
                "failed_requests": 3,
                "success_rate": 0.92,
                "submitted_at": "2024-01-15T09:00:00Z",
                "started_at": "2024-01-15T09:05:00Z",
                "status": "processing",
                "message": "Batch processing in progress"
            }
        }

class DelistingStatusUpdate(BaseModel):
    """Schema for status update notifications"""
    request_id: str = Field(..., description="Request identifier")
    url: str = Field(..., description="URL being processed")
    search_engine: str = Field(..., description="Search engine")
    old_status: str = Field(..., description="Previous status")
    new_status: str = Field(..., description="New status")
    timestamp: datetime = Field(..., description="Update timestamp")
    message: Optional[str] = Field(None, description="Status message")

class DelistingStatsResponse(BaseModel):
    """Schema for delisting statistics response"""
    time_period: str = Field(..., description="Statistics time period")
    total_requests: int = Field(..., description="Total requests in period")
    successful_requests: int = Field(..., description="Successfully completed requests")
    failed_requests: int = Field(..., description="Failed requests")
    pending_requests: int = Field(..., description="Pending requests")
    success_rate: float = Field(..., description="Overall success rate")
    average_processing_time: float = Field(..., description="Average processing time in seconds")
    search_engine_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="Per-engine statistics")
    updated_at: datetime = Field(..., description="When statistics were calculated")

    class Config:
        schema_extra = {
            "example": {
                "time_period": "24h",
                "total_requests": 125,
                "successful_requests": 98,
                "failed_requests": 15,
                "pending_requests": 12,
                "success_rate": 0.867,
                "average_processing_time": 1847.5,
                "search_engine_breakdown": {
                    "google": {"total_requests": 125, "successful": 105, "success_rate": 0.84},
                    "bing": {"total_requests": 125, "successful": 98, "success_rate": 0.784}
                },
                "updated_at": "2024-01-15T15:30:00Z"
            }
        }

class DelistingVerificationResponse(BaseModel):
    """Schema for delisting verification results"""
    id: str = Field(..., description="Verification record ID")
    url: str = Field(..., description="Verified URL")
    search_engine: str = Field(..., description="Search engine")
    is_removed: bool = Field(..., description="Whether URL was successfully removed")
    verified_at: datetime = Field(..., description="Verification timestamp")
    verification_method: str = Field(..., description="Method used for verification")
    search_queries_used: List[str] = Field(..., description="Search queries used to verify")
    search_results_found: int = Field(..., description="Number of search results found")

    class Config:
        schema_extra = {
            "example": {
                "id": "verify_123",
                "url": "https://example.com/content",
                "search_engine": "google",
                "is_removed": True,
                "verified_at": "2024-01-15T16:00:00Z",
                "verification_method": "search_api",
                "search_queries_used": ["\"https://example.com/content\"", "site:example.com"],
                "search_results_found": 0
            }
        }

class DelistingAlertResponse(BaseModel):
    """Schema for delisting alert information"""
    id: str = Field(..., description="Alert ID")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    metric_name: str = Field(..., description="Metric that triggered alert")
    threshold_value: float = Field(..., description="Alert threshold")
    current_value: float = Field(..., description="Current metric value")
    triggered_at: datetime = Field(..., description="When alert was triggered")
    acknowledged_at: Optional[datetime] = Field(None, description="When alert was acknowledged")
    is_active: bool = Field(..., description="Whether alert is still active")

    class Config:
        schema_extra = {
            "example": {
                "id": "alert_456",
                "alert_type": "success_rate_low",
                "severity": "warning",
                "title": "Low Success Rate Detected",
                "message": "Delisting success rate has fallen below 80%",
                "metric_name": "success_rate",
                "threshold_value": 0.8,
                "current_value": 0.72,
                "triggered_at": "2024-01-15T14:30:00Z",
                "is_active": True
            }
        }

# Webhook payload schemas
class DelistingWebhookPayload(BaseModel):
    """Schema for delisting webhook notifications"""
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")

    class Config:
        schema_extra = {
            "example": {
                "event_type": "delisting.status_changed",
                "timestamp": "2024-01-15T10:45:00Z",
                "data": {
                    "request_id": "req_123",
                    "url": "https://example.com/content",
                    "old_status": "submitted",
                    "new_status": "removed",
                    "search_engine": "google"
                }
            }
        }

# Dashboard widget schemas
class DashboardMetrics(BaseModel):
    """Schema for dashboard metrics widget"""
    active_requests: int = Field(..., description="Currently active requests")
    success_rate_24h: float = Field(..., description="24-hour success rate")
    total_requests_today: int = Field(..., description="Total requests submitted today")
    average_processing_time: float = Field(..., description="Average processing time")
    queue_length: int = Field(..., description="Current queue length")

class RecentActivity(BaseModel):
    """Schema for recent activity widget"""
    request_id: str = Field(..., description="Request ID")
    url: str = Field(..., description="URL")
    status: str = Field(..., description="Current status")
    search_engines: List[str] = Field(..., description="Target search engines")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update")

class AlertSummary(BaseModel):
    """Schema for alert summary widget"""
    active_alerts: int = Field(..., description="Number of active alerts")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    recent_alerts: List[str] = Field(..., description="Recent alert messages")

# Bulk operation schemas
class BulkStatusUpdate(BaseModel):
    """Schema for bulk status updates"""
    request_ids: List[str] = Field(..., description="List of request IDs")
    new_status: DelistingRequestStatus = Field(..., description="New status to apply")
    reason: Optional[str] = Field(None, description="Reason for status change")

class BulkRetry(BaseModel):
    """Schema for bulk retry operations"""
    request_ids: List[str] = Field(..., description="List of failed request IDs to retry")
    priority: Optional[DelistingRequestPriority] = Field(None, description="Priority for retries")

class BulkCancel(BaseModel):
    """Schema for bulk cancellation operations"""
    request_ids: List[str] = Field(..., description="List of request IDs to cancel")
    reason: Optional[str] = Field(None, description="Reason for cancellation")