"""
Email Service for DMCA Takedown Notices

Provides email dispatch functionality with SendGrid integration, SMTP fallback,
delivery tracking, and bounce handling for DMCA notices.
"""

import asyncio
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr, make_msgid
from typing import Dict, List, Optional, Any, Tuple
import re
from pathlib import Path

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType
import httpx

from ..models.takedown import TakedownRequest
from ..models.hosting import ContactInfo, DMCAAgent
from ..templates.template_renderer import TemplateRenderer
from ..utils.cache import CacheManager
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class EmailDeliveryStatus:
    """Email delivery status tracking."""
    
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"
    OPENED = "opened"
    CLICKED = "clicked"


class EmailService:
    """
    Comprehensive email service for DMCA takedown notices.
    """
    
    def __init__(
        self,
        sendgrid_api_key: Optional[str] = None,
        smtp_config: Optional[Dict[str, Any]] = None,
        template_renderer: Optional[TemplateRenderer] = None,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize email service.
        
        Args:
            sendgrid_api_key: SendGrid API key for primary email delivery
            smtp_config: SMTP configuration for fallback
            template_renderer: Template renderer for email content
            cache_manager: Cache for delivery tracking
            rate_limiter: Rate limiter for email sending
        """
        self.sendgrid_client = None
        self.smtp_config = smtp_config or {}
        self.template_renderer = template_renderer or TemplateRenderer()
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=100, time_window=60)
        
        # Initialize SendGrid if API key provided
        if sendgrid_api_key:
            try:
                self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
                logger.info("SendGrid client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {e}")
        
        # Email validation regex
        self.email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        # Delivery tracking
        self.delivery_callbacks: Dict[str, Any] = {}
    
    async def send_dmca_notice(
        self,
        takedown_request: TakedownRequest,
        recipient_email: str,
        agent_contact: Optional[DMCAAgent] = None,
        template_type: str = "standard",
        attachments: Optional[List[Dict[str, Any]]] = None,
        track_delivery: bool = True
    ) -> Dict[str, Any]:
        """
        Send DMCA takedown notice email.
        
        Args:
            takedown_request: Takedown request data
            recipient_email: Recipient email address
            agent_contact: DMCA agent contact information
            template_type: Type of DMCA notice (standard, followup, final)
            attachments: Optional list of attachments
            track_delivery: Whether to track email delivery
        
        Returns:
            Dict with sending results and tracking information
        """
        try:
            # Validate recipient email
            if not self._validate_email(recipient_email):
                raise ValueError(f"Invalid recipient email: {recipient_email}")
            
            # Rate limit check
            await self.rate_limiter.acquire()
            
            # Generate email content
            email_content = self.template_renderer.render_dmca_notice(
                takedown_request,
                agent_contact,
                template_type
            )
            
            # Prepare email data
            email_data = {
                'to_email': recipient_email,
                'subject': email_content['subject'],
                'body': email_content['body'],
                'from_email': agent_contact.email if agent_contact else takedown_request.creator_profile.email,
                'from_name': agent_contact.name if agent_contact else takedown_request.creator_profile.public_name,
                'reply_to': agent_contact.email if agent_contact else takedown_request.creator_profile.email,
                'attachments': attachments or [],
                'track_delivery': track_delivery,
                'template_type': template_type,
                'takedown_id': str(takedown_request.id)
            }
            
            # Send email via primary method (SendGrid) or fallback (SMTP)
            result = await self._send_email(email_data)
            
            # Update takedown request with email info
            if result.get('success'):
                takedown_request.email_message_id = result.get('message_id')
                takedown_request.notice_content = email_content['body']
                takedown_request.notice_sent_at = datetime.utcnow()
                takedown_request.update_status("notice_sent")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send DMCA notice: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def send_batch_notices(
        self,
        takedown_requests: List[TakedownRequest],
        recipient_emails: List[str],
        agent_contact: Optional[DMCAAgent] = None,
        template_type: str = "standard",
        max_concurrent: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Send multiple DMCA notices in batch.
        
        Args:
            takedown_requests: List of takedown requests
            recipient_emails: List of recipient emails (must match requests)
            agent_contact: DMCA agent contact
            template_type: Type of DMCA notice
            max_concurrent: Maximum concurrent sends
        
        Returns:
            Dict with successful and failed sends
        """
        if len(takedown_requests) != len(recipient_emails):
            raise ValueError("Number of requests must match number of recipients")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def send_single(request: TakedownRequest, email: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                result = await self.send_dmca_notice(
                    request, email, agent_contact, template_type
                )
                return str(request.id), result
        
        # Execute batch sends
        tasks = [
            send_single(req, email)
            for req, email in zip(takedown_requests, recipient_emails)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Categorize results
        successful = []
        failed = []
        
        for result in results:
            if isinstance(result, Exception):
                failed.append({
                    'error': str(result),
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                request_id, send_result = result
                if send_result.get('success'):
                    successful.append({
                        'request_id': request_id,
                        **send_result
                    })
                else:
                    failed.append({
                        'request_id': request_id,
                        **send_result
                    })
        
        return {
            'successful': successful,
            'failed': failed,
            'total_sent': len(successful),
            'total_failed': len(failed)
        }
    
    async def send_followup_notice(
        self,
        takedown_request: TakedownRequest,
        recipient_email: str,
        agent_contact: Optional[DMCAAgent] = None,
        followup_type: str = "followup"
    ) -> Dict[str, Any]:
        """
        Send follow-up notice for existing takedown request.
        
        Args:
            takedown_request: Original takedown request
            recipient_email: Recipient email
            agent_contact: DMCA agent contact
            followup_type: Type of follow-up (followup, final)
        
        Returns:
            Dict with sending results
        """
        # Increment follow-up count
        takedown_request.followup_count += 1
        takedown_request.last_followup_at = datetime.utcnow()
        
        # Send follow-up with appropriate template
        return await self.send_dmca_notice(
            takedown_request,
            recipient_email,
            agent_contact,
            followup_type
        )
    
    async def _send_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email using best available method.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            Dict with sending results
        """
        # Try SendGrid first
        if self.sendgrid_client:
            try:
                return await self._send_via_sendgrid(email_data)
            except Exception as e:
                logger.warning(f"SendGrid failed, falling back to SMTP: {e}")
        
        # Fallback to SMTP
        if self.smtp_config:
            try:
                return await self._send_via_smtp(email_data)
            except Exception as e:
                logger.error(f"SMTP also failed: {e}")
                return {
                    'success': False,
                    'error': f"All email methods failed. SendGrid: {e}",
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return {
            'success': False,
            'error': "No email delivery method configured",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _send_via_sendgrid(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via SendGrid API."""
        try:
            # Create SendGrid mail object
            mail = Mail(
                from_email=Email(email_data['from_email'], email_data['from_name']),
                to_emails=To(email_data['to_email']),
                subject=email_data['subject'],
                plain_text_content=Content("text/plain", email_data['body'])
            )
            
            # Set reply-to
            if email_data.get('reply_to'):
                mail.reply_to = Email(email_data['reply_to'])
            
            # Add tracking if enabled
            if email_data.get('track_delivery'):
                mail.tracking_settings = self._get_sendgrid_tracking_settings()
            
            # Add custom headers for tracking
            mail.headers = {
                'X-DMCA-Request-ID': email_data.get('takedown_id', ''),
                'X-DMCA-Template': email_data.get('template_type', 'standard')
            }
            
            # Add attachments
            for attachment in email_data.get('attachments', []):
                mail.add_attachment(self._create_sendgrid_attachment(attachment))
            
            # Send email
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.sendgrid_client.send, mail
            )
            
            # Extract message ID from response headers
            message_id = self._extract_message_id(response.headers)
            
            # Track delivery if enabled
            if email_data.get('track_delivery') and message_id:
                await self._track_email_delivery(message_id, email_data)
            
            return {
                'success': True,
                'message_id': message_id,
                'method': 'sendgrid',
                'status_code': response.status_code,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SendGrid sending failed: {e}")
            raise
    
    async def _send_via_smtp(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = formataddr((email_data['from_name'], email_data['from_email']))
            msg['To'] = email_data['to_email']
            msg['Subject'] = email_data['subject']
            msg['Message-ID'] = make_msgid(domain=email_data['from_email'].split('@')[1])
            
            if email_data.get('reply_to'):
                msg['Reply-To'] = email_data['reply_to']
            
            # Add custom headers
            msg['X-DMCA-Request-ID'] = email_data.get('takedown_id', '')
            msg['X-DMCA-Template'] = email_data.get('template_type', 'standard')
            
            # Add body
            msg.attach(MIMEText(email_data['body'], 'plain'))
            
            # Add attachments
            for attachment in email_data.get('attachments', []):
                part = MIMEApplication(
                    attachment['content'],
                    _subtype=attachment.get('type', 'octet-stream')
                )
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=attachment['filename']
                )
                msg.attach(part)
            
            # Send via SMTP
            await asyncio.get_event_loop().run_in_executor(
                None, self._smtp_send, msg, email_data['to_email']
            )
            
            message_id = msg['Message-ID']
            
            # Track delivery if enabled
            if email_data.get('track_delivery') and message_id:
                await self._track_email_delivery(message_id, email_data)
            
            return {
                'success': True,
                'message_id': message_id,
                'method': 'smtp',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            raise
    
    def _smtp_send(self, msg: MIMEMultipart, to_email: str) -> None:
        """Send email via SMTP (blocking)."""
        config = self.smtp_config
        
        with smtplib.SMTP(config.get('host'), config.get('port', 587)) as server:
            server.starttls()
            server.login(config.get('username'), config.get('password'))
            server.send_message(msg, to_addrs=[to_email])
    
    def _get_sendgrid_tracking_settings(self) -> Dict[str, Any]:
        """Get SendGrid tracking settings."""
        return {
            "click_tracking": {"enable": True},
            "open_tracking": {"enable": True},
            "subscription_tracking": {"enable": False},
            "ganalytics": {"enable": False}
        }
    
    def _create_sendgrid_attachment(self, attachment_data: Dict[str, Any]) -> Attachment:
        """Create SendGrid attachment from data."""
        return Attachment(
            FileContent(attachment_data['content']),
            FileName(attachment_data['filename']),
            FileType(attachment_data.get('type', 'application/octet-stream'))
        )
    
    def _extract_message_id(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract message ID from response headers."""
        # SendGrid returns message ID in X-Message-Id header
        return headers.get('X-Message-Id') or headers.get('x-message-id')
    
    async def _track_email_delivery(self, message_id: str, email_data: Dict[str, Any]) -> None:
        """Track email delivery status."""
        tracking_data = {
            'message_id': message_id,
            'to_email': email_data['to_email'],
            'status': EmailDeliveryStatus.SENT,
            'sent_at': datetime.utcnow().isoformat(),
            'takedown_id': email_data.get('takedown_id'),
            'template_type': email_data.get('template_type')
        }
        
        # Store in cache for tracking
        cache_key = f"email_tracking:{message_id}"
        await self.cache_manager.set(cache_key, tracking_data, ttl=timedelta(days=30))
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format."""
        return bool(self.email_regex.match(email.strip().lower()))
    
    async def get_delivery_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get email delivery status.
        
        Args:
            message_id: Email message ID
        
        Returns:
            Dict with delivery status information
        """
        try:
            cache_key = f"email_tracking:{message_id}"
            return await self.cache_manager.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get delivery status: {e}")
            return None
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Handle webhook notifications from email provider.
        
        Args:
            webhook_data: Webhook payload data
        
        Returns:
            True if handled successfully
        """
        try:
            # Handle SendGrid webhooks
            if 'sg_message_id' in webhook_data or 'message-id' in webhook_data:
                return await self._handle_sendgrid_webhook(webhook_data)
            
            logger.warning(f"Unknown webhook format: {webhook_data}")
            return False
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return False
    
    async def _handle_sendgrid_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Handle SendGrid webhook notifications."""
        try:
            message_id = webhook_data.get('sg_message_id') or webhook_data.get('message-id')
            event_type = webhook_data.get('event')
            
            if not message_id or not event_type:
                return False
            
            # Get existing tracking data
            cache_key = f"email_tracking:{message_id}"
            tracking_data = await self.cache_manager.get(cache_key)
            
            if not tracking_data:
                tracking_data = {
                    'message_id': message_id,
                    'status': EmailDeliveryStatus.SENT
                }
            
            # Update status based on event
            status_mapping = {
                'delivered': EmailDeliveryStatus.DELIVERED,
                'bounce': EmailDeliveryStatus.BOUNCED,
                'dropped': EmailDeliveryStatus.FAILED,
                'open': EmailDeliveryStatus.OPENED,
                'click': EmailDeliveryStatus.CLICKED
            }
            
            new_status = status_mapping.get(event_type)
            if new_status:
                tracking_data['status'] = new_status
                tracking_data[f'{event_type}_at'] = webhook_data.get('timestamp')
                
                # Update cache
                await self.cache_manager.set(cache_key, tracking_data, ttl=timedelta(days=30))
                
                # If this is a takedown request, update its status
                if tracking_data.get('takedown_id'):
                    await self._update_takedown_status(tracking_data)
            
            return True
            
        except Exception as e:
            logger.error(f"SendGrid webhook handling failed: {e}")
            return False
    
    async def _update_takedown_status(self, tracking_data: Dict[str, Any]) -> None:
        """Update takedown request status based on email delivery."""
        # In a full implementation, this would update the database
        # For now, just log the status change
        takedown_id = tracking_data.get('takedown_id')
        status = tracking_data.get('status')
        
        logger.info(f"Takedown {takedown_id} email status updated to: {status}")
    
    async def validate_email_deliverability(self, email: str) -> Dict[str, Any]:
        """
        Validate email deliverability (basic check).
        
        Args:
            email: Email address to validate
        
        Returns:
            Dict with validation results
        """
        try:
            if not self._validate_email(email):
                return {
                    'valid': False,
                    'reason': 'Invalid email format',
                    'deliverable': False
                }
            
            # Extract domain
            domain = email.split('@')[1]
            
            # Basic MX record check (simplified)
            try:
                import socket
                mx_records = socket.getaddrinfo(domain, None)
                has_mx = len(mx_records) > 0
            except socket.gaierror:
                has_mx = False
            
            return {
                'valid': True,
                'deliverable': has_mx,
                'domain': domain,
                'has_mx_record': has_mx,
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'reason': str(e),
                'deliverable': False
            }
    
    async def get_bounce_list(self) -> List[Dict[str, Any]]:
        """Get list of bounced emails."""
        try:
            # This would query the email provider's bounce list API
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Failed to get bounce list: {e}")
            return []
    
    async def cleanup_old_tracking_data(self, days_old: int = 90) -> int:
        """
        Clean up old email tracking data.
        
        Args:
            days_old: Remove tracking data older than this many days
        
        Returns:
            Number of records cleaned up
        """
        # This would clean up old tracking data from cache/database
        # Implementation depends on your specific storage solution
        return 0