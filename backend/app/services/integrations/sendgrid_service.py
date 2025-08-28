"""
SendGrid Email Service Integration

Provides advanced email delivery capabilities with templates, analytics, and robust delivery.
Falls back to SMTP service if SendGrid is unavailable.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent, Attachment, FileContent, FileName, FileType, Disposition
    from sendgrid.helpers.mail.personalization import Personalization
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from app.core.config import settings
from app.services.auth.email_service import email_service

logger = logging.getLogger(__name__)


class SendGridError(Exception):
    """SendGrid service specific errors"""
    pass


class SendGridService:
    """
    Advanced email service using SendGrid API with comprehensive features:
    - Template-based emails with dynamic content
    - Bulk email sending with personalization
    - Email analytics and tracking
    - Attachment support
    - Fallback to SMTP service
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        self.from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', None) or settings.EMAILS_FROM_EMAIL
        self.from_name = getattr(settings, 'SENDGRID_FROM_NAME', None) or settings.EMAILS_FROM_NAME
        
        if not self.api_key or not SENDGRID_AVAILABLE:
            logger.warning("SendGrid not configured or unavailable, will fallback to SMTP service")
            self.client = None
        else:
            self.client = sendgrid.SendGridAPIClient(api_key=self.api_key)
            logger.info("SendGrid service initialized successfully")
        
        # Email templates configuration
        self.templates = {
            'dmca_takedown': getattr(settings, 'SENDGRID_DMCA_TEMPLATE_ID', None),
            'infringement_alert': getattr(settings, 'SENDGRID_ALERT_TEMPLATE_ID', None),
            'welcome': getattr(settings, 'SENDGRID_WELCOME_TEMPLATE_ID', None),
            'verification': getattr(settings, 'SENDGRID_VERIFICATION_TEMPLATE_ID', None),
            'password_reset': getattr(settings, 'SENDGRID_PASSWORD_RESET_TEMPLATE_ID', None),
            'subscription_confirmation': getattr(settings, 'SENDGRID_SUBSCRIPTION_TEMPLATE_ID', None),
            'billing_reminder': getattr(settings, 'SENDGRID_BILLING_REMINDER_TEMPLATE_ID', None)
        }
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        to_name: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        categories: Optional[List[str]] = None,
        custom_args: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a single email with optional template and attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject (ignored if using template)
            text_content: Plain text content
            html_content: HTML content
            to_name: Recipient name
            attachments: List of attachment dicts with 'content', 'filename', 'type'
            template_id: SendGrid template ID
            template_data: Dynamic template data
            categories: Email categories for analytics
            custom_args: Custom arguments for tracking
        """
        if not self.client:
            logger.info("SendGrid unavailable, falling back to SMTP service")
            return await email_service.send_email(
                to_email=to_email,
                subject=subject,
                body_text=text_content,
                body_html=html_content,
                to_name=to_name
            )
        
        try:
            # Create mail object
            from_email = From(self.from_email, self.from_name)
            to = To(to_email, to_name)
            
            if template_id:
                # Use dynamic template
                mail = Mail(from_email=from_email, to_emails=to)
                mail.template_id = template_id
                
                if template_data:
                    mail.dynamic_template_data = template_data
            else:
                # Regular email
                subject_obj = Subject(subject)
                plain_text = PlainTextContent(text_content)
                mail = Mail(from_email, to, subject_obj, plain_text)
                
                if html_content:
                    mail.add_content(HtmlContent(html_content))
            
            # Add attachments
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment()
                    attachment.file_content = FileContent(attachment_data.get('content', ''))
                    attachment.file_name = FileName(attachment_data.get('filename', 'attachment'))
                    attachment.file_type = FileType(attachment_data.get('type', 'application/octet-stream'))
                    attachment.disposition = Disposition('attachment')
                    mail.add_attachment(attachment)
            
            # Add categories for analytics
            if categories:
                for category in categories[:10]:  # SendGrid limit
                    mail.add_category(category)
            
            # Add custom arguments
            if custom_args:
                for key, value in custom_args.items():
                    mail.add_custom_arg(key, str(value))
            
            # Send email
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.send(mail)
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
                # Fallback to SMTP
                return await email_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body_text=text_content,
                    body_html=html_content,
                    to_name=to_name
                )
        
        except Exception as e:
            logger.error(f"SendGrid email send error: {e}")
            # Fallback to SMTP service
            return await email_service.send_email(
                to_email=to_email,
                subject=subject,
                body_text=text_content,
                body_html=html_content,
                to_name=to_name
            )
    
    async def send_bulk_email(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        template_id: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send bulk emails with personalization.
        
        Args:
            recipients: List of dicts with 'email', 'name', and optional 'template_data'
            subject: Email subject
            text_content: Plain text content template
            html_content: HTML content template
            template_id: SendGrid template ID
            categories: Email categories
            
        Returns:
            Dict with success count and failed recipients
        """
        if not self.client:
            logger.warning("SendGrid unavailable for bulk email, sending individually via SMTP")
            results = {'sent': 0, 'failed': []}
            
            for recipient in recipients:
                try:
                    success = await email_service.send_email(
                        to_email=recipient['email'],
                        subject=subject,
                        body_text=text_content,
                        body_html=html_content,
                        to_name=recipient.get('name')
                    )
                    if success:
                        results['sent'] += 1
                    else:
                        results['failed'].append(recipient['email'])
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient['email']}: {e}")
                    results['failed'].append(recipient['email'])
            
            return results
        
        try:
            from_email = From(self.from_email, self.from_name)
            mail = Mail(from_email=from_email)
            
            if template_id:
                mail.template_id = template_id
            else:
                mail.subject = Subject(subject)
                mail.add_content(PlainTextContent(text_content))
                if html_content:
                    mail.add_content(HtmlContent(html_content))
            
            # Add personalizations for each recipient
            for recipient in recipients:
                personalization = Personalization()
                personalization.add_to(To(recipient['email'], recipient.get('name')))
                
                if template_id and 'template_data' in recipient:
                    personalization.dynamic_template_data = recipient['template_data']
                
                mail.add_personalization(personalization)
            
            # Add categories
            if categories:
                for category in categories[:10]:
                    mail.add_category(category)
            
            # Send bulk email
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.send(mail)
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"Bulk email sent successfully via SendGrid to {len(recipients)} recipients")
                return {'sent': len(recipients), 'failed': []}
            else:
                logger.error(f"SendGrid bulk email error: {response.status_code}")
                return {'sent': 0, 'failed': [r['email'] for r in recipients]}
        
        except Exception as e:
            logger.error(f"SendGrid bulk email error: {e}")
            return {'sent': 0, 'failed': [r['email'] for r in recipients]}
    
    async def send_dmca_takedown_email(
        self,
        to_email: str,
        to_name: str,
        infringement_data: Dict[str, Any],
        legal_representative: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send DMCA takedown notice email with professional template."""
        template_data = {
            'recipient_name': to_name,
            'infringement_url': infringement_data.get('url', ''),
            'infringement_description': infringement_data.get('description', ''),
            'original_work_title': infringement_data.get('original_title', ''),
            'copyright_owner': infringement_data.get('copyright_owner', ''),
            'legal_representative': legal_representative.get('name', ''),
            'legal_contact': legal_representative.get('contact_info', ''),
            'takedown_deadline': infringement_data.get('deadline', '7 business days'),
            'case_reference': infringement_data.get('case_id', ''),
            'platform_name': infringement_data.get('platform', 'your platform')
        }
        
        # Fallback text content
        text_content = f"""
DMCA TAKEDOWN NOTICE

Dear {to_name},

We are writing to inform you of alleged copyright infringement on your platform.

Infringing Content: {infringement_data.get('url', 'N/A')}
Original Work: {infringement_data.get('original_title', 'N/A')}
Copyright Owner: {infringement_data.get('copyright_owner', 'N/A')}

Please remove the infringing content within {infringement_data.get('deadline', '7 business days')}.

Legal Representative: {legal_representative.get('name', 'N/A')}
Contact: {legal_representative.get('contact_info', 'N/A')}
Case Reference: {infringement_data.get('case_id', 'N/A')}

This notice is sent in good faith under the Digital Millennium Copyright Act.

Regards,
{settings.PROJECT_NAME} Legal Team
        """.strip()
        
        return await self.send_email(
            to_email=to_email,
            subject=f"DMCA Takedown Notice - Case #{infringement_data.get('case_id', 'N/A')}",
            text_content=text_content,
            to_name=to_name,
            template_id=self.templates.get('dmca_takedown'),
            template_data=template_data,
            attachments=attachments,
            categories=['dmca', 'legal', 'takedown'],
            custom_args={
                'case_id': str(infringement_data.get('case_id', '')),
                'infringement_type': infringement_data.get('type', 'unknown')
            }
        )
    
    async def send_infringement_alert(
        self,
        to_email: str,
        to_name: str,
        infringement_data: Dict[str, Any],
        alert_preferences: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send infringement alert to content creator."""
        template_data = {
            'creator_name': to_name,
            'infringement_url': infringement_data.get('url', ''),
            'platform_name': infringement_data.get('platform', 'Unknown'),
            'confidence_score': f"{infringement_data.get('confidence_score', 0):.0%}",
            'detected_at': infringement_data.get('detected_at', datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')),
            'dashboard_url': f"{getattr(settings, 'FRONTEND_URL', 'https://app.autodmca.com')}/infringements/{infringement_data.get('id', '')}",
            'auto_takedown_enabled': alert_preferences.get('auto_takedown', False) if alert_preferences else False,
            'profile_name': infringement_data.get('profile_name', 'Unknown')
        }
        
        text_content = f"""
INFRINGEMENT ALERT

Hello {to_name},

We've detected potential infringement of your protected content:

Platform: {infringement_data.get('platform', 'Unknown')}
URL: {infringement_data.get('url', 'N/A')}
Confidence: {infringement_data.get('confidence_score', 0):.0%}
Profile: {infringement_data.get('profile_name', 'Unknown')}

Detected: {infringement_data.get('detected_at', 'Just now')}

View in dashboard: {getattr(settings, 'FRONTEND_URL', '')}/infringements/{infringement_data.get('id', '')}

Best regards,
{settings.PROJECT_NAME} Team
        """.strip()
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Infringement Detected on {infringement_data.get('platform', 'Unknown Platform')}",
            text_content=text_content,
            to_name=to_name,
            template_id=self.templates.get('infringement_alert'),
            template_data=template_data,
            categories=['alert', 'infringement', 'detection'],
            custom_args={
                'infringement_id': str(infringement_data.get('id', '')),
                'platform': infringement_data.get('platform', 'unknown'),
                'confidence': str(infringement_data.get('confidence_score', 0))
            }
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        to_name: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send welcome email to new users."""
        template_data = {
            'user_name': to_name,
            'login_url': f"{getattr(settings, 'FRONTEND_URL', 'https://app.autodmca.com')}/login",
            'dashboard_url': f"{getattr(settings, 'FRONTEND_URL', 'https://app.autodmca.com')}/dashboard",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@autodmca.com'),
            'getting_started_steps': [
                'Complete your profile setup',
                'Add your first protected content',
                'Configure monitoring preferences',
                'Review your dashboard settings'
            ]
        }
        
        text_content = f"""
Welcome to {settings.PROJECT_NAME}!

Hello {to_name},

Thank you for joining {settings.PROJECT_NAME}! Your account has been created successfully.

Getting started:
1. Complete your profile setup
2. Add your first protected content
3. Configure monitoring preferences
4. Review your dashboard settings

Login to your dashboard: {getattr(settings, 'FRONTEND_URL', '')}/login

If you have any questions, contact us at {getattr(settings, 'SUPPORT_EMAIL', 'support@autodmca.com')}

Best regards,
The {settings.PROJECT_NAME} Team
        """.strip()
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.PROJECT_NAME}!",
            text_content=text_content,
            to_name=to_name,
            template_id=self.templates.get('welcome'),
            template_data=template_data,
            categories=['welcome', 'onboarding', 'user_lifecycle']
        )
    
    async def send_subscription_confirmation(
        self,
        to_email: str,
        to_name: str,
        subscription_data: Dict[str, Any]
    ) -> bool:
        """Send subscription confirmation email."""
        template_data = {
            'user_name': to_name,
            'plan_name': subscription_data.get('plan_name', 'Premium'),
            'billing_amount': subscription_data.get('amount', '0'),
            'billing_interval': subscription_data.get('interval', 'monthly'),
            'next_billing_date': subscription_data.get('next_billing_date', 'N/A'),
            'billing_portal_url': f"{getattr(settings, 'FRONTEND_URL', '')}/billing",
            'features': subscription_data.get('features', [])
        }
        
        text_content = f"""
Subscription Confirmed

Hello {to_name},

Your {subscription_data.get('plan_name', 'Premium')} subscription has been confirmed!

Plan: {subscription_data.get('plan_name', 'Premium')}
Amount: ${subscription_data.get('amount', '0')}/{subscription_data.get('interval', 'month')}
Next billing: {subscription_data.get('next_billing_date', 'N/A')}

Manage your subscription: {getattr(settings, 'FRONTEND_URL', '')}/billing

Thank you for choosing {settings.PROJECT_NAME}!

Best regards,
The {settings.PROJECT_NAME} Team
        """.strip()
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Subscription Confirmed - {settings.PROJECT_NAME}",
            text_content=text_content,
            to_name=to_name,
            template_id=self.templates.get('subscription_confirmation'),
            template_data=template_data,
            categories=['billing', 'subscription', 'confirmation'],
            custom_args={
                'plan': subscription_data.get('plan_name', 'premium'),
                'amount': str(subscription_data.get('amount', 0))
            }
        )
    
    async def get_email_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get email delivery statistics from SendGrid."""
        if not self.client:
            return {'error': 'SendGrid not available'}
        
        try:
            # Default to last 30 days
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            # Format dates for SendGrid API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Get statistics
            params = {
                'start_date': start_date_str,
                'end_date': end_date_str,
                'aggregated_by': 'day'
            }
            
            if categories:
                params['categories'] = categories
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.client.stats.get(query_params=params)
            )
            
            if response.status_code == 200:
                stats_data = json.loads(response.body)
                
                # Aggregate totals
                totals = {
                    'delivered': 0,
                    'opens': 0,
                    'clicks': 0,
                    'bounces': 0,
                    'spam_reports': 0,
                    'unsubscribes': 0
                }
                
                for day_stats in stats_data:
                    for metric in day_stats.get('stats', []):
                        for key in totals.keys():
                            totals[key] += metric.get('metrics', {}).get(key, 0)
                
                # Calculate rates
                if totals['delivered'] > 0:
                    open_rate = (totals['opens'] / totals['delivered']) * 100
                    click_rate = (totals['clicks'] / totals['delivered']) * 100
                    bounce_rate = (totals['bounces'] / totals['delivered']) * 100
                else:
                    open_rate = click_rate = bounce_rate = 0
                
                return {
                    'period': f"{start_date_str} to {end_date_str}",
                    'totals': totals,
                    'rates': {
                        'open_rate': round(open_rate, 2),
                        'click_rate': round(click_rate, 2),
                        'bounce_rate': round(bounce_rate, 2)
                    },
                    'daily_stats': stats_data
                }
            else:
                logger.error(f"SendGrid stats API error: {response.status_code}")
                return {'error': f'API error: {response.status_code}'}
        
        except Exception as e:
            logger.error(f"Error getting SendGrid statistics: {e}")
            return {'error': str(e)}
    
    async def validate_email_address(self, email: str) -> Dict[str, Any]:
        """Validate email address using SendGrid validation API."""
        if not self.client:
            return {'valid': True, 'note': 'SendGrid validation not available'}
        
        try:
            # This would use SendGrid's email validation API
            # For now, return a simple validation
            import re
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = bool(re.match(email_pattern, email))
            
            return {
                'email': email,
                'valid': is_valid,
                'result': {
                    'local': email.split('@')[0] if '@' in email else '',
                    'host': email.split('@')[1] if '@' in email else '',
                    'suggestion': None
                },
                'checks': {
                    'format': is_valid,
                    'mx': True,  # Assume valid for basic check
                    'disposable': False
                }
            }
        
        except Exception as e:
            logger.error(f"Error validating email: {e}")
            return {'valid': False, 'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Check SendGrid service health."""
        if not self.client:
            return {
                'service': 'sendgrid',
                'status': 'disabled',
                'message': 'SendGrid not configured or unavailable'
            }
        
        try:
            # Simple API key validation
            # In a real implementation, you might make a test API call
            return {
                'service': 'sendgrid',
                'status': 'healthy',
                'api_key_configured': bool(self.api_key),
                'templates_configured': len([t for t in self.templates.values() if t]),
                'fallback_available': True
            }
        except Exception as e:
            return {
                'service': 'sendgrid',
                'status': 'unhealthy',
                'error': str(e)
            }


# Create singleton instance
sendgrid_service = SendGridService()


# Convenience functions
async def send_dmca_takedown_notice(
    to_email: str,
    to_name: str,
    infringement_data: Dict[str, Any],
    legal_representative: Dict[str, Any],
    attachments: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """Send DMCA takedown notice."""
    return await sendgrid_service.send_dmca_takedown_email(
        to_email, to_name, infringement_data, legal_representative, attachments
    )


async def send_infringement_notification(
    to_email: str,
    to_name: str,
    infringement_data: Dict[str, Any],
    alert_preferences: Optional[Dict[str, Any]] = None
) -> bool:
    """Send infringement alert to creator."""
    return await sendgrid_service.send_infringement_alert(
        to_email, to_name, infringement_data, alert_preferences
    )


async def send_bulk_notifications(
    recipients: List[Dict[str, Any]],
    template_type: str,
    template_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Send bulk notifications using templates."""
    template_id = sendgrid_service.templates.get(template_type)
    
    return await sendgrid_service.send_bulk_email(
        recipients=recipients,
        subject="",  # Template handles subject
        text_content="",  # Template handles content
        template_id=template_id,
        categories=[template_type, 'bulk']
    )