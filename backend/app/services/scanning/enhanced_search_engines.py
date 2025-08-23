"""
Enhanced Search Engine Integration
Comprehensive search engine integration including Google Custom Search, Bing, and others
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
from urllib.parse import quote_plus, urljoin
import hashlib

from .platforms.base_scanner import BaseScanner, ScanResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class EnhancedSearchEngineScanner:
    """
    Enhanced search engine scanner that coordinates multiple search engines
    PRD: "Search Engine Integration" with Google Custom Search API and Bing Web Search API
    """
    
    def __init__(self):
        self.google_scanner = GoogleCustomSearchScanner()
        self.bing_scanner = BingWebSearchScanner() 
        self.yandex_scanner = YandexSearchScanner()
        self.duckduckgo_scanner = DuckDuckGoSearchScanner()
        
        self.search_engines = [
            self.google_scanner,
            self.bing_scanner,
            self.yandex_scanner,
            self.duckduckgo_scanner
        ]
        
        # Search query generation patterns
        self.query_patterns = [
            '"{username}"',
            '"{username}" leaked',
            '"{username}" onlyfans',
            '"{username}" content',
            '"{username}" exclusive',
            '"{username}" premium',
            'site:reddit.com "{username}"',
            'site:telegram.me "{username}"',
            'site:discord.gg "{username}"',
            'filetype:jpg "{username}"',
            'filetype:mp4 "{username}"',
        ]
    
    async def comprehensive_search(
        self,
        profile_data: Dict[str, Any],
        limit_per_engine: int = 25,
        include_metadata: bool = True
    ) -> Dict[str, List[ScanResult]]:
        """
        Perform comprehensive search across all search engines
        """
        username = profile_data.get('username', '')
        aliases = profile_data.get('aliases', [])
        
        if not username:
            logger.warning("No username provided for search")
            return {}
        
        results = {}
        search_terms = [username] + aliases[:3]  # Limit aliases to avoid too many queries
        
        try:
            # Generate search queries
            queries = self._generate_search_queries(search_terms)
            
            # Search each engine
            for engine in self.search_engines:
                if not await engine.health_check():
                    logger.warning(f"Skipping unhealthy search engine: {engine.__class__.__name__}")
                    continue
                
                engine_results = []
                
                for query in queries[:5]:  # Limit queries per engine
                    try:
                        query_results = await engine.search(
                            query=query,
                            limit=limit_per_engine // len(queries[:5]),
                            include_metadata=include_metadata
                        )
                        engine_results.extend(query_results)
                        
                        # Small delay between queries
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Query error on {engine.__class__.__name__}: {e}")
                        continue
                
                # Deduplicate and sort results
                engine_results = self._deduplicate_results(engine_results)
                engine_results.sort(key=lambda x: x.confidence_score, reverse=True)
                
                results[engine.get_platform_name()] = engine_results[:limit_per_engine]
                
                logger.info(f"Found {len(engine_results)} results from {engine.__class__.__name__}")
        
        except Exception as e:
            logger.error(f"Comprehensive search error: {e}")
        
        return results
    
    def _generate_search_queries(self, search_terms: List[str]) -> List[str]:
        """Generate comprehensive search queries"""
        queries = []
        
        for term in search_terms:
            for pattern in self.query_patterns:
                query = pattern.format(username=term)
                queries.append(query)
        
        # Add general leak searches
        for term in search_terms:
            queries.extend([
                f"{term} leak mega",
                f"{term} onlyfans leak",
                f"{term} premium content free",
                f"{term} telegram channel",
                f"{term} discord server"
            ])
        
        return list(set(queries))  # Remove duplicates
    
    def _deduplicate_results(self, results: List[ScanResult]) -> List[ScanResult]:
        """Remove duplicate results based on URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url_hash = hashlib.md5(result.url.encode()).hexdigest()
            if url_hash not in seen_urls:
                seen_urls.add(url_hash)
                unique_results.append(result)
        
        return unique_results
    
    async def targeted_leak_search(
        self,
        username: str,
        platforms: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[ScanResult]:
        """
        Targeted search for leaked content
        """
        results = []
        
        # Specific leak-focused queries
        leak_queries = [
            f'"{username}" leaked onlyfans',
            f'"{username}" content leak',
            f'"{username}" mega link',
            f'"{username}" telegram leak',
            f'site:reddit.com "{username}" leak',
            f'site:discord.gg "{username}"',
            f'"{username}" premium free download'
        ]
        
        # Use Google and Bing for targeted searches
        target_engines = [self.google_scanner, self.bing_scanner]
        
        for engine in target_engines:
            try:
                if not await engine.health_check():
                    continue
                
                for query in leak_queries:
                    query_results = await engine.search(
                        query=query,
                        limit=10,
                        include_metadata=True
                    )
                    
                    # Filter for high-confidence results
                    high_confidence = [
                        r for r in query_results 
                        if r.confidence_score > 0.7
                    ]
                    
                    results.extend(high_confidence)
                    await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Targeted leak search error on {engine.__class__.__name__}: {e}")
                continue
        
        # Deduplicate and sort
        results = self._deduplicate_results(results)
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return results[:limit]
    
    async def reverse_image_search(
        self,
        image_urls: List[str],
        limit: int = 25
    ) -> List[ScanResult]:
        """
        Perform reverse image search to find where images appear
        """
        results = []
        
        # Google reverse image search (requires special handling)
        for image_url in image_urls[:5]:  # Limit to avoid overwhelming
            try:
                # Google reverse image search query
                query = f"imageurl:{image_url}"
                
                google_results = await self.google_scanner.search(
                    query=query,
                    limit=limit // len(image_urls[:5]),
                    search_images=True
                )
                
                results.extend(google_results)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Reverse image search error for {image_url}: {e}")
                continue
        
        return results[:limit]
    
    async def monitor_new_indexed_content(
        self,
        username: str,
        last_check: datetime,
        limit: int = 50
    ) -> List[ScanResult]:
        """
        Monitor for newly indexed content since last check
        """
        results = []
        
        # Date-restricted queries (Google supports date filtering)
        queries = [
            f'"{username}" after:{last_check.strftime("%Y-%m-%d")}',
            f'"{username}" leaked after:{last_check.strftime("%Y-%m-%d")}',
        ]
        
        for query in queries:
            try:
                google_results = await self.google_scanner.search(
                    query=query,
                    limit=limit // len(queries),
                    include_metadata=True
                )
                
                results.extend(google_results)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"New content monitoring error: {e}")
                continue
        
        return results[:limit]


