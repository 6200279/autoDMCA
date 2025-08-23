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
from app.schemas.takedown import (
    TakedownRequest as TakedownSchema,
    TakedownRequestCreate,
    TakedownRequestUpdate,
    TakedownTemplate,
    TakedownTemplateCreate,
    TakedownTemplateUpdate,
    TakedownStats,
    BulkTakedownRequest,
    TakedownFilter,
    TakedownStatus,
    TakedownMethod
)
from app.schemas.common import PaginatedResponse, StatusResponse
from app.api.deps.auth import get_current_verified_user
from app.api.deps.common import get_pagination_params, PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_takedown_requests(
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: Optional[TakedownStatus] = Query(None, alias="status", description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    method: Optional[TakedownMethod] = Query(None, description="Filter by method"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search in subject or recipient"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's takedown requests with filtering."""
    # Mock data for local development
    from app.core.config import settings
    if settings.ENVIRONMENT == "local":
        import random
        
        # Generate mock takedown requests
        mock_takedowns = []
        platforms = ["Twitter", "Instagram", "TikTok", "YouTube", "Reddit", "OnlyFans"]
        statuses = ["DRAFT", "SENT", "PENDING", "ACCEPTED", "REJECTED", "ESCALATED"]
        methods = ["EMAIL", "FORM", "API", "MANUAL"]
        
        for i in range(30):  # Generate 30 mock takedown requests
            platform = random.choice(platforms)
            status = random.choice(statuses)
            method = random.choice(methods)
            
            mock_takedowns.append({
                "id": i + 1,
                "user_id": current_user.id,
                "infringement_id": i + 1,
                "infringement_url": f"https://{platform.lower()}.com/content/{i+2000}",
                "platform": platform,
                "status": status,
                "method": method,
                "recipient_email": f"legal@{platform.lower()}.com",
                "recipient_name": f"{platform} Legal Team",
                "subject": f"DMCA Takedown Notice - Content ID {i+2000}",
                "body": f"This is a formal DMCA takedown notice for unauthorized content...",
                "sent_at": datetime.utcnow() - timedelta(days=random.randint(0, 15)) if status != "DRAFT" else None,
                "response_received_at": datetime.utcnow() - timedelta(days=random.randint(0, 5)) if status in ["ACCEPTED", "REJECTED"] else None,
                "response_body": "Content has been removed" if status == "ACCEPTED" else None,
                "attachments": [],
                "metadata": {
                    "tracking_id": f"DMCA-{i+1000}",
                    "priority": random.choice(["low", "medium", "high"])
                },
                "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 20)),
                "updated_at": datetime.utcnow()
            })
        
        # Apply filters
        filtered = mock_takedowns
        
        if status_filter:
            filtered = [t for t in filtered if t["status"] == status_filter]
        
        if platform:
            filtered = [t for t in filtered if platform.lower() in t["platform"].lower()]
        
        if method:
            filtered = [t for t in filtered if t["method"] == method]
        
        if search:
            filtered = [t for t in filtered if 
                       search.lower() in t["subject"].lower() or 
                       search.lower() in t["recipient_email"].lower()]
        
        # Sort by created_at (newest first)
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
        
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
        # Base query - only takedown requests for user
        query = db.query(TakedownRequest)\
            .filter(TakedownRequest.user_id == current_user.id)\
            .options(joinedload(TakedownRequest.infringement))
        
        # Apply filters
        if status_filter:
            query = query.filter(TakedownRequest.status == status_filter)
        
        if platform:
            query = query.join(Infringement)\
                .filter(Infringement.platform.ilike(f"%{platform}%"))
        
        if method:
            query = query.filter(TakedownRequest.method == method)
        
        if date_from:
            query = query.filter(TakedownRequest.created_at >= date_from)
        
        if date_to:
            query = query.filter(TakedownRequest.created_at <= date_to)
        
        if search:
            query = query.filter(
                or_(
                    TakedownRequest.subject.ilike(f"%{search}%"),
                    TakedownRequest.recipient_email.ilike(f"%{search}%"),
                    TakedownRequest.recipient_name.ilike(f"%{search}%")
                )
            )
        
        # Order by creation date (newest first)
        query = query.order_by(desc(TakedownRequest.created_at))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        takedowns = query.offset(offset).limit(pagination.size).all()
        
        # Calculate pages
        pages = (total + pagination.size - 1) // pagination.size
        
        # Transform to response format
        items = []
        for takedown in takedowns:
            item = TakedownSchema(
                id=takedown.id,
                user_id=takedown.user_id,
                infringement_id=takedown.infringement_id,
                infringement_url=takedown.infringement.url if takedown.infringement else "",
                platform=takedown.infringement.platform if takedown.infringement else "",
                status=takedown.status,
                method=takedown.method,
                recipient_email=takedown.recipient_email,
                recipient_name=takedown.recipient_name,
                subject=takedown.subject,
                body=takedown.body,
                legal_basis=takedown.legal_basis,
                copyright_statement=takedown.copyright_statement,
                good_faith_statement=takedown.good_faith_statement,
                accuracy_statement=takedown.accuracy_statement,
                notes=takedown.notes,
                sent_at=takedown.sent_at,
                acknowledged_at=takedown.acknowledged_at,
                resolved_at=takedown.resolved_at,
                expires_at=takedown.expires_at,
                created_at=takedown.created_at,
                updated_at=takedown.updated_at
            )
            items.append(item)
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )


@router.get("/stats", response_model=TakedownStats)
async def get_takedown_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days for stats"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get takedown statistics."""
    # Base query for user's takedowns
    base_query = db.query(TakedownRequest)\
        .filter(TakedownRequest.user_id == current_user.id)
    
    # Date range for recent requests
    date_from = datetime.utcnow() - timedelta(days=days)
    recent_query = base_query.filter(TakedownRequest.created_at >= date_from)
    
    # Total requests
    total_requests = base_query.count()
    
    # By status
    status_stats = {}
    for status_val in TakedownStatus:
        count = base_query.filter(TakedownRequest.status == status_val).count()
        status_stats[status_val] = count
    
    # By platform
    platform_stats = {}
    platform_counts = base_query.join(Infringement)\
        .with_entities(Infringement.platform, func.count(TakedownRequest.id))\
        .group_by(Infringement.platform).all()
    
    for platform, count in platform_counts:
        platform_stats[platform] = count
    
    # Success rate (content_removed / total_sent)
    successful_requests = base_query.filter(TakedownRequest.status == "content_removed").count()
    sent_requests = base_query.filter(TakedownRequest.sent_at.isnot(None)).count()
    success_rate = (successful_requests / sent_requests * 100) if sent_requests > 0 else 0.0
    
    # Average response time (in hours)
    resolved_requests = base_query.filter(
        and_(
            TakedownRequest.sent_at.isnot(None),
            TakedownRequest.resolved_at.isnot(None)
        )
    ).all()
    
    total_response_time = 0.0
    for request in resolved_requests:
        if request.sent_at and request.resolved_at:
            response_time = (request.resolved_at - request.sent_at).total_seconds() / 3600
            total_response_time += response_time
    
    average_response_time = (total_response_time / len(resolved_requests)) if resolved_requests else 0.0
    
    # Recent requests count
    recent_requests = recent_query.count()
    
    return TakedownStats(
        total_requests=total_requests,
        by_status=status_stats,
        by_platform=platform_stats,
        success_rate=success_rate,
        average_response_time=average_response_time,
        recent_requests=recent_requests
    )


@router.get("/{takedown_id}", response_model=TakedownSchema)
async def get_takedown_request(
    takedown_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed takedown request information."""
    takedown = db.query(TakedownRequest)\
        .filter(
            and_(
                TakedownRequest.id == takedown_id,
                TakedownRequest.user_id == current_user.id
            )
        ).options(joinedload(TakedownRequest.infringement)).first()
    
    if not takedown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Takedown request not found"
        )
    
    return TakedownSchema(
        id=takedown.id,
        user_id=takedown.user_id,
        infringement_id=takedown.infringement_id,
        infringement_url=takedown.infringement.url if takedown.infringement else "",
        platform=takedown.infringement.platform if takedown.infringement else "",
        status=takedown.status,
        method=takedown.method,
        recipient_email=takedown.recipient_email,
        recipient_name=takedown.recipient_name,
        subject=takedown.subject,
        body=takedown.body,
        legal_basis=takedown.legal_basis,
        copyright_statement=takedown.copyright_statement,
        good_faith_statement=takedown.good_faith_statement,
        accuracy_statement=takedown.accuracy_statement,
        notes=takedown.notes,
        sent_at=takedown.sent_at,
        acknowledged_at=takedown.acknowledged_at,
        resolved_at=takedown.resolved_at,
        expires_at=takedown.expires_at,
        created_at=takedown.created_at,
        updated_at=takedown.updated_at
    )


@router.post("", response_model=TakedownSchema, status_code=status.HTTP_201_CREATED)
async def create_takedown_request(
    takedown_data: TakedownRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create new takedown request."""
    # Verify user owns the infringement
    infringement = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id == takedown_data.infringement_id,
                ProtectedProfile.user_id == current_user.id
            )
        ).first()
    
    if not infringement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infringement not found"
        )
    
    # Check if takedown already exists for this infringement
    existing = db.query(TakedownRequest).filter(
        and_(
            TakedownRequest.infringement_id == takedown_data.infringement_id,
            TakedownRequest.status.in_(["draft", "sent", "acknowledged", "compliance_review"])
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active takedown request already exists for this infringement"
        )
    
    # Create takedown request
    takedown = TakedownRequest(
        user_id=current_user.id,
        infringement_id=takedown_data.infringement_id,
        recipient_email=takedown_data.recipient_email,
        recipient_name=takedown_data.recipient_name,
        subject=takedown_data.subject,
        body=takedown_data.body,
        legal_basis=takedown_data.legal_basis,
        copyright_statement=takedown_data.copyright_statement,
        good_faith_statement=takedown_data.good_faith_statement,
        accuracy_statement=takedown_data.accuracy_statement,
        method=takedown_data.method,
        status="draft",
        created_at=datetime.utcnow()
    )
    
    db.add(takedown)
    db.commit()
    db.refresh(takedown)
    
    # If method is email and we have recipient, send immediately
    if takedown.method == "email" and takedown.recipient_email:
        background_tasks.add_task(send_takedown_request, takedown.id)
    
    return TakedownSchema(
        id=takedown.id,
        user_id=takedown.user_id,
        infringement_id=takedown.infringement_id,
        infringement_url=infringement.url,
        platform=infringement.platform,
        status=takedown.status,
        method=takedown.method,
        recipient_email=takedown.recipient_email,
        recipient_name=takedown.recipient_name,
        subject=takedown.subject,
        body=takedown.body,
        legal_basis=takedown.legal_basis,
        copyright_statement=takedown.copyright_statement,
        good_faith_statement=takedown.good_faith_statement,
        accuracy_statement=takedown.accuracy_statement,
        notes=takedown.notes,
        sent_at=takedown.sent_at,
        acknowledged_at=takedown.acknowledged_at,
        resolved_at=takedown.resolved_at,
        expires_at=takedown.expires_at,
        created_at=takedown.created_at,
        updated_at=takedown.updated_at
    )


@router.put("/{takedown_id}", response_model=TakedownSchema)
async def update_takedown_request(
    takedown_id: int,
    takedown_update: TakedownRequestUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update takedown request."""
    takedown = db.query(TakedownRequest)\
        .filter(
            and_(
                TakedownRequest.id == takedown_id,
                TakedownRequest.user_id == current_user.id
            )
        ).first()
    
    if not takedown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Takedown request not found"
        )
    
    # Can only update draft requests
    if takedown.status not in ["draft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft takedown requests"
        )
    
    update_data = takedown_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(takedown, field, value)
    
    takedown.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(takedown)
    
    # Get infringement info for response
    infringement = db.query(Infringement).filter(
        Infringement.id == takedown.infringement_id
    ).first()
    
    return TakedownSchema(
        id=takedown.id,
        user_id=takedown.user_id,
        infringement_id=takedown.infringement_id,
        infringement_url=infringement.url if infringement else "",
        platform=infringement.platform if infringement else "",
        status=takedown.status,
        method=takedown.method,
        recipient_email=takedown.recipient_email,
        recipient_name=takedown.recipient_name,
        subject=takedown.subject,
        body=takedown.body,
        legal_basis=takedown.legal_basis,
        copyright_statement=takedown.copyright_statement,
        good_faith_statement=takedown.good_faith_statement,
        accuracy_statement=takedown.accuracy_statement,
        notes=takedown.notes,
        sent_at=takedown.sent_at,
        acknowledged_at=takedown.acknowledged_at,
        resolved_at=takedown.resolved_at,
        expires_at=takedown.expires_at,
        created_at=takedown.created_at,
        updated_at=takedown.updated_at
    )


@router.post("/{takedown_id}/send", response_model=StatusResponse)
async def send_takedown(
    takedown_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Send takedown request."""
    takedown = db.query(TakedownRequest)\
        .filter(
            and_(
                TakedownRequest.id == takedown_id,
                TakedownRequest.user_id == current_user.id
            )
        ).first()
    
    if not takedown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Takedown request not found"
        )
    
    if takedown.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only send draft takedown requests"
        )
    
    # Validate required fields for sending
    if takedown.method == "email" and not takedown.recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient email is required for email method"
        )
    
    # Send takedown request
    background_tasks.add_task(send_takedown_request, takedown_id)
    
    return StatusResponse(success=True, message="Takedown request scheduled for sending")


