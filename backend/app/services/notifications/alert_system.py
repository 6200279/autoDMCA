"""
Real-time Alert and Notification System
Provides immediate notifications for detected infringements and status updates
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import aiohttp
from jinja2 import Template

from app.core.config import settings
from app.services.websocket import WebSocketManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    INFRINGEMENT_DETECTED = "infringement_detected"
    TAKEDOWN_SENT = "takedown_sent"
    CONTENT_REMOVED = "content_removed"
    SCAN_COMPLETED = "scan_completed"
    IMPERSONATION_FOUND = "impersonation_found"
    HIGH_RISK_ACTIVITY = "high_risk_activity"
    SYSTEM_ERROR = "system_error"


class AlertPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBSOCKET = "websocket"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """Alert/notification data structure"""
    alert_id: str
    user_id: int
    profile_id: Optional[int]
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    data: Dict[str, Any]
    channels: List[NotificationChannel]
    created_at: datetime
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, failed, read


class RealTimeAlertSystem:
    """
    Real-time alert and notification system
    PRD: "Daily/Real-Time Reports" and immediate notifications
    """
    
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.active_subscriptions: Dict[int, Set[str]] = {}  # user_id -> alert_types
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        self.email_queue: asyncio.Queue = asyncio.Queue()
        self.batch_alerts: Dict[int, List[Alert]] = {}  # user_id -> alerts
        
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', 'alerts@contentprotection.com')
        
        # SMS configuration (would integrate with Twilio, AWS SNS, etc.)
        self.sms_enabled = bool(os.getenv('SMS_API_KEY'))
        
        # Push notification configuration
        self.push_enabled = bool(os.getenv('PUSH_SERVICE_KEY'))
        
        # Start background workers
        self._start_workers()
        
    def _start_workers(self):
        """Start background worker tasks"""
        asyncio.create_task(self._alert_processor())
        asyncio.create_task(self._email_processor())
        asyncio.create_task(self._batch_processor())
        
    async def send_alert(
        self,
        user_id: int,
        alert_type: AlertType,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        priority: AlertPriority = AlertPriority.MEDIUM,
        channels: List[NotificationChannel] = None,
        profile_id: Optional[int] = None
    ) -> str:
        """
        Send an alert through specified channels
        """
        if data is None:
            data = {}
            
        if channels is None:
            channels = [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
            
        alert = Alert(
            alert_id=f"alert_{datetime.utcnow().timestamp()}_{user_id}",
            user_id=user_id,
            profile_id=profile_id,
            alert_type=alert_type,
            priority=priority,
            title=title,
            message=message,
            data=data,
            channels=channels,
            created_at=datetime.utcnow()
        )
        
        # Queue alert for processing
        await self.alert_queue.put(alert)
        
        logger.info(f"Alert queued: {alert.alert_id} for user {user_id}")
        return alert.alert_id
        
    async def send_infringement_alert(
        self,
        user_id: int,
        profile_id: int,
        infringement_data: Dict[str, Any]
    ):
        """Send alert when new infringement is detected"""
        
        confidence = infringement_data.get('confidence', 0.0)
        url = infringement_data.get('url', 'Unknown')
        detection_method = infringement_data.get('detection_method', 'Unknown')
        
        # Determine priority based on confidence
        if confidence >= 0.9:
            priority = AlertPriority.CRITICAL
        elif confidence >= 0.8:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM
            
        title = "🚨 New Infringement Detected"
        message = f"High-confidence match found: {url}"
        
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.INFRINGEMENT_DETECTED,
            title=title,
            message=message,
            data={
                'infringement': infringement_data,
                'confidence': confidence,
                'detection_method': detection_method
            },
            priority=priority,
            profile_id=profile_id
        )
        
    async def send_takedown_sent_alert(
        self,
        user_id: int,
        profile_id: int,
        takedown_data: Dict[str, Any]
    ):
        """Send alert when DMCA takedown is sent"""
        
        url = takedown_data.get('url', 'Unknown')
        host_provider = takedown_data.get('host_provider', 'Unknown')
        
        title = "📧 DMCA Notice Sent"
        message = f"Takedown notice sent to {host_provider} for {url}"
        
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.TAKEDOWN_SENT,
            title=title,
            message=message,
            data=takedown_data,
            priority=AlertPriority.MEDIUM,
            profile_id=profile_id
        )
        
    async def send_content_removed_alert(
        self,
        user_id: int,
        profile_id: int,
        removal_data: Dict[str, Any]
    ):
        """Send alert when content is successfully removed"""
        
        url = removal_data.get('url', 'Unknown')
        
        title = "✅ Content Successfully Removed"
        message = f"Infringing content removed: {url}"
        
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.CONTENT_REMOVED,
            title=title,
            message=message,
            data=removal_data,
            priority=AlertPriority.MEDIUM,
            profile_id=profile_id
        )
        
    async def send_scan_completed_alert(
        self,
        user_id: int,
        profile_id: int,
        scan_results: Dict[str, Any]
    ):
        """Send alert when scan is completed"""
        
        matches_found = scan_results.get('matches_found', 0)
        urls_scanned = scan_results.get('urls_scanned', 0)
        
        if matches_found > 0:
            title = f"🔍 Scan Complete - {matches_found} matches found"
            priority = AlertPriority.HIGH
        else:
            title = f"🔍 Scan Complete - No infringements detected"
            priority = AlertPriority.LOW
            
        message = f"Scanned {urls_scanned} URLs, found {matches_found} potential matches"
        
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.SCAN_COMPLETED,
            title=title,
            message=message,
            data=scan_results,
            priority=priority,
            profile_id=profile_id
        )
        
    async def send_impersonation_alert(
        self,
        user_id: int,
        profile_id: int,
        impersonation_data: Dict[str, Any]
    ):
        """Send alert when impersonation is detected"""
        
        platform = impersonation_data.get('platform', 'Unknown')
        profile_url = impersonation_data.get('profile_url', 'Unknown')
        risk_level = impersonation_data.get('risk_level', 'medium')
        
        # Map risk level to priority
        priority_map = {
            'critical': AlertPriority.CRITICAL,
            'high': AlertPriority.HIGH,
            'medium': AlertPriority.MEDIUM,
            'low': AlertPriority.LOW
        }
        
        priority = priority_map.get(risk_level, AlertPriority.MEDIUM)
        
        title = f"👤 Impersonation Detected on {platform.title()}"
        message = f"Potential fake account found: {profile_url}"
        
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.IMPERSONATION_FOUND,
            title=title,
            message=message,
            data=impersonation_data,
            priority=priority,
            profile_id=profile_id
        )
        
    async def send_daily_summary(
        self,
        user_id: int,
        summary_data: Dict[str, Any]
    ):
        """
        Send daily summary report
        PRD: "daily reports of detected links and their status"
        """
        
        total_scans = summary_data.get('total_scans', 0)
        infringements_found = summary_data.get('infringements_found', 0)
        takedowns_sent = summary_data.get('takedowns_sent', 0)
        content_removed = summary_data.get('content_removed', 0)
        
        title = f"📊 Daily Protection Summary - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        message = f"""
