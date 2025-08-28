"""
Subscription Tier Enforcement Service
Implements PRD requirements for subscription-based feature access control

PRD Requirements:
- Basic Plan ($49/month): 1 profile, 10 manual submissions/day
- Professional Plan ($99/month): 5 profiles, unlimited manual submissions
- Enforce limits based on user's active subscription
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.models.billing import Subscription, SubscriptionPlan
from app.db.models.user import User
from app.services.cache.multi_level_cache import MultiLevelCache

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Subscription tiers as defined in PRD"""
    FREE = "free"  # Limited trial/demo access
    BASIC = "basic"  # $49/month - 1 profile, 10 submissions/day
    PROFESSIONAL = "professional"  # $99/month - 5 profiles, unlimited submissions


class FeatureLimits:
    """Feature limits for each subscription tier"""
    
    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            "max_profiles": 0,  # No profiles for free tier
            "daily_manual_submissions": 0,
            "daily_scans": 1,  # Very limited for demo
            "features": ["basic_dashboard"],
            "priority_support": False,
            "social_media_monitoring": False,
            "telegram_monitoring": False,
            "api_access": False
        },
        SubscriptionTier.BASIC: {
            "max_profiles": 1,
            "daily_manual_submissions": 10,
            "daily_scans": 50,  # 50 scans per day
            "features": [
                "automated_scanning", "dmca_takedowns", "search_delisting",
                "ai_face_recognition", "dashboard", "email_support",
                "basic_social_monitoring"
            ],
            "priority_support": False,
            "social_media_monitoring": "reactive",  # Only responds to reports
            "telegram_monitoring": False,
            "api_access": False
        },
        SubscriptionTier.PROFESSIONAL: {
            "max_profiles": 5,
            "daily_manual_submissions": -1,  # Unlimited
            "daily_scans": -1,  # Unlimited
            "features": [
                "automated_scanning", "dmca_takedowns", "search_delisting",
                "ai_face_recognition", "dashboard", "priority_support",
                "advanced_social_monitoring", "telegram_monitoring",
                "custom_search_terms", "extended_reports", "api_access",
                "watermarking", "impersonation_detection"
            ],
            "priority_support": True,
            "social_media_monitoring": "proactive",  # Active monitoring
            "telegram_monitoring": True,
            "api_access": True
        }
    }


