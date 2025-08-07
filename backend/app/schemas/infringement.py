from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field
from .common import BaseSchema


class InfringementStatus(str, Enum):
    """Infringement status enum."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    TAKEDOWN_REQUESTED = "takedown_requested"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class InfringementSeverity(str, Enum):
    """Infringement severity enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InfringementType(str, Enum):
    """Infringement type enum."""
    IMAGE = "image"
    VIDEO = "video"
    PROFILE = "profile"
    CONTENT = "content"
    DEEPFAKE = "deepfake"


class InfringementBase(BaseModel):
    """Base infringement schema."""
    profile_id: int
    url: HttpUrl
    platform: str = Field(..., max_length=100)
    infringement_type: InfringementType
    severity: InfringementSeverity = InfringementSeverity.MEDIUM
    confidence_score: float = Field(..., ge=0, le=1)
    description: Optional[str] = None
    evidence_urls: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class InfringementCreate(InfringementBase):
    """Infringement creation schema."""
    pass


class ManualInfringementCreate(BaseModel):
    """Manual infringement submission schema."""
    profile_id: int
    url: HttpUrl
    platform: str = Field(..., max_length=100)
    infringement_type: InfringementType
    description: str = Field(..., min_length=10)
    evidence_urls: Optional[List[str]] = None


class InfringementUpdate(BaseModel):
    """Infringement update schema."""
    status: Optional[InfringementStatus] = None
    severity: Optional[InfringementSeverity] = None
    description: Optional[str] = None
    evidence_urls: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class Infringement(BaseSchema):
    """Infringement response schema."""
    id: int
    profile_id: int
    profile_name: str
    reporter_id: Optional[int]
    url: str
    platform: str
    infringement_type: InfringementType
    status: InfringementStatus
    severity: InfringementSeverity
    confidence_score: float
    description: Optional[str]
    evidence_urls: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    notes: Optional[str]
    discovered_at: datetime
    updated_at: Optional[datetime]


class InfringementDetail(Infringement):
    """Detailed infringement with related data."""
    takedown_requests: List[Dict[str, Any]]
    similar_infringements: List[Dict[str, Any]]
    scan_results: Optional[Dict[str, Any]]


class InfringementFilter(BaseModel):
    """Infringement filter schema."""
    profile_id: Optional[int] = None
    platform: Optional[str] = None
    status: Optional[InfringementStatus] = None
    severity: Optional[InfringementSeverity] = None
    infringement_type: Optional[InfringementType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)


class InfringementStats(BaseSchema):
    """Infringement statistics schema."""
    total_infringements: int
    by_status: Dict[str, int]
    by_platform: Dict[str, int]
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    recent_count: int
    resolved_count: int
    success_rate: float


class BulkInfringementAction(BaseModel):
    """Bulk infringement action schema."""
    infringement_ids: List[int]
    action: str  # "mark_resolved", "request_takedown", "mark_false_positive"
    notes: Optional[str] = None


class ScanRequest(BaseModel):
    """Scan request schema."""
    profile_id: int
    platforms: Optional[List[str]] = None
    scan_type: str = "comprehensive"  # quick, comprehensive, deep
    priority: str = "normal"  # low, normal, high


class ScanResult(BaseSchema):
    """Scan result schema."""
    id: int
    profile_id: int
    scan_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    infringements_found: int
    platforms_scanned: List[str]
    metadata: Optional[Dict[str, Any]]