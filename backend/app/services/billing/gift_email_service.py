import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models.gift_subscription import GiftSubscription, GiftEmailLog
from app.core.config import settings
from app.services.email.email_service import email_service
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class GiftEmailService:
    """Service for handling gift subscription email notifications."""
    
    def __init__(self):
        self.templates = {
            "gift_notification": {
                "subject_template": "🎁 You've received a gift subscription!",
                "template_name": "gift_notification"
            },
            "gift_confirmation": {
                "subject_template": "✅ Gift subscription purchase confirmed",
                "template_name": "gift_confirmation"
            },
            "redemption_confirmation": {
                "subject_template": "🎉 Gift subscription activated!",
                "template_name": "redemption_confirmation"
            },
            "gift_reminder": {
                "subject_template": "⏰ Don't forget to redeem your gift subscription",
                "template_name": "gift_reminder"
            },
            "gift_expiry_warning": {
                "subject_template": "⚠️ Your gift subscription expires soon",
                "template_name": "gift_expiry_warning"
            },
            "gift_cancellation": {
                "subject_template": "❌ Gift subscription cancelled",
                "template_name": "gift_cancellation"
            }
        }
    
    async def send_gift_notification_email(
        self,
        gift_subscription_id: int,
        db: Session = None
    ) -> bool:
        """Send notification email to gift recipient."""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            gift = db.query(GiftSubscription).filter(
                GiftSubscription.id == gift_subscription_id
            ).first()
            
            if not gift:
                logger.error(f"Gift subscription {gift_subscription_id} not found")
                return False
            
            # Check if notification already sent
            existing_log = db.query(GiftEmailLog).filter(
                GiftEmailLog.gift_subscription_id == gift_subscription_id,
                GiftEmailLog.email_type == "gift_notification",
                GiftEmailLog.sent_at.isnot(None)
            ).first()
            
            if existing_log:
                logger.info(f"Gift notification already sent for gift {gift_subscription_id}")
                return True
            
            # Prepare email data
            template_config = self.templates["gift_notification"]
            sender_name = gift.custom_sender_name or gift.giver_name
            plan_name = gift.plan.value.title()
            interval_name = gift.billing_interval.value.title()
            
            email_data = {
                "recipient_email": gift.recipient_email,
                "recipient_name": gift.recipient_name or "Friend",
                "sender_name": sender_name,
                "giver_email": gift.giver_email,
                "plan_name": plan_name,
                "interval_name": interval_name,
                "amount": float(gift.amount),
                "currency": gift.currency,
                "gift_code": gift.gift_code,
                "personal_message": gift.personal_message,
                "redemption_url": self._generate_redemption_url(gift.gift_code),
                "expires_at": gift.expires_at.isoformat(),
                "support_email": settings.SUPPORT_EMAIL,
                "company_name": settings.COMPANY_NAME,
                "platform_url": settings.FRONTEND_URL
            }
            
            # Send email
            success = await self._send_email(
                email_type="gift_notification",
                recipient_email=gift.recipient_email,
                subject=template_config["subject_template"],
                template_name=template_config["template_name"],
                template_data=email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            if success:
                # Update gift with email sent timestamp
                gift.gift_email_sent_at = datetime.now(timezone.utc)
                db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending gift notification email: {str(e)}")
            return False
        finally:
            if close_db:
                db.close()
    
    async def send_gift_confirmation_email(
        self,
        gift_subscription_id: int,
        db: Session = None
    ) -> bool:
        """Send confirmation email to gift giver after purchase."""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            gift = db.query(GiftSubscription).filter(
                GiftSubscription.id == gift_subscription_id
            ).first()
            
            if not gift:
                logger.error(f"Gift subscription {gift_subscription_id} not found")
                return False
            
            # Prepare email data
            template_config = self.templates["gift_confirmation"]
            plan_name = gift.plan.value.title()
            interval_name = gift.billing_interval.value.title()
            
            email_data = {
                "giver_name": gift.giver_name,
                "recipient_email": gift.recipient_email,
                "recipient_name": gift.recipient_name or "the recipient",
                "plan_name": plan_name,
                "interval_name": interval_name,
                "amount": float(gift.amount),
                "currency": gift.currency,
                "gift_code": gift.gift_code,
                "redemption_url": self._generate_redemption_url(gift.gift_code),
                "expires_at": gift.expires_at.isoformat(),
                "transaction_id": gift.stripe_payment_intent_id,
                "receipt_url": gift.gift_transaction.receipt_url if gift.gift_transaction else None,
                "support_email": settings.SUPPORT_EMAIL,
                "company_name": settings.COMPANY_NAME,
                "platform_url": settings.FRONTEND_URL
            }
            
            # Send email
            success = await self._send_email(
                email_type="gift_confirmation",
                recipient_email=gift.giver_email,
                subject=template_config["subject_template"],
                template_name=template_config["template_name"],
                template_data=email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending gift confirmation email: {str(e)}")
            return False
        finally:
            if close_db:
                db.close()
    
    async def send_redemption_confirmation_email(
        self,
        gift_subscription_id: int,
        db: Session = None
    ) -> bool:
        """Send confirmation email after gift redemption."""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            gift = db.query(GiftSubscription).filter(
                GiftSubscription.id == gift_subscription_id
            ).first()
            
            if not gift or not gift.created_subscription:
                logger.error(f"Gift subscription {gift_subscription_id} not found or not redeemed")
                return False
            
            # Prepare email data
            template_config = self.templates["redemption_confirmation"]
            plan_name = gift.plan.value.title()
            interval_name = gift.billing_interval.value.title()
            subscription = gift.created_subscription
            
            email_data = {
                "recipient_name": gift.recipient_name or "there",
                "sender_name": gift.custom_sender_name or gift.giver_name,
                "plan_name": plan_name,
                "interval_name": interval_name,
                "subscription_start": subscription.current_period_start.isoformat(),
                "subscription_end": subscription.current_period_end.isoformat(),
                "features": self._get_plan_features(gift.plan),
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "support_email": settings.SUPPORT_EMAIL,
                "company_name": settings.COMPANY_NAME
            }
            
            # Send to recipient
            recipient_success = await self._send_email(
                email_type="redemption_confirmation",
                recipient_email=gift.recipient_email,
                subject=template_config["subject_template"],
                template_name=template_config["template_name"],
                template_data=email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            # Also notify the giver
            giver_email_data = email_data.copy()
            giver_email_data.update({
                "recipient_name": gift.giver_name,
                "gift_recipient_name": gift.recipient_name or gift.recipient_email
            })
            
            giver_success = await self._send_email(
                email_type="redemption_confirmation",
                recipient_email=gift.giver_email,
                subject=f"✅ Your gift to {gift.recipient_email} has been redeemed!",
                template_name="gift_redeemed_notification",
                template_data=giver_email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            return recipient_success and giver_success
            
        except Exception as e:
            logger.error(f"Error sending redemption confirmation email: {str(e)}")
            return False
        finally:
            if close_db:
                db.close()
    
    async def send_gift_reminder_email(
        self,
        gift_subscription_id: int,
        db: Session = None
    ) -> bool:
        """Send reminder email to unredeemed gift recipient."""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            gift = db.query(GiftSubscription).filter(
                GiftSubscription.id == gift_subscription_id
            ).first()
            
            if not gift or gift.status.value != "pending":
                logger.warning(f"Gift subscription {gift_subscription_id} not eligible for reminder")
                return False
            
            # Check reminder limits
            if gift.reminder_emails_sent >= 3:  # Max 3 reminders
                logger.info(f"Maximum reminders sent for gift {gift_subscription_id}")
                return False
            
            # Prepare email data
            template_config = self.templates["gift_reminder"]
            days_left = gift.days_until_expiry()
            sender_name = gift.custom_sender_name or gift.giver_name
            
            email_data = {
                "recipient_name": gift.recipient_name or "Friend",
                "sender_name": sender_name,
                "days_left": days_left,
                "gift_code": gift.gift_code,
                "redemption_url": self._generate_redemption_url(gift.gift_code),
                "plan_name": gift.plan.value.title(),
                "interval_name": gift.billing_interval.value.title(),
                "support_email": settings.SUPPORT_EMAIL,
                "company_name": settings.COMPANY_NAME
            }
            
            # Send email
            success = await self._send_email(
                email_type="gift_reminder",
                recipient_email=gift.recipient_email,
                subject=template_config["subject_template"],
                template_name=template_config["template_name"],
                template_data=email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            if success:
                # Update reminder count
                gift.reminder_emails_sent += 1
                gift.last_reminder_sent_at = datetime.now(timezone.utc)
                db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending gift reminder email: {str(e)}")
            return False
        finally:
            if close_db:
                db.close()
    
    async def _send_email(
        self,
        email_type: str,
        recipient_email: str,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        gift_subscription_id: int,
        db: Session
    ) -> bool:
        """Internal method to send email and log the attempt."""
        try:
            # Create email log entry
            email_log = GiftEmailLog(
                gift_subscription_id=gift_subscription_id,
                email_type=email_type,
                recipient_email=recipient_email,
                subject=subject,
                template_name=template_name,
                template_version="1.0"
            )
            
            db.add(email_log)
            db.flush()  # Get the ID
            
            # Attempt to send email
            success = await email_service.send_template_email(
                to_email=recipient_email,
                subject=subject,
                template_name=template_name,
                template_data=template_data
            )
            
            if success:
                email_log.sent_at = datetime.now(timezone.utc)
                email_log.email_provider = "sendgrid"  # or whatever provider is used
                logger.info(f"Gift email sent successfully: {email_type} to {recipient_email}")
            else:
                email_log.failed_at = datetime.now(timezone.utc)
                email_log.failure_reason = "Email service failed"
                logger.error(f"Failed to send gift email: {email_type} to {recipient_email}")
            
            db.commit()
            return success
            
        except Exception as e:
            email_log.failed_at = datetime.now(timezone.utc)
            email_log.failure_reason = str(e)
            email_log.retry_count += 1
            db.commit()
            
            logger.error(f"Error sending gift email: {str(e)}")
            return False
    
    def _generate_redemption_url(self, gift_code: str) -> str:
        """Generate redemption URL for a gift code."""
        return f"{settings.FRONTEND_URL}/gift/redeem?code={gift_code}"
    
    def _get_plan_features(self, plan) -> List[str]:
        """Get feature list for a subscription plan."""
        from app.services.billing.stripe_service import SUBSCRIPTION_PLANS
        
        if plan.value in SUBSCRIPTION_PLANS:
            features = SUBSCRIPTION_PLANS[plan.value]["features"]
            limits = SUBSCRIPTION_PLANS[plan.value]["limits"]
            
            feature_list = []
            feature_list.append(f"Up to {limits['max_protected_profiles']} protected profiles")
            feature_list.append(f"{limits['max_monthly_scans']:,} monthly scans")
            feature_list.append(f"{limits['max_takedown_requests']} takedown requests per month")
            
            if features["ai_face_recognition"]:
                feature_list.append("AI-powered face recognition")
            if features["priority_support"]:
                feature_list.append("Priority customer support")
            if features["custom_branding"]:
                feature_list.append("Custom branding options")
            if features["api_access"]:
                feature_list.append("Full API access")
            
            return feature_list
        
        return ["Full platform access"]
    
    async def send_gift_expiry_warning(
        self,
        gift_subscription_id: int,
        db: Session = None
    ) -> bool:
        """Send warning email when gift is about to expire."""
        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            gift = db.query(GiftSubscription).filter(
                GiftSubscription.id == gift_subscription_id
            ).first()
            
            if not gift or gift.status.value != "pending":
                return False
            
            days_left = gift.days_until_expiry()
            if days_left > 7:  # Only send warning in last 7 days
                return False
            
            template_config = self.templates["gift_expiry_warning"]
            sender_name = gift.custom_sender_name or gift.giver_name
            
            email_data = {
                "recipient_name": gift.recipient_name or "Friend",
                "sender_name": sender_name,
                "days_left": days_left,
                "gift_code": gift.gift_code,
                "redemption_url": self._generate_redemption_url(gift.gift_code),
                "plan_name": gift.plan.value.title(),
                "support_email": settings.SUPPORT_EMAIL,
                "company_name": settings.COMPANY_NAME
            }
            
            success = await self._send_email(
                email_type="gift_expiry_warning",
                recipient_email=gift.recipient_email,
                subject=template_config["subject_template"],
                template_name=template_config["template_name"],
                template_data=email_data,
                gift_subscription_id=gift_subscription_id,
                db=db
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending gift expiry warning: {str(e)}")
            return False
        finally:
            if close_db:
                db.close()


# Create singleton instance
gift_email_service = GiftEmailService()