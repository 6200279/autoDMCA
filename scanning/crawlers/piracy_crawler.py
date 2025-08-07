"""
Specialized crawler for known piracy sites and forums.
"""

import asyncio
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, quote_plus
import json

import structlog
from bs4 import BeautifulSoup

from .web_crawler import WebCrawler, CrawlResult
from ..config import ScannerSettings, PiracySiteConfig


logger = structlog.get_logger(__name__)


@dataclass
class InfringingContent:
    """Represents potentially infringing content found on piracy sites."""
    
    title: str
    url: str
    site_name: str
    content_type: str  # image, video, post, file
    description: str = ""
    thumbnail_url: Optional[str] = None
    download_urls: List[str] = field(default_factory=list)
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    file_size: Optional[str] = None
    confidence_score: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate confidence score based on matched content."""
        if not self.confidence_score:
            self.confidence_score = self._calculate_confidence()
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence score for content match."""
        score = 0.0
        
        # Base score for having matched keywords
        if self.matched_keywords:
            score += min(len(self.matched_keywords) * 0.2, 0.8)
        
        # Boost for explicit leak terms
        leak_terms = ['leaked', 'leak', 'stolen', 'pirated', 'onlyfans', 'premium']
        title_lower = self.title.lower()
        desc_lower = self.description.lower()
        
        for term in leak_terms:
            if term in title_lower or term in desc_lower:
                score += 0.3
                break
        
        # Penalty for generic titles
        generic_terms = ['untitled', 'image', 'video', 'file', 'download']
        if any(term in title_lower for term in generic_terms):
            score -= 0.2
        
        return min(max(score, 0.0), 1.0)


@dataclass
class CrawlSession:
    """Represents a crawling session for a specific site and search terms."""
    
    site_config: PiracySiteConfig
    search_terms: List[str]
    max_pages: int = 5
    max_results: int = 100
    results: List[InfringingContent] = field(default_factory=list)
    pages_crawled: int = 0
    errors: List[str] = field(default_factory=list)
    
    def add_result(self, content: InfringingContent):
        """Add a result to this session."""
        self.results.append(content)
    
    def add_error(self, error: str):
        """Add an error to this session."""
        self.errors.append(error)
        logger.warning(f"Crawl session error on {self.site_config.name}: {error}")


