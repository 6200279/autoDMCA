"""
DMCA takedown request queue and processing system.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlparse
import re

import aioredis
import aiohttp
from jinja2 import Environment, FileSystemLoader, Template
import structlog

from ..config import ScannerSettings
from ..processors.content_matcher import ContentMatch
from ..crawlers.piracy_crawler import InfringingContent


logger = structlog.get_logger(__name__)


class DMCAStatus(Enum):
    """DMCA request status states."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLIED = "complied"
    REJECTED = "rejected"
    FAILED = "failed"
    DELISTED = "delisted"  # Removed from search engines
    EXPIRED = "expired"


class NotificationType(Enum):
    """Types of notifications to send."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    API_CALLBACK = "api_callback"


@dataclass
class DMCARequest:
    """Represents a DMCA takedown request."""
    
    # Core identification
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    person_id: str = ""
    content_match: Optional[ContentMatch] = None
    
    # Target information
    infringing_url: str = ""
    hosting_provider: str = ""
    contact_email: str = ""
    contact_form_url: str = ""
    
    # Content details
    original_work_title: str = ""
    original_work_url: str = ""
    copyright_owner: str = ""
    infringement_description: str = ""
    
    # Processing metadata
    status: DMCAStatus = DMCAStatus.PENDING
    priority: int = 3  # 1=highest, 5=lowest
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    sent_at: Optional[float] = None
    deadline: Optional[float] = None  # When to expect compliance
    
    # Attempt tracking
    attempt_count: int = 0
    max_attempts: int = 3
    retry_after: Optional[float] = None
    
    # Response tracking
    responses: List['DMCAResponse'] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.hosting_provider and self.infringing_url:
            self.hosting_provider = self._extract_hosting_provider()
        
        if not self.deadline and self.created_at:
            # Default 14-day deadline
            self.deadline = self.created_at + (14 * 24 * 60 * 60)
    
    def _extract_hosting_provider(self) -> str:
        """Extract hosting provider from URL."""
        try:
            parsed = urlparse(self.infringing_url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception:
            return "unknown"
    
    @property
    def is_expired(self) -> bool:
        """Check if the request has expired."""
        return self.deadline and time.time() > self.deadline
    
    @property
    def can_retry(self) -> bool:
        """Check if the request can be retried."""
        if self.attempt_count >= self.max_attempts:
            return False
        
        if self.retry_after and time.time() < self.retry_after:
            return False
        
        return self.status in [DMCAStatus.FAILED, DMCAStatus.REJECTED]
    
    @property
    def is_successful(self) -> bool:
        """Check if the request was successful."""
        return self.status in [DMCAStatus.COMPLIED, DMCAStatus.DELISTED]
    
    def add_note(self, note: str):
        """Add a note to the request."""
        self.notes.append(f"{datetime.now().isoformat()}: {note}")
        self.updated_at = time.time()
    
    def increment_attempt(self):
        """Increment attempt count and set retry delay."""
        self.attempt_count += 1
        
        # Exponential backoff for retries
        retry_delay = min(2 ** self.attempt_count * 3600, 24 * 3600)  # Max 24 hours
        self.retry_after = time.time() + retry_delay
        self.updated_at = time.time()
    
    def update_status(self, status: DMCAStatus, note: str = ""):
        """Update the request status."""
        old_status = self.status
        self.status = status
        self.updated_at = time.time()
        
        if status == DMCAStatus.SENT and not self.sent_at:
            self.sent_at = time.time()
        
        status_note = f"Status changed from {old_status.value} to {status.value}"
        if note:
            status_note += f": {note}"
        
        self.add_note(status_note)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DMCARequest':
        """Create from dictionary."""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = DMCAStatus(data['status'])
        
        # Handle responses
        if 'responses' in data:
            responses = []
            for resp_data in data['responses']:
                if isinstance(resp_data, dict):
                    responses.append(DMCAResponse.from_dict(resp_data))
                else:
                    responses.append(resp_data)
            data['responses'] = responses
        
        return cls(**data)


@dataclass
class DMCAResponse:
    """Represents a response to a DMCA request."""
    
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    
    # Response details
    response_type: str = "email"  # email, form, api, phone
    sender_info: str = ""
    subject: str = ""
    content: str = ""
    
    # Metadata
    received_at: float = field(default_factory=time.time)
    is_acknowledgment: bool = False
    is_compliance: bool = False
    is_rejection: bool = False
    
    # Parsed information
    estimated_completion_time: Optional[float] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DMCAResponse':
        """Create from dictionary."""
        return cls(**data)


class DMCATemplateManager:
    """Manages DMCA notice templates."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.env = Environment(
            loader=FileSystemLoader('templates'),
            autoescape=True
        )
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load DMCA templates."""
        try:
            # Standard DMCA notice template
            self.templates['standard'] = self.env.from_string("""
