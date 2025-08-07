import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.billing import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionCancel,
    SubscriptionResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    SetupIntentCreate,
    SetupIntentResponse,
    InvoiceResponse,
    InvoiceListResponse,
    BillingDashboard,
    PlanFeatures,
    CurrentUsage,
    UsageLimits,
    UsageAnalytics,
    UsageLimitCheck,
    WebhookEventResponse,
    BillingAddress,
    SubscriptionPlan,
    BillingInterval
)
from app.services.billing.subscription_service import subscription_service
from app.services.billing.stripe_service import stripe_service, SUBSCRIPTION_PLANS
from app.services.billing.usage_service import usage_service
from app.services.billing.webhook_service import webhook_service

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription for the current user."""
    try:
        # Check if user already has a subscription
        existing_subscription = await subscription_service.get_subscription(db, current_user.id)
        if existing_subscription and existing_subscription.status in ["active", "trialing"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription"
            )
        
        subscription, stripe_subscription = await subscription_service.create_subscription(
            db=db,
            user=current_user,
            plan=subscription_data.plan,
            interval=subscription_data.interval,
            payment_method_id=subscription_data.payment_method_id,
            trial_days=subscription_data.trial_days
        )
        
        return SubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Failed to create subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )


@router.get("/subscriptions/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's subscription."""
    try:
        subscription = await subscription_service.get_subscription(db, current_user.id)
        if not subscription:
            return None
        
        return SubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Failed to get subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription"
        )


@router.put("/subscriptions/current", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the current user's subscription."""
    try:
        subscription = await subscription_service.get_subscription(db, current_user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )
        
        if subscription_data.plan or subscription_data.interval:
            # Change plan
            new_plan = subscription_data.plan or subscription.plan
            new_interval = subscription_data.interval or subscription.interval
            
            updated_subscription = await subscription_service.change_plan(
                db=db,
                user_id=current_user.id,
                new_plan=new_plan,
                new_interval=new_interval
            )
            
            return SubscriptionResponse.from_orm(updated_subscription)
        
        return SubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Failed to update subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )


