from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: list
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class StatusResponse(BaseModel):
    """Generic status response."""
    success: bool
    message: Optional[str] = None