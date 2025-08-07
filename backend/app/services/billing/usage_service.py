import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from calendar import monthrange

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.db.models.user import User
from app.db.models.subscription import Subscription, UsageRecord, SubscriptionPlan
from app.db.models.profile import ProtectedProfile
from app.db.models.takedown import TakedownRequest

logger = logging.getLogger(__name__)


class UsageService:
    """Service for tracking and enforcing usage limits."""
    
    async def get_current_usage(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:
        """Get current usage metrics for a user."""
        try:
            now = datetime.now(timezone.utc)
            
            # Get current month period
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            _, days_in_month = monthrange(now.year, now.month)
            month_end = month_start.replace(day=days_in_month, hour=23, minute=59, second=59)
            
            # Count protected profiles
            protected_profiles_result = await db.execute(
                select(func.count(ProtectedProfile.id))
                .where(
                    and_(
                        ProtectedProfile.user_id == user_id,
                        ProtectedProfile.is_active == True
                    )
                )
            )
            protected_profiles_count = protected_profiles_result.scalar() or 0
            
            # Count monthly scans (from usage records)
            monthly_scans_result = await db.execute(
                select(func.coalesce(func.sum(UsageRecord.quantity), 0))
                .where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.metric == "monthly_scans",
                        UsageRecord.period_start >= month_start,
                        UsageRecord.period_end <= month_end
                    )
                )
            )
            monthly_scans_count = monthly_scans_result.scalar() or 0
            
            # Count monthly takedown requests
            takedown_requests_result = await db.execute(
                select(func.count(TakedownRequest.id))
                .where(
                    and_(
                        TakedownRequest.user_id == user_id,
                        TakedownRequest.created_at >= month_start,
                        TakedownRequest.created_at <= month_end
                    )
                )
            )
            takedown_requests_count = takedown_requests_result.scalar() or 0
            
            return {
                "protected_profiles": protected_profiles_count,
                "monthly_scans": monthly_scans_count,
                "takedown_requests": takedown_requests_count,
                "period_start": month_start.isoformat(),
                "period_end": month_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get current usage for user {user_id}: {str(e)}")
            raise
    
    async def check_usage_limits(
        self,
        db: AsyncSession,
        user_id: int,
        metric: str,
        quantity: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """Check if user can perform an action based on usage limits."""
        try:
            # Get user's subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False, "No active subscription found"
            
            # Get current usage
            current_usage = await self.get_current_usage(db, user_id)
            
            # Check limits based on metric
            if metric == "protected_profiles":
                current_count = current_usage["protected_profiles"]
                limit = subscription.max_protected_profiles
                
                if current_count + quantity > limit:
                    return False, f"Protected profiles limit exceeded. Current: {current_count}, Limit: {limit}"
            
            elif metric == "monthly_scans":
                current_count = current_usage["monthly_scans"]
                limit = subscription.max_monthly_scans
                
                if current_count + quantity > limit:
                    return False, f"Monthly scans limit exceeded. Current: {current_count}, Limit: {limit}"
            
            elif metric == "takedown_requests":
                current_count = current_usage["takedown_requests"]
                limit = subscription.max_takedown_requests
                
                if current_count + quantity > limit:
                    return False, f"Takedown requests limit exceeded. Current: {current_count}, Limit: {limit}"
            
            else:
                return False, f"Unknown metric: {metric}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to check usage limits for user {user_id}: {str(e)}")
            return False, "Error checking usage limits"
    
    async def record_usage(
        self,
        db: AsyncSession,
        user_id: int,
        metric: str,
        quantity: int = 1,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> UsageRecord:
        """Record usage for a metric."""
        try:
            # Get user's subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                raise ValueError("No subscription found for user")
            
            # Set default period (current month)
            if not period_start or not period_end:
                now = datetime.now(timezone.utc)
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                _, days_in_month = monthrange(now.year, now.month)
                period_end = period_start.replace(day=days_in_month, hour=23, minute=59, second=59)
            
            # Check if usage record already exists for this period
            existing_result = await db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.subscription_id == subscription.id,
                        UsageRecord.metric == metric,
                        UsageRecord.period_start == period_start,
                        UsageRecord.period_end == period_end
                    )
                )
            )
            existing_record = existing_result.scalar_one_or_none()
            
            if existing_record:
                # Update existing record
                existing_record.quantity += quantity
                usage_record = existing_record
            else:
                # Create new record
                usage_record = UsageRecord(
                    subscription_id=subscription.id,
                    user_id=user_id,
                    metric=metric,
                    quantity=quantity,
                    period_start=period_start,
                    period_end=period_end
                )
                db.add(usage_record)
            
            await db.commit()
            await db.refresh(usage_record)
            
            logger.info(f"Recorded usage: {metric}={quantity} for user {user_id}")
            return usage_record
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to record usage for user {user_id}: {str(e)}")
            raise
    
    async def get_usage_history(
        self,
        db: AsyncSession,
        user_id: int,
        metric: Optional[str] = None,
        limit: int = 12
    ) -> list[UsageRecord]:
        """Get usage history for a user."""
        try:
            query = select(UsageRecord).where(UsageRecord.user_id == user_id)
            
            if metric:
                query = query.where(UsageRecord.metric == metric)
            
            query = query.order_by(UsageRecord.period_start.desc()).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get usage history for user {user_id}: {str(e)}")
            raise
    
    async def get_subscription_limits(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:
        """Get subscription limits for a user."""
        try:
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                # Return free plan limits
                return {
                    "max_protected_profiles": 0,
                    "max_monthly_scans": 0,
                    "max_takedown_requests": 0
                }
            
            return {
                "max_protected_profiles": subscription.max_protected_profiles,
                "max_monthly_scans": subscription.max_monthly_scans,
                "max_takedown_requests": subscription.max_takedown_requests
            }
            
        except Exception as e:
            logger.error(f"Failed to get subscription limits for user {user_id}: {str(e)}")
            raise
    
    async def check_feature_access(
        self,
        db: AsyncSession,
        user_id: int,
        feature: str
    ) -> bool:
        """Check if user has access to a specific feature."""
        try:
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return False
            
            # Check feature access
            if feature == "ai_face_recognition":
                return subscription.ai_face_recognition
            elif feature == "priority_support":
                return subscription.priority_support
            elif feature == "custom_branding":
                return subscription.custom_branding
            elif feature == "api_access":
                return subscription.api_access
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to check feature access for user {user_id}: {str(e)}")
            return False
    
    async def get_usage_analytics(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, any]:
        """Get usage analytics for the past N days."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get usage records for the period
            result = await db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.period_start >= start_date
                    )
                ).order_by(UsageRecord.period_start.asc())
            )
            usage_records = result.scalars().all()
            
            # Aggregate usage by metric and period
            analytics = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                },
                "metrics": {},
                "trends": {},
                "total_usage": {}
            }
            
            # Group by metric
            for record in usage_records:
                metric = record.metric
                if metric not in analytics["metrics"]:
                    analytics["metrics"][metric] = []
                
                analytics["metrics"][metric].append({
                    "period_start": record.period_start.isoformat(),
                    "period_end": record.period_end.isoformat(),
                    "quantity": record.quantity
                })
            
            # Calculate totals and trends
            for metric, records in analytics["metrics"].items():
                total = sum(r["quantity"] for r in records)
                analytics["total_usage"][metric] = total
                
                # Simple trend calculation (comparing first half vs second half)
                if len(records) >= 2:
                    mid_point = len(records) // 2
                    first_half = sum(r["quantity"] for r in records[:mid_point])
                    second_half = sum(r["quantity"] for r in records[mid_point:])
                    
                    if first_half > 0:
                        trend = ((second_half - first_half) / first_half) * 100
                    else:
                        trend = 100 if second_half > 0 else 0
                    
                    analytics["trends"][metric] = {
                        "percentage_change": round(trend, 2),
                        "direction": "up" if trend > 0 else "down" if trend < 0 else "stable"
                    }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get usage analytics for user {user_id}: {str(e)}")
            raise


# Create singleton instance
usage_service = UsageService()