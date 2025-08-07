from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.subscription import Subscription
from app.schemas.subscription import (
    Subscription as SubscriptionSchema,
    SubscriptionCreate,
    SubscriptionUpdate,
    PlanFeatures,
    UsageStats,
    Invoice,
    PaymentMethod,
    PaymentMethodCreate,
    SubscriptionChange,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingInterval
)
from app.schemas.common import StatusResponse, PaginatedResponse
from app.api.deps.auth import get_current_verified_user
from app.api.deps.common import get_pagination_params, PaginationParams

router = APIRouter()


@router.get("/plans", response_model=List[PlanFeatures])
async def get_subscription_plans() -> Any:
    """Get available subscription plans."""
    plans = [
        PlanFeatures(
            plan=SubscriptionPlan.FREE,
            max_profiles=1,
            max_scans_per_month=10,
            max_takedowns_per_month=5,
            api_access=False,
            priority_support=False,
            bulk_operations=False,
            advanced_analytics=False,
            custom_templates=False,
            whitelabeling=False,
            monthly_price=Decimal("0.00"),
            yearly_price=Decimal("0.00")
        ),
        PlanFeatures(
            plan=SubscriptionPlan.BASIC,
            max_profiles=3,
            max_scans_per_month=100,
            max_takedowns_per_month=50,
            api_access=True,
            priority_support=False,
            bulk_operations=True,
            advanced_analytics=True,
            custom_templates=True,
            whitelabeling=False,
            monthly_price=Decimal("29.99"),
            yearly_price=Decimal("299.99")
        ),
        PlanFeatures(
            plan=SubscriptionPlan.PROFESSIONAL,
            max_profiles=10,
            max_scans_per_month=500,
            max_takedowns_per_month=250,
            api_access=True,
            priority_support=True,
            bulk_operations=True,
            advanced_analytics=True,
            custom_templates=True,
            whitelabeling=False,
            monthly_price=Decimal("99.99"),
            yearly_price=Decimal("999.99")
        ),
        PlanFeatures(
            plan=SubscriptionPlan.ENTERPRISE,
            max_profiles=-1,  # Unlimited
            max_scans_per_month=-1,  # Unlimited
            max_takedowns_per_month=-1,  # Unlimited
            api_access=True,
            priority_support=True,
            bulk_operations=True,
            advanced_analytics=True,
            custom_templates=True,
            whitelabeling=True,
            monthly_price=Decimal("299.99"),
            yearly_price=Decimal("2999.99")
        )
    ]
    
    return plans