Subject: DMCA Takedown Notice - Copyright Infringement

Dear Sir/Madam,

I am writing to notify you of copyright infringement occurring on your platform. This notice is submitted under the Digital Millennium Copyright Act (DMCA), 17 U.S.C. § 512.

IDENTIFICATION OF COPYRIGHTED WORK:
The copyrighted work being infringed is original content owned by {{ copyright_owner }}.
{% if original_work_url %}Original work URL: {{ original_work_url }}{% endif %}
{% if original_work_title %}Title/Description: {{ original_work_title }}{% endif %}

IDENTIFICATION OF INFRINGING MATERIAL:
The infringing material is located at the following URL(s):
{{ infringing_url }}

DESCRIPTION OF INFRINGEMENT:
{{ infringement_description }}

STATEMENT OF GOOD FAITH BELIEF:
I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.

STATEMENT OF ACCURACY:
The information in this notification is accurate, and under penalty of perjury, I am authorized to act on behalf of the copyright owner.

CONTACT INFORMATION:
{{ dmca_sender_name }}
{{ dmca_sender_email }}

Please remove or disable access to the infringing material immediately. I request that you confirm the removal in writing.

Thank you for your cooperation.

Sincerely,
{{ dmca_sender_name }}
{{ dmca_sender_email }}
            """)
            
            # Follow-up template
            self.templates['followup'] = self.env.from_string("""
Subject: DMCA Takedown Notice - Follow-up (Request ID: {{ request_id }})

Dear Sir/Madam,

This is a follow-up to our DMCA takedown notice sent on {{ original_date }} regarding copyright infringement at:
{{ infringing_url }}

As we have not received confirmation that the infringing material has been removed, we are following up to ensure this matter receives prompt attention.

Under the DMCA, service providers are required to expeditiously remove infringing content upon receiving proper notification. Failure to do so may result in loss of safe harbor protections.

Please confirm removal of the infringing content or provide an explanation for any delay.

Original request details:
Request ID: {{ request_id }}
Copyright Owner: {{ copyright_owner }}
Infringing URL: {{ infringing_url }}

Thank you for your prompt attention to this matter.

