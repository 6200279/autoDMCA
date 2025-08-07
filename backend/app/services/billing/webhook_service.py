import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.subscription import (
    Subscription, 
    SubscriptionStatus, 
    Invoice, 
    InvoiceStatus,
    InvoiceLineItem,
    PaymentMethod
)
from app.db.models.user import User
from app.services.billing.stripe_service import stripe_service
from app.services.billing.subscription_service import subscription_service

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for handling Stripe webhook events."""
    
    async def handle_webhook_event(
        self,
        db: AsyncSession,
        event: Dict[str, Any]
    ) -> bool:
        """Process webhook event from Stripe."""
        try:
            event_type = event["type"]
            data = event["data"]["object"]
            
            logger.info(f"Processing webhook event: {event_type}")
            
            # Customer events
            if event_type == "customer.created":
                return await self._handle_customer_created(db, data)
            elif event_type == "customer.updated":
                return await self._handle_customer_updated(db, data)
            elif event_type == "customer.deleted":
                return await self._handle_customer_deleted(db, data)
            
            # Subscription events
            elif event_type == "customer.subscription.created":
                return await self._handle_subscription_created(db, data)
            elif event_type == "customer.subscription.updated":
                return await self._handle_subscription_updated(db, data)
            elif event_type == "customer.subscription.deleted":
                return await self._handle_subscription_deleted(db, data)
            elif event_type == "customer.subscription.trial_will_end":
                return await self._handle_trial_will_end(db, data)
            
            # Invoice events
            elif event_type == "invoice.created":
                return await self._handle_invoice_created(db, data)
            elif event_type == "invoice.finalized":
                return await self._handle_invoice_finalized(db, data)
            elif event_type == "invoice.paid":
                return await self._handle_invoice_paid(db, data)
            elif event_type == "invoice.payment_failed":
                return await self._handle_invoice_payment_failed(db, data)
            elif event_type == "invoice.voided":
                return await self._handle_invoice_voided(db, data)
            
            # Payment method events
            elif event_type == "payment_method.attached":
                return await self._handle_payment_method_attached(db, data)
            elif event_type == "payment_method.detached":
                return await self._handle_payment_method_detached(db, data)
            elif event_type == "payment_method.updated":
                return await self._handle_payment_method_updated(db, data)
            
            # Payment events
            elif event_type == "payment_intent.succeeded":
                return await self._handle_payment_succeeded(db, data)
            elif event_type == "payment_intent.payment_failed":
                return await self._handle_payment_failed(db, data)
            
            # Setup intent events
            elif event_type == "setup_intent.succeeded":
                return await self._handle_setup_intent_succeeded(db, data)
            
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to process webhook event {event_type}: {str(e)}")
            return False
    
    async def _handle_customer_created(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.created event."""
        try:
            customer_id = data["id"]
            email = data.get("email")
            name = data.get("name")
            
            logger.info(f"Customer created: {customer_id} - {email}")
            
            # Update user's subscription with Stripe customer ID if found
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                
                if user and user.subscription:
                    user.subscription.stripe_customer_id = customer_id
                    await db.commit()
                    logger.info(f"Updated user {user.id} with Stripe customer ID")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle customer.created: {str(e)}")
            return False
    
    async def _handle_customer_updated(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.updated event."""
        try:
            customer_id = data["id"]
            logger.info(f"Customer updated: {customer_id}")
            
            # Update local customer data if needed
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            subscription = result.scalar_one_or_none()
            
            if subscription:
                # Update any relevant customer information
                await db.commit()
                logger.info(f"Updated customer data for subscription {subscription.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle customer.updated: {str(e)}")
            return False
    
    async def _handle_customer_deleted(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.deleted event."""
        try:
            customer_id = data["id"]
            logger.info(f"Customer deleted: {customer_id}")
            
            # Mark subscription as cancelled
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            )
            subscription = result.scalar_one_or_none()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(f"Cancelled subscription {subscription.id} due to customer deletion")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle customer.deleted: {str(e)}")
            return False
    
    async def _handle_subscription_created(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.subscription.created event."""
        try:
            subscription_id = data["id"]
            logger.info(f"Subscription created: {subscription_id}")
            
            # Update local subscription with Stripe data
            await subscription_service.update_subscription_from_stripe(db, data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle subscription.created: {str(e)}")
            return False
    
    async def _handle_subscription_updated(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.subscription.updated event."""
        try:
            subscription_id = data["id"]
            logger.info(f"Subscription updated: {subscription_id}")
            
            # Update local subscription with Stripe data
            await subscription_service.update_subscription_from_stripe(db, data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle subscription.updated: {str(e)}")
            return False
    
    async def _handle_subscription_deleted(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.subscription.deleted event."""
        try:
            subscription_id = data["id"]
            logger.info(f"Subscription deleted: {subscription_id}")
            
            # Mark subscription as cancelled
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(f"Cancelled local subscription {subscription.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle subscription.deleted: {str(e)}")
            return False
    
    async def _handle_trial_will_end(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle customer.subscription.trial_will_end event."""
        try:
            subscription_id = data["id"]
            trial_end = datetime.fromtimestamp(data["trial_end"], tz=timezone.utc)
            
            logger.info(f"Trial ending for subscription: {subscription_id} at {trial_end}")
            
            # Find local subscription and send notification
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
            if subscription:
                # TODO: Send trial ending notification email
                logger.info(f"Trial ending notification for subscription {subscription.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle trial_will_end: {str(e)}")
            return False
    
    async def _handle_invoice_created(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle invoice.created event."""
        try:
            await self._sync_invoice(db, data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle invoice.created: {str(e)}")
            return False
    
    async def _handle_invoice_finalized(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle invoice.finalized event."""
        try:
            await self._sync_invoice(db, data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle invoice.finalized: {str(e)}")
            return False
    
    async def _handle_invoice_paid(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle invoice.paid event."""
        try:
            await self._sync_invoice(db, data)
            
            # Additional logic for successful payment
            invoice_id = data["id"]
            logger.info(f"Invoice paid: {invoice_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle invoice.paid: {str(e)}")
            return False
    
    async def _handle_invoice_payment_failed(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle invoice.payment_failed event."""
        try:
            await self._sync_invoice(db, data)
            
            # Additional logic for failed payment
            invoice_id = data["id"]
            subscription_id = data.get("subscription")
            
            logger.warning(f"Invoice payment failed: {invoice_id}")
            
            # Update subscription status if needed
            if subscription_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
                )
                subscription = result.scalar_one_or_none()
                
                if subscription:
                    subscription.status = SubscriptionStatus.PAST_DUE
                    await db.commit()
                    
                    # TODO: Send payment failed notification
                    logger.info(f"Marked subscription {subscription.id} as past due")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle invoice.payment_failed: {str(e)}")
            return False
    
    async def _handle_invoice_voided(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle invoice.voided event."""
        try:
            await self._sync_invoice(db, data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle invoice.voided: {str(e)}")
            return False
    
    async def _handle_payment_method_attached(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle payment_method.attached event."""
        try:
            payment_method_id = data["id"]
            customer_id = data.get("customer")
            
            logger.info(f"Payment method attached: {payment_method_id}")
            
            # Find subscription by customer ID
            if customer_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.stripe_customer_id == customer_id)
                )
                subscription = result.scalar_one_or_none()
                
                if subscription:
                    # Create or update payment method record
                    await self._sync_payment_method(db, data, subscription.user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment_method.attached: {str(e)}")
            return False
    
    async def _handle_payment_method_detached(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle payment_method.detached event."""
        try:
            payment_method_id = data["id"]
            
            logger.info(f"Payment method detached: {payment_method_id}")
            
            # Remove or deactivate payment method record
            result = await db.execute(
                select(PaymentMethod).where(PaymentMethod.stripe_payment_method_id == payment_method_id)
            )
            payment_method = result.scalar_one_or_none()
            
            if payment_method:
                payment_method.is_active = False
                await db.commit()
                logger.info(f"Deactivated payment method {payment_method.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment_method.detached: {str(e)}")
            return False
    
    async def _handle_payment_method_updated(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle payment_method.updated event."""
        try:
            payment_method_id = data["id"]
            customer_id = data.get("customer")
            
            logger.info(f"Payment method updated: {payment_method_id}")
            
            # Find user by customer ID and update payment method
            if customer_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.stripe_customer_id == customer_id)
                )
                subscription = result.scalar_one_or_none()
                
                if subscription:
                    await self._sync_payment_method(db, data, subscription.user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment_method.updated: {str(e)}")
            return False
    
    async def _handle_payment_succeeded(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle payment_intent.succeeded event."""
        try:
            payment_intent_id = data["id"]
            invoice_id = data.get("invoice")
            
            logger.info(f"Payment succeeded: {payment_intent_id}")
            
            # Update invoice payment status if applicable
            if invoice_id:
                result = await db.execute(
                    select(Invoice).where(Invoice.stripe_invoice_id == invoice_id)
                )
                invoice = result.scalar_one_or_none()
                
                if invoice:
                    invoice.stripe_payment_intent_id = payment_intent_id
                    invoice.status = InvoiceStatus.PAID
                    invoice.paid_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info(f"Updated invoice {invoice.id} as paid")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment_intent.succeeded: {str(e)}")
            return False
    
    async def _handle_payment_failed(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle payment_intent.payment_failed event."""
        try:
            payment_intent_id = data["id"]
            logger.warning(f"Payment failed: {payment_intent_id}")
            
            # TODO: Handle failed payment logic
            # This might include sending notifications, updating subscription status, etc.
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment_intent.payment_failed: {str(e)}")
            return False
    
    async def _handle_setup_intent_succeeded(self, db: AsyncSession, data: Dict[str, Any]) -> bool:
        """Handle setup_intent.succeeded event."""
        try:
            setup_intent_id = data["id"]
            payment_method_id = data.get("payment_method")
            customer_id = data.get("customer")
            
            logger.info(f"Setup intent succeeded: {setup_intent_id}")
            
            # Update payment method as confirmed
            if payment_method_id and customer_id:
                result = await db.execute(
                    select(Subscription).where(Subscription.stripe_customer_id == customer_id)
                )
                subscription = result.scalar_one_or_none()
                
                if subscription:
                    # Fetch payment method details and sync
                    stripe_payment_method = await stripe_service.get_payment_method(payment_method_id)
                    if stripe_payment_method:
                        await self._sync_payment_method(db, stripe_payment_method, subscription.user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle setup_intent.succeeded: {str(e)}")
            return False
    
    async def _sync_invoice(self, db: AsyncSession, stripe_invoice: Dict[str, Any]) -> Optional[Invoice]:
        """Sync invoice data from Stripe."""
        try:
            invoice_id = stripe_invoice["id"]
            subscription_id = stripe_invoice.get("subscription")
            customer_id = stripe_invoice["customer"]
            
            # Find local subscription
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                logger.warning(f"Subscription not found for invoice: {invoice_id}")
                return None
            
            # Check if invoice already exists
            result = await db.execute(
                select(Invoice).where(Invoice.stripe_invoice_id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                invoice = Invoice(
                    subscription_id=subscription.id,
                    user_id=subscription.user_id,
                    stripe_invoice_id=invoice_id
                )
                db.add(invoice)
            
            # Update invoice details
            invoice.invoice_number = stripe_invoice.get("number")
            invoice.status = InvoiceStatus(stripe_invoice["status"])
            invoice.subtotal = stripe_invoice["subtotal"] / 100  # Convert cents to dollars
            invoice.tax = (stripe_invoice.get("tax") or 0) / 100
            invoice.discount = (stripe_invoice.get("discount", {}).get("amount") or 0) / 100
            invoice.total = stripe_invoice["total"] / 100
            invoice.amount_paid = stripe_invoice["amount_paid"] / 100
            invoice.amount_due = stripe_invoice["amount_due"] / 100
            invoice.currency = stripe_invoice["currency"].upper()
            
            # Set dates
            invoice.invoice_date = datetime.fromtimestamp(stripe_invoice["created"], tz=timezone.utc)
            if stripe_invoice.get("due_date"):
                invoice.due_date = datetime.fromtimestamp(stripe_invoice["due_date"], tz=timezone.utc)
            invoice.period_start = datetime.fromtimestamp(stripe_invoice["period_start"], tz=timezone.utc)
            invoice.period_end = datetime.fromtimestamp(stripe_invoice["period_end"], tz=timezone.utc)
            
            if stripe_invoice.get("status_transitions", {}).get("paid_at"):
                invoice.paid_at = datetime.fromtimestamp(
                    stripe_invoice["status_transitions"]["paid_at"], tz=timezone.utc
                )
            
            # Set URLs
            invoice.invoice_pdf_url = stripe_invoice.get("invoice_pdf")
            invoice.hosted_invoice_url = stripe_invoice.get("hosted_invoice_url")
            
            invoice.description = stripe_invoice.get("description")
            
            # Sync line items
            for line_item_data in stripe_invoice.get("lines", {}).get("data", []):
                await self._sync_invoice_line_item(db, invoice, line_item_data)
            
            await db.commit()
            await db.refresh(invoice)
            
            logger.info(f"Synced invoice: {invoice.id}")
            return invoice
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to sync invoice: {str(e)}")
            raise
    
    async def _sync_invoice_line_item(
        self, 
        db: AsyncSession, 
        invoice: Invoice, 
        line_item_data: Dict[str, Any]
    ) -> InvoiceLineItem:
        """Sync invoice line item."""
        try:
            line_item_id = line_item_data["id"]
            
            # Check if line item already exists
            result = await db.execute(
                select(InvoiceLineItem).where(
                    InvoiceLineItem.invoice_id == invoice.id
                ).where(
                    InvoiceLineItem.stripe_price_id == line_item_data.get("price", {}).get("id")
                )
            )
            line_item = result.scalar_one_or_none()
            
            if not line_item:
                line_item = InvoiceLineItem(invoice_id=invoice.id)
                db.add(line_item)
            
            # Update line item details
            line_item.description = line_item_data.get("description", "")
            line_item.quantity = line_item_data.get("quantity", 1)
            line_item.unit_amount = line_item_data.get("amount", 0) / 100
            line_item.amount = line_item_data.get("amount", 0) / 100
            line_item.currency = line_item_data.get("currency", "usd").upper()
            line_item.stripe_price_id = line_item_data.get("price", {}).get("id")
            
            if line_item_data.get("period"):
                period = line_item_data["period"]
                line_item.period_start = datetime.fromtimestamp(period["start"], tz=timezone.utc)
                line_item.period_end = datetime.fromtimestamp(period["end"], tz=timezone.utc)
            
            return line_item
            
        except Exception as e:
            logger.error(f"Failed to sync invoice line item: {str(e)}")
            raise
    
    async def _sync_payment_method(
        self, 
        db: AsyncSession, 
        payment_method_data: Dict[str, Any], 
        user_id: int
    ) -> PaymentMethod:
        """Sync payment method data."""
        try:
            payment_method_id = payment_method_data["id"]
            
            # Check if payment method already exists
            result = await db.execute(
                select(PaymentMethod).where(
                    PaymentMethod.stripe_payment_method_id == payment_method_id
                )
            )
            payment_method = result.scalar_one_or_none()
            
            if not payment_method:
                payment_method = PaymentMethod(
                    user_id=user_id,
                    stripe_payment_method_id=payment_method_id
                )
                db.add(payment_method)
            
            # Update payment method details
            payment_method.type = payment_method_data["type"]
            
            # Update card details if applicable
            if payment_method_data["type"] == "card" and "card" in payment_method_data:
                card = payment_method_data["card"]
                payment_method.card_brand = card.get("brand")
                payment_method.card_last4 = card.get("last4")
                payment_method.card_exp_month = card.get("exp_month")
                payment_method.card_exp_year = card.get("exp_year")
            
            await db.commit()
            await db.refresh(payment_method)
            
            logger.info(f"Synced payment method: {payment_method.id}")
            return payment_method
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to sync payment method: {str(e)}")
            raise


# Create singleton instance
webhook_service = WebhookService()