from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from .common import BaseSchema


class TemplateType(str, Enum):
    STANDARD = "standard"
    COPYRIGHT = "copyright"
    TRADEMARK = "trademark"
    CUSTOM = "custom"


# Template Category Schemas
class TemplateCategoryBase(BaseModel):
    """Base template category schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class TemplateCategoryCreate(TemplateCategoryBase):
    """Template category creation schema."""
    pass


class TemplateCategoryUpdate(BaseModel):
    """Template category update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class TemplateCategory(BaseSchema):
    """Template category response schema."""
    id: int
    name: str
    description: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Computed fields
    template_count: Optional[int] = 0


# DMCA Template Schemas
class DMCATemplateBase(BaseModel):
    """Base DMCA template schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_type: TemplateType = TemplateType.STANDARD
    subject_template: str = Field(..., min_length=1, max_length=500)
    body_template: str = Field(..., min_length=1)
    category_id: Optional[int] = None
    is_default: bool = False
    is_active: bool = True
    requires_signature: bool = True
    requires_sworn_statement: bool = True
    requires_contact_info: bool = True
    available_variables: Optional[str] = None


class DMCATemplateCreate(DMCATemplateBase):
    """DMCA template creation schema."""
    
    @validator('subject_template', 'body_template')
    def validate_template_syntax(cls, v):
        """Validate that template contains valid placeholder syntax."""
        if not v or not v.strip():
            raise ValueError("Template content cannot be empty")
        return v.strip()


class DMCATemplateUpdate(BaseModel):
    """DMCA template update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    template_type: Optional[TemplateType] = None
    subject_template: Optional[str] = Field(None, min_length=1, max_length=500)
    body_template: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    requires_signature: Optional[bool] = None
    requires_sworn_statement: Optional[bool] = None
    requires_contact_info: Optional[bool] = None
    available_variables: Optional[str] = None
    
    @validator('subject_template', 'body_template')
    def validate_template_syntax(cls, v):
        """Validate that template contains valid placeholder syntax."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Template content cannot be empty")
        return v.strip() if v else v


class DMCATemplate(BaseSchema):
    """DMCA template response schema."""
    id: int
    name: str
    description: Optional[str]
    template_type: TemplateType
    subject_template: str
    body_template: str
    category_id: Optional[int]
    is_default: bool
    is_active: bool
    usage_count: int
    requires_signature: bool
    requires_sworn_statement: bool
    requires_contact_info: bool
    available_variables: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Related data
    category: Optional[TemplateCategory] = None


class DMCATemplateListItem(BaseSchema):
    """Simplified DMCA template for list views."""
    id: int
    name: str
    description: Optional[str]
    template_type: TemplateType
    category_id: Optional[int]
    is_default: bool
    is_active: bool
    usage_count: int
    created_at: datetime
    
    # Related data
    category_name: Optional[str] = None


# Template Preview and Rendering
class TemplateVariables(BaseModel):
    """Template variables for preview/rendering."""
    infringer_name: Optional[str] = "John Doe"
    infringer_email: Optional[str] = "john@example.com"
    infringing_url: Optional[str] = "https://example.com/infringing-content"
    original_work_title: Optional[str] = "My Original Work"
    original_work_url: Optional[str] = "https://mysite.com/original"
    copyright_holder: Optional[str] = "Jane Smith"
    contact_email: Optional[str] = "legal@mycompany.com"
    contact_phone: Optional[str] = "+1-555-0123"
    date: Optional[str] = "2024-01-01"
    additional_info: Optional[str] = ""


class TemplatePreviewRequest(BaseModel):
    """Request for template preview."""
    template_id: int
    variables: Optional[TemplateVariables] = None


class TemplatePreviewResponse(BaseModel):
    """Template preview response."""
    subject: str
    body: str
    html_body: Optional[str] = None
    missing_variables: List[str] = []


# Template Statistics
class TemplateUsageStats(BaseModel):
    """Template usage statistics."""
    template_id: int
    template_name: str
    usage_count: int
    success_rate: Optional[float] = None  # Percentage of successful takedowns using this template
    avg_response_time: Optional[float] = None  # Average response time in hours
    last_used: Optional[datetime] = None