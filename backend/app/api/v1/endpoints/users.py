from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.profile import ProtectedProfile
from app.db.models.infringement import Infringement
from app.db.models.takedown import TakedownRequest
from app.schemas.user import (
    User as UserSchema, 
    UserProfile, 
    UserUpdate, 
    UserSettings,
    UserSettingsUpdate,
    UserActivity
)
from app.schemas.common import PaginatedResponse, StatusResponse
from app.api.deps.auth import get_current_active_user, get_current_superuser
from app.api.deps.common import get_pagination_params, PaginationParams

router = APIRouter()


@router.get("/me-mock", response_model=UserProfile)
async def get_mock_user_profile() -> Any:
    """Get mock user profile for local testing (bypasses authentication)."""
    from app.core.config import settings
    from datetime import datetime
    
    if settings.ENVIRONMENT != "local":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock endpoint only available in local environment"
        )
    
    return UserProfile(
        id=1,
        email="admin@autodmca.com",
        full_name="Admin User",
        company="AutoDMCA",
        phone="+1234567890",
        bio="System Administrator",
        avatar_url=None,
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
        subscription_plan="Premium",
        subscription_status="active",
        profiles_count=5,
        infringements_count=12,
        takedowns_count=8
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current user profile with statistics."""
    from app.core.config import settings
    
    # Handle mock users for local development
    if settings.ENVIRONMENT == "local" and hasattr(current_user, '__class__') and current_user.__class__.__name__ == 'MockUser':
        # Return mock statistics for local testing
        return UserProfile(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            company=current_user.company,
            phone=current_user.phone,
            bio=current_user.bio,
            avatar_url=current_user.avatar_url,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
            subscription_plan="Premium" if current_user.is_superuser else "Basic",
            subscription_status="active",
            profiles_count=5 if current_user.is_superuser else 2,
            infringements_count=12 if current_user.is_superuser else 3,
            takedowns_count=8 if current_user.is_superuser else 1
        )
    
    # Get user statistics from database
    profiles_count = db.query(func.count(ProtectedProfile.id))\
        .filter(ProtectedProfile.user_id == current_user.id).scalar()
    
    infringements_count = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == current_user.id).scalar()
    
    takedowns_count = db.query(func.count(TakedownRequest.id))\
        .filter(TakedownRequest.user_id == current_user.id).scalar()
    
    # Get subscription info
    subscription_plan = None
    subscription_status = None
    if hasattr(current_user, 'subscription') and current_user.subscription:
        subscription_plan = current_user.subscription.plan
        subscription_status = current_user.subscription.status
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        company=current_user.company,
        phone=current_user.phone,
        bio=current_user.bio,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        subscription_plan=subscription_plan,
        subscription_status=subscription_status,
        profiles_count=profiles_count,
        infringements_count=infringements_count,
        takedowns_count=takedowns_count
    )


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user profile."""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/me/avatar", response_model=UserSchema)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Upload user avatar."""
    # Validate file type
    if not avatar.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (5MB max)
    if avatar.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )
    
    # Save file and update user
    from app.services.file.storage import save_avatar
    avatar_url = await save_avatar(current_user.id, avatar)
    
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete("/me/avatar", response_model=StatusResponse)
async def delete_avatar(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user avatar."""
    if current_user.avatar_url:
        from app.services.file.storage import delete_avatar
        await delete_avatar(current_user.avatar_url)
        
        current_user.avatar_url = None
        db.commit()
    
    return StatusResponse(success=True, message="Avatar deleted successfully")


@router.get("/me/settings", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get user settings."""
    # In a real implementation, settings would be stored in a separate table
    # For now, return default settings
    return UserSettings(
        email_notifications=True,
        sms_notifications=False,
        push_notifications=True,
        weekly_reports=True,
        monthly_reports=True,
        auto_takedown=False,
        scan_frequency="daily",
        language="en",
        timezone="UTC"
    )


@router.put("/me/settings", response_model=UserSettings)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user settings."""
    # In a real implementation, you would update the user_settings table
    # For now, return updated settings
    current_settings = UserSettings()
    update_data = settings_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_settings, field, value)
    
    return current_settings


@router.get("/me/activity", response_model=PaginatedResponse)
async def get_user_activity(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user activity log."""
    # In a real implementation, you would query the activity log table
    # For now, return empty response
    return PaginatedResponse(
        items=[],
        total=0,
        page=pagination.page,
        size=pagination.size,
        pages=0
    )


# Admin endpoints
@router.get("", response_model=PaginatedResponse)
async def get_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """Get all users (admin only)."""
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.company.ilike(f"%{search}%"))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    users = query.offset(offset).limit(pagination.size).all()
    
    # Calculate pages
    pages = (total + pagination.size - 1) // pagination.size
    
    return PaginatedResponse(
        items=[UserSchema.from_orm(user) for user in users],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages
    )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """Get user by ID (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user statistics
    profiles_count = db.query(func.count(ProtectedProfile.id))\
        .filter(ProtectedProfile.user_id == user.id).scalar()
    
    infringements_count = db.query(func.count(Infringement.id))\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == user.id).scalar()
    
    takedowns_count = db.query(func.count(TakedownRequest.id))\
        .filter(TakedownRequest.user_id == user.id).scalar()
    
    # Get subscription info
    subscription_plan = None
    subscription_status = None
    if hasattr(user, 'subscription') and user.subscription:
        subscription_plan = user.subscription.plan
        subscription_status = user.subscription.status
    
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company=user.company,
        phone=user.phone,
        bio=user.bio,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
        subscription_plan=subscription_plan,
        subscription_status=subscription_status,
        profiles_count=profiles_count,
        infringements_count=infringements_count,
        takedowns_count=takedowns_count
    )


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", response_model=StatusResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    
    return StatusResponse(success=True, message="User deactivated successfully")