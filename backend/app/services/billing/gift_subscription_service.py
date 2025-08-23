import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.db.models.gift_subscription import (
    GiftSubscription, GiftCode, GiftTransaction, GiftEmailLog,
    GiftStatus, GiftTransactionStatus
)
from app.db.models.subscription import Subscription, SubscriptionPlan, BillingInterval, SubscriptionStatus
from app.db.models.user import User
from app.schemas.gift_subscription import (
    GiftPurchaseRequest, GiftRedemptionRequest, GiftStatusRequest,
    GiftPurchaseResponse, GiftRedemptionResponse, GiftStatusResponse
)
from app.services.billing.stripe_service import stripe_service
from app.services.billing.gift_code_service import gift_code_service
from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class GiftSubscriptionService:
    """Service for managing gift subscription operations."""
    
    def __init__(self):
        self.default_expiry_days = 90
    
    async def create_gift_subscription(
        self,
        db: Session,
        request: GiftPurchaseRequest,
        giver_user: User,
        user_ip: str = None
    ) -> GiftPurchaseResponse:
        """Create a new gift subscription purchase."""
        try:
            # Generate unique gift code
            gift_code = gift_code_service.generate_unique_code()
            
            # Calculate pricing
            price_info = stripe_service.calculate_gift_price(
                request.plan, 
                request.billing_interval
            )
            
            # Create Stripe customer if needed
            if not giver_user.stripe_customer_id:
                customer = await stripe_service.create_customer(
                    email=giver_user.email,
                    name=giver_user.full_name or giver_user.email,
                    metadata={"user_id": str(giver_user.id)}
                )
                giver_user.stripe_customer_id = customer.id
                db.commit()
            
            # Calculate expiry date
            expires_at = gift_code_service.calculate_expiry_date(self.default_expiry_days)
            
            # Create gift subscription record
            gift_subscription = GiftSubscription(
                giver_user_id=giver_user.id,
                giver_email=giver_user.email,
                giver_name=giver_user.full_name or giver_user.email,
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                plan=request.plan,
                billing_interval=request.billing_interval,
                amount=Decimal(price_info["final_price"]) / 100,  # Convert from cents
                currency="USD",
                status=GiftStatus.PENDING,
                gift_code=gift_code,
                stripe_customer_id=giver_user.stripe_customer_id,
                personal_message=request.personal_message,
                custom_sender_name=request.custom_sender_name,
                expires_at=expires_at,
                metadata={
                    "giver_ip": user_ip,
                    "price_calculation": price_info
                }
            )
            
            db.add(gift_subscription)
            db.flush()  # Get the ID
            
            # Create gift code record
            gift_code_data = gift_code_service.create_gift_code_data(
                gift_subscription.id,
                user_ip=user_ip
            )
            
            gift_code_record = GiftCode(**gift_code_data)
            db.add(gift_code_record)
            
            # Handle payment method
            if request.use_checkout:
                # Create Stripe Checkout session
                checkout_session = await stripe_service.create_gift_checkout_session(
                    customer_id=giver_user.stripe_customer_id,
                    plan=request.plan,
                    interval=request.billing_interval,
                    gift_code=gift_code,
                    recipient_email=request.recipient_email,
                    success_url=request.success_url or f"{settings.FRONTEND_URL}/gift/success",
                    cancel_url=request.cancel_url or f"{settings.FRONTEND_URL}/gift/cancel",
                    metadata={
                        "gift_subscription_id": str(gift_subscription.id),
                        "giver_user_id": str(giver_user.id)
                    }
                )
                
                # Create transaction record (will be updated after payment)
                transaction = GiftTransaction(
                    gift_subscription_id=gift_subscription.id,
                    stripe_payment_intent_id=checkout_session.payment_intent or "",
                    amount=gift_subscription.amount,
                    currency=gift_subscription.currency,
                    status=GiftTransactionStatus.PENDING,
                    net_amount=gift_subscription.amount
                )
                
                db.add(transaction)
                db.commit()
                
                return GiftPurchaseResponse(
                    success=True,
                    gift_id=gift_subscription.id,
                    gift_code=gift_code,
                    redemption_url=gift_code_service.generate_redemption_url(gift_code),
                    checkout_session_id=checkout_session.id,
                    checkout_url=checkout_session.url,
                    amount=gift_subscription.amount,
                    currency=gift_subscription.currency,
                    expires_at=expires_at,
                    message="Gift subscription created. Complete payment to activate."
                )
            
            else:
                # Create payment intent
                payment_intent = await stripe_service.create_gift_payment_intent(
                    customer_id=giver_user.stripe_customer_id,
                    amount=price_info["final_price"],
                    currency="usd",
                    gift_code=gift_code,
                    recipient_email=request.recipient_email,
                    metadata={
                        "gift_subscription_id": str(gift_subscription.id),
                        "giver_user_id": str(giver_user.id)
                    }
                )
                
                gift_subscription.stripe_payment_intent_id = payment_intent.id
                
                # Create transaction record
                transaction = GiftTransaction(
                    gift_subscription_id=gift_subscription.id,
                    stripe_payment_intent_id=payment_intent.id,
                    amount=gift_subscription.amount,
                    currency=gift_subscription.currency,
                    status=GiftTransactionStatus.PENDING,
                    net_amount=gift_subscription.amount
                )
                
                db.add(transaction)
                
                # Confirm payment if payment method provided
                if request.payment_method_id:
                    await stripe_service.confirm_gift_payment_intent(
                        payment_intent.id,
                        request.payment_method_id
                    )
                
                db.commit()
                
                return GiftPurchaseResponse(
                    success=True,
                    gift_id=gift_subscription.id,
                    gift_code=gift_code,
                    redemption_url=gift_code_service.generate_redemption_url(gift_code),
                    payment_intent_id=payment_intent.id,
                    client_secret=payment_intent.client_secret,
                    amount=gift_subscription.amount,
                    currency=gift_subscription.currency,
                    expires_at=expires_at,
                    message="Gift subscription created successfully."
                )
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating gift subscription: {str(e)}")
            raise
    
    async def redeem_gift_subscription(
        self,
        db: Session,
        request: GiftRedemptionRequest,
        recipient_user: User,
        user_ip: str = None
    ) -> GiftRedemptionResponse:
        """Redeem a gift subscription."""
        try:
            # Normalize and validate gift code format
            normalized_code = gift_code_service.normalize_code(request.gift_code)
            
            if not gift_code_service.validate_code_format(normalized_code):
                return GiftRedemptionResponse(
                    success=False,
                    message="Invalid gift code format",
                    error_code="INVALID_FORMAT"
                )
            
            # Find gift code
            gift_code = db.query(GiftCode).filter(
                GiftCode.code == normalized_code
            ).first()
            
            if not gift_code:
                return GiftRedemptionResponse(
                    success=False,
                    message="Gift code not found",
                    error_code="CODE_NOT_FOUND"
                )
            
            # Record attempt
            gift_code_service.record_redemption_attempt(gift_code, user_ip, False)
            
            # Validate redemption eligibility
            is_valid, error_message = gift_code_service.validate_redemption_eligibility(
                gift_code,
                user_ip=user_ip,
                user_email=recipient_user.email
            )
            
            if not is_valid:
                db.commit()  # Save the failed attempt
                return GiftRedemptionResponse(
                    success=False,
                    message=error_message,
                    error_code="REDEMPTION_FAILED"
                )
            
            gift_subscription = gift_code.gift_subscription
            
            # Check if user already has an active subscription
            existing_subscription = db.query(Subscription).filter(
                and_(
                    Subscription.user_id == recipient_user.id,
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING
                    ])
                )
            ).first()
            
            if existing_subscription:
                # Handle existing subscription (could upgrade, extend, or queue)
                # For now, we'll extend the current subscription
                current_end = existing_subscription.current_period_end or datetime.now(timezone.utc)
                extension_days = 30 if gift_subscription.billing_interval == BillingInterval.MONTH else 365
                new_end = current_end + timedelta(days=extension_days)
                
                existing_subscription.current_period_end = new_end
                created_subscription = existing_subscription
            else:
                # Create new subscription
                current_time = datetime.now(timezone.utc)
                period_days = 30 if gift_subscription.billing_interval == BillingInterval.MONTH else 365
                period_end = current_time + timedelta(days=period_days)
                
                created_subscription = Subscription(
                    user_id=recipient_user.id,
                    plan=gift_subscription.plan,
                    status=SubscriptionStatus.ACTIVE,
                    stripe_customer_id=None,  # No Stripe subscription for gifts
                    stripe_subscription_id=None,
                    amount=gift_subscription.amount,
                    currency=gift_subscription.currency,
                    interval=gift_subscription.billing_interval,
                    current_period_start=current_time,
                    current_period_end=period_end,
                    # Set plan features based on gift plan
                    max_protected_profiles=1 if gift_subscription.plan == SubscriptionPlan.BASIC else 5,
                    max_monthly_scans=1000 if gift_subscription.plan == SubscriptionPlan.BASIC else 10000,
                    max_takedown_requests=50 if gift_subscription.plan == SubscriptionPlan.BASIC else 500,
                    ai_face_recognition=True,
                    priority_support=gift_subscription.plan == SubscriptionPlan.PROFESSIONAL,
                    custom_branding=gift_subscription.plan == SubscriptionPlan.PROFESSIONAL,
                    api_access=gift_subscription.plan == SubscriptionPlan.PROFESSIONAL,
                )
                
                db.add(created_subscription)
                db.flush()
            
            # Update gift subscription as redeemed
            gift_subscription.status = GiftStatus.REDEEMED
            gift_subscription.recipient_user_id = recipient_user.id
            gift_subscription.redeemed_at = datetime.now(timezone.utc)
            gift_subscription.created_subscription_id = created_subscription.id
            
            # Mark gift code as redeemed
            gift_code_service.record_redemption_attempt(gift_code, user_ip, True)
            
            db.commit()
            
            logger.info(f"Gift subscription {gift_subscription.id} redeemed by user {recipient_user.id}")
            
            return GiftRedemptionResponse(
                success=True,
                subscription_id=created_subscription.id,
                plan=gift_subscription.plan,
                billing_interval=gift_subscription.billing_interval,
                message="Gift subscription redeemed successfully!"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error redeeming gift subscription: {str(e)}")
            return GiftRedemptionResponse(
                success=False,
                message="An error occurred while redeeming the gift code",
                error_code="INTERNAL_ERROR"
            )
    
    async def get_gift_status(
        self,
        db: Session,
        request: GiftStatusRequest,
        user_ip: str = None
    ) -> GiftStatusResponse:
        """Get the status of a gift subscription."""
        try:
            # Normalize gift code
            normalized_code = gift_code_service.normalize_code(request.gift_code)
            
            if not gift_code_service.validate_code_format(normalized_code):
                return GiftStatusResponse(
                    success=True,
                    exists=False,
                    error_message="Invalid gift code format"
                )
            
            # Find gift code
            gift_code = db.query(GiftCode).filter(
                GiftCode.code == normalized_code
            ).first()
            
            if not gift_code or not gift_code.gift_subscription:
                return GiftStatusResponse(
                    success=True,
                    exists=False,
                    error_message="Gift code not found"
                )
            
            gift_subscription = gift_code.gift_subscription
            
            # Get transaction info
            transaction_info = None
            if gift_subscription.gift_transaction:
                from app.schemas.gift_subscription import GiftTransactionInfo
                transaction_info = GiftTransactionInfo.from_orm(gift_subscription.gift_transaction)
            
            # Create gift info
            from app.schemas.gift_subscription import GiftSubscriptionInfo
            gift_info = GiftSubscriptionInfo.from_orm(gift_subscription)
            
            # Check if it can be redeemed
            can_be_redeemed, _ = gift_code_service.validate_redemption_eligibility(gift_code, user_ip)
            
            return GiftStatusResponse(
                success=True,
                exists=True,
                gift=gift_info,
                transaction=transaction_info,
                can_be_redeemed=can_be_redeemed,
                days_until_expiry=gift_subscription.days_until_expiry()
            )
            
        except Exception as e:
            logger.error(f"Error getting gift status: {str(e)}")
            return GiftStatusResponse(
                success=False,
                exists=False,
                error_message="An error occurred while checking gift status"
            )
    
    async def process_payment_webhook(
        self,
        db: Session,
        event_type: str,
        payment_intent_data: Dict[str, Any]
    ) -> bool:
        """Process Stripe webhook events for gift payments."""
        try:
            payment_intent_id = payment_intent_data.get("id")
            
            # Find gift transaction
            transaction = db.query(GiftTransaction).filter(
                GiftTransaction.stripe_payment_intent_id == payment_intent_id
            ).first()
            
            if not transaction:
                logger.warning(f"Gift transaction not found for payment intent: {payment_intent_id}")
                return False
            
            gift_subscription = transaction.gift_subscription
            
            if event_type == "payment_intent.succeeded":
                # Update transaction as completed
                transaction.status = GiftTransactionStatus.COMPLETED
                transaction.processed_at = datetime.now(timezone.utc)
                
                # Update payment method info if available
                if payment_intent_data.get("charges", {}).get("data"):
                    charge = payment_intent_data["charges"]["data"][0]
                    transaction.stripe_charge_id = charge.get("id")
                    transaction.receipt_url = charge.get("receipt_url")
                    
                    payment_method = charge.get("payment_method_details", {})
                    if payment_method:
                        transaction.payment_method_type = payment_method.get("type")
                        if payment_method.get("card"):
                            card = payment_method["card"]
                            transaction.payment_method_last4 = card.get("last4")
                            transaction.payment_method_brand = card.get("brand")
                
                # Update gift as ready to redeem (still pending until redeemed)
                logger.info(f"Gift subscription {gift_subscription.id} payment completed")
                
                # TODO: Send gift notification email
                
            elif event_type == "payment_intent.payment_failed":
                # Update transaction as failed
                transaction.status = GiftTransactionStatus.FAILED
                transaction.failure_code = payment_intent_data.get("last_payment_error", {}).get("code")
                transaction.failure_message = payment_intent_data.get("last_payment_error", {}).get("message")
                
                logger.error(f"Gift subscription {gift_subscription.id} payment failed")
                
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing gift payment webhook: {str(e)}")
            return False
    
    def get_user_gifts_given(
        self,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> List[GiftSubscription]:
        """Get gifts given by a user."""
        offset = (page - 1) * page_size
        
        return db.query(GiftSubscription).filter(
            GiftSubscription.giver_user_id == user_id
        ).order_by(desc(GiftSubscription.created_at)).offset(offset).limit(page_size).all()
    
    def get_user_gifts_received(
        self,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> List[GiftSubscription]:
        """Get gifts received by a user."""
        offset = (page - 1) * page_size
        
        return db.query(GiftSubscription).filter(
            GiftSubscription.recipient_user_id == user_id
        ).order_by(desc(GiftSubscription.created_at)).offset(offset).limit(page_size).all()
    
    async def cancel_gift_subscription(
        self,
        db: Session,
        gift_id: int,
        user_id: int,
        reason: str = "cancelled_by_user"
    ) -> bool:
        """Cancel a gift subscription (only if not redeemed)."""
        try:
            gift_subscription = db.query(GiftSubscription).filter(
                and_(
                    GiftSubscription.id == gift_id,
                    GiftSubscription.giver_user_id == user_id,
                    GiftSubscription.status == GiftStatus.PENDING
                )
            ).first()
            
            if not gift_subscription:
                return False
            
            # Cancel the gift
            gift_subscription.status = GiftStatus.CANCELLED
            
            # Deactivate gift code
            if gift_subscription.gift_code_record:
                gift_subscription.gift_code_record.is_active = False
            
            # Process refund if payment was completed
            if (gift_subscription.gift_transaction and 
                gift_subscription.gift_transaction.status == GiftTransactionStatus.COMPLETED):
                
                if gift_subscription.gift_transaction.stripe_charge_id:
                    await stripe_service.refund_gift_payment(
                        gift_subscription.gift_transaction.stripe_charge_id,
                        reason=reason,
                        metadata={"gift_id": str(gift_id)}
                    )
                    
                    gift_subscription.gift_transaction.status = GiftTransactionStatus.REFUNDED
                    gift_subscription.gift_transaction.refund_reason = reason
                    gift_subscription.gift_transaction.refunded_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Gift subscription {gift_id} cancelled by user {user_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling gift subscription: {str(e)}")
            return False


# Create singleton instance
gift_subscription_service = GiftSubscriptionService()