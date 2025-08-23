from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
import stripe
import json
import logging

from ...db.models.addon_service import (
    AddonService, 
    UserAddonSubscription, 
    AddonUsage,
    AddonServiceType, 
    AddonServiceStatus
)
from ...db.models.user import User
from ...core.config import settings

logger = logging.getLogger(__name__)

class AddonServiceManager:
    def __init__(self, db: Session):
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def get_available_addons(self) -> List[AddonService]:
        """Get all available add-on services"""
        return self.db.query(AddonService).filter(
            AddonService.is_active == True
        ).all()

    def get_user_addons(self, user_id: int) -> List[UserAddonSubscription]:
        """Get user's current add-on subscriptions"""
        return self.db.query(UserAddonSubscription).filter(
            and_(
                UserAddonSubscription.user_id == user_id,
                UserAddonSubscription.status == AddonServiceStatus.ACTIVE
            )
        ).all()

    def subscribe_to_addon(
        self, 
        user_id: int, 
        addon_service_id: int, 
        quantity: int = 1,
        payment_method_id: str = None
    ) -> Dict[str, Any]:
        """Subscribe user to an add-on service"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            addon_service = self.db.query(AddonService).filter(
                AddonService.id == addon_service_id
            ).first()
            if not addon_service:
                return {"success": False, "error": "Add-on service not found"}

            # Check if user already has this add-on
            existing = self.db.query(UserAddonSubscription).filter(
                and_(
                    UserAddonSubscription.user_id == user_id,
                    UserAddonSubscription.addon_service_id == addon_service_id,
                    UserAddonSubscription.status == AddonServiceStatus.ACTIVE
                )
            ).first()

            if existing and addon_service.service_type != AddonServiceType.EXTRA_PROFILE:
                return {"success": False, "error": "Already subscribed to this add-on"}

            # Handle different billing types
            if addon_service.is_recurring:
                return self._create_recurring_subscription(
                    user, addon_service, quantity, payment_method_id
                )
            else:
                return self._create_one_time_purchase(
                    user, addon_service, quantity, payment_method_id
                )

        except Exception as e:
            logger.error(f"Error subscribing to add-on: {str(e)}")
            return {"success": False, "error": "Failed to subscribe to add-on"}

    def _create_recurring_subscription(
        self, 
        user: User, 
        addon_service: AddonService, 
        quantity: int,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Create a recurring Stripe subscription for add-on"""
        try:
            # Get or create Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.full_name,
                    payment_method=payment_method_id
                )
                user.stripe_customer_id = customer.id
                self.db.commit()
            else:
                # Attach payment method to existing customer
                if payment_method_id:
                    stripe.PaymentMethod.attach(
                        payment_method_id,
                        customer=user.stripe_customer_id
                    )

            # Create Stripe price for this add-on if not exists
            price_id = self._get_or_create_stripe_price(addon_service)

            # Create Stripe subscription
            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{
                    'price': price_id,
                    'quantity': quantity
                }],
                default_payment_method=payment_method_id,
                expand=['latest_invoice.payment_intent']
            )

            # Create database record
            user_subscription = UserAddonSubscription(
                user_id=user.id,
                addon_service_id=addon_service.id,
                status=AddonServiceStatus.ACTIVE,
                quantity=quantity,
                stripe_subscription_id=subscription.id,
                stripe_price_id=price_id,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end)
            )
            
            self.db.add(user_subscription)
            self.db.commit()

            return {
                "success": True,
                "subscription_id": user_subscription.id,
                "stripe_subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating add-on subscription: {str(e)}")
            return {"success": False, "error": f"Payment error: {str(e)}"}

    def _create_one_time_purchase(
        self, 
        user: User, 
        addon_service: AddonService, 
        quantity: int,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Create a one-time payment for add-on"""
        try:
            # Calculate total amount
            total_amount = int((addon_service.price_one_time * quantity) * 100)  # Convert to cents

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=total_amount,
                currency='usd',
                payment_method=payment_method_id,
                customer=user.stripe_customer_id,
                confirm=True,
                return_url=f"{settings.FRONTEND_URL}/billing/addon-success"
            )

            # Create database record
            user_subscription = UserAddonSubscription(
                user_id=user.id,
                addon_service_id=addon_service.id,
                status=AddonServiceStatus.ACTIVE,
                quantity=quantity,
                stripe_payment_intent_id=payment_intent.id,
                paid_at=datetime.utcnow()
            )
            
            self.db.add(user_subscription)
            self.db.commit()

            return {
                "success": True,
                "subscription_id": user_subscription.id,
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating one-time purchase: {str(e)}")
            return {"success": False, "error": f"Payment error: {str(e)}"}

    def _get_or_create_stripe_price(self, addon_service: AddonService) -> str:
        """Get existing or create new Stripe price for add-on"""
        # For demo, we'll create a simple naming convention
        # In production, you'd want to store these price IDs in the database
        price_lookup_key = f"addon_{addon_service.service_type.value}_monthly"
        
        try:
            # Try to find existing price
            prices = stripe.Price.list(
                lookup_keys=[price_lookup_key],
                expand=['data.product']
            )
            
            if prices.data:
                return prices.data[0].id
            
            # Create new product and price
            product = stripe.Product.create(
                name=addon_service.name,
                description=addon_service.description
            )
            
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(addon_service.price_monthly * 100),  # Convert to cents
                currency='usd',
                recurring={'interval': 'month'},
                lookup_key=price_lookup_key
            )
            
            return price.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe price: {str(e)}")
            raise e

    def cancel_addon(self, user_id: int, subscription_id: int) -> Dict[str, Any]:
        """Cancel an add-on subscription"""
        try:
            subscription = self.db.query(UserAddonSubscription).filter(
                and_(
                    UserAddonSubscription.id == subscription_id,
                    UserAddonSubscription.user_id == user_id
                )
            ).first()

            if not subscription:
                return {"success": False, "error": "Subscription not found"}

            # Cancel Stripe subscription if it exists
            if subscription.stripe_subscription_id:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )

            # Update database record
            subscription.status = AddonServiceStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            self.db.commit()

            return {"success": True}

        except Exception as e:
            logger.error(f"Error canceling add-on subscription: {str(e)}")
            return {"success": False, "error": "Failed to cancel subscription"}

    def track_addon_usage(
        self, 
        user_id: int, 
        addon_subscription_id: int, 
        usage_type: str,
        usage_count: int = 1,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Track usage of an add-on service"""
        try:
            usage_record = AddonUsage(
                user_id=user_id,
                addon_subscription_id=addon_subscription_id,
                usage_type=usage_type,
                usage_count=usage_count,
                metadata=json.dumps(metadata) if metadata else None
            )
            
            self.db.add(usage_record)
            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error tracking add-on usage: {str(e)}")
            return False

    def get_user_addon_usage(
        self, 
        user_id: int, 
        addon_subscription_id: int,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AddonUsage]:
        """Get usage statistics for a user's add-on"""
        query = self.db.query(AddonUsage).filter(
            and_(
                AddonUsage.user_id == user_id,
                AddonUsage.addon_subscription_id == addon_subscription_id
            )
        )

        if start_date:
            query = query.filter(AddonUsage.usage_date >= start_date)
        if end_date:
            query = query.filter(AddonUsage.usage_date <= end_date)

        return query.order_by(AddonUsage.usage_date.desc()).all()

    def get_addon_limits(self, user_id: int, addon_type: AddonServiceType) -> Dict[str, Any]:
        """Get usage limits for a specific add-on type"""
        subscriptions = self.db.query(UserAddonSubscription).join(
            AddonService
        ).filter(
            and_(
                UserAddonSubscription.user_id == user_id,
                AddonService.service_type == addon_type,
                UserAddonSubscription.status == AddonServiceStatus.ACTIVE
            )
        ).all()

        if not subscriptions:
            return {"has_addon": False, "limit": 0, "used": 0}

        # Calculate total limits and usage
        total_limit = sum(sub.quantity * (sub.addon_service.profile_limit or 0) for sub in subscriptions)
        
        # Calculate current usage for this month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total_used = self.db.query(func.sum(AddonUsage.usage_count)).filter(
            and_(
                AddonUsage.user_id == user_id,
                AddonUsage.usage_date >= start_of_month,
                AddonUsage.addon_subscription_id.in_([sub.id for sub in subscriptions])
            )
        ).scalar() or 0

        return {
            "has_addon": True,
            "limit": total_limit,
            "used": total_used,
            "remaining": max(0, total_limit - total_used)
        }

