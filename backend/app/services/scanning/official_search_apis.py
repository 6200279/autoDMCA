"""
Official Search APIs Integration Service
Implements PRD requirement for Google Custom Search JSON API and Bing Web Search API

PRD Requirements:
- "Google Custom Search JSON API or Bing Web Search API"
- "Automated queries for terms like '<CreatorName> leaked' or known file names"
- "Stay within usage policies to avoid scraping that could get IP-blocked"
- "Search engines for initial discovery"
"""

import logging
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import quote_plus, urlparse

from app.core.config import settings
from app.services.cache.multi_level_cache import MultiLevelCache

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """Supported search engines"""
    GOOGLE = "google"
    BING = "bing"
    YAHOO = "yahoo"  # Future support
    DUCKDUCKGO = "duckduckgo"  # Future support


class SearchResultType(str, Enum):
    """Types of search results"""
    GENERAL = "general"
    IMAGE = "image"
    VIDEO = "video"
    NEWS = "news"


@dataclass
class SearchResult:
    """Individual search result"""
    title: str
    url: str
    snippet: str
    display_url: str
    result_type: SearchResultType
    search_engine: SearchEngine
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    last_modified: Optional[datetime] = None
    rank: int = 0
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class SearchQuery:
    """Search query configuration"""
    terms: List[str]
    exact_phrase: Optional[str] = None
    exclude_terms: List[str] = None
    site_filter: Optional[str] = None  # site:example.com
    file_type: Optional[str] = None  # filetype:jpg
    date_filter: Optional[str] = None  # past week, month, year
    safe_search: bool = True
    result_count: int = 50
    result_type: SearchResultType = SearchResultType.GENERAL


