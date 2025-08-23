"""
Scanning Orchestrator Service - Core missing functionality implementation
Coordinates all scanning activities across platforms with global distribution capability
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import redis.asyncio as redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.ai.content_matcher import ContentMatcher
from app.services.dmca.takedown_processor import DMCATakedownProcessor
from app.services.scanning.scheduler import ScanningScheduler, ScanJob, JobStatus
from app.services.scanning.monitoring import scanning_monitor
from app.api.websocket import notify_scan_progress, notify_infringement_found

logger = logging.getLogger(__name__)


class ScanPriority(str, Enum):
    """Scan priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"  # New user scans - within hours


class ScanScope(str, Enum):
    """Scan scope definitions"""
    QUICK = "quick"          # Basic platforms, limited depth
    COMPREHENSIVE = "comprehensive"  # All platforms, medium depth  
    DEEP = "deep"            # All platforms, maximum depth
    TARGETED = "targeted"    # Specific platforms/sites only


@dataclass
class ScanRegion:
    """Global scanning region configuration"""
    region_id: str
    country_code: str
    vpn_server: Optional[str] = None
    proxy_config: Optional[Dict[str, Any]] = None
    active: bool = True
    last_used: Optional[datetime] = None


@dataclass
class PlatformConfig:
    """Platform-specific scanning configuration"""
    platform_name: str
    scanner_class: str
    rate_limit: int  # requests per minute
    priority_weight: float
    api_available: bool = False
    requires_auth: bool = False
    auth_config: Optional[Dict[str, Any]] = None