Sincerely,
{{ dmca_sender_name }}
{{ dmca_sender_email }}
            """)
            
            logger.info("DMCA templates loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load DMCA templates", error=str(e))
    
    def render_notice(
        self,
        template_name: str,
        request: DMCARequest,
        **additional_context
    ) -> str:
        """Render a DMCA notice template."""
        try:
            template = self.templates.get(template_name, self.templates['standard'])
            
            context = {
                'request_id': request.request_id,
                'copyright_owner': request.copyright_owner,
                'original_work_title': request.original_work_title,
                'original_work_url': request.original_work_url,
                'infringing_url': request.infringing_url,
                'infringement_description': request.infringement_description,
                'dmca_sender_name': self.settings.dmca_sender_name,
                'dmca_sender_email': self.settings.dmca_sender_email,
                'hosting_provider': request.hosting_provider,
                'original_date': datetime.fromtimestamp(request.created_at).strftime('%Y-%m-%d'),
                **additional_context
            }
            
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Failed to render DMCA template: {template_name}", error=str(e))
            return ""


class ContactInfoResolver:
    """Resolves contact information for hosting providers."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.contact_cache = {}
    
    async def initialize(self):
        """Initialize the resolver."""
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def resolve_contact_info(self, domain: str) -> Dict[str, str]:
        """Resolve contact information for a domain."""
        if domain in self.contact_cache:
            return self.contact_cache[domain]
        
        contact_info = {
            'email': '',
            'form_url': '',
            'abuse_email': '',
            'dmca_email': ''
        }
        
        try:
            # Try to find DMCA contact info
            dmca_info = await self._find_dmca_contacts(domain)
            contact_info.update(dmca_info)
            
            # Try WHOIS lookup for abuse contacts
            abuse_info = await self._find_abuse_contacts(domain)
            contact_info.update(abuse_info)
            
            # Cache the result
            self.contact_cache[domain] = contact_info
            
        except Exception as e:
            logger.error(f"Failed to resolve contact info for {domain}", error=str(e))
        
        return contact_info
    
    async def _find_dmca_contacts(self, domain: str) -> Dict[str, str]:
        """Find DMCA-specific contact information."""
        contacts = {}
        
        try:
            # Common DMCA contact URLs
            dmca_urls = [
                f"https://{domain}/dmca",
                f"https://{domain}/copyright",
                f"https://{domain}/takedown",
                f"https://{domain}/legal"
            ]
            
            for url in dmca_urls:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            text = await response.text()
                            
                            # Extract email addresses
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            emails = re.findall(email_pattern, text.lower())
                            
                            # Look for DMCA-related emails
                            for email in emails:
                                if any(keyword in email for keyword in ['dmca', 'copyright', 'legal', 'abuse']):
                                    contacts['dmca_email'] = email
                                    break
                            
                            # Look for contact forms
                            form_pattern = r'<form[^>]*action="([^"]*)"'
                            forms = re.findall(form_pattern, text.lower())
                            if forms:
                                contacts['form_url'] = forms[0]
                            
                            if contacts:
                                break
                                
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"DMCA contact lookup failed for {domain}", error=str(e))
        
        return contacts
    
    async def _find_abuse_contacts(self, domain: str) -> Dict[str, str]:
        """Find abuse contact information via WHOIS."""
        contacts = {}
        
        try:
            # This is a simplified implementation
            # In production, you'd use a proper WHOIS library or service
            
            # Common abuse email patterns
            abuse_emails = [
                f"abuse@{domain}",
                f"dmca@{domain}",
                f"legal@{domain}",
                f"support@{domain}"
            ]
            
            # Test which emails might be valid (basic check)
            for email in abuse_emails:
                if '@' in email and '.' in email:
                    contacts['abuse_email'] = email
                    break
                    
        except Exception as e:
            logger.debug(f"Abuse contact lookup failed for {domain}", error=str(e))
        
        return contacts


