"""
Checkout Service for AutoDMCA

Handles subscription checkout and payment processing:
- Stripe Checkout session creation
- Subscription plan selection
- Payment processing
- Trial period management
- Success/failure handling
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from app.core.config import settings
from app.db.models.billing import Subscription, SubscriptionPlan, BillingInterval
from app.db.models.user import User
from app.services.billing.stripe_service import StripeService
from app.services.billing.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutService:
    """
    Subscription checkout and payment processing service
    
    Features:
    - Stripe Checkout session creation
    - Multi-plan subscription support
    - Trial period management
    - Promotional code support
    - Success/failure webhook handling
    """
    
    def __init__(self):
        self.stripe_service = StripeService()
        self.subscription_service = SubscriptionService()
        self.success_url = f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        self.cancel_url = f"{settings.FRONTEND_URL}/billing/cancel"
        
        # Plan pricing configuration (should be in database/config)
        self.plan_prices = {
            SubscriptionPlan.BASIC: {
                BillingInterval.MONTHLY: "price_basic_monthly",  # Replace with actual Stripe Price IDs
                BillingInterval.YEARLY: "price_basic_yearly"
            },
            SubscriptionPlan.PROFESSIONAL: {
                BillingInterval.MONTHLY: "price_pro_monthly",
                BillingInterval.YEARLY: "price_pro_yearly"
            },
            SubscriptionPlan.ENTERPRISE: {
                BillingInterval.MONTHLY: "price_enterprise_monthly",
                BillingInterval.YEARLY: "price_enterprise_yearly"
            }
        }
    
    async def create_subscription_checkout(
        self,
        db: AsyncSession,
        user_id: int,
        plan: SubscriptionPlan,
        interval: BillingInterval,
        trial_days: Optional[int] = None,
        promotional_code: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Stripe Checkout session for subscription"""
        try:
            # Get user
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"error": "User not found"}
            
            # Check if user already has an active subscription
            existing_sub = await db.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .where(Subscription.status.in_(['active', 'trialing']))
            )
            
            if existing_sub.scalar_one_or_none():
                return {"error": "User already has an active subscription"}
            
            # Get Stripe price ID
            price_id = self.plan_prices.get(plan, {}).get(interval)
            if not price_id:
                return {"error": f"Price not configured for {plan.value} {interval.value}"}
            
            # Ensure user has Stripe customer
            customer_id = await self._ensure_stripe_customer(user)
            
            # Build checkout session parameters
            checkout_params = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1
                }],
                'success_url': success_url or self.success_url,
                'cancel_url': cancel_url or self.cancel_url,
                'billing_address_collection': 'required',
                'allow_promotion_codes': True,
                'metadata': {
                    'user_id': str(user_id),
                    'plan': plan.value,
                    'interval': interval.value
                },
                'subscription_data': {
                    'metadata': {
                        'user_id': str(user_id),
                        'plan': plan.value,
                        'interval': interval.value
                    }
                }
            }
            
            # Add trial period if specified
            if trial_days and trial_days > 0:
                checkout_params['subscription_data']['trial_period_days'] = trial_days
                # Free trial
                checkout_params['subscription_data']['trial_settings'] = {
                    'end_behavior': {
                        'missing_payment_method': 'cancel'
                    }
                }
            
            # Add promotional code if provided
            if promotional_code:
                # Validate promo code exists in Stripe
                try:
                    promo_codes = stripe.PromotionCode.list(code=promotional_code, active=True, limit=1)
                    if promo_codes.data:
                        checkout_params['discounts'] = [{
                            'promotion_code': promo_codes.data[0].id
                        }]
                except stripe.error.StripeError:
                    logger.warning(f"Invalid promotional code: {promotional_code}")
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(**checkout_params)
            
            logger.info(f"Created checkout session {checkout_session.id} for user {user_id}")
            
            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
                "customer_id": customer_id,
                "plan": plan.value,
                "interval": interval.value,
                "trial_days": trial_days,
                "expires_at": datetime.fromtimestamp(checkout_session.created + 86400).isoformat()  # 24 hours
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return {"error": f"Payment processing error: {str(e)}"}
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {"error": str(e)}
    
    async def handle_checkout_success(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Dict[str, Any]:
        """Handle successful checkout completion"""
        try:
            # Retrieve checkout session
            checkout_session = stripe.checkout.Session.retrieve(
                session_id,
                expand=['subscription', 'customer']
            )
            
            if checkout_session.payment_status != 'paid' and checkout_session.mode != 'subscription':
                return {"error": "Payment not completed"}
            
            user_id = int(checkout_session.metadata.get('user_id'))
            plan = SubscriptionPlan(checkout_session.metadata.get('plan'))
            interval = BillingInterval(checkout_session.metadata.get('interval'))
            
            # Create subscription record
            subscription_data = {
                'user_id': user_id,
                'plan': plan,
                'billing_interval': interval,
                'stripe_customer_id': checkout_session.customer.id,
                'stripe_subscription_id': checkout_session.subscription.id,
                'stripe_price_id': checkout_session.subscription.items.data[0].price.id,
                'status': checkout_session.subscription.status,
                'current_period_start': datetime.fromtimestamp(checkout_session.subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(checkout_session.subscription.current_period_end),
                'trial_start': datetime.fromtimestamp(checkout_session.subscription.trial_start) if checkout_session.subscription.trial_start else None,
                'trial_end': datetime.fromtimestamp(checkout_session.subscription.trial_end) if checkout_session.subscription.trial_end else None
            }
            
            # Create subscription using subscription service
            subscription = await self.subscription_service.create_subscription(db, **subscription_data)
            
            if not subscription:
                return {"error": "Failed to create subscription record"}
            
            logger.info(f"Successfully created subscription {subscription.id} for user {user_id}")
            
            return {
                "success": True,
                "subscription_id": subscription.id,
                "user_id": user_id,
                "plan": plan.value,
                "status": subscription.status,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "next_billing_date": subscription.current_period_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to handle checkout success: {e}")
            return {"error": str(e)}
    
    async def create_plan_change_checkout(
        self,
        db: AsyncSession,
        user_id: int,
        new_plan: SubscriptionPlan,
        new_interval: Optional[BillingInterval] = None
    ) -> Dict[str, Any]:
        """Create checkout for plan change with immediate payment"""
        try:
            # Get current subscription
            result = await db.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .where(Subscription.status.in_(['active', 'trialing']))
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                return {"error": "No active subscription found"}
            
            # Use current interval if not specified
            interval = new_interval or subscription.billing_interval
            
            # Get new price ID
            price_id = self.plan_prices.get(new_plan, {}).get(interval)
            if not price_id:
                return {"error": f"Price not configured for {new_plan.value} {interval.value}"}
            
            # Create checkout session for immediate plan change
            checkout_params = {
                'customer': subscription.stripe_customer_id,
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1
                }],
                'success_url': f"{settings.FRONTEND_URL}/billing/upgrade-success?session_id={{CHECKOUT_SESSION_ID}}",
                'cancel_url': f"{settings.FRONTEND_URL}/billing/cancel",
                'subscription_data': {
                    'metadata': {
                        'user_id': str(user_id),
                        'plan': new_plan.value,
                        'interval': interval.value,
                        'upgrade_from': subscription.plan.value
                    }
                },
                'metadata': {
                    'user_id': str(user_id),
                    'plan_change': 'true',
                    'old_subscription_id': str(subscription.id)
                }
            }
            
            checkout_session = stripe.checkout.Session.create(**checkout_params)
            
            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
                "current_plan": subscription.plan.value,
                "new_plan": new_plan.value,
                "billing_interval": interval.value
            }
            
        except Exception as e:
            logger.error(f"Failed to create plan change checkout: {e}")
            return {"error": str(e)}
    
    async def get_available_plans(self) -> Dict[str, Any]:
        """Get available subscription plans with pricing"""
        try:
            plans = {}
            
            for plan in SubscriptionPlan:
                plan_info = {
                    "name": plan.value.title(),
                    "description": self._get_plan_description(plan),
                    "features": self._get_plan_features(plan),
                    "pricing": {}
                }
                
                for interval in BillingInterval:
                    price_id = self.plan_prices.get(plan, {}).get(interval)
                    if price_id:
                        # In production, fetch actual price from Stripe
                        # For now, use placeholder pricing
                        plan_info["pricing"][interval.value] = {
                            "price_id": price_id,
                            "amount": self._get_placeholder_pricing(plan, interval),
                            "currency": "usd",
                            "trial_days": 7 if plan != SubscriptionPlan.ENTERPRISE else 14
                        }
                
                plans[plan.value] = plan_info
            
            return {"plans": plans}
            
        except Exception as e:
            logger.error(f"Failed to get available plans: {e}")
            return {"error": str(e)}
    
    async def _ensure_stripe_customer(self, user: User) -> str:
        """Ensure user has a Stripe customer ID"""
        if user.stripe_customer_id:
            # Verify customer exists in Stripe
            try:
                stripe.Customer.retrieve(user.stripe_customer_id)
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                logger.warning(f"Stripe customer {user.stripe_customer_id} not found, creating new one")
        
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': str(user.id),
                'username': user.username
            }
        )
        
        # Update user record (would need database update)
        logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
        return customer.id
    
    def _get_plan_description(self, plan: SubscriptionPlan) -> str:
        """Get plan description"""
        descriptions = {
            SubscriptionPlan.BASIC: "Perfect for individual creators starting their content protection journey",
            SubscriptionPlan.PROFESSIONAL: "Advanced features for professional creators and small businesses",
            SubscriptionPlan.ENTERPRISE: "Complete protection suite for large organizations and enterprises"
        }
        return descriptions.get(plan, "")
    
    def _get_plan_features(self, plan: SubscriptionPlan) -> List[str]:
        """Get plan features list"""
        features = {
            SubscriptionPlan.BASIC: [
                "5 protected profiles",
                "100 monthly scans",
                "50 DMCA takedowns/month",
                "Email support",
                "Basic watermarking"
            ],
            SubscriptionPlan.PROFESSIONAL: [
                "25 protected profiles",
                "500 monthly scans",
                "200 DMCA takedowns/month",
                "Priority support",
                "Advanced watermarking",
                "Analytics dashboard",
                "API access"
            ],
            SubscriptionPlan.ENTERPRISE: [
                "Unlimited profiles",
                "Unlimited scans",
                "Unlimited takedowns",
                "24/7 dedicated support",
                "Custom watermarking",
                "Advanced analytics",
                "Full API access",
                "Custom integrations"
            ]
        }
        return features.get(plan, [])
    
    def _get_placeholder_pricing(self, plan: SubscriptionPlan, interval: BillingInterval) -> int:
        """Get placeholder pricing (in cents)"""
        pricing = {
            SubscriptionPlan.BASIC: {
                BillingInterval.MONTHLY: 2900,  # $29.00
                BillingInterval.YEARLY: 29000   # $290.00 (save 17%)
            },
            SubscriptionPlan.PROFESSIONAL: {
                BillingInterval.MONTHLY: 7900,  # $79.00
                BillingInterval.YEARLY: 79000   # $790.00 (save 17%)
            },
            SubscriptionPlan.ENTERPRISE: {
                BillingInterval.MONTHLY: 19900, # $199.00
                BillingInterval.YEARLY: 199000  # $1990.00 (save 17%)
            }
        }
        return pricing.get(plan, {}).get(interval, 0)


# Global checkout service instance
checkout_service = CheckoutService()


__all__ = [
    'CheckoutService',
    'checkout_service'
]