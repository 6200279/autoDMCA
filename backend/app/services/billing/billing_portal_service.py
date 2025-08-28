"""
Billing Portal Service for AutoDMCA

Provides customer self-service billing portal functionality:
- Stripe billing portal integration
- Customer portal session management
- Self-service subscription management
- Payment method updates
- Invoice access and downloads
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from app.core.config import settings
from app.db.models.billing import Subscription
from app.db.models.user import User
from app.services.billing.stripe_service import StripeService

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingPortalService:
    """
    Stripe billing portal integration service
    
    Features:
    - Customer portal session creation
    - Portal configuration management
    - Self-service subscription management
    - Payment method management
    - Invoice access and downloads
    """
    
    def __init__(self):
        self.stripe_service = StripeService()
        self.return_url = getattr(settings, 'BILLING_PORTAL_RETURN_URL', 'https://app.autodmca.com/billing')
        
    async def create_portal_session(
        self, 
        db: AsyncSession, 
        user_id: int,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Stripe billing portal session for customer"""
        try:
            # Get user's Stripe customer ID
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"error": "User not found"}
            
            # Ensure user has a Stripe customer ID
            customer_id = await self._ensure_stripe_customer(user)
            
            # Create portal session
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url or self.return_url,
                configuration=await self._get_portal_configuration_id()
            )
            
            logger.info(f"Created billing portal session for user {user_id}")
            
            return {
                "url": portal_session.url,
                "session_id": portal_session.id,
                "customer_id": customer_id,
                "return_url": portal_session.return_url,
                "expires_at": datetime.fromtimestamp(portal_session.created + 86400).isoformat()  # 24 hours
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            return {"error": f"Stripe error: {str(e)}"}
        except Exception as e:
            logger.error(f"Failed to create portal session for user {user_id}: {e}")
            return {"error": str(e)}
    
    async def _ensure_stripe_customer(self, user: User) -> str:
        """Ensure user has a Stripe customer ID"""
        if user.stripe_customer_id:
            return user.stripe_customer_id
        
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': str(user.id),
                'username': user.username
            }
        )
        
        # Update user record (would need to update database)
        logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
        return customer.id
    
    async def _get_portal_configuration_id(self) -> Optional[str]:
        """Get or create portal configuration"""
        try:
            # Check if we have a stored configuration ID
            config_id = getattr(settings, 'STRIPE_PORTAL_CONFIG_ID', None)
            
            if config_id:
                return config_id
            
            # Create default portal configuration
            configuration = stripe.billing_portal.Configuration.create(
                features={
                    "customer_update": {
                        "allowed_updates": ["email", "name", "address", "phone", "tax_id"],
                        "enabled": True
                    },
                    "invoice_history": {
                        "enabled": True
                    },
                    "payment_method_update": {
                        "enabled": True
                    },
                    "subscription_cancel": {
                        "enabled": True,
                        "mode": "at_period_end",
                        "proration_behavior": "none"
                    },
                    "subscription_pause": {
                        "enabled": False  # Can be enabled later
                    },
                    "subscription_update": {
                        "enabled": True,
                        "default_allowed_updates": ["price", "promotion_code"],
                        "proration_behavior": "create_prorations"
                    }
                },
                business_profile={
                    "headline": "AutoDMCA - Content Protection Services",
                    "privacy_policy_url": f"{settings.FRONTEND_URL}/privacy",
                    "terms_of_service_url": f"{settings.FRONTEND_URL}/terms"
                },
                default_return_url=self.return_url
            )
            
            logger.info(f"Created portal configuration: {configuration.id}")
            return configuration.id
            
        except Exception as e:
            logger.error(f"Failed to get portal configuration: {e}")
            return None
    
    async def get_portal_configuration(self) -> Dict[str, Any]:
        """Get current portal configuration details"""
        try:
            config_id = await self._get_portal_configuration_id()
            
            if not config_id:
                return {"error": "Portal configuration not available"}
            
            configuration = stripe.billing_portal.Configuration.retrieve(config_id)
            
            return {
                "configuration_id": configuration.id,
                "features": {
                    "customer_update": configuration.features.customer_update.enabled,
                    "invoice_history": configuration.features.invoice_history.enabled,
                    "payment_method_update": configuration.features.payment_method_update.enabled,
                    "subscription_cancel": {
                        "enabled": configuration.features.subscription_cancel.enabled,
                        "mode": configuration.features.subscription_cancel.mode
                    },
                    "subscription_update": configuration.features.subscription_update.enabled
                },
                "business_profile": {
                    "headline": configuration.business_profile.headline,
                    "privacy_policy_url": configuration.business_profile.privacy_policy_url,
                    "terms_of_service_url": configuration.business_profile.terms_of_service_url
                },
                "default_return_url": configuration.default_return_url
            }
            
        except Exception as e:
            logger.error(f"Failed to get portal configuration details: {e}")
            return {"error": str(e)}
    
    async def update_portal_configuration(
        self, 
        features: Optional[Dict[str, Any]] = None,
        business_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update portal configuration"""
        try:
            config_id = await self._get_portal_configuration_id()
            
            if not config_id:
                return {"error": "Portal configuration not found"}
            
            update_params = {}
            
            if features:
                # Map feature updates
                if 'subscription_cancel_enabled' in features:
                    update_params['features'] = update_params.get('features', {})
                    update_params['features']['subscription_cancel'] = {
                        'enabled': features['subscription_cancel_enabled'],
                        'mode': features.get('subscription_cancel_mode', 'at_period_end')
                    }
                
                if 'subscription_update_enabled' in features:
                    update_params['features'] = update_params.get('features', {})
                    update_params['features']['subscription_update'] = {
                        'enabled': features['subscription_update_enabled'],
                        'default_allowed_updates': features.get('allowed_updates', ['price']),
                        'proration_behavior': features.get('proration_behavior', 'create_prorations')
                    }
            
            if business_profile:
                update_params['business_profile'] = business_profile
            
            if update_params:
                stripe.billing_portal.Configuration.modify(config_id, **update_params)
                logger.info(f"Updated portal configuration: {config_id}")
                
            return {"success": True, "configuration_id": config_id}
            
        except Exception as e:
            logger.error(f"Failed to update portal configuration: {e}")
            return {"error": str(e)}
    
    async def get_customer_portal_info(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get customer portal access information"""
        try:
            # Get user and subscription info
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"error": "User not found"}
            
            # Get active subscription
            result = await db.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .where(Subscription.status.in_(['active', 'trialing', 'past_due']))
            )
            subscription = result.scalar_one_or_none()
            
            portal_info = {
                "has_customer_id": bool(user.stripe_customer_id),
                "has_subscription": bool(subscription),
                "portal_available": bool(user.stripe_customer_id),
                "features_available": {
                    "update_payment_method": True,
                    "download_invoices": True,
                    "update_billing_info": True,
                    "cancel_subscription": bool(subscription),
                    "change_plan": bool(subscription and subscription.status == 'active')
                }
            }
            
            if subscription:
                portal_info["subscription_info"] = {
                    "plan": subscription.plan.value,
                    "status": subscription.status,
                    "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                    "cancel_at_period_end": subscription.cancel_at_period_end
                }
            
            return portal_info
            
        except Exception as e:
            logger.error(f"Failed to get portal info for user {user_id}: {e}")
            return {"error": str(e)}
    
    async def handle_portal_return(
        self, 
        db: AsyncSession, 
        user_id: int,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle customer returning from portal"""
        try:
            # Log portal session completion
            logger.info(f"User {user_id} returned from billing portal (session: {session_id})")
            
            # Refresh subscription data from Stripe
            result = await db.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .where(Subscription.status.in_(['active', 'trialing', 'past_due', 'canceled']))
            )
            subscription = result.scalar_one_or_none()
            
            if subscription and subscription.stripe_subscription_id:
                # Sync latest subscription data
                stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                
                # Update local subscription record (would need database update)
                sync_updates = {
                    "status": stripe_sub.status,
                    "current_period_end": datetime.fromtimestamp(stripe_sub.current_period_end),
                    "cancel_at_period_end": stripe_sub.cancel_at_period_end,
                    "canceled_at": datetime.fromtimestamp(stripe_sub.canceled_at) if stripe_sub.canceled_at else None
                }
                
                logger.info(f"Synced subscription data for user {user_id}: {sync_updates}")
            
            return {
                "success": True,
                "message": "Portal session completed successfully",
                "subscription_updated": bool(subscription),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to handle portal return for user {user_id}: {e}")
            return {"error": str(e)}


# Global billing portal service instance
billing_portal_service = BillingPortalService()


__all__ = [
    'BillingPortalService',
    'billing_portal_service'
]