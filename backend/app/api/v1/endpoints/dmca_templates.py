from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.schemas.dmca_template import (
    DMCATemplate,
    DMCATemplateCreate,
    DMCATemplateUpdate,
    DMCATemplateListItem,
    TemplateCategory,
    TemplateCategoryCreate,
    TemplateCategoryUpdate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateUsageStats,
    TemplateType,
    TemplateVariables
)
from app.schemas.common import PaginatedResponse, StatusResponse, MessageResponse
from app.api.deps.auth import get_current_active_user, get_current_superuser
from app.api.deps.common import get_pagination_params, PaginationParams
from app.services.dmca_template_service import DMCATemplateService, TemplateCategoryService

router = APIRouter()


# DMCA Template Endpoints
@router.get("", response_model=PaginatedResponse)
async def get_templates(
    pagination: PaginationParams = Depends(get_pagination_params),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    template_type: Optional[TemplateType] = Query(None, description="Filter by template type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, description, or content"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get templates with filtering and pagination."""
    
    # Get templates
    templates = DMCATemplateService.get_templates(
        db=db,
        skip=(pagination.page - 1) * pagination.size,
        limit=pagination.size,
        category_id=category_id,
        template_type=template_type,
        is_active=is_active,
        search=search
    )
    
    # Get total count
    total = DMCATemplateService.count_templates(
        db=db,
        category_id=category_id,
        template_type=template_type,
        is_active=is_active,
        search=search
    )
    
    # Calculate pages
    pages = (total + pagination.size - 1) // pagination.size
    
    # Convert to list items with category names
    items = []
    for template in templates:
        template_dict = template.__dict__.copy()
        template_dict['category_name'] = template.category.name if template.category else None
        items.append(DMCATemplateListItem.from_orm(template))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages
    )


@router.get("/default", response_model=List[DMCATemplate])
async def get_default_templates(
    template_type: Optional[TemplateType] = Query(None, description="Filter by template type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get default templates."""
    templates = DMCATemplateService.get_default_templates(db=db, template_type=template_type)
    return [DMCATemplate.from_orm(template) for template in templates]


@router.get("/{template_id}", response_model=DMCATemplate)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get template by ID."""
    template = DMCATemplateService.get_template(db=db, template_id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return DMCATemplate.from_orm(template)


@router.post("", response_model=DMCATemplate)
async def create_template(
    template: DMCATemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create new DMCA template."""
    
    # Check if category exists if provided
    if template.category_id:
        category = TemplateCategoryService.get_category(db=db, category_id=template.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Create template
    db_template = DMCATemplateService.create_template(db=db, template=template)
    
    return DMCATemplate.from_orm(db_template)


@router.put("/{template_id}", response_model=DMCATemplate)
async def update_template(
    template_id: int,
    template_update: DMCATemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update DMCA template."""
    
    # Check if category exists if provided
    if template_update.category_id:
        category = TemplateCategoryService.get_category(db=db, category_id=template_update.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Update template
    db_template = DMCATemplateService.update_template(
        db=db, 
        template_id=template_id, 
        template_update=template_update
    )
    
    if not db_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return DMCATemplate.from_orm(db_template)


@router.delete("/{template_id}", response_model=StatusResponse)
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete DMCA template (soft delete)."""
    
    success = DMCATemplateService.delete_template(db=db, template_id=template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return StatusResponse(success=True, message="Template deactivated successfully")


@router.post("/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    preview_request: TemplatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Preview template with variable substitution."""
    
    preview = DMCATemplateService.preview_template(
        db=db,
        template_id=preview_request.template_id,
        variables=preview_request.variables
    )
    
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return preview


@router.post("/{template_id}/use", response_model=MessageResponse)
async def use_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Mark template as used (increment usage count)."""
    
    success = DMCATemplateService.increment_usage(db=db, template_id=template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return MessageResponse(message="Template usage recorded")


# Template Category Endpoints
@router.get("/categories", response_model=List[TemplateCategory])
async def get_categories(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all template categories."""
    
    categories = TemplateCategoryService.get_categories(
        db=db,
        is_active=is_active
    )
    
    # Add template count to each category
    result = []
    for category in categories:
        category_dict = category.__dict__.copy()
        category_dict['template_count'] = len([t for t in category.templates if t.is_active])
        result.append(TemplateCategory.from_orm(category))
    
    return result


@router.get("/categories/{category_id}", response_model=TemplateCategory)
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get category by ID."""
    
    category_data = TemplateCategoryService.get_category_with_template_count(
        db=db, 
        category_id=category_id
    )
    
    if not category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    category_dict = category_data["category"].__dict__.copy()
    category_dict['template_count'] = category_data["template_count"]
    
    return TemplateCategory.from_orm(category_data["category"])


@router.post("/categories", response_model=TemplateCategory)
async def create_category(
    category: TemplateCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create new template category."""
    
    db_category = TemplateCategoryService.create_category(db=db, category=category)
    
    return TemplateCategory.from_orm(db_category)


@router.put("/categories/{category_id}", response_model=TemplateCategory)
async def update_category(
    category_id: int,
    category_update: TemplateCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update template category."""
    
    db_category = TemplateCategoryService.update_category(
        db=db,
        category_id=category_id,
        category_update=category_update
    )
    
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return TemplateCategory.from_orm(db_category)


@router.delete("/categories/{category_id}", response_model=StatusResponse)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete template category."""
    
    success = TemplateCategoryService.delete_category(db=db, category_id=category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return StatusResponse(success=True, message="Category deleted successfully")


# Statistics and Analytics
@router.get("/stats/usage", response_model=List[TemplateUsageStats])
async def get_template_usage_stats(
    limit: int = Query(10, ge=1, le=100, description="Number of top templates to return"),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """Get template usage statistics (admin only)."""
    
    # Get top used templates
    templates = DMCATemplateService.get_templates(
        db=db,
        skip=0,
        limit=limit,
        is_active=True
    )
    
    stats = []
    for template in templates:
        stats.append(TemplateUsageStats(
            template_id=template.id,
            template_name=template.name,
            usage_count=template.usage_count,
            success_rate=None,  # Would need additional data tracking
            avg_response_time=None,  # Would need additional data tracking
            last_used=None  # Would need additional data tracking
        ))
    
    return stats


# Mock endpoints for development
@router.get("/mock", response_model=List[DMCATemplateListItem])
async def get_mock_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get mock templates for development."""
    from datetime import datetime
    
    mock_templates = [
        DMCATemplateListItem(
            id=1,
            name="Standard Copyright Notice",
            description="Standard DMCA takedown notice for copyright infringement",
            template_type=TemplateType.COPYRIGHT,
            category_id=1,
            is_default=True,
            is_active=True,
            usage_count=150,
            created_at=datetime.utcnow(),
            category_name="Copyright"
        ),
        DMCATemplateListItem(
            id=2,
            name="Trademark Infringement Notice",
            description="DMCA notice specifically for trademark violations",
            template_type=TemplateType.TRADEMARK,
            category_id=2,
            is_default=True,
            is_active=True,
            usage_count=89,
            created_at=datetime.utcnow(),
            category_name="Trademark"
        ),
        DMCATemplateListItem(
            id=3,
            name="Social Media Content Takedown",
            description="Template optimized for social media platform takedowns",
            template_type=TemplateType.STANDARD,
            category_id=3,
            is_default=False,
            is_active=True,
            usage_count=45,
            created_at=datetime.utcnow(),
            category_name="Social Media"
        )
    ]
    
    return mock_templates


@router.get("/mock/categories", response_model=List[TemplateCategory])
async def get_mock_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get mock categories for development."""
    from datetime import datetime
    
    mock_categories = [
        TemplateCategory(
            id=1,
            name="Copyright",
            description="Templates for copyright infringement notices",
            display_order=1,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=None,
            template_count=5
        ),
        TemplateCategory(
            id=2,
            name="Trademark",
            description="Templates for trademark violation notices",
            display_order=2,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=None,
            template_count=3
        ),
        TemplateCategory(
            id=3,
            name="Social Media",
            description="Templates optimized for social media platforms",
            display_order=3,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=None,
            template_count=2
        )
    ]
    
    return mock_categories