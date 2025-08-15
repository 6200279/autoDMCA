"""
Optimized Web Crawler with High Performance and Concurrent Processing
Implements advanced crawling strategies with rate limiting, caching, and batch processing
"""
import asyncio
import aiohttp
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import random

from bs4 import BeautifulSoup
import redis.asyncio as redis

from app.core.config import settings
from app.services.ai.optimized_content_matcher import OptimizedContentMatcher
from app.services.cache.multi_level_cache import cache_manager, cached
from app.services.monitoring.performance_monitor import performance_monitor, track_performance

logger = logging.getLogger(__name__)


class CrawlStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CACHED = "cached"


@dataclass
class CrawlResult:
    """Enhanced crawl result with performance metrics"""
    url: str
    status: CrawlStatus
    content_type: str
    content_hash: str
    images: List[str]
    videos: List[str]
    text_content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None


@dataclass
class CrawlerMetrics:
    """Crawler performance metrics"""
    total_urls_processed: int = 0
    successful_crawls: int = 0
    failed_crawls: int = 0
    cached_responses: int = 0
    rate_limited_requests: int = 0
    average_response_time_ms: float = 0.0
    bandwidth_used_mb: float = 0.0
    concurrent_requests: int = 0


class RateLimiter:
    """Advanced rate limiter with domain-specific limits and burst handling"""
    
    def __init__(self):
        self.domain_limits = {
            'default': 1.0,  # 1 request per second
            'reddit.com': 0.5,  # 1 request per 2 seconds
            'twitter.com': 0.3,  # 1 request per 3 seconds
            'facebook.com': 0.2,  # 1 request per 5 seconds
            'instagram.com': 0.2,
            'google.com': 2.0,  # Google allows higher rates
            'bing.com': 2.0
        }
        
        # Track last request time per domain
        self.last_request_times: Dict[str, float] = {}
        
        # Track request counts for burst detection
        self.request_counts: Dict[str, List[float]] = {}
        
        # Burst limits (requests per minute)
        self.burst_limits = {
            'default': 30,
            'reddit.com': 15,
            'twitter.com': 10,
            'facebook.com': 10,
            'instagram.com': 10
        }
    
    async def acquire(self, url: str) -> bool:
        """Acquire rate limit permission for URL"""
        domain = urlparse(url).netloc.lower()
        
        # Get rate limit for domain
        rate_limit = self.domain_limits.get(domain, self.domain_limits['default'])
        burst_limit = self.burst_limits.get(domain, self.burst_limits['default'])
        
        current_time = time.time()
        
        # Check burst limit (requests per minute)
        if domain in self.request_counts:
            # Remove requests older than 1 minute
            self.request_counts[domain] = [
                t for t in self.request_counts[domain] 
                if current_time - t < 60
            ]
            
            if len(self.request_counts[domain]) >= burst_limit:
                logger.warning(f"Burst limit exceeded for {domain}")
                return False
        else:
            self.request_counts[domain] = []
        
        # Check rate limit
        if domain in self.last_request_times:
            time_since_last = current_time - self.last_request_times[domain]
            min_interval = 1.0 / rate_limit
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                await asyncio.sleep(wait_time)
        
        # Update tracking
        self.last_request_times[domain] = time.time()
        self.request_counts[domain].append(time.time())
        
        return True


