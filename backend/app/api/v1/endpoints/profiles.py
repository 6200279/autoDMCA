from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.session import get_db
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
    query = db.query(ProtectedProfile).filter(ProtectedProfile.user_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            (ProtectedProfile.name.ilike(f"%{search}%")) |
            (ProtectedProfile.stage_name.ilike(f"%{search}%")) |
            (ProtectedProfile.real_name.ilike(f"%{search}%"))
        )
    
    if is_active is not None:
        query = query.filter(ProtectedProfile.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    profiles = query.offset(offset).limit(pagination.size).all()
    
    # Calculate pages
    pages = (total + pagination.size - 1) // pagination.size
    
    return PaginatedResponse(
        items=[ProfileSchema.from_orm(profile) for profile in profiles],
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
    """Create new protected profile."""
    # Check subscription limits
    existing_profiles = db.query(func.count(ProtectedProfile.id))\
        .filter(ProtectedProfile.user_id == current_user.id).scalar()
    
    # This would check against user's subscription plan limits
    max_profiles = 10  # This should come from user's subscription
    if existing_profiles >= max_profiles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile limit reached. Maximum {max_profiles} profiles allowed."
        )
    
    profile = ProtectedProfile(
        user_id=current_user.id,
        **profile_data.dict()
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # Start initial scan for the profile
    background_tasks.add_task(schedule_profile_scan, profile.id)
    
    return profile


@router.get("/{profile_id}", response_model=ProfileWithStats)
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get protected profile with statistics."""
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
    
    # Get profile statistics
    total_scans = 0  # This would come from scan_results table
    active_infringements = db.query(func.count(Infringement.id))\
        .filter(
            and_(
                Infringement.profile_id == profile_id,
                Infringement.status.in_(["pending", "confirmed"])
            )
        ).scalar()
    
    resolved_infringements = db.query(func.count(Infringement.id))\
        .filter(
            and_(
                Infringement.profile_id == profile_id,
                Infringement.status == "resolved"
            )
        ).scalar()
    
    pending_takedowns = 0  # This would come from takedown_requests table
    successful_takedowns = 0  # This would come from takedown_requests table
    
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
    
    # Get recent infringements count
    recent_infringements_count = db.query(func.count(Infringement.id))\
        .filter(
            and_(
                Infringement.profile_id == profile_id,
                Infringement.discovered_at >= func.current_date() - func.interval('7 days')
            )
        ).scalar()
    
    return ProfileWithStats(
        id=profile.id,
        user_id=profile.user_id,
        name=profile.name,
        description=profile.description,
        stage_name=profile.stage_name,
        real_name=profile.real_name,
        date_of_birth=profile.date_of_birth,
        social_media_handles=profile.social_media_handles,
        website_urls=profile.website_urls,
        keywords=profile.keywords,
        aliases=profile.aliases,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
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