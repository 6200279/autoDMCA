from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.session import get_db, get_async_session
from app.db.models.user import User
from app.db.models.profile import ProtectedProfile
from app.db.models.infringement import Infringement
from app.schemas.profile import (
    ProtectedProfile as ProfileSchema,
    ProtectedProfileCreate,
    ProtectedProfileUpdate,
    ProfileWithStats,
    ProfileStats,
    ReferenceImage,
    ReferenceImageCreate,
    ReferenceImageUpdate
)
from app.schemas.common import PaginatedResponse, StatusResponse
from app.api.deps.auth import get_current_active_user, get_current_verified_user
from app.api.deps.common import (
    get_pagination_params, 
    PaginationParams, 
    validate_owner_access
)
from app.core.config import settings
from app.services.billing.subscription_tier_enforcement import (
    enforce_profile_limit,
    subscription_enforcement
)
from app.services.scanning.automated_scheduler import automated_scheduler

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_profiles(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's protected profiles."""
    # Mock profile data for local testing
    from datetime import datetime
    
    mock_profiles = [
        {
            "id": 1,
            "user_id": current_user.id,
            "name": "Content Creator Pro",
            "stage_name": "CreatorPro",
            "real_name": "John Creator",
            "bio": "Professional content creator and artist",
            "profile_image_url": None,
            "is_active": True,
            "monitoring_enabled": True,
            "notification_settings": {"email": True, "push": True},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": 2,
            "user_id": current_user.id,
            "name": "Artistic Content",
            "stage_name": "ArtisticSoul",
            "real_name": "Jane Artist",
            "bio": "Digital artist and photographer",
            "profile_image_url": None,
            "is_active": True,
            "monitoring_enabled": True,
            "notification_settings": {"email": True, "push": False},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": 3,
            "user_id": current_user.id,
            "name": "Video Content",
            "stage_name": "VideoMaker",
            "real_name": "Mike Video",
            "bio": "YouTube content creator",
            "profile_image_url": None,
            "is_active": False,
            "monitoring_enabled": False,
            "notification_settings": {"email": False, "push": False},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Apply search filter
    if search:
        filtered_profiles = []
        for profile in mock_profiles:
            if (search.lower() in profile["name"].lower() or 
                search.lower() in profile["stage_name"].lower() or 
                search.lower() in profile["real_name"].lower()):
                filtered_profiles.append(profile)
        mock_profiles = filtered_profiles
    
    # Apply is_active filter
    if is_active is not None:
        mock_profiles = [p for p in mock_profiles if p["is_active"] == is_active]
    
    total = len(mock_profiles)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    profiles = mock_profiles[offset:offset + pagination.size]
    
    # Calculate pages
    pages = (total + pagination.size - 1) // pagination.size
    
    return PaginatedResponse(
        items=profiles,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages
    )


@router.post("", response_model=ProfileSchema, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProtectedProfileCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create new protected profile with subscription tier enforcement.
    
    PRD Requirements:
    - Basic Plan: Maximum 1 profile
    - Professional Plan: Maximum 5 profiles
    """
    from datetime import datetime
    
    # Convert to async session for subscription enforcement
    async with get_async_session() as async_db:
        # Check subscription tier limits before creating profile
        allowed, info = await subscription_enforcement.check_profile_limit(
            async_db, current_user.id, requested_profiles=1
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "subscription_limit_exceeded",
                    "message": f"Profile limit exceeded. You have {info['current_profiles']} of {info['max_profiles']} profiles.",
                    "current_profiles": info["current_profiles"],
                    "max_profiles": info["max_profiles"],
                    "tier": info["tier"],
                    "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade" if info["tier"] == "basic" else None
                }
            )
        
        # Mock profile creation response (with subscription context)
        new_profile = {
            "id": 4,  # Mock new profile ID
            "user_id": current_user.id,
            "name": profile_data.name,
            "stage_name": profile_data.stage_name,
            "real_name": profile_data.real_name,
            "bio": profile_data.bio,
            "profile_image_url": None,
            "is_active": True,
            "monitoring_enabled": True,
            "notification_settings": {"email": True, "push": True},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Schedule initial scan for new profile (PRD requirement)
        # "Find leaks immediately or within hours of signup"
        background_tasks.add_task(
            automated_scheduler.schedule_initial_scan_for_new_user,
            async_db,
            current_user.id
        )
        
        return new_profile


@router.get("/{profile_id}", response_model=ProfileWithStats)
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get protected profile with statistics."""
    # Mock profile data for local testing
    from datetime import datetime
    
    if profile_id not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    mock_profiles = {
        1: {
            "id": 1,
            "user_id": current_user.id,
            "name": "Content Creator Pro",
            "stage_name": "CreatorPro", 
            "real_name": "John Creator",
            "bio": "Professional content creator and artist",
            "profile_image_url": None,
            "is_active": True,
            "monitoring_enabled": True,
            "notification_settings": {"email": True, "push": True},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        2: {
            "id": 2,
            "user_id": current_user.id,
            "name": "Artistic Content",
            "stage_name": "ArtisticSoul",
            "real_name": "Jane Artist", 
            "bio": "Digital artist and photographer",
            "profile_image_url": None,
            "is_active": True,
            "monitoring_enabled": True,
            "notification_settings": {"email": True, "push": False},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        3: {
            "id": 3,
            "user_id": current_user.id,
            "name": "Video Content",
            "stage_name": "VideoMaker",
            "real_name": "Mike Video",
            "bio": "YouTube content creator",
            "profile_image_url": None,
            "is_active": False,
            "monitoring_enabled": False,
            "notification_settings": {"email": False, "push": False},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
    
    profile = mock_profiles[profile_id]
    
    # Mock profile statistics for local testing
    stats_data = {
        1: {"active_infringements": 5, "resolved_infringements": 18, "total_scans": 12},
        2: {"active_infringements": 3, "resolved_infringements": 15, "total_scans": 8}, 
        3: {"active_infringements": 0, "resolved_infringements": 2, "total_scans": 3}
    }
    
    profile_stats = stats_data.get(profile_id, {"active_infringements": 0, "resolved_infringements": 0, "total_scans": 0})
    
    total_scans = profile_stats["total_scans"]
    active_infringements = profile_stats["active_infringements"]
    resolved_infringements = profile_stats["resolved_infringements"]
    pending_takedowns = 2  # Mock pending takedowns
    successful_takedowns = 12  # Mock successful takedowns
    
    # Calculate protection score (0-100)
    total_infringements = active_infringements + resolved_infringements
    if total_infringements > 0:
        protection_score = (resolved_infringements / total_infringements) * 100
    else:
        protection_score = 100.0
    
    stats = ProfileStats(
        profile_id=profile_id,
        total_scans=total_scans,
        active_infringements=active_infringements,
        resolved_infringements=resolved_infringements,
        pending_takedowns=pending_takedowns,
        successful_takedowns=successful_takedowns,
        last_scan=None,  # This would come from scan_results table
        protection_score=protection_score
    )
    
    # Get reference images count
    reference_images_count = 0  # This would come from reference_images table
    
    # Get recent infringements count (mock)
    recent_infringements_count = 2  # Mock recent infringements in last 7 days
    
    return ProfileWithStats(
        id=profile["id"],
        user_id=profile["user_id"],
        name=profile["name"],
        description=profile.get("description"),
        stage_name=profile["stage_name"],
        real_name=profile["real_name"],
        date_of_birth=profile.get("date_of_birth"),
        social_media_handles=profile.get("social_media_handles"),
        website_urls=profile.get("website_urls"),
        keywords=profile.get("keywords"),
        aliases=profile.get("aliases"),
        is_active=profile["is_active"],
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
        stats=stats,
        reference_images_count=reference_images_count,
        recent_infringements_count=recent_infringements_count
    )


@router.put("/{profile_id}", response_model=ProfileSchema)
async def update_profile(
    profile_id: int,
    profile_update: ProtectedProfileUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update protected profile."""
    # Mock profile update for local testing
    from datetime import datetime
    
    if profile_id not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Mock updated profile data
    updated_profile = {
        "id": profile_id,
        "user_id": current_user.id,
        "name": profile_update.name or "Updated Profile",
        "stage_name": profile_update.stage_name or "UpdatedStage",
        "real_name": profile_update.real_name or "Updated Name",
        "bio": profile_update.bio or "Updated bio",
        "profile_image_url": None,
        "is_active": profile_update.is_active if profile_update.is_active is not None else True,
        "monitoring_enabled": profile_update.monitoring_enabled if profile_update.monitoring_enabled is not None else True,
        "notification_settings": {"email": True, "push": True},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    return updated_profile
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.delete("/{profile_id}", response_model=StatusResponse)
async def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete protected profile."""
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check if profile has active infringements
    active_infringements = db.query(func.count(Infringement.id))\
        .filter(
            and_(
                Infringement.profile_id == profile_id,
                Infringement.status.in_(["pending", "confirmed", "takedown_requested"])
            )
        ).scalar()
    
    if active_infringements > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete profile with active infringements"
        )
    
    db.delete(profile)
    db.commit()
    
    return StatusResponse(success=True, message="Profile deleted successfully")


@router.post("/{profile_id}/scan", response_model=StatusResponse)
async def scan_profile(
    profile_id: int,
    background_tasks: BackgroundTasks,
    scan_type: str = "comprehensive",
    platforms: Optional[List[str]] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Start scan for protected profile."""
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    if not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot scan inactive profile"
        )
    
    # Check scan limits based on subscription
    # This would check against user's monthly scan limit
    
    # Schedule scan
    background_tasks.add_task(
        schedule_profile_scan, 
        profile_id, 
        scan_type, 
        platforms
    )
    
    return StatusResponse(success=True, message="Scan scheduled successfully")


@router.post("/{profile_id}/reference-images", response_model=ReferenceImage, status_code=status.HTTP_201_CREATED)
async def upload_reference_image(
    profile_id: int,
    image: UploadFile = File(...),
    is_primary: bool = False,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Upload reference image for profile."""
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Validate image file
    if not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    if image.size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size must be less than 10MB"
        )
    
    # Save image and process
    from app.services.image.processor import process_reference_image
    image_data = await process_reference_image(profile_id, image, is_primary)
    
    return image_data


@router.get("/{profile_id}/reference-images", response_model=List[ReferenceImage])
async def get_reference_images(
    profile_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get reference images for profile."""
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # This would query the reference_images table
    return []


@router.delete("/{profile_id}/reference-images/{image_id}", response_model=StatusResponse)
async def delete_reference_image(
    profile_id: int,
    image_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete reference image."""
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Delete image from reference_images table and storage
    from app.services.image.processor import delete_reference_image
    await delete_reference_image(image_id)
    
    return StatusResponse(success=True, message="Reference image deleted successfully")


async def schedule_profile_scan(
    profile_id: int, 
    scan_type: str = "comprehensive", 
    platforms: Optional[List[str]] = None
):
    """Schedule a profile scan (background task)."""
    from app.services.scanning.scheduler import schedule_scan
    await schedule_scan(profile_id, scan_type, platforms)