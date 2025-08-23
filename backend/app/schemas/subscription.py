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


class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    plan: SubscriptionPlan
    billing_interval: BillingInterval = BillingInterval.MONTH


class SubscriptionCreate(SubscriptionBase):
    """Subscription creation schema."""
    payment_method_id: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    plan: Optional[SubscriptionPlan] = None
    billing_interval: Optional[BillingInterval] = None
    auto_renew: Optional[bool] = None


class Subscription(BaseSchema):
    """Subscription response schema."""
    id: int
    user_id: int
    plan: SubscriptionPlan
    status: SubscriptionStatus
    billing_interval: BillingInterval
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]
    auto_renew: bool
    created_at: datetime
    updated_at: Optional[datetime]


class PlanFeatures(BaseSchema):
    """Plan features schema."""
    plan: SubscriptionPlan
    max_profiles: int
    max_scans_per_month: int
    max_takedowns_per_month: int
    api_access: bool
    priority_support: bool
    bulk_operations: bool
    advanced_analytics: bool
    custom_templates: bool
    whitelabeling: bool
    monthly_price: Decimal
    yearly_price: Decimal


class UsageStats(BaseSchema):
    """Usage statistics schema."""
    subscription_id: int
    current_period_start: datetime
    current_period_end: datetime
    profiles_used: int
    scans_used: int
    takedowns_used: int
    storage_used: int  # in MB
    api_calls_used: int


class Invoice(BaseSchema):
    """Invoice schema."""
    id: str
    subscription_id: int
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    invoice_url: Optional[str]


class PaymentMethod(BaseSchema):
    """Payment method schema."""
    id: str
    user_id: int
    type: str  # card, bank_account, paypal
    last4: Optional[str]
    brand: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    is_default: bool
    created_at: datetime


class BillingAddress(BaseModel):
    """Billing address schema."""
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str


class PaymentMethodCreate(BaseModel):
    """Payment method creation schema."""
    payment_method_id: str
    billing_address: BillingAddress
    is_default: bool = False


class SubscriptionChange(BaseSchema):
    """Subscription change log schema."""
    id: int
    subscription_id: int
    from_plan: SubscriptionPlan
    to_plan: SubscriptionPlan
    change_type: str  # upgrade, downgrade, cancel, reactivate
    proration_amount: Optional[Decimal]
    effective_date: datetime
    created_at: datetime