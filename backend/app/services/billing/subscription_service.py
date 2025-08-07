import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.models.user import User
from app.db.models.subscription import (
    Subscription, 
    SubscriptionPlan, 
    SubscriptionStatus,
    BillingInterval,
    Invoice,
    InvoiceLineItem,
    PaymentMethod,
    UsageRecord,
    BillingAddress
)
from app.services.billing.stripe_service import stripe_service, SUBSCRIPTION_PLANS
from app.services.billing.usage_service import usage_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions and billing operations."""
    
    async def create_subscription(
        self,
        db: AsyncSession,
        user: User,
        plan: SubscriptionPlan,
        interval: BillingInterval,
        payment_method_id: Optional[str] = None,
        trial_days: Optional[int] = None
    ) -> Tuple[Subscription, Dict[str, any]]:
        """Create a new subscription for a user."""
        try:
            # Get plan configuration
            plan_config = stripe_service.get_plan_config(plan, interval)
            
            # Create or get Stripe customer
            if not user.subscription or not user.subscription.stripe_customer_id:
                stripe_customer = await stripe_service.create_customer(
                    email=user.email,
                    name=user.full_name,
                    metadata={"user_id": str(user.id)}
                )
                stripe_customer_id = stripe_customer.id
            else:
                stripe_customer_id = user.subscription.stripe_customer_id
            
            # Create Stripe subscription
            stripe_subscription = await stripe_service.create_subscription(
                customer_id=stripe_customer_id,
                price_id=plan_config["stripe_price_id"],
                payment_method_id=payment_method_id,
                trial_period_days=trial_days,
                metadata={
                    "user_id": str(user.id),
                    "plan": plan.value,
                    "interval": interval.value
                }
            )
            
            # Create or update local subscription
            if user.subscription:
                subscription = user.subscription
                subscription.previous_plan = subscription.plan
            else:
                subscription = Subscription(user_id=user.id)
                db.add(subscription)
            
            # Update subscription details
            subscription.plan = plan
            subscription.status = SubscriptionStatus(stripe_subscription.status)
            subscription.stripe_customer_id = stripe_customer_id
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.stripe_price_id = plan_config["stripe_price_id"]
            subscription.amount = Decimal(plan_config["price"]) / 100  # Convert cents to dollars
            subscription.currency = "USD"
            subscription.interval = interval
            
            # Set dates
            if stripe_subscription.current_period_start:
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_subscription.current_period_start, tz=timezone.utc
                )
            if stripe_subscription.current_period_end:
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_subscription.current_period_end, tz=timezone.utc
                )
            if stripe_subscription.trial_start:
                subscription.trial_start = datetime.fromtimestamp(
                    stripe_subscription.trial_start, tz=timezone.utc
                )
            if stripe_subscription.trial_end:
                subscription.trial_end = datetime.fromtimestamp(
                    stripe_subscription.trial_end, tz=timezone.utc
                )
            
            # Set limits and features
            limits = plan_config["limits"]
            features = plan_config["features"]
            
            subscription.max_protected_profiles = limits["max_protected_profiles"]
            subscription.max_monthly_scans = limits["max_monthly_scans"]
            subscription.max_takedown_requests = limits["max_takedown_requests"]
            
            subscription.ai_face_recognition = features["ai_face_recognition"]
            subscription.priority_support = features["priority_support"]
            subscription.custom_branding = features["custom_branding"]
            subscription.api_access = features["api_access"]
            
            await db.commit()
            await db.refresh(subscription)
            
            logger.info(f"Created subscription for user {user.id}: {subscription.id}")
            return subscription, stripe_subscription
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create subscription for user {user.id}: {str(e)}")
            raise
    
    async def get_subscription(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Optional[Subscription]:
        """Get user's subscription."""
        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.invoices))
            .where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_subscription_from_stripe(
        self,
        db: AsyncSession,
        stripe_subscription_data: Dict[str, any]
    ) -> Optional[Subscription]:
        """Update local subscription from Stripe data."""
        try:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_subscription_data["id"]
                )
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.warning(f"Subscription not found for Stripe ID: {stripe_subscription_data['id']}")
                return None
            
            # Update status
            subscription.status = SubscriptionStatus(stripe_subscription_data["status"])
            
            # Update dates
            if stripe_subscription_data.get("current_period_start"):
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_subscription_data["current_period_start"], tz=timezone.utc
                )
            if stripe_subscription_data.get("current_period_end"):
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_subscription_data["current_period_end"], tz=timezone.utc
                )
            if stripe_subscription_data.get("canceled_at"):
                subscription.canceled_at = datetime.fromtimestamp(
                    stripe_subscription_data["canceled_at"], tz=timezone.utc
                )
            if stripe_subscription_data.get("cancel_at_period_end") and stripe_subscription_data.get("current_period_end"):
                subscription.ends_at = datetime.fromtimestamp(
                    stripe_subscription_data["current_period_end"], tz=timezone.utc
                )
            
            await db.commit()
            await db.refresh(subscription)
            
            logger.info(f"Updated subscription from Stripe: {subscription.id}")
            return subscription
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update subscription from Stripe: {str(e)}")
            raise
    
    async def change_plan(
        self,
        db: AsyncSession,
        user_id: int,
        new_plan: SubscriptionPlan,
        new_interval: BillingInterval,
        proration_behavior: str = "always_invoice"
    ) -> Subscription:
        """Change subscription plan."""
        try:
            subscription = await self.get_subscription(db, user_id)
            if not subscription:
                raise ValueError("No active subscription found")
            
            if not subscription.stripe_subscription_id:
                raise ValueError("No Stripe subscription ID found")
            
            # Get new plan configuration
            plan_config = stripe_service.get_plan_config(new_plan, new_interval)
            
            # Update Stripe subscription
            stripe_subscription = await stripe_service.change_subscription_plan(
                subscription_id=subscription.stripe_subscription_id,
                new_price_id=plan_config["stripe_price_id"],
                proration_behavior=proration_behavior
            )
            
            # Update local subscription
            subscription.previous_plan = subscription.plan
            subscription.plan = new_plan
            subscription.interval = new_interval
            subscription.stripe_price_id = plan_config["stripe_price_id"]
            subscription.amount = Decimal(plan_config["price"]) / 100
            
            # Update limits and features
            limits = plan_config["limits"]
            features = plan_config["features"]
            
            subscription.max_protected_profiles = limits["max_protected_profiles"]
            subscription.max_monthly_scans = limits["max_monthly_scans"]
            subscription.max_takedown_requests = limits["max_takedown_requests"]
            
            subscription.ai_face_recognition = features["ai_face_recognition"]
            subscription.priority_support = features["priority_support"]
            subscription.custom_branding = features["custom_branding"]
            subscription.api_access = features["api_access"]
            
            await db.commit()
            await db.refresh(subscription)
            
            logger.info(f"Changed plan for subscription {subscription.id} to {new_plan}")
            return subscription
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to change plan for user {user_id}: {str(e)}")
            raise
    
    async def cancel_subscription(
        self,
        db: AsyncSession,
        user_id: int,
        at_period_end: bool = True
    ) -> Subscription:
        """Cancel a subscription."""
        try:
            subscription = await self.get_subscription(db, user_id)
            if not subscription:
                raise ValueError("No active subscription found")
            
            if not subscription.stripe_subscription_id:
                raise ValueError("No Stripe subscription ID found")
            
            # Cancel Stripe subscription
            stripe_subscription = await stripe_service.cancel_subscription(
                subscription_id=subscription.stripe_subscription_id,
                at_period_end=at_period_end
            )
            
            # Update local subscription
            if at_period_end:
                subscription.ends_at = subscription.current_period_end
            else:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.now(timezone.utc)
                subscription.ends_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(subscription)
            
            logger.info(f"Cancelled subscription {subscription.id}")
            return subscription
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cancel subscription for user {user_id}: {str(e)}")
            raise
    
    async def reactivate_subscription(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Subscription:
        """Reactivate a cancelled subscription."""
        try:
            subscription = await self.get_subscription(db, user_id)
            if not subscription:
                raise ValueError("No subscription found")
            
            if subscription.status != SubscriptionStatus.CANCELED:
                raise ValueError("Subscription is not cancelled")
            
            if not subscription.stripe_subscription_id:
                raise ValueError("No Stripe subscription ID found")
            
            # Reactivate in Stripe by removing the cancellation
            stripe_subscription = await stripe_service.update_subscription(
                subscription_id=subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            
            # Update local subscription
            subscription.status = SubscriptionStatus(stripe_subscription.status)
            subscription.canceled_at = None
            subscription.ends_at = None
            
            await db.commit()
            await db.refresh(subscription)
            
            logger.info(f"Reactivated subscription {subscription.id}")
            return subscription
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to reactivate subscription for user {user_id}: {str(e)}")
            raise
    
    async def add_payment_method(
        self,
        db: AsyncSession,
        user_id: int,
        payment_method_id: str
    ) -> PaymentMethod:
        """Add a payment method for a user."""
        try:
            subscription = await self.get_subscription(db, user_id)
            if not subscription or not subscription.stripe_customer_id:
                raise ValueError("No customer found")
            
            # Attach payment method to Stripe customer
            stripe_payment_method = await stripe_service.attach_payment_method(
                payment_method_id=payment_method_id,
                customer_id=subscription.stripe_customer_id
            )
            
            # Save payment method locally
            payment_method = PaymentMethod(
                user_id=user_id,
                stripe_payment_method_id=payment_method_id,
                type=stripe_payment_method["type"],
                is_default=False
            )
            
            # Add card details if it's a card
            if stripe_payment_method["type"] == "card":
                card = stripe_payment_method["card"]
                payment_method.card_brand = card["brand"]
                payment_method.card_last4 = card["last4"]
                payment_method.card_exp_month = card["exp_month"]
                payment_method.card_exp_year = card["exp_year"]
            
            db.add(payment_method)
            await db.commit()
            await db.refresh(payment_method)
            
            logger.info(f"Added payment method for user {user_id}")
            return payment_method
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to add payment method for user {user_id}: {str(e)}")
            raise
    
    async def remove_payment_method(
        self,
        db: AsyncSession,
        user_id: int,
        payment_method_id: int
    ) -> bool:
        """Remove a payment method."""
        try:
            result = await db.execute(
                select(PaymentMethod).where(
                    and_(
                        PaymentMethod.id == payment_method_id,
                        PaymentMethod.user_id == user_id
                    )
                )
            )
            payment_method = result.scalar_one_or_none()
            
            if not payment_method:
                raise ValueError("Payment method not found")
            
            # Detach from Stripe
            await stripe_service.detach_payment_method(
                payment_method.stripe_payment_method_id
            )
            
            # Remove from database
            await db.delete(payment_method)
            await db.commit()
            
            logger.info(f"Removed payment method {payment_method_id} for user {user_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to remove payment method {payment_method_id}: {str(e)}")
            raise
    
    async def get_billing_history(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> list[Invoice]:
        """Get billing history for a user."""
        result = await db.execute(
            select(Invoice)
            .options(selectinload(Invoice.line_items))
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.invoice_date.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_current_usage(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:
        """Get current usage for a user."""
        return await usage_service.get_current_usage(db, user_id)
    
    async def check_usage_limits(
        self,
        db: AsyncSession,
        user_id: int,
        metric: str,
        quantity: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """Check if user can perform an action based on usage limits."""
        return await usage_service.check_usage_limits(db, user_id, metric, quantity)


# Create singleton instance
subscription_service = SubscriptionService()