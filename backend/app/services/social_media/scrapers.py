"""
Web scraping engine for social media platforms with anti-detection measures.
"""

import asyncio
import random
import time
import socket
import ipaddress
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import hashlib
import json
import re

import aiohttp
import structlog
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    # Selenium not available for local testing
    webdriver = None
    SELENIUM_AVAILABLE = False

try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    UserAgent = None
    FAKE_USERAGENT_AVAILABLE = False

from app.db.models.social_media import SocialMediaPlatform
from .config import PlatformConfig, SocialMediaSettings
from .api_clients import ProfileData
from ..auth.rate_limiter import RateLimiter
from app.core.config import settings


logger = structlog.get_logger(__name__)


class SSRFProtection:
    """Server-Side Request Forgery protection for web scraping."""
    
    def __init__(self):
        # Define allowed domains for scraping
        self.allowed_domains = {
            'instagram.com', 'www.instagram.com',
            'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com',
            'facebook.com', 'www.facebook.com', 'm.facebook.com',
            'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com',
            'reddit.com', 'www.reddit.com', 'old.reddit.com',
            'linkedin.com', 'www.linkedin.com',
            'youtube.com', 'www.youtube.com', 'youtu.be',
            'pinterest.com', 'www.pinterest.com',
            'snapchat.com', 'www.snapchat.com'
        }
        
        # Private IP ranges to block (RFC 1918, RFC 3927, etc.)
        self.blocked_ip_ranges = [
            ipaddress.IPv4Network('127.0.0.0/8'),    # Loopback
            ipaddress.IPv4Network('10.0.0.0/8'),     # Private Class A
            ipaddress.IPv4Network('172.16.0.0/12'),  # Private Class B
            ipaddress.IPv4Network('192.168.0.0/16'), # Private Class C
            ipaddress.IPv4Network('169.254.0.0/16'), # Link-local
            ipaddress.IPv4Network('224.0.0.0/4'),    # Multicast
            ipaddress.IPv4Network('0.0.0.0/8'),      # "This" network
            ipaddress.IPv4Network('240.0.0.0/4'),    # Reserved
        ]
        
        # Additional blocked hostnames
        self.blocked_hostnames = {
            'localhost', 'local', '0.0.0.0', 'metadata.google.internal',
            'instance-data', 'metadata.aws.com', 'metadata.azure.com'
        }
        
        # Maximum redirects to follow
        self.max_redirects = 3
        
        # DNS cache to prevent repeated lookups
        self.dns_cache = {}
    
    def is_safe_url(self, url: str) -> tuple[bool, str]:
        """Check if URL is safe for scraping."""
        try:
            parsed = urlparse(url)
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False, "Only HTTP/HTTPS schemes allowed"
            
            # Must have hostname
            if not parsed.hostname:
                return False, "URL must have hostname"
            
            hostname = parsed.hostname.lower()
            
            # Check blocked hostnames
            if hostname in self.blocked_hostnames:
                return False, f"Hostname {hostname} is blocked"
            
            # Check if hostname matches allowed domains
            domain_allowed = False
            for allowed_domain in self.allowed_domains:
                if hostname == allowed_domain or hostname.endswith('.' + allowed_domain):
                    domain_allowed = True
                    break
            
            if not domain_allowed:
                return False, f"Domain {hostname} not in allowlist"
            
            # Resolve hostname and check IP
            is_ip_safe, ip_message = self._is_safe_ip(hostname)
            if not is_ip_safe:
                return False, ip_message
            
            # Check for suspicious patterns
            if self._has_suspicious_patterns(url):
                return False, "URL contains suspicious patterns"
            
            return True, "URL is safe"
            
        except Exception as e:
            logger.error("URL validation error", url=url, error=str(e))
            return False, f"URL validation failed: {str(e)}"
    
    def _is_safe_ip(self, hostname: str) -> tuple[bool, str]:
        """Check if resolved IP is safe."""
        try:
            # Check DNS cache first
            if hostname in self.dns_cache:
                ip = self.dns_cache[hostname]
            else:
                # Resolve hostname
                ip = socket.gethostbyname(hostname)
                self.dns_cache[hostname] = ip
            
            # Parse IP address
            ip_addr = ipaddress.IPv4Address(ip)
            
            # Check against blocked ranges
            for blocked_range in self.blocked_ip_ranges:
                if ip_addr in blocked_range:
                    return False, f"IP {ip} is in blocked range {blocked_range}"
            
            return True, "IP is safe"
            
        except socket.gaierror as e:
            return False, f"DNS resolution failed: {str(e)}"
        except ipaddress.AddressValueError as e:
            return False, f"Invalid IP address: {str(e)}"
        except Exception as e:
            return False, f"IP validation error: {str(e)}"
    
    def _has_suspicious_patterns(self, url: str) -> bool:
        """Check for suspicious URL patterns."""
        suspicious_patterns = [
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # Raw IP addresses
            r'localhost',
            r'127\.0\.0\.1',
            r'\.\./',  # Directory traversal
            r'file://',  # File protocol
            r'ftp://',   # FTP protocol
            r'gopher://', # Gopher protocol
            r'dict://',  # Dict protocol
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def validate_response_redirect(self, original_url: str, redirect_url: str) -> bool:
        """Validate redirect URL during response handling."""
        # Check if redirect is to a safe URL
        is_safe, message = self.is_safe_url(redirect_url)
        if not is_safe:
            logger.warning(
                "Blocked redirect to unsafe URL",
                original_url=original_url,
                redirect_url=redirect_url,
                reason=message
            )
            return False
        
        # Additional check: ensure redirect doesn't change domain drastically
        try:
            orig_domain = urlparse(original_url).hostname
            redir_domain = urlparse(redirect_url).hostname
            
            # Allow same domain or subdomains
            if orig_domain and redir_domain:
                if not (redir_domain == orig_domain or 
                       redir_domain.endswith('.' + orig_domain) or
                       orig_domain.endswith('.' + redir_domain)):
                    # Cross-domain redirect - extra scrutiny
                    if redir_domain not in self.allowed_domains:
                        logger.warning(
                            "Blocked cross-domain redirect",
                            original_domain=orig_domain,
                            redirect_domain=redir_domain
                        )
                        return False
        except Exception as e:
            logger.error("Redirect validation error", error=str(e))
            return False
        
        return True


@dataclass
class ScrapingSession:
    """Represents a scraping session with anti-detection measures."""
    session_id: str
    platform: SocialMediaPlatform
    user_agent: str
    proxy: Optional[str] = None
    cookies: Dict[str, str] = None
    created_at: float = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.cookies:
            self.cookies = {}


class AntiDetectionManager:
    """Manages anti-detection measures for secure web scraping."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.ua = UserAgent() if FAKE_USERAGENT_AVAILABLE else None
        self.user_agents = self._load_user_agents()
        self.proxies = []
        self.sessions: Dict[str, ScrapingSession] = {}
        self.request_delays: Dict[SocialMediaPlatform, float] = {}
        self.ssrf_protection = SSRFProtection()
        
    def _load_user_agents(self) -> List[str]:
        """Load realistic user agents for different browsers."""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
    
    def get_user_agent(self, platform: SocialMediaPlatform) -> str:
        """Get appropriate user agent for platform."""
        # Some platforms work better with specific browsers
        platform_preferences = {
            SocialMediaPlatform.INSTAGRAM: ["Chrome", "Safari"],
            SocialMediaPlatform.TWITTER: ["Chrome", "Firefox"],
            SocialMediaPlatform.TIKTOK: ["Chrome"],
            SocialMediaPlatform.FACEBOOK: ["Chrome", "Firefox"],
            SocialMediaPlatform.REDDIT: ["Chrome", "Firefox"]
        }
        
        preferred_browsers = platform_preferences.get(platform, ["Chrome"])
        
        # Filter user agents by preferred browsers
        filtered_agents = []
        for agent in self.user_agents:
            for browser in preferred_browsers:
                if browser.lower() in agent.lower():
                    filtered_agents.append(agent)
                    break
        
        return random.choice(filtered_agents) if filtered_agents else random.choice(self.user_agents)
    
    def create_session(self, platform: SocialMediaPlatform) -> ScrapingSession:
        """Create a new scraping session with anti-detection measures."""
        session_id = hashlib.md5(f"{platform.value}_{time.time()}_{random.randint(1, 1000)}".encode()).hexdigest()
        
        session = ScrapingSession(
            session_id=session_id,
            platform=platform,
            user_agent=self.get_user_agent(platform),
            proxy=self._get_proxy(platform) if self._should_use_proxy(platform) else None
        )
        
        self.sessions[session_id] = session
        
        # Clean old sessions (older than 30 minutes)
        current_time = time.time()
        expired_sessions = [
            sid for sid, sess in self.sessions.items()
            if current_time - sess.created_at > 1800
        ]
        for sid in expired_sessions:
            del self.sessions[sid]
        
        return session
    
    def _should_use_proxy(self, platform: SocialMediaPlatform) -> bool:
        """Determine if proxy should be used for platform."""
        if self.settings.proxy_strategy.value == "disabled":
            return False
        elif self.settings.proxy_strategy.value == "required":
            return True
        elif self.settings.proxy_strategy.value == "platform_specific":
            # TikTok and some regions benefit from proxies
            return platform in [SocialMediaPlatform.TIKTOK]
        return False
    
    def _get_proxy(self, platform: SocialMediaPlatform) -> Optional[str]:
        """Get proxy for platform if available."""
        # This would integrate with proxy providers
        # For now, return None
        return None
    
    async def apply_request_delay(self, platform: SocialMediaPlatform) -> None:
        """Apply intelligent request delay."""
        min_delay = self.settings.request_delay_min
        max_delay = self.settings.request_delay_max
        
        # Adjust delays based on platform
        platform_multipliers = {
            SocialMediaPlatform.INSTAGRAM: 2.0,
            SocialMediaPlatform.TIKTOK: 3.0,
            SocialMediaPlatform.FACEBOOK: 2.5,
            SocialMediaPlatform.TWITTER: 1.0,
            SocialMediaPlatform.REDDIT: 1.0
        }
        
        multiplier = platform_multipliers.get(platform, 1.0)
        delay = random.uniform(min_delay * multiplier, max_delay * multiplier)
        
        # Track last request time for this platform
        last_request = self.request_delays.get(platform, 0)
        time_since_last = time.time() - last_request
        
        if time_since_last < delay:
            additional_delay = delay - time_since_last
            await asyncio.sleep(additional_delay)
        
        self.request_delays[platform] = time.time()


class SocialMediaScraper:
    """Secure web scraper for social media platforms with SSRF protection."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        self.config = config
        self.settings = settings
        self.platform = config.platform
        self.anti_detection = AntiDetectionManager(settings)
        self.ssrf_protection = SSRFProtection()
        self.rate_limiter = RateLimiter(
            max_requests=config.requests_per_minute,
            time_window=60
        )
        self.logger = logger.bind(platform=self.platform.value)
        
        # Security: Request size limits
        self.max_response_size = 10 * 1024 * 1024  # 10MB
        self.max_content_length = 50 * 1024 * 1024  # 50MB
        
    async def scrape_profile(self, username: str, use_selenium: bool = None) -> Optional[ProfileData]:
        """Scrape profile information from social media platform."""
        if use_selenium is None:
            use_selenium = self.config.javascript_rendering_required
        
        session = self.anti_detection.create_session(self.platform)
        
        try:
            if use_selenium:
                return await self._scrape_with_selenium(username, session)
            else:
                return await self._scrape_with_requests(username, session)
        except Exception as e:
            self.logger.error("Profile scraping failed", username=username, error=str(e))
            return None
    
    async def _scrape_with_requests(self, username: str, session: ScrapingSession) -> Optional[ProfileData]:
        """Securely scrape using aiohttp requests with SSRF protection."""
        await self.rate_limiter.acquire()
        await self.anti_detection.apply_request_delay(self.platform)
        
        profile_url = self._build_profile_url(username)
        
        # Security: Validate URL before making request
        is_safe, safety_message = self.ssrf_protection.is_safe_url(profile_url)
        if not is_safe:
            self.logger.warning(
                "Blocked unsafe URL",
                username=username,
                url=profile_url,
                reason=safety_message
            )
            return None
        
        headers = {
            "User-Agent": session.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            **self.config.required_headers
        }
        
        # Security: Strict timeouts and size limits
        timeout = ClientTimeout(total=30, connect=10, sock_read=10)
        
        try:
            connector = aiohttp.TCPConnector(
                limit=10,  # Connection pool limit
                limit_per_host=5,  # Per-host connection limit
                enable_cleanup_closed=True,
                force_close=True  # Close connections after use
            )
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                max_redirects=self.ssrf_protection.max_redirects
            ) as http_session:
                async with http_session.get(
                    profile_url,
                    headers=headers,
                    proxy=session.proxy,
                    cookies=session.cookies,
                    max_redirects=self.ssrf_protection.max_redirects,
                    allow_redirects=True
                ) as response:
                    # Security: Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_content_length:
                        self.logger.warning(
                            "Response too large",
                            username=username,
                            content_length=content_length
                        )
                        return None
                    
                    # Security: Validate redirects
                    if response.history:
                        for redirect in response.history:
                            redirect_url = str(redirect.url)
                            if not self.ssrf_protection.validate_response_redirect(
                                profile_url, redirect_url
                            ):
                                return None
                    
                    if response.status == 200:
                        # Security: Read response with size limit
                        content_size = 0
                        html_chunks = []
                        
                        async for chunk in response.content.iter_chunked(8192):
                            content_size += len(chunk)
                            if content_size > self.max_response_size:
                                self.logger.warning(
                                    "Response size exceeded limit",
                                    username=username,
                                    size=content_size
                                )
                                return None
                            html_chunks.append(chunk)
                        
                        html = b''.join(html_chunks).decode('utf-8', errors='ignore')
                        return self._extract_profile_data(html, username, profile_url)
                        
                    elif response.status == 404:
                        self.logger.info("Profile not found", username=username, platform=self.platform.value)
                        return None
                    else:
                        self.logger.warning(
                            "Unexpected response status",
                            username=username,
                            status=response.status
                        )
                        return None
                        
        except asyncio.TimeoutError:
            self.logger.warning("Request timeout", username=username)
            return None
        except aiohttp.ClientError as e:
            self.logger.error("HTTP client error", username=username, error=str(e))
            return None
        except Exception as e:
            self.logger.error("HTTP request failed", username=username, error=str(e))
            return None
    
    async def _scrape_with_selenium(self, username: str, session: ScrapingSession) -> Optional[ProfileData]:
        """Scrape using Selenium WebDriver."""
        await self.rate_limiter.acquire()
        await self.anti_detection.apply_request_delay(self.platform)
        
        profile_url = self._build_profile_url(username)
        
        # Run Selenium in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._selenium_scrape_sync,
            profile_url,
            username,
            session
        )
    
    def _selenium_scrape_sync(self, profile_url: str, username: str, session: ScrapingSession) -> Optional[ProfileData]:
        """Synchronous Selenium scraping function."""
        if not SELENIUM_AVAILABLE:
            self.logger.warning("Selenium not available for local testing", username=username)
            return None
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={session.user_agent}')
        
        if session.proxy:
            chrome_options.add_argument(f'--proxy-server={session.proxy}')
        
        # Add stealth options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(profile_url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for JavaScript-heavy pages
            time.sleep(3)
            
            html = driver.page_source
            return self._extract_profile_data(html, username, profile_url)
            
        except Exception as e:
            # Handle both TimeoutException and WebDriverException if selenium is available
            if SELENIUM_AVAILABLE and 'TimeoutException' in str(type(e)):
                self.logger.warning("Selenium timeout", username=username)
            elif SELENIUM_AVAILABLE and 'WebDriverException' in str(type(e)):
                self.logger.error("Selenium WebDriver error", username=username, error=str(e))
            else:
                self.logger.error("Selenium scraping failed", username=username, error=str(e))
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _build_profile_url(self, username: str) -> str:
        """Build and validate profile URL for the platform."""
        # Security: Sanitize username input
        sanitized_username = self._sanitize_username(username)
        if not sanitized_username:
            raise ValueError("Invalid username provided")
        
        url_patterns = {
            SocialMediaPlatform.INSTAGRAM: f"{self.config.base_url}/{sanitized_username}/",
            SocialMediaPlatform.TWITTER: f"{self.config.base_url}/{sanitized_username}",
            SocialMediaPlatform.FACEBOOK: f"{self.config.base_url}/{sanitized_username}",
            SocialMediaPlatform.TIKTOK: f"{self.config.base_url}/@{sanitized_username}",
            SocialMediaPlatform.REDDIT: f"{self.config.base_url}/user/{sanitized_username}",
        }
        
        return url_patterns.get(self.platform, f"{self.config.base_url}/{sanitized_username}")
    
    def _sanitize_username(self, username: str) -> Optional[str]:
        """Sanitize username to prevent injection attacks."""
        if not username or not isinstance(username, str):
            return None
        
        # Remove dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', username)
        
        # Check length limits
        if len(sanitized) < 1 or len(sanitized) > 50:
            return None
        
        # Check for suspicious patterns
        suspicious_patterns = [r'\.\.', r'__', r'--', r'admin', r'root', r'test']
        for pattern in suspicious_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                self.logger.warning("Suspicious username pattern detected", username=username)
                return None
        
        return sanitized
    
    def _extract_profile_data(self, html: str, username: str, url: str) -> Optional[ProfileData]:
        """Extract profile data from HTML using CSS selectors."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Get selectors for this platform
            selectors = self.config.profile_selectors
            
            if not selectors:
                self.logger.warning("No selectors configured for platform", platform=self.platform.value)
                return None
            
            # Extract data using selectors
            data = {}
            
            # Basic profile info
            if 'username' in selectors:
                element = soup.select_one(selectors['username'])
                data['username'] = element.get_text().strip() if element else username
            else:
                data['username'] = username
                
            if 'display_name' in selectors:
                element = soup.select_one(selectors['display_name'])
                data['display_name'] = element.get_text().strip() if element else None
                
            if 'bio' in selectors:
                element = soup.select_one(selectors['bio'])
                data['bio'] = element.get_text().strip() if element else None
            
            # Counts (followers, following, posts)
            if 'follower_count' in selectors:
                element = soup.select_one(selectors['follower_count'])
                data['follower_count'] = self._extract_count(element) if element else None
                
            if 'following_count' in selectors:
                element = soup.select_one(selectors['following_count'])
                data['following_count'] = self._extract_count(element) if element else None
                
            if 'post_count' in selectors:
                element = soup.select_one(selectors['post_count'])
                data['post_count'] = self._extract_count(element) if element else None
            
            # Profile images
            if 'profile_image' in selectors:
                element = soup.select_one(selectors['profile_image'])
                data['profile_image_url'] = element.get('src') if element else None
                
            if 'cover_image' in selectors:
                element = soup.select_one(selectors['cover_image'])
                data['cover_image_url'] = element.get('src') if element else None
            
            # Platform-specific data extraction
            if self.platform == SocialMediaPlatform.INSTAGRAM:
                data.update(self._extract_instagram_data(soup))
            elif self.platform == SocialMediaPlatform.TWITTER:
                data.update(self._extract_twitter_data(soup))
            elif self.platform == SocialMediaPlatform.TIKTOK:
                data.update(self._extract_tiktok_data(soup))
            
            return ProfileData(
                username=data.get('username', username),
                display_name=data.get('display_name'),
                bio=data.get('bio'),
                follower_count=data.get('follower_count'),
                following_count=data.get('following_count'),
                post_count=data.get('post_count'),
                profile_image_url=data.get('profile_image_url'),
                cover_image_url=data.get('cover_image_url'),
                is_verified=data.get('is_verified', False),
                is_private=data.get('is_private', False),
                url=url,
                metadata=data
            )
            
        except Exception as e:
            self.logger.error("Failed to extract profile data", username=username, error=str(e))
            return None
    
    def _extract_count(self, element) -> Optional[int]:
        """Extract numeric count from element text."""
        if not element:
            return None
            
        text = element.get_text().strip()
        if not text:
            return None
        
        # Remove commas and convert suffixes
        text = text.replace(',', '').lower()
        
        multipliers = {
            'k': 1000,
            'm': 1000000,
            'b': 1000000000
        }
        
        for suffix, multiplier in multipliers.items():
            if text.endswith(suffix):
                try:
                    number = float(text[:-1])
                    return int(number * multiplier)
                except ValueError:
                    continue
        
        # Try to extract just the number
        try:
            return int(''.join(c for c in text if c.isdigit()))
        except ValueError:
            return None
    
    def _extract_instagram_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Instagram-specific data."""
        data = {}
        
        # Check for verification badge
        verified_element = soup.select_one('[aria-label*="Verified"]')
        data['is_verified'] = verified_element is not None
        
        # Check for private account
        private_element = soup.select_one('[data-testid="private-account-icon"]')
        data['is_private'] = private_element is not None
        
        # Try to extract from JSON-LD scripts
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict) and '@type' in json_data:
                    if json_data['@type'] == 'Person':
                        data['display_name'] = json_data.get('name')
                        data['bio'] = json_data.get('description')
                        break
            except (json.JSONDecodeError, KeyError):
                continue
        
        return data
    
    def _extract_twitter_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Twitter-specific data."""
        data = {}
        
        # Check for verification badge
        verified_element = soup.select_one('[data-testid="icon-verified"]')
        data['is_verified'] = verified_element is not None
        
        # Check for protected tweets
        protected_element = soup.select_one('[data-testid="icon-lock"]')
        data['is_private'] = protected_element is not None
        
        return data
    
    def _extract_tiktok_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract TikTok-specific data."""
        data = {}
        
        # TikTok verification
        verified_element = soup.select_one('[data-e2e="user-verified-icon"]')
        data['is_verified'] = verified_element is not None
        
        # TikTok follower counts often in different selectors
        likes_element = soup.select_one('[data-e2e="likes-count"]')
        if likes_element:
            data['likes_count'] = self._extract_count(likes_element)
        
        return data
    
    async def search_profiles(self, query: str, limit: int = 20) -> List[ProfileData]:
        """Search for profiles using web scraping."""
        session = self.anti_detection.create_session(self.platform)
        
        search_url = self._build_search_url(query)
        if not search_url:
            self.logger.warning("Search not supported for platform", platform=self.platform.value)
            return []
        
        await self.rate_limiter.acquire()
        await self.anti_detection.apply_request_delay(self.platform)
        
        # This would implement search functionality
        # For brevity, returning empty list here
        # In a real implementation, this would scrape search results
        self.logger.info("Search functionality not fully implemented", query=query, platform=self.platform.value)
        return []
    
    def _build_search_url(self, query: str) -> Optional[str]:
        """Build search URL for the platform."""
        search_patterns = {
            SocialMediaPlatform.TWITTER: f"{self.config.base_url}/search?q={query}&src=typed_query&f=user",
            SocialMediaPlatform.REDDIT: f"{self.config.base_url}/search?q={query}&type=user",
            # Instagram and TikTok don't have direct search URLs
        }
        
        return search_patterns.get(self.platform)


# Factory function for creating scrapers
def create_scraper(platform: SocialMediaPlatform, config: PlatformConfig, settings: SocialMediaSettings) -> SocialMediaScraper:
    """Factory function to create appropriate scraper for platform."""
    return SocialMediaScraper(config, settings)