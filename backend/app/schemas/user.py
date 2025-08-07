from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from .common import BaseSchema


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class User(BaseSchema):
    """User response schema."""
    id: int
    email: EmailStr
    full_name: str
    company: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]


class UserProfile(User):
    """Extended user profile with subscription info."""
    subscription_plan: Optional[str]
    subscription_status: Optional[str]
    profiles_count: int
    infringements_count: int
    takedowns_count: int


class UserSettings(BaseModel):
    """User settings schema."""
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    weekly_reports: bool = True
    monthly_reports: bool = True
    auto_takedown: bool = False
    scan_frequency: str = "daily"  # daily, weekly, monthly
    language: str = "en"
    timezone: str = "UTC"


class UserSettingsUpdate(BaseModel):
    """User settings update schema."""
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    weekly_reports: Optional[bool] = None
    monthly_reports: Optional[bool] = None
    auto_takedown: Optional[bool] = None
    scan_frequency: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class UserActivity(BaseSchema):
    """User activity log entry."""
    id: int
    user_id: int
    action: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime