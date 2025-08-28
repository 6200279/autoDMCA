"""
Comprehensive Piracy Sites Database and Specialized Scrapers
Implements PRD requirement for "curated list of leak sites, forums, and file-sharing boards"

PRD Requirements:
- "Curated list of leak sites, forums, and file-sharing boards relevant to our users"
- "Platform-specific scrapers that understand the unique structure of each site"
- "Specialized scrapers for each platform type (OnlyFans leaks, Instagram content, etc.)"
- "Monitor relevant leak sites, forums, and file-sharing boards"
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import hashlib
import json

from app.core.config import settings
from app.services.ai.content_matcher import ContentMatcher
from app.services.scanning.web_crawler import WebCrawler

logger = logging.getLogger(__name__)


class SiteType(str, Enum):
    """Types of piracy sites we monitor"""
    ONLYFANS_LEAK = "onlyfans_leak"
    INSTAGRAM_LEAK = "instagram_leak"
    TIKTOK_LEAK = "tiktok_leak"
    TWITTER_LEAK = "twitter_leak"
    FILE_SHARING = "file_sharing"
    FORUM = "forum"
    TELEGRAM_LEAK = "telegram_leak"
    DISCORD_LEAK = "discord_leak"
    REDDIT_LEAK = "reddit_leak"
    IMAGE_BOARD = "image_board"
    TUBE_SITE = "tube_site"
    TORRENT = "torrent"


class SiteStatus(str, Enum):
    """Site monitoring status"""
    ACTIVE = "active"           # Actively monitored
    INACTIVE = "inactive"       # Temporarily down or not monitored
    BLOCKED = "blocked"         # Site blocked our access
    DISCONTINUED = "discontinued"  # Site no longer exists


@dataclass
class ScrapePattern:
    """Configuration for scraping specific content types"""
    content_selector: str       # CSS selector for main content
    title_selector: str         # CSS selector for post titles
    image_selector: str         # CSS selector for images
    video_selector: str         # CSS selector for videos
    author_selector: str        # CSS selector for post author
    date_selector: str          # CSS selector for post date
    link_selector: str          # CSS selector for content links
    pagination_selector: str    # CSS selector for next page


@dataclass 
class PiracySite:
    """Configuration for a piracy site"""
    id: str
    name: str
    base_url: str
    site_type: SiteType
    status: SiteStatus
    scrape_patterns: ScrapePattern
    rate_limit_delay: float     # Seconds between requests
    headers: Dict[str, str]     # Custom headers for requests
    requires_js: bool           # Whether site requires JavaScript execution
    keywords: List[str]         # Keywords to search for
    blocked_content: List[str]  # Content patterns to avoid
    priority: int               # 1=high, 5=low priority
    last_crawled: Optional[datetime] = None
    crawl_frequency: int = 24   # Hours between crawls


class PiracySiteDatabase:
    """
    Comprehensive database of piracy sites with specialized scrapers
    
    Implements PRD requirements:
    - Curated list of leak sites and forums
    - Platform-specific scrapers for each site type
    - Intelligent content detection and matching
    """
    
    def __init__(self):
        self.sites: Dict[str, PiracySite] = {}
        self.content_matcher = ContentMatcher()
        self.web_crawler = WebCrawler()
        self._load_site_database()
        
    def _load_site_database(self) -> None:
        """Load comprehensive piracy sites database"""
        
        # OnlyFans leak sites
        self.sites["leaked-models"] = PiracySite(
            id="leaked-models",
            name="Leaked Models",
            base_url="https://leaked-models.com",
            site_type=SiteType.ONLYFANS_LEAK,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".post-content",
                title_selector=".post-title a",
                image_selector=".post-content img",
                video_selector=".post-content video",
                author_selector=".post-author",
                date_selector=".post-date",
                link_selector=".download-links a",
                pagination_selector=".pagination .next"
            ),
            rate_limit_delay=2.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            },
            requires_js=False,
            keywords=["onlyfans", "leaked", "premium", "exclusive"],
            blocked_content=["advertisement", "popup", "spam"],
            priority=1
        )
        
        self.sites["thothub"] = PiracySite(
            id="thothub",
            name="ThotHub",
            base_url="https://thothub.tv",
            site_type=SiteType.ONLYFANS_LEAK,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".thread-content",
                title_selector=".thread-title",
                image_selector=".attachment-image img",
                video_selector=".attachment-video video",
                author_selector=".author-name",
                date_selector=".post-timestamp",
                link_selector=".download-button",
                pagination_selector=".pageNav-jump--next"
            ),
            rate_limit_delay=1.5,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=True,
            keywords=["onlyfans", "thot", "leaked", "premium"],
            blocked_content=["advertisement"],
            priority=1
        )
        
        # Instagram leak sites
        self.sites["instagram-leaked"] = PiracySite(
            id="instagram-leaked",
            name="Instagram Leaked",
            base_url="https://instagram-leaked.com",
            site_type=SiteType.INSTAGRAM_LEAK,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".leak-post",
                title_selector=".leak-title",
                image_selector=".leak-images img",
                video_selector=".leak-videos video",
                author_selector=".instagram-handle",
                date_selector=".leak-date",
                link_selector=".download-link",
                pagination_selector=".next-page"
            ),
            rate_limit_delay=2.5,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=False,
            keywords=["instagram", "leaked", "private", "stories"],
            blocked_content=["advertisement", "popup"],
            priority=2
        )
        
        # File sharing sites
        self.sites["mega-leaks"] = PiracySite(
            id="mega-leaks",
            name="MEGA Leaks",
            base_url="https://mega-leaks.net",
            site_type=SiteType.FILE_SHARING,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".file-listing",
                title_selector=".file-name",
                image_selector=".file-preview img",
                video_selector=".file-preview video",
                author_selector=".uploader",
                date_selector=".upload-date",
                link_selector=".mega-link",
                pagination_selector=".pagination .next"
            ),
            rate_limit_delay=3.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=False,
            keywords=["mega", "leaked", "premium", "exclusive"],
            blocked_content=["advertisement"],
            priority=2
        )
        
        # Forums
        self.sites["leakforums"] = PiracySite(
            id="leakforums",
            name="Leak Forums",
            base_url="https://leakforums.net",
            site_type=SiteType.FORUM,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".forum-post",
                title_selector=".post-title",
                image_selector=".post-attachments img",
                video_selector=".post-attachments video",
                author_selector=".post-author",
                date_selector=".post-date",
                link_selector=".attachment-download",
                pagination_selector=".forum-pagination .next"
            ),
            rate_limit_delay=2.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=False,
            keywords=["leaked", "premium", "onlyfans", "instagram"],
            blocked_content=["advertisement", "spam"],
            priority=2
        )
        
        # TikTok leak sites
        self.sites["tiktok-leaked"] = PiracySite(
            id="tiktok-leaked", 
            name="TikTok Leaked",
            base_url="https://tiktok-leaked.com",
            site_type=SiteType.TIKTOK_LEAK,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".tiktok-leak",
                title_selector=".leak-title",
                image_selector=".leak-thumbnail img",
                video_selector=".leak-video video",
                author_selector=".tiktok-user",
                date_selector=".leak-timestamp",
                link_selector=".download-tiktok",
                pagination_selector=".load-more"
            ),
            rate_limit_delay=2.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=True,
            keywords=["tiktok", "leaked", "private", "exclusive"],
            blocked_content=["advertisement"],
            priority=2
        )
        
        # Reddit-based leak communities
        self.sites["reddit-leaks"] = PiracySite(
            id="reddit-leaks",
            name="Reddit Leaks",
            base_url="https://reddit.com/r/leaked",
            site_type=SiteType.REDDIT_LEAK,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".Post",
                title_selector="._eYtD2XCVieq6emjKBH3m",
                image_selector=".ImageBox-image",
                video_selector=".VideoBox-video",
                author_selector="._2tbHP6ZydRpjI44J3syuqC",
                date_selector="._3jOxDPIQ0KaOWpzvSQo-1s",
                link_selector=".RichTextJSON-root a",
                pagination_selector=".next-button"
            ),
            rate_limit_delay=1.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=False,
            keywords=["leaked", "premium", "exclusive"],
            blocked_content=["advertisement"],
            priority=3
        )
        
        # Image boards
        self.sites["imageboard-leaks"] = PiracySite(
            id="imageboard-leaks",
            name="Imageboard Leaks",
            base_url="https://imageboard-leaks.org",
            site_type=SiteType.IMAGE_BOARD,
            status=SiteStatus.ACTIVE,
            scrape_patterns=ScrapePattern(
                content_selector=".post",
                title_selector=".post-title",
                image_selector=".post-image img",
                video_selector=".post-video video",
                author_selector=".post-author",
                date_selector=".post-date",
                link_selector=".post-link",
                pagination_selector=".pagination .next"
            ),
            rate_limit_delay=1.5,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            requires_js=False,
            keywords=["leaked", "premium", "exclusive"],
            blocked_content=["advertisement"],
            priority=3
        )
        
        logger.info(f"Loaded {len(self.sites)} piracy sites into database")
    
    async def get_sites_by_type(self, site_type: SiteType) -> List[PiracySite]:
        """Get all sites of a specific type"""
        return [site for site in self.sites.values() if site.site_type == site_type]
    
    async def get_active_sites(self) -> List[PiracySite]:
        """Get all currently active sites"""
        return [site for site in self.sites.values() if site.status == SiteStatus.ACTIVE]
    
    async def get_priority_sites(self, max_priority: int = 2) -> List[PiracySite]:
        """Get high priority sites for scanning"""
        return [
            site for site in self.sites.values() 
            if site.status == SiteStatus.ACTIVE and site.priority <= max_priority
        ]
    
    async def scrape_site_for_creator(
        self, 
        site: PiracySite, 
        creator_keywords: List[str],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape a specific site for creator content
        
        Returns list of potential matches with metadata
        """
        
        logger.info(f"Scraping {site.name} for creator keywords: {creator_keywords}")
        
        try:
            # Apply rate limiting
            await asyncio.sleep(site.rate_limit_delay)
            
            results = []
            
            # Generate search URLs based on site structure
            search_urls = self._generate_search_urls(site, creator_keywords)
            
            async with aiohttp.ClientSession(headers=site.headers) as session:
                for search_url in search_urls[:3]:  # Limit to first 3 search variations
                    try:
                        async with session.get(search_url) as response:
                            if response.status != 200:
                                logger.warning(f"Failed to access {search_url}: {response.status}")
                                continue
                                
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract content using site-specific patterns
                            posts = soup.select(site.scrape_patterns.content_selector)
                            
                            for post in posts[:limit]:
                                post_data = await self._extract_post_data(post, site)
                                
                                if post_data and self._is_relevant_to_creator(post_data, creator_keywords):
                                    # Calculate confidence score
                                    confidence = await self._calculate_confidence_score(
                                        post_data, creator_keywords
                                    )
                                    
                                    post_data['confidence_score'] = confidence
                                    post_data['site_info'] = {
                                        'site_id': site.id,
                                        'site_name': site.name,
                                        'site_type': site.site_type.value,
                                        'scraped_at': datetime.utcnow().isoformat()
                                    }
                                    
                                    results.append(post_data)
                    
                    except Exception as e:
                        logger.error(f"Error scraping {search_url}: {e}")
                        continue
            
            logger.info(f"Found {len(results)} potential matches on {site.name}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to scrape {site.name}: {e}")
            return []
    
    def _generate_search_urls(self, site: PiracySite, keywords: List[str]) -> List[str]:
        """Generate search URLs for the site based on keywords"""
        
        search_urls = []
        
        # Basic keyword searches
        for keyword in keywords[:2]:  # Limit to top 2 keywords
            # Common search patterns
            search_patterns = [
                f"/search?q={keyword}",
                f"/search/{keyword}",
                f"/?s={keyword}",
                f"/forum/search/{keyword}",
                f"/leaked/{keyword}"
            ]
            
            for pattern in search_patterns:
                search_urls.append(urljoin(site.base_url, pattern))
        
        # Also add main pages for browsing
        search_urls.append(site.base_url)
        search_urls.append(urljoin(site.base_url, "/latest"))
        search_urls.append(urljoin(site.base_url, "/recent"))
        
        return search_urls
    
    async def _extract_post_data(self, post_element, site: PiracySite) -> Optional[Dict[str, Any]]:
        """Extract structured data from a post element"""
        
        try:
            patterns = site.scrape_patterns
            
            # Extract basic information
            title_elem = post_element.select_one(patterns.title_selector)
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            author_elem = post_element.select_one(patterns.author_selector)
            author = author_elem.get_text(strip=True) if author_elem else ""
            
            date_elem = post_element.select_one(patterns.date_selector)
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            
            # Extract media
            images = []
            for img in post_element.select(patterns.image_selector):
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append(urljoin(site.base_url, src))
            
            videos = []
            for video in post_element.select(patterns.video_selector):
                src = video.get('src') or video.get('data-src')
                if src:
                    videos.append(urljoin(site.base_url, src))
            
            # Extract download links
            links = []
            for link in post_element.select(patterns.link_selector):
                href = link.get('href')
                if href:
                    links.append({
                        'url': urljoin(site.base_url, href),
                        'text': link.get_text(strip=True)
                    })
            
            # Get full post content text
            content = post_element.get_text(strip=True)
            
            if not title and not content:
                return None
                
            return {
                'title': title,
                'author': author,
                'date': date_text,
                'content': content,
                'images': images,
                'videos': videos,
                'links': links,
                'url': site.base_url  # Will be updated with specific post URL if available
            }
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None
    
    def _is_relevant_to_creator(self, post_data: Dict[str, Any], creator_keywords: List[str]) -> bool:
        """Check if post data is relevant to creator keywords"""
        
        # Combine all text content
        text_content = " ".join([
            post_data.get('title', ''),
            post_data.get('content', ''),
            post_data.get('author', '')
        ]).lower()
        
        # Check for keyword matches
        for keyword in creator_keywords:
            if keyword.lower() in text_content:
                return True
        
        # Check link text for keyword matches
        for link in post_data.get('links', []):
            if any(keyword.lower() in link.get('text', '').lower() for keyword in creator_keywords):
                return True
                
        return False
    
    async def _calculate_confidence_score(
        self, 
        post_data: Dict[str, Any], 
        creator_keywords: List[str]
    ) -> float:
        """Calculate confidence score for content match"""
        
        score = 0.0
        text_content = " ".join([
            post_data.get('title', ''),
            post_data.get('content', ''),
            post_data.get('author', '')
        ]).lower()
        
        # Keyword matching (40% of score)
        keyword_matches = sum(
            1 for keyword in creator_keywords 
            if keyword.lower() in text_content
        )
        keyword_score = min(keyword_matches / len(creator_keywords), 1.0) * 40
        
        # Content indicators (30% of score)
        leak_indicators = ['leaked', 'exclusive', 'premium', 'private', 'onlyfans']
        indicator_matches = sum(
            1 for indicator in leak_indicators 
            if indicator in text_content
        )
        indicator_score = min(indicator_matches / len(leak_indicators), 1.0) * 30
        
        # Media presence (20% of score)
        has_media = bool(post_data.get('images') or post_data.get('videos'))
        media_score = 20 if has_media else 0
        
        # Download links (10% of score)
        has_links = bool(post_data.get('links'))
        link_score = 10 if has_links else 0
        
        total_score = keyword_score + indicator_score + media_score + link_score
        return min(total_score, 100.0)
    
    async def scan_all_sites_for_creator(
        self, 
        creator_keywords: List[str],
        site_types: Optional[List[SiteType]] = None,
        priority_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Scan multiple sites for creator content
        
        Args:
            creator_keywords: List of keywords to search for
            site_types: Specific site types to scan (None = all)
            priority_threshold: Maximum priority level to scan
        """
        
        logger.info(f"Starting comprehensive scan for creator keywords: {creator_keywords}")
        
        # Get sites to scan
        sites_to_scan = []
        for site in self.sites.values():
            if site.status != SiteStatus.ACTIVE:
                continue
            if site.priority > priority_threshold:
                continue
            if site_types and site.site_type not in site_types:
                continue
                
            sites_to_scan.append(site)
        
        logger.info(f"Scanning {len(sites_to_scan)} sites")
        
        # Scan sites in parallel with controlled concurrency
        all_results = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent site scans
        
        async def scan_site_with_semaphore(site):
            async with semaphore:
                return await self.scrape_site_for_creator(site, creator_keywords)
        
        # Execute scans
        tasks = [scan_site_with_semaphore(site) for site in sites_to_scan]
        site_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all results
        for results in site_results:
            if isinstance(results, list):
                all_results.extend(results)
            elif isinstance(results, Exception):
                logger.error(f"Site scan failed: {results}")
        
        # Sort by confidence score
        all_results.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        
        logger.info(f"Found {len(all_results)} total potential matches across all sites")
        
        return all_results
    
    async def update_site_status(self, site_id: str, status: SiteStatus) -> bool:
        """Update site status (e.g., mark as blocked or inactive)"""
        if site_id in self.sites:
            self.sites[site_id].status = status
            self.sites[site_id].last_crawled = datetime.utcnow()
            logger.info(f"Updated {site_id} status to {status.value}")
            return True
        return False
    
    async def get_site_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        stats = {
            'total_sites': len(self.sites),
            'active_sites': len([s for s in self.sites.values() if s.status == SiteStatus.ACTIVE]),
            'inactive_sites': len([s for s in self.sites.values() if s.status == SiteStatus.INACTIVE]),
            'blocked_sites': len([s for s in self.sites.values() if s.status == SiteStatus.BLOCKED]),
            'sites_by_type': {},
            'priority_distribution': {}
        }
        
        # Count by type
        for site in self.sites.values():
            site_type = site.site_type.value
            stats['sites_by_type'][site_type] = stats['sites_by_type'].get(site_type, 0) + 1
            
            priority = site.priority
            stats['priority_distribution'][priority] = stats['priority_distribution'].get(priority, 0) + 1
        
        return stats


# Global instance
piracy_sites_db = PiracySiteDatabase()


__all__ = [
    'PiracySiteDatabase', 
    'PiracySite',
    'SiteType',
    'SiteStatus', 
    'ScrapePattern',
    'piracy_sites_db'
]