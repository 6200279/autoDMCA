from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.gift_subscription import (
    GiftPurchaseRequest, GiftPurchaseResponse,
    GiftRedemptionRequest, GiftRedemptionResponse,
    GiftStatusRequest, GiftStatusResponse,
    GiftListResponse, GiftListItem,
    GiftRefundRequest, GiftRefundResponse,
    WebhookEventResponse
)
from app.services.billing.gift_subscription_service import gift_subscription_service
from app.services.billing.gift_code_service import gift_code_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


@router.post("/purchase", response_model=GiftPurchaseResponse)
async def purchase_gift_subscription(
    request: GiftPurchaseRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Purchase a gift subscription for someone else."""
    try:
        user_ip = get_client_ip(http_request)
        
        # Create the gift subscription
        response = await gift_subscription_service.create_gift_subscription(
            db=db,
            request=request,
            giver_user=current_user,
            user_ip=user_ip
        )
        
        # TODO: Add background task for email notifications
        # background_tasks.add_task(send_gift_notification_email, response.gift_id)
        
        return response
        
    except Exception as e:
        logger.error(f"Error purchasing gift subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process gift subscription purchase"
        )


@router.post("/redeem", response_model=GiftRedemptionResponse)
async def redeem_gift_subscription(
    request: GiftRedemptionRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Redeem a gift subscription code."""
    try:
        user_ip = get_client_ip(http_request)
        
        # Redeem the gift subscription
        response = await gift_subscription_service.redeem_gift_subscription(
            db=db,
            request=request,
            recipient_user=current_user,
            user_ip=user_ip
        )
        
        # TODO: Add background task for confirmation emails
        if response.success:
            # background_tasks.add_task(send_redemption_confirmation_email, current_user.id, response.subscription_id)
            pass
        
        return response
        
    except Exception as e:
        logger.error(f"Error redeeming gift subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to redeem gift subscription"
        )


@router.post("/status", response_model=GiftStatusResponse)
async def check_gift_status(
    request: GiftStatusRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Check the status of a gift subscription (no authentication required)."""
    try:
        user_ip = get_client_ip(http_request)
        
        response = await gift_subscription_service.get_gift_status(
            db=db,
            request=request,
            user_ip=user_ip
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error checking gift status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check gift status"
        )


@router.get("/my-gifts-given", response_model=GiftListResponse)
async def get_my_gifts_given(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get gifts given by the current user."""
    try:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        gifts = gift_subscription_service.get_user_gifts_given(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        gift_items = []
        for gift in gifts:
            gift_items.append(GiftListItem(
                id=gift.id,
                recipient_email=gift.recipient_email,
                recipient_name=gift.recipient_name,
                plan=gift.plan,
                billing_interval=gift.billing_interval,
                amount=gift.amount,
                status=gift.status,
                gift_code_masked=gift_code_service.mask_gift_code(gift.gift_code),
                expires_at=gift.expires_at,
                redeemed_at=gift.redeemed_at,
                created_at=gift.created_at
            ))
        
        # Get total count for pagination
        total_count = db.query(gift_subscription_service.GiftSubscription).filter(
            gift_subscription_service.GiftSubscription.giver_user_id == current_user.id
        ).count()
        
        return GiftListResponse(
            success=True,
            gifts=gift_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total_count
        )
        
    except Exception as e:
        logger.error(f"Error getting user's given gifts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gift history"
        )


@router.get("/my-gifts-received", response_model=GiftListResponse)
async def get_my_gifts_received(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get gifts received by the current user."""
    try:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        gifts = gift_subscription_service.get_user_gifts_received(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        gift_items = []
        for gift in gifts:
            gift_items.append(GiftListItem(
                id=gift.id,
                recipient_email=gift.recipient_email,
                recipient_name=gift.recipient_name,
                plan=gift.plan,
                billing_interval=gift.billing_interval,
                amount=gift.amount,
                status=gift.status,
                gift_code_masked=gift_code_service.mask_gift_code(gift.gift_code),
                expires_at=gift.expires_at,
                redeemed_at=gift.redeemed_at,
                created_at=gift.created_at
            ))
        
        # Get total count for pagination
        from app.db.models.gift_subscription import GiftSubscription
        total_count = db.query(GiftSubscription).filter(
            GiftSubscription.recipient_user_id == current_user.id
        ).count()
        
        return GiftListResponse(
            success=True,
            gifts=gift_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total_count
        )
        
    except Exception as e:
        logger.error(f"Error getting user's received gifts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve received gifts"
        )


@router.post("/cancel/{gift_id}")
async def cancel_gift_subscription(
    gift_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a gift subscription (only if not redeemed)."""
    try:
        success = await gift_subscription_service.cancel_gift_subscription(
            db=db,
            gift_id=gift_id,
            user_id=current_user.id,
            reason="cancelled_by_user"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gift not found or cannot be cancelled"
            )
        
        # TODO: Add background task for cancellation emails
        # background_tasks.add_task(send_gift_cancellation_email, gift_id)
        
        return {"success": True, "message": "Gift subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling gift subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel gift subscription"
        )


@router.get("/validate-code/{gift_code}")
async def validate_gift_code(
    gift_code: str,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Validate a gift code format and basic availability (public endpoint)."""
    try:
        user_ip = get_client_ip(http_request)
        
        # Basic format validation
        normalized_code = gift_code_service.normalize_code(gift_code)
        is_valid_format = gift_code_service.validate_code_format(normalized_code)
        
        if not is_valid_format:
            return {
                "valid": False,
                "error": "Invalid gift code format",
                "code": normalized_code
            }
        
        # Check if code exists (basic check without full validation)
        from app.db.models.gift_subscription import GiftCode
        gift_code_record = db.query(GiftCode).filter(
            GiftCode.code == normalized_code
        ).first()
        
        if not gift_code_record:
            return {
                "valid": False,
                "error": "Gift code not found",
                "code": normalized_code
            }
        
        # Basic availability check
        gift_subscription = gift_code_record.gift_subscription
        basic_info = {
            "valid": True,
            "code": normalized_code,
            "exists": True,
            "expired": gift_subscription.is_expired() if gift_subscription else True,
            "redeemed": gift_subscription.status.value if gift_subscription else "unknown",
            "recipient_email": gift_subscription.recipient_email if gift_subscription else None
        }
        
        return basic_info
        
    except Exception as e:
        logger.error(f"Error validating gift code: {str(e)}")
        return {
            "valid": False,
            "error": "An error occurred while validating the gift code",
            "code": gift_code
        }


@router.post("/webhook/stripe", response_model=WebhookEventResponse)
async def handle_stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events for gift subscriptions."""
    try:
        # Get raw body and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Verify webhook
        from app.services.billing.stripe_service import stripe_service
        event = stripe_service.construct_webhook_event(payload, signature)
        
        event_type = event["type"]
        
        # Process gift-related events
        if event_type in ["payment_intent.succeeded", "payment_intent.payment_failed"]:
            payment_intent = event["data"]["object"]
            
            # Check if this is a gift payment
            metadata = payment_intent.get("metadata", {})
            if metadata.get("type") == "gift_subscription":
                processed = await gift_subscription_service.process_payment_webhook(
                    db=db,
                    event_type=event_type,
                    payment_intent_data=payment_intent
                )
                
                return WebhookEventResponse(
                    success=True,
                    processed=processed,
                    event_type=event_type,
                    message="Gift payment webhook processed"
                )
        
        # Event not related to gifts
        return WebhookEventResponse(
            success=True,
            processed=False,
            event_type=event_type,
            message="Event not related to gift subscriptions"
        )
        
    except Exception as e:
        logger.error(f"Error processing gift webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )