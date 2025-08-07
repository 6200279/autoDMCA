"""
Notification sender for DMCA processing updates and alerts.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from ..config import ScannerSettings
from .dmca_queue import DMCARequest, DMCAStatus


logger = structlog.get_logger(__name__)


class NotificationLevel(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Represents a notification to be sent."""
    
    recipient: str  # email, webhook URL, user ID, etc.
    notification_type: str  # email, webhook, sms, push
    level: NotificationLevel
    subject: str
    message: str
    data: Dict[str, Any]
    
    # Timing
    created_at: float = None
    send_after: float = None  # Delay sending until this time
    expires_at: float = None
    
    # Delivery tracking
    attempts: int = 0
    max_attempts: int = 3
    last_attempt_at: float = None
    delivered: bool = False
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        
        if self.expires_at is None:
            # Default expiration: 24 hours
            self.expires_at = self.created_at + (24 * 60 * 60)
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        return time.time() > self.expires_at
    
    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return (
            not self.delivered and
            self.attempts < self.max_attempts and
            not self.is_expired
        )
    
    @property
    def is_ready_to_send(self) -> bool:
        """Check if notification is ready to be sent."""
        current_time = time.time()
        return (
            not self.delivered and
            not self.is_expired and
            (self.send_after is None or current_time >= self.send_after)
        )


class EmailNotificationSender:
    """Sends notifications via email using SendGrid."""
    
    def __init__(self, api_key: str, from_email: str, from_name: str = "AutoDMCA"):
        self.client = SendGridAPIClient(api_key) if api_key else None
        self.from_email = from_email
        self.from_name = from_name
        
    async def send(self, notification: Notification) -> bool:
        """Send email notification."""
        if not self.client:
            logger.warning("SendGrid not configured - email notification skipped")
            return False
        
        try:
            mail = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(notification.recipient),
                subject=notification.subject,
                html_content=Content("text/html", self._format_html_message(notification))
            )
            
            response = self.client.send(mail)
            success = response.status_code in [200, 202]
            
            if success:
                logger.info(f"Email sent successfully to {notification.recipient}")
            else:
                logger.warning(f"Email send failed: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send email to {notification.recipient}", error=str(e))
            return False
    
    def _format_html_message(self, notification: Notification) -> str:
        """Format notification message as HTML."""
        html = f"""
        <html>
        <body>
        <h2>{notification.subject}</h2>
        <p>{notification.message}</p>
        
        <h3>Details:</h3>
        <ul>
        """
        
        for key, value in notification.data.items():
            html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        
        html += """
        </ul>
        
        <p><em>This is an automated notification from AutoDMCA.</em></p>
        </body>
        </html>
        """
        
        return html


