from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.addon_service import AddonService, UserAddonSubscription, AddonServiceType
from app.services.billing.addon_service import AddonServiceManager

router = APIRouter()

# Pydantic models
class AddonServiceResponse(BaseModel):
    id: int
    name: str
    service_type: str
    description: Optional[str]
    price_monthly: Optional[float]
    price_one_time: Optional[float]
    is_recurring: bool
    features: Optional[str]

    class Config:
        from_attributes = True

class UserAddonSubscriptionResponse(BaseModel):
    id: int
    addon_service: AddonServiceResponse
    status: str
    quantity: int
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    activated_at: datetime

    class Config:
        from_attributes = True

class AddonSubscribeRequest(BaseModel):
    addon_service_id: int
    quantity: int = 1
    payment_method_id: Optional[str] = None

class AddonUsageResponse(BaseModel):
    addon_type: str
    has_addon: bool
    limit: int
    used: int
    remaining: int

@router.get("/available", response_model=List[AddonServiceResponse])
def get_available_addons(
    db: Session = Depends(get_db)
):
    """Get all available add-on services"""
    manager = AddonServiceManager(db)
    addons = manager.get_available_addons()
    
    return [
        AddonServiceResponse(
            id=addon.id,
            name=addon.name,
            service_type=addon.service_type.value,
            description=addon.description,
            price_monthly=addon.price_monthly,
            price_one_time=addon.price_one_time,
            is_recurring=addon.is_recurring,
            features=addon.features
        )
        for addon in addons
    ]

@router.get("/my-addons", response_model=List[UserAddonSubscriptionResponse])
def get_my_addons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's add-on subscriptions"""
    manager = AddonServiceManager(db)
    subscriptions = manager.get_user_addons(current_user.id)
    
    return [
        UserAddonSubscriptionResponse(
            id=sub.id,
            addon_service=AddonServiceResponse(
                id=sub.addon_service.id,
                name=sub.addon_service.name,
                service_type=sub.addon_service.service_type.value,
                description=sub.addon_service.description,
                price_monthly=sub.addon_service.price_monthly,
                price_one_time=sub.addon_service.price_one_time,
                is_recurring=sub.addon_service.is_recurring,
                features=sub.addon_service.features
            ),
            status=sub.status.value,
            quantity=sub.quantity,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            activated_at=sub.activated_at
        )
        for sub in subscriptions
    ]

@router.post("/subscribe")
def subscribe_to_addon(
    request: AddonSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Subscribe to an add-on service"""
    manager = AddonServiceManager(db)
    
    result = manager.subscribe_to_addon(
        user_id=current_user.id,
        addon_service_id=request.addon_service_id,
        quantity=request.quantity,
        payment_method_id=request.payment_method_id
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@router.post("/cancel/{subscription_id}")
def cancel_addon_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an add-on subscription"""
    manager = AddonServiceManager(db)
    
    result = manager.cancel_addon(
        user_id=current_user.id,
        subscription_id=subscription_id
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {"message": "Add-on subscription cancelled successfully"}

@router.get("/usage/{addon_type}", response_model=AddonUsageResponse)
def get_addon_usage(
    addon_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for an add-on type"""
    try:
        addon_type_enum = AddonServiceType(addon_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid add-on type"
        )
    
    manager = AddonServiceManager(db)
    limits = manager.get_addon_limits(current_user.id, addon_type_enum)
    
    return AddonUsageResponse(
        addon_type=addon_type,
        **limits
    )

@router.get("/extra-profiles/available")
def get_extra_profile_slots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available extra profile slots"""
    manager = AddonServiceManager(db)
    limits = manager.get_addon_limits(current_user.id, AddonServiceType.EXTRA_PROFILE)
    
    # Get base plan profile limit (this would come from user's main subscription)
    base_profiles = 1  # Default for basic plan
    if hasattr(current_user, 'subscription_plan'):
        if current_user.subscription_plan == 'professional':
            base_profiles = 5
        elif current_user.subscription_plan == 'enterprise':
            base_profiles = -1  # Unlimited
    
    total_available = base_profiles + limits.get("limit", 0) if base_profiles != -1 else -1
    
    return {
        "base_profiles": base_profiles,
        "extra_profiles": limits.get("limit", 0),
        "total_available": total_available,
        "currently_used": limits.get("used", 0),
        "can_add_more": total_available == -1 or limits.get("used", 0) < total_available
    }