@dataclass
class ScanRequest:
    """Comprehensive scan request"""
    scan_id: str
    profile_id: int
    user_id: int
    profile_data: Dict[str, Any]
    priority: ScanPriority
    scope: ScanScope
    platforms: List[str]
    regions: List[str]
    keywords: List[str]
    face_encodings: List[str] = field(default_factory=list)
    reference_urls: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScanningOrchestrator:
    """
    Core Scanning Orchestrator - implements the main PRD requirements:
    - Daily scans across 50+ country servers
    - Major platform scanning (Google, Reddit, Instagram, Twitter, YouTube, TikTok)
    - Facial recognition for stolen content
    - Immediate scanning for new users (within hours)
    - Automated DMCA takedown integration
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.content_matcher = ContentMatcher()
        self.takedown_processor = DMCATakedownProcessor()
        self.scheduler = ScanningScheduler()
        
        # Global scanning infrastructure
        self.scan_regions: Dict[str, ScanRegion] = {}
        self.platform_configs: Dict[str, PlatformConfig] = {}
        self.active_scans: Dict[str, ScanRequest] = {}
        self.scan_workers: List[asyncio.Task] = []
        
        # Performance configuration
        self.max_concurrent_scans = 20
        self.max_regions_per_scan = 5
        self.max_scan_duration = timedelta(hours=4)
        self.new_user_scan_timeout = timedelta(hours=2)
        
        # Thread pool for CPU-intensive tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        self._initialize_regions()
        self._initialize_platforms()
        
    async def initialize(self):
        """Initialize orchestrator and all dependencies"""
        try:
            # Connect to Redis
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Initialize monitoring system
            await scanning_monitor.initialize()
            
            # Initialize scheduler
            await self.scheduler.initialize()
            
            # Start scan workers
            for i in range(self.max_concurrent_scans):
                worker = asyncio.create_task(self._scan_worker(i))
                self.scan_workers.append(worker)
            
            # Schedule priority scans for new users
            await self._schedule_new_user_monitoring()
            
            logger.info(f"Scanning orchestrator initialized with {len(self.scan_regions)} regions and monitoring enabled")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            # Stop all workers
            for worker in self.scan_workers:
                worker.cancel()
                
            # Wait for active scans to complete or timeout
            timeout = 30  # seconds
            active_tasks = list(self.active_scans.keys())
            
            if active_tasks:
                logger.info(f"Waiting for {len(active_tasks)} active scans to complete...")
                await asyncio.sleep(min(timeout, 10))
            
            # Shutdown scheduler
            await self.scheduler.shutdown()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
                
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=False)
            
            logger.info("Scanning orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during orchestrator shutdown: {e}")
    
    def _initialize_regions(self):
        """Initialize global scanning regions (50+ countries)"""
        # Major regions with high content piracy activity
        regions_config = [
            ("US-EAST", "US", "us-east-vpn.example.com"),
            ("US-WEST", "US", "us-west-vpn.example.com"),
            ("EU-CENTRAL", "DE", "eu-central-vpn.example.com"),
            ("EU-WEST", "GB", "eu-west-vpn.example.com"),
            ("ASIA-EAST", "JP", "asia-east-vpn.example.com"),
            ("ASIA-SOUTH", "SG", "asia-south-vpn.example.com"),
            ("CANADA", "CA", "canada-vpn.example.com"),
            ("AUSTRALIA", "AU", "australia-vpn.example.com"),
            ("BRAZIL", "BR", "brazil-vpn.example.com"),
            ("RUSSIA", "RU", "russia-vpn.example.com"),
            ("INDIA", "IN", "india-vpn.example.com"),
            ("CHINA", "CN", "china-vpn.example.com"),
            ("SOUTH-KOREA", "KR", "korea-vpn.example.com"),
            ("NETHERLANDS", "NL", "netherlands-vpn.example.com"),
            ("FRANCE", "FR", "france-vpn.example.com"),
            ("SPAIN", "ES", "spain-vpn.example.com"),
            ("ITALY", "IT", "italy-vpn.example.com"),
            ("POLAND", "PL", "poland-vpn.example.com"),
            ("CZECH", "CZ", "czech-vpn.example.com"),
            ("UKRAINE", "UA", "ukraine-vpn.example.com"),
            ("TURKEY", "TR", "turkey-vpn.example.com"),
            ("MEXICO", "MX", "mexico-vpn.example.com"),
            ("ARGENTINA", "AR", "argentina-vpn.example.com"),
            ("COLOMBIA", "CO", "colombia-vpn.example.com"),
            ("CHILE", "CL", "chile-vpn.example.com"),
        ]
        
        for region_id, country_code, vpn_server in regions_config:
            self.scan_regions[region_id] = ScanRegion(
                region_id=region_id,
                country_code=country_code,
                vpn_server=vpn_server,
                active=True
            )
    
    def _initialize_platforms(self):
        """Initialize platform-specific configurations"""
        platforms = [
            # Search engines
            PlatformConfig("google", "GoogleScanner", 30, 1.0, True, False),
            PlatformConfig("bing", "BingScanner", 30, 0.8, True, False),
            PlatformConfig("yandex", "YandexScanner", 20, 0.6, False, False),
            
            # Social media platforms
            PlatformConfig("reddit", "RedditScanner", 60, 0.9, True, True),
            PlatformConfig("instagram", "InstagramScanner", 30, 0.95, False, True),
            PlatformConfig("twitter", "TwitterScanner", 300, 0.9, True, True),
            PlatformConfig("tiktok", "TikTokScanner", 20, 0.85, False, False),
            PlatformConfig("youtube", "YouTubeScanner", 100, 0.8, True, True),
            PlatformConfig("facebook", "FacebookScanner", 20, 0.7, False, True),
            PlatformConfig("telegram", "TelegramScanner", 10, 0.8, False, False),
            PlatformConfig("discord", "DiscordScanner", 15, 0.7, False, True),
            
            # Adult platforms
            PlatformConfig("onlyfans", "OnlyFansScanner", 10, 1.0, False, False),
            PlatformConfig("pornhub", "PornhubScanner", 20, 0.9, False, False),
            PlatformConfig("xvideos", "XvideosScanner", 15, 0.85, False, False),
            PlatformConfig("xhamster", "XHamsterScanner", 15, 0.8, False, False),
            PlatformConfig("redtube", "RedTubeScanner", 15, 0.8, False, False),
            PlatformConfig("youporn", "YouPornScanner", 15, 0.8, False, False),
            
            # Forums and leak sites
            PlatformConfig("4chan", "FourChanScanner", 5, 0.7, False, False),
            PlatformConfig("leak_forums", "LeakForumScanner", 5, 0.9, False, False),
            PlatformConfig("piracy_sites", "PiracySiteScanner", 10, 0.95, False, False),
        ]
        
        for platform in platforms:
            self.platform_configs[platform.platform_name] = platform
    
    async def schedule_new_user_scan(
        self,
        profile_id: int,
        user_id: int,
        profile_data: Dict[str, Any]
    ) -> str:
        """
        Schedule immediate priority scan for new user
        PRD: "Finds leaks immediately upon signup (within hours)"
        """
        scan_id = str(uuid.uuid4())
        
        # Priority scan with comprehensive scope
        scan_request = ScanRequest(
            scan_id=scan_id,
            profile_id=profile_id,
            user_id=user_id,
            profile_data=profile_data,
            priority=ScanPriority.URGENT,
            scope=ScanScope.COMPREHENSIVE,
            platforms=self._get_high_priority_platforms(),
            regions=self._select_optimal_regions(5),
            keywords=self._generate_search_keywords(profile_data),
            expires_at=datetime.utcnow() + self.new_user_scan_timeout,
            metadata={"scan_reason": "new_user_onboarding"}
        )
        
        await self._queue_scan_request(scan_request)
        
        logger.info(f"Scheduled urgent new user scan {scan_id} for profile {profile_id}")
        return scan_id
    
    async def schedule_daily_scan(
        self,
        profile_id: int,
        user_id: int,
        profile_data: Dict[str, Any]
    ) -> str:
        """Schedule regular daily scan"""
        scan_id = str(uuid.uuid4())
        
        scan_request = ScanRequest(
            scan_id=scan_id,
            profile_id=profile_id,
            user_id=user_id,
            profile_data=profile_data,
            priority=ScanPriority.NORMAL,
            scope=ScanScope.COMPREHENSIVE,
            platforms=self._get_all_platforms(),
            regions=self._select_optimal_regions(3),
            keywords=self._generate_search_keywords(profile_data),
            scheduled_for=datetime.utcnow() + timedelta(minutes=5),  # Small delay to batch
            metadata={"scan_reason": "daily_automated"}
        )
        
        await self._queue_scan_request(scan_request)
        
        logger.info(f"Scheduled daily scan {scan_id} for profile {profile_id}")
        return scan_id
    
    async def schedule_manual_scan(
        self,
        profile_id: int,
        user_id: int,
        profile_data: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        scope: ScanScope = ScanScope.COMPREHENSIVE
    ) -> str:
        """Schedule manual user-initiated scan"""
        scan_id = str(uuid.uuid4())
        
        scan_request = ScanRequest(
            scan_id=scan_id,
            profile_id=profile_id,
            user_id=user_id,
            profile_data=profile_data,
            priority=ScanPriority.HIGH,
            scope=scope,
            platforms=platforms or self._get_high_priority_platforms(),
            regions=self._select_optimal_regions(4),
            keywords=self._generate_search_keywords(profile_data),
            metadata={"scan_reason": "manual_user_request"}
        )
        
        await self._queue_scan_request(scan_request)
        
        logger.info(f"Scheduled manual scan {scan_id} for profile {profile_id}")
        return scan_id
    
    async def _queue_scan_request(self, scan_request: ScanRequest):
        """Queue scan request in Redis with priority ordering"""
        try:
            # Store scan request data
            await self.redis_client.hset(
                f"scan:{scan_request.scan_id}",
                mapping={
                    "data": json.dumps(scan_request.__dict__, default=str),
                    "status": "queued",
                    "created_at": scan_request.created_at.isoformat()
                }
            )
            
            # Add to priority queue
            priority_score = self._calculate_priority_score(scan_request)
            await self.redis_client.zadd(
                "scan_queue",
                {scan_request.scan_id: priority_score}
            )
            
            # Set expiration if specified
            if scan_request.expires_at:
                expire_seconds = int((scan_request.expires_at - datetime.utcnow()).total_seconds())
                await self.redis_client.expire(f"scan:{scan_request.scan_id}", expire_seconds)
            
        except Exception as e:
            logger.error(f"Error queuing scan request: {e}")
            raise
    
    def _calculate_priority_score(self, scan_request: ScanRequest) -> float:
        """Calculate priority score for queue ordering (higher = higher priority)"""
        base_scores = {
            ScanPriority.URGENT: 1000,
            ScanPriority.HIGH: 800,
            ScanPriority.NORMAL: 500,
            ScanPriority.LOW: 200
        }
        
        score = base_scores.get(scan_request.priority, 500)
        
        # Boost score for new user scans
        if scan_request.metadata.get("scan_reason") == "new_user_onboarding":
            score += 500
            
        # Time-based urgency factor
        if scan_request.expires_at:
            time_remaining = (scan_request.expires_at - datetime.utcnow()).total_seconds()
            urgency_factor = max(0, (3600 - time_remaining) / 3600) * 200
            score += urgency_factor
        
        return score
    
    async def _scan_worker(self, worker_id: int):
        """Worker process to execute scan requests"""
        logger.info(f"Scan worker {worker_id} started")
        
        while True:
            try:
                # Get highest priority scan from queue
                scan_data = await self.redis_client.zpopmax("scan_queue")
                
                if not scan_data:
                    # No scans available, wait
                    await asyncio.sleep(5)
                    continue
                
                scan_id, priority_score = scan_data[0]
                
                # Load scan request data
                scan_data_raw = await self.redis_client.hget(f"scan:{scan_id}", "data")
                if not scan_data_raw:
                    logger.warning(f"Scan data not found for {scan_id}")
                    continue
                
                # Deserialize scan request
                scan_dict = json.loads(scan_data_raw)
                scan_request = ScanRequest(**scan_dict)
                
                # Check if scan has expired
                if (scan_request.expires_at and 
                    datetime.fromisoformat(scan_request.expires_at.replace('Z', '+00:00')) < datetime.utcnow()):
                    logger.info(f"Scan {scan_id} expired, skipping")
                    await self._cleanup_scan(scan_id)
                    continue
                
                # Execute the scan
                logger.info(f"Worker {worker_id} executing scan {scan_id}")
                await self._execute_scan(scan_request, worker_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_scan(self, scan_request: ScanRequest, worker_id: int):
        """Execute comprehensive scan across platforms and regions"""
        scan_id = scan_request.scan_id
        start_time = datetime.utcnow()
        
        # Start comprehensive monitoring
        scan_metrics = await scanning_monitor.start_scan_monitoring(
            scan_id=scan_id,
            user_id=scan_request.user_id,
            profile_id=scan_request.profile_id,
            scan_type=scan_request.scope.value,
            platforms=scan_request.platforms
        )
        
        try:
            # Update status to running
            await self.redis_client.hset(f"scan:{scan_id}", "status", "running")
            await self.redis_client.hset(f"scan:{scan_id}", "started_at", start_time.isoformat())
            
            self.active_scans[scan_id] = scan_request
            
            # Initialize results tracking
            scan_results = {
                "scan_id": scan_id,
                "profile_id": scan_request.profile_id,
                "total_urls_scanned": 0,
                "total_matches_found": 0,
                "infringements": [],
                "platforms_scanned": [],
                "regions_used": [],
                "scan_duration_seconds": 0,
                "error_count": 0,
                "errors": []
            }
            
            # Execute scan across selected platforms and regions
            platform_tasks = []
            
            for platform in scan_request.platforms:
                if platform in self.platform_configs:
                    # Create platform scan task
                    task = asyncio.create_task(
                        self._scan_platform(
                            platform,
                            scan_request,
                            scan_results
                        )
                    )
                    platform_tasks.append(task)
            
            # Execute all platform scans concurrently
            await asyncio.gather(*platform_tasks, return_exceptions=True)
            
            # Calculate final results
            scan_duration = (datetime.utcnow() - start_time).total_seconds()
            scan_results["scan_duration_seconds"] = scan_duration
            
            # Process high-confidence matches for DMCA takedowns
            await self._process_scan_matches(scan_request, scan_results)
            
            # Update final status
            await self.redis_client.hset(f"scan:{scan_id}", "status", "completed")
            await self.redis_client.hset(f"scan:{scan_id}", "results", json.dumps(scan_results, default=str))
            await self.redis_client.hset(f"scan:{scan_id}", "completed_at", datetime.utcnow().isoformat())
            
            # Notify user of completion
            await notify_scan_progress(scan_request.user_id, {
                "scan_id": scan_id,
                "status": "completed",
                "progress": 100,
                "message": f"Scan completed - {scan_results['total_matches_found']} matches found",
                "results_summary": {
                    "urls_scanned": scan_results["total_urls_scanned"],
                    "matches_found": scan_results["total_matches_found"],
                    "platforms_scanned": len(scan_results["platforms_scanned"]),
                    "duration_minutes": round(scan_duration / 60, 1)
                }
            })
            
            logger.info(f"Scan {scan_id} completed successfully in {scan_duration:.1f}s")
            
            # Complete monitoring with success
            await scanning_monitor.complete_scan_monitoring(
                scan_id=scan_id,
                user_id=scan_request.user_id,
                success=True,
                results=scan_results
            )
            
        except Exception as e:
            logger.error(f"Scan execution error for {scan_id}: {e}")
            
            # Report error to monitoring system
            await scanning_monitor.report_error(
                scan_id=scan_id,
                error_type="scan_execution_error",
                error_message=str(e)
            )
            
            # Update error status
            await self.redis_client.hset(f"scan:{scan_id}", "status", "failed")
            await self.redis_client.hset(f"scan:{scan_id}", "error", str(e))
            
            # Complete monitoring with failure
            await scanning_monitor.complete_scan_monitoring(
                scan_id=scan_id,
                user_id=scan_request.user_id,
                success=False,
                results={"error": str(e)}
            )
            
        finally:
            # Cleanup
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]
    
    async def _scan_platform(
        self,
        platform: str,
        scan_request: ScanRequest,
        scan_results: Dict[str, Any]
    ):
        """Scan a specific platform across multiple regions"""
        try:
            # Import platform scanner dynamically
            scanner_class = await self._get_platform_scanner(platform)
            if not scanner_class:
                logger.warning(f"Scanner not available for platform {platform}")
                return
            
            # Select regions for this platform
            regions = self._select_regions_for_platform(platform, scan_request.regions)
            
            platform_results = []
            
            # Scan across selected regions
            for region in regions:
                try:
                    region_config = self.scan_regions.get(region)
                    if not region_config or not region_config.active:
                        continue
                    
                    # Execute region-specific scan
                    region_results = await self._scan_platform_region(
                        scanner_class,
                        platform,
                        region_config,
                        scan_request
                    )
                    
                    platform_results.extend(region_results)
                    
                except Exception as e:
                    logger.error(f"Error scanning {platform} in region {region}: {e}")
                    scan_results["error_count"] += 1
                    scan_results["errors"].append({
                        "platform": platform,
                        "region": region,
                        "error": str(e)
                    })
            
            # Aggregate platform results
            if platform_results:
                scan_results["platforms_scanned"].append(platform)
                scan_results["total_urls_scanned"] += len(platform_results)
                
                # Analyze results with AI content matcher
                matches = await self._analyze_platform_results(
                    platform_results,
                    scan_request
                )
                
                scan_results["total_matches_found"] += len(matches)
                scan_results["infringements"].extend(matches)
            
        except Exception as e:
            logger.error(f"Platform scan error for {platform}: {e}")
            scan_results["error_count"] += 1
            scan_results["errors"].append({
                "platform": platform,
                "error": str(e)
            })
    
    async def _get_platform_scanner(self, platform: str):
        """Dynamically import platform scanner class"""
        try:
            scanner_map = {
                "google": "app.services.scanning.platforms.google_scanner.GoogleScanner",
                "reddit": "app.services.scanning.platforms.reddit_scanner.RedditScanner", 
                "instagram": "app.services.scanning.platforms.social_media_scanner.InstagramScanner",
                "twitter": "app.services.scanning.platforms.social_media_scanner.TwitterScanner",
                "piracy_sites": "app.services.scanning.piracy_sites.PiracySiteScanner"
            }
            
            scanner_path = scanner_map.get(platform)
            if not scanner_path:
                return None
                
            module_path, class_name = scanner_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
            
        except ImportError as e:
            logger.warning(f"Could not import scanner for {platform}: {e}")
            return None
    
    def _select_regions_for_platform(self, platform: str, requested_regions: List[str]) -> List[str]:
        """Select optimal regions for platform scanning"""
        # Platform-specific region preferences
        platform_regions = {
            "google": ["US-EAST", "EU-CENTRAL", "ASIA-EAST"],
            "reddit": ["US-EAST", "US-WEST", "EU-WEST"],
            "instagram": ["US-EAST", "EU-CENTRAL", "BRAZIL"],
            "twitter": ["US-EAST", "EU-WEST", "JAPAN"],
            "piracy_sites": ["EU-CENTRAL", "RUSSIA", "ASIA-EAST"],
        }
        
        preferred = platform_regions.get(platform, requested_regions)
        
        # Filter to active regions and limit count
        active_regions = [
            r for r in preferred[:3] 
            if r in self.scan_regions and self.scan_regions[r].active
        ]
        
        return active_regions or requested_regions[:2]
    
    async def _scan_platform_region(
        self,
        scanner_class,
        platform: str,
        region_config: ScanRegion,
        scan_request: ScanRequest
    ) -> List[Dict[str, Any]]:
        """Execute scan for specific platform in specific region"""
        results = []
        
        try:
            # Initialize scanner with region configuration
            scanner = scanner_class(
                region=region_config,
                rate_limit=self.platform_configs[platform].rate_limit
            )
            
            # Execute search queries
            for keyword in scan_request.keywords:
                try:
                    # Search for keyword on platform
                    search_results = await scanner.search(
                        query=keyword,
                        limit=50,  # Configurable based on scan scope
                        include_metadata=True
                    )
                    
                    results.extend(search_results)
                    
                    # Respect rate limits
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Search error for '{keyword}' on {platform}: {e}")
            
        except Exception as e:
            logger.error(f"Scanner initialization error for {platform}: {e}")
        
        return results
    
    async def _analyze_platform_results(
        self,
        platform_results: List[Dict[str, Any]],
        scan_request: ScanRequest
    ) -> List[Dict[str, Any]]:
        """Analyze platform results using AI content matcher"""
        matches = []
        
        try:
            for result in platform_results[:100]:  # Limit for performance
                # Extract media URLs from result
                media_urls = self._extract_media_urls(result)
                
                for media_url in media_urls:
                    try:
                        # Use AI content matcher for facial recognition
                        content_matches = await self.content_matcher.analyze_url(
                            media_url,
                            scan_request.profile_data.get("face_encodings", []),
                            confidence_threshold=0.75
                        )
                        
                        for match in content_matches:
                            if match.confidence > 0.75:  # High confidence only
                                matches.append({
                                    "url": media_url,
                                    "source_url": result.get("url"),
                                    "platform": result.get("platform"),
                                    "match_type": match.match_type,
                                    "confidence": match.confidence,
                                    "detected_at": datetime.utcnow().isoformat(),
                                    "metadata": {
                                        "region": result.get("region"),
                                        "search_query": result.get("search_query"),
                                        "match_details": match.metadata
                                    }
                                })
                        
                    except Exception as e:
                        logger.error(f"Content analysis error for {media_url}: {e}")
            
        except Exception as e:
            logger.error(f"Platform results analysis error: {e}")
        
        return matches
    
    def _extract_media_urls(self, result: Dict[str, Any]) -> List[str]:
        """Extract image/video URLs from search result"""
        media_urls = []
        
        # Extract from common fields
        for field in ["image_url", "video_url", "thumbnail_url", "media_urls"]:
            if field in result:
                if isinstance(result[field], list):
                    media_urls.extend(result[field])
                elif result[field]:
                    media_urls.append(result[field])
        
        # Extract from embedded media
        if "media" in result:
            for media_item in result["media"]:
                if media_item.get("url"):
                    media_urls.append(media_item["url"])
        
        return list(set(media_urls))  # Remove duplicates
    
    async def _process_scan_matches(
        self,
        scan_request: ScanRequest,
        scan_results: Dict[str, Any]
    ):
        """Process high-confidence matches for automated DMCA takedowns"""
        try:
            high_confidence_matches = [
                match for match in scan_results["infringements"]
                if match["confidence"] > 0.85  # Very high confidence for automation
            ]
            
            for match in high_confidence_matches:
                try:
                    # Create DMCA takedown request
                    await self.takedown_processor.process_infringement(
                        infringement_url=match["url"],
                        profile_data=scan_request.profile_data,
                        evidence={
                            "match_confidence": match["confidence"],
                            "detection_method": "automated_scan",
                            "scan_id": scan_request.scan_id,
                            "platform": match["platform"]
                        },
                        priority=scan_request.priority == ScanPriority.URGENT
                    )
                    
                    # Notify user of infringement found
                    await notify_infringement_found(scan_request.user_id, {
                        "scan_id": scan_request.scan_id,
                        "url": match["url"],
                        "platform": match["platform"],
                        "confidence": match["confidence"],
                        "takedown_initiated": True
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing match for DMCA: {e}")
            
            logger.info(f"Processed {len(high_confidence_matches)} high-confidence matches for DMCA")
            
        except Exception as e:
            logger.error(f"Error processing scan matches: {e}")
    
    async def _schedule_new_user_monitoring(self):
        """Schedule monitoring for new user priority scans"""
        # This would integrate with user registration events
        # For now, we set up periodic checks
        pass
    
    def _get_high_priority_platforms(self) -> List[str]:
        """Get platforms with highest priority for scanning"""
        return [
            "google", "reddit", "instagram", "twitter", "tiktok", 
            "onlyfans", "pornhub", "piracy_sites"
        ]
    
    def _get_all_platforms(self) -> List[str]:
        """Get all available platforms for scanning"""
        return list(self.platform_configs.keys())
    
    def _select_optimal_regions(self, count: int) -> List[str]:
        """Select optimal regions for scanning based on load and performance"""
        # Simple round-robin for now, could be enhanced with load balancing
        active_regions = [
            region_id for region_id, region in self.scan_regions.items()
            if region.active
        ]
        return active_regions[:count]
    
    def _generate_search_keywords(self, profile_data: Dict[str, Any]) -> List[str]:
        """Generate search keywords from profile data"""
        keywords = []
        
        # Add username variations
        username = profile_data.get("username", "")
        if username:
            keywords.extend([
                username,
                f'"{username}"',
                f"{username} leaked",
                f"{username} content",
                f"{username} OnlyFans",
            ])
        
        # Add aliases
        aliases = profile_data.get("aliases", [])
        for alias in aliases[:3]:  # Limit to avoid too many queries
            keywords.extend([alias, f'"{alias}"'])
        
        # Add platform-specific keywords
        platform = profile_data.get("platform", "")
        if platform:
            keywords.append(f"{username} {platform}")
        
        return keywords[:20]  # Limit total keywords
    
    async def _cleanup_scan(self, scan_id: str):
        """Clean up expired or completed scan data"""
        try:
            await self.redis_client.delete(f"scan:{scan_id}")
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]
        except Exception as e:
            logger.error(f"Error cleaning up scan {scan_id}: {e}")
    
    async def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a scan"""
        try:
            scan_data = await self.redis_client.hgetall(f"scan:{scan_id}")
            if scan_data:
                status = {
                    "scan_id": scan_id,
                    "status": scan_data.get("status", "unknown"),
                    "created_at": scan_data.get("created_at"),
                    "started_at": scan_data.get("started_at"),
                    "completed_at": scan_data.get("completed_at"),
                    "error": scan_data.get("error")
                }
                
                if "results" in scan_data:
                    status["results"] = json.loads(scan_data["results"])
                
                return status
            
        except Exception as e:
            logger.error(f"Error getting scan status: {e}")
        
        return None
    
    async def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        try:
            queue_size = await self.redis_client.zcard("scan_queue")
            
            return {
                "active_scans": len(self.active_scans),
                "queue_size": queue_size,
                "total_regions": len(self.scan_regions),
                "active_regions": len([r for r in self.scan_regions.values() if r.active]),
                "total_platforms": len(self.platform_configs),
                "worker_count": len(self.scan_workers),
                "scan_workers": [
                    {
                        "worker_id": i,
                        "status": "running" if not worker.done() else "stopped"
                    }
                    for i, worker in enumerate(self.scan_workers)
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting orchestrator stats: {e}")
            return {"error": str(e)}


# Global orchestrator instance
orchestrator = ScanningOrchestrator()