"""
Search Engine Integration for Content Discovery
Implements search engine APIs for finding potential infringements
"""
import asyncio
import aiohttp
import json
import os
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse
import logging
from datetime import datetime
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchEngineScanner:
    """
    Integrates with search engines for content discovery
    PRD: "leverage search engines for initial discovery"
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API Keys from environment
        self.google_api_key = os.getenv('GOOGLE_API_KEY', '')
        self.google_cx = os.getenv('GOOGLE_CUSTOM_SEARCH_ID', '')
        self.bing_api_key = os.getenv('BING_API_KEY', '')
        
        # Rate limiting
        self.last_google_request = None
        self.last_bing_request = None
        self.min_request_interval = 1.0  # seconds between requests
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def search_google(
        self, 
        query: str, 
        num_results: int = 50,
        start_index: int = 1
    ) -> List[str]:
        """
        Search Google using Custom Search API
        PRD: "use APIs or automated queries against Google"
        """
        if not self.google_api_key or not self.google_cx:
            logger.warning("Google API credentials not configured, using fallback")
            return await self._search_google_fallback(query)
            
        urls = []
        
        try:
            # Google Custom Search API has a limit of 10 results per request
            for start in range(start_index, min(start_index + num_results, 100), 10):
                await self._rate_limit_google()
                
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cx,
                    'q': query,
                    'start': start,
                    'num': min(10, num_results - len(urls))
                }
                
                async with self.session.get(
                    'https://www.googleapis.com/customsearch/v1',
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        
                        for item in items:
                            urls.append(item.get('link'))
                            
                    elif response.status == 429:
                        logger.warning("Google API rate limit reached")
                        break
                    else:
                        logger.error(f"Google API error: {response.status}")
                        break
                        
        except Exception as e:
            logger.error(f"Google search error: {e}")
            
        return urls
        
    async def search_bing(
        self, 
        query: str,
        num_results: int = 50
    ) -> List[str]:
        """
        Search Bing using Web Search API
        PRD: "automated queries against...Bing"
        """
        if not self.bing_api_key:
            logger.warning("Bing API key not configured, using fallback")
            return await self._search_bing_fallback(query)
            
        urls = []
        
        try:
            await self._rate_limit_bing()
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.bing_api_key
            }
            
            params = {
                'q': query,
                'count': min(num_results, 50),  # Bing limit
                'offset': 0,
                'mkt': 'en-US'
            }
            
            async with self.session.get(
                'https://api.bing.microsoft.com/v7.0/search',
                headers=headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    web_pages = data.get('webPages', {})
                    results = web_pages.get('value', [])
                    
                    for result in results:
                        urls.append(result.get('url'))
                        
                elif response.status == 429:
                    logger.warning("Bing API rate limit reached")
                else:
                    logger.error(f"Bing API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Bing search error: {e}")
            
        return urls
        
    async def search_google_images(
        self,
        query: str,
        num_results: int = 30
    ) -> List[str]:
        """
        Search Google Images for visual content
        PRD: "For image-based search"
        """
        if not self.google_api_key or not self.google_cx:
            return await self._search_google_images_fallback(query)
            
        urls = []
        
        try:
            await self._rate_limit_google()
            
            params = {
                'key': self.google_api_key,
                'cx': self.google_cx,
                'q': query,
                'searchType': 'image',
                'num': min(num_results, 10),  # API limit
                'imgSize': 'large',
                'safe': 'off'  # Include all content
            }
            
            async with self.session.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    
                    for item in items:
                        # Get both the image URL and the page it's on
                        urls.append(item.get('link'))  # Direct image
                        urls.append(item.get('image', {}).get('contextLink'))  # Page URL
                        
        except Exception as e:
            logger.error(f"Google Images search error: {e}")
            
        return [url for url in urls if url]  # Filter None values
        
    async def search_specific_site(
        self,
        site: str,
        query: str
    ) -> List[str]:
        """
        Search within a specific website
        """
        site_query = f'site:{site} {query}'
        
        # Try Google first
        results = await self.search_google(site_query, num_results=20)
        
        # Also try Bing for more coverage
        bing_results = await self.search_bing(site_query, num_results=20)
        results.extend(bing_results)
        
        # Deduplicate
        return list(set(results))
        
    async def reverse_image_search(
        self,
        image_url: str
    ) -> List[str]:
        """
        Perform reverse image search to find copies
        Note: Google's API doesn't directly support this,
        would need to use Google Vision API or third-party service
        """
        # This would integrate with Google Vision API or TinEye API
        # For MVP, returning empty list
        logger.info(f"Reverse image search for {image_url} not yet implemented")
        return []
        
    async def _search_google_fallback(self, query: str) -> List[str]:
        """
        Fallback method using web scraping when API is not available
        Note: This is for demonstration - production should use official APIs
        """
        urls = []
        
        try:
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract search result links
                    for link in soup.find_all('a'):
                        href = link.get('href')
                        if href and href.startswith('/url?q='):
                            url = href.split('/url?q=')[1].split('&')[0]
                            if url.startswith('http'):
                                urls.append(url)
                                
        except Exception as e:
            logger.error(f"Google fallback search error: {e}")
            
        return urls[:20]  # Limit results
        
    async def _search_bing_fallback(self, query: str) -> List[str]:
        """
        Fallback method for Bing search without API
        """
        urls = []
        
        try:
            search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract search result links
                    for result in soup.find_all('li', class_='b_algo'):
                        link = result.find('a')
                        if link and link.get('href'):
                            urls.append(link['href'])
                            
        except Exception as e:
            logger.error(f"Bing fallback search error: {e}")
            
        return urls[:20]
        
    async def _search_google_images_fallback(self, query: str) -> List[str]:
        """
        Fallback for Google Images search
        """
        # Would implement web scraping for Google Images
        # For now, using regular search with "image" modifier
        return await self.search_google(f'{query} image photo', num_results=20)
        
    async def _rate_limit_google(self):
        """Enforce rate limiting for Google API"""
        if self.last_google_request:
            elapsed = (datetime.utcnow() - self.last_google_request).total_seconds()
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_google_request = datetime.utcnow()
        
    async def _rate_limit_bing(self):
        """Enforce rate limiting for Bing API"""
        if self.last_bing_request:
            elapsed = (datetime.utcnow() - self.last_bing_request).total_seconds()
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_bing_request = datetime.utcnow()
        
    async def check_url_in_search_index(self, url: str) -> Dict[str, bool]:
        """
        Check if a URL appears in search engine indexes
        Used to verify if delisting was successful
        """
        results = {
            'google': False,
            'bing': False
        }
        
        # Search for exact URL
        google_results = await self.search_google(f'"{url}"', num_results=10)
        if url in google_results:
            results['google'] = True
            
        bing_results = await self.search_bing(f'"{url}"', num_results=10)
        if url in bing_results:
            results['bing'] = True
            
        return results