"""
Piracy Site Database and Targeted Crawler
Database of known leak sites and specialized crawling for adult content piracy
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import logging
import json
import hashlib
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, quote_plus
import re

from .platforms.base_scanner import BaseScanner, ScanResult
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PiracySite:
    """Piracy site configuration"""
    name: str
    domain: str
    base_url: str
    site_type: str  # 'forum', 'leak_site', 'tube_site', 'telegram', 'discord'
    risk_level: str  # 'high', 'medium', 'low'
    search_patterns: List[str] = field(default_factory=list)
    content_selectors: Dict[str, str] = field(default_factory=dict)
    rate_limit: int = 10  # requests per minute
    requires_cloudflare_bypass: bool = False
    active: bool = True
    last_scanned: Optional[datetime] = None
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PiracySiteDatabase:
    """
    Database of known piracy sites and leak forums
    PRD: "Targeted scanning for adult content piracy sites"
    """
    
    def __init__(self):
        self.sites: Dict[str, PiracySite] = {}
        self._initialize_sites()
    
    def _initialize_sites(self):
        """Initialize database with known piracy sites"""
        
        # Major adult content leak forums and sites
        sites_data = [
            # Forums and Leak Sites
            {
                "name": "LeakHub",
                "domain": "leakhub.to",
                "base_url": "https://leakhub.to",
                "site_type": "forum",
                "risk_level": "high",
                "search_patterns": [
                    "/search?q={query}",
                    "/search/{query}",
                    "/?s={query}"
                ],
                "content_selectors": {
                    "posts": ".post, .thread, .topic",
                    "title": ".post-title, .thread-title, h3, h4",
                    "content": ".post-content, .thread-content, .excerpt",
                    "author": ".post-author, .author, .username",
                    "images": "img[src*='jpg'], img[src*='jpeg'], img[src*='png']",
                    "videos": "video source, a[href*='.mp4'], a[href*='.webm']"
                },
                "rate_limit": 5,
                "requires_cloudflare_bypass": True
            },
            {
                "name": "OnlyFans Leaks",
                "domain": "onlyfansleaks.com",
                "base_url": "https://onlyfansleaks.com", 
                "site_type": "leak_site",
                "risk_level": "high",
                "search_patterns": [
                    "/search/{query}",
                    "/?s={query}"
                ],
                "content_selectors": {
                    "posts": ".post, .entry",
                    "title": ".post-title, h2, h3",
                    "content": ".post-content, .entry-content",
                    "images": "img[src*='jpg'], img[src*='jpeg'], img[src*='png']",
                    "videos": "video, a[href*='.mp4']"
                },
                "rate_limit": 5
            },
            {
                "name": "Thothub",
                "domain": "thothub.tv",
                "base_url": "https://thothub.tv",
                "site_type": "leak_site", 
                "risk_level": "high",
                "search_patterns": [
                    "/search?q={query}",
                    "/models/{query}"
                ],
                "content_selectors": {
                    "posts": ".model-card, .post-card",
                    "title": ".model-name, .post-title",
                    "content": ".model-description, .post-excerpt",
                    "images": "img.model-image, img.post-image",
                    "videos": "video, .video-container"
                },
                "rate_limit": 8
            },
            {
                "name": "Simpcity",
                "domain": "simpcity.su",
                "base_url": "https://simpcity.su",
                "site_type": "forum",
                "risk_level": "high",
                "search_patterns": [
                    "/search/?q={query}",
                    "/threads/{query}"
                ],
                "content_selectors": {
                    "posts": ".structItem, .message",
                    "title": ".structItem-title, .message-title",
                    "content": ".structItem-cell--main, .message-body",
                    "images": "img[data-src], img[src*='attachments']",
                    "videos": "video, a[href*='mp4']"
                },
                "rate_limit": 10,
                "requires_cloudflare_bypass": True
            },
            
            # Tube Sites
            {
                "name": "Pornhub",
                "domain": "pornhub.com",
                "base_url": "https://www.pornhub.com",
                "site_type": "tube_site",
                "risk_level": "medium",
                "search_patterns": [
                    "/video/search?search={query}",
                    "/channels/{query}",
                    "/users/{query}"
                ],
                "content_selectors": {
                    "posts": ".phimage, .videoblock",
                    "title": ".title, .videoTitle",
                    "content": ".video-wrapper",
                    "images": "img[data-src], .thumb",
                    "videos": "video, .videoPreview"
                },
                "rate_limit": 20
            },
            {
                "name": "Xvideos",
                "domain": "xvideos.com", 
                "base_url": "https://www.xvideos.com",
                "site_type": "tube_site",
                "risk_level": "medium",
                "search_patterns": [
                    "/?k={query}",
                    "/c/{query}",
                    "/profiles/{query}"
                ],
                "content_selectors": {
                    "posts": ".thumb-block",
                    "title": ".title",
                    "content": ".thumb-inside",
                    "images": "img[data-src]",
                    "videos": "video"
                },
                "rate_limit": 15
            },
            {
                "name": "XHamster",
                "domain": "xhamster.com",
                "base_url": "https://xhamster.com",
                "site_type": "tube_site", 
                "risk_level": "medium",
                "search_patterns": [
                    "/search/{query}",
                    "/users/{query}",
                    "/channels/{query}"
                ],
                "content_selectors": {
                    "posts": ".thumb-list__item",
                    "title": ".video-thumb-info__name",
                    "content": ".thumb-image-container",
                    "images": "img[data-src]",
                    "videos": "video"
                },
                "rate_limit": 15
            },
            
            # File Sharing and Mega Sites
            {
                "name": "Mega Links",
                "domain": "megalinks.info",
                "base_url": "https://megalinks.info",
                "site_type": "forum",
                "risk_level": "high",
                "search_patterns": [
                    "/search?q={query}",
                    "/category/{query}"
                ],
                "content_selectors": {
                    "posts": ".post, .link-post",
                    "title": ".post-title, h2",
                    "content": ".post-content",
                    "links": "a[href*='mega.nz'], a[href*='drive.google'], a[href*='dropbox']"
                },
                "rate_limit": 5,
                "requires_cloudflare_bypass": True
            },
            
            # Reddit alternatives and chans
            {
                "name": "4chan Adult",
                "domain": "4chan.org",
                "base_url": "https://boards.4chan.org",
                "site_type": "forum",
                "risk_level": "medium",
                "search_patterns": [
                    "/s/catalog#{query}",
                    "/b/catalog#{query}"
                ],
                "content_selectors": {
                    "posts": ".thread, .post",
                    "title": ".subject",
                    "content": ".postMessage",
                    "images": "img[src*='i.4cdn.org']",
                    "videos": "video"
                },
                "rate_limit": 5
            },
            
            # Telegram Channels (would require Telegram API)
            {
                "name": "Telegram Leaks",
                "domain": "t.me",
                "base_url": "https://t.me",
                "site_type": "telegram",
                "risk_level": "high",
                "search_patterns": [
                    "/s/{query}",
                    "/{query}",
                    "/joinchat/{query}"
                ],
                "content_selectors": {
                    "posts": ".tgme_widget_message",
                    "title": ".tgme_widget_message_author",
                    "content": ".tgme_widget_message_text",
                    "images": "img.tgme_widget_message_photo",
                    "videos": "video.tgme_widget_message_video"
                },
                "rate_limit": 10,
                "active": False  # Requires special handling
            }
        ]
        
        # Initialize site objects
        for site_data in sites_data:
            site = PiracySite(**site_data)
            self.sites[site.domain] = site
    
    def get_active_sites(self) -> List[PiracySite]:
        """Get all active piracy sites"""
        return [site for site in self.sites.values() if site.active]
    
    def get_sites_by_type(self, site_type: str) -> List[PiracySite]:
        """Get sites by type"""
        return [
            site for site in self.sites.values() 
            if site.site_type == site_type and site.active
        ]
    
    def get_high_risk_sites(self) -> List[PiracySite]:
        """Get high-risk sites most likely to have leaked content"""
        return [
            site for site in self.sites.values()
            if site.risk_level == "high" and site.active
        ]
    
    def update_site_performance(self, domain: str, success: bool):
        """Update site performance metrics"""
        if domain in self.sites:
            site = self.sites[domain]
            site.last_scanned = datetime.utcnow()
            
            # Update success rate with exponential moving average
            alpha = 0.1
            if success:
                site.success_rate = site.success_rate * (1 - alpha) + alpha
            else:
                site.success_rate = site.success_rate * (1 - alpha)
            
            # Deactivate sites with very low success rates
            if site.success_rate < 0.2:
                site.active = False
                logger.warning(f"Deactivated site {domain} due to low success rate")


class PiracySiteScanner(BaseScanner):
    """
    Specialized scanner for piracy sites and leak forums
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=10, **kwargs)
        
        self.piracy_db = PiracySiteDatabase()
        self.cloudflare_bypass_enabled = getattr(settings, 'CLOUDFLARE_BYPASS_ENABLED', False)
        
        # Content filtering patterns
        self.content_indicators = [
            r'\b(?:onlyfans|of)\b',
            r'\b(?:leaked?|leaks?)\b', 
            r'\b(?:exclusive|premium)\b',
            r'\b(?:free\s+download)\b',
            r'\b(?:mega\.nz|drive\.google|dropbox)\b',
            r'\b(?:telegram|discord)\b'
        ]
        
        # Compile regex patterns for performance
        self.content_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.content_indicators]
    
    async def get_platform_name(self) -> str:
        return "piracy_sites"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search across multiple piracy sites and leak forums
        """
        results = []
        site_type = kwargs.get('site_type', None)
        risk_level = kwargs.get('risk_level', 'high')
        
        try:
            # Get target sites based on criteria
            if site_type:
                target_sites = self.piracy_db.get_sites_by_type(site_type)
            elif risk_level == 'high':
                target_sites = self.piracy_db.get_high_risk_sites()
            else:
                target_sites = self.piracy_db.get_active_sites()
            
            # Limit number of sites to avoid overwhelming
            target_sites = target_sites[:10]
            
            # Search each site
            search_tasks = []
            results_per_site = max(5, limit // len(target_sites)) if target_sites else limit
            
            for site in target_sites:
                if len(search_tasks) >= 5:  # Limit concurrent searches
                    break
                    
                task = asyncio.create_task(
                    self._search_piracy_site(site, query, results_per_site)
                )
                search_tasks.append(task)
            
            # Execute searches concurrently
            site_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Aggregate results
            for site_result in site_results:
                if isinstance(site_result, list):
                    results.extend(site_result)
                elif isinstance(site_result, Exception):
                    logger.error(f"Piracy site search error: {site_result}")
            
            # Sort by confidence score and limit results
            results.sort(key=lambda x: x.confidence_score, reverse=True)
            results = results[:limit]
            
        except Exception as e:
            logger.error(f"Piracy sites search error for query '{query}': {e}")
        
        logger.info(f"Piracy sites search found {len(results)} results for query: {query}")
        return results
    
    async def _search_piracy_site(
        self,
        site: PiracySite,
        query: str,
        limit: int
    ) -> List[ScanResult]:
        """Search a specific piracy site"""
        results = []
        
        try:
            # Try each search pattern for the site
            for search_pattern in site.search_patterns:
                try:
                    search_url = urljoin(site.base_url, search_pattern.format(query=quote_plus(query)))
                    
                    # Special handling for Cloudflare-protected sites
                    if site.requires_cloudflare_bypass and not self.cloudflare_bypass_enabled:
                        logger.warning(f"Skipping {site.name} - Cloudflare bypass not enabled")
                        continue
                    
                    # Fetch search results page
                    html_content = await self._fetch_site_content(site, search_url)
                    
                    if html_content:
                        # Parse results from HTML
                        site_results = await self._parse_piracy_site_results(
                            site, html_content, query, search_url
                        )
                        
                        results.extend(site_results)
                        self.piracy_db.update_site_performance(site.domain, True)
                        
                        # Stop if we have enough results from this site
                        if len(results) >= limit:
                            break
                    else:
                        self.piracy_db.update_site_performance(site.domain, False)
                        
                except Exception as e:
                    logger.error(f"Error searching {site.name} with pattern {search_pattern}: {e}")
                    self.piracy_db.update_site_performance(site.domain, False)
                    continue
                
                # Small delay between searches on same site
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Error searching piracy site {site.name}: {e}")
            self.piracy_db.update_site_performance(site.domain, False)
        
        return results[:limit]
    
    async def _fetch_site_content(self, site: PiracySite, url: str) -> Optional[str]:
        """Fetch content from piracy site with appropriate headers"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        # Add site-specific headers if configured
        if 'headers' in site.metadata:
            headers.update(site.metadata['headers'])
        
        try:
            # Respect site's rate limit
            if hasattr(self, '_last_request_times'):
                last_request = self._last_request_times.get(site.domain, 0)
                min_interval = 60 / site.rate_limit  # Convert rate limit to interval
                elapsed = asyncio.get_event_loop().time() - last_request
                
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    await asyncio.sleep(wait_time)
            else:
                self._last_request_times = {}
            
            self._last_request_times[site.domain] = asyncio.get_event_loop().time()
            
            return await self._fetch_html(url, headers=headers)
            
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return None
    
    async def _parse_piracy_site_results(
        self,
        site: PiracySite,
        html_content: str,
        query: str,
        search_url: str
    ) -> List[ScanResult]:
        """Parse search results from piracy site HTML"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find posts using site's CSS selectors
            posts_selector = site.content_selectors.get('posts', '.post, .thread, .item')
            posts = soup.select(posts_selector)
            
            for post in posts[:20]:  # Limit processing per site
                try:
                    result = await self._process_piracy_post(site, post, query, search_url)
                    if result and self._is_relevant_content(result, query):
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing post from {site.name}: {e}")
                    continue
            
        except ImportError:
            logger.warning("BeautifulSoup not available for parsing piracy site results")
        except Exception as e:
            logger.error(f"Error parsing results from {site.name}: {e}")
        
        return results
    
    async def _process_piracy_post(
        self,
        site: PiracySite,
        post_element,
        query: str,
        search_url: str
    ) -> Optional[ScanResult]:
        """Process individual post from piracy site"""
        try:
            # Extract title
            title_selector = site.content_selectors.get('title', '.title, h2, h3, h4')
            title_elem = post_element.select_one(title_selector)
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract content/description
            content_selector = site.content_selectors.get('content', '.content, .excerpt, p')
            content_elem = post_element.select_one(content_selector)
            description = content_elem.get_text(strip=True) if content_elem else ''
            
            # Extract URL
            url = None
            link_elem = post_element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                url = urljoin(site.base_url, href) if not href.startswith('http') else href
            
            if not url:
                return None
            
            # Extract author
            author_selector = site.content_selectors.get('author', '.author, .username')
            author_elem = post_element.select_one(author_selector)
            author = author_elem.get_text(strip=True) if author_elem else ''
            
            # Extract media URLs
            media_urls = []
            
            # Images
            image_selector = site.content_selectors.get('images', 'img')
            images = post_element.select(image_selector)
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    img_url = urljoin(site.base_url, src) if not src.startswith('http') else src
                    if self._is_valid_media_url(img_url):
                        media_urls.append(img_url)
            
            # Videos
            video_selector = site.content_selectors.get('videos', 'video')
            videos = post_element.select(video_selector)
            for video in videos:
                src = video.get('src')
                if src:
                    video_url = urljoin(site.base_url, src) if not src.startswith('http') else src
                    if self._is_valid_media_url(video_url):
                        media_urls.append(video_url)
            
            # Calculate confidence score
            confidence_score = self._calculate_piracy_relevance(
                title, description, site, query
            )
            
            # Build metadata
            metadata = {
                'site_name': site.name,
                'site_domain': site.domain,
                'site_type': site.site_type,
                'risk_level': site.risk_level,
                'search_url': search_url,
                'content_indicators_found': self._find_content_indicators(f"{title} {description}")
            }
            
            return ScanResult(
                url=url,
                platform="piracy_sites",
                title=self._clean_text(title),
                description=self._clean_text(description[:300]),
                image_url=media_urls[0] if media_urls and any('jpg' in u or 'png' in u for u in media_urls) else None,
                video_url=next((u for u in media_urls if any(ext in u for ext in ['.mp4', '.webm', '.avi'])), None),
                media_urls=media_urls,
                author=author,
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing piracy post: {e}")
            return None
    
    def _calculate_piracy_relevance(
        self,
        title: str,
        description: str,
        site: PiracySite,
        query: str
    ) -> float:
        """Calculate relevance score for piracy site result"""
        score = 0.3  # Base score
        
        content_text = f"{title} {description}".lower()
        query_terms = query.lower().split()
        
        # Score based on query term matches
        for term in query_terms:
            if term in content_text:
                score += 0.2
        
        # Boost score based on site risk level
        if site.risk_level == "high":
            score += 0.3
        elif site.risk_level == "medium":
            score += 0.2
        
        # Boost score for content indicators
        indicators_found = self._find_content_indicators(content_text)
        score += len(indicators_found) * 0.1
        
        # Boost for specific leak terms
        if any(term in content_text for term in ['leaked', 'leak', 'exclusive', 'premium']):
            score += 0.3
        
        # Boost for file sharing links
        if any(term in content_text for term in ['mega.nz', 'drive.google', 'dropbox', 'telegram']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _find_content_indicators(self, text: str) -> List[str]:
        """Find content indicators in text"""
        indicators = []
        
        for pattern in self.content_regex:
            matches = pattern.findall(text)
            indicators.extend(matches)
        
        return list(set(indicators))  # Remove duplicates
    
    def _is_relevant_content(self, result: ScanResult, query: str) -> bool:
        """Check if result is relevant for content protection"""
        # Must have reasonable confidence score
        if result.confidence_score < 0.4:
            return False
        
        # Must contain query terms or content indicators
        content_text = f"{result.title} {result.description}".lower()
        query_terms = query.lower().split()
        
        has_query_match = any(term in content_text for term in query_terms)
        has_content_indicators = len(self._find_content_indicators(content_text)) > 0
        
        return has_query_match or has_content_indicators
    
    async def search_high_risk_sites(
        self,
        query: str,
        limit: int = 25,
        **kwargs
    ) -> List[ScanResult]:
        """Search only high-risk piracy sites"""
        return await self.search(query, limit=limit, risk_level='high', **kwargs)
    
    async def search_forums(
        self,
        query: str,
        limit: int = 25,
        **kwargs
    ) -> List[ScanResult]:
        """Search piracy forums specifically"""
        return await self.search(query, limit=limit, site_type='forum', **kwargs)
    
    async def search_tube_sites(
        self,
        query: str,
        limit: int = 25,
        **kwargs
    ) -> List[ScanResult]:
        """Search adult tube sites"""
        return await self.search(query, limit=limit, site_type='tube_site', **kwargs)
    
    async def health_check(self) -> bool:
        """Check if piracy site scanner is healthy"""
        try:
            # Test a few high-success-rate sites
            active_sites = [s for s in self.piracy_db.get_active_sites() if s.success_rate > 0.5]
            
            if not active_sites:
                return False
            
            # Simple connectivity test to a reliable site
            test_site = active_sites[0]
            response = await self._make_request(test_site.base_url)
            return response is not None
            
        except Exception as e:
            logger.error(f"Piracy site scanner health check failed: {e}")
            return False
    
    def get_site_statistics(self) -> Dict[str, Any]:
        """Get statistics about piracy sites"""
        all_sites = list(self.piracy_db.sites.values())
        active_sites = [s for s in all_sites if s.active]
        
        return {
            'total_sites': len(all_sites),
            'active_sites': len(active_sites),
            'sites_by_type': {
                site_type: len([s for s in active_sites if s.site_type == site_type])
                for site_type in set(s.site_type for s in active_sites)
            },
            'sites_by_risk': {
                risk: len([s for s in active_sites if s.risk_level == risk])
                for risk in set(s.risk_level for s in active_sites)  
            },
            'average_success_rate': sum(s.success_rate for s in active_sites) / len(active_sites) if active_sites else 0
        }