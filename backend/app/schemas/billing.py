from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, validator
from decimal import Decimal
from .common import BaseSchema


class SubscriptionPlan(str, Enum):
    """Subscription plan enum."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class BillingInterval(str, Enum):
    """Billing interval enum."""
    MONTH = "month"
    YEAR = "year"


class InvoiceStatus(str, Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    CANCELED = "canceled"
    REQUIRES_ACTION = "requires_action"


# Subscription Schemas

class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    plan: SubscriptionPlan
    interval: BillingInterval = BillingInterval.MONTH


class SubscriptionCreate(SubscriptionBase):
    """Subscription creation schema."""
    payment_method_id: Optional[str] = None
    trial_days: Optional[int] = None
    
    @validator('trial_days')
    def validate_trial_days(cls, v):
        if v is not None and (v < 0 or v > 30):
            raise ValueError('Trial days must be between 0 and 30')
        return v


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    plan: Optional[SubscriptionPlan] = None
    interval: Optional[BillingInterval] = None


class SubscriptionCancel(BaseModel):
    """Subscription cancellation schema."""
    at_period_end: bool = True
    cancellation_reason: Optional[str] = None


class SubscriptionResponse(BaseSchema):
    """Subscription response schema."""
    id: int
    user_id: int
    plan: SubscriptionPlan
    status: SubscriptionStatus
    interval: BillingInterval
    amount: Decimal
    currency: str
    
    # Stripe data
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    stripe_price_id: Optional[str]
    
    # Dates
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]
    ends_at: Optional[datetime]
    
    # Limits
    max_protected_profiles: int
    max_monthly_scans: int
    max_takedown_requests: int
    
    # Features
    ai_face_recognition: bool
    priority_support: bool
    custom_branding: bool
    api_access: bool
    
    # Metadata
    previous_plan: Optional[SubscriptionPlan]
    next_plan: Optional[SubscriptionPlan]
    plan_change_at: Optional[datetime]
    
    created_at: datetime
    updated_at: Optional[datetime]


class PlanFeatures(BaseModel):
    """Plan features schema."""
    plan: SubscriptionPlan
    name: str
    description: str
    
    # Pricing
    monthly_price: Decimal
    yearly_price: Decimal
    yearly_discount: Decimal  # Percentage discount for yearly billing
    
    # Limits
    max_protected_profiles: int
    max_monthly_scans: int
    max_takedown_requests: int
    
    # Features
    ai_face_recognition: bool
    priority_support: bool
    custom_branding: bool
    api_access: bool
    
    # Additional features
    bulk_operations: bool = False
    advanced_analytics: bool = False
    custom_templates: bool = False
    whitelabeling: bool = False


# Payment Method Schemas

class BillingAddress(BaseModel):
    """Billing address schema."""
    company: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    
    # Tax information
    tax_id: Optional[str] = None
    tax_id_type: Optional[str] = None


class PaymentMethodCreate(BaseModel):
    """Payment method creation schema."""
    payment_method_id: str
    billing_address: Optional[BillingAddress] = None
    set_as_default: bool = False


class PaymentMethodResponse(BaseSchema):
    """Payment method response schema."""
    id: int
    user_id: int
    stripe_payment_method_id: str
    type: str
    is_default: bool
    is_active: bool
    
    # Card details
    card_brand: Optional[str]
    card_last4: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    
    # Bank details
    bank_name: Optional[str]
    bank_last4: Optional[str]
    
    created_at: datetime
    updated_at: Optional[datetime]


class SetupIntentCreate(BaseModel):
    """Setup intent creation schema."""
    usage: str = "off_session"  # or "on_session"


class SetupIntentResponse(BaseModel):
    """Setup intent response schema."""
    client_secret: str
    setup_intent_id: str
    customer_id: str


# Invoice Schemas

class InvoiceLineItemResponse(BaseSchema):
    """Invoice line item response schema."""
    id: int
    description: str
    quantity: int
    unit_amount: Decimal
    amount: Decimal
    currency: str
    stripe_price_id: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]


class InvoiceResponse(BaseSchema):
    """Invoice response schema."""
    id: int
    subscription_id: int
    user_id: int
    
    # Stripe data
    stripe_invoice_id: str
    stripe_payment_intent_id: Optional[str]
    
    # Invoice details
    invoice_number: Optional[str]
    status: InvoiceStatus
    
    # Financial details
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    
    # Dates
    invoice_date: datetime
    due_date: Optional[datetime]
    period_start: datetime
    period_end: datetime
    paid_at: Optional[datetime]
    
    # URLs
    invoice_pdf_url: Optional[str]
    hosted_invoice_url: Optional[str]
    
    # Metadata
    description: Optional[str]
    
    # Line items
    line_items: List[InvoiceLineItemResponse] = []
    
    created_at: datetime
    updated_at: Optional[datetime]


class InvoiceListResponse(BaseModel):
    """Invoice list response schema."""
    invoices: List[InvoiceResponse]
    total_count: int
    has_more: bool


# Usage Schemas

class UsageRecord(BaseSchema):
    """Usage record schema."""
    id: int
    subscription_id: int
    user_id: int
    metric: str
    quantity: int
    period_start: datetime
    period_end: datetime
    created_at: datetime


class CurrentUsage(BaseModel):
    """Current usage schema."""
    protected_profiles: int
    monthly_scans: int
    takedown_requests: int
    period_start: str
    period_end: str


class UsageLimits(BaseModel):
    """Usage limits schema."""
    max_protected_profiles: int
    max_monthly_scans: int
    max_takedown_requests: int


class UsageAnalytics(BaseModel):
    """Usage analytics schema."""
    period: Dict[str, Any]
    metrics: Dict[str, List[Dict[str, Any]]]
    trends: Dict[str, Dict[str, Any]]
    total_usage: Dict[str, int]


class UsageLimitCheck(BaseModel):
    """Usage limit check response."""
    allowed: bool
    reason: Optional[str] = None
    current_usage: int
    limit: int
    remaining: int


# Billing Dashboard Schemas

class BillingDashboard(BaseModel):
    """Billing dashboard schema."""
    subscription: Optional[SubscriptionResponse]
    current_usage: CurrentUsage
    usage_limits: UsageLimits
    upcoming_invoice: Optional[InvoiceResponse]
    payment_methods: List[PaymentMethodResponse]
    billing_address: Optional[BillingAddress]
    recent_invoices: List[InvoiceResponse]


# Webhook Schemas

class WebhookEventCreate(BaseModel):
    """Webhook event creation schema."""
    type: str
    data: Dict[str, Any]
    
    
class WebhookEventResponse(BaseModel):
    """Webhook event response schema."""
    processed: bool
    message: str


# Stripe Integration Schemas

class StripeCustomerCreate(BaseModel):
    """Stripe customer creation schema."""
    email: str
    name: str
    metadata: Optional[Dict[str, str]] = None


class StripeSubscriptionCreate(BaseModel):
    """Stripe subscription creation schema."""
    customer_id: str
    price_id: str
    payment_method_id: Optional[str] = None
    trial_period_days: Optional[int] = None


class StripePriceResponse(BaseModel):
    """Stripe price response schema."""
    id: str
    object: str
    active: bool
    currency: str
    unit_amount: int
    recurring: Dict[str, Any]
    product: str


class StripeProductResponse(BaseModel):
    """Stripe product response schema."""
    id: str
    object: str
    active: bool
    name: str
    description: Optional[str]
    metadata: Dict[str, str]