@router.get("/current", response_model=SubscriptionSchema)
async def get_current_subscription(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current user's subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        # Create default free subscription
        subscription = Subscription(
            user_id=current_user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            auto_renew=True,
            created_at=datetime.utcnow()
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription


@router.post("/create", response_model=SubscriptionSchema, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create or upgrade subscription."""
    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if existing_subscription and existing_subscription.plan != SubscriptionPlan.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )
    
    # Calculate dates
    start_date = datetime.utcnow()
    if subscription_data.billing_interval == BillingInterval.YEARLY:
        end_date = start_date + timedelta(days=365)
    else:
        end_date = start_date + timedelta(days=30)
    
    if existing_subscription:
        # Upgrade existing free subscription
        existing_subscription.plan = subscription_data.plan
        existing_subscription.billing_interval = subscription_data.billing_interval
        existing_subscription.status = SubscriptionStatus.ACTIVE
        existing_subscription.current_period_start = start_date
        existing_subscription.current_period_end = end_date
        existing_subscription.updated_at = datetime.utcnow()
        
        subscription = existing_subscription
    else:
        # Create new subscription
        subscription = Subscription(
            user_id=current_user.id,
            plan=subscription_data.plan,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=subscription_data.billing_interval,
            current_period_start=start_date,
            current_period_end=end_date,
            auto_renew=True,
            created_at=datetime.utcnow()
        )
        db.add(subscription)
    
    db.commit()
    db.refresh(subscription)
    
    # Process payment if payment method provided
    if subscription_data.payment_method_id:
        background_tasks.add_task(
            process_subscription_payment,
            subscription.id,
            subscription_data.payment_method_id
        )
    
    # Log subscription change
    background_tasks.add_task(
        log_subscription_change,
        subscription.id,
        SubscriptionPlan.FREE if existing_subscription else None,
        subscription_data.plan,
        "upgrade" if existing_subscription else "create"
    )
    
    return subscription


@router.put("/current", response_model=SubscriptionSchema)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    update_data = subscription_update.dict(exclude_unset=True)
    old_plan = subscription.plan
    
    for field, value in update_data.items():
        setattr(subscription, field, value)
    
    subscription.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(subscription)
    
    # Log change if plan changed
    if "plan" in update_data and update_data["plan"] != old_plan:
        change_type = "upgrade" if update_data["plan"].value > old_plan.value else "downgrade"
        background_tasks.add_task(
            log_subscription_change,
            subscription.id,
            old_plan,
            update_data["plan"],
            change_type
        )
    
    return subscription


@router.post("/cancel", response_model=StatusResponse)
async def cancel_subscription(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Cancel current subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    if subscription.status == SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already canceled"
        )
    
    # Cancel at end of current period
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.utcnow()
    subscription.auto_renew = False
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Log cancellation
    background_tasks.add_task(
        log_subscription_change,
        subscription.id,
        subscription.plan,
        SubscriptionPlan.FREE,
        "cancel"
    )
    
    # Send cancellation email
    background_tasks.add_task(
        send_cancellation_email,
        current_user.email,
        current_user.full_name,
        subscription.current_period_end
    )
    
    return StatusResponse(
        success=True, 
        message=f"Subscription will be canceled at the end of the current period ({subscription.current_period_end.strftime('%Y-%m-%d')})"
    )


@router.post("/reactivate", response_model=SubscriptionSchema)
async def reactivate_subscription(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Reactivate canceled subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if subscription.status != SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not canceled"
        )
    
    # Reactivate subscription
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.canceled_at = None
    subscription.auto_renew = True
    subscription.updated_at = datetime.utcnow()
    
    # Extend current period if expired
    if subscription.current_period_end <= datetime.utcnow():
        if subscription.billing_interval == BillingInterval.YEARLY:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=365)
        else:
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
    
    db.commit()
    db.refresh(subscription)
    
    # Log reactivation
    background_tasks.add_task(
        log_subscription_change,
        subscription.id,
        SubscriptionPlan.FREE,
        subscription.plan,
        "reactivate"
    )
    
    return subscription


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current usage statistics."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Calculate usage for current period
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end
    
    # In a real implementation, these would come from usage tracking tables
    profiles_used = 1  # From profiles table
    scans_used = 5  # From scan_results table
    takedowns_used = 2  # From takedown_requests table
    storage_used = 150  # In MB, from file storage
    api_calls_used = 100  # From api_usage table
    
    return UsageStats(
        subscription_id=subscription.id,
        current_period_start=period_start,
        current_period_end=period_end,
        profiles_used=profiles_used,
        scans_used=scans_used,
        takedowns_used=takedowns_used,
        storage_used=storage_used,
        api_calls_used=api_calls_used
    )


@router.get("/invoices", response_model=PaginatedResponse)
async def get_invoices(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's invoices."""
    # In a real implementation, this would query invoices table
    return PaginatedResponse(
        items=[],
        total=0,
        page=pagination.page,
        size=pagination.size,
        pages=0
    )


@router.get("/payment-methods", response_model=List[PaymentMethod])
async def get_payment_methods(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's payment methods."""
    # In a real implementation, this would query payment_methods table
    return []


@router.post("/payment-methods", response_model=PaymentMethod, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    payment_data: PaymentMethodCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Add new payment method."""
    # In a real implementation, this would integrate with Stripe/payment processor
    background_tasks.add_task(
        process_payment_method,
        current_user.id,
        payment_data.payment_method_id,
        payment_data.billing_address.dict(),
        payment_data.is_default
    )
    
    # Return placeholder payment method
    return PaymentMethod(
        id=payment_data.payment_method_id,
        user_id=current_user.id,
        type="card",
        last4="4242",
        brand="visa",
        exp_month=12,
        exp_year=2025,
        is_default=payment_data.is_default,
        created_at=datetime.utcnow()
    )


@router.delete("/payment-methods/{method_id}", response_model=StatusResponse)
async def delete_payment_method(
    method_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete payment method."""
    # In a real implementation, this would delete from payment_methods table
    return StatusResponse(success=True, message="Payment method deleted successfully")


@router.get("/changes", response_model=List[SubscriptionChange])
async def get_subscription_changes(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get subscription change history."""
    # In a real implementation, this would query subscription_changes table
    return []


# Background tasks
async def process_subscription_payment(subscription_id: int, payment_method_id: str):
    """Process subscription payment (background task)."""
    from app.services.billing.payment_processor import process_payment
    await process_payment(subscription_id, payment_method_id)


async def log_subscription_change(
    subscription_id: int,
    from_plan: Optional[SubscriptionPlan],
    to_plan: SubscriptionPlan,
    change_type: str
):
    """Log subscription change (background task)."""
    from app.services.billing.subscription_logger import log_change
    await log_change(subscription_id, from_plan, to_plan, change_type)


async def send_cancellation_email(email: str, name: str, end_date: datetime):
    """Send subscription cancellation email (background task)."""
    from app.services.auth.email_service import send_cancellation_email
    await send_cancellation_email(email, name, end_date)


async def process_payment_method(
    user_id: int,
    payment_method_id: str,
    billing_address: dict,
    is_default: bool
):
    """Process new payment method (background task)."""
    from app.services.billing.payment_processor import add_payment_method
    await add_payment_method(user_id, payment_method_id, billing_address, is_default)