class SubscriptionTierEnforcement:
    """
    Service to enforce subscription tier limits throughout the application
    
    This service integrates with all major components to ensure users
    only access features and resources allowed by their subscription tier.
    """
    
    def __init__(self, cache: Optional[MultiLevelCache] = None):
        self.cache = cache
        self.cache_ttl = 300  # 5 minutes cache for subscription data
    
    async def get_user_subscription_tier(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Tuple[SubscriptionTier, Dict[str, Any]]:
        """Get user's current subscription tier and metadata"""
        
        # Check cache first
        cache_key = f"subscription_tier:{user_id}"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return SubscriptionTier(cached_data['tier']), cached_data['metadata']
        
        # Query active subscription
        result = await db.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(['active', 'trialing']),
                    Subscription.current_period_end > datetime.utcnow()
                )
            )
        )
        
        subscription_user = result.first()
        
        if not subscription_user:
            # No active subscription - default to free tier
            tier = SubscriptionTier.FREE
            metadata = {
                "plan": "free",
                "status": "inactive",
                "expires_at": None,
                "trial": False
            }
        else:
            subscription, user = subscription_user
            
            # Map subscription plan to tier
            if subscription.plan == SubscriptionPlan.BASIC:
                tier = SubscriptionTier.BASIC
            elif subscription.plan == SubscriptionPlan.PROFESSIONAL:
                tier = SubscriptionTier.PROFESSIONAL
            else:
                tier = SubscriptionTier.FREE
            
            metadata = {
                "plan": subscription.plan.value,
                "status": subscription.status,
                "expires_at": subscription.current_period_end.isoformat(),
                "trial": subscription.status == 'trialing',
                "subscription_id": subscription.id
            }
        
        # Cache the result
        if self.cache:
            await self.cache.set(
                cache_key, 
                {"tier": tier.value, "metadata": metadata},
                ttl=self.cache_ttl
            )
        
        return tier, metadata
    
    async def check_profile_limit(
        self, 
        db: AsyncSession, 
        user_id: int, 
        requested_profiles: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if user can create/have the requested number of profiles"""
        
        tier, metadata = await self.get_user_subscription_tier(db, user_id)
        limits = FeatureLimits.TIER_LIMITS[tier]
        max_profiles = limits["max_profiles"]
        
        # Get current profile count
        current_count_result = await db.execute(
            select(func.count()).where(
                and_(
                    # Assuming we have a protected_profiles table
                    # This would need to be imported from the actual model
                    # For now, using a placeholder query
                    text("SELECT COUNT(*) FROM protected_profiles WHERE user_id = :user_id AND status = 'active'")
                ).params(user_id=user_id)
            )
        )
        current_profiles = current_count_result.scalar() or 0
        
        allowed = (
            max_profiles == -1 or  # Unlimited
            (current_profiles + requested_profiles) <= max_profiles
        )
        
        return allowed, {
            "current_profiles": current_profiles,
            "max_profiles": max_profiles,
            "requested": requested_profiles,
            "tier": tier.value,
            "unlimited": max_profiles == -1
        }
    
    async def check_manual_submission_limit(
        self, 
        db: AsyncSession, 
        user_id: int, 
        requested_submissions: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if user can make manual submissions today"""
        
        tier, metadata = await self.get_user_subscription_tier(db, user_id)
        limits = FeatureLimits.TIER_LIMITS[tier]
        daily_limit = limits["daily_manual_submissions"]
        
        # Get today's submission count
        today = datetime.utcnow().date()
        result = await db.execute(
            select(func.count()).where(
                and_(
                    # Assuming manual submissions are tracked in a table
                    text("SELECT COUNT(*) FROM manual_submissions WHERE user_id = :user_id AND DATE(created_at) = :today")
                ).params(user_id=user_id, today=today)
            )
        )
        today_submissions = result.scalar() or 0
        
        allowed = (
            daily_limit == -1 or  # Unlimited
            (today_submissions + requested_submissions) <= daily_limit
        )
        
        return allowed, {
            "today_submissions": today_submissions,
            "daily_limit": daily_limit,
            "requested": requested_submissions,
            "tier": tier.value,
            "unlimited": daily_limit == -1,
            "resets_at": (datetime.combine(today, datetime.min.time()) + timedelta(days=1)).isoformat()
        }
    
    async def check_feature_access(
        self, 
        db: AsyncSession, 
        user_id: int, 
        feature_name: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if user has access to a specific feature"""
        
        tier, metadata = await self.get_user_subscription_tier(db, user_id)
        limits = FeatureLimits.TIER_LIMITS[tier]
        features = limits["features"]
        
        allowed = feature_name in features
        
        return allowed, {
            "feature": feature_name,
            "tier": tier.value,
            "available_features": features,
            "has_access": allowed
        }
    
    async def check_daily_scan_limit(
        self, 
        db: AsyncSession, 
        user_id: int, 
        requested_scans: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if user can perform daily scans"""
        
        tier, metadata = await self.get_user_subscription_tier(db, user_id)
        limits = FeatureLimits.TIER_LIMITS[tier]
        daily_limit = limits["daily_scans"]
        
        # Get today's scan count
        today = datetime.utcnow().date()
        result = await db.execute(
            select(func.count()).where(
                and_(
                    # Assuming scans are tracked in scan_history table
                    text("SELECT COUNT(*) FROM scan_history WHERE user_id = :user_id AND DATE(started_at) = :today")
                ).params(user_id=user_id, today=today)
            )
        )
        today_scans = result.scalar() or 0
        
        allowed = (
            daily_limit == -1 or  # Unlimited
            (today_scans + requested_scans) <= daily_limit
        )
        
        return allowed, {
            "today_scans": today_scans,
            "daily_limit": daily_limit,
            "requested": requested_scans,
            "tier": tier.value,
            "unlimited": daily_limit == -1,
            "resets_at": (datetime.combine(today, datetime.min.time()) + timedelta(days=1)).isoformat()
        }
    
    async def get_tier_comparison(self) -> Dict[str, Any]:
        """Get comparison of all subscription tiers for frontend display"""
        
        comparison = {}
        for tier in SubscriptionTier:
            limits = FeatureLimits.TIER_LIMITS[tier]
            
            comparison[tier.value] = {
                "name": tier.value.title(),
                "max_profiles": "Unlimited" if limits["max_profiles"] == -1 else limits["max_profiles"],
                "daily_submissions": "Unlimited" if limits["daily_manual_submissions"] == -1 else limits["daily_manual_submissions"],
                "daily_scans": "Unlimited" if limits["daily_scans"] == -1 else limits["daily_scans"],
                "features": limits["features"],
                "priority_support": limits["priority_support"],
                "social_monitoring": limits["social_media_monitoring"],
                "telegram_monitoring": limits["telegram_monitoring"],
                "api_access": limits["api_access"]
            }
        
        return comparison
    
    def create_enforcement_error(
        self, 
        limit_type: str, 
        current: int, 
        limit: int, 
        tier: str
    ) -> HTTPException:
        """Create a standardized HTTP exception for limit enforcement"""
        
        if limit == -1:
            # This shouldn't happen, but handle gracefully
            message = f"Unexpected limit check for unlimited tier: {tier}"
        else:
            message = f"Subscription limit exceeded: {limit_type}. Current: {current}, Limit: {limit}. Upgrade to Professional plan for higher limits."
        
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "subscription_limit_exceeded",
                "limit_type": limit_type,
                "current": current,
                "limit": limit,
                "tier": tier,
                "message": message,
                "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade"
            }
        )
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate cached subscription data for a user"""
        if self.cache:
            cache_key = f"subscription_tier:{user_id}"
            await self.cache.delete(cache_key)


# Global instance
subscription_enforcement = SubscriptionTierEnforcement()


# Dependency function for FastAPI endpoints
async def enforce_profile_limit(
    db: AsyncSession,
    user_id: int,
    requested_profiles: int = 1
) -> None:
    """FastAPI dependency to enforce profile limits"""
    allowed, info = await subscription_enforcement.check_profile_limit(
        db, user_id, requested_profiles
    )
    
    if not allowed:
        raise subscription_enforcement.create_enforcement_error(
            "max_profiles", 
            info["current_profiles"], 
            info["max_profiles"],
            info["tier"]
        )


async def enforce_manual_submission_limit(
    db: AsyncSession,
    user_id: int,
    requested_submissions: int = 1
) -> None:
    """FastAPI dependency to enforce manual submission limits"""
    allowed, info = await subscription_enforcement.check_manual_submission_limit(
        db, user_id, requested_submissions
    )
    
    if not allowed:
        raise subscription_enforcement.create_enforcement_error(
            "daily_manual_submissions",
            info["today_submissions"],
            info["daily_limit"],
            info["tier"]
        )


async def enforce_feature_access(
    db: AsyncSession,
    user_id: int,
    feature_name: str
) -> None:
    """FastAPI dependency to enforce feature access"""
    allowed, info = await subscription_enforcement.check_feature_access(
        db, user_id, feature_name
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "feature_not_available",
                "feature": feature_name,
                "tier": info["tier"],
                "message": f"Feature '{feature_name}' is not available in your {info['tier']} plan. Please upgrade.",
                "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade"
            }
        )


async def enforce_daily_scan_limit(
    db: AsyncSession,
    user_id: int,
    requested_scans: int = 1
) -> None:
    """FastAPI dependency to enforce daily scan limits"""
    allowed, info = await subscription_enforcement.check_daily_scan_limit(
        db, user_id, requested_scans
    )
    
    if not allowed:
        raise subscription_enforcement.create_enforcement_error(
            "daily_scans",
            info["today_scans"],
            info["daily_limit"],
            info["tier"]
        )


__all__ = [
    'SubscriptionTier',
    'FeatureLimits', 
    'SubscriptionTierEnforcement',
    'subscription_enforcement',
    'enforce_profile_limit',
    'enforce_manual_submission_limit',
    'enforce_feature_access',
    'enforce_daily_scan_limit'
]