def initialize_default_addons(db: Session):
    """Initialize default add-on services"""
    default_addons = [
        {
            "name": "Extra Profile",
            "service_type": AddonServiceType.EXTRA_PROFILE,
            "description": "Add an additional profile to monitor for piracy",
            "price_monthly": 10.0,
            "is_recurring": True,
            "profile_limit": 1,
            "features": json.dumps([
                "1 Additional Profile",
                "Same monitoring features",
                "Separate analytics"
            ])
        },
        {
            "name": "Copyright Registration Service",
            "service_type": AddonServiceType.COPYRIGHT_REGISTRATION,
            "description": "Professional copyright registration assistance",
            "price_one_time": 199.0,
            "is_recurring": False,
            "features": json.dumps([
                "Professional copyright filing",
                "Legal document preparation",
                "USPTO submission",
                "Certificate delivery"
            ])
        },
        {
            "name": "Priority Takedown Service",
            "service_type": AddonServiceType.PRIORITY_TAKEDOWN,
            "description": "24-hour priority takedown processing",
            "price_monthly": 49.0,
            "is_recurring": True,
            "takedown_limit": 100,
            "features": json.dumps([
                "24-hour processing guarantee",
                "Priority queue placement",
                "Dedicated support",
                "Success tracking"
            ])
        },
        {
            "name": "API Access",
            "service_type": AddonServiceType.API_ACCESS,
            "description": "Full API access for integrations",
            "price_monthly": 99.0,
            "is_recurring": True,
            "api_rate_limit": 10000,
            "features": json.dumps([
                "Full API access",
                "10,000 requests/month",
                "Webhook support",
                "API documentation"
            ])
        }
    ]

    for addon_data in default_addons:
        existing = db.query(AddonService).filter(
            AddonService.service_type == addon_data["service_type"]
        ).first()
        
        if not existing:
            addon = AddonService(**addon_data)
            db.add(addon)
    
    db.commit()