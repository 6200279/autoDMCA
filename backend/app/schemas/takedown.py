from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, HttpUrl
from .common import BaseSchema


class TakedownStatus(str, Enum):
    """Takedown request status enum."""
    DRAFT = "draft"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLIANCE_REVIEW = "compliance_review"
    CONTENT_REMOVED = "content_removed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class TakedownMethod(str, Enum):
    """Takedown request method enum."""
    EMAIL = "email"
    WEBFORM = "webform"
    API = "api"
    MANUAL = "manual"


class TakedownRequestBase(BaseModel):
    """Base takedown request schema."""
    infringement_id: int
    recipient_email: Optional[EmailStr] = None
    recipient_name: Optional[str] = None
    subject: str
    body: str
    legal_basis: str
    copyright_statement: str
    good_faith_statement: str
    accuracy_statement: str
    method: TakedownMethod = TakedownMethod.EMAIL


class TakedownRequestCreate(TakedownRequestBase):
    """Takedown request creation schema."""
    pass


class TakedownRequestUpdate(BaseModel):
    """Takedown request update schema."""
    status: Optional[TakedownStatus] = None
    recipient_email: Optional[EmailStr] = None
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    legal_basis: Optional[str] = None
    notes: Optional[str] = None


class TakedownRequest(BaseSchema):
    """Takedown request response schema."""
    id: int
    user_id: int
    infringement_id: int
    infringement_url: str
    platform: str
    status: TakedownStatus
    method: TakedownMethod
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    subject: str
    body: str
    legal_basis: str
    copyright_statement: str
    good_faith_statement: str
    accuracy_statement: str
    notes: Optional[str]
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class TakedownTemplate(BaseSchema):
    """Takedown template schema."""
    id: int
    user_id: Optional[int]
    name: str
    description: Optional[str]
    subject_template: str
    body_template: str
    legal_basis: str
    copyright_statement: str
    good_faith_statement: str
    accuracy_statement: str
    is_default: bool
    is_public: bool
    created_at: datetime


class TakedownTemplateCreate(BaseModel):
    """Takedown template creation schema."""
    name: str
    description: Optional[str] = None
    subject_template: str
    body_template: str
    legal_basis: str
    copyright_statement: str
    good_faith_statement: str
    accuracy_statement: str
    is_default: bool = False


class TakedownTemplateUpdate(BaseModel):
    """Takedown template update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    legal_basis: Optional[str] = None
    copyright_statement: Optional[str] = None
    good_faith_statement: Optional[str] = None
    accuracy_statement: Optional[str] = None
    is_default: Optional[bool] = None


class TakedownResponse(BaseSchema):
    """Takedown response schema."""
    id: int
    takedown_request_id: int
    responder_email: Optional[str]
    responder_name: Optional[str]
    response_type: str  # compliance, rejection, counter_notice
    response_text: str
    attachments: Optional[List[str]]
    received_at: datetime


class CounterNotice(BaseSchema):
    """Counter notice schema."""
    id: int
    takedown_request_id: int
    claimant_name: str
    claimant_email: EmailStr
    claimant_address: str
    identification_statement: str
    good_faith_statement: str
    accuracy_statement: str
    consent_statement: str
    signature: str
    received_at: datetime


class TakedownStats(BaseSchema):
    """Takedown statistics schema."""
    total_requests: int
    by_status: Dict[str, int]
    by_platform: Dict[str, int]
    success_rate: float
    average_response_time: float  # in hours
    recent_requests: int


class BulkTakedownRequest(BaseModel):
    """Bulk takedown request schema."""
    infringement_ids: List[int]
    template_id: Optional[int] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    priority: str = "normal"  # low, normal, high


class TakedownFilter(BaseModel):
    """Takedown filter schema."""
    status: Optional[TakedownStatus] = None
    platform: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    method: Optional[TakedownMethod] = None