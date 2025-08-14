"""
Web Crawler Service for Content Detection
Implements the automated content scanning engine as per PRD requirements
"""
import asyncio
import aiohttp
import hashlib
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass
from enum import Enum
import json

from app.core.config import settings
from app.db.session import get_db
from app.services.ai.content_matcher import ContentMatcher
from app.services.scanning.search_engines import SearchEngineScanner

logger = logging.getLogger(__name__)


class CrawlStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class CrawlResult:
    """Result from a crawl operation"""
    url: str
    status: CrawlStatus
    content_type: str
    content_hash: str
    images: List[str]
    videos: List[str]
    text_content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None


class WebCrawler:
    """
    Core web crawler for automated content detection
    Implements PRD requirement: "continuous or daily scans of the internet"
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.content_matcher = ContentMatcher()
        self.search_scanner = SearchEngineScanner()
        self.rate_limits: Dict[str, datetime] = {}
        self.crawl_queue: asyncio.Queue = asyncio.Queue()
        self.visited_urls: Set[str] = set()
        
        # Known piracy sites - would be loaded from database in production
        self.priority_sites = [
            # Adult content leak sites
            "leakfanatic.com",
            "thotsbay.com", 
            "forum.sexy-egirls.com",
            "coomer.party",
            "kemono.party",
            
            # General file sharing
            "mega.nz",
            "anonfiles.com",
            "gofile.io",
            "pixeldrain.com",
            
            # Image boards and forums
            "reddit.com/r/",  # Various NSFW subreddits
            "4chan.org",
            "8kun.top",
            
            # Video platforms
            "xvideos.com",
            "xnxx.com",
            "pornhub.com",
            "spankbang.com",
            
            # Social media platforms
            "twitter.com",
            "instagram.com",
            "tiktok.com",
            "facebook.com"
        ]
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def scan_for_profile(
        self, 
        profile_data: Dict[str, Any],
        deep_scan: bool = False
    ) -> List[CrawlResult]:
        """
        Main entry point for scanning content for a specific profile
        PRD: "performs continuous or daily scans...looking for matches to the creator's content"
        """
        results = []
        
        # Step 1: Search engine discovery
        logger.info(f"Starting scan for profile: {profile_data.get('username')}")
        search_urls = await self._search_engine_discovery(profile_data)
        
        # Step 2: Known site scanning  
        priority_urls = self._generate_priority_urls(profile_data)
        
        # Step 3: Combine and deduplicate URLs
        all_urls = list(set(search_urls + priority_urls))
        logger.info(f"Found {len(all_urls)} URLs to scan")
        
        # Step 4: Crawl URLs with rate limiting
        crawl_tasks = []
        for url in all_urls[:100]:  # Limit for MVP
            if not self._is_rate_limited(url):
                crawl_tasks.append(self._crawl_url(url, profile_data))
                
        # Step 5: Process results in batches
        if crawl_tasks:
            batch_results = await asyncio.gather(*crawl_tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, CrawlResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Crawl error: {result}")
                    
        # Step 6: Deep scan if requested (follow links)
        if deep_scan and results:
            deep_results = await self._deep_scan(results, profile_data)
            results.extend(deep_results)
            
        logger.info(f"Scan completed with {len(results)} results")
        return results
        
    async def _search_engine_discovery(
        self, 
        profile_data: Dict[str, Any]
    ) -> List[str]:
        """
        Use search engines to discover potential infringement URLs
        PRD: "leveraging search engines for initial discovery"
        """
        search_terms = self._generate_search_terms(profile_data)
        urls = []
        
        for term in search_terms:
            try:
                # Google search
                google_results = await self.search_scanner.search_google(term)
                urls.extend(google_results)
                
                # Bing search  
                bing_results = await self.search_scanner.search_bing(term)
                urls.extend(bing_results)
                
                # Google Images
                if profile_data.get('scan_images', True):
                    image_results = await self.search_scanner.search_google_images(term)
                    urls.extend(image_results)
                    
            except Exception as e:
                logger.error(f"Search engine error for term '{term}': {e}")
                
        return urls
        
    def _generate_search_terms(self, profile_data: Dict[str, Any]) -> List[str]:
        """
        Generate intelligent search terms for finding leaked content
        PRD: "keyword matching (e.g. the creator's username, content titles, watermarks)"
        """
        terms = []
        username = profile_data.get('username', '')
        
        if username:
            # Basic username searches
            terms.append(f'"{username}"')
            terms.append(f'"{username}" leaked')
            terms.append(f'"{username}" onlyfans')
            terms.append(f'"{username}" patreon')
            terms.append(f'"{username}" mega')
            
            # Common misspellings and variations
            terms.append(f'"{username.replace("_", " ")}"')
            terms.append(f'"{username.replace(".", " ")}"')
            
            # Platform specific
            if profile_data.get('platform') == 'onlyfans':
                terms.append(f'"onlyfans.com/{username}"')
                terms.append(f'OF {username}')
                
        # Additional keywords from profile
        keywords = profile_data.get('keywords', [])
        for keyword in keywords:
            terms.append(f'"{keyword}"')
            
        return terms[:10]  # Limit for efficiency
        
    def _generate_priority_urls(self, profile_data: Dict[str, Any]) -> List[str]:
        """
        Generate URLs for known leak sites to check directly
        PRD: "Custom crawler scripts will routinely visit known piracy websites"
        """
        urls = []
        username = profile_data.get('username', '')
        
        if not username:
            return urls
            
        # Generate URLs for each priority site
        for site in self.priority_sites:
            if 'reddit.com' in site:
                # Reddit specific URLs
                urls.extend([
                    f'https://www.reddit.com/search/?q={username}',
                    f'https://www.reddit.com/r/OnlyFans101/search/?q={username}',
                    f'https://www.reddit.com/user/{username}'
                ])
            elif 'mega.nz' in site:
                # Mega links often shared on forums
                urls.append(f'https://www.google.com/search?q=site:mega.nz+{username}')
            elif any(x in site for x in ['coomer.party', 'kemono.party']):
                # Direct profile checks on leak sites
                urls.append(f'https://{site}/onlyfans/user/{username}')
                urls.append(f'https://{site}/patreon/user/{username}')
            else:
                # Generic search on the site
                urls.append(f'https://{site}/search?q={username}')
                
        return urls
        
    async def _crawl_url(
        self, 
        url: str, 
        profile_data: Dict[str, Any]
    ) -> CrawlResult:
        """
        Crawl a single URL and extract content
        """
        try:
            # Check if already visited
            if url in self.visited_urls:
                return None
            self.visited_urls.add(url)
            
            # Make request with timeout
            async with self.session.get(url) as response:
                if response.status != 200:
                    return CrawlResult(
                        url=url,
                        status=CrawlStatus.FAILED,
                        content_type="",
                        content_hash="",
                        images=[],
                        videos=[],
                        text_content="",
                        metadata={"status_code": response.status},
                        timestamp=datetime.utcnow(),
                        error=f"HTTP {response.status}"
                    )
                    
                content_type = response.headers.get('Content-Type', '')
                content = await response.read()
                
                # Generate content hash for deduplication
                content_hash = hashlib.sha256(content).hexdigest()
                
                # Parse based on content type
                if 'text/html' in content_type:
                    return await self._parse_html_content(
                        url, content, content_hash, profile_data
                    )
                elif 'image' in content_type:
                    return await self._handle_image_content(
                        url, content, content_hash, profile_data
                    )
                elif 'video' in content_type:
                    return await self._handle_video_content(
                        url, content, content_hash, profile_data
                    )
                else:
                    return CrawlResult(
                        url=url,
                        status=CrawlStatus.COMPLETED,
                        content_type=content_type,
                        content_hash=content_hash,
                        images=[],
                        videos=[],
                        text_content="",
                        metadata={"size": len(content)},
                        timestamp=datetime.utcnow()
                    )
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout crawling {url}")
            return CrawlResult(
                url=url,
                status=CrawlStatus.FAILED,
                content_type="",
                content_hash="",
                images=[],
                videos=[],
                text_content="",
                metadata={},
                timestamp=datetime.utcnow(),
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawlResult(
                url=url,
                status=CrawlStatus.FAILED,
                content_type="",
                content_hash="",
                images=[],
                videos=[],
                text_content="",
                metadata={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
            
    async def _parse_html_content(
        self,
        url: str,
        content: bytes,
        content_hash: str,
        profile_data: Dict[str, Any]
    ) -> CrawlResult:
        """Parse HTML content and extract relevant data"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract images
            images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    absolute_url = urljoin(url, src)
                    images.append(absolute_url)
                    
            # Extract videos
            videos = []
            for video in soup.find_all(['video', 'iframe']):
                src = video.get('src')
                if src:
                    absolute_url = urljoin(url, src)
                    videos.append(absolute_url)
                    
            # Extract text content
            text_content = soup.get_text()
            
            # Check for username mentions
            username = profile_data.get('username', '')
            username_found = username.lower() in text_content.lower() if username else False
            
            # Extract metadata
            metadata = {
                "title": soup.title.string if soup.title else "",
                "description": "",
                "username_found": username_found,
                "image_count": len(images),
                "video_count": len(videos)
            }
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata["description"] = meta_desc.get('content', '')
                
            return CrawlResult(
                url=url,
                status=CrawlStatus.COMPLETED,
                content_type="text/html",
                content_hash=content_hash,
                images=images[:100],  # Limit for performance
                videos=videos[:50],
                text_content=text_content[:10000],  # Limit text size
                metadata=metadata,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error parsing HTML from {url}: {e}")
            return CrawlResult(
                url=url,
                status=CrawlStatus.FAILED,
                content_type="text/html",
                content_hash=content_hash,
                images=[],
                videos=[],
                text_content="",
                metadata={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
            
    async def _handle_image_content(
        self,
        url: str,
        content: bytes,
        content_hash: str,
        profile_data: Dict[str, Any]
    ) -> CrawlResult:
        """Handle direct image URLs"""
        return CrawlResult(
            url=url,
            status=CrawlStatus.COMPLETED,
            content_type="image",
            content_hash=content_hash,
            images=[url],
            videos=[],
            text_content="",
            metadata={
                "size": len(content),
                "direct_image": True
            },
            timestamp=datetime.utcnow()
        )
        
    async def _handle_video_content(
        self,
        url: str,
        content: bytes,
        content_hash: str,
        profile_data: Dict[str, Any]
    ) -> CrawlResult:
        """Handle direct video URLs"""
        return CrawlResult(
            url=url,
            status=CrawlStatus.COMPLETED,
            content_type="video",
            content_hash=content_hash,
            images=[],
            videos=[url],
            text_content="",
            metadata={
                "size": len(content),
                "direct_video": True
            },
            timestamp=datetime.utcnow()
        )
        
    async def _deep_scan(
        self,
        initial_results: List[CrawlResult],
        profile_data: Dict[str, Any]
    ) -> List[CrawlResult]:
        """
        Perform deep scanning by following links from initial results
        """
        deep_results = []
        
        for result in initial_results:
            if result.status == CrawlStatus.COMPLETED:
                # Extract links from HTML content
                if 'html' in result.content_type:
                    # Would parse and follow relevant links
                    pass
                    
        return deep_results
        
    def _is_rate_limited(self, url: str) -> bool:
        """Check if URL domain is rate limited"""
        domain = urlparse(url).netloc
        if domain in self.rate_limits:
            if datetime.utcnow() < self.rate_limits[domain]:
                return True
        return False
        
    def _set_rate_limit(self, url: str, seconds: int = 60):
        """Set rate limit for a domain"""
        domain = urlparse(url).netloc
        self.rate_limits[domain] = datetime.utcnow() + timedelta(seconds=seconds)