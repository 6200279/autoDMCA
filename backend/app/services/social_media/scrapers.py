"""
Web scraping engine for social media platforms with anti-detection measures.
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import hashlib
import json

import aiohttp
import structlog
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from fake_useragent import UserAgent

from app.db.models.social_media import SocialMediaPlatform
from .config import PlatformConfig, SocialMediaSettings
from .api_clients import ProfileData
from ..auth.rate_limiter import RateLimiter


logger = structlog.get_logger(__name__)


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
    """Manages anti-detection measures for web scraping."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.ua = UserAgent()
        self.user_agents = self._load_user_agents()
        self.proxies = []
        self.sessions: Dict[str, ScrapingSession] = {}
        self.request_delays: Dict[SocialMediaPlatform, float] = {}
        
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
    """Web scraper for social media platforms."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        self.config = config
        self.settings = settings
        self.platform = config.platform
        self.anti_detection = AntiDetectionManager(settings)
        self.rate_limiter = RateLimiter(
            max_requests=config.requests_per_minute,
            time_window=60
        )
        self.logger = logger.bind(platform=self.platform.value)
        
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
        """Scrape using aiohttp requests."""
        await self.rate_limiter.acquire()
        await self.anti_detection.apply_request_delay(self.platform)
        
        profile_url = self._build_profile_url(username)
        
        headers = {
            "User-Agent": session.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            **self.config.required_headers
        }
        
        timeout = ClientTimeout(total=30, connect=10)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as http_session:
                async with http_session.get(
                    profile_url,
                    headers=headers,
                    proxy=session.proxy,
                    cookies=session.cookies
                ) as response:
                    if response.status == 200:
                        html = await response.text()
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
            
        except TimeoutException:
            self.logger.warning("Selenium timeout", username=username)
            return None
        except WebDriverException as e:
            self.logger.error("Selenium WebDriver error", username=username, error=str(e))
            return None
        except Exception as e:
            self.logger.error("Selenium scraping failed", username=username, error=str(e))
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _build_profile_url(self, username: str) -> str:
        """Build profile URL for the platform."""
        url_patterns = {
            SocialMediaPlatform.INSTAGRAM: f"{self.config.base_url}/{username}/",
            SocialMediaPlatform.TWITTER: f"{self.config.base_url}/{username}",
            SocialMediaPlatform.FACEBOOK: f"{self.config.base_url}/{username}",
            SocialMediaPlatform.TIKTOK: f"{self.config.base_url}/@{username}",
            SocialMediaPlatform.REDDIT: f"{self.config.base_url}/user/{username}",
        }
        
        return url_patterns.get(self.platform, f"{self.config.base_url}/{username}")
    
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