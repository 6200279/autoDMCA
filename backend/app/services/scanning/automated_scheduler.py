"""
Automated Scanning Scheduler Service
Implements PRD requirement for daily automated content scans

PRD Requirements:
- "Daily scans (minimum) with options for continuous monitoring"
- "Find leaks immediately or within hours of signup"
- "Scans are performed at least daily (if not continuously in the background)"
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from dataclasses import dataclass

from app.core.config import settings
from app.core.celery_app import celery_app
from app.db.session import get_async_session
from app.db.models.user import User
from app.db.models.billing import Subscription
from app.services.scanning.orchestrator import ScanningOrchestrator
from app.services.billing.subscription_tier_enforcement import (
    SubscriptionTierEnforcement, 
    SubscriptionTier
)
from app.services.notifications.alert_system import alert_system

logger = logging.getLogger(__name__)


class ScanFrequency(str, Enum):
    """Scan frequency options"""
    CONTINUOUS = "continuous"    # Every 2-6 hours
    DAILY = "daily"             # Once per day
    WEEKLY = "weekly"           # Once per week  
    ON_DEMAND = "on_demand"     # Manual only


class ScanPriority(str, Enum):
    """Scan priority levels"""
    LOW = "low"        # Weekly scans
    NORMAL = "normal"  # Daily scans
    HIGH = "high"      # Multiple times per day
    URGENT = "urgent"  # Continuous monitoring


@dataclass
class ScanSchedule:
    """Scheduled scan configuration"""
    user_id: int
    profile_ids: List[int]
    frequency: ScanFrequency
    priority: ScanPriority
    next_scan_at: datetime
    subscription_tier: SubscriptionTier
    enabled: bool = True


class AutomatedScanScheduler:
    """
    Manages automated scanning schedules for all users
    
    Implements PRD requirements:
    - Daily automated scans for all paid users
    - Continuous monitoring for Professional tier
    - Immediate scanning for new signups
    - Respects subscription tier limits
    """
    
    def __init__(self):
        self.subscription_enforcement = SubscriptionTierEnforcement()
        self.scanning_orchestrator = ScanningOrchestrator()
        
        # Scan frequency by tier (PRD requirements)
        self.tier_frequencies = {
            SubscriptionTier.FREE: ScanFrequency.ON_DEMAND,     # No automated scans
            SubscriptionTier.BASIC: ScanFrequency.DAILY,        # Daily scans
            SubscriptionTier.PROFESSIONAL: ScanFrequency.CONTINUOUS  # Continuous monitoring
        }
        
        # Scan times configuration
        self.daily_scan_times = [
            time(2, 0),   # 2:00 AM
            time(8, 0),   # 8:00 AM  
            time(14, 0),  # 2:00 PM
            time(20, 0)   # 8:00 PM
        ]
    
    async def schedule_initial_scan_for_new_user(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Schedule immediate scan for new user signup
        PRD: "Find leaks immediately or within hours of signup"
        """
        try:
            # Get user's subscription tier
            tier, metadata = await self.subscription_enforcement.get_user_subscription_tier(
                db, user_id
            )
            
            if tier == SubscriptionTier.FREE:
                logger.info(f"Skipping initial scan for free tier user {user_id}")
                return {"scheduled": False, "reason": "free_tier"}
            
            # Schedule immediate scan (within 5 minutes)
            scan_at = datetime.utcnow() + timedelta(minutes=5)
            
            # Use Celery to schedule the task
            result = celery_app.send_task(
                'scan_user_content',
                args=[user_id],
                eta=scan_at
            )
            
            logger.info(f"Scheduled initial scan for user {user_id} at {scan_at}")
            
            # Send welcome notification
            await alert_system.send_alert(
                user_id=user_id,
                alert_type="scan_scheduled",
                title="Content Protection Activated",
                message="Your content protection is now active. We'll start scanning for your content within the next few minutes.",
                metadata={
                    "scan_id": result.id,
                    "scheduled_at": scan_at.isoformat(),
                    "type": "initial_scan"
                }
            )
            
            return {
                "scheduled": True,
                "task_id": result.id,
                "scan_at": scan_at.isoformat(),
                "tier": tier.value
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule initial scan for user {user_id}: {e}")
            return {"scheduled": False, "error": str(e)}
    
    async def get_users_for_daily_scanning(self, db: AsyncSession) -> List[ScanSchedule]:
        """Get all users who need daily scanning"""
        
        # Get all active subscribers
        result = await db.execute(
            select(User, Subscription)
            .join(Subscription, User.id == Subscription.user_id)
            .where(
                and_(
                    User.is_active == True,
                    Subscription.status.in_(['active', 'trialing']),
                    Subscription.current_period_end > datetime.utcnow()
                )
            )
        )
        
        schedules = []
        current_time = datetime.utcnow()
        
        for user, subscription in result:
            # Determine scan frequency based on subscription tier
            if subscription.plan.value == 'basic':
                frequency = ScanFrequency.DAILY
                priority = ScanPriority.NORMAL
            elif subscription.plan.value == 'professional':
                frequency = ScanFrequency.CONTINUOUS
                priority = ScanPriority.HIGH
            else:
                continue  # Skip free tier
            
            # Get user's profiles (we'll need to query the profiles table)
            # For now, using placeholder - this would need to be implemented
            # with the actual profile model
            profile_ids = [1]  # Placeholder
            
            # Calculate next scan time
            if frequency == ScanFrequency.DAILY:
                next_scan = self._get_next_daily_scan_time(current_time)
            else:  # CONTINUOUS
                next_scan = current_time + timedelta(hours=2)  # Every 2 hours
            
            schedules.append(ScanSchedule(
                user_id=user.id,
                profile_ids=profile_ids,
                frequency=frequency,
                priority=priority,
                next_scan_at=next_scan,
                subscription_tier=SubscriptionTier(subscription.plan.value)
            ))
        
        return schedules
    
    def _get_next_daily_scan_time(self, current_time: datetime) -> datetime:
        """Calculate next daily scan time"""
        current_date = current_time.date()
        
        # Find the next scan time today
        for scan_time in self.daily_scan_times:
            scan_datetime = datetime.combine(current_date, scan_time)
            if scan_datetime > current_time:
                return scan_datetime
        
        # If no more scans today, schedule for tomorrow's first scan
        tomorrow = current_date + timedelta(days=1)
        return datetime.combine(tomorrow, self.daily_scan_times[0])
    
    async def schedule_daily_scans(self) -> Dict[str, Any]:
        """Schedule all daily scans for active users"""
        
        scheduled_count = 0
        errors = []
        
        try:
            async with get_async_session() as db:
                schedules = await self.get_users_for_daily_scanning(db)
                
                for schedule in schedules:
                    try:
                        # Schedule Celery task
                        result = celery_app.send_task(
                            'scan_user_content',
                            args=[schedule.user_id],
                            kwargs={
                                'profile_ids': schedule.profile_ids,
                                'scan_type': 'daily_automated',
                                'priority': schedule.priority.value
                            },
                            eta=schedule.next_scan_at
                        )
                        
                        scheduled_count += 1
                        
                        logger.debug(
                            f"Scheduled {schedule.frequency.value} scan for user {schedule.user_id} "
                            f"at {schedule.next_scan_at}"
                        )
                        
                    except Exception as e:
                        error_msg = f"Failed to schedule scan for user {schedule.user_id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                logger.info(f"Scheduled {scheduled_count} daily scans with {len(errors)} errors")
                
                return {
                    "scheduled_count": scheduled_count,
                    "errors": errors,
                    "total_users": len(schedules)
                }
                
        except Exception as e:
            logger.error(f"Failed to schedule daily scans: {e}")
            return {
                "scheduled_count": 0,
                "errors": [str(e)],
                "total_users": 0
            }
    
    async def schedule_continuous_monitoring(self) -> Dict[str, Any]:
        """Schedule continuous monitoring for Professional tier users"""
        
        scheduled_count = 0
        errors = []
        
        try:
            async with get_async_session() as db:
                # Get Professional tier users
                result = await db.execute(
                    select(User, Subscription)
                    .join(Subscription, User.id == Subscription.user_id)
                    .where(
                        and_(
                            User.is_active == True,
                            Subscription.status.in_(['active', 'trialing']),
                            Subscription.plan == 'professional',
                            Subscription.current_period_end > datetime.utcnow()
                        )
                    )
                )
                
                professional_users = result.all()
                
                # Schedule scans every 2-6 hours for Professional users
                scan_intervals = [2, 4, 6]  # hours
                
                for user, subscription in professional_users:
                    try:
                        for i, interval in enumerate(scan_intervals):
                            scan_time = datetime.utcnow() + timedelta(hours=interval)
                            
                            result = celery_app.send_task(
                                'scan_user_content',
                                args=[user.id],
                                kwargs={
                                    'scan_type': 'continuous_monitoring',
                                    'priority': 'high'
                                },
                                eta=scan_time
                            )
                            
                            scheduled_count += 1
                        
                        logger.debug(f"Scheduled continuous monitoring for user {user.id}")
                        
                    except Exception as e:
                        error_msg = f"Failed to schedule continuous monitoring for user {user.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                logger.info(
                    f"Scheduled continuous monitoring for {len(professional_users)} users "
                    f"({scheduled_count} total tasks)"
                )
                
                return {
                    "scheduled_count": scheduled_count,
                    "errors": errors,
                    "professional_users": len(professional_users)
                }
                
        except Exception as e:
            logger.error(f"Failed to schedule continuous monitoring: {e}")
            return {
                "scheduled_count": 0,
                "errors": [str(e)],
                "professional_users": 0
            }
    
    async def get_user_scan_schedule(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get scan schedule information for a specific user"""
        
        try:
            # Get user's subscription tier
            tier, metadata = await self.subscription_enforcement.get_user_subscription_tier(
                db, user_id
            )
            
            frequency = self.tier_frequencies.get(tier, ScanFrequency.ON_DEMAND)
            
            if frequency == ScanFrequency.ON_DEMAND:
                return {
                    "frequency": frequency.value,
                    "tier": tier.value,
                    "next_scan": None,
                    "automated_scanning": False
                }
            
            # Calculate next scan time
            current_time = datetime.utcnow()
            if frequency == ScanFrequency.DAILY:
                next_scan = self._get_next_daily_scan_time(current_time)
            else:  # CONTINUOUS
                next_scan = current_time + timedelta(hours=2)
            
            return {
                "frequency": frequency.value,
                "tier": tier.value,
                "next_scan": next_scan.isoformat(),
                "automated_scanning": True,
                "scan_times_per_day": len(self.daily_scan_times) if frequency == ScanFrequency.DAILY else 12
            }
            
        except Exception as e:
            logger.error(f"Failed to get scan schedule for user {user_id}: {e}")
            return {
                "frequency": "error",
                "error": str(e)
            }


# Global instance
automated_scheduler = AutomatedScanScheduler()


# Celery task definitions
@celery_app.task(bind=True, max_retries=3)
def scan_user_content(
    self, 
    user_id: int, 
    profile_ids: Optional[List[int]] = None,
    scan_type: str = "automated",
    priority: str = "normal"
):
    """
    Celery task for scanning user content
    This task will be executed by Celery workers
    """
    
    logger.info(f"Starting {scan_type} scan for user {user_id}")
    
    try:
        # This would need to be implemented with proper async context
        # For now, this is a placeholder showing the structure
        
        # 1. Get user's active profiles
        # 2. Run content scans for each profile
        # 3. Process and store results
        # 4. Send notifications if infringements found
        
        # Placeholder implementation
        import time
        time.sleep(30)  # Simulate scan time
        
        logger.info(f"Completed {scan_type} scan for user {user_id}")
        
        return {
            "status": "completed",
            "user_id": user_id,
            "scan_type": scan_type,
            "infringements_found": 0,  # Placeholder
            "scan_duration": 30
        }
        
    except Exception as e:
        logger.error(f"Scan failed for user {user_id}: {e}")
        
        # Retry the task
        raise self.retry(countdown=60 * (self.request.retries + 1))


@celery_app.task
def schedule_all_daily_scans():
    """
    Celery task to schedule all daily scans
    Should be run by Celery Beat on a schedule
    """
    
    logger.info("Starting daily scan scheduling job")
    
    try:
        # This would need proper async context in a real implementation
        # For now, placeholder showing the structure
        result = {
            "scheduled_count": 0,
            "errors": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Daily scan scheduling completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily scan scheduling failed: {e}")
        raise


__all__ = [
    'AutomatedScanScheduler',
    'ScanFrequency',
    'ScanPriority', 
    'ScanSchedule',
    'automated_scheduler',
    'scan_user_content',
    'schedule_all_daily_scans'
]