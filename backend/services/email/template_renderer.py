"""
HTML Email Template Rendering Service

This service handles rendering of HTML email templates using Jinja2 templating engine.
Supports base templates, template inheritance, and dynamic content rendering.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class TemplateRenderError(Exception):
    """Template rendering specific errors"""
    pass


class EmailTemplateRenderer:
    """
    HTML email template rendering service with Jinja2 support.
    
    Features:
    - Template inheritance with base templates
    - Dynamic content rendering
    - Context preprocessing for common variables
    - Template caching for performance
    - Fallback to plain text if HTML rendering fails
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = template_dir or "backend/templates"
        self.templates_path = Path(self.template_dir) / "email"
        
        if not JINJA2_AVAILABLE:
            logger.warning("Jinja2 not available, HTML email templates disabled")
            self.env = None
        else:
            # Initialize Jinja2 environment
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_path)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Add custom filters
            self.env.filters['pluralize'] = self._pluralize_filter
            self.env.filters['currency'] = self._currency_filter
            self.env.filters['datetime_format'] = self._datetime_format_filter
            
            logger.info(f"Email template renderer initialized with templates from {self.templates_path}")
    
    def _pluralize_filter(self, count: int, singular: str = '', plural: str = 's') -> str:
        """Jinja2 filter for pluralization."""
        if count == 1:
            return singular
        return plural
    
    def _currency_filter(self, amount: float, currency: str = 'USD') -> str:
        """Jinja2 filter for currency formatting."""
        if currency == 'USD':
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {currency}"
    
    def _datetime_format_filter(self, dt: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
        """Jinja2 filter for datetime formatting."""
        if isinstance(dt, str):
            return dt
        return dt.strftime(format_str)
    
    def _get_base_context(self, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get base context variables available to all templates."""
        context = {
            # Application info
            'app_name': settings.PROJECT_NAME,
            'app_version': settings.VERSION,
            'app_description': settings.DESCRIPTION,
            'current_year': datetime.utcnow().year,
            'current_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'current_datetime': datetime.utcnow(),
            
            # URLs
            'frontend_url': getattr(settings, 'FRONTEND_URL', 'https://app.autodmca.com'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@autodmca.com'),
            'support_phone': getattr(settings, 'SUPPORT_PHONE', '+1-555-0123'),
            
            # Common URLs (will be populated by template-specific context)
            'dashboard_url': '',
            'login_url': '',
            'billing_url': '',
            'settings_url': '',
            'help_center_url': '',
            'unsubscribe_url': '',
            
            # User info
            'user_name': 'User',
            'user_email': '',
        }
        
        # Add user-specific data
        if user_data:
            context.update({
                'user_name': user_data.get('name', user_data.get('username', 'User')),
                'user_email': user_data.get('email', ''),
                'user_id': user_data.get('id', ''),
            })
            
            # Build user-specific URLs
            base_url = context['frontend_url']
            context.update({
                'dashboard_url': f"{base_url}/dashboard",
                'login_url': f"{base_url}/login",
                'billing_url': f"{base_url}/billing",
                'settings_url': f"{base_url}/settings",
                'profile_url': f"{base_url}/profile",
                'help_center_url': f"{base_url}/help",
                'unsubscribe_url': f"{base_url}/unsubscribe?user_id={user_data.get('id', '')}",
            })
        
        return context
    
    def render_template(
        self,
        template_name: str,
        context_data: Dict[str, Any],
        user_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render HTML email template with given context.
        
        Args:
            template_name: Template file name (e.g., 'welcome.html')
            context_data: Template-specific context data
            user_data: User information for base context
            
        Returns:
            Rendered HTML content
            
        Raises:
            TemplateRenderError: If template rendering fails
        """
        if not self.env:
            raise TemplateRenderError("Jinja2 not available for template rendering")
        
        try:
            # Load template
            template = self.env.get_template(template_name)
            
            # Build complete context
            context = self._get_base_context(user_data)
            context.update(context_data)
            
            # Add template-specific context enhancements
            context = self._enhance_context(template_name, context)
            
            # Render template
            html_content = template.render(context)
            
            logger.debug(f"Successfully rendered template: {template_name}")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise TemplateRenderError(f"Template rendering failed: {e}")
    
    def _enhance_context(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add template-specific context enhancements."""
        
        # Common enhancements for all templates
        context['time_of_day'] = self._get_time_of_day()
        
        # Template-specific enhancements
        if template_name == 'daily_report.html':
            context = self._enhance_daily_report_context(context)
        elif template_name == 'infringement_alert.html':
            context = self._enhance_infringement_alert_context(context)
        elif template_name == 'dmca_takedown.html':
            context = self._enhance_dmca_context(context)
        elif template_name == 'welcome.html':
            context = self._enhance_welcome_context(context)
        
        return context
    
    def _get_time_of_day(self) -> str:
        """Get appropriate greeting based on current time."""
        hour = datetime.utcnow().hour
        if hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        else:
            return "evening"
    
    def _enhance_daily_report_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context for daily report emails."""
        # Ensure required report data has defaults
        context.setdefault('new_detections', 0)
        context.setdefault('successful_takedowns', 0)
        context.setdefault('active_takedowns', 0)
        context.setdefault('scanning_hours', 24)
        context.setdefault('protected_content_count', 0)
        context.setdefault('manual_review_needed', 0)
        
        # Add report-specific URLs
        base_url = context.get('frontend_url', '')
        context.update({
            'reports_url': f"{base_url}/reports",
            'bulk_review_url': f"{base_url}/dashboard?tab=review",
            'auto_takedown_settings_url': f"{base_url}/settings/auto-takedown",
            'add_content_url': f"{base_url}/content/upload",
            'platform_settings_url': f"{base_url}/settings/platforms",
            'email_settings_url': f"{base_url}/settings/notifications",
        })
        
        # Format report date
        if 'report_date' not in context:
            context['report_date'] = datetime.utcnow().strftime('%B %d, %Y')
        
        return context
    
    def _enhance_infringement_alert_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context for infringement alert emails."""
        # Ensure confidence score is formatted as percentage
        confidence = context.get('confidence_score', 0)
        if isinstance(confidence, (int, float)) and confidence <= 1:
            context['confidence_score'] = f"{confidence * 100:.0f}%"
        elif isinstance(confidence, str) and not confidence.endswith('%'):
            context['confidence_score'] = f"{confidence}%"
        
        # Add alert-specific URLs
        base_url = context.get('frontend_url', '')
        infringement_id = context.get('infringement_id', '')
        context.update({
            'dashboard_url': f"{base_url}/infringements/{infringement_id}",
            'support_url': f"{base_url}/help",
        })
        
        # Default values for statistics
        context.setdefault('total_detections_today', 0)
        context.setdefault('total_takedowns_month', 0)
        context.setdefault('auto_takedown_enabled', False)
        
        return context
    
    def _enhance_dmca_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context for DMCA takedown emails."""
        # Ensure current date is set
        context.setdefault('current_date', datetime.utcnow().strftime('%B %d, %Y'))
        
        # Default legal information
        context.setdefault('legal_representative', 'AutoDMCA Legal Team')
        context.setdefault('legal_title', 'Copyright Agent')
        context.setdefault('legal_organization', settings.PROJECT_NAME)
        context.setdefault('takedown_deadline', '7 business days')
        
        # Add DMCA-specific URLs
        base_url = context.get('frontend_url', '')
        case_id = context.get('case_reference', '')
        context.update({
            'response_portal_url': f"{base_url}/dmca/respond/{case_id}",
        })
        
        return context
    
    def _enhance_welcome_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context for welcome emails."""
        # Add welcome-specific URLs
        base_url = context.get('frontend_url', '')
        context.update({
            'upload_url': f"{base_url}/content/upload",
            'upgrade_url': f"{base_url}/billing/upgrade",
            'video_tutorials_url': f"{base_url}/help/tutorials",
            'faq_url': f"{base_url}/help/faq",
        })
        
        # Default subscription info
        context.setdefault('subscription_plan', 'Basic')
        
        return context
    
    def render_dmca_takedown_email(
        self,
        recipient_name: str,
        infringement_data: Dict[str, Any],
        legal_representative: Dict[str, Any],
        case_reference: str
    ) -> str:
        """Render DMCA takedown notice email."""
        context = {
            'recipient_name': recipient_name,
            'infringement_url': infringement_data.get('url', ''),
            'infringement_description': infringement_data.get('description', ''),
            'original_work_title': infringement_data.get('original_title', ''),
            'original_work_url': infringement_data.get('original_url', ''),
            'copyright_owner': infringement_data.get('copyright_owner', ''),
            'platform_name': infringement_data.get('platform', 'your platform'),
            'case_reference': case_reference,
            'legal_representative': legal_representative.get('name', ''),
            'legal_contact': legal_representative.get('contact_info', ''),
            'legal_title': legal_representative.get('title', 'Copyright Agent'),
            'legal_organization': legal_representative.get('organization', settings.PROJECT_NAME),
        }
        
        return self.render_template('dmca_takedown.html', context)
    
    def render_infringement_alert_email(
        self,
        user_data: Dict[str, Any],
        infringement_data: Dict[str, Any],
        alert_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render infringement alert email."""
        context = {
            'creator_name': user_data.get('name', 'User'),
            'infringement_url': infringement_data.get('url', ''),
            'platform_name': infringement_data.get('platform', 'Unknown'),
            'profile_name': infringement_data.get('profile_name', 'Unknown'),
            'confidence_score': infringement_data.get('confidence_score', 0),
            'detected_at': infringement_data.get('detected_at', datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')),
            'infringement_id': infringement_data.get('id', ''),
            'auto_takedown_enabled': alert_preferences.get('auto_takedown', False) if alert_preferences else False,
        }
        
        return self.render_template('infringement_alert.html', context, user_data)
    
    def render_welcome_email(
        self,
        user_data: Dict[str, Any],
        subscription_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render welcome email for new users."""
        context = {
            'user_name': user_data.get('name', 'User'),
        }
        
        if subscription_data:
            context.update({
                'subscription_plan': subscription_data.get('plan_name', 'Basic'),
                'plan_benefits': subscription_data.get('benefits', ''),
            })
        
        return self.render_template('welcome.html', context, user_data)
    
    def render_daily_report_email(
        self,
        user_data: Dict[str, Any],
        report_data: Dict[str, Any]
    ) -> str:
        """Render daily protection report email."""
        return self.render_template('daily_report.html', report_data, user_data)
    
    def render_subscription_confirmation_email(
        self,
        user_data: Dict[str, Any],
        subscription_data: Dict[str, Any]
    ) -> str:
        """Render subscription confirmation email."""
        return self.render_template('subscription_confirmation.html', subscription_data, user_data)
    
    def get_plain_text_fallback(self, template_name: str, context: Dict[str, Any]) -> str:
        """Generate plain text fallback when HTML rendering fails."""
        if template_name == 'dmca_takedown.html':
            return self._dmca_plain_text_fallback(context)
        elif template_name == 'infringement_alert.html':
            return self._alert_plain_text_fallback(context)
        elif template_name == 'welcome.html':
            return self._welcome_plain_text_fallback(context)
        else:
            return self._generic_plain_text_fallback(context)
    
    def _dmca_plain_text_fallback(self, context: Dict[str, Any]) -> str:
        """Plain text fallback for DMCA notices."""
        return f"""
DMCA TAKEDOWN NOTICE

To: {context.get('recipient_name', 'Recipient')}
From: {context.get('legal_representative', 'Legal Team')}
Case Reference: {context.get('case_reference', 'N/A')}

We are writing to notify you of claimed copyright infringement.

Infringing Content: {context.get('infringement_url', 'N/A')}
Original Work: {context.get('original_work_title', 'N/A')}
Copyright Owner: {context.get('copyright_owner', 'N/A')}

Please remove the infringing content within {context.get('takedown_deadline', '7 business days')}.

This notice is submitted in good faith under the Digital Millennium Copyright Act.

{context.get('legal_representative', 'Legal Team')}
{context.get('legal_contact', '')}
        """.strip()
    
    def _alert_plain_text_fallback(self, context: Dict[str, Any]) -> str:
        """Plain text fallback for infringement alerts."""
        return f"""
INFRINGEMENT ALERT

Hello {context.get('creator_name', 'User')},

We've detected potential infringement of your content:

Platform: {context.get('platform_name', 'Unknown')}
URL: {context.get('infringement_url', 'N/A')}
Confidence: {context.get('confidence_score', '0%')}
Detected: {context.get('detected_at', 'Recently')}

View in dashboard: {context.get('dashboard_url', '')}

Best regards,
{settings.PROJECT_NAME} Team
        """.strip()
    
    def _welcome_plain_text_fallback(self, context: Dict[str, Any]) -> str:
        """Plain text fallback for welcome emails."""
        return f"""
Welcome to {settings.PROJECT_NAME}!

Hello {context.get('user_name', 'User')},

Thank you for joining {settings.PROJECT_NAME}! Your account is ready.

Getting started:
1. Complete your profile
2. Upload your content
3. Configure monitoring
4. Let us protect your work

Login: {context.get('login_url', '')}

Best regards,
The {settings.PROJECT_NAME} Team
        """.strip()
    
    def _generic_plain_text_fallback(self, context: Dict[str, Any]) -> str:
        """Generic plain text fallback."""
        return f"""
{settings.PROJECT_NAME}

Hello {context.get('user_name', 'User')},

This email was sent from {settings.PROJECT_NAME}.

Visit your dashboard: {context.get('dashboard_url', '')}

Best regards,
The {settings.PROJECT_NAME} Team
        """.strip()
    
    def health_check(self) -> Dict[str, Any]:
        """Check template renderer health."""
        try:
            if not self.env:
                return {
                    'service': 'email_template_renderer',
                    'status': 'disabled',
                    'message': 'Jinja2 not available'
                }
            
            # Test template directory
            if not self.templates_path.exists():
                return {
                    'service': 'email_template_renderer',
                    'status': 'unhealthy',
                    'error': f'Template directory not found: {self.templates_path}'
                }
            
            # Count available templates
            template_files = list(self.templates_path.glob('*.html'))
            
            return {
                'service': 'email_template_renderer',
                'status': 'healthy',
                'template_directory': str(self.templates_path),
                'available_templates': len(template_files),
                'jinja2_available': JINJA2_AVAILABLE
            }
        
        except Exception as e:
            return {
                'service': 'email_template_renderer',
                'status': 'unhealthy',
                'error': str(e)
            }


# Create singleton instance
template_renderer = EmailTemplateRenderer()


# Convenience functions
async def render_dmca_takedown_email(
    recipient_name: str,
    infringement_data: Dict[str, Any],
    legal_representative: Dict[str, Any],
    case_reference: str
) -> str:
    """Render DMCA takedown notice email."""
    return template_renderer.render_dmca_takedown_email(
        recipient_name, infringement_data, legal_representative, case_reference
    )


async def render_infringement_alert_email(
    user_data: Dict[str, Any],
    infringement_data: Dict[str, Any],
    alert_preferences: Optional[Dict[str, Any]] = None
) -> str:
    """Render infringement alert email."""
    return template_renderer.render_infringement_alert_email(
        user_data, infringement_data, alert_preferences
    )


async def render_welcome_email(
    user_data: Dict[str, Any],
    subscription_data: Optional[Dict[str, Any]] = None
) -> str:
    """Render welcome email."""
    return template_renderer.render_welcome_email(user_data, subscription_data)


async def render_daily_report_email(
    user_data: Dict[str, Any],
    report_data: Dict[str, Any]
) -> str:
    """Render daily report email."""
    return template_renderer.render_daily_report_email(user_data, report_data)