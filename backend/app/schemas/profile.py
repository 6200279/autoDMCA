from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from .common import BaseSchema


class ProtectedProfileBase(BaseModel):
    """Base protected profile schema."""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    stage_name: Optional[str] = Field(None, max_length=255)
    real_name: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[datetime] = None
    social_media_handles: Optional[dict] = None
    website_urls: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    aliases: Optional[List[str]] = None


class ProtectedProfileCreate(ProtectedProfileBase):
    """Protected profile creation schema."""
    pass


class ProtectedProfileUpdate(BaseModel):
    """Protected profile update schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    stage_name: Optional[str] = Field(None, max_length=255)
    real_name: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[datetime] = None
    social_media_handles: Optional[dict] = None
    website_urls: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ProtectedProfile(BaseSchema):
    """Protected profile response schema."""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    stage_name: Optional[str]
    real_name: Optional[str]
    date_of_birth: Optional[datetime]
    social_media_handles: Optional[dict]
    website_urls: Optional[List[str]]
    keywords: Optional[List[str]]
    aliases: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class ProfileStats(BaseSchema):
    """Profile statistics schema."""
    profile_id: int
    total_scans: int
    active_infringements: int
    resolved_infringements: int
    pending_takedowns: int
    successful_takedowns: int
    last_scan: Optional[datetime]
    protection_score: float  # 0-100


class ReferenceImage(BaseSchema):
    """Reference image schema."""
    id: int
    profile_id: int
    filename: str
    url: str
    image_hash: str
    face_encoding: Optional[str]
    is_primary: bool
    created_at: datetime


class ReferenceImageCreate(BaseModel):
    """Reference image creation schema."""
    profile_id: int
    is_primary: bool = False


class ReferenceImageUpdate(BaseModel):
    """Reference image update schema."""
    is_primary: Optional[bool] = None


class ProfileWithStats(ProtectedProfile):
    """Protected profile with statistics."""
    stats: ProfileStats
    reference_images_count: int
    recent_infringements_count: int