class DMCAQueue:
    """DMCA request queue and processing system."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.redis: Optional[aioredis.Redis] = None
        self.template_manager = DMCATemplateManager(settings)
        self.contact_resolver = ContactInfoResolver()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Queue keys
        self.pending_queue = "dmca:pending"
        self.processing_queue = "dmca:processing"
        self.completed_queue = "dmca:completed"
        self.failed_queue = "dmca:failed"
        
    async def initialize(self):
        """Initialize the DMCA queue system."""
        # Connect to Redis
        self.redis = aioredis.from_url(
            self.settings.redis_url,
            encoding='utf-8',
            decode_responses=True
        )
        
        # Initialize sub-components
        await self.contact_resolver.initialize()
        
        # Setup HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        logger.info("DMCA queue system initialized")
    
    async def close(self):
        """Clean up resources."""
        if self.redis:
            await self.redis.close()
        
        await self.contact_resolver.close()
        
        if self.session:
            await self.session.close()
    
    async def enqueue_request(self, request: DMCARequest) -> bool:
        """Add a DMCA request to the queue."""
        try:
            # Enrich request with contact information
            await self._enrich_request(request)
            
            # Serialize and add to pending queue
            request_data = json.dumps(request.to_dict())
            
            # Use priority scoring for queue ordering
            priority_score = self._calculate_priority_score(request)
            
            await self.redis.zadd(self.pending_queue, {request.request_id: priority_score})
            await self.redis.hset(f"dmca:request:{request.request_id}", mapping={"data": request_data})
            
            logger.info(
                f"DMCA request enqueued",
                request_id=request.request_id,
                url=request.infringing_url,
                priority=request.priority
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue DMCA request: {request.request_id}", error=str(e))
            return False
    
    async def _enrich_request(self, request: DMCARequest):
        """Enrich request with contact information and metadata."""
        try:
            # Get hosting provider info
            domain = request.hosting_provider
            contact_info = await self.contact_resolver.resolve_contact_info(domain)
            
            # Update request with contact info
            if contact_info.get('dmca_email'):
                request.contact_email = contact_info['dmca_email']
            elif contact_info.get('abuse_email'):
                request.contact_email = contact_info['abuse_email']
            
            if contact_info.get('form_url'):
                request.contact_form_url = contact_info['form_url']
            
            # Set default infringement description if not provided
            if not request.infringement_description:
                request.infringement_description = (
                    f"The above URL contains copyrighted material belonging to {request.copyright_owner} "
                    f"that has been posted without authorization. This constitutes copyright infringement "
                    f"under applicable copyright laws."
                )
            
        except Exception as e:
            logger.error(f"Failed to enrich DMCA request: {request.request_id}", error=str(e))
    
    def _calculate_priority_score(self, request: DMCARequest) -> float:
        """Calculate priority score for queue ordering (higher = more urgent)."""
        base_score = 5 - request.priority  # Invert priority (1=high becomes 4)
        
        # Age factor (older requests get higher priority)
        age_hours = (time.time() - request.created_at) / 3600
        age_factor = min(age_hours / 24, 2.0)  # Max 2 points for age
        
        # Content type factor
        content_factor = 0
        if request.content_match:
            content_factor = request.content_match.confidence_score * 2
        
        # High-profile site factor
        site_factor = 0
        if request.hosting_provider.lower() in ['google.com', 'bing.com', 'youtube.com', 'reddit.com']:
            site_factor = 1.0
        
        return base_score + age_factor + content_factor + site_factor
    
    async def process_pending_requests(self, max_requests: int = 10) -> int:
        """Process pending DMCA requests."""
        processed_count = 0
        
        try:
            # Get highest priority requests
            request_ids = await self.redis.zrevrange(
                self.pending_queue, 0, max_requests - 1
            )
            
            for request_id in request_ids:
                try:
                    # Load request data
                    request_data = await self.redis.hget(
                        f"dmca:request:{request_id}", "data"
                    )
                    
                    if not request_data:
                        continue
                    
                    request = DMCARequest.from_dict(json.loads(request_data))
                    
                    # Process the request
                    success = await self._process_single_request(request)
                    
                    if success:
                        # Move to processing queue
                        await self.redis.zrem(self.pending_queue, request_id)
                        await self.redis.zadd(
                            self.processing_queue,
                            {request_id: time.time()}
                        )
                        processed_count += 1
                    else:
                        # Update attempt count and potentially move to failed
                        request.increment_attempt()
                        if not request.can_retry:
                            await self.redis.zrem(self.pending_queue, request_id)
                            await self.redis.zadd(
                                self.failed_queue,
                                {request_id: time.time()}
                            )
                        
                        # Update stored request
                        updated_data = json.dumps(request.to_dict())
                        await self.redis.hset(
                            f"dmca:request:{request_id}",
                            mapping={"data": updated_data}
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to process DMCA request: {request_id}", error=str(e))
                    continue
            
        except Exception as e:
            logger.error("Failed to process pending DMCA requests", error=str(e))
        
        logger.info(f"Processed {processed_count} DMCA requests")
        return processed_count
    
    async def _process_single_request(self, request: DMCARequest) -> bool:
        """Process a single DMCA request."""
        try:
            request.update_status(DMCAStatus.PROCESSING)
            
            # Generate DMCA notice
            notice_content = self.template_manager.render_notice('standard', request)
            
            if not notice_content:
                request.update_status(DMCAStatus.FAILED, "Failed to generate DMCA notice")
                return False
            
            # Send notice
            if request.contact_email:
                success = await self._send_email_notice(request, notice_content)
            elif request.contact_form_url:
                success = await self._send_form_notice(request, notice_content)
            else:
                request.update_status(DMCAStatus.FAILED, "No contact method available")
                return False
            
            if success:
                request.update_status(DMCAStatus.SENT)
                logger.info(f"DMCA notice sent successfully: {request.request_id}")
                return True
            else:
                request.update_status(DMCAStatus.FAILED, "Failed to send notice")
                return False
                
        except Exception as e:
            request.update_status(DMCAStatus.FAILED, f"Processing error: {str(e)}")
            logger.error(f"DMCA request processing failed: {request.request_id}", error=str(e))
            return False
    
    async def _send_email_notice(self, request: DMCARequest, content: str) -> bool:
        """Send DMCA notice via email."""
        try:
            # This would integrate with your email service (SendGrid, etc.)
            # For now, we'll just log the action
            
            logger.info(
                f"DMCA email notice would be sent",
                request_id=request.request_id,
                to_email=request.contact_email,
                hosting_provider=request.hosting_provider
            )
            
            # In a real implementation:
            # 1. Use SendGrid/SES/etc. to send email
            # 2. Include proper headers and formatting
            # 3. Handle delivery confirmations
            # 4. Store sent message details
            
            return True  # Simulate success
            
        except Exception as e:
            logger.error(f"Failed to send DMCA email: {request.request_id}", error=str(e))
            return False
    
    async def _send_form_notice(self, request: DMCARequest, content: str) -> bool:
        """Send DMCA notice via web form."""
        try:
            # This would automate form submission to DMCA contact forms
            # Complex implementation involving form parsing and submission
            
            logger.info(
                f"DMCA form notice would be sent",
                request_id=request.request_id,
                form_url=request.contact_form_url,
                hosting_provider=request.hosting_provider
            )
            
            return True  # Simulate success
            
        except Exception as e:
            logger.error(f"Failed to send DMCA form: {request.request_id}", error=str(e))
            return False
    
    async def get_queue_status(self) -> Dict[str, int]:
        """Get status of all queues."""
        try:
            status = {
                'pending': await self.redis.zcard(self.pending_queue),
                'processing': await self.redis.zcard(self.processing_queue),
                'completed': await self.redis.zcard(self.completed_queue),
                'failed': await self.redis.zcard(self.failed_queue)
            }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get queue status", error=str(e))
            return {}
    
    async def get_request_status(self, request_id: str) -> Optional[DMCARequest]:
        """Get status of a specific request."""
        try:
            request_data = await self.redis.hget(
                f"dmca:request:{request_id}", "data"
            )
            
            if request_data:
                return DMCARequest.from_dict(json.loads(request_data))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get request status: {request_id}", error=str(e))
            return None
    
    async def cleanup_old_requests(self, days_old: int = 30) -> int:
        """Clean up old completed/failed requests."""
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            cleaned_count = 0
            
            # Clean completed requests
            old_completed = await self.redis.zrangebyscore(
                self.completed_queue, 0, cutoff_time
            )
            
            for request_id in old_completed:
                await self.redis.zrem(self.completed_queue, request_id)
                await self.redis.delete(f"dmca:request:{request_id}")
                cleaned_count += 1
            
            # Clean failed requests
            old_failed = await self.redis.zrangebyscore(
                self.failed_queue, 0, cutoff_time
            )
            
            for request_id in old_failed:
                await self.redis.zrem(self.failed_queue, request_id)
                await self.redis.delete(f"dmca:request:{request_id}")
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old DMCA requests")
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup old requests", error=str(e))
            return 0