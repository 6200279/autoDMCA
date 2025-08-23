import stripe
import logging
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ....core.config import settings
from ....api.deps.database import get_db
from ....db.models.user import User
from ....db.models.addon_service import UserAddonSubscription, AddonServiceStatus
from ....db.models.gift_subscription import GiftSubscription, GiftStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Handle the event
    try:
        if event['type'] == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event['data']['object'], db)
        elif event['type'] == 'invoice.payment_failed':
            await handle_payment_failed(event['data']['object'], db)
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_cancelled(event['data']['object'], db)
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event['data']['object'], db)
        elif event['type'] == 'payment_intent.succeeded':
            await handle_one_time_payment_succeeded(event['data']['object'], db)
        elif event['type'] == 'payment_intent.payment_failed':
            await handle_one_time_payment_failed(event['data']['object'], db)
        else:
            logger.info(f"Unhandled event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error processing webhook event {event['type']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )

    return {"received": True}

async def handle_payment_succeeded(invoice, db: Session):
    """Handle successful recurring payment"""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        # Find add-on subscription
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if addon_subscription:
            # Update subscription status to active
            addon_subscription.status = AddonServiceStatus.ACTIVE
            db.commit()
            
            logger.info(f"✅ Add-on payment succeeded for subscription {subscription_id}")
        
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {e}")
        db.rollback()

async def handle_payment_failed(invoice, db: Session):
    """Handle failed recurring payment"""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        # Find add-on subscription
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if addon_subscription:
            # Update subscription status to suspended
            addon_subscription.status = AddonServiceStatus.SUSPENDED
            db.commit()
            
            logger.warning(f"⚠️  Add-on payment failed for subscription {subscription_id}")
            
            # TODO: Send email notification to user about payment failure
        
    except Exception as e:
        logger.error(f"Error handling payment failed: {e}")
        db.rollback()

async def handle_subscription_cancelled(subscription, db: Session):
    """Handle subscription cancellation"""
    try:
        subscription_id = subscription.get('id')
        
        # Find and cancel add-on subscription
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if addon_subscription:
            addon_subscription.status = AddonServiceStatus.CANCELLED
            addon_subscription.cancelled_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ Add-on subscription cancelled: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription cancelled: {e}")
        db.rollback()

async def handle_subscription_updated(subscription, db: Session):
    """Handle subscription updates"""
    try:
        subscription_id = subscription.get('id')
        
        # Find add-on subscription
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if addon_subscription:
            # Update period dates
            from datetime import datetime
            addon_subscription.current_period_start = datetime.fromtimestamp(
                subscription.get('current_period_start')
            )
            addon_subscription.current_period_end = datetime.fromtimestamp(
                subscription.get('current_period_end')
            )
            
            # Update status based on subscription status
            stripe_status = subscription.get('status')
            if stripe_status == 'active':
                addon_subscription.status = AddonServiceStatus.ACTIVE
            elif stripe_status == 'canceled':
                addon_subscription.status = AddonServiceStatus.CANCELLED
            elif stripe_status == 'past_due':
                addon_subscription.status = AddonServiceStatus.SUSPENDED
            
            db.commit()
            logger.info(f"✅ Add-on subscription updated: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")
        db.rollback()

async def handle_one_time_payment_succeeded(payment_intent, db: Session):
    """Handle successful one-time payment"""
    try:
        payment_intent_id = payment_intent.get('id')
        
        # Check if this is for an add-on service
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if addon_subscription:
            addon_subscription.status = AddonServiceStatus.ACTIVE
            from datetime import datetime
            addon_subscription.paid_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ One-time add-on payment succeeded: {payment_intent_id}")
            return
        
        # Check if this is for a gift subscription
        gift_subscription = db.query(GiftSubscription).filter(
            GiftSubscription.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if gift_subscription:
            gift_subscription.status = GiftStatus.PENDING
            from datetime import datetime
            gift_subscription.paid_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ Gift subscription payment succeeded: {payment_intent_id}")
            
            # TODO: Send gift notification email
        
    except Exception as e:
        logger.error(f"Error handling one-time payment succeeded: {e}")
        db.rollback()

async def handle_one_time_payment_failed(payment_intent, db: Session):
    """Handle failed one-time payment"""
    try:
        payment_intent_id = payment_intent.get('id')
        
        # Check if this is for an add-on service
        addon_subscription = db.query(UserAddonSubscription).filter(
            UserAddonSubscription.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if addon_subscription:
            # Remove the failed subscription record
            db.delete(addon_subscription)
            db.commit()
            
            logger.warning(f"⚠️  One-time add-on payment failed: {payment_intent_id}")
            return
        
        # Check if this is for a gift subscription
        gift_subscription = db.query(GiftSubscription).filter(
            GiftSubscription.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if gift_subscription:
            gift_subscription.status = GiftStatus.FAILED
            db.commit()
            
            logger.warning(f"⚠️  Gift subscription payment failed: {payment_intent_id}")
        
    except Exception as e:
        logger.error(f"Error handling one-time payment failed: {e}")
        db.rollback()