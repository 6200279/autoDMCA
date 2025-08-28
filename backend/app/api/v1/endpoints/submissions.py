"""
Manual Submissions API Endpoints
Handles user manual content submissions with subscription tier enforcement

PRD Requirements:
- Basic Plan: 10 manual submissions per day
- Professional Plan: Unlimited manual submissions
- Track and enforce daily limits
"""

import logging
from typing import Any, List, Optional, Dict
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, validator
from enum import Enum

from app.db.session import get_async_session
from app.db.models.user import User
from app.api.deps.auth import get_current_verified_user
from app.services.billing.subscription_tier_enforcement import (
    enforce_manual_submission_limit,
    subscription_enforcement
)
from app.services.dmca.takedown_processor import DMCATakedownProcessor
from app.services.scanning.web_crawler import WebCrawler
from app.services.notifications.alert_system import alert_system
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class ContentType(str, Enum):
    """Types of content that can be submitted"""
    IMAGE = "image"
    VIDEO = "video"  
    PROFILE = "profile"
    PAGE = "page"
    POST = "post"


class SubmissionPriority(str, Enum):
    """Priority levels for manual submissions"""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ManualSubmissionRequest(BaseModel):
    """Request model for manual content submission"""
    url: HttpUrl
    content_type: ContentType
    platform: Optional[str] = None
    description: Optional[str] = None
    priority: SubmissionPriority = SubmissionPriority.NORMAL
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format and accessibility"""
        url_str = str(v)
        
        # Basic validation
        if len(url_str) > 1000:
            raise ValueError('URL too long (max 1000 characters)')
        
        # Check for suspicious or malicious URLs
        suspicious_patterns = ['javascript:', 'data:', 'file:', 'ftp://']
        if any(pattern in url_str.lower() for pattern in suspicious_patterns):
            raise ValueError('Unsupported URL scheme')
        
        return v


class ManualSubmissionResponse(BaseModel):
    """Response model for manual submission"""
    id: str
    url: str
    content_type: str
    platform: Optional[str]
    status: str
    priority: str
    estimated_processing_time: str
    submission_count_today: int
    daily_limit: int
    unlimited: bool
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SubmissionStatsResponse(BaseModel):
    """Response model for submission statistics"""
    today_submissions: int
    daily_limit: int
    unlimited: bool
    remaining_submissions: Optional[int]
    resets_at: datetime
    tier: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@router.post("/submit", response_model=ManualSubmissionResponse)
async def submit_manual_url(
    submission: ManualSubmissionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Submit URL for manual takedown processing
    
    PRD Requirements:
    - Basic: 10 submissions per day
    - Professional: Unlimited submissions
    - Process submissions within hours
    """
    
    logger.info(f"Manual submission from user {current_user.id}: {submission.url}")
    
    # Check subscription tier limits
    allowed, info = await subscription_enforcement.check_manual_submission_limit(
        db, current_user.id, requested_submissions=1
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "daily_limit_exceeded", 
                "message": f"Daily submission limit exceeded. You have used {info['today_submissions']} of {info['daily_limit']} submissions today.",
                "today_submissions": info["today_submissions"],
                "daily_limit": info["daily_limit"], 
                "tier": info["tier"],
                "resets_at": info["resets_at"],
                "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade" if info["tier"] == "basic" else None
            }
        )
    
    try:
        # Create submission record (mock implementation)
        submission_id = f"sub_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{current_user.id}"
        
        # Estimate processing time based on priority and subscription tier
        if info["tier"] == "professional" and submission.priority in ["high", "urgent"]:
            estimated_time = "1-2 hours"
        elif info["tier"] == "professional":
            estimated_time = "2-6 hours"
        else:  # Basic tier
            estimated_time = "6-24 hours"
        
        # Schedule background processing
        background_tasks.add_task(
            process_manual_submission,
            submission_id,
            str(submission.url),
            submission.content_type.value,
            submission.platform,
            submission.description,
            submission.priority.value,
            current_user.id
        )
        
        # Send confirmation notification
        await alert_system.send_alert(
            user_id=current_user.id,
            alert_type="submission_received",
            title="Manual Submission Received",
            message=f"We've received your submission for {submission.url} and will process it within {estimated_time}.",
            metadata={
                "submission_id": submission_id,
                "url": str(submission.url),
                "estimated_processing_time": estimated_time
            }
        )
        
        logger.info(f"Manual submission {submission_id} queued for processing")
        
        return ManualSubmissionResponse(
            id=submission_id,
            url=str(submission.url),
            content_type=submission.content_type.value,
            platform=submission.platform,
            status="queued",
            priority=submission.priority.value,
            estimated_processing_time=estimated_time,
            submission_count_today=info["today_submissions"] + 1,
            daily_limit=info["daily_limit"],
            unlimited=info["unlimited"],
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to process manual submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process submission. Please try again."
        )