class WebhookNotificationSender:
    """Sends notifications via HTTP webhooks."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def send(self, notification: Notification) -> bool:
        """Send webhook notification."""
        if not self.session:
            await self.initialize()
        
        try:
            payload = {
                'event': 'dmca_notification',
                'level': notification.level.value,
                'subject': notification.subject,
                'message': notification.message,
                'timestamp': notification.created_at,
                'data': notification.data
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'AutoDMCA-Notifications/1.0'
            }
            
            async with self.session.post(
                notification.recipient,  # recipient is webhook URL
                json=payload,
                headers=headers
            ) as response:
                success = 200 <= response.status < 300
                
                if success:
                    logger.info(f"Webhook sent successfully to {notification.recipient}")
                else:
                    logger.warning(f"Webhook failed: {response.status}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to send webhook to {notification.recipient}", error=str(e))
            return False


class NotificationSender:
    """Main notification sender that handles multiple channels."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        
        # Initialize senders
        self.email_sender = None
        if hasattr(settings, 'sendgrid_api_key') and settings.sendgrid_api_key:
            self.email_sender = EmailNotificationSender(
                settings.sendgrid_api_key,
                settings.dmca_sender_email,
                settings.dmca_sender_name
            )
        
        self.webhook_sender = WebhookNotificationSender()
        
        # Notification queue
        self.notification_queue = []
        self._queue_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the notification sender."""
        await self.webhook_sender.initialize()
        logger.info("Notification sender initialized")
    
    async def close(self):
        """Clean up resources."""
        await self.webhook_sender.close()
    
    async def send_dmca_status_update(
        self,
        request: DMCARequest,
        recipient_email: str,
        level: NotificationLevel = NotificationLevel.MEDIUM
    ):
        """Send DMCA status update notification."""
        subject = f"DMCA Request Update - {request.status.value.title()}"
        
        message = self._create_dmca_status_message(request)
        
        notification = Notification(
            recipient=recipient_email,
            notification_type="email",
            level=level,
            subject=subject,
            message=message,
            data={
                'request_id': request.request_id,
                'status': request.status.value,
                'url': request.infringing_url,
                'hosting_provider': request.hosting_provider,
                'created_at': request.created_at,
                'updated_at': request.updated_at
            }
        )
        
        await self.queue_notification(notification)
    
    def _create_dmca_status_message(self, request: DMCARequest) -> str:
        """Create status update message for DMCA request."""
        status_messages = {
            DMCAStatus.PENDING: "Your DMCA request has been received and is pending processing.",
            DMCAStatus.PROCESSING: "Your DMCA request is currently being processed.",
            DMCAStatus.SENT: "Your DMCA takedown notice has been sent to the hosting provider.",
            DMCAStatus.ACKNOWLEDGED: "The hosting provider has acknowledged your DMCA request.",
            DMCAStatus.COMPLIED: "Great news! The infringing content has been removed.",
            DMCAStatus.REJECTED: "The hosting provider has rejected your DMCA request.",
            DMCAStatus.FAILED: "We encountered an issue processing your DMCA request.",
            DMCAStatus.DELISTED: "The infringing content has been removed from search engines.",
            DMCAStatus.EXPIRED: "Your DMCA request has expired without resolution."
        }
        
        base_message = status_messages.get(
            request.status,
            f"Your DMCA request status has been updated to: {request.status.value}"
        )
        
        # Add additional context based on status
        if request.status == DMCAStatus.SENT:
            base_message += f"\n\nWe expect a response within 14 days. The hosting provider is: {request.hosting_provider}"
        
        elif request.status == DMCAStatus.FAILED and request.notes:
            latest_note = request.notes[-1] if request.notes else ""
            base_message += f"\n\nReason: {latest_note}"
        
        elif request.status == DMCAStatus.COMPLIED:
            base_message += "\n\nThe infringing URL should no longer be accessible."
        
        base_message += f"\n\nInfringing URL: {request.infringing_url}"
        base_message += f"\nRequest ID: {request.request_id}"
        
        return base_message
    
    async def send_content_match_alert(
        self,
        person_id: str,
        matches: List[Any],  # ContentMatch objects
        recipient_email: str,
        level: NotificationLevel = NotificationLevel.HIGH
    ):
        """Send alert about new content matches found."""
        match_count = len(matches)
        high_confidence_count = len([m for m in matches if m.is_high_confidence])
        
        if match_count == 1:
            subject = "New Content Match Found"
        else:
            subject = f"{match_count} New Content Matches Found"
        
        message = f"We found {match_count} potential matches for your protected content.\n\n"
        
        if high_confidence_count > 0:
            message += f"{high_confidence_count} are high-confidence matches.\n\n"
        
        message += "Details:\n"
        
        for i, match in enumerate(matches[:5], 1):  # Limit to first 5 matches
            message += f"\n{i}. {match.content.title}\n"
            message += f"   URL: {match.content.url}\n"
            message += f"   Site: {match.content.site_name}\n"
            message += f"   Confidence: {match.confidence_score:.2%}\n"
            message += f"   Match Types: {match.match_summary}\n"
        
        if len(matches) > 5:
            message += f"\n... and {len(matches) - 5} more matches."
        
        message += "\n\nWe will automatically process DMCA takedown requests for high-confidence matches."
        
        notification = Notification(
            recipient=recipient_email,
            notification_type="email",
            level=level,
            subject=subject,
            message=message,
            data={
                'person_id': person_id,
                'total_matches': match_count,
                'high_confidence_matches': high_confidence_count,
                'matches': [
                    {
                        'url': m.content.url,
                        'confidence': m.confidence_score,
                        'site': m.content.site_name
                    }
                    for m in matches
                ]
            }
        )
        
        await self.queue_notification(notification)
    
    async def send_system_alert(
        self,
        alert_type: str,
        message: str,
        admin_emails: List[str],
        level: NotificationLevel = NotificationLevel.CRITICAL,
        **additional_data
    ):
        """Send system alert to administrators."""
        subject = f"AutoDMCA System Alert: {alert_type}"
        
        for admin_email in admin_emails:
            notification = Notification(
                recipient=admin_email,
                notification_type="email", 
                level=level,
                subject=subject,
                message=message,
                data={
                    'alert_type': alert_type,
                    'timestamp': time.time(),
                    **additional_data
                }
            )
            
            await self.queue_notification(notification)
    
    async def send_webhook_notification(
        self,
        webhook_url: str,
        event_type: str,
        data: Dict[str, Any],
        level: NotificationLevel = NotificationLevel.MEDIUM
    ):
        """Send webhook notification."""
        notification = Notification(
            recipient=webhook_url,
            notification_type="webhook",
            level=level,
            subject=f"AutoDMCA Event: {event_type}",
            message=f"Event type: {event_type}",
            data={
                'event_type': event_type,
                **data
            }
        )
        
        await self.queue_notification(notification)
    
    async def queue_notification(self, notification: Notification):
        """Add notification to the sending queue."""
        async with self._queue_lock:
            self.notification_queue.append(notification)
        
        logger.debug(
            f"Notification queued",
            recipient=notification.recipient,
            type=notification.notification_type,
            level=notification.level.value
        )
    
    async def process_notification_queue(self, batch_size: int = 10) -> int:
        """Process queued notifications."""
        processed = 0
        
        async with self._queue_lock:
            # Get ready notifications
            ready_notifications = [
                n for n in self.notification_queue
                if n.is_ready_to_send and n.can_retry
            ]
            
            # Process in batches
            for notification in ready_notifications[:batch_size]:
                try:
                    success = await self._send_notification(notification)
                    
                    notification.attempts += 1
                    notification.last_attempt_at = time.time()
                    
                    if success:
                        notification.delivered = True
                        processed += 1
                    else:
                        notification.error = "Send failed"
                    
                except Exception as e:
                    notification.attempts += 1
                    notification.last_attempt_at = time.time()
                    notification.error = str(e)
                    logger.error(f"Notification send failed", error=str(e))
            
            # Remove delivered or expired notifications
            self.notification_queue = [
                n for n in self.notification_queue
                if not n.delivered and not n.is_expired and n.can_retry
            ]
        
        if processed > 0:
            logger.info(f"Processed {processed} notifications")
        
        return processed
    
    async def _send_notification(self, notification: Notification) -> bool:
        """Send individual notification based on type."""
        if notification.notification_type == "email" and self.email_sender:
            return await self.email_sender.send(notification)
        
        elif notification.notification_type == "webhook":
            return await self.webhook_sender.send(notification)
        
        else:
            logger.warning(f"Unsupported notification type: {notification.notification_type}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get notification queue statistics."""
        async with self._queue_lock:
            stats = {
                'total_queued': len(self.notification_queue),
                'ready_to_send': len([n for n in self.notification_queue if n.is_ready_to_send]),
                'delivered': len([n for n in self.notification_queue if n.delivered]),
                'failed': len([n for n in self.notification_queue if not n.can_retry and not n.delivered]),
                'expired': len([n for n in self.notification_queue if n.is_expired])
            }
        
        return stats
    
    async def cleanup_old_notifications(self, hours_old: int = 24) -> int:
        """Clean up old delivered/failed notifications."""
        cutoff_time = time.time() - (hours_old * 60 * 60)
        
        async with self._queue_lock:
            original_count = len(self.notification_queue)
            
            self.notification_queue = [
                n for n in self.notification_queue
                if (
                    n.created_at > cutoff_time or
                    (not n.delivered and not n.is_expired and n.can_retry)
                )
            ]
            
            cleaned_count = original_count - len(self.notification_queue)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old notifications")
        
        return cleaned_count