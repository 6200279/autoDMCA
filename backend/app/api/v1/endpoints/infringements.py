from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.profile import ProtectedProfile
from app.db.models.infringement import Infringement
from app.db.models.takedown import TakedownRequest
from app.schemas.infringement import (
    Infringement as InfringementSchema,
    InfringementDetail,
    InfringementUpdate,
    InfringementStats,
    InfringementFilter,
    BulkInfringementAction,
    ScanRequest,
    ScanResult,
    ManualInfringementCreate,
    InfringementStatus,
    InfringementSeverity,
    InfringementType
)
from app.schemas.common import PaginatedResponse, StatusResponse
from app.api.deps.auth import get_current_verified_user
from app.api.deps.common import get_pagination_params, PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_infringements(
    pagination: PaginationParams = Depends(get_pagination_params),
    profile_id: Optional[int] = Query(None, description="Filter by profile ID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[InfringementStatus] = Query(None, description="Filter by status"),
    severity: Optional[InfringementSeverity] = Query(None, description="Filter by severity"),
    infringement_type: Optional[InfringementType] = Query(None, description="Filter by type"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence score"),
    search: Optional[str] = Query(None, description="Search in URL or description"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's infringements with filtering."""
    # Mock data for local development
    from app.core.config import settings
    if settings.ENVIRONMENT == "local":
        from datetime import datetime, timedelta
        import random
        
        # Generate mock infringements
        mock_infringements = []
        platforms = ["Twitter", "Instagram", "TikTok", "YouTube", "Reddit", "OnlyFans"]
        types = ["IMAGE", "VIDEO", "TEXT", "PROFILE"]
        statuses = ["PENDING", "SUBMITTED", "RESOLVED", "DISMISSED", "FAILED"]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for i in range(50):  # Generate 50 mock infringements
            mock_infringements.append({
                "id": i + 1,
                "profile_id": (i % 3) + 1,
                "profile_name": f"Profile {(i % 3) + 1}",
                "reporter_id": None,
                "url": f"https://{random.choice(platforms).lower()}.com/content/{i+1000}",
                "platform": random.choice(platforms),
                "infringement_type": random.choice(types),
                "status": random.choice(statuses),
                "severity": random.choice(severities),
                "confidence_score": round(random.uniform(0.6, 0.99), 2),
                "description": f"Unauthorized use of copyrighted content - Item #{i+1}",
                "evidence_urls": [f"https://evidence.autodmca.com/{i+1}"],
                "metadata": {
                    "views": random.randint(100, 100000),
                    "likes": random.randint(10, 10000),
                    "shares": random.randint(1, 1000)
                },
                "notes": f"Detected by automated scanner",
                "discovered_at": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                "updated_at": datetime.utcnow()
            })
        
        # Apply filters
        filtered = mock_infringements
        
        if profile_id:
            filtered = [i for i in filtered if i["profile_id"] == profile_id]
        
        if platform:
            filtered = [i for i in filtered if platform.lower() in i["platform"].lower()]
        
        if status:
            filtered = [i for i in filtered if i["status"] == status]
        
        if severity:
            filtered = [i for i in filtered if i["severity"] == severity]
        
        if infringement_type:
            filtered = [i for i in filtered if i["infringement_type"] == infringement_type]
        
        if search:
            filtered = [i for i in filtered if 
                       search.lower() in i["url"].lower() or 
                       search.lower() in i["description"].lower()]
        
        # Sort by discovered_at (newest first)
        filtered.sort(key=lambda x: x["discovered_at"], reverse=True)
        
        total = len(filtered)
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        paginated_items = filtered[offset:offset + pagination.size]
        
        # Calculate pages
        pages = (total + pagination.size - 1) // pagination.size if pagination.size > 0 else 0
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )
    
    # Original database query code (for production)
    else:
        # Base query - only infringements for user's profiles
        query = db.query(Infringement)\
            .join(ProtectedProfile)\
            .filter(ProtectedProfile.user_id == current_user.id)\
            .options(joinedload(Infringement.profile))
    
        # Apply filters
        if profile_id:
            # Verify user owns the profile
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
            query = query.filter(Infringement.profile_id == profile_id)
        
        if platform:
            query = query.filter(Infringement.platform.ilike(f"%{platform}%"))
        
        if status:
            query = query.filter(Infringement.status == status)
        
        if severity:
            query = query.filter(Infringement.severity == severity)
        
        if infringement_type:
            query = query.filter(Infringement.infringement_type == infringement_type)
        
        if date_from:
            query = query.filter(Infringement.discovered_at >= date_from)
        
        if date_to:
            query = query.filter(Infringement.discovered_at <= date_to)
        
        if min_confidence is not None:
            query = query.filter(Infringement.confidence_score >= min_confidence)
        
        if search:
            query = query.filter(
                or_(
                    Infringement.url.ilike(f"%{search}%"),
                    Infringement.description.ilike(f"%{search}%")
                )
            )
        
        # Order by discovery date (newest first)
        query = query.order_by(desc(Infringement.discovered_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        infringements = query.offset(offset).limit(pagination.size).all()
        
        # Calculate pages
        pages = (total + pagination.size - 1) // pagination.size
        
        # Transform to response format
        items = []
        for infringement in infringements:
            item = InfringementSchema(
                id=infringement.id,
                profile_id=infringement.profile_id,
                profile_name=infringement.profile.name,
                reporter_id=infringement.reporter_id,
                url=infringement.url,
                platform=infringement.platform,
                infringement_type=infringement.infringement_type,
                status=infringement.status,
                severity=infringement.severity,
                confidence_score=infringement.confidence_score,
                description=infringement.description,
                evidence_urls=infringement.evidence_urls,
                metadata=infringement.metadata,
                notes=infringement.notes,
                discovered_at=infringement.discovered_at,
                updated_at=infringement.updated_at
            )
            items.append(item)
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )


@router.get("/stats", response_model=InfringementStats)
async def get_infringement_stats(
    profile_id: Optional[int] = Query(None, description="Filter by profile ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days for stats"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get infringement statistics."""
    # Mock data for local development
    from app.core.config import settings
    if settings.ENVIRONMENT == "local":
        from datetime import datetime, timedelta
        
        # Return mock statistics
        return InfringementStats(
            total_infringements=127,
            pending_infringements=43,
            resolved_infringements=67,
            dismissed_infringements=17,
            total_takedowns_sent=82,
            successful_takedowns=61,
            pending_takedowns=15,
            failed_takedowns=6,
            average_resolution_time=72.5,
            infringements_by_platform={
                "Twitter": 35,
                "Instagram": 28,
                "TikTok": 24,
                "YouTube": 18,
                "Reddit": 12,
                "OnlyFans": 10
            },
            infringements_by_type={
                "IMAGE": 58,
                "VIDEO": 42,
                "TEXT": 18,
                "PROFILE": 9
            },
            recent_infringements_count=23,
            resolution_rate=0.76,
            false_positive_rate=0.13
        )
    
    # Original database query code (for production)
    # Base query for user's infringements
    base_query = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(ProtectedProfile.user_id == current_user.id)
    
    if profile_id:
        # Verify user owns the profile
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
        base_query = base_query.filter(Infringement.profile_id == profile_id)
    
    # Date range
    date_from = datetime.utcnow() - timedelta(days=days)
    recent_query = base_query.filter(Infringement.discovered_at >= date_from)
    
    # Total infringements
    total_infringements = base_query.count()
    
    # By status
    status_stats = {}
    for status_val in InfringementStatus:
        count = base_query.filter(Infringement.status == status_val).count()
        status_stats[status_val] = count
    
    # By platform
    platform_stats = {}
    platform_counts = base_query.with_entities(
        Infringement.platform, 
        func.count(Infringement.id)
    ).group_by(Infringement.platform).all()
    
    for platform, count in platform_counts:
        platform_stats[platform] = count
    
    # By severity
    severity_stats = {}
    for severity_val in InfringementSeverity:
        count = base_query.filter(Infringement.severity == severity_val).count()
        severity_stats[severity_val] = count
    
    # By type
    type_stats = {}
    for type_val in InfringementType:
        count = base_query.filter(Infringement.infringement_type == type_val).count()
        type_stats[type_val] = count
    
    # Recent count
    recent_count = recent_query.count()
    
    # Resolved count
    resolved_count = base_query.filter(Infringement.status == "resolved").count()
    
    # Success rate
    success_rate = 0.0
    if total_infringements > 0:
        success_rate = (resolved_count / total_infringements) * 100
    
    return InfringementStats(
        total_infringements=total_infringements,
        by_status=status_stats,
        by_platform=platform_stats,
        by_severity=severity_stats,
        by_type=type_stats,
        recent_count=recent_count,
        resolved_count=resolved_count,
        success_rate=success_rate
    )


@router.get("/{infringement_id}", response_model=InfringementDetail)
async def get_infringement(
    infringement_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed infringement information."""
    infringement = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id == infringement_id,
                ProtectedProfile.user_id == current_user.id
            )
        ).options(joinedload(Infringement.profile)).first()
    
    if not infringement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infringement not found"
        )
    
    # Get related takedown requests
    takedown_requests = db.query(TakedownRequest)\
        .filter(TakedownRequest.infringement_id == infringement_id)\
        .all()
    
    takedown_data = []
    for takedown in takedown_requests:
        takedown_data.append({
            "id": takedown.id,
            "status": takedown.status,
            "method": takedown.method,
            "sent_at": takedown.sent_at,
            "resolved_at": takedown.resolved_at
        })
    
    # Get similar infringements (same profile, platform, or similar URL)
    similar_infringements = db.query(Infringement)\
        .filter(
            and_(
                Infringement.id != infringement_id,
                or_(
                    Infringement.profile_id == infringement.profile_id,
                    and_(
                        Infringement.platform == infringement.platform,
                        Infringement.url.ilike(f"%{infringement.platform}%")
                    )
                )
            )
        ).limit(5).all()
    
    similar_data = []
    for similar in similar_infringements:
        similar_data.append({
            "id": similar.id,
            "url": similar.url,
            "platform": similar.platform,
            "confidence_score": similar.confidence_score,
            "status": similar.status
        })
    
    return InfringementDetail(
        id=infringement.id,
        profile_id=infringement.profile_id,
        profile_name=infringement.profile.name,
        reporter_id=infringement.reporter_id,
        url=infringement.url,
        platform=infringement.platform,
        infringement_type=infringement.infringement_type,
        status=infringement.status,
        severity=infringement.severity,
        confidence_score=infringement.confidence_score,
        description=infringement.description,
        evidence_urls=infringement.evidence_urls,
        metadata=infringement.metadata,
        notes=infringement.notes,
        discovered_at=infringement.discovered_at,
        updated_at=infringement.updated_at,
        takedown_requests=takedown_data,
        similar_infringements=similar_data,
        scan_results=infringement.metadata.get("scan_results") if infringement.metadata else None
    )


@router.put("/{infringement_id}", response_model=InfringementSchema)
async def update_infringement(
    infringement_id: int,
    infringement_update: InfringementUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update infringement details."""
    infringement = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id == infringement_id,
                ProtectedProfile.user_id == current_user.id
            )
        ).first()
    
    if not infringement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infringement not found"
        )
    
    update_data = infringement_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(infringement, field, value)
    
    infringement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(infringement)
    
    return InfringementSchema(
        id=infringement.id,
        profile_id=infringement.profile_id,
        profile_name=infringement.profile.name,
        reporter_id=infringement.reporter_id,
        url=infringement.url,
        platform=infringement.platform,
        infringement_type=infringement.infringement_type,
        status=infringement.status,
        severity=infringement.severity,
        confidence_score=infringement.confidence_score,
        description=infringement.description,
        evidence_urls=infringement.evidence_urls,
        metadata=infringement.metadata,
        notes=infringement.notes,
        discovered_at=infringement.discovered_at,
        updated_at=infringement.updated_at
    )


@router.post("/bulk-action", response_model=StatusResponse)
async def bulk_infringement_action(
    action_data: BulkInfringementAction,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Perform bulk action on infringements."""
    # Verify all infringements belong to user
    infringements = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id.in_(action_data.infringement_ids),
                ProtectedProfile.user_id == current_user.id
            )
        ).all()
    
    if len(infringements) != len(action_data.infringement_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some infringements not found"
        )
    
    # Perform action
    if action_data.action == "mark_resolved":
        for infringement in infringements:
            infringement.status = "resolved"
            if action_data.notes:
                infringement.notes = action_data.notes
        
        db.commit()
        return StatusResponse(
            success=True, 
            message=f"Marked {len(infringements)} infringements as resolved"
        )
    
    elif action_data.action == "mark_false_positive":
        for infringement in infringements:
            infringement.status = "false_positive"
            if action_data.notes:
                infringement.notes = action_data.notes
        
        db.commit()
        return StatusResponse(
            success=True, 
            message=f"Marked {len(infringements)} infringements as false positive"
        )
    
    elif action_data.action == "request_takedown":
        # Schedule takedown requests
        for infringement in infringements:
            background_tasks.add_task(
                schedule_takedown_request,
                infringement.id,
                current_user.id,
                action_data.notes
            )
        
        return StatusResponse(
            success=True, 
            message=f"Scheduled takedown requests for {len(infringements)} infringements"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action"
        )


@router.delete("/{infringement_id}", response_model=StatusResponse)
async def delete_infringement(
    infringement_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete infringement (mark as ignored)."""
    infringement = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id == infringement_id,
                ProtectedProfile.user_id == current_user.id
            )
        ).first()
    
    if not infringement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infringement not found"
        )
    
    # Check if there are active takedown requests
    active_takedowns = db.query(TakedownRequest).filter(
        and_(
            TakedownRequest.infringement_id == infringement_id,
            TakedownRequest.status.in_(["sent", "acknowledged", "compliance_review"])
        )
    ).count()
    
    if active_takedowns > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete infringement with active takedown requests"
        )
    
    # Soft delete by marking as ignored
    infringement.status = "ignored"
    db.commit()
    
    return StatusResponse(success=True, message="Infringement marked as ignored")


@router.post("/manual", response_model=InfringementSchema, status_code=status.HTTP_201_CREATED)
async def create_manual_infringement(
    infringement_data: ManualInfringementCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create manual infringement report."""
    # Verify user owns the profile
    profile = db.query(ProtectedProfile).filter(
        and_(
            ProtectedProfile.id == infringement_data.profile_id,
            ProtectedProfile.user_id == current_user.id
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check for duplicate URL
    existing = db.query(Infringement).filter(
        and_(
            Infringement.url == str(infringement_data.url),
            Infringement.profile_id == infringement_data.profile_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Infringement with this URL already exists for this profile"
        )
    
    # Create infringement
    infringement = Infringement(
        profile_id=infringement_data.profile_id,
        reporter_id=current_user.id,
        url=str(infringement_data.url),
        platform=infringement_data.platform,
        infringement_type=infringement_data.infringement_type,
        status="confirmed",  # Manual reports are pre-confirmed
        severity="medium",  # Default severity
        confidence_score=1.0,  # Manual reports have 100% confidence
        description=infringement_data.description,
        evidence_urls=infringement_data.evidence_urls,
        metadata={"source": "manual", "reporter_id": current_user.id},
        discovered_at=datetime.utcnow()
    )
    
    db.add(infringement)
    db.commit()
    db.refresh(infringement)
    
    # Schedule analysis to improve confidence and gather more evidence
    background_tasks.add_task(analyze_manual_infringement, infringement.id)
    
    return InfringementSchema(
        id=infringement.id,
        profile_id=infringement.profile_id,
        profile_name=profile.name,
        reporter_id=infringement.reporter_id,
        url=infringement.url,
        platform=infringement.platform,
        infringement_type=infringement.infringement_type,
        status=infringement.status,
        severity=infringement.severity,
        confidence_score=infringement.confidence_score,
        description=infringement.description,
        evidence_urls=infringement.evidence_urls,
        metadata=infringement.metadata,
        notes=infringement.notes,
        discovered_at=infringement.discovered_at,
        updated_at=infringement.updated_at
    )


async def schedule_takedown_request(infringement_id: int, user_id: int, notes: Optional[str] = None):
    """Schedule takedown request for infringement (background task)."""
    from app.services.takedown.scheduler import schedule_takedown
    await schedule_takedown(infringement_id, user_id, notes)


async def analyze_manual_infringement(infringement_id: int):
    """Analyze manual infringement to gather more evidence (background task)."""
    from app.services.analysis.infringement_analyzer import analyze_infringement
    await analyze_infringement(infringement_id)