@router.get("/stats", response_model=SubmissionStatsResponse)
async def get_submission_stats(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get user's submission statistics and limits"""
    
    # Get current submission stats
    allowed, info = await subscription_enforcement.check_manual_submission_limit(
        db, current_user.id, requested_submissions=0
    )
    
    remaining = None
    if not info["unlimited"]:
        remaining = max(0, info["daily_limit"] - info["today_submissions"])
    
    return SubmissionStatsResponse(
        today_submissions=info["today_submissions"],
        daily_limit=info["daily_limit"],
        unlimited=info["unlimited"],
        remaining_submissions=remaining,
        resets_at=datetime.fromisoformat(info["resets_at"].replace('Z', '+00:00')),
        tier=info["tier"]
    )


@router.get("/history")
async def get_submission_history(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get user's manual submission history"""
    
    # Mock submission history
    mock_submissions = [
        {
            "id": "sub_20250101_120000_123",
            "url": "https://example.com/stolen-content",
            "content_type": "image",
            "platform": "instagram",
            "status": "completed",
            "priority": "normal",
            "dmca_sent": True,
            "content_removed": True,
            "created_at": datetime.utcnow().isoformat(),
            "processed_at": datetime.utcnow().isoformat()
        },
        {
            "id": "sub_20250101_140000_123", 
            "url": "https://example2.com/fake-profile",
            "content_type": "profile",
            "platform": "twitter",
            "status": "processing",
            "priority": "high",
            "dmca_sent": False,
            "content_removed": False,
            "created_at": datetime.utcnow().isoformat(),
            "processed_at": None
        }
    ]
    
    # Apply filters
    if status_filter:
        mock_submissions = [s for s in mock_submissions if s["status"] == status_filter]
    
    # Apply pagination
    paginated = mock_submissions[offset:offset + limit]
    
    return {
        "submissions": paginated,
        "total": len(mock_submissions),
        "limit": limit,
        "offset": offset
    }


@router.get("/limits")
async def get_tier_limits(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """Get subscription tier limits comparison"""
    
    # Get user's current tier
    tier, metadata = await subscription_enforcement.get_user_subscription_tier(
        db, current_user.id
    )
    
    # Get tier comparison
    comparison = await subscription_enforcement.get_tier_comparison()
    
    return {
        "current_tier": tier.value,
        "metadata": metadata,
        "tier_comparison": comparison,
        "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade" if tier.value != "professional" else None
    }


async def process_manual_submission(
    submission_id: str,
    url: str,
    content_type: str,
    platform: Optional[str],
    description: Optional[str],
    priority: str,
    user_id: int
) -> None:
    """
    Background task to process manual submission
    
    This would integrate with the scanning and DMCA services
    to analyze the content and initiate takedown if infringement is detected
    """
    
    logger.info(f"Processing manual submission {submission_id} for user {user_id}")
    
    try:
        # 1. Analyze the submitted URL
        # 2. Check for content matches using AI
        # 3. If infringement detected, generate DMCA notice
        # 4. Send takedown request
        # 5. Update submission status
        # 6. Notify user of results
        
        # Mock processing (simulate analysis time)
        import asyncio
        await asyncio.sleep(10)  # Simulate processing time
        
        # Mock result: infringement detected
        infringement_detected = True
        confidence_score = 85
        
        if infringement_detected:
            # Mock DMCA sending
            await asyncio.sleep(5)  # Simulate DMCA processing
            
            # Notify user of success
            async with get_async_session() as db:
                await alert_system.send_alert(
                    user_id=user_id,
                    alert_type="infringement_found",
                    title="Infringement Detected",
                    message=f"We found a match for your submitted content and have sent a DMCA takedown notice.",
                    metadata={
                        "submission_id": submission_id,
                        "url": url,
                        "confidence_score": confidence_score,
                        "dmca_sent": True
                    }
                )
        else:
            # Notify user: no infringement found
            async with get_async_session() as db:
                await alert_system.send_alert(
                    user_id=user_id,
                    alert_type="no_infringement", 
                    title="Analysis Complete",
                    message=f"We analyzed your submission but did not detect any copyright infringement.",
                    metadata={
                        "submission_id": submission_id,
                        "url": url,
                        "confidence_score": confidence_score
                    }
                )
        
        logger.info(f"Manual submission {submission_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process manual submission {submission_id}: {e}")
        
        # Notify user of failure
        try:
            async with get_async_session() as db:
                await alert_system.send_alert(
                    user_id=user_id,
                    alert_type="processing_failed",
                    title="Processing Failed", 
                    message=f"We encountered an error processing your submission. Our team has been notified.",
                    metadata={
                        "submission_id": submission_id,
                        "url": url,
                        "error": str(e)
                    }
                )
        except Exception as notify_error:
            logger.error(f"Failed to notify user of processing failure: {notify_error}")


__all__ = ['router']