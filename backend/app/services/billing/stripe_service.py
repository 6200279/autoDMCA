import stripe
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.core.config import settings
from app.db.models.subscription import (
    SubscriptionPlan, 
    SubscriptionStatus,
    BillingInterval
)
from .exceptions import StripeConfigurationError, StripeError
from .error_handler import BillingErrorHandler, handle_billing_errors

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Subscription plan configuration with pricing
SUBSCRIPTION_PLANS = {
    SubscriptionPlan.BASIC: {
        "monthly": {
            "price": 4900,  # $49.00 in cents
            "stripe_price_id": "price_basic_monthly",  # Replace with actual Stripe price ID
        },
        "yearly": {
            "price": 49000,  # $490.00 in cents (2 months free)
            "stripe_price_id": "price_basic_yearly",  # Replace with actual Stripe price ID
        },
        "limits": {
            "max_protected_profiles": 1,
            "max_monthly_scans": 1000,
            "max_takedown_requests": 50,
        },
        "features": {
            "ai_face_recognition": True,
            "priority_support": False,
            "custom_branding": False,
            "api_access": False,
        }
    },
    SubscriptionPlan.PROFESSIONAL: {
        "monthly": {
            "price": 9900,  # $99.00 in cents
            "stripe_price_id": "price_pro_monthly",  # Replace with actual Stripe price ID
        },
        "yearly": {
            "price": 99000,  # $990.00 in cents (2 months free)
            "stripe_price_id": "price_pro_yearly",  # Replace with actual Stripe price ID
        },
        "limits": {
            "max_protected_profiles": 5,
            "max_monthly_scans": 10000,
            "max_takedown_requests": 500,
        },
        "features": {
            "ai_face_recognition": True,
            "priority_support": True,
            "custom_branding": True,
            "api_access": True,
        }
    }
}