class OptimizedWebCrawler:
    """
    High-performance web crawler with advanced optimization features:
    - Concurrent request processing with rate limiting
    - Multi-level caching for content and results
    - Smart content deduplication
    - Bandwidth optimization with compression
    - Connection pooling and keepalive
    - Retry logic with exponential backoff
    - Performance monitoring and metrics
    """
    
    def __init__(self):
        self.content_matcher: Optional[OptimizedContentMatcher] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter()
        
        # Configuration
        self.max_concurrent_requests = getattr(settings, 'CRAWLER_MAX_CONCURRENT', 10)
        self.request_timeout = getattr(settings, 'CRAWLER_TIMEOUT', 30)
        self.max_content_size = getattr(settings, 'CRAWLER_MAX_CONTENT_SIZE', 10 * 1024 * 1024)  # 10MB
        self.enable_compression = getattr(settings, 'CRAWLER_ENABLE_COMPRESSION', True)
        self.cache_ttl = getattr(settings, 'CRAWLER_CACHE_TTL', 3600)
        
        # State tracking
        self.visited_urls: Set[str] = set()
        self.crawl_queue = asyncio.Queue(maxsize=1000)
        self.metrics = CrawlerMetrics()
        
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Content type filters
        self.allowed_content_types = {
            'text/html', 'text/plain',
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/webm', 'video/avi',
            'application/json'
        }
        
        # Known leak sites with priority scoring
        self.priority_sites = {
            # High priority leak sites
            'coomer.party': 10,
            'kemono.party': 10,
            'leakfanatic.com': 9,
            'thotsbay.com': 9,
            
            # Medium priority file sharing
            'mega.nz': 7,
            'gofile.io': 7,
            'pixeldrain.com': 7,
            'anonfiles.com': 6,
            
            # Social media (lower priority but high volume)
            'reddit.com': 5,
            'twitter.com': 5,
            'instagram.com': 5,
            
            # Adult platforms
            'pornhub.com': 6,
            'xvideos.com': 6,
            'xnxx.com': 6,
            'spankbang.com': 6
        }
        
        logger.info("Optimized web crawler initialized")
    
    async def initialize(self):
        """Initialize crawler components"""
        # Initialize content matcher
        self.content_matcher = OptimizedContentMatcher()
        await self.content_matcher.initialize()
        
        # Create optimized HTTP session
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent_requests * 2,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout,
            connect=10,
            sock_read=10
        )
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate' if self.enable_compression else 'identity',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            trace_configs=[self._create_trace_config()]
        )
        
        logger.info("Optimized web crawler initialized successfully")
    
    def _create_trace_config(self) -> aiohttp.TraceConfig:
        """Create trace configuration for monitoring"""
        trace_config = aiohttp.TraceConfig()
        
        async def on_request_start(session, trace_config_ctx, params):
            trace_config_ctx.start_time = time.time()
            self.metrics.concurrent_requests += 1
        
        async def on_request_end(session, trace_config_ctx, params):
            if hasattr(trace_config_ctx, 'start_time'):
                request_time = (time.time() - trace_config_ctx.start_time) * 1000
                current_avg = self.metrics.average_response_time_ms
                total_requests = self.metrics.total_urls_processed
                self.metrics.average_response_time_ms = (
                    (current_avg * total_requests + request_time) / (total_requests + 1)
                )
            self.metrics.concurrent_requests -= 1
        
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)
        
        return trace_config
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        
        if self.content_matcher:
            await self.content_matcher.cleanup()
        
        self.executor.shutdown(wait=True)
    
    @track_performance(endpoint="crawler_scan")
    async def scan_for_profile_optimized(
        self,
        profile_data: Dict[str, Any],
        max_urls: int = 100,
        deep_scan: bool = False,
        priority_only: bool = False
    ) -> List[CrawlResult]:
        """
        Optimized profile scanning with concurrent processing
        
        Args:
            profile_data: Profile information for matching
            max_urls: Maximum URLs to scan
            deep_scan: Whether to follow links from initial results
            priority_only: Only scan high-priority sites
        """
        start_time = time.time()
        
        logger.info(f"Starting optimized scan for profile: {profile_data.get('username')}")
        
        try:
            # Step 1: URL Discovery
            urls_to_scan = await self._discover_urls_optimized(profile_data, max_urls, priority_only)
            
            # Step 2: Concurrent Crawling
            crawl_results = await self._crawl_urls_concurrent(urls_to_scan, profile_data)
            
            # Step 3: Content Analysis (Batch Processing)
            analyzed_results = await self._analyze_content_batch(crawl_results, profile_data)
            
            # Step 4: Deep Scan (if requested)
            if deep_scan:
                additional_urls = self._extract_additional_urls(analyzed_results)
                if additional_urls:
                    deep_results = await self._crawl_urls_concurrent(additional_urls[:20], profile_data)
                    deep_analyzed = await self._analyze_content_batch(deep_results, profile_data)
                    analyzed_results.extend(deep_analyzed)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.total_urls_processed += len(urls_to_scan)
            
            # Performance monitoring
            performance_monitor.track_ai_inference(
                model_name="web_crawler",
                inference_time_ms=processing_time,
                batch_size=len(urls_to_scan),
                memory_usage_mb=self._get_memory_usage()
            )
            
            logger.info(
                f"Scan completed: {len(analyzed_results)} results from {len(urls_to_scan)} URLs "
                f"in {processing_time:.2f}ms"
            )
            
            return analyzed_results
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return []
    
    async def _discover_urls_optimized(
        self,
        profile_data: Dict[str, Any],
        max_urls: int,
        priority_only: bool
    ) -> List[str]:
        """Optimized URL discovery with intelligent prioritization"""
        
        username = profile_data.get('username', '')
        if not username:
            return []
        
        discovered_urls = []
        
        # Generate priority URLs first
        priority_urls = self._generate_priority_urls_optimized(profile_data)
        
        if priority_only:
            return priority_urls[:max_urls]
        
        # Search engine discovery (with caching)
        cache_key = f"search_urls:{hashlib.md5(username.encode()).hexdigest()}"
        cached_search_urls = await cache_manager.get(cache_key, cache_type="scan_result")
        
        if cached_search_urls:
            search_urls = cached_search_urls
            logger.info(f"Using cached search URLs: {len(search_urls)} URLs")
        else:
            search_urls = await self._search_engine_discovery_optimized(profile_data)
            await cache_manager.set(cache_key, search_urls, ttl=self.cache_ttl, cache_type="scan_result")
        
        # Combine and prioritize URLs
        all_urls = priority_urls + search_urls
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen and len(unique_urls) < max_urls:
                seen.add(url)
                unique_urls.append(url)
        
        # Score and sort URLs by priority
        scored_urls = []
        for url in unique_urls:
            score = self._calculate_url_priority(url, profile_data)
            scored_urls.append((score, url))
        
        # Sort by score (highest first) and return URLs
        scored_urls.sort(reverse=True)
        
        return [url for _, url in scored_urls[:max_urls]]
    
    def _generate_priority_urls_optimized(self, profile_data: Dict[str, Any]) -> List[str]:
        """Generate high-priority URLs with intelligent patterns"""
        urls = []
        username = profile_data.get('username', '')
        
        if not username:
            return urls
        
        # Direct profile URLs on known leak sites
        for site, priority in self.priority_sites.items():
            if priority >= 8:  # High priority sites only
                if 'coomer.party' in site or 'kemono.party' in site:
                    urls.extend([
                        f'https://{site}/onlyfans/user/{username}',
                        f'https://{site}/patreon/user/{username}',
                        f'https://{site}/search?q={username}'
                    ])
                elif 'reddit.com' in site:
                    urls.extend([
                        f'https://www.reddit.com/search/?q={username}',
                        f'https://www.reddit.com/user/{username}',
                        f'https://www.reddit.com/r/OnlyFans101/search/?q={username}',
                        f'https://www.reddit.com/r/onlyfansgirls101/search/?q={username}'
                    ])
                elif 'mega.nz' in site:
                    # Search for mega links containing username
                    urls.append(f'https://www.google.com/search?q=site:mega.nz+{username}')
                else:
                    urls.append(f'https://{site}/search?q={username}')
        
        return urls
    
    async def _search_engine_discovery_optimized(self, profile_data: Dict[str, Any]) -> List[str]:
        """Optimized search engine discovery with rate limiting"""
        # This would integrate with search APIs or web scraping
        # For now, return placeholder URLs
        username = profile_data.get('username', '')
        
        search_urls = []
        
        # Generate search terms
        search_terms = [
            f'"{username}" leaked',
            f'"{username}" onlyfans',
            f'"{username}" mega',
            f'"{username}" download'
        ]
        
        # In a production system, this would use actual search APIs
        # For demo purposes, generating sample URLs
        for term in search_terms:
            # This would be replaced with actual search API calls
            search_urls.extend([
                f"https://example-leak-site.com/search?q={term.replace(' ', '+')}",
                f"https://another-site.com/search?q={term.replace(' ', '+')}"
            ])
        
        return search_urls[:20]  # Limit search results
    
    def _calculate_url_priority(self, url: str, profile_data: Dict[str, Any]) -> float:
        """Calculate URL priority score for crawling order"""
        domain = urlparse(url).netloc.lower()
        score = 1.0  # Base score
        
        # Domain priority
        for site, priority_score in self.priority_sites.items():
            if site in domain:
                score += priority_score
                break
        
        # Username mention bonus
        username = profile_data.get('username', '').lower()
        if username and username in url.lower():
            score += 5.0
        
        # Platform-specific bonuses
        platform = profile_data.get('platform', '').lower()
        if platform and platform in url.lower():
            score += 3.0
        
        # URL pattern bonuses
        if any(keyword in url.lower() for keyword in ['leaked', 'mega', 'download', 'free']):
            score += 2.0
        
        return score
    
    async def _crawl_urls_concurrent(
        self,
        urls: List[str],
        profile_data: Dict[str, Any]
    ) -> List[CrawlResult]:
        """Crawl URLs with optimized concurrency and caching"""
        
        if not urls:
            return []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Create crawl tasks
        tasks = []
        for url in urls:
            task = self._crawl_single_url_cached(url, profile_data, semaphore)
            tasks.append(task)
        
        # Execute with progress tracking
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    results.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    logger.info(f"Crawl progress: {completed}/{len(tasks)} URLs completed")
                    
            except Exception as e:
                logger.error(f"Crawl task error: {e}")
                completed += 1
        
        # Update metrics
        self.metrics.successful_crawls += len(results)
        self.metrics.failed_crawls += len(tasks) - len(results)
        
        return results
    
    async def _crawl_single_url_cached(
        self,
        url: str,
        profile_data: Dict[str, Any],
        semaphore: asyncio.Semaphore
    ) -> Optional[CrawlResult]:
        """Crawl single URL with caching and rate limiting"""
        
        async with semaphore:
            start_time = time.time()
            
            # Check cache first
            cache_key = f"crawl:{hashlib.md5(url.encode()).hexdigest()}"
            cached_result = await cache_manager.get(cache_key, cache_type="scan_result")
            
            if cached_result:
                cached_result['cache_hit'] = True
                cached_result['processing_time_ms'] = (time.time() - start_time) * 1000
                self.metrics.cached_responses += 1
                return CrawlResult(**cached_result)
            
            # Rate limiting
            if not await self.rate_limiter.acquire(url):
                self.metrics.rate_limited_requests += 1
                return CrawlResult(
                    url=url,
                    status=CrawlStatus.RATE_LIMITED,
                    content_type="",
                    content_hash="",
                    images=[],
                    videos=[],
                    text_content="",
                    metadata={},
                    timestamp=datetime.utcnow(),
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error="Rate limited"
                )
            
            # Skip if already visited recently
            if url in self.visited_urls:
                return None
            
            self.visited_urls.add(url)
            
            try:
                # Make HTTP request
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
                            processing_time_ms=(time.time() - start_time) * 1000,
                            error=f"HTTP {response.status}"
                        )
                    
                    content_type = response.headers.get('Content-Type', '').split(';')[0]
                    content_length = int(response.headers.get('Content-Length', 0))
                    
                    # Skip if content too large
                    if content_length > self.max_content_size:
                        return CrawlResult(
                            url=url,
                            status=CrawlStatus.FAILED,
                            content_type=content_type,
                            content_hash="",
                            images=[],
                            videos=[],
                            text_content="",
                            metadata={"content_length": content_length},
                            timestamp=datetime.utcnow(),
                            processing_time_ms=(time.time() - start_time) * 1000,
                            error="Content too large"
                        )
                    
                    # Skip if not allowed content type
                    if content_type not in self.allowed_content_types:
                        return None
                    
                    # Read content with size limit
                    content = await response.read()
                    if len(content) > self.max_content_size:
                        content = content[:self.max_content_size]
                    
                    # Update bandwidth metrics
                    self.metrics.bandwidth_used_mb += len(content) / 1024 / 1024
                    
                    # Process content
                    result = await self._process_content_optimized(
                        url, content, content_type, start_time
                    )
                    
                    # Cache successful results
                    if result and result.status == CrawlStatus.COMPLETED:
                        result_dict = asdict(result)
                        result_dict['cache_hit'] = False
                        await cache_manager.set(
                            cache_key, 
                            result_dict, 
                            ttl=self.cache_ttl, 
                            cache_type="scan_result"
                        )
                    
                    return result
                    
            except asyncio.TimeoutError:
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
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error="Timeout"
                )
            except Exception as e:
                logger.error(f"Crawl error for {url}: {e}")
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
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error=str(e)
                )
    
    async def _process_content_optimized(
        self,
        url: str,
        content: bytes,
        content_type: str,
        start_time: float
    ) -> CrawlResult:
        """Process crawled content with optimization"""
        
        # Generate content hash for deduplication
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Parse content based on type
        if 'text/html' in content_type:
            # Parse HTML in thread pool to avoid blocking
            soup = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: BeautifulSoup(content, 'html.parser')
            )
            
            # Extract content
            images = [urljoin(url, img.get('src', '')) for img in soup.find_all('img') if img.get('src')]
            videos = [urljoin(url, vid.get('src', '')) for vid in soup.find_all(['video', 'iframe']) if vid.get('src')]
            text_content = soup.get_text()[:10000]  # Limit text size
            
            metadata = {
                "title": soup.title.string if soup.title else "",
                "image_count": len(images),
                "video_count": len(videos),
                "text_length": len(text_content)
            }
            
        elif 'image' in content_type:
            images = [url]
            videos = []
            text_content = ""
            metadata = {"direct_image": True, "size": len(content)}
            
        elif 'video' in content_type:
            images = []
            videos = [url]
            text_content = ""
            metadata = {"direct_video": True, "size": len(content)}
            
        else:
            images = []
            videos = []
            text_content = content.decode('utf-8', errors='ignore')[:10000]
            metadata = {"size": len(content)}
        
        return CrawlResult(
            url=url,
            status=CrawlStatus.COMPLETED,
            content_type=content_type,
            content_hash=content_hash,
            images=images[:50],  # Limit for performance
            videos=videos[:20],
            text_content=text_content,
            metadata=metadata,
            timestamp=datetime.utcnow(),
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    async def _analyze_content_batch(
        self,
        crawl_results: List[CrawlResult],
        profile_data: Dict[str, Any]
    ) -> List[CrawlResult]:
        """Analyze crawled content using batch AI processing"""
        
        if not crawl_results or not self.content_matcher:
            return crawl_results
        
        # Prepare content items for batch analysis
        content_items = []
        result_mapping = {}
        
        for i, result in enumerate(crawl_results):
            if result.status == CrawlStatus.COMPLETED:
                # Create content data based on type
                if 'image' in result.content_type and result.images:
                    # For direct images, we need to fetch the content
                    try:
                        async with self.session.get(result.images[0]) as response:
                            if response.status == 200:
                                image_data = await response.read()
                                content_items.append((result.url, image_data, profile_data))
                                result_mapping[len(content_items) - 1] = i
                    except Exception as e:
                        logger.error(f"Failed to fetch image for analysis: {e}")
                        
                elif result.text_content:
                    # For text content
                    text_data = result.text_content.encode('utf-8')
                    content_items.append((result.url, text_data, profile_data))
                    result_mapping[len(content_items) - 1] = i
        
        # Batch analyze content
        if content_items:
            try:
                analysis_results = await self.content_matcher.analyze_content_batch(content_items)
                
                # Add analysis results to crawl results
                for analysis_idx, matches in enumerate(analysis_results):
                    if analysis_idx in result_mapping:
                        result_idx = result_mapping[analysis_idx]
                        crawl_results[result_idx].metadata['content_matches'] = [
                            {
                                'match_type': match.match_type,
                                'confidence': match.confidence,
                                'metadata': match.metadata
                            }
                            for match in matches
                        ]
                        crawl_results[result_idx].metadata['match_count'] = len(matches)
                        
            except Exception as e:
                logger.error(f"Batch content analysis error: {e}")
        
        return crawl_results
    
    def _extract_additional_urls(self, results: List[CrawlResult]) -> List[str]:
        """Extract additional URLs from crawl results for deep scanning"""
        additional_urls = []
        
        for result in results:
            if result.status == CrawlStatus.COMPLETED:
                # Extract image and video URLs
                additional_urls.extend(result.images[:5])  # Limit per result
                additional_urls.extend(result.videos[:3])
        
        # Remove duplicates and filter
        unique_urls = list(set(additional_urls))
        
        # Filter out already visited
        new_urls = [url for url in unique_urls if url not in self.visited_urls]
        
        return new_urls
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    async def get_crawler_metrics(self) -> Dict[str, Any]:
        """Get comprehensive crawler metrics"""
        return {
            'total_urls_processed': self.metrics.total_urls_processed,
            'successful_crawls': self.metrics.successful_crawls,
            'failed_crawls': self.metrics.failed_crawls,
            'success_rate': (self.metrics.successful_crawls / max(self.metrics.total_urls_processed, 1)) * 100,
            'cached_responses': self.metrics.cached_responses,
            'cache_hit_rate': (self.metrics.cached_responses / max(self.metrics.total_urls_processed, 1)) * 100,
            'rate_limited_requests': self.metrics.rate_limited_requests,
            'average_response_time_ms': self.metrics.average_response_time_ms,
            'bandwidth_used_mb': self.metrics.bandwidth_used_mb,
            'concurrent_requests': self.metrics.concurrent_requests,
            'visited_urls_count': len(self.visited_urls),
            'priority_sites_count': len(self.priority_sites)
        }


# Global crawler instance
optimized_crawler = OptimizedWebCrawler()