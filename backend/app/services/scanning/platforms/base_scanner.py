"""
Base Scanner Class
Provides common functionality for all platform scanners
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import aiohttp
import logging
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Standard scan result format"""
    url: str
    platform: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_urls: List[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    view_count: Optional[int] = None
    engagement_stats: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    search_query: Optional[str] = None
    region: Optional[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.media_urls is None:
            self.media_urls = []
        if self.metadata is None:
            self.metadata = {}


class BaseScanner(ABC):
    """
    Base class for all platform scanners
    Provides common functionality like rate limiting, proxy support, etc.
    """
    
    def __init__(
        self,
        region: Optional[Dict[str, Any]] = None,
        rate_limit: int = 30,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.region = region
        self.rate_limit = rate_limit  # requests per minute
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Rate limiting
        self.request_times: List[float] = []
        self.last_request_time = 0
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session is initialized"""
        if not self.session:
            async with self._session_lock:
                if not self.session:
                    # Configure session with proxy if needed
                    connector_kwargs = {}
                    headers = {
                        'User-Agent': self._get_user_agent()
                    }
                    
                    # Add proxy configuration if region has one
                    if self.region and self.region.get('proxy_config'):
                        proxy_config = self.region['proxy_config']
                        connector_kwargs['connector'] = aiohttp.TCPConnector(
                            limit=100,
                            limit_per_host=10
                        )
                        # Proxy would be configured here
                    
                    timeout = aiohttp.ClientTimeout(total=self.timeout)
                    
                    self.session = aiohttp.ClientSession(
                        headers=headers,
                        timeout=timeout,
                        **connector_kwargs
                    )
    
    def _get_user_agent(self) -> str:
        """Get user agent string"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        import random
        return random.choice(agents)
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        
        # Clean old request times (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.rate_limit:
            wait_time = 60 - (now - self.request_times[0])
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
        self.last_request_time = now
    
    async def _make_request(
        self,
        url: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[aiohttp.ClientResponse]:
        """Make HTTP request with rate limiting and retries"""
        await self._ensure_session()
        await self._rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                request_headers = headers or {}
                
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=request_headers,
                    json=data if data else None
                ) as response:
                    if response.status == 200:
                        return response
                    elif response.status == 429:  # Too Many Requests
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited by {url}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status in [403, 404]:
                        logger.warning(f"Request failed with status {response.status} for {url}")
                        return None
                    else:
                        logger.warning(f"Unexpected status {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for request {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Request error for {url}: {e}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def _fetch_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from URL"""
        response = await self._make_request(url, params=params, headers=headers)
        if response:
            try:
                return await response.json()
            except Exception as e:
                logger.error(f"JSON parse error for {url}: {e}")
        return None
    
    async def _fetch_html(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Fetch HTML content from URL"""
        response = await self._make_request(url, params=params, headers=headers)
        if response:
            try:
                return await response.text()
            except Exception as e:
                logger.error(f"HTML parse error for {url}: {e}")
        return None
    
    def _extract_media_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract image and video URLs from HTML"""
        media_urls = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find images
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    full_url = urljoin(base_url, src)
                    if self._is_valid_media_url(full_url):
                        media_urls.append(full_url)
            
            # Find videos
            for video in soup.find_all('video'):
                src = video.get('src')
                if src:
                    full_url = urljoin(base_url, src)
                    if self._is_valid_media_url(full_url):
                        media_urls.append(full_url)
                
                # Check source tags within video
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src:
                        full_url = urljoin(base_url, src)
                        if self._is_valid_media_url(full_url):
                            media_urls.append(full_url)
            
        except ImportError:
            logger.warning("BeautifulSoup not available for HTML parsing")
        except Exception as e:
            logger.error(f"Error extracting media from HTML: {e}")
        
        return list(set(media_urls))  # Remove duplicates
    
    def _is_valid_media_url(self, url: str) -> bool:
        """Check if URL is a valid media URL"""
        try:
            parsed = urlparse(url)
            
            # Must have valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check file extension
            path_lower = parsed.path.lower()
            media_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
                '.mp4', '.avi', '.mov', '.webm', '.mkv', '.m4v'
            ]
            
            return any(path_lower.endswith(ext) for ext in media_extensions)
            
        except Exception:
            return False
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove common HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#x27;': "'",
            '&#x2F;': '/'
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        return text.strip()
    
    def _calculate_relevance_score(
        self,
        result: ScanResult,
        search_query: str,
        profile_keywords: List[str]
    ) -> float:
        """Calculate relevance score for scan result"""
        score = 0.0
        
        search_terms = search_query.lower().split()
        content_text = f"{result.title} {result.description} {result.author}".lower()
        
        # Score based on search term matches
        for term in search_terms:
            if term in content_text:
                score += 0.3
        
        # Score based on profile keyword matches
        for keyword in profile_keywords:
            if keyword.lower() in content_text:
                score += 0.5
        
        # Boost score for exact username matches
        for keyword in profile_keywords:
            if len(keyword) > 3 and keyword.lower() in content_text.split():
                score += 1.0
        
        # Normalize score to 0-1 range
        return min(score, 1.0)
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search platform for query
        Must be implemented by each platform scanner
        """
        pass
    
    @abstractmethod
    async def get_platform_name(self) -> str:
        """Get platform name"""
        pass
    
    async def health_check(self) -> bool:
        """Check if platform scanner is healthy"""
        try:
            # Perform a simple test search
            results = await self.search("test", limit=1)
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False