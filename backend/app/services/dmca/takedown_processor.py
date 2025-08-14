"""
Automated DMCA Takedown Processing System
Generates and dispatches DMCA notices automatically
"""
import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
import aiohttp
from enum import Enum
from dataclasses import dataclass
import whois
from urllib.parse import urlparse
import dns.resolver
import re

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)


class TakedownStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    REMOVED = "removed"
    DELISTED = "delisted"
    REJECTED = "rejected"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class TakedownRequest:
    """DMCA takedown request data"""
    infringement_url: str
    original_content_url: str
    profile_data: Dict[str, Any]
    host_provider: str
    abuse_email: str
    status: TakedownStatus
    notice_text: str
    sent_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    response_text: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None


class DMCATakedownProcessor:
    """
    Automated DMCA takedown notice generation and dispatch
    PRD: "automatically generate and issue DMCA takedown requests"
    """
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.dmca_agent_email = os.getenv('DMCA_AGENT_EMAIL', 'dmca@contentprotection.com')
        self.dmca_agent_name = os.getenv('DMCA_AGENT_NAME', 'Content Protection Service')
        
        # Cache for host provider lookups
        self.provider_cache = {}
        
        # Known host provider abuse contacts
        self.known_providers = {
            'cloudflare.com': 'abuse@cloudflare.com',
            'godaddy.com': 'abuse@godaddy.com',
            'namecheap.com': 'abuse@namecheap.com',
            'hostgator.com': 'abuse@hostgator.com',
            'bluehost.com': 'abuse@bluehost.com',
            'digitalocean.com': 'abuse@digitalocean.com',
            'aws.amazon.com': 'abuse@amazonaws.com',
            'google.com': 'dmca@google.com',
            'microsoft.com': 'abuse@microsoft.com',
            'facebook.com': 'ip@fb.com',
            'twitter.com': 'copyright@twitter.com',
            'instagram.com': 'ip@fb.com',
            'tiktok.com': 'copyright@tiktok.com',
            'reddit.com': 'copyright@reddit.com',
            'mega.nz': 'copyright@mega.nz',
            'imgur.com': 'copyright@imgur.com',
            'tumblr.com': 'dmca@tumblr.com'
        }
        
    async def process_infringement(
        self,
        infringement_url: str,
        profile_data: Dict[str, Any],
        original_content_url: Optional[str] = None,
        priority: bool = False
    ) -> TakedownRequest:
        """
        Main entry point for processing an infringement
        PRD: "automatically generate and issue DMCA takedown requests"
        """
        try:
            # Step 1: Identify host provider
            host_provider, abuse_email = await self._identify_host_provider(
                infringement_url
            )
            
            if not abuse_email:
                logger.warning(f"No abuse contact found for {infringement_url}")
                # Fall back to search engine delisting
                return await self._create_delisting_request(
                    infringement_url, profile_data
                )
                
            # Step 2: Generate DMCA notice
            notice_text = self._generate_dmca_notice(
                infringement_url,
                original_content_url or profile_data.get('profile_url', ''),
                profile_data
            )
            
            # Step 3: Create takedown request
            request = TakedownRequest(
                infringement_url=infringement_url,
                original_content_url=original_content_url,
                profile_data=profile_data,
                host_provider=host_provider,
                abuse_email=abuse_email,
                status=TakedownStatus.PENDING,
                notice_text=notice_text,
                metadata={
                    'priority': priority,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            # Step 4: Send the notice
            if priority:
                # Send immediately for priority requests
                await self._send_dmca_notice(request)
            else:
                # Queue for batch sending
                await self._queue_takedown(request)
                
            return request
            
        except Exception as e:
            logger.error(f"Error processing infringement {infringement_url}: {e}")
            return TakedownRequest(
                infringement_url=infringement_url,
                original_content_url=original_content_url,
                profile_data=profile_data,
                host_provider="unknown",
                abuse_email="",
                status=TakedownStatus.FAILED,
                notice_text="",
                metadata={'error': str(e)}
            )
            
    async def _identify_host_provider(
        self,
        url: str
    ) -> Tuple[str, str]:
        """
        Identify hosting provider and abuse contact
        PRD: "determines the hosting provider or website owner contact"
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Check cache first
            if domain in self.provider_cache:
                return self.provider_cache[domain]
                
            # Check known providers
            for provider, email in self.known_providers.items():
                if provider in domain:
                    result = (provider, email)
                    self.provider_cache[domain] = result
                    return result
                    
            # WHOIS lookup for hosting provider
            try:
                w = whois.whois(domain)
                
                # Look for abuse email in WHOIS
                abuse_email = None
                
                # Check various WHOIS fields
                if hasattr(w, 'emails'):
                    if isinstance(w.emails, list):
                        for email in w.emails:
                            if 'abuse' in email.lower():
                                abuse_email = email
                                break
                    elif isinstance(w.emails, str) and 'abuse' in w.emails.lower():
                        abuse_email = w.emails
                        
                # If no abuse email, try registrar
                if not abuse_email and hasattr(w, 'registrar'):
                    registrar = w.registrar.lower() if w.registrar else ''
                    for provider, email in self.known_providers.items():
                        if provider in registrar:
                            abuse_email = email
                            break
                            
                # Extract hosting provider name
                provider_name = 'unknown'
                if hasattr(w, 'org'):
                    provider_name = w.org or 'unknown'
                elif hasattr(w, 'registrar'):
                    provider_name = w.registrar or 'unknown'
                    
                result = (provider_name, abuse_email or '')
                self.provider_cache[domain] = result
                return result
                
            except Exception as e:
                logger.error(f"WHOIS lookup failed for {domain}: {e}")
                
            # DNS lookup for hosting provider
            try:
                # Get IP address
                answers = dns.resolver.resolve(domain, 'A')
                if answers:
                    ip = str(answers[0])
                    # Reverse DNS lookup
                    rev_name = dns.reversename.from_address(ip)
                    rev_answers = dns.resolver.resolve(rev_name, 'PTR')
                    if rev_answers:
                        ptr_record = str(rev_answers[0])
                        # Check if it matches known providers
                        for provider, email in self.known_providers.items():
                            if provider in ptr_record.lower():
                                result = (provider, email)
                                self.provider_cache[domain] = result
                                return result
                                
            except Exception as e:
                logger.debug(f"DNS lookup failed for {domain}: {e}")
                
            # Default fallback
            return ('unknown', '')
            
        except Exception as e:
            logger.error(f"Error identifying host provider for {url}: {e}")
            return ('unknown', '')
            
    def _generate_dmca_notice(
        self,
        infringement_url: str,
        original_url: str,
        profile_data: Dict[str, Any]
    ) -> str:
        """
        Generate a formal DMCA takedown notice
        PRD: "populate the notice with all required information"
        """
        
        creator_name = profile_data.get('public_name', 'Content Creator')
        creator_username = profile_data.get('username', '')
        platform = profile_data.get('platform', '')
        
        notice = f"""
DMCA TAKEDOWN NOTICE

Date: {datetime.utcnow().strftime('%Y-%m-%d')}

To Whom It May Concern:

I am writing on behalf of {creator_name} to notify you of copyright infringement on your platform/service.

1. IDENTIFICATION OF COPYRIGHTED WORK:
The copyrighted work at issue is exclusive content created and owned by {creator_name}.
"""

        if original_url:
            notice += f"\nOriginal authorized location: {original_url}"
            
        if platform:
            notice += f"\nContent originally published on: {platform}"
            
        if creator_username:
            notice += f"\nCreator username/handle: {creator_username}"
            
        notice += f"""

2. IDENTIFICATION OF INFRINGING MATERIAL:
The following URL(s) contain unauthorized copies of the copyrighted work:
{infringement_url}

3. CONTACT INFORMATION:
{self.dmca_agent_name}
Acting as authorized agent for {creator_name}
Email: {self.dmca_agent_email}

4. GOOD FAITH STATEMENT:
I have a good faith belief that the use of the copyrighted materials described above is not authorized by the copyright owner, its agent, or the law. The information in this notification is accurate.

5. STATEMENT UNDER PENALTY OF PERJURY:
I swear, under penalty of perjury, that I am authorized to act on behalf of the owner of the copyright that is allegedly infringed.

6. REQUESTED ACTION:
Please immediately remove or disable access to the infringing material identified above.

Under 17 U.S.C. § 512(c), you must expeditiously remove or disable access to the material identified above upon receipt of this notice. Failure to do so may result in loss of your safe harbor protections under the DMCA.

We appreciate your cooperation in this matter and request confirmation once the content has been removed.

Sincerely,

{self.dmca_agent_name}
Authorized DMCA Agent
"""
        
        return notice
        
    async def _send_dmca_notice(self, request: TakedownRequest) -> bool:
        """
        Send DMCA notice via email
        PRD: "sends a formal takedown notice compliant with the Digital Millennium Copyright Act"
        """
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = f"{self.dmca_agent_name} <{self.dmca_agent_email}>"
            message["To"] = request.abuse_email
            message["Subject"] = f"DMCA Takedown Notice - {request.infringement_url}"
            
            # Add notice text
            message.attach(MIMEText(request.notice_text, "plain"))
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                    
                server.send_message(message)
                
            # Update request status
            request.status = TakedownStatus.SENT
            request.sent_date = datetime.utcnow()
            
            logger.info(f"DMCA notice sent to {request.abuse_email} for {request.infringement_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send DMCA notice: {e}")
            request.status = TakedownStatus.FAILED
            request.metadata['send_error'] = str(e)
            return False
            
    async def _queue_takedown(self, request: TakedownRequest):
        """
        Queue takedown for batch processing
        """
        # In production, this would add to a message queue (RabbitMQ, Redis, etc.)
        # For MVP, we'll process immediately
        await self._send_dmca_notice(request)
        
    async def _create_delisting_request(
        self,
        url: str,
        profile_data: Dict[str, Any]
    ) -> TakedownRequest:
        """
        Create a search engine delisting request when direct takedown isn't possible
        PRD: "fall back to search engine delisting"
        """
        return TakedownRequest(
            infringement_url=url,
            original_content_url=profile_data.get('profile_url', ''),
            profile_data=profile_data,
            host_provider="search_engines",
            abuse_email="",
            status=TakedownStatus.PENDING,
            notice_text="Search engine delisting required",
            metadata={
                'delisting_required': True,
                'reason': 'No host provider contact found'
            }
        )
        
    async def send_search_engine_delisting(
        self,
        urls: List[str],
        profile_data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Submit URLs for search engine delisting
        PRD: "automatically submitting requests to Google, Bing, etc., to remove the offending URLs"
        """
        results = {}
        
        for url in urls:
            # Google URL removal
            google_success = await self._submit_google_removal(url, profile_data)
            results[f"{url}_google"] = google_success
            
            # Bing URL removal
            bing_success = await self._submit_bing_removal(url, profile_data)
            results[f"{url}_bing"] = bing_success
            
        return results
        
    async def _submit_google_removal(
        self,
        url: str,
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        Submit URL removal request to Google
        """
        try:
            # Google Search Console API endpoint
            # Note: Requires OAuth2 authentication in production
            api_url = "https://searchconsole.googleapis.com/v1/urlRemovals"
            
            # In production, this would use proper OAuth2
            headers = {
                "Authorization": f"Bearer {os.getenv('GOOGLE_SEARCH_CONSOLE_TOKEN', '')}",
                "Content-Type": "application/json"
            }
            
            data = {
                "siteUrl": urlparse(url).netloc,
                "url": url,
                "type": "URL_TEMPORARY_REMOVAL"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Google removal request submitted for {url}")
                        return True
                    else:
                        logger.error(f"Google removal failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error submitting Google removal: {e}")
            return False
            
    async def _submit_bing_removal(
        self,
        url: str,
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        Submit URL removal request to Bing
        """
        try:
            # Bing Webmaster API endpoint
            api_url = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlRemoval"
            
            headers = {
                "Content-Type": "application/json",
                "ApiKey": os.getenv('BING_WEBMASTER_API_KEY', '')
            }
            
            data = {
                "siteUrl": urlparse(url).netloc,
                "url": url,
                "removalMethod": "page"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Bing removal request submitted for {url}")
                        return True
                    else:
                        logger.error(f"Bing removal failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error submitting Bing removal: {e}")
            return False
            
    async def check_takedown_status(
        self,
        request: TakedownRequest
    ) -> TakedownStatus:
        """
        Check the status of a takedown request
        """
        try:
            # Check if URL is still accessible
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    request.infringement_url,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 404:
                        request.status = TakedownStatus.REMOVED
                        request.response_date = datetime.utcnow()
                        return TakedownStatus.REMOVED
                    elif response.status == 451:  # Unavailable for legal reasons
                        request.status = TakedownStatus.REMOVED
                        request.response_date = datetime.utcnow()
                        return TakedownStatus.REMOVED
                    elif response.status == 200:
                        # Still accessible, check if delisted from search engines
                        from app.services.scanning.search_engines import SearchEngineScanner
                        scanner = SearchEngineScanner()
                        
                        async with scanner:
                            indexed = await scanner.check_url_in_search_index(
                                request.infringement_url
                            )
                            
                        if not indexed['google'] and not indexed['bing']:
                            request.status = TakedownStatus.DELISTED
                            return TakedownStatus.DELISTED
                            
        except aiohttp.ClientError as e:
            # Connection error might mean content removed
            if 'Cannot connect' in str(e):
                request.status = TakedownStatus.REMOVED
                return TakedownStatus.REMOVED
                
        except Exception as e:
            logger.error(f"Error checking takedown status: {e}")
            
        return request.status
        
    async def retry_failed_takedowns(self, max_retries: int = 3):
        """
        Retry failed takedown requests
        """
        # In production, this would query the database for failed requests
        # For now, this is a placeholder
        pass


import os  # Add this import at the top of the file