class PiracySiteCrawler:
    """Specialized crawler for piracy sites with site-specific parsing."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.web_crawler = WebCrawler(settings)
        self.site_parsers: Dict[str, callable] = {}
        self._register_parsers()
    
    async def initialize(self):
        """Initialize the crawler."""
        await self.web_crawler.initialize()
    
    async def close(self):
        """Clean up resources."""
        await self.web_crawler.close()
    
    def _register_parsers(self):
        """Register site-specific parsers."""
        self.site_parsers.update({
            'generic_leak_forum': self._parse_generic_forum,
            'generic_file_host': self._parse_generic_filehost,
            'social_media_mirror': self._parse_social_mirror,
            'image_host': self._parse_image_host,
            'video_host': self._parse_video_host
        })
    
    async def crawl_site(
        self,
        site_config: PiracySiteConfig,
        search_terms: List[str],
        max_pages: int = 5,
        max_results: int = 100
    ) -> CrawlSession:
        """Crawl a specific piracy site for search terms."""
        session = CrawlSession(
            site_config=site_config,
            search_terms=search_terms,
            max_pages=max_pages,
            max_results=max_results
        )
        
        logger.info(
            f"Starting crawl session for {site_config.name}",
            search_terms=search_terms,
            max_pages=max_pages
        )
        
        try:
            for term in search_terms:
                if len(session.results) >= max_results:
                    break
                    
                await self._crawl_search_term(session, term)
                
                # Respect site rate limits
                await asyncio.sleep(site_config.rate_limit_delay)
                
        except Exception as e:
            session.add_error(f"Site crawl failed: {str(e)}")
            logger.error(f"Site crawl failed for {site_config.name}", error=str(e))
        
        logger.info(
            f"Crawl session completed for {site_config.name}",
            results_found=len(session.results),
            pages_crawled=session.pages_crawled,
            errors=len(session.errors)
        )
        
        return session
    
    async def _crawl_search_term(self, session: CrawlSession, search_term: str):
        """Crawl a specific search term on the site."""
        site = session.site_config
        
        for pattern in site.search_patterns:
            try:
                # Format search URL
                search_url = self._format_search_url(
                    site.base_url,
                    pattern,
                    search_term
                )
                
                # Crawl search pages
                page = 1
                while page <= session.max_pages and len(session.results) < session.max_results:
                    page_url = self._add_pagination(search_url, page)
                    
                    result = await self.web_crawler.crawl(
                        page_url,
                        use_proxy=site.requires_proxy,
                        render_js=site.cloudflare_protection,
                        extract_images=True,
                        extract_links=True
                    )
                    
                    if not result.is_success:
                        session.add_error(f"Failed to crawl {page_url}: {result.error}")
                        break
                    
                    # Parse results from page
                    content_items = await self._parse_search_results(
                        session, result, search_term
                    )
                    
                    if not content_items:
                        break  # No more results
                    
                    session.pages_crawled += 1
                    page += 1
                    
                    # Rate limiting
                    await asyncio.sleep(site.rate_limit_delay)
                    
            except Exception as e:
                session.add_error(f"Search term '{search_term}' failed: {str(e)}")
    
    def _format_search_url(self, base_url: str, pattern: str, search_term: str) -> str:
        """Format search URL with proper encoding."""
        # URL encode the search term
        encoded_term = quote_plus(search_term)
        
        # Replace placeholders in pattern
        formatted_pattern = pattern.format(
            username=encoded_term,
            query=encoded_term,
            term=encoded_term
        )
        
        # Join with base URL
        return urljoin(base_url, formatted_pattern)
    
    def _add_pagination(self, url: str, page: int) -> str:
        """Add pagination parameters to URL."""
        if page == 1:
            return url
        
        # Common pagination patterns
        pagination_params = [
            f"&page={page}",
            f"?page={page}", 
            f"&p={page}",
            f"?p={page}",
            f"&offset={(page-1)*20}",  # Assuming 20 results per page
            f"/page/{page}"
        ]
        
        # Simple heuristic - add page parameter
        if '?' in url:
            return f"{url}&page={page}"
        else:
            return f"{url}?page={page}"
    
    async def _parse_search_results(
        self,
        session: CrawlSession,
        crawl_result: CrawlResult,
        search_term: str
    ) -> List[InfringingContent]:
        """Parse search results from crawled page."""
        content_items = []
        
        try:
            soup = BeautifulSoup(crawl_result.html, 'html.parser')
            site_name = session.site_config.name
            
            # Try to detect site type and use appropriate parser
            parser = self._get_site_parser(session.site_config, soup)
            if parser:
                content_items = await parser(session, soup, search_term, crawl_result.url)
            else:
                # Fall back to generic parsing
                content_items = await self._parse_generic_results(
                    session, soup, search_term, crawl_result.url
                )
            
            # Filter results by confidence score
            filtered_items = [
                item for item in content_items
                if item.confidence_score >= 0.3  # Minimum confidence threshold
            ]
            
            logger.debug(
                f"Parsed search results from {site_name}",
                total_items=len(content_items),
                filtered_items=len(filtered_items),
                search_term=search_term
            )
            
            # Add to session
            for item in filtered_items:
                session.add_result(item)
            
            return filtered_items
            
        except Exception as e:
            session.add_error(f"Failed to parse results: {str(e)}")
            return []
    
    def _get_site_parser(self, site_config: PiracySiteConfig, soup: BeautifulSoup) -> Optional[callable]:
        """Get appropriate parser for the site type."""
        site_name = site_config.name.lower()
        
        # Check for specific site types
        if 'forum' in site_name:
            return self.site_parsers.get('generic_leak_forum')
        elif 'filehost' in site_name or 'file_host' in site_name:
            return self.site_parsers.get('generic_file_host')
        elif 'social' in site_name or 'mirror' in site_name:
            return self.site_parsers.get('social_media_mirror')
        
        # Auto-detect based on page structure
        if soup.find_all('div', class_=re.compile('post|thread|topic')):
            return self.site_parsers.get('generic_leak_forum')
        elif soup.find_all('div', class_=re.compile('file|download')):
            return self.site_parsers.get('generic_file_host')
        elif soup.find_all('img', class_=re.compile('thumb|preview')):
            return self.site_parsers.get('image_host')
        
        return None
    
    async def _parse_generic_forum(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Parse generic forum/leak site structure."""
        results = []
        site_config = session.site_config
        
        try:
            # Look for common forum post selectors
            post_selectors = [
                '.post', '.thread', '.topic',
                '[class*="post"]', '[class*="thread"]', '[class*="topic"]'
            ]
            
            posts = []
            for selector in post_selectors:
                posts = soup.select(selector)
                if posts:
                    break
            
            for post in posts[:20]:  # Limit to first 20 posts
                try:
                    # Extract title
                    title_elem = (
                        post.find('h1') or post.find('h2') or post.find('h3') or
                        post.find('a', class_=re.compile('title|subject')) or
                        post.find(class_=re.compile('title|subject'))
                    )
                    title = title_elem.get_text(strip=True) if title_elem else "Untitled"
                    
                    # Extract URL
                    link_elem = title_elem if title_elem and title_elem.name == 'a' else post.find('a')
                    url = urljoin(page_url, link_elem['href']) if link_elem and link_elem.get('href') else page_url
                    
                    # Extract description
                    content_elem = post.find(class_=re.compile('content|body|text'))
                    description = content_elem.get_text(strip=True)[:500] if content_elem else ""
                    
                    # Extract images
                    img_elements = post.find_all('img')
                    thumbnail_url = None
                    if img_elements:
                        for img in img_elements:
                            src = img.get('src') or img.get('data-src')
                            if src:
                                thumbnail_url = urljoin(page_url, src)
                                break
                    
                    # Check if content matches search term
                    text_content = f"{title} {description}".lower()
                    if search_term.lower() in text_content:
                        matched_keywords = [search_term]
                    else:
                        matched_keywords = []
                    
                    # Extract metadata
                    uploader = None
                    uploader_elem = post.find(class_=re.compile('author|user|poster'))
                    if uploader_elem:
                        uploader = uploader_elem.get_text(strip=True)
                    
                    # Create content item
                    content = InfringingContent(
                        title=title,
                        url=url,
                        site_name=site_config.name,
                        content_type='post',
                        description=description,
                        thumbnail_url=thumbnail_url,
                        uploader=uploader,
                        matched_keywords=matched_keywords
                    )
                    
                    results.append(content)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse forum post: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Forum parsing failed: {str(e)}")
        
        return results
    
    async def _parse_generic_filehost(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Parse generic file hosting site structure."""
        results = []
        site_config = session.site_config
        
        try:
            # Look for file entries
            file_selectors = [
                '.file', '.download', '.item',
                '[class*="file"]', '[class*="download"]', '[class*="item"]'
            ]
            
            files = []
            for selector in file_selectors:
                files = soup.select(selector)
                if files:
                    break
            
            for file_elem in files[:30]:  # Limit to first 30 files
                try:
                    # Extract file name/title
                    title_elem = (
                        file_elem.find(class_=re.compile('name|title|filename')) or
                        file_elem.find('a') or
                        file_elem.find('h1') or file_elem.find('h2')
                    )
                    title = title_elem.get_text(strip=True) if title_elem else "Unknown File"
                    
                    # Extract download URL
                    download_elem = file_elem.find('a', class_=re.compile('download|link'))
                    if not download_elem:
                        download_elem = file_elem.find('a')
                    
                    url = urljoin(page_url, download_elem['href']) if download_elem and download_elem.get('href') else page_url
                    
                    # Extract file info
                    size_elem = file_elem.find(class_=re.compile('size|bytes'))
                    file_size = size_elem.get_text(strip=True) if size_elem else None
                    
                    # Extract thumbnail
                    img_elem = file_elem.find('img')
                    thumbnail_url = None
                    if img_elem:
                        src = img_elem.get('src') or img_elem.get('data-src')
                        if src:
                            thumbnail_url = urljoin(page_url, src)
                    
                    # Check relevance
                    if search_term.lower() in title.lower():
                        matched_keywords = [search_term]
                    else:
                        matched_keywords = []
                    
                    # Determine content type from filename
                    content_type = 'file'
                    title_lower = title.lower()
                    if any(ext in title_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        content_type = 'image'
                    elif any(ext in title_lower for ext in ['.mp4', '.avi', '.mov', '.wmv']):
                        content_type = 'video'
                    
                    content = InfringingContent(
                        title=title,
                        url=url,
                        site_name=site_config.name,
                        content_type=content_type,
                        thumbnail_url=thumbnail_url,
                        file_size=file_size,
                        download_urls=[url],
                        matched_keywords=matched_keywords
                    )
                    
                    results.append(content)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse file entry: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"File host parsing failed: {str(e)}")
        
        return results
    
    async def _parse_social_mirror(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Parse social media mirror/aggregator sites."""
        results = []
        site_config = session.site_config
        
        try:
            # Look for social media posts
            post_selectors = [
                '.post', '.item', '.content',
                '[class*="post"]', '[class*="item"]', '[class*="content"]'
            ]
            
            posts = []
            for selector in post_selectors:
                posts = soup.select(selector)
                if posts:
                    break
            
            for post in posts[:25]:  # Limit to first 25 posts
                try:
                    # Extract images
                    img_elements = post.find_all('img')
                    if not img_elements:
                        continue
                    
                    # Get main image
                    main_img = img_elements[0]
                    img_src = main_img.get('src') or main_img.get('data-src')
                    if not img_src:
                        continue
                    
                    img_url = urljoin(page_url, img_src)
                    
                    # Extract caption/title
                    caption_elem = (
                        post.find(class_=re.compile('caption|description|text')) or
                        post.find('p') or post.find('span')
                    )
                    title = caption_elem.get_text(strip=True)[:100] if caption_elem else "Social Media Post"
                    
                    # Extract post URL
                    link_elem = post.find('a')
                    post_url = urljoin(page_url, link_elem['href']) if link_elem and link_elem.get('href') else page_url
                    
                    # Check for username mentions
                    text_content = f"{title}".lower()
                    matched_keywords = []
                    if search_term.lower() in text_content:
                        matched_keywords = [search_term]
                    
                    content = InfringingContent(
                        title=title,
                        url=post_url,
                        site_name=site_config.name,
                        content_type='image',
                        thumbnail_url=img_url,
                        download_urls=[img_url],
                        matched_keywords=matched_keywords
                    )
                    
                    results.append(content)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse social post: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Social mirror parsing failed: {str(e)}")
        
        return results
    
    async def _parse_image_host(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Parse image hosting sites."""
        results = []
        site_config = session.site_config
        
        try:
            # Find image galleries or thumbnails
            img_containers = soup.find_all(['div', 'a'], class_=re.compile('thumb|image|gallery|photo'))
            
            for container in img_containers[:40]:  # Limit to first 40 images
                try:
                    img_elem = container.find('img')
                    if not img_elem:
                        continue
                    
                    # Get image source
                    img_src = img_elem.get('src') or img_elem.get('data-src')
                    if not img_src:
                        continue
                    
                    img_url = urljoin(page_url, img_src)
                    
                    # Get full resolution link if available
                    full_res_url = img_url
                    if container.name == 'a' and container.get('href'):
                        full_res_url = urljoin(page_url, container['href'])
                    
                    # Extract title from alt text or filename
                    title = (
                        img_elem.get('alt') or
                        img_elem.get('title') or
                        img_url.split('/')[-1]
                    )
                    
                    # Check relevance (filename often contains usernames)
                    if search_term.lower() in title.lower():
                        matched_keywords = [search_term]
                    else:
                        matched_keywords = []
                    
                    content = InfringingContent(
                        title=title,
                        url=full_res_url,
                        site_name=site_config.name,
                        content_type='image',
                        thumbnail_url=img_url,
                        download_urls=[full_res_url],
                        matched_keywords=matched_keywords
                    )
                    
                    results.append(content)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse image: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Image host parsing failed: {str(e)}")
        
        return results
    
    async def _parse_video_host(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Parse video hosting sites."""
        results = []
        site_config = session.site_config
        
        try:
            # Find video containers
            video_containers = soup.find_all(['div', 'article'], class_=re.compile('video|player|item'))
            
            for container in video_containers[:20]:  # Limit to first 20 videos
                try:
                    # Extract title
                    title_elem = container.find(['h1', 'h2', 'h3', 'title'])
                    if not title_elem:
                        title_elem = container.find(class_=re.compile('title|name'))
                    
                    title = title_elem.get_text(strip=True) if title_elem else "Video"
                    
                    # Extract video URL
                    video_link = container.find('a')
                    video_url = urljoin(page_url, video_link['href']) if video_link and video_link.get('href') else page_url
                    
                    # Extract thumbnail
                    thumbnail_url = None
                    img_elem = container.find('img')
                    if img_elem:
                        src = img_elem.get('src') or img_elem.get('data-src')
                        if src:
                            thumbnail_url = urljoin(page_url, src)
                    
                    # Extract duration if available
                    duration_elem = container.find(class_=re.compile('duration|time'))
                    duration = duration_elem.get_text(strip=True) if duration_elem else None
                    
                    # Check relevance
                    if search_term.lower() in title.lower():
                        matched_keywords = [search_term]
                    else:
                        matched_keywords = []
                    
                    content = InfringingContent(
                        title=title,
                        url=video_url,
                        site_name=site_config.name,
                        content_type='video',
                        thumbnail_url=thumbnail_url,
                        matched_keywords=matched_keywords
                    )
                    
                    if duration:
                        content.metadata['duration'] = duration
                    
                    results.append(content)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse video: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Video host parsing failed: {str(e)}")
        
        return results
    
    async def _parse_generic_results(
        self,
        session: CrawlSession,
        soup: BeautifulSoup,
        search_term: str,
        page_url: str
    ) -> List[InfringingContent]:
        """Generic result parser when site-specific parser is not available."""
        results = []
        
        try:
            # Look for any links that might contain relevant content
            links = soup.find_all('a', href=True)
            
            for link in links[:50]:  # Limit to first 50 links
                href = link.get('href')
                if not href or href.startswith('#'):
                    continue
                
                link_text = link.get_text(strip=True)
                if not link_text:
                    continue
                
                # Check if link text contains search term
                if search_term.lower() in link_text.lower():
                    url = urljoin(page_url, href)
                    
                    content = InfringingContent(
                        title=link_text,
                        url=url,
                        site_name=session.site_config.name,
                        content_type='unknown',
                        matched_keywords=[search_term]
                    )
                    
                    results.append(content)
            
        except Exception as e:
            logger.error(f"Generic parsing failed: {str(e)}")
        
        return results
    
    async def bulk_crawl(
        self,
        site_configs: List[PiracySiteConfig],
        search_terms: List[str],
        **kwargs
    ) -> Dict[str, CrawlSession]:
        """Crawl multiple piracy sites concurrently."""
        async def crawl_single_site(site_config: PiracySiteConfig) -> Tuple[str, CrawlSession]:
            try:
                session = await self.crawl_site(site_config, search_terms, **kwargs)
                return site_config.name, session
            except Exception as e:
                logger.error(f"Site crawl failed: {site_config.name}", error=str(e))
                return site_config.name, CrawlSession(
                    site_config=site_config,
                    search_terms=search_terms,
                    errors=[str(e)]
                )
        
        tasks = [crawl_single_site(site) for site in site_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        sessions = {}
        for result in results:
            if isinstance(result, tuple):
                site_name, session = result
                sessions[site_name] = session
        
        return sessions