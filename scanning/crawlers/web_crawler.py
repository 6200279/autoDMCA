"""
Advanced web crawler with proxy support, rate limiting, and anti-detection features.
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Set, Tuple, AsyncIterator
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path
import json

import aiohttp
from aiohttp_socks import ProxyConnector
import aiofiles
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import structlog
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from ..config import ScannerSettings


logger = structlog.get_logger(__name__)


@dataclass
class ProxyConfig:
    """Configuration for a proxy server."""
    
    host: str
    port: int
    protocol: str = "http"  # http, https, socks4, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    anonymity: str = "unknown"  # transparent, anonymous, elite
    last_used: float = 0.0
    failure_count: int = 0
    max_failures: int = 3
    
    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is considered healthy."""
        return self.failure_count < self.max_failures
    
    def mark_used(self):
        """Mark proxy as recently used."""
        self.last_used = time.time()
    
    def mark_failure(self):
        """Mark proxy failure."""
        self.failure_count += 1
        logger.warning(
            "Proxy marked as failed", 
            host=self.host, 
            failures=self.failure_count
        )
    
    def reset_failures(self):
        """Reset failure count.""" 
        self.failure_count = 0


class ProxyManager:
    """Manages proxy rotation and health checking."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.proxies: List[ProxyConfig] = []
        self.current_index = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize proxy list from various sources."""
        if not self.settings.proxy_enabled:
            logger.info("Proxy support disabled")
            return
            
        await self._load_proxy_providers()
        await self._test_proxies()
        
        logger.info(
            "Proxy manager initialized",
            total_proxies=len(self.proxies),
            healthy_proxies=len([p for p in self.proxies if p.is_healthy])
        )
    
    async def _load_proxy_providers(self):
        """Load proxies from configured providers."""
        for provider in self.settings.proxy_providers:
            try:
                if provider == "free-proxy-list":
                    await self._load_free_proxy_list()
                elif provider.startswith("file://"):
                    await self._load_from_file(provider[7:])
                else:
                    logger.warning(f"Unknown proxy provider: {provider}")
            except Exception as e:
                logger.error(f"Failed to load proxies from {provider}", error=str(e))
    
    async def _load_free_proxy_list(self):
        """Load proxies from free-proxy-list.net (example implementation)."""
        try:
            url = "https://www.proxy-list.download/api/v1/get?type=http"
            
            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10))
            async with session.get(url) as response:
                if response.status == 200:
                    proxy_text = await response.text()
                    lines = proxy_text.strip().split('\n')
                    
                    for line in lines[:50]:  # Limit to first 50 proxies
                        if ':' in line:
                            host, port = line.strip().split(':', 1)
                            proxy = ProxyConfig(
                                host=host.strip(),
                                port=int(port.strip()),
                                protocol="http"
                            )
                            self.proxies.append(proxy)
            
            await session.close()
            logger.info(f"Loaded {len(self.proxies)} free proxies")
            
        except Exception as e:
            logger.error("Failed to load free proxies", error=str(e))
    
    async def _load_from_file(self, file_path: str):
        """Load proxies from a file.""" 
        try:
            path = Path(file_path)
            if path.exists():
                async with aiofiles.open(path, 'r') as f:
                    content = await f.read()
                    
                if file_path.endswith('.json'):
                    proxy_data = json.loads(content)
                    for item in proxy_data:
                        proxy = ProxyConfig(**item)
                        self.proxies.append(proxy)
                else:
                    # Assume text format: host:port
                    lines = content.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            host, port = line.strip().split(':', 1)
                            proxy = ProxyConfig(
                                host=host.strip(),
                                port=int(port.strip())
                            )
                            self.proxies.append(proxy)
                            
                logger.info(f"Loaded {len(self.proxies)} proxies from {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to load proxies from file: {file_path}", error=str(e))
    
    async def _test_proxies(self):
        """Test proxy connectivity and remove non-working ones."""
        if not self.proxies:
            return
            
        logger.info(f"Testing {len(self.proxies)} proxies...")
        
        async def test_proxy(proxy: ProxyConfig) -> bool:
            try:
                if proxy.protocol.startswith('socks'):
                    connector = ProxyConnector.from_url(proxy.url)
                else:
                    connector = aiohttp.TCPConnector()
                
                timeout = aiohttp.ClientTimeout(total=10)
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )
                
                test_url = "http://httpbin.org/ip"
                
                if proxy.protocol.startswith('socks'):
                    async with session.get(test_url) as response:
                        success = response.status == 200
                else:
                    proxy_dict = {'http': proxy.url, 'https': proxy.url}
                    async with session.get(test_url, proxy=proxy.url) as response:
                        success = response.status == 200
                
                await session.close()
                return success
                
            except Exception as e:
                logger.debug(f"Proxy test failed: {proxy.host}:{proxy.port}", error=str(e))
                return False
        
        # Test proxies concurrently
        test_tasks = [test_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        # Keep only working proxies
        working_proxies = []
        for i, (proxy, result) in enumerate(zip(self.proxies, results)):
            if isinstance(result, bool) and result:
                working_proxies.append(proxy)
                proxy.reset_failures()
            else:
                proxy.mark_failure()
        
        self.proxies = working_proxies
        logger.info(f"Proxy testing completed: {len(self.proxies)} working proxies")
    
    async def get_proxy(self) -> Optional[ProxyConfig]:
        """Get next available proxy with rotation."""
        async with self._lock:
            if not self.proxies or not self.settings.proxy_enabled:
                return None
            
            # Filter healthy proxies
            healthy_proxies = [p for p in self.proxies if p.is_healthy]
            if not healthy_proxies:
                logger.warning("No healthy proxies available")
                return None
            
            # Simple round-robin selection
            proxy = healthy_proxies[self.current_index % len(healthy_proxies)]
            self.current_index = (self.current_index + 1) % len(healthy_proxies)
            
            proxy.mark_used()
            return proxy
    
    async def release_proxy(self, proxy: ProxyConfig, success: bool = True):
        """Mark proxy as available and update its status."""
        if not success:
            proxy.mark_failure()
            if not proxy.is_healthy:
                logger.warning(f"Proxy marked as unhealthy: {proxy.host}:{proxy.port}")


@dataclass
class CrawlResult:
    """Result from crawling a URL."""
    
    url: str
    status_code: int
    content: str = ""
    html: str = ""
    title: str = ""
    images: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    text_content: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    response_time: float = 0.0
    used_proxy: bool = False
    
    @property
    def is_success(self) -> bool:
        """Check if crawl was successful."""
        return self.status_code == 200 and not self.error


class WebCrawler:
    """Advanced web crawler with anti-detection and proxy support."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.proxy_manager = ProxyManager(settings)
        self.user_agent = UserAgent()
        self.session_pool: List[aiohttp.ClientSession] = []
        self.rate_limiter = asyncio.Semaphore(settings.concurrent_requests)
        self.domain_delays: Dict[str, float] = {}
        
    async def initialize(self):
        """Initialize the crawler."""
        await self.proxy_manager.initialize()
        await self._create_session_pool()
        
    async def _create_session_pool(self):
        """Create a pool of HTTP sessions for reuse."""
        pool_size = min(self.settings.concurrent_requests, 10)
        
        for i in range(pool_size):
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                keepalive_timeout=60
            )
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': self.user_agent.random}
            )
            
            self.session_pool.append(session)
    
    async def close(self):
        """Clean up resources."""
        for session in self.session_pool:
            await session.close()
        self.session_pool.clear()
    
    async def crawl(
        self,
        url: str,
        use_proxy: bool = True,
        extract_images: bool = True,
        extract_links: bool = True,
        render_js: bool = False,
        **kwargs
    ) -> CrawlResult:
        """Crawl a single URL."""
        start_time = time.time()
        
        async with self.rate_limiter:
            # Apply domain-specific rate limiting
            await self._apply_domain_rate_limit(url)
            
            try:
                if render_js:
                    return await self._crawl_with_selenium(url, extract_images, extract_links)
                else:
                    return await self._crawl_with_aiohttp(
                        url, use_proxy, extract_images, extract_links, **kwargs
                    )
                    
            except Exception as e:
                logger.error("Crawl failed", url=url, error=str(e))
                return CrawlResult(
                    url=url,
                    status_code=0,
                    error=str(e),
                    response_time=time.time() - start_time
                )
    
    async def _apply_domain_rate_limit(self, url: str):
        """Apply rate limiting per domain."""
        domain = urlparse(url).netloc.lower()
        current_time = time.time()
        
        if domain in self.domain_delays:
            time_since_last = current_time - self.domain_delays[domain]
            min_delay = 60.0 / self.settings.requests_per_minute
            
            if time_since_last < min_delay:
                sleep_time = min_delay - time_since_last
                await asyncio.sleep(sleep_time)
        
        self.domain_delays[domain] = time.time()
    
    async def _crawl_with_aiohttp(
        self,
        url: str,
        use_proxy: bool,
        extract_images: bool,
        extract_links: bool,
        **kwargs
    ) -> CrawlResult:
        """Crawl URL using aiohttp."""
        start_time = time.time()
        proxy = None
        session = None
        
        try:
            # Get proxy if requested
            if use_proxy:
                proxy = await self.proxy_manager.get_proxy()
            
            # Get session from pool
            session = self.session_pool[0] if self.session_pool else None
            if not session:
                session = aiohttp.ClientSession()
            
            # Prepare request headers
            headers = {
                'User-Agent': self.user_agent.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Add custom headers
            if 'headers' in kwargs:
                headers.update(kwargs['headers'])
            
            # Make request
            proxy_url = proxy.url if proxy else None
            
            async with session.get(
                url,
                headers=headers,
                proxy=proxy_url,
                allow_redirects=True,
                max_redirects=5
            ) as response:
                
                html = await response.text()
                
                result = CrawlResult(
                    url=str(response.url),
                    status_code=response.status,
                    html=html,
                    content=html,
                    response_time=time.time() - start_time,
                    used_proxy=proxy is not None
                )
                
                if response.status == 200:
                    await self._extract_content(result, extract_images, extract_links)
                    
                    if proxy:
                        await self.proxy_manager.release_proxy(proxy, success=True)
                else:
                    result.error = f"HTTP {response.status}"
                    if proxy:
                        await self.proxy_manager.release_proxy(proxy, success=False)
                
                return result
                
        except Exception as e:
            if proxy:
                await self.proxy_manager.release_proxy(proxy, success=False)
            
            return CrawlResult(
                url=url,
                status_code=0,
                error=str(e),
                response_time=time.time() - start_time,
                used_proxy=proxy is not None
            )
    
    async def _crawl_with_selenium(
        self,
        url: str,
        extract_images: bool,
        extract_links: bool
    ) -> CrawlResult:
        """Crawl URL using Selenium for JavaScript rendering."""
        start_time = time.time()
        driver = None
        
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={self.user_agent.random}')
            
            # Add proxy if available
            proxy = await self.proxy_manager.get_proxy()
            if proxy and proxy.protocol in ['http', 'https']:
                chrome_options.add_argument(f'--proxy-server={proxy.url}')
            
            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Navigate to URL
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Get page source
            html = driver.page_source
            current_url = driver.current_url
            title = driver.title
            
            result = CrawlResult(
                url=current_url,
                status_code=200,
                html=html,
                content=html,
                title=title,
                response_time=time.time() - start_time,
                used_proxy=proxy is not None
            )
            
            await self._extract_content(result, extract_images, extract_links)
            
            if proxy:
                await self.proxy_manager.release_proxy(proxy, success=True)
            
            return result
            
        except TimeoutException:
            error_msg = "Page load timeout"
            logger.warning("Selenium crawl timeout", url=url)
            
        except WebDriverException as e:
            error_msg = f"Selenium error: {str(e)}"
            logger.error("Selenium crawl failed", url=url, error=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error("Selenium crawl failed", url=url, error=error_msg)
        
        finally:
            if driver:
                driver.quit()
            if proxy:
                await self.proxy_manager.release_proxy(proxy, success=False)
        
        return CrawlResult(
            url=url,
            status_code=0,
            error=error_msg,
            response_time=time.time() - start_time
        )
    
    async def _extract_content(
        self,
        result: CrawlResult,
        extract_images: bool,
        extract_links: bool
    ):
        """Extract structured content from HTML."""
        try:
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                result.title = title_tag.get_text(strip=True)
            
            # Extract text content
            for script in soup(["script", "style"]):
                script.decompose()
            result.text_content = soup.get_text(strip=True, separator=' ')
            
            # Extract images
            if extract_images:
                img_tags = soup.find_all('img')
                for img in img_tags:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        absolute_url = urljoin(result.url, src)
                        result.images.append(absolute_url)
            
            # Extract links
            if extract_links:
                a_tags = soup.find_all('a', href=True)
                for a in a_tags:
                    href = a['href']
                    if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                        absolute_url = urljoin(result.url, href)
                        result.links.append(absolute_url)
            
            # Extract metadata
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    result.metadata[name] = content
                    
        except Exception as e:
            logger.error("Content extraction failed", url=result.url, error=str(e))
    
    async def bulk_crawl(
        self,
        urls: List[str],
        **kwargs
    ) -> List[CrawlResult]:
        """Crawl multiple URLs concurrently."""
        tasks = [self.crawl(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Bulk crawl failed for URL: {urls[i]}", error=str(result))
                valid_results.append(CrawlResult(
                    url=urls[i],
                    status_code=0,
                    error=str(result)
                ))
            else:
                valid_results.append(result)
        
        return valid_results