Daily Summary:
• {total_scans} scans completed
• {infringements_found} infringements detected
• {takedowns_sent} DMCA notices sent
• {content_removed} items removed
"""
        
        # Send as email-only for daily summaries
        await self.send_alert(
            user_id=user_id,
            alert_type=AlertType.SCAN_COMPLETED,
            title=title,
            message=message.strip(),
            data=summary_data,
            priority=AlertPriority.LOW,
            channels=[NotificationChannel.EMAIL]
        )
        
    async def _alert_processor(self):
        """Background task to process alerts"""
        while True:
            try:
                alert = await self.alert_queue.get()
                
                # Process each notification channel
                for channel in alert.channels:
                    try:
                        if channel == NotificationChannel.WEBSOCKET:
                            await self._send_websocket_alert(alert)
                        elif channel == NotificationChannel.EMAIL:
                            await self._queue_email_alert(alert)
                        elif channel == NotificationChannel.SMS:
                            await self._send_sms_alert(alert)
                        elif channel == NotificationChannel.PUSH:
                            await self._send_push_alert(alert)
                        elif channel == NotificationChannel.WEBHOOK:
                            await self._send_webhook_alert(alert)
                            
                    except Exception as e:
                        logger.error(f"Error sending alert via {channel}: {e}")
                        
                # Update alert status
                alert.status = "sent"
                alert.sent_at = datetime.utcnow()
                
                # Store alert in database
                await self._store_alert(alert)
                
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
                
    async def _send_websocket_alert(self, alert: Alert):
        """Send alert via WebSocket"""
        try:
            message = {
                'type': 'alert',
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'priority': alert.priority,
                'title': alert.title,
                'message': alert.message,
                'data': alert.data,
                'timestamp': alert.created_at.isoformat()
            }
            
            await self.websocket_manager.send_to_user(
                alert.user_id, 
                json.dumps(message)
            )
            
            logger.info(f"WebSocket alert sent to user {alert.user_id}")
            
        except Exception as e:
            logger.error(f"WebSocket alert error: {e}")
            
    async def _queue_email_alert(self, alert: Alert):
        """Queue email alert for processing"""
        await self.email_queue.put(alert)
        
    async def _email_processor(self):
        """Background task to process email alerts"""
        while True:
            try:
                alert = await self.email_queue.get()
                
                # Check if we should batch this email
                if self._should_batch_email(alert):
                    await self._add_to_batch(alert)
                else:
                    await self._send_immediate_email(alert)
                    
            except Exception as e:
                logger.error(f"Email processing error: {e}")
                
    def _should_batch_email(self, alert: Alert) -> bool:
        """Determine if email should be batched or sent immediately"""
        
        # Send immediately for high priority alerts
        if alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
            return False
            
        # Batch low priority alerts
        return True
        
    async def _add_to_batch(self, alert: Alert):
        """Add alert to batch for later sending"""
        user_id = alert.user_id
        
        if user_id not in self.batch_alerts:
            self.batch_alerts[user_id] = []
            
        self.batch_alerts[user_id].append(alert)
        
    async def _send_immediate_email(self, alert: Alert):
        """Send email immediately"""
        try:
            # Get user email address
            user_email = await self._get_user_email(alert.user_id)
            if not user_email:
                logger.warning(f"No email found for user {alert.user_id}")
                return
                
            # Generate email content
            subject = f"[Content Protection] {alert.title}"
            
            # Create HTML email template
            html_template = Template("""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                    <h1>{{ title }}</h1>
                </div>
                <div style="padding: 20px;">
                    <p style="font-size: 16px; line-height: 1.5;">{{ message }}</p>
                    
                    {% if data %}
                    <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0;">
                        <h3>Details:</h3>
                        {% for key, value in data.items() %}
                        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
                        {% endfor %}
                    </div>
                    {% endif %}
                    
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{{ dashboard_url }}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            View Dashboard
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 14px;">
                        This is an automated alert from your Content Protection service.
                        <br>
                        Time: {{ timestamp }}
                    </p>
                </div>
            </body>
            </html>
            """)
            
            html_body = html_template.render(
                title=alert.title,
                message=alert.message,
                data=alert.data,
                dashboard_url=f"{settings.FRONTEND_URL}/dashboard",
                timestamp=alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            
            # Send email
            await self._send_email(user_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Error sending immediate email: {e}")
            
    async def _batch_processor(self):
        """Process batched alerts every hour"""
        while True:
            try:
                # Wait 1 hour between batch processing
                await asyncio.sleep(3600)
                
                # Process batches for each user
                for user_id, alerts in self.batch_alerts.items():
                    if alerts:
                        await self._send_batch_email(user_id, alerts)
                        
                # Clear processed batches
                self.batch_alerts.clear()
                
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                
    async def _send_batch_email(self, user_id: int, alerts: List[Alert]):
        """Send batched alerts as single email"""
        try:
            user_email = await self._get_user_email(user_id)
            if not user_email:
                return
                
            # Group alerts by type
            alert_groups = {}
            for alert in alerts:
                alert_type = alert.alert_type
                if alert_type not in alert_groups:
                    alert_groups[alert_type] = []
                alert_groups[alert_type].append(alert)
                
            # Generate batch email
            subject = f"[Content Protection] {len(alerts)} Updates"
            
            html_template = Template("""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                    <h1>Content Protection Updates</h1>
                    <p>{{ alerts|length }} notifications from the last hour</p>
                </div>
                
                {% for alert_type, type_alerts in alert_groups.items() %}
                <div style="padding: 20px; border-bottom: 1px solid #eee;">
                    <h2 style="color: #333; margin-bottom: 15px;">
                        {{ alert_type.replace('_', ' ').title() }} ({{ type_alerts|length }})
                    </h2>
                    
                    {% for alert in type_alerts %}
                    <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea;">
                        <h4>{{ alert.title }}</h4>
                        <p>{{ alert.message }}</p>
                        <small style="color: #666;">{{ alert.created_at.strftime('%H:%M:%S') }}</small>
                    </div>
                    {% endfor %}
                </div>
                {% endfor %}
                
                <div style="padding: 20px; text-align: center;">
                    <a href="{{ dashboard_url }}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Full Dashboard
                    </a>
                </div>
            </body>
            </html>
            """)
            
            html_body = html_template.render(
                alerts=alerts,
                alert_groups=alert_groups,
                dashboard_url=f"{settings.FRONTEND_URL}/dashboard"
            )
            
            await self._send_email(user_email, subject, html_body)
            
        except Exception as e:
            logger.error(f"Error sending batch email: {e}")
            
    async def _send_email(self, to_email: str, subject: str, html_body: str):
        """Send email via SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"Content Protection <{self.from_email}>"
            message["To"] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
                
            logger.info(f"Email sent to {to_email}: {subject}")
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            
    async def _send_sms_alert(self, alert: Alert):
        """Send SMS alert (placeholder)"""
        if not self.sms_enabled:
            return
            
        # Would integrate with SMS service like Twilio
        logger.info(f"SMS alert sent to user {alert.user_id}: {alert.title}")
        
    async def _send_push_alert(self, alert: Alert):
        """Send push notification (placeholder)"""
        if not self.push_enabled:
            return
            
        # Would integrate with push service like Firebase
        logger.info(f"Push notification sent to user {alert.user_id}: {alert.title}")
        
    async def _send_webhook_alert(self, alert: Alert):
        """Send webhook notification"""
        try:
            # Get user's webhook URL
            webhook_url = await self._get_user_webhook_url(alert.user_id)
            if not webhook_url:
                return
                
            payload = {
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'priority': alert.priority,
                'title': alert.title,
                'message': alert.message,
                'data': alert.data,
                'timestamp': alert.created_at.isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent to user {alert.user_id}")
                    else:
                        logger.warning(f"Webhook failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            
    async def _get_user_email(self, user_id: int) -> Optional[str]:
        """Get user email from database"""
        # Placeholder - would query database
        return "user@example.com"
        
    async def _get_user_webhook_url(self, user_id: int) -> Optional[str]:
        """Get user webhook URL from database"""
        # Placeholder - would query database
        return None
        
    async def _store_alert(self, alert: Alert):
        """Store alert in database"""
        # Placeholder - would store in database
        logger.info(f"Alert stored: {alert.alert_id}")
        
    async def get_user_alerts(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get alerts for a user"""
        # Placeholder - would query database
        return []
        
    async def mark_alert_read(self, alert_id: str, user_id: int) -> bool:
        """Mark an alert as read"""
        # Placeholder - would update database
        logger.info(f"Alert marked as read: {alert_id}")
        return True


# Global alert system instance (compatible with service registry)
alert_system = RealTimeAlertSystem()

import os