@router.post("/subscriptions/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    cancel_data: SubscriptionCancel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel the current user's subscription."""
    try:
        subscription = await subscription_service.cancel_subscription(
            db=db,
            user_id=current_user.id,
            at_period_end=cancel_data.at_period_end
        )
        
        return SubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.post("/subscriptions/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a cancelled subscription."""
    try:
        subscription = await subscription_service.reactivate_subscription(
            db=db,
            user_id=current_user.id
        )
        
        return SubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Failed to reactivate subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription"
        )


@router.get("/plans", response_model=List[PlanFeatures])
async def get_subscription_plans():
    """Get available subscription plans and features."""
    try:
        plans = []
        
        # Basic Plan
        basic_config = SUBSCRIPTION_PLANS[SubscriptionPlan.BASIC]
        plans.append(PlanFeatures(
            plan=SubscriptionPlan.BASIC,
            name="Basic Plan",
            description="Perfect for individuals getting started with content protection",
            monthly_price=basic_config["monthly"]["price"] / 100,
            yearly_price=basic_config["yearly"]["price"] / 100,
            yearly_discount=17,  # ~2 months free
            max_protected_profiles=basic_config["limits"]["max_protected_profiles"],
            max_monthly_scans=basic_config["limits"]["max_monthly_scans"],
            max_takedown_requests=basic_config["limits"]["max_takedown_requests"],
            ai_face_recognition=basic_config["features"]["ai_face_recognition"],
            priority_support=basic_config["features"]["priority_support"],
            custom_branding=basic_config["features"]["custom_branding"],
            api_access=basic_config["features"]["api_access"]
        ))
        
        # Professional Plan
        pro_config = SUBSCRIPTION_PLANS[SubscriptionPlan.PROFESSIONAL]
        plans.append(PlanFeatures(
            plan=SubscriptionPlan.PROFESSIONAL,
            name="Professional Plan",
            description="Ideal for content creators and small businesses",
            monthly_price=pro_config["monthly"]["price"] / 100,
            yearly_price=pro_config["yearly"]["price"] / 100,
            yearly_discount=17,  # ~2 months free
            max_protected_profiles=pro_config["limits"]["max_protected_profiles"],
            max_monthly_scans=pro_config["limits"]["max_monthly_scans"],
            max_takedown_requests=pro_config["limits"]["max_takedown_requests"],
            ai_face_recognition=pro_config["features"]["ai_face_recognition"],
            priority_support=pro_config["features"]["priority_support"],
            custom_branding=pro_config["features"]["custom_branding"],
            api_access=pro_config["features"]["api_access"],
            bulk_operations=True,
            advanced_analytics=True
        ))
        
        return plans
        
    except Exception as e:
        logger.error(f"Failed to get subscription plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription plans"
        )


# Payment Methods

@router.post("/payment-methods/setup-intent", response_model=SetupIntentResponse)
async def create_setup_intent(
    setup_data: SetupIntentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a setup intent for adding a payment method."""
    try:
        subscription = await subscription_service.get_subscription(db, current_user.id)
        if not subscription or not subscription.stripe_customer_id:
            # Create customer if not exists
            stripe_customer = await stripe_service.create_customer(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id)}
            )
            customer_id = stripe_customer.id
            
            # Update subscription with customer ID if exists
            if subscription:
                subscription.stripe_customer_id = customer_id
                await db.commit()
        else:
            customer_id = subscription.stripe_customer_id
        
        setup_intent = await stripe_service.create_setup_intent(
            customer_id=customer_id,
            usage=setup_data.usage
        )
        
        return SetupIntentResponse(
            client_secret=setup_intent.client_secret,
            setup_intent_id=setup_intent.id,
            customer_id=customer_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create setup intent for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create setup intent"
        )


@router.post("/payment-methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    payment_data: PaymentMethodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a payment method for the current user."""
    try:
        payment_method = await subscription_service.add_payment_method(
            db=db,
            user_id=current_user.id,
            payment_method_id=payment_data.payment_method_id
        )
        
        return PaymentMethodResponse.from_orm(payment_method)
        
    except Exception as e:
        logger.error(f"Failed to add payment method for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add payment method"
        )


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all payment methods for the current user."""
    try:
        subscription = await subscription_service.get_subscription(db, current_user.id)
        if not subscription or not subscription.stripe_customer_id:
            return []
        
        stripe_payment_methods = await stripe_service.list_payment_methods(
            customer_id=subscription.stripe_customer_id
        )
        
        # Convert to response format
        payment_methods = []
        for pm in stripe_payment_methods:
            payment_method_data = PaymentMethodResponse(
                id=0,  # Placeholder, would need to sync with local DB
                user_id=current_user.id,
                stripe_payment_method_id=pm.id,
                type=pm.type,
                is_default=False,  # Would need to check with subscription
                is_active=True,
                card_brand=pm.card.brand if pm.type == "card" else None,
                card_last4=pm.card.last4 if pm.type == "card" else None,
                card_exp_month=pm.card.exp_month if pm.type == "card" else None,
                card_exp_year=pm.card.exp_year if pm.type == "card" else None,
                created_at=datetime.now(),
                updated_at=None
            )
            payment_methods.append(payment_method_data)
        
        return payment_methods
        
    except Exception as e:
        logger.error(f"Failed to get payment methods for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment methods"
        )


@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a payment method."""
    try:
        await subscription_service.remove_payment_method(
            db=db,
            user_id=current_user.id,
            payment_method_id=payment_method_id
        )
        
        return {"message": "Payment method removed successfully"}
        
    except Exception as e:
        logger.error(f"Failed to remove payment method for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove payment method"
        )


# Invoices

@router.get("/invoices", response_model=InvoiceListResponse)
async def get_invoices(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing history for the current user."""
    try:
        invoices = await subscription_service.get_billing_history(
            db=db,
            user_id=current_user.id,
            limit=limit
        )
        
        invoice_responses = [InvoiceResponse.from_orm(invoice) for invoice in invoices]
        
        return InvoiceListResponse(
            invoices=invoice_responses,
            total_count=len(invoice_responses),
            has_more=len(invoices) == limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get invoices for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoices"
        )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific invoice by ID."""
    try:
        # Implementation would require invoice service method
        # For now, return a placeholder
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Invoice retrieval not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Failed to get invoice {invoice_id} for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoice"
        )


# Usage and Analytics

@router.get("/usage/current", response_model=CurrentUsage)
async def get_current_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current usage statistics."""
    try:
        usage = await usage_service.get_current_usage(db, current_user.id)
        return CurrentUsage(**usage)
        
    except Exception as e:
        logger.error(f"Failed to get usage for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )


@router.get("/usage/limits", response_model=UsageLimits)
async def get_usage_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get subscription limits."""
    try:
        limits = await usage_service.get_subscription_limits(db, current_user.id)
        return UsageLimits(**limits)
        
    except Exception as e:
        logger.error(f"Failed to get usage limits for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage limits"
        )


@router.get("/usage/check/{metric}", response_model=UsageLimitCheck)
async def check_usage_limit(
    metric: str,
    quantity: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if user can perform an action based on usage limits."""
    try:
        allowed, reason = await usage_service.check_usage_limits(
            db, current_user.id, metric, quantity
        )
        
        current_usage = await usage_service.get_current_usage(db, current_user.id)
        limits = await usage_service.get_subscription_limits(db, current_user.id)
        
        metric_mapping = {
            "protected_profiles": ("protected_profiles", "max_protected_profiles"),
            "monthly_scans": ("monthly_scans", "max_monthly_scans"),
            "takedown_requests": ("takedown_requests", "max_takedown_requests")
        }
        
        if metric in metric_mapping:
            usage_key, limit_key = metric_mapping[metric]
            current_count = current_usage[usage_key]
            limit_count = limits[limit_key]
            remaining = max(0, limit_count - current_count)
        else:
            current_count = 0
            limit_count = 0
            remaining = 0
        
        return UsageLimitCheck(
            allowed=allowed,
            reason=reason,
            current_usage=current_count,
            limit=limit_count,
            remaining=remaining
        )
        
    except Exception as e:
        logger.error(f"Failed to check usage limit for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check usage limit"
        )


@router.get("/usage/analytics", response_model=UsageAnalytics)
async def get_usage_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage analytics."""
    try:
        analytics = await usage_service.get_usage_analytics(db, current_user.id, days)
        return UsageAnalytics(**analytics)
        
    except Exception as e:
        logger.error(f"Failed to get usage analytics for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage analytics"
        )


# Dashboard

@router.get("/dashboard", response_model=BillingDashboard)
async def get_billing_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive billing dashboard data."""
    try:
        # Get subscription
        subscription = await subscription_service.get_subscription(db, current_user.id)
        subscription_response = SubscriptionResponse.from_orm(subscription) if subscription else None
        
        # Get current usage
        usage = await usage_service.get_current_usage(db, current_user.id)
        current_usage = CurrentUsage(**usage)
        
        # Get usage limits
        limits = await usage_service.get_subscription_limits(db, current_user.id)
        usage_limits = UsageLimits(**limits)
        
        # Get recent invoices
        invoices = await subscription_service.get_billing_history(db, current_user.id, limit=5)
        recent_invoices = [InvoiceResponse.from_orm(invoice) for invoice in invoices]
        
        # TODO: Get upcoming invoice, payment methods, billing address
        
        return BillingDashboard(
            subscription=subscription_response,
            current_usage=current_usage,
            usage_limits=usage_limits,
            upcoming_invoice=None,
            payment_methods=[],
            billing_address=None,
            recent_invoices=recent_invoices
        )
        
    except Exception as e:
        logger.error(f"Failed to get billing dashboard for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get billing dashboard"
        )


# Webhooks

@router.post("/webhooks/stripe", response_model=WebhookEventResponse)
async def handle_stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Verify webhook signature and construct event
        event = stripe_service.construct_webhook_event(payload, signature)
        
        # Process the event
        processed = await webhook_service.handle_webhook_event(db, event)
        
        return WebhookEventResponse(
            processed=processed,
            message="Webhook processed successfully" if processed else "Webhook processing failed"
        )
        
    except Exception as e:
        logger.error(f"Failed to process Stripe webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )