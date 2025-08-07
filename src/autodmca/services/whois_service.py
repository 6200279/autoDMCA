"""
WHOIS Lookup Service

Provides WHOIS domain lookup functionality to identify hosting providers,
contact information, and DMCA agent details for takedown notices.
"""

import re
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import asyncio
import logging

import whois
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models.hosting import HostingProvider, ContactInfo, DMCAAgent
from ..utils.cache import CacheManager
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class WHOISService:
    """
    Service for performing WHOIS lookups and extracting hosting provider information.
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 10
    ):
        """
        Initialize WHOIS service.
        
        Args:
            cache_manager: Optional cache for WHOIS results
            rate_limiter: Optional rate limiter for API calls
            timeout: Timeout for WHOIS queries in seconds
        """
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=60, time_window=60)
        self.timeout = timeout
        
        # Configure HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Known hosting providers and their DMCA contact patterns
        self.known_providers = self._load_known_providers()
        
        # WHOIS server overrides for better results
        self.whois_servers = {
            'com': 'whois.verisign-grs.com',
            'net': 'whois.verisign-grs.com', 
            'org': 'whois.pir.org',
            'info': 'whois.afilias.net',
            'biz': 'whois.neulevel.biz',
        }
    
    async def lookup_domain(self, url: str) -> Optional[HostingProvider]:
        """
        Perform WHOIS lookup for a URL and extract hosting provider information.
        
        Args:
            url: The URL to lookup
        
        Returns:
            HostingProvider object with contact information, or None if lookup fails
        """
        try:
            # Extract domain from URL
            domain = self._extract_domain(url)
            if not domain:
                logger.warning(f"Could not extract domain from URL: {url}")
                return None
            
            # Check cache first
            cache_key = f"whois:{domain}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Using cached WHOIS data for {domain}")
                return HostingProvider(**cached_result)
            
            # Rate limit check
            await self.rate_limiter.acquire()
            
            # Perform WHOIS lookup
            whois_data = await self._perform_whois_lookup(domain)
            if not whois_data:
                return None
            
            # Extract hosting provider information
            hosting_provider = await self._extract_hosting_info(domain, whois_data)
            
            # Enhance with additional contact information
            if hosting_provider:
                hosting_provider = await self._enhance_contact_info(hosting_provider)
                
                # Cache the result
                await self.cache_manager.set(
                    cache_key, 
                    hosting_provider.model_dump(),
                    ttl=timedelta(days=7)
                )
            
            return hosting_provider
            
        except Exception as e:
            logger.error(f"WHOIS lookup failed for {url}: {str(e)}")
            return None
    
    async def lookup_ip_address(self, ip: str) -> Optional[HostingProvider]:
        """
        Perform reverse DNS and WHOIS lookup for an IP address.
        
        Args:
            ip: IP address to lookup
        
        Returns:
            HostingProvider with network information
        """
        try:
            # Validate IP address
            socket.inet_aton(ip)
            
            # Check cache
            cache_key = f"ip_whois:{ip}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return HostingProvider(**cached_result)
            
            await self.rate_limiter.acquire()
            
            # Perform IP WHOIS lookup
            result = await self._perform_ip_whois(ip)
            if result:
                await self.cache_manager.set(
                    cache_key,
                    result.model_dump(),
                    ttl=timedelta(days=1)
                )
            
            return result
            
        except Exception as e:
            logger.error(f"IP WHOIS lookup failed for {ip}: {str(e)}")
            return None
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            if not url.startswith(('http://', 'https://')):
                url = f"http://{url}"
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port number if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain if '.' in domain else None
            
        except Exception:
            return None
    
    async def _perform_whois_lookup(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Perform the actual WHOIS lookup with timeout and error handling.
        
        Args:
            domain: Domain to lookup
        
        Returns:
            Dictionary containing WHOIS data
        """
        try:
            # Use asyncio to run the blocking whois call with timeout
            loop = asyncio.get_event_loop()
            whois_result = await asyncio.wait_for(
                loop.run_in_executor(None, self._whois_query, domain),
                timeout=self.timeout
            )
            
            if not whois_result:
                return None
            
            # Convert whois object to dictionary
            whois_dict = {}
            for key in dir(whois_result):
                if not key.startswith('_'):
                    value = getattr(whois_result, key)
                    if value is not None:
                        # Convert datetime objects to strings
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        elif isinstance(value, list):
                            # Handle lists of values
                            value = [str(v) for v in value if v is not None]
                        else:
                            value = str(value)
                        whois_dict[key] = value
            
            return whois_dict
            
        except asyncio.TimeoutError:
            logger.warning(f"WHOIS lookup timeout for {domain}")
            return None
        except Exception as e:
            logger.error(f"WHOIS lookup error for {domain}: {str(e)}")
            return None
    
    def _whois_query(self, domain: str) -> Optional[Any]:
        """Blocking WHOIS query."""
        try:
            return whois.whois(domain)
        except Exception:
            return None
    
    async def _extract_hosting_info(self, domain: str, whois_data: Dict[str, Any]) -> Optional[HostingProvider]:
        """
        Extract hosting provider information from WHOIS data.
        
        Args:
            domain: The domain being looked up
            whois_data: Raw WHOIS data
        
        Returns:
            HostingProvider object with extracted information
        """
        try:
            # Extract basic information
            registrar = whois_data.get('registrar', '')
            name_servers = whois_data.get('name_servers', [])
            
            # Determine hosting provider name
            provider_name = self._identify_provider(registrar, name_servers, domain)
            
            # Extract contact information
            contacts = self._extract_contacts(whois_data)
            
            # Create hosting provider object
            hosting_provider = HostingProvider(
                domain=domain,
                name=provider_name,
                registrar=registrar,
                whois_server=whois_data.get('whois_server', ''),
                
                # Contact information
                administrative_contact=contacts.get('admin'),
                technical_contact=contacts.get('tech'),
                
                # WHOIS metadata
                created_at=datetime.utcnow(),
                last_verified=datetime.utcnow(),
                metadata={
                    'name_servers': name_servers,
                    'creation_date': whois_data.get('creation_date'),
                    'expiration_date': whois_data.get('expiration_date'),
                    'updated_date': whois_data.get('updated_date'),
                    'status': whois_data.get('status', []),
                }
            )
            
            return hosting_provider
            
        except Exception as e:
            logger.error(f"Error extracting hosting info for {domain}: {str(e)}")
            return None
    
    def _identify_provider(self, registrar: str, name_servers: List[str], domain: str) -> str:
        """Identify hosting provider from WHOIS data."""
        # Check known providers first
        for provider_pattern, provider_info in self.known_providers.items():
            if provider_pattern.lower() in registrar.lower():
                return provider_info['name']
            
            # Check name servers
            for ns in name_servers:
                if isinstance(ns, str) and provider_pattern.lower() in ns.lower():
                    return provider_info['name']
        
        # Extract provider name from registrar or name servers
        if registrar:
            # Clean up registrar name
            cleaned = re.sub(r'[,.]?\s*(inc|llc|corp|ltd)\.?$', '', registrar, flags=re.IGNORECASE)
            return cleaned.strip() or registrar
        
        # Fallback to name server analysis
        if name_servers:
            for ns in name_servers:
                if isinstance(ns, str):
                    # Extract provider from name server (e.g., ns1.google.com -> Google)
                    parts = ns.split('.')
                    if len(parts) >= 2:
                        provider_part = parts[-2]  # Second to last part
                        if provider_part not in ['name', 'dns', 'ns']:
                            return provider_part.capitalize()
        
        return f"Provider for {domain}"
    
    def _extract_contacts(self, whois_data: Dict[str, Any]) -> Dict[str, ContactInfo]:
        """Extract contact information from WHOIS data."""
        contacts = {}
        
        # Contact type mappings
        contact_mappings = {
            'admin': ['admin_', 'administrative_'],
            'tech': ['tech_', 'technical_'],
            'registrant': ['registrant_', ''],
        }
        
        for contact_type, prefixes in contact_mappings.items():
            contact = self._extract_single_contact(whois_data, prefixes)
            if contact:
                contacts[contact_type] = contact
        
        return contacts
    
    def _extract_single_contact(self, whois_data: Dict[str, Any], prefixes: List[str]) -> Optional[ContactInfo]:
        """Extract a single contact from WHOIS data."""
        contact_data = {}
        
        # Fields to extract
        fields = {
            'name': 'name',
            'email': 'email', 
            'phone': 'phone',
            'fax': 'fax',
            'address': 'address',
            'city': 'city',
            'state': 'state',
            'postal_code': 'postal_code',
            'country': 'country',
        }
        
        # Try each prefix
        for prefix in prefixes:
            for field, contact_field in fields.items():
                # Try different WHOIS field variations
                possible_keys = [
                    f"{prefix}{field}",
                    f"{prefix}{field}s",
                    field if prefix == '' else None
                ]
                
                for key in filter(None, possible_keys):
                    value = whois_data.get(key)
                    if value and not contact_data.get(contact_field):
                        if isinstance(value, list) and value:
                            contact_data[contact_field] = value[0]
                        else:
                            contact_data[contact_field] = str(value)
                        break
        
        # Only create contact if we have at least name and email
        if contact_data.get('name') and contact_data.get('email'):
            try:
                return ContactInfo(
                    name=contact_data.get('name'),
                    email=contact_data.get('email'),
                    phone=contact_data.get('phone'),
                    fax=contact_data.get('fax'),
                    address_line1=contact_data.get('address'),
                    city=contact_data.get('city'),
                    state_province=contact_data.get('state'),
                    postal_code=contact_data.get('postal_code'),
                    country=contact_data.get('country'),
                )
            except Exception as e:
                logger.warning(f"Error creating contact info: {str(e)}")
                return None
        
        return None
    
    async def _enhance_contact_info(self, hosting_provider: HostingProvider) -> HostingProvider:
        """
        Enhance hosting provider with additional contact information.
        
        This method attempts to find DMCA-specific contact information
        by checking the provider's website and known databases.
        """
        try:
            # Check if we have a known provider with enhanced info
            known_info = self.known_providers.get(hosting_provider.name.lower())
            if known_info:
                # Update with known DMCA contacts
                if 'dmca_email' in known_info:
                    hosting_provider.dmca_email = known_info['dmca_email']
                if 'abuse_email' in known_info:
                    hosting_provider.abuse_email = known_info['abuse_email']
                if 'dmca_policy_url' in known_info:
                    hosting_provider.dmca_policy_url = known_info['dmca_policy_url']
            
            # Try to find abuse email if not already present
            if not hosting_provider.abuse_email:
                abuse_email = await self._find_abuse_email(hosting_provider.domain)
                if abuse_email:
                    hosting_provider.abuse_email = abuse_email
            
            # Set default DMCA email if not found
            if not hosting_provider.dmca_email:
                if hosting_provider.abuse_email:
                    hosting_provider.dmca_email = hosting_provider.abuse_email
                else:
                    # Common DMCA email patterns
                    common_emails = [
                        f"dmca@{hosting_provider.domain}",
                        f"abuse@{hosting_provider.domain}",
                        f"legal@{hosting_provider.domain}",
                    ]
                    hosting_provider.dmca_email = common_emails[0]  # Best guess
            
            return hosting_provider
            
        except Exception as e:
            logger.error(f"Error enhancing contact info: {str(e)}")
            return hosting_provider
    
    async def _find_abuse_email(self, domain: str) -> Optional[str]:
        """Attempt to find abuse email for a domain."""
        try:
            # Try common abuse email addresses
            common_abuse_emails = [
                f"abuse@{domain}",
                f"dmca@{domain}",
                f"legal@{domain}",
                f"copyright@{domain}",
            ]
            
            # In a production system, you might want to verify these emails
            # For now, return the most common one
            return common_abuse_emails[0]
            
        except Exception:
            return None
    
    async def _perform_ip_whois(self, ip: str) -> Optional[HostingProvider]:
        """Perform WHOIS lookup for IP address."""
        try:
            # This is a simplified implementation
            # In production, you'd use specialized IP WHOIS databases
            
            # Try reverse DNS first
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                if hostname:
                    # Extract domain from hostname
                    domain_parts = hostname.split('.')
                    if len(domain_parts) >= 2:
                        domain = '.'.join(domain_parts[-2:])
                        return await self.lookup_domain(domain)
            except socket.herror:
                pass
            
            # Fallback to basic IP-based provider info
            return HostingProvider(
                name=f"Provider for {ip}",
                domain=ip,
                metadata={'ip_address': ip, 'lookup_method': 'ip_whois'}
            )
            
        except Exception as e:
            logger.error(f"IP WHOIS lookup failed for {ip}: {str(e)}")
            return None
    
    def _load_known_providers(self) -> Dict[str, Dict[str, str]]:
        """Load known hosting providers with their contact information."""
        return {
            # Major cloud providers
            'amazon': {
                'name': 'Amazon Web Services',
                'dmca_email': 'dmca-notice@amazon.com',
                'abuse_email': 'abuse@amazonaws.com',
                'dmca_policy_url': 'https://aws.amazon.com/aup/',
            },
            'google': {
                'name': 'Google Cloud Platform',
                'dmca_email': 'dmca@google.com',
                'abuse_email': 'abuse@google.com',
                'dmca_policy_url': 'https://www.google.com/dmca.html',
            },
            'microsoft': {
                'name': 'Microsoft Azure',
                'dmca_email': 'dmca@microsoft.com',
                'abuse_email': 'abuse@microsoft.com',
                'dmca_policy_url': 'https://www.microsoft.com/en-us/legal/dmca',
            },
            'cloudflare': {
                'name': 'Cloudflare',
                'dmca_email': 'dmca@cloudflare.com',
                'abuse_email': 'abuse@cloudflare.com',
                'dmca_policy_url': 'https://www.cloudflare.com/dmca/',
            },
            
            # Popular hosting providers
            'godaddy': {
                'name': 'GoDaddy',
                'dmca_email': 'dmca@godaddy.com',
                'abuse_email': 'abuse@godaddy.com',
                'dmca_policy_url': 'https://www.godaddy.com/agreements/dmca',
            },
            'namecheap': {
                'name': 'Namecheap',
                'dmca_email': 'dmca@namecheap.com',
                'abuse_email': 'abuse@namecheap.com',
            },
            'bluehost': {
                'name': 'Bluehost',
                'dmca_email': 'dmca@bluehost.com',
                'abuse_email': 'abuse@bluehost.com',
            },
            'hostgator': {
                'name': 'HostGator',
                'dmca_email': 'dmca@hostgator.com',
                'abuse_email': 'abuse@hostgator.com',
            },
        }