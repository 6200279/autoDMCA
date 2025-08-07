from typing import Optional
from fastapi import Query, HTTPException, status
from sqlalchemy import asc, desc

from app.schemas.common import PaginationParams


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """Get pagination parameters."""
    return PaginationParams(page=page, size=size)


def get_sort_params(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order")
):
    """Get sorting parameters."""
    if sort_by and sort_order:
        return sort_order, sort_by
    return None, None


def validate_owner_access(resource_user_id: int, current_user_id: int, is_superuser: bool = False):
    """Validate that user can access resource."""
    if not is_superuser and resource_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this resource"
        )


def apply_sorting(query, sort_field: str, sort_order: str, model_class):
    """Apply sorting to query."""
    if hasattr(model_class, sort_field):
        field = getattr(model_class, sort_field)
        if sort_order == "desc":
            return query.order_by(desc(field))
        else:
            return query.order_by(asc(field))
    return query