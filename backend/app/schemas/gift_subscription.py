from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

from app.db.models.gift_subscription import GiftStatus, GiftTransactionStatus
from app.db.models.subscription import SubscriptionPlan, BillingInterval


# ========== REQUEST SCHEMAS ==========

class GiftPurchaseRequest(BaseModel):
    """Request schema for purchasing a gift subscription."""
    recipient_email: EmailStr = Field(..., description="Email address of the gift recipient")
    recipient_name: Optional[str] = Field(None, max_length=255, description="Name of the gift recipient")
    plan: SubscriptionPlan = Field(..., description="Subscription plan to gift")
    billing_interval: BillingInterval = Field(..., description="Billing interval for the gift")
    personal_message: Optional[str] = Field(None, max_length=1000, description="Personal message for the recipient")
    custom_sender_name: Optional[str] = Field(None, max_length=255, description="Custom sender name to display")
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")
    use_checkout: bool = Field(default=False, description="Use Stripe Checkout instead of Payment Intent")
    success_url: Optional[str] = Field(None, description="Success URL for Stripe Checkout")
    cancel_url: Optional[str] = Field(None, description="Cancel URL for Stripe Checkout")
    
    @validator('personal_message')
    def validate_personal_message(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v
    
    @validator('custom_sender_name')
    def validate_custom_sender_name(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v


class GiftRedemptionRequest(BaseModel):
    """Request schema for redeeming a gift subscription."""
    gift_code: str = Field(..., min_length=16, max_length=32, description="Gift redemption code")
    recipient_email: Optional[EmailStr] = Field(None, description="Email address to verify redemption eligibility")
    
    @validator('gift_code')
    def validate_gift_code(cls, v):
        # Remove whitespace and normalize
        cleaned = ''.join(v.split()).upper()
        return cleaned


class GiftStatusRequest(BaseModel):
    """Request schema for checking gift status."""
    gift_code: str = Field(..., min_length=16, max_length=32, description="Gift code to check")
    
    @validator('gift_code')
    def validate_gift_code(cls, v):
        cleaned = ''.join(v.split()).upper()
        return cleaned


class GiftRefundRequest(BaseModel):
    """Request schema for refunding a gift subscription."""
    gift_id: int = Field(..., description="Gift subscription ID")
    reason: Optional[str] = Field("requested_by_customer", description="Reason for refund")
    amount: Optional[int] = Field(None, description="Partial refund amount in cents")


# ========== RESPONSE SCHEMAS ==========

class GiftCodeInfo(BaseModel):
    """Basic gift code information."""
    code: str
    is_active: bool
    redemption_attempts: int
    max_redemptions: int
    current_redemptions: int
    created_at: datetime


class GiftTransactionInfo(BaseModel):
    """Gift transaction information."""
    id: int
    stripe_payment_intent_id: str
    amount: Decimal
    currency: str
    status: GiftTransactionStatus
    payment_method_type: Optional[str]
    payment_method_last4: Optional[str]
    payment_method_brand: Optional[str]
    receipt_url: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class GiftSubscriptionInfo(BaseModel):
    """Gift subscription information."""
    id: int
    giver_email: str
    giver_name: str
    recipient_email: str
    recipient_name: Optional[str]
    plan: SubscriptionPlan
    billing_interval: BillingInterval
    amount: Decimal
    currency: str
    status: GiftStatus
    gift_code: str
    personal_message: Optional[str]
    custom_sender_name: Optional[str]
    expires_at: datetime
    redeemed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class GiftPurchaseResponse(BaseModel):
    """Response schema for gift purchase."""
    success: bool
    gift_id: int
    gift_code: str
    redemption_url: str
    payment_intent_id: Optional[str] = None
    checkout_session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    amount: Decimal
    currency: str
    expires_at: datetime
    message: str


class GiftStatusResponse(BaseModel):
    """Response schema for gift status check."""
    success: bool
    exists: bool
    gift: Optional[GiftSubscriptionInfo] = None
    transaction: Optional[GiftTransactionInfo] = None
    can_be_redeemed: bool = False
    days_until_expiry: Optional[int] = None
    error_message: Optional[str] = None


class GiftRedemptionResponse(BaseModel):
    """Response schema for gift redemption."""
    success: bool
    subscription_id: Optional[int] = None
    plan: Optional[SubscriptionPlan] = None
    billing_interval: Optional[BillingInterval] = None
    message: str
    error_code: Optional[str] = None


class GiftRefundResponse(BaseModel):
    """Response schema for gift refund."""
    success: bool
    refund_id: Optional[str] = None
    refunded_amount: Decimal
    currency: str
    message: str


class GiftListItem(BaseModel):
    """Gift item for listing responses."""
    id: int
    recipient_email: str
    recipient_name: Optional[str]
    plan: SubscriptionPlan
    billing_interval: BillingInterval
    amount: Decimal
    status: GiftStatus
    gift_code_masked: str
    expires_at: datetime
    redeemed_at: Optional[datetime]
    created_at: datetime


class GiftListResponse(BaseModel):
    """Response schema for listing gifts."""
    success: bool
    gifts: List[GiftListItem]
    total_count: int
    page: int
    page_size: int
    has_more: bool


# ========== CHECKOUT AND PAYMENT SCHEMAS ==========

class CheckoutSessionResponse(BaseModel):
    """Response schema for Stripe checkout session creation."""
    success: bool
    checkout_session_id: str
    checkout_url: str
    gift_code: str
    expires_at: datetime


class PaymentIntentResponse(BaseModel):
    """Response schema for payment intent creation."""
    success: bool
    payment_intent_id: str
    client_secret: str
    gift_code: str
    amount: int
    currency: str


class WebhookEventResponse(BaseModel):
    """Response schema for webhook event processing."""
    success: bool
    processed: bool
    event_type: str
    gift_id: Optional[int] = None
    message: str


# ========== UTILITY SCHEMAS ==========

class GiftPriceCalculation(BaseModel):
    """Schema for gift price calculation."""
    base_price: int
    discount_amount: int
    final_price: int
    currency: str
    plan: str
    interval: str
    discount_percentage: Optional[int] = None


class GiftValidationResult(BaseModel):
    """Schema for gift code validation results."""
    is_valid: bool
    error_message: Optional[str] = None
    gift_exists: bool = False
    can_be_redeemed: bool = False
    expires_at: Optional[datetime] = None
    recipient_email: Optional[str] = None


# ========== ADMIN SCHEMAS ==========

class AdminGiftListRequest(BaseModel):
    """Request schema for admin gift listing."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[GiftStatus] = None
    plan: Optional[SubscriptionPlan] = None
    search_email: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class AdminGiftInfo(BaseModel):
    """Extended gift information for admin."""
    id: int
    giver_email: str
    giver_name: str
    giver_user_id: int
    recipient_email: str
    recipient_name: Optional[str]
    recipient_user_id: Optional[int]
    plan: SubscriptionPlan
    billing_interval: BillingInterval
    amount: Decimal
    currency: str
    status: GiftStatus
    gift_code: str
    stripe_payment_intent_id: str
    personal_message: Optional[str]
    expires_at: datetime
    redeemed_at: Optional[datetime]
    created_subscription_id: Optional[int]
    transaction: Optional[GiftTransactionInfo]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminGiftListResponse(BaseModel):
    """Response schema for admin gift listing."""
    success: bool
    gifts: List[AdminGiftInfo]
    total_count: int
    page: int
    page_size: int
    has_more: bool