class StripeService:
    """Service for handling Stripe payment operations with comprehensive error handling."""
    
    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY is required")
        self.api_key = settings.STRIPE_SECRET_KEY
    
    async def create_customer(
        self, 
        email: str, 
        name: str, 
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
                idempotency_key=f"customer_{email}_{hash(name)}"
            )
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for {email}: {str(e)}")
            raise
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a Stripe customer."""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer
        except stripe.error.InvalidRequestError:
            logger.warning(f"Stripe customer not found: {customer_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe customer {customer_id}: {str(e)}")
            raise
    
    async def update_customer(
        self, 
        customer_id: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Update a Stripe customer."""
        try:
            customer = stripe.Customer.modify(customer_id, **kwargs)
            logger.info(f"Updated Stripe customer: {customer_id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer {customer_id}: {str(e)}")
            raise
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_period_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe subscription."""
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "payment_settings": {"save_default_payment_method": "on_subscription"},
                "expand": ["latest_invoice.payment_intent"],
                "metadata": metadata or {}
            }
            
            if payment_method_id:
                subscription_data["default_payment_method"] = payment_method_id
            
            if trial_period_days:
                subscription_data["trial_period_days"] = trial_period_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            logger.info(f"Created Stripe subscription: {subscription.id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription for customer {customer_id}: {str(e)}")
            raise
    
    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a Stripe subscription."""
        try:
            subscription = stripe.Subscription.retrieve(
                subscription_id,
                expand=["latest_invoice", "default_payment_method"]
            )
            return subscription
        except stripe.error.InvalidRequestError:
            logger.warning(f"Stripe subscription not found: {subscription_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription {subscription_id}: {str(e)}")
            raise
    
    async def update_subscription(
        self,
        subscription_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update a Stripe subscription."""
        try:
            subscription = stripe.Subscription.modify(subscription_id, **kwargs)
            logger.info(f"Updated Stripe subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {str(e)}")
            raise
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel a Stripe subscription."""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Scheduled Stripe subscription cancellation: {subscription_id}")
            else:
                subscription = stripe.Subscription.cancel(subscription_id)
                logger.info(f"Immediately cancelled Stripe subscription: {subscription_id}")
            
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {str(e)}")
            raise
    
    async def change_subscription_plan(
        self,
        subscription_id: str,
        new_price_id: str,
        proration_behavior: str = "always_invoice"
    ) -> Dict[str, Any]:
        """Change subscription plan with prorated billing."""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription["items"]["data"][0]["id"],
                    "price": new_price_id,
                }],
                proration_behavior=proration_behavior,
            )
            
            updated_subscription = stripe.Subscription.retrieve(subscription_id)
            logger.info(f"Changed plan for subscription {subscription_id} to {new_price_id}")
            return updated_subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to change plan for subscription {subscription_id}: {str(e)}")
            raise
    
    async def create_setup_intent(
        self,
        customer_id: str,
        usage: str = "off_session"
    ) -> Dict[str, Any]:
        """Create a setup intent for saving payment methods."""
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                usage=usage,
                payment_method_types=["card"]
            )
            logger.info(f"Created setup intent for customer: {customer_id}")
            return setup_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create setup intent for customer {customer_id}: {str(e)}")
            raise
    
    async def get_payment_method(self, payment_method_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a payment method."""
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            return payment_method
        except stripe.error.InvalidRequestError:
            logger.warning(f"Payment method not found: {payment_method_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment method {payment_method_id}: {str(e)}")
            raise
    
    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str
    ) -> Dict[str, Any]:
        """Attach a payment method to a customer."""
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            return payment_method
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method {payment_method_id}: {str(e)}")
            raise
    
    async def detach_payment_method(self, payment_method_id: str) -> Dict[str, Any]:
        """Detach a payment method from a customer."""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Detached payment method: {payment_method_id}")
            return payment_method
        except stripe.error.StripeError as e:
            logger.error(f"Failed to detach payment method {payment_method_id}: {str(e)}")
            raise
    
    async def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card"
    ) -> List[Dict[str, Any]]:
        """List customer payment methods."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type
            )
            return payment_methods.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods for customer {customer_id}: {str(e)}")
            raise
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a Stripe invoice."""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return invoice
        except stripe.error.InvalidRequestError:
            logger.warning(f"Invoice not found: {invoice_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve invoice {invoice_id}: {str(e)}")
            raise
    
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List customer invoices."""
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            return invoices.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list invoices for customer {customer_id}: {str(e)}")
            raise
    
    async def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool = True
    ) -> Dict[str, Any]:
        """Create a draft invoice."""
        try:
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=auto_advance
            )
            logger.info(f"Created invoice for customer: {customer_id}")
            return invoice
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create invoice for customer {customer_id}: {str(e)}")
            raise
    
    async def finalize_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Finalize a draft invoice."""
        try:
            invoice = stripe.Invoice.finalize_invoice(invoice_id)
            logger.info(f"Finalized invoice: {invoice_id}")
            return invoice
        except stripe.error.StripeError as e:
            logger.error(f"Failed to finalize invoice {invoice_id}: {str(e)}")
            raise
    
    async def pay_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Pay an invoice."""
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            logger.info(f"Paid invoice: {invoice_id}")
            return invoice
        except stripe.error.StripeError as e:
            logger.error(f"Failed to pay invoice {invoice_id}: {str(e)}")
            raise
    
    async def get_upcoming_invoice(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get the upcoming invoice for a customer."""
        try:
            invoice = stripe.Invoice.upcoming(customer=customer_id)
            return invoice
        except stripe.error.InvalidRequestError:
            logger.info(f"No upcoming invoice for customer: {customer_id}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get upcoming invoice for customer {customer_id}: {str(e)}")
            raise
    
    def get_plan_config(
        self, 
        plan: SubscriptionPlan, 
        interval: BillingInterval
    ) -> Dict[str, Any]:
        """Get subscription plan configuration."""
        if plan not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Unknown subscription plan: {plan}")
        
        plan_config = SUBSCRIPTION_PLANS[plan]
        interval_key = "yearly" if interval == BillingInterval.YEAR else "monthly"
        
        return {
            "price": plan_config[interval_key]["price"],
            "stripe_price_id": plan_config[interval_key]["stripe_price_id"],
            "limits": plan_config["limits"],
            "features": plan_config["features"]
        }
    
    def construct_webhook_event(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Construct and verify webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise


# Create singleton instance
stripe_service = StripeService()