class OfficialSearchAPIService:
    """
    Official Search APIs integration service
    
    Implements PRD requirements for search engine integration
    using official APIs to avoid IP blocking and stay within usage policies
    """
    
    def __init__(self, cache: Optional[MultiLevelCache] = None):
        self.cache = cache
        self.cache_ttl = 3600  # 1 hour cache for search results
        
        # API credentials from settings
        self.google_api_key = getattr(settings, 'GOOGLE_SEARCH_API_KEY', None)
        self.google_search_engine_id = getattr(settings, 'GOOGLE_SEARCH_ENGINE_ID', None)
        self.bing_api_key = getattr(settings, 'BING_SEARCH_API_KEY', None)
        
        # Rate limiting
        self.google_daily_limit = 100  # Google Custom Search free tier limit
        self.bing_monthly_limit = 1000  # Bing Search API free tier limit
        self.google_requests_today = 0
        self.bing_requests_this_month = 0
        
        # Query templates for DMCA content detection
        self.leak_query_templates = [
            '"{creator_name}" leaked',
            '"{creator_name}" onlyfans leaked',
            '"{creator_name}" content leaked',
            'download "{creator_name}" free',
            '"{creator_name}" leaked photos',
            '"{creator_name}" leaked videos',
            '"{creator_name}" mega link',
            '"{creator_name}" telegram leak',
        ]
        
        # Site patterns that commonly host leaked content
        self.common_leak_sites = [
            'reddit.com',
            'forum',
            'mega.nz', 
            'discord',
            'telegram',
            'leak',
            'free',
            'download'
        ]
    
    async def search_for_creator_content(
        self,
        creator_name: str,
        keywords: List[str],
        profile_id: str,
        search_engines: List[SearchEngine] = None,
        result_limit: int = 100
    ) -> List[SearchResult]:
        """
        Search for creator content across multiple search engines
        
        PRD: "Search for multiple terms at once...avoid duplicate work"
        """
        
        if not search_engines:
            search_engines = [SearchEngine.GOOGLE, SearchEngine.BING]
        
        all_results = []
        
        # Generate search queries based on creator name and keywords
        search_queries = self._generate_search_queries(creator_name, keywords)
        
        logger.info(f"Searching for creator '{creator_name}' with {len(search_queries)} queries across {len(search_engines)} engines")
        
        # Execute searches across multiple engines concurrently
        tasks = []
        for engine in search_engines:
            for query in search_queries:
                task = self._execute_search(engine, query, profile_id)
                tasks.append(task)
        
        # Execute all searches concurrently with rate limiting
        results = await self._execute_with_rate_limiting(tasks)
        
        # Flatten and deduplicate results
        for result_batch in results:
            if result_batch:
                all_results.extend(result_batch)
        
        # Remove duplicates based on URL
        unique_results = self._deduplicate_results(all_results)
        
        # Sort by relevance and confidence
        sorted_results = sorted(
            unique_results,
            key=lambda x: (x.confidence_score, -x.rank),
            reverse=True
        )
        
        return sorted_results[:result_limit]
    
    def _generate_search_queries(
        self, 
        creator_name: str, 
        keywords: List[str]
    ) -> List[SearchQuery]:
        """Generate comprehensive search queries for content discovery"""
        
        queries = []
        
        # Basic leak searches
        for template in self.leak_query_templates:
            query_text = template.format(creator_name=creator_name)
            
            queries.append(SearchQuery(
                terms=[query_text],
                exclude_terms=['site:onlyfans.com', 'site:patreon.com'],  # Exclude legitimate sites
                safe_search=False,  # We need to find leak content
                result_count=50
            ))
        
        # Keyword-based searches
        for keyword in keywords[:5]:  # Limit to avoid excessive API usage
            # General search with keyword
            queries.append(SearchQuery(
                terms=[f'"{creator_name}"', keyword, 'free'],
                exclude_terms=['site:onlyfans.com', 'site:patreon.com'],
                result_count=30
            ))
            
            # Image searches
            queries.append(SearchQuery(
                terms=[f'"{creator_name}"', keyword],
                result_type=SearchResultType.IMAGE,
                result_count=20
            ))
        
        # File type searches
        for file_ext in ['jpg', 'png', 'mp4', 'zip', 'rar']:
            queries.append(SearchQuery(
                terms=[f'"{creator_name}"'],
                file_type=file_ext,
                result_count=20
            ))
        
        # Site-specific searches for known leak platforms
        for site in ['reddit.com', 'forum.*', 'mega.nz']:
            queries.append(SearchQuery(
                terms=[f'"{creator_name}"', 'leaked'],
                site_filter=site,
                result_count=25
            ))
        
        return queries
    
    async def _execute_search(
        self, 
        engine: SearchEngine, 
        query: SearchQuery,
        profile_id: str
    ) -> List[SearchResult]:
        """Execute search on specified engine"""
        
        # Check cache first
        cache_key = f"search:{engine.value}:{hash(str(query))}"
        if self.cache:
            cached_results = await self.cache.get(cache_key)
            if cached_results:
                logger.debug(f"Cache hit for search: {engine.value}")
                return [SearchResult(**result) for result in cached_results]
        
        results = []
        
        try:
            if engine == SearchEngine.GOOGLE:
                results = await self._search_google(query, profile_id)
            elif engine == SearchEngine.BING:
                results = await self._search_bing(query, profile_id)
            else:
                logger.warning(f"Unsupported search engine: {engine}")
            
            # Cache results
            if self.cache and results:
                serializable_results = [
                    {
                        'title': r.title,
                        'url': r.url,
                        'snippet': r.snippet,
                        'display_url': r.display_url,
                        'result_type': r.result_type.value,
                        'search_engine': r.search_engine.value,
                        'image_url': r.image_url,
                        'video_url': r.video_url,
                        'thumbnail_url': r.thumbnail_url,
                        'rank': r.rank,
                        'confidence_score': r.confidence_score,
                        'metadata': r.metadata or {}
                    }
                    for r in results
                ]
                await self.cache.set(cache_key, serializable_results, ttl=self.cache_ttl)
            
        except Exception as e:
            logger.error(f"Search failed for {engine.value}: {e}")
        
        return results
    
    async def _search_google(self, query: SearchQuery, profile_id: str) -> List[SearchResult]:
        """Search using Google Custom Search JSON API"""
        
        if not self.google_api_key or not self.google_search_engine_id:
            logger.warning("Google Search API credentials not configured")
            return []
        
        if self.google_requests_today >= self.google_daily_limit:
            logger.warning("Google Search API daily limit exceeded")
            return []
        
        # Build query string
        query_parts = []
        
        # Main search terms
        if query.exact_phrase:
            query_parts.append(f'"{query.exact_phrase}"')
        else:
            query_parts.extend(query.terms)
        
        # Exclude terms
        if query.exclude_terms:
            for term in query.exclude_terms:
                query_parts.append(f'-{term}')
        
        # Site filter
        if query.site_filter:
            query_parts.append(f'site:{query.site_filter}')
        
        # File type filter
        if query.file_type:
            query_parts.append(f'filetype:{query.file_type}')
        
        search_query = ' '.join(query_parts)
        
        # API parameters
        params = {
            'key': self.google_api_key,
            'cx': self.google_search_engine_id,
            'q': search_query,
            'num': min(query.result_count, 10),  # Google API max 10 per request
            'safe': 'off' if not query.safe_search else 'active'
        }
        
        # Search type
        if query.result_type == SearchResultType.IMAGE:
            params['searchType'] = 'image'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://www.googleapis.com/customsearch/v1',
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self.google_requests_today += 1
                        
                        return self._parse_google_results(data, query)
                    
                    elif response.status == 403:
                        logger.warning("Google Search API quota exceeded or forbidden")
                        self.google_requests_today = self.google_daily_limit
                    
                    else:
                        logger.error(f"Google Search API error: {response.status}")
        
        except asyncio.TimeoutError:
            logger.warning("Google Search API timeout")
        except Exception as e:
            logger.error(f"Google Search API exception: {e}")
        
        return []
    
    async def _search_bing(self, query: SearchQuery, profile_id: str) -> List[SearchResult]:
        """Search using Bing Web Search API"""
        
        if not self.bing_api_key:
            logger.warning("Bing Search API credentials not configured")
            return []
        
        if self.bing_requests_this_month >= self.bing_monthly_limit:
            logger.warning("Bing Search API monthly limit exceeded")
            return []
        
        # Build query string (similar to Google)
        query_parts = []
        
        if query.exact_phrase:
            query_parts.append(f'"{query.exact_phrase}"')
        else:
            query_parts.extend(query.terms)
        
        if query.exclude_terms:
            for term in query.exclude_terms:
                query_parts.append(f'-{term}')
        
        if query.site_filter:
            query_parts.append(f'site:{query.site_filter}')
        
        if query.file_type:
            query_parts.append(f'filetype:{query.file_type}')
        
        search_query = ' '.join(query_parts)
        
        # API parameters
        params = {
            'q': search_query,
            'count': min(query.result_count, 50),  # Bing API max 50 per request
            'offset': 0,
            'mkt': 'en-US',
            'safesearch': 'Off' if not query.safe_search else 'Moderate'
        }
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key,
            'User-Agent': 'AutoDMCA-ContentScanner/1.0'
        }
        
        # Determine endpoint based on search type
        if query.result_type == SearchResultType.IMAGE:
            endpoint = 'https://api.bing.microsoft.com/v7.0/images/search'
        elif query.result_type == SearchResultType.VIDEO:
            endpoint = 'https://api.bing.microsoft.com/v7.0/videos/search'
        elif query.result_type == SearchResultType.NEWS:
            endpoint = 'https://api.bing.microsoft.com/v7.0/news/search'
        else:
            endpoint = 'https://api.bing.microsoft.com/v7.0/search'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self.bing_requests_this_month += 1
                        
                        return self._parse_bing_results(data, query)
                    
                    elif response.status == 429:
                        logger.warning("Bing Search API rate limit exceeded")
                    
                    else:
                        logger.error(f"Bing Search API error: {response.status}")
        
        except asyncio.TimeoutError:
            logger.warning("Bing Search API timeout")
        except Exception as e:
            logger.error(f"Bing Search API exception: {e}")
        
        return []
    
    def _parse_google_results(self, data: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
        """Parse Google Custom Search JSON response"""
        results = []
        
        items = data.get('items', [])
        
        for i, item in enumerate(items):
            # Calculate confidence score based on relevance indicators
            confidence = self._calculate_confidence_score(
                item.get('title', ''),
                item.get('snippet', ''),
                item.get('link', '')
            )
            
            result = SearchResult(
                title=item.get('title', ''),
                url=item.get('link', ''),
                snippet=item.get('snippet', ''),
                display_url=item.get('displayLink', ''),
                result_type=query.result_type,
                search_engine=SearchEngine.GOOGLE,
                rank=i + 1,
                confidence_score=confidence,
                metadata={
                    'htmlTitle': item.get('htmlTitle'),
                    'htmlSnippet': item.get('htmlSnippet'),
                    'cacheId': item.get('cacheId'),
                    'formattedUrl': item.get('formattedUrl')
                }
            )
            
            # Add image-specific data if available
            if query.result_type == SearchResultType.IMAGE:
                image_info = item.get('image', {})
                result.image_url = item.get('link')
                result.thumbnail_url = image_info.get('thumbnailLink')
                
                if result.metadata:
                    result.metadata.update({
                        'image_width': image_info.get('width'),
                        'image_height': image_info.get('height'),
                        'image_size': image_info.get('byteSize')
                    })
            
            results.append(result)
        
        return results
    
    def _parse_bing_results(self, data: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
        """Parse Bing Web Search API response"""
        results = []
        
        # Handle different result types
        if query.result_type == SearchResultType.IMAGE:
            items = data.get('value', [])
            for i, item in enumerate(items):
                confidence = self._calculate_confidence_score(
                    item.get('name', ''),
                    item.get('hostPageDisplayUrl', ''),
                    item.get('contentUrl', '')
                )
                
                result = SearchResult(
                    title=item.get('name', ''),
                    url=item.get('hostPageUrl', ''),
                    snippet=item.get('hostPageDisplayUrl', ''),
                    display_url=item.get('hostPageDisplayUrl', ''),
                    result_type=SearchResultType.IMAGE,
                    search_engine=SearchEngine.BING,
                    image_url=item.get('contentUrl'),
                    thumbnail_url=item.get('thumbnailUrl'),
                    rank=i + 1,
                    confidence_score=confidence,
                    metadata={
                        'width': item.get('width'),
                        'height': item.get('height'),
                        'size': item.get('contentSize'),
                        'encodingFormat': item.get('encodingFormat')
                    }
                )
                results.append(result)
        
        else:
            # Web search results
            web_pages = data.get('webPages', {}).get('value', [])
            for i, item in enumerate(web_pages):
                confidence = self._calculate_confidence_score(
                    item.get('name', ''),
                    item.get('snippet', ''),
                    item.get('url', '')
                )
                
                result = SearchResult(
                    title=item.get('name', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    display_url=item.get('displayUrl', ''),
                    result_type=SearchResultType.GENERAL,
                    search_engine=SearchEngine.BING,
                    rank=i + 1,
                    confidence_score=confidence,
                    last_modified=self._parse_date(item.get('dateLastCrawled')),
                    metadata={
                        'deepLinks': item.get('deepLinks', [])
                    }
                )
                results.append(result)
        
        return results
    
    def _calculate_confidence_score(self, title: str, snippet: str, url: str) -> float:
        """
        Calculate confidence score for search result relevance
        
        Higher scores for results more likely to contain leaked content
        """
        score = 0.0
        
        # Check for leak-related keywords in title and snippet
        leak_keywords = [
            'leaked', 'leak', 'free', 'download', 'mega', 'telegram',
            'onlyfans', 'patreon', 'exclusive', 'private', 'premium'
        ]
        
        text = f"{title} {snippet}".lower()
        
        # Score based on keyword presence
        for keyword in leak_keywords:
            if keyword in text:
                score += 0.1
        
        # Score based on URL patterns
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc
        path = parsed_url.path
        
        # Known leak platforms get higher scores
        leak_domains = ['reddit.com', 'mega.nz', 'discord', 'telegram']
        for leak_domain in leak_domains:
            if leak_domain in domain:
                score += 0.3
                break
        
        # Forum-like sites often host leaked content
        if any(indicator in domain for indicator in ['forum', 'board', 'community']):
            score += 0.2
        
        # File sharing indicators
        if any(indicator in path for indicator in ['download', 'file', 'share']):
            score += 0.15
        
        # Normalize score to 0-1 range
        return min(score, 1.0)
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            # Normalize URL for comparison
            normalized_url = result.url.lower().strip('/')
            
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
        
        return unique_results
    
    async def _execute_with_rate_limiting(self, tasks: List) -> List:
        """Execute tasks with rate limiting to respect API limits"""
        
        # Group tasks by search engine to apply per-engine rate limiting
        google_tasks = []
        bing_tasks = []
        
        for task in tasks:
            # This is a simplified approach - in practice you'd need to inspect the task
            # to determine which engine it targets
            if len(google_tasks) < 50:  # Reasonable daily limit
                google_tasks.append(task)
            else:
                bing_tasks.append(task)
        
        # Execute Google tasks with rate limiting (max 1 per second)
        google_results = []
        for task in google_tasks:
            try:
                result = await task
                google_results.append(result)
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Search task failed: {e}")
                google_results.append(None)
        
        # Execute Bing tasks with rate limiting (max 3 per second)
        bing_results = []
        bing_batch_size = 3
        for i in range(0, len(bing_tasks), bing_batch_size):
            batch = bing_tasks[i:i + bing_batch_size]
            try:
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                bing_results.extend(batch_results)
                if i + bing_batch_size < len(bing_tasks):
                    await asyncio.sleep(1)  # Rate limiting between batches
            except Exception as e:
                logger.error(f"Search batch failed: {e}")
                bing_results.extend([None] * len(batch))
        
        return google_results + bing_results
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_string:
            return None
        
        try:
            # Handle ISO format
            if 'T' in date_string:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except Exception:
            pass
        
        return None
    
    async def get_api_usage_stats(self) -> Dict[str, Any]:
        """Get current API usage statistics"""
        return {
            "google": {
                "requests_today": self.google_requests_today,
                "daily_limit": self.google_daily_limit,
                "remaining_today": max(0, self.google_daily_limit - self.google_requests_today),
                "api_configured": bool(self.google_api_key and self.google_search_engine_id)
            },
            "bing": {
                "requests_this_month": self.bing_requests_this_month,
                "monthly_limit": self.bing_monthly_limit,
                "remaining_this_month": max(0, self.bing_monthly_limit - self.bing_requests_this_month),
                "api_configured": bool(self.bing_api_key)
            }
        }


# Global instance
official_search_service = OfficialSearchAPIService()


__all__ = [
    'OfficialSearchAPIService',
    'SearchEngine',
    'SearchResultType', 
    'SearchResult',
    'SearchQuery',
    'official_search_service'
]