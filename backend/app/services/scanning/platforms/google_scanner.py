"""
Google Search API Integration
Searches Google using Custom Search API for content discovery
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import quote_plus
import json

from .base_scanner import BaseScanner, ScanResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleScanner(BaseScanner):
    """
    Google Search scanner using Custom Search API
    PRD: "Scans major platforms: Google"
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=100, **kwargs)  # 100 queries per minute
        
        # Google Custom Search API configuration
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        self.search_engine_id = getattr(settings, 'GOOGLE_SEARCH_ENGINE_ID', None)
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        if not self.api_key or not self.search_engine_id:
            logger.warning("Google API credentials not configured")
    
    async def get_platform_name(self) -> str:
        return "google"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search Google using Custom Search API
        """
        if not self.api_key or not self.search_engine_id:
            logger.warning("Google API not configured, using fallback search")
            return await self._fallback_search(query, limit)
        
        results = []
        
        try:
            # Google Custom Search API allows max 10 results per request
            # Make multiple requests if needed
            pages_needed = min((limit + 9) // 10, 10)  # Max 10 pages (100 results)
            
            for page in range(pages_needed):
                start_index = page * 10 + 1
                
                params = {
                    'key': self.api_key,
                    'cx': self.search_engine_id,
                    'q': query,
                    'start': start_index,
                    'num': min(10, limit - len(results)),
                    'searchType': 'image' if kwargs.get('search_images') else None,
                    'safe': 'off',  # Allow adult content
                    'gl': self.region.get('country_code', 'us').lower() if self.region else 'us',
                    'lr': f"lang_{self.region.get('country_code', 'us').lower()}" if self.region else None
                }
                
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}
                
                response_data = await self._fetch_json(self.base_url, params=params)
                
                if not response_data:
                    logger.warning(f"No response from Google API for query: {query}")
                    break
                
                if 'items' not in response_data:
                    logger.info(f"No results found for query: {query}")
                    break
                
                # Process search results
                for item in response_data['items']:
                    scan_result = await self._process_google_result(item, query)
                    if scan_result:
                        results.append(scan_result)
                        
                        if len(results) >= limit:
                            break
                
                if len(results) >= limit:
                    break
                
                # Small delay between API requests
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Google search error for query '{query}': {e}")
            # Fall back to web scraping if API fails
            return await self._fallback_search(query, limit)
        
        logger.info(f"Google search found {len(results)} results for query: {query}")
        return results
    
    async def _process_google_result(self, item: Dict[str, Any], query: str) -> Optional[ScanResult]:
        """Process individual Google search result"""
        try:
            url = item.get('link', '')
            if not url:
                return None
            
            # Extract basic information
            title = item.get('title', '')
            description = item.get('snippet', '')
            
            # Extract image information if available
            image_url = None
            if 'pagemap' in item and 'cse_image' in item['pagemap']:
                images = item['pagemap']['cse_image']
                if images:
                    image_url = images[0].get('src')
            
            # Check if this is an image result
            if item.get('mime') and item['mime'].startswith('image/'):
                image_url = url
            
            # Extract thumbnail
            thumbnail_url = None
            if 'pagemap' in item and 'cse_thumbnail' in item['pagemap']:
                thumbnails = item['pagemap']['cse_thumbnail']
                if thumbnails:
                    thumbnail_url = thumbnails[0].get('src')
            
            # Build media URLs list
            media_urls = []
            if image_url:
                media_urls.append(image_url)
            
            # Additional media from pagemap
            if 'pagemap' in item:
                pagemap = item['pagemap']
                
                # Extract images from various sources
                for image_source in ['imageobject', 'product', 'organization']:
                    if image_source in pagemap:
                        for img_item in pagemap[image_source]:
                            img_url = img_item.get('image') or img_item.get('logo')
                            if img_url and self._is_valid_media_url(img_url):
                                media_urls.append(img_url)
            
            # Extract metadata
            metadata = {
                'google_result_kind': item.get('kind', ''),
                'cache_id': item.get('cacheId', ''),
                'formatted_url': item.get('formattedUrl', ''),
                'html_formatted_url': item.get('htmlFormattedUrl', ''),
                'display_link': item.get('displayLink', ''),
                'html_title': item.get('htmlTitle', ''),
                'html_snippet': item.get('htmlSnippet', ''),
            }
            
            # Calculate confidence score based on relevance
            confidence_score = self._calculate_google_relevance(item, query)
            
            return ScanResult(
                url=url,
                platform="google",
                title=self._clean_text(title),
                description=self._clean_text(description),
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                media_urls=list(set(media_urls)),  # Remove duplicates
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing Google result: {e}")
            return None
    
    def _calculate_google_relevance(self, item: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for Google result"""
        score = 0.5  # Base score
        
        query_terms = query.lower().split()
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()
        url = item.get('link', '').lower()
        
        # Score based on query term matches
        for term in query_terms:
            if term in title:
                score += 0.3
            if term in snippet:
                score += 0.2
            if term in url:
                score += 0.1
        
        # Boost score for adult content sites (likely to have leaked content)
        adult_domains = [
            'pornhub', 'xvideos', 'xhamster', 'redtube', 'youporn', 
            'onlyfans', 'manyvids', 'clips4sale', 'iwantclips',
            'telegram', 'discord', 'reddit'
        ]
        
        for domain in adult_domains:
            if domain in url:
                score += 0.4
                break
        
        # Boost for leak-related terms
        leak_terms = ['leaked', 'leak', 'free', 'mega', 'download', 'onlyfans']
        content_text = f"{title} {snippet}"
        
        for term in leak_terms:
            if term in content_text:
                score += 0.3
        
        return min(score, 1.0)
    
    async def _fallback_search(self, query: str, limit: int) -> List[ScanResult]:
        """
        Fallback search using web scraping when API is not available
        """
        results = []
        
        try:
            # Use DuckDuckGo as fallback (no API required)
            search_url = f"https://duckduckgo.com/html/"
            params = {
                'q': query,
                'kl': self.region.get('country_code', 'us-en').lower() if self.region else 'us-en'
            }
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            html_content = await self._fetch_html(search_url, params=params, headers=headers)
            
            if html_content:
                results = await self._parse_search_results(html_content, query, limit)
            
        except Exception as e:
            logger.error(f"Fallback search error: {e}")
        
        return results
    
    async def _parse_search_results(self, html_content: str, query: str, limit: int) -> List[ScanResult]:
        """Parse search results from HTML content"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find result divs (DuckDuckGo structure)
            result_divs = soup.find_all('div', class_='result')[:limit]
            
            for div in result_divs:
                try:
                    # Extract URL
                    link_elem = div.find('a', class_='result__a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    url = link_elem['href']
                    title = link_elem.get_text(strip=True)
                    
                    # Extract description
                    desc_elem = div.find('div', class_='result__snippet')
                    description = desc_elem.get_text(strip=True) if desc_elem else ''
                    
                    # Calculate simple relevance score
                    confidence_score = self._calculate_relevance_score(
                        ScanResult(url=url, platform="google", title=title, description=description),
                        query,
                        query.split()
                    )
                    
                    result = ScanResult(
                        url=url,
                        platform="google",
                        title=self._clean_text(title),
                        description=self._clean_text(description),
                        search_query=query,
                        region=self.region.get('region_id') if self.region else None,
                        confidence_score=confidence_score,
                        metadata={'source': 'fallback_search'}
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error parsing search result: {e}")
                    continue
        
        except ImportError:
            logger.warning("BeautifulSoup not available for fallback search")
        except Exception as e:
            logger.error(f"Error parsing search results HTML: {e}")
        
        return results
    
    async def search_images(
        self,
        query: str,
        limit: int = 50,
        **kwargs
    ) -> List[ScanResult]:
        """Specialized image search"""
        return await self.search(query, limit=limit, search_images=True, **kwargs)
    
    async def search_site(
        self,
        query: str,
        site: str,
        limit: int = 50,
        **kwargs
    ) -> List[ScanResult]:
        """Search within a specific site"""
        site_query = f"site:{site} {query}"
        return await self.search(site_query, limit=limit, **kwargs)
    
    async def health_check(self) -> bool:
        """Check if Google scanner is healthy"""
        try:
            if not self.api_key or not self.search_engine_id:
                # Test fallback search
                results = await self._fallback_search("test", 1)
                return len(results) > 0
            else:
                # Test API
                results = await self.search("test", limit=1)
                return len(results) > 0
        except Exception as e:
            logger.error(f"Google scanner health check failed: {e}")
            return False