@router.post("/bulk", response_model=StatusResponse)
async def create_bulk_takedown_requests(
    bulk_data: BulkTakedownRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create bulk takedown requests."""
    # Verify all infringements belong to user
    infringements = db.query(Infringement)\
        .join(ProtectedProfile)\
        .filter(
            and_(
                Infringement.id.in_(bulk_data.infringement_ids),
                ProtectedProfile.user_id == current_user.id
            )
        ).all()
    
    if len(infringements) != len(bulk_data.infringement_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some infringements not found"
        )
    
    # Get template if specified
    template = None
    if bulk_data.template_id:
        template = db.query(TakedownTemplate).filter(
            and_(
                TakedownTemplate.id == bulk_data.template_id,
                or_(
                    TakedownTemplate.user_id == current_user.id,
                    TakedownTemplate.is_public == True
                )
            )
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
    
    # Create takedown requests
    created_count = 0
    for infringement in infringements:
        # Check if takedown already exists
        existing = db.query(TakedownRequest).filter(
            and_(
                TakedownRequest.infringement_id == infringement.id,
                TakedownRequest.status.in_(["draft", "sent", "acknowledged", "compliance_review"])
            )
        ).first()
        
        if existing:
            continue  # Skip if active takedown exists
        
        # Create takedown request
        takedown = TakedownRequest(
            user_id=current_user.id,
            infringement_id=infringement.id,
            subject=bulk_data.custom_subject or (template.subject_template if template else "DMCA Takedown Notice"),
            body=bulk_data.custom_body or (template.body_template if template else ""),
            legal_basis=template.legal_basis if template else "Copyright infringement",
            copyright_statement=template.copyright_statement if template else "",
            good_faith_statement=template.good_faith_statement if template else "",
            accuracy_statement=template.accuracy_statement if template else "",
            method="email",
            status="draft",
            created_at=datetime.utcnow()
        )
        
        db.add(takedown)
        created_count += 1
    
    db.commit()
    
    # Schedule sending based on priority
    if bulk_data.priority == "high":
        background_tasks.add_task(process_bulk_takedowns, current_user.id, "high")
    
    return StatusResponse(
        success=True, 
        message=f"Created {created_count} takedown requests"
    )


@router.delete("/{takedown_id}", response_model=StatusResponse)
async def cancel_takedown_request(
    takedown_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Cancel/withdraw takedown request."""
    takedown = db.query(TakedownRequest)\
        .filter(
            and_(
                TakedownRequest.id == takedown_id,
                TakedownRequest.user_id == current_user.id
            )
        ).first()
    
    if not takedown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Takedown request not found"
        )
    
    if takedown.status in ["content_removed", "rejected", "expired", "withdrawn"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel takedown request in current status"
        )
    
    if takedown.status == "draft":
        # Delete draft requests
        db.delete(takedown)
    else:
        # Mark as withdrawn for sent requests
        takedown.status = "withdrawn"
        takedown.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return StatusResponse(success=True, message="Takedown request cancelled")


# Template management
@router.get("/templates", response_model=List[TakedownTemplate])
async def get_takedown_templates(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's takedown templates."""
    templates = db.query(TakedownTemplate)\
        .filter(
            or_(
                TakedownTemplate.user_id == current_user.id,
                TakedownTemplate.is_public == True
            )
        ).all()
    
    return templates


@router.post("/templates", response_model=TakedownTemplate, status_code=status.HTTP_201_CREATED)
async def create_takedown_template(
    template_data: TakedownTemplateCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create takedown template."""
    template = TakedownTemplate(
        user_id=current_user.id,
        **template_data.dict(),
        created_at=datetime.utcnow()
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


async def send_takedown_request(takedown_id: int):
    """Send takedown request via email (background task)."""
    from app.services.takedown.sender import send_takedown_email
    await send_takedown_email(takedown_id)


async def process_bulk_takedowns(user_id: int, priority: str):
    """Process bulk takedown requests (background task)."""
    from app.services.takedown.bulk_processor import process_bulk_takedowns_for_user
    await process_bulk_takedowns_for_user(user_id, priority)