import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime
import asyncio
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings


class EmailService:
    """Email service for sending notifications."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.EMAILS_FROM_NAME or settings.PROJECT_NAME
        
        # Setup Jinja2 template environment
        try:
            self.template_env = Environment(
                loader=FileSystemLoader('app/templates/email'),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except Exception:
            print("Warning: Email templates directory not found")
            self.template_env = None
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        to_name: Optional[str] = None
    ) -> bool:
        """Send an email."""
        if not self.smtp_host:
            print(f"Email would be sent to {to_email}: {subject}")
            return True  # Simulate success when SMTP not configured
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            message['Subject'] = subject
            
            # Add text part
            text_part = MIMEText(body_text, 'plain', 'utf-8')
            message.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                message.attach(html_part)
            
            # Send email
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_smtp_email, message
            )
            
            return True
            
        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")
            return False
    
    def _send_smtp_email(self, message: MIMEMultipart):
        """Send email via SMTP (blocking operation)."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_user and self.smtp_password:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            
            server.send_message(message)
    
    def _render_template(self, template_name: str, **context) -> tuple[str, str]:
        """Render email template."""
        if not self.template_env:
            # Fallback to basic templates
            return self._render_basic_template(template_name, **context)
        
        try:
            # Load text template
            text_template = self.template_env.get_template(f"{template_name}.txt")
            text_content = text_template.render(**context)
            
            # Load HTML template
            try:
                html_template = self.template_env.get_template(f"{template_name}.html")
                html_content = html_template.render(**context)
            except Exception:
                html_content = None
            
            return text_content, html_content
            
        except Exception as e:
            print(f"Error rendering template {template_name}: {e}")
            return self._render_basic_template(template_name, **context)
    
    def _render_basic_template(self, template_name: str, **context) -> tuple[str, str]:
        """Render basic email template when Jinja2 is not available."""
        if template_name == "verification":
            text = f"""
Dear {context.get('name', 'User')},

Welcome to {settings.PROJECT_NAME}!

Please verify your email address by clicking the link below:
{context.get('verification_url', '#')}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
The {settings.PROJECT_NAME} Team
            """.strip()
            
            html = f"""
<html>
<body>
<h2>Welcome to {settings.PROJECT_NAME}!</h2>
<p>Dear {context.get('name', 'User')},</p>
<p>Please verify your email address by clicking the button below:</p>
<a href="{context.get('verification_url', '#')}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a>
<p>Or copy and paste this link into your browser:</p>
<p>{context.get('verification_url', '#')}</p>
<p>This link will expire in 24 hours.</p>
<p>If you did not create an account, please ignore this email.</p>
<p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
</body>
</html>
            """.strip()
            
        elif template_name == "password_reset":
            text = f"""
Dear {context.get('name', 'User')},

You requested a password reset for your {settings.PROJECT_NAME} account.

Click the link below to reset your password:
{context.get('reset_url', '#')}

This link will expire in 1 hour.

If you did not request this reset, please ignore this email.

Best regards,
The {settings.PROJECT_NAME} Team
            """.strip()
            
            html = f"""
<html>
<body>
<h2>Password Reset Request</h2>
<p>Dear {context.get('name', 'User')},</p>
<p>You requested a password reset for your {settings.PROJECT_NAME} account.</p>
<p><a href="{context.get('reset_url', '#')}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
<p>Or copy and paste this link into your browser:</p>
<p>{context.get('reset_url', '#')}</p>
<p>This link will expire in 1 hour.</p>
<p>If you did not request this reset, please ignore this email.</p>
<p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
</body>
</html>
            """.strip()
            
        else:
            text = f"Email from {settings.PROJECT_NAME}"
            html = f"<p>Email from {settings.PROJECT_NAME}</p>"
        
        return text, html


# Global instance
email_service = EmailService()


# Convenience functions
async def send_verification_email(email: str, name: str, token: str) -> bool:
    """Send email verification email."""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    text_content, html_content = email_service._render_template(
        "verification",
        name=name,
        verification_url=verification_url,
        project_name=settings.PROJECT_NAME
    )
    
    return await email_service.send_email(
        to_email=email,
        to_name=name,
        subject=f"Verify your {settings.PROJECT_NAME} account",
        body_text=text_content,
        body_html=html_content
    )


async def send_password_reset_email(email: str, name: str, token: str) -> bool:
    """Send password reset email."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    text_content, html_content = email_service._render_template(
        "password_reset",
        name=name,
        reset_url=reset_url,
        project_name=settings.PROJECT_NAME
    )
    
    return await email_service.send_email(
        to_email=email,
        to_name=name,
        subject=f"Reset your {settings.PROJECT_NAME} password",
        body_text=text_content,
        body_html=html_content
    )


async def send_welcome_email(email: str, name: str) -> bool:
    """Send welcome email to new users."""
    text_content = f"""
Dear {name},

Welcome to {settings.PROJECT_NAME}!

Your account has been successfully created and verified. You can now start protecting your content and fighting infringement.

Getting started:
1. Add your first protected profile
2. Upload reference images
3. Start your first scan

If you have any questions, please don't hesitate to contact our support team.

Best regards,
The {settings.PROJECT_NAME} Team
    """.strip()
    
    return await email_service.send_email(
        to_email=email,
        to_name=name,
        subject=f"Welcome to {settings.PROJECT_NAME}!",
        body_text=text_content
    )


async def send_infringement_alert(email: str, name: str, infringement_data: dict) -> bool:
    """Send infringement alert email."""
    text_content = f"""
Dear {name},

We've detected a new infringement of your protected content:

URL: {infringement_data['url']}
Platform: {infringement_data['platform']}
Confidence: {infringement_data['confidence_score']:.0%}
Profile: {infringement_data['profile_name']}

Please review this infringement in your dashboard and take appropriate action.

View in Dashboard: {settings.FRONTEND_URL}/infringements/{infringement_data['id']}

Best regards,
The {settings.PROJECT_NAME} Team
    """.strip()
    
    return await email_service.send_email(
        to_email=email,
        to_name=name,
        subject=f"New Infringement Detected - {infringement_data['platform']}",
        body_text=text_content
    )


async def send_cancellation_email(email: str, name: str, end_date: datetime) -> bool:
    """Send subscription cancellation confirmation email."""
    text_content = f"""
Dear {name},

Your {settings.PROJECT_NAME} subscription has been cancelled as requested.

Your subscription will remain active until {end_date.strftime('%B %d, %Y')}, after which your account will be downgraded to the free plan.

You can reactivate your subscription at any time before the end date.

If you cancelled by mistake or have any questions, please contact our support team.

Best regards,
The {settings.PROJECT_NAME} Team
    """.strip()
    
    return await email_service.send_email(
        to_email=email,
        to_name=name,
        subject=f"Subscription Cancelled - {settings.PROJECT_NAME}",
        body_text=text_content
    )