class GoogleCustomSearchScanner(BaseScanner):
    """Enhanced Google Custom Search implementation"""
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=100, **kwargs)
        
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        self.search_engine_id = getattr(settings, 'GOOGLE_SEARCH_ENGINE_ID', None)
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    async def get_platform_name(self) -> str:
        return "google_enhanced"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """Enhanced Google search with additional parameters"""
        
        if not self.api_key or not self.search_engine_id:
            return []
        
        results = []
        search_images = kwargs.get('search_images', False)
        
        try:
            pages_needed = min((limit + 9) // 10, 10)
            
            for page in range(pages_needed):
                start_index = page * 10 + 1
                
                params = {
                    'key': self.api_key,
                    'cx': self.search_engine_id,
                    'q': query,
                    'start': start_index,
                    'num': min(10, limit - len(results)),
                    'safe': 'off',
                    'gl': self.region.get('country_code', 'us').lower() if self.region else 'us',
                    'lr': f"lang_{self.region.get('country_code', 'us').lower()}" if self.region else None
                }
                
                # Add search type if specified
                if search_images:
                    params['searchType'] = 'image'
                
                # Add date restriction if specified
                if kwargs.get('date_restrict'):
                    params['dateRestrict'] = kwargs['date_restrict']
                
                # Add site restriction if specified  
                if kwargs.get('site_search'):
                    params['siteSearch'] = kwargs['site_search']
                
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}
                
                response_data = await self._fetch_json(self.base_url, params=params)
                
                if not response_data or 'items' not in response_data:
                    break
                
                for item in response_data['items']:
                    scan_result = self._process_enhanced_google_result(item, query)
                    if scan_result:
                        results.append(scan_result)
                        
                        if len(results) >= limit:
                            break
                
                if len(results) >= limit:
                    break
                
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Enhanced Google search error: {e}")
        
        return results
    
    def _process_enhanced_google_result(self, item: Dict[str, Any], query: str) -> Optional[ScanResult]:
        """Enhanced Google result processing with better metadata extraction"""
        try:
            url = item.get('link', '')
            if not url:
                return None
            
            title = item.get('title', '')
            description = item.get('snippet', '')
            
            # Enhanced media extraction
            media_urls = []
            image_url = None
            
            # Check for image results
            if item.get('mime') and item['mime'].startswith('image/'):
                image_url = url
                media_urls.append(url)
            
            # Extract from pagemap with better logic
            if 'pagemap' in item:
                pagemap = item['pagemap']
                
                # Extract images from multiple sources
                image_sources = ['cse_image', 'imageobject', 'product', 'organization', 'person']
                for source in image_sources:
                    if source in pagemap:
                        for img_item in pagemap[source]:
                            img_url = img_item.get('src') or img_item.get('image') or img_item.get('logo')
                            if img_url and self._is_valid_media_url(img_url):
                                media_urls.append(img_url)
                                if not image_url:
                                    image_url = img_url
                
                # Extract video URLs
                if 'videoobject' in pagemap:
                    for video_item in pagemap['videoobject']:
                        video_url = video_item.get('contenturl') or video_item.get('embedurl')
                        if video_url and self._is_valid_media_url(video_url):
                            media_urls.append(video_url)
            
            # Enhanced relevance scoring
            confidence_score = self._calculate_enhanced_google_relevance(item, query)
            
            # Enhanced metadata
            metadata = {
                'google_result_kind': item.get('kind', ''),
                'cache_id': item.get('cacheId', ''),
                'display_link': item.get('displayLink', ''),
                'file_format': item.get('fileFormat', ''),
                'mime_type': item.get('mime', ''),
                'image_context_link': item.get('image', {}).get('contextLink') if item.get('image') else None,
                'has_pagemap': 'pagemap' in item,
                'pagemap_types': list(item.get('pagemap', {}).keys()) if 'pagemap' in item else []
            }
            
            return ScanResult(
                url=url,
                platform="google_enhanced",
                title=self._clean_text(title),
                description=self._clean_text(description),
                image_url=image_url,
                media_urls=list(set(media_urls)),
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing enhanced Google result: {e}")
            return None
    
    def _calculate_enhanced_google_relevance(self, item: Dict[str, Any], query: str) -> float:
        """Enhanced Google relevance calculation"""
        score = 0.5
        
        query_terms = query.lower().split()
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()
        url = item.get('link', '').lower()
        
        # Basic term matching
        for term in query_terms:
            if term in title:
                score += 0.3
            if term in snippet:
                score += 0.2
            if term in url:
                score += 0.1
        
        # Boost for adult content domains
        high_value_domains = [
            'reddit.com', 'telegram', 'discord', 'mega.nz', 'drive.google',
            'pornhub', 'xvideos', 'onlyfans', 'manyvids', 'clips4sale'
        ]
        
        for domain in high_value_domains:
            if domain in url:
                score += 0.4
                break
        
        # Boost for leak indicators
        leak_terms = ['leaked', 'leak', 'free', 'download', 'exclusive', 'premium']
        content_text = f"{title} {snippet}"
        
        for term in leak_terms:
            if term in content_text:
                score += 0.2
        
        # Boost for media content
        if item.get('mime', '').startswith(('image/', 'video/')):
            score += 0.3
        
        # Boost for rich pagemap data
        if 'pagemap' in item and len(item['pagemap']) > 2:
            score += 0.1
        
        return min(score, 1.0)


class BingWebSearchScanner(BaseScanner):
    """Bing Web Search API implementation"""
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=60, **kwargs)
        
        self.subscription_key = getattr(settings, 'BING_SUBSCRIPTION_KEY', None)
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
    
    async def get_platform_name(self) -> str:
        return "bing"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """Search using Bing Web Search API"""
        
        if not self.subscription_key:
            return []
        
        results = []
        
        try:
            params = {
                'q': query,
                'count': min(limit, 50),  # Bing API limit
                'offset': 0,
                'mkt': self.region.get('market', 'en-US') if self.region else 'en-US',
                'safesearch': 'Off',  # Allow adult content
                'responseFilter': 'Webpages,Images,Videos'
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            response_data = await self._fetch_json(
                self.base_url, 
                params=params, 
                headers=headers
            )
            
            if response_data:
                # Process web results
                if 'webPages' in response_data and 'value' in response_data['webPages']:
                    for item in response_data['webPages']['value']:
                        scan_result = self._process_bing_result(item, query, 'web')
                        if scan_result:
                            results.append(scan_result)
                
                # Process image results
                if 'images' in response_data and 'value' in response_data['images']:
                    for item in response_data['images']['value']:
                        scan_result = self._process_bing_result(item, query, 'image')
                        if scan_result:
                            results.append(scan_result)
                
                # Process video results
                if 'videos' in response_data and 'value' in response_data['videos']:
                    for item in response_data['videos']['value']:
                        scan_result = self._process_bing_result(item, query, 'video')
                        if scan_result:
                            results.append(scan_result)
        
        except Exception as e:
            logger.error(f"Bing search error: {e}")
        
        return results[:limit]
    
    def _process_bing_result(self, item: Dict[str, Any], query: str, result_type: str) -> Optional[ScanResult]:
        """Process Bing search result"""
        try:
            url = item.get('url') or item.get('webSearchUrl', '')
            if not url:
                return None
            
            title = item.get('name', '')
            description = item.get('snippet', '')
            
            # Type-specific processing
            image_url = None
            video_url = None
            media_urls = []
            
            if result_type == 'image':
                image_url = item.get('contentUrl', url)
                media_urls.append(image_url)
            elif result_type == 'video':
                video_url = item.get('contentUrl', url)
                media_urls.append(video_url)
                # Add thumbnail if available
                if item.get('thumbnailUrl'):
                    media_urls.append(item['thumbnailUrl'])
            
            # Calculate confidence
            confidence_score = self._calculate_bing_relevance(item, query, result_type)
            
            # Build metadata
            metadata = {
                'result_type': result_type,
                'date_published': item.get('datePublished'),
                'publisher': item.get('provider', [{}])[0].get('name') if item.get('provider') else None,
                'content_size': item.get('contentSize'),
                'encoding_format': item.get('encodingFormat'),
                'thumbnail_url': item.get('thumbnailUrl')
            }
            
            return ScanResult(
                url=url,
                platform="bing",
                title=self._clean_text(title),
                description=self._clean_text(description),
                image_url=image_url,
                video_url=video_url,
                media_urls=media_urls,
                search_query=query,
                region=self.region.get('region_id') if self.region else None,
                confidence_score=confidence_score,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing Bing result: {e}")
            return None
    
    def _calculate_bing_relevance(self, item: Dict[str, Any], query: str, result_type: str) -> float:
        """Calculate Bing result relevance"""
        score = 0.5
        
        query_terms = query.lower().split()
        title = item.get('name', '').lower()
        snippet = item.get('snippet', '').lower()
        url = item.get('url', '').lower()
        
        # Term matching
        for term in query_terms:
            if term in title:
                score += 0.3
            if term in snippet:
                score += 0.2
            if term in url:
                score += 0.1
        
        # Boost for media content
        if result_type in ['image', 'video']:
            score += 0.2
        
        # Boost for high-value domains
        high_value_domains = ['reddit', 'telegram', 'discord', 'mega', 'pornhub', 'onlyfans']
        for domain in high_value_domains:
            if domain in url:
                score += 0.3
                break
        
        return min(score, 1.0)


class YandexSearchScanner(BaseScanner):
    """Yandex search implementation for Russian/Eastern European regions"""
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=30, **kwargs)
        
        # Yandex doesn't have a free API, so we'll use web scraping
        self.base_url = "https://yandex.com/search"
    
    async def get_platform_name(self) -> str:
        return "yandex"
    
    async def search(self, query: str, limit: int = 50, **kwargs) -> List[ScanResult]:
        """Yandex search via web scraping"""
        # Simplified implementation - Yandex has strong anti-bot measures
        logger.info(f"Yandex search would target query: {query}")
        return []


class DuckDuckGoSearchScanner(BaseScanner):
    """DuckDuckGo search implementation"""
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=30, **kwargs)
        
        self.base_url = "https://duckduckgo.com/html/"
    
    async def get_platform_name(self) -> str:
        return "duckduckgo"
    
    async def search(self, query: str, limit: int = 50, **kwargs) -> List[ScanResult]:
        """DuckDuckGo search via web interface"""
        results = []
        
        try:
            params = {
                'q': query,
                'kl': self.region.get('country_code', 'us-en').lower() if self.region else 'us-en'
            }
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1'
            }
            
            html_content = await self._fetch_html(self.base_url, params=params, headers=headers)
            
            if html_content:
                results = await self._parse_duckduckgo_results(html_content, query, limit)
        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return results
    
    async def _parse_duckduckgo_results(self, html_content: str, query: str, limit: int) -> List[ScanResult]:
        """Parse DuckDuckGo results from HTML"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            result_divs = soup.find_all('div', class_='result')[:limit]
            
            for div in result_divs:
                try:
                    link_elem = div.find('a', class_='result__a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    url = link_elem['href']
                    title = link_elem.get_text(strip=True)
                    
                    desc_elem = div.find('div', class_='result__snippet')
                    description = desc_elem.get_text(strip=True) if desc_elem else ''
                    
                    confidence_score = self._calculate_relevance_score(
                        ScanResult(url=url, platform="duckduckgo", title=title, description=description),
                        query,
                        query.split()
                    )
                    
                    result = ScanResult(
                        url=url,
                        platform="duckduckgo",
                        title=self._clean_text(title),
                        description=self._clean_text(description),
                        search_query=query,
                        region=self.region.get('region_id') if self.region else None,
                        confidence_score=confidence_score,
                        metadata={'source': 'web_scraping'}
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error parsing DuckDuckGo result: {e}")
                    continue
        
        except ImportError:
            logger.warning("BeautifulSoup not available for DuckDuckGo parsing")
        except Exception as e:
            logger.error(f"Error parsing DuckDuckGo results: {e}")
        
        return results