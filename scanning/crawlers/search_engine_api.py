"""
Search engine API integrations for Google Custom Search and Bing Search.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlencode, quote_plus
import json

import aiohttp
import backoff
import structlog
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from aiohttp import ClientTimeout, ClientError

from ..config import ScannerSettings


logger = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    """Represents a search result from any search engine."""
    
    title: str
    url: str
    snippet: str
    source_engine: str
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    domain: str = ""
    relevance_score: float = 0.0
    
    def __post_init__(self):
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.domain = parsed.netloc.lower()
        except Exception as e:
            logger.warning("Failed to parse domain from URL", url=self.url, error=str(e))
            self.domain = "unknown"


class SearchEngineAPI(ABC):
    """Abstract base class for search engine APIs."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(settings.concurrent_requests)
        
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'AutoDMCA Scanner/1.0 (Content Protection Service)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        num_results: int = 10,
        search_type: str = "web",
        **kwargs
    ) -> List[SearchResult]:
        """Perform a search and return results."""
        pass
    
    @abstractmethod 
    async def image_search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform an image search and return results."""
        pass
    
    async def bulk_search(
        self,
        queries: List[str],
        num_results_per_query: int = 10,
        search_type: str = "web"
    ) -> Dict[str, List[SearchResult]]:
        """Perform multiple searches concurrently."""
        async def search_single(query: str) -> tuple[str, List[SearchResult]]:
            try:
                if search_type == "image":
                    results = await self.image_search(query, num_results_per_query)
                else:
                    results = await self.search(query, num_results_per_query, search_type)
                return query, results
            except Exception as e:
                logger.error(f"Search failed for query: {query}", error=str(e))
                return query, []
        
        tasks = [search_single(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            query: search_results 
            for query, search_results in results 
            if not isinstance(search_results, Exception)
        }


class GoogleSearchAPI(SearchEngineAPI):
    """Google Custom Search API integration."""
    
    def __init__(self, settings: ScannerSettings):
        super().__init__(settings)
        if not settings.google_api_key:
            raise ValueError("Google API key is required")
        if not settings.google_search_engine_id:
            raise ValueError("Google Search Engine ID is required")
        
        self.api_key = settings.google_api_key
        self.search_engine_id = settings.google_search_engine_id
        self.service = None
        
    def _build_service(self):
        """Build Google API service client."""
        if not self.service:
            self.service = build('customsearch', 'v1', developerKey=self.api_key)
        return self.service
    
    @backoff.on_exception(
        backoff.expo,
        (HttpError, ConnectionError),
        max_tries=3,
        max_time=60
    )
    async def search(
        self,
        query: str,
        num_results: int = 10, 
        search_type: str = "web",
        safe: str = "off",
        **kwargs
    ) -> List[SearchResult]:
        """Perform Google Custom Search."""
        async with self.rate_limiter:
            try:
                service = self._build_service()
                
                # Google CSE returns max 10 results per request
                start_index = kwargs.get('start_index', 1)
                
                search_params = {
                    'q': query,
                    'cx': self.search_engine_id,
                    'num': min(num_results, 10),
                    'start': start_index,
                    'safe': safe
                }
                
                if search_type == "image":
                    search_params['searchType'] = 'image'
                
                # Execute search in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: service.cse().list(**search_params).execute()
                )
                
                results = []
                for item in response.get('items', []):
                    result = SearchResult(
                        title=item.get('title', ''),
                        url=item.get('link', ''),
                        snippet=item.get('snippet', ''),
                        source_engine='google',
                        image_url=item.get('link') if search_type == 'image' else None,
                        thumbnail_url=item.get('image', {}).get('thumbnailLink') if search_type == 'image' else None
                    )
                    results.append(result)
                
                logger.info(
                    "Google search completed",
                    query=query,
                    results_count=len(results),
                    search_type=search_type
                )
                
                return results
                
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    logger.warning("Google API rate limit exceeded", query=query)
                    await asyncio.sleep(60)  # Wait 1 minute
                    raise
                else:
                    logger.error("Google API error", error=str(e), query=query)
                    raise
            except Exception as e:
                logger.error("Google search failed", error=str(e), query=query)
                raise
    
    async def image_search(
        self,
        query: str,
        num_results: int = 10,
        image_size: str = "large",
        image_type: str = "photo",
        **kwargs
    ) -> List[SearchResult]:
        """Perform Google Image Search."""
        return await self.search(
            query=query,
            num_results=num_results,
            search_type="image",
            imgSize=image_size,
            imgType=image_type,
            **kwargs
        )


class BingSearchAPI(SearchEngineAPI):
    """Bing Search API integration."""
    
    def __init__(self, settings: ScannerSettings):
        super().__init__(settings)
        if not settings.bing_api_key:
            raise ValueError("Bing API key is required")
        
        self.api_key = settings.bing_api_key
        self.base_url = "https://api.bing.microsoft.com/v7.0"
        
    @backoff.on_exception(
        backoff.expo,
        (ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "web",
        market: str = "en-US",
        safe_search: str = "Off",
        **kwargs
    ) -> List[SearchResult]:
        """Perform Bing Web Search.""" 
        async with self.rate_limiter:
            try:
                headers = {
                    'Ocp-Apim-Subscription-Key': self.api_key,
                    'User-Agent': 'AutoDMCA Scanner/1.0'
                }
                
                params = {
                    'q': query,
                    'count': min(num_results, 50),  # Bing allows up to 50
                    'mkt': market,
                    'safeSearch': safe_search,
                    'textDecorations': 'false',
                    'textFormat': 'Raw'
                }
                
                offset = kwargs.get('offset', 0)
                if offset:
                    params['offset'] = offset
                
                endpoint = f"{self.base_url}/search"
                
                async with self.session.get(endpoint, headers=headers, params=params) as response:
                    if response.status == 429:  # Rate limit
                        logger.warning("Bing API rate limit exceeded", query=query)
                        retry_after = int(response.headers.get('Retry-After', 60))
                        await asyncio.sleep(retry_after)
                        raise ClientError("Rate limit exceeded")
                    
                    response.raise_for_status()
                    data = await response.json()
                
                results = []
                for item in data.get('webPages', {}).get('value', []):
                    result = SearchResult(
                        title=item.get('name', ''),
                        url=item.get('url', ''),
                        snippet=item.get('snippet', ''),
                        source_engine='bing'
                    )
                    results.append(result)
                
                logger.info(
                    "Bing search completed",
                    query=query,
                    results_count=len(results)
                )
                
                return results
                
            except Exception as e:
                logger.error("Bing search failed", error=str(e), query=query)
                raise
    
    async def image_search(
        self,
        query: str,
        num_results: int = 10,
        size: str = "Large",
        image_type: str = "Photo",
        **kwargs
    ) -> List[SearchResult]:
        """Perform Bing Image Search."""
        async with self.rate_limiter:
            try:
                headers = {
                    'Ocp-Apim-Subscription-Key': self.api_key,
                    'User-Agent': 'AutoDMCA Scanner/1.0'
                }
                
                params = {
                    'q': query,
                    'count': min(num_results, 35),  # Bing images max 35
                    'size': size,
                    'imageType': image_type,
                    'safeSearch': 'Off'
                }
                
                offset = kwargs.get('offset', 0)
                if offset:
                    params['offset'] = offset
                
                endpoint = f"{self.base_url}/images/search"
                
                async with self.session.get(endpoint, headers=headers, params=params) as response:
                    if response.status == 429:
                        logger.warning("Bing Images API rate limit exceeded", query=query)
                        retry_after = int(response.headers.get('Retry-After', 60))
                        await asyncio.sleep(retry_after)
                        raise ClientError("Rate limit exceeded")
                    
                    response.raise_for_status()
                    data = await response.json()
                
                results = []
                for item in data.get('value', []):
                    result = SearchResult(
                        title=item.get('name', ''),
                        url=item.get('contentUrl', ''),
                        snippet=item.get('name', ''),
                        source_engine='bing',
                        image_url=item.get('contentUrl'),
                        thumbnail_url=item.get('thumbnailUrl')
                    )
                    results.append(result)
                
                logger.info(
                    "Bing image search completed", 
                    query=query,
                    results_count=len(results)
                )
                
                return results
                
            except Exception as e:
                logger.error("Bing image search failed", error=str(e), query=query)
                raise
    
    async def news_search(
        self,
        query: str,
        num_results: int = 10,
        market: str = "en-US",
        freshness: str = "Day"
    ) -> List[SearchResult]:
        """Perform Bing News Search (useful for finding recent mentions)."""
        async with self.rate_limiter:
            try:
                headers = {
                    'Ocp-Apim-Subscription-Key': self.api_key,
                    'User-Agent': 'AutoDMCA Scanner/1.0'
                }
                
                params = {
                    'q': query,
                    'count': min(num_results, 100),
                    'mkt': market,
                    'freshness': freshness,
                    'safeSearch': 'Off'
                }
                
                endpoint = f"{self.base_url}/news/search"
                
                async with self.session.get(endpoint, headers=headers, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                
                results = []
                for item in data.get('value', []):
                    result = SearchResult(
                        title=item.get('name', ''),
                        url=item.get('url', ''),
                        snippet=item.get('description', ''),
                        source_engine='bing_news'
                    )
                    results.append(result)
                
                logger.info(
                    "Bing news search completed",
                    query=query,
                    results_count=len(results)
                )
                
                return results
                
            except Exception as e:
                logger.error("Bing news search failed", error=str(e), query=query)
                raise


class SearchEngineManager:
    """Manages multiple search engines and aggregates results."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.engines = []
        
        # Initialize available search engines
        if settings.google_api_key and settings.google_search_engine_id:
            self.engines.append(("google", GoogleSearchAPI(settings)))
        
        if settings.bing_api_key:
            self.engines.append(("bing", BingSearchAPI(settings)))
        
        if not self.engines:
            logger.warning("No search engines configured")
    
    async def search_all(
        self,
        query: str,
        num_results_per_engine: int = 10,
        search_type: str = "web"
    ) -> List[SearchResult]:
        """Search across all configured engines and aggregate results."""
        all_results = []
        
        async def search_engine(name: str, engine: SearchEngineAPI) -> List[SearchResult]:
            try:
                async with engine:
                    if search_type == "image":
                        return await engine.image_search(query, num_results_per_engine)
                    else:
                        return await engine.search(query, num_results_per_engine, search_type)
            except Exception as e:
                logger.error(f"Search failed on {name}", error=str(e), query=query)
                return []
        
        # Execute searches concurrently
        tasks = [search_engine(name, engine) for name, engine in self.engines]
        engine_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for results in engine_results:
            if isinstance(results, list):
                all_results.extend(results)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        # Sort by relevance (placeholder - could implement more sophisticated scoring)
        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(
            "Aggregated search completed",
            query=query,
            total_results=len(unique_results),
            engines_used=len(self.engines)
        )
        
        return unique_results