"""
Scanning Job Scheduler and Queue System
Manages automated daily scans and job processing
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from enum import Enum
from dataclasses import dataclass
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import redis.asyncio as redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.scanning.web_crawler import WebCrawler
from app.services.ai.content_matcher import ContentMatcher
from app.services.dmca.takedown_processor import DMCATakedownProcessor
from app.services.scanning.search_engines import SearchEngineScanner

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScanJob:
    """Scanning job data"""
    job_id: str
    profile_id: int
    profile_data: Dict[str, Any]
    scan_type: str  # 'daily', 'manual', 'priority'
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScanningScheduler:
    """
    Manages automated scanning schedules and job processing
    PRD: "continuous or daily scans of the internet"
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.redis_client: Optional[redis.Redis] = None
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.active_jobs: Dict[str, ScanJob] = {}
        self.max_concurrent_scans = 10
        self.workers: List[asyncio.Task] = []
        
        # Services
        self.crawler = WebCrawler()
        self.content_matcher = ContentMatcher()
        self.takedown_processor = DMCATakedownProcessor()
        
    async def initialize(self):
        """Initialize scheduler and connections"""
        try:
            # Connect to Redis for job queue
            self.redis_client = await redis.from_url(
                os.getenv('REDIS_URL', 'redis://localhost:6379'),
                encoding="utf-8",
                decode_responses=True
            )
            
            # Start scheduler
            self.scheduler.start()
            
            # Schedule daily scans
            self._schedule_daily_scans()
            
            # Start worker tasks
            for i in range(self.max_concurrent_scans):
                worker = asyncio.create_task(self._job_worker(i))
                self.workers.append(worker)
                
            logger.info("Scanning scheduler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            
    async def shutdown(self):
        """Shutdown scheduler and workers"""
        try:
            # Stop scheduler
            self.scheduler.shutdown()
            
            # Cancel workers
            for worker in self.workers:
                worker.cancel()
                
            # Close connections
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("Scanning scheduler shutdown")
            
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")
            
    def _schedule_daily_scans(self):
        """
        Schedule daily automated scans for all active profiles
        PRD: "Daily scans for infringements across web"
        """
        
        # Schedule daily scan at 2 AM
        self.scheduler.add_job(
            self._run_daily_scans,
            CronTrigger(hour=2, minute=0),
            id='daily_scan',
            name='Daily Content Scan',
            replace_existing=True
        )
        
        # Schedule hourly quick scans for priority profiles
        self.scheduler.add_job(
            self._run_priority_scans,
            IntervalTrigger(hours=1),
            id='priority_scan',
            name='Priority Profile Scan',
            replace_existing=True
        )
        
        # Schedule search engine index checks every 6 hours
        self.scheduler.add_job(
            self._check_delisting_status,
            IntervalTrigger(hours=6),
            id='delisting_check',
            name='Search Engine Delisting Check',
            replace_existing=True
        )
        
        logger.info("Scheduled automated scans configured")
        
    async def _run_daily_scans(self):
        """Execute daily scans for all active profiles"""
        logger.info("Starting daily scan cycle")
        
        try:
            # Get all active profiles from database
            # In production, this would query the database
            profiles = await self._get_active_profiles()
            
            for profile in profiles:
                # Create scan job
                job = ScanJob(
                    job_id=f"daily_{profile['id']}_{datetime.utcnow().timestamp()}",
                    profile_id=profile['id'],
                    profile_data=profile,
                    scan_type='daily',
                    status=JobStatus.QUEUED,
                    created_at=datetime.utcnow()
                )
                
                # Queue the job
                await self.queue_scan_job(job)
                
            logger.info(f"Queued {len(profiles)} daily scan jobs")
            
        except Exception as e:
            logger.error(f"Error in daily scan: {e}")
            
    async def _run_priority_scans(self):
        """Execute priority scans for premium profiles"""
        logger.info("Starting priority scan cycle")
        
        try:
            # Get priority profiles (premium tier)
            profiles = await self._get_priority_profiles()
            
            for profile in profiles:
                job = ScanJob(
                    job_id=f"priority_{profile['id']}_{datetime.utcnow().timestamp()}",
                    profile_id=profile['id'],
                    profile_data=profile,
                    scan_type='priority',
                    status=JobStatus.QUEUED,
                    created_at=datetime.utcnow()
                )
                
                await self.queue_scan_job(job)
                
            logger.info(f"Queued {len(profiles)} priority scan jobs")
            
        except Exception as e:
            logger.error(f"Error in priority scan: {e}")
            
    async def _check_delisting_status(self):
        """Check status of previous delisting requests"""
        logger.info("Checking delisting status")
        
        try:
            # Get pending delisting requests
            # In production, this would query the database
            pending_delistings = await self._get_pending_delistings()
            
            scanner = SearchEngineScanner()
            async with scanner:
                for delisting in pending_delistings:
                    indexed = await scanner.check_url_in_search_index(
                        delisting['url']
                    )
                    
                    if not indexed['google'] and not indexed['bing']:
                        # Update status to delisted
                        await self._update_delisting_status(
                            delisting['id'], 
                            'delisted'
                        )
                        
        except Exception as e:
            logger.error(f"Error checking delisting status: {e}")
            
    async def queue_scan_job(self, job: ScanJob):
        """Add a scan job to the queue"""
        try:
            # Add to Redis queue
            if self.redis_client:
                await self.redis_client.lpush(
                    'scan_queue',
                    json.dumps({
                        'job_id': job.job_id,
                        'profile_id': job.profile_id,
                        'profile_data': job.profile_data,
                        'scan_type': job.scan_type,
                        'created_at': job.created_at.isoformat()
                    })
                )
                
            # Also add to in-memory queue
            await self.job_queue.put(job)
            
            logger.info(f"Queued scan job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error queuing job: {e}")
            
    async def _job_worker(self, worker_id: int):
        """Worker task to process scan jobs"""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get job from queue
                job = await self.job_queue.get()
                
                if job:
                    logger.info(f"Worker {worker_id} processing job {job.job_id}")
                    
                    # Update job status
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.utcnow()
                    self.active_jobs[job.job_id] = job
                    
                    # Execute scan
                    results = await self._execute_scan(job)
                    
                    # Update job with results
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    job.results = results
                    
                    # Process results (create takedown requests)
                    await self._process_scan_results(job, results)
                    
                    # Remove from active jobs
                    del self.active_jobs[job.job_id]
                    
                    logger.info(f"Worker {worker_id} completed job {job.job_id}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    
            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.1)
            
    async def _execute_scan(self, job: ScanJob) -> Dict[str, Any]:
        """Execute the actual scanning process"""
        results = {
            'urls_scanned': 0,
            'matches_found': 0,
            'infringements': [],
            'scan_duration': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            async with self.crawler:
                # Perform web crawling
                crawl_results = await self.crawler.scan_for_profile(
                    job.profile_data,
                    deep_scan=(job.scan_type == 'priority')
                )
                
                results['urls_scanned'] = len(crawl_results)
                
                # Analyze each result for content matches
                for crawl_result in crawl_results:
                    if crawl_result.status == 'completed':
                        # Check images
                        for image_url in crawl_result.images[:20]:  # Limit for performance
                            matches = await self._check_content_match(
                                image_url,
                                job.profile_data
                            )
                            
                            if matches:
                                results['matches_found'] += len(matches)
                                results['infringements'].append({
                                    'url': image_url,
                                    'page_url': crawl_result.url,
                                    'matches': matches,
                                    'confidence': max(m['confidence'] for m in matches)
                                })
                                
                        # Check videos
                        for video_url in crawl_result.videos[:10]:  # Limit for performance
                            matches = await self._check_content_match(
                                video_url,
                                job.profile_data
                            )
                            
                            if matches:
                                results['matches_found'] += len(matches)
                                results['infringements'].append({
                                    'url': video_url,
                                    'page_url': crawl_result.url,
                                    'matches': matches,
                                    'confidence': max(m['confidence'] for m in matches)
                                })
                                
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            results['error'] = str(e)
            
        results['scan_duration'] = (
            datetime.utcnow() - start_time
        ).total_seconds()
        
        return results
        
    async def _check_content_match(
        self,
        content_url: str,
        profile_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check if content matches profile"""
        matches = []
        
        try:
            # Download content
            async with aiohttp.ClientSession() as session:
                async with session.get(content_url) as response:
                    if response.status == 200:
                        content_data = await response.read()
                        
                        # Use AI matcher
                        content_matches = await self.content_matcher.analyze_content(
                            content_url,
                            content_data,
                            profile_data
                        )
                        
                        for match in content_matches:
                            if match.confidence > 0.7:  # Confidence threshold
                                matches.append({
                                    'type': match.match_type,
                                    'confidence': match.confidence,
                                    'metadata': match.metadata
                                })
                                
        except Exception as e:
            logger.error(f"Error checking content match: {e}")
            
        return matches
        
    async def _process_scan_results(
        self,
        job: ScanJob,
        results: Dict[str, Any]
    ):
        """Process scan results and create takedown requests"""
        try:
            infringements = results.get('infringements', [])
            
            for infringement in infringements:
                # Only process high-confidence matches
                if infringement['confidence'] > 0.8:
                    # Create takedown request
                    await self.takedown_processor.process_infringement(
                        infringement_url=infringement['url'],
                        profile_data=job.profile_data,
                        original_content_url=job.profile_data.get('profile_url'),
                        priority=(job.scan_type == 'priority')
                    )
                    
            # Store results in database
            await self._store_scan_results(job, results)
            
            # Send notifications if configured
            if infringements:
                await self._send_scan_notifications(job, results)
                
        except Exception as e:
            logger.error(f"Error processing scan results: {e}")
            
    async def _get_active_profiles(self) -> List[Dict[str, Any]]:
        """Get all active profiles from database"""
        # Placeholder - would query database
        return [
            {
                'id': 1,
                'username': 'test_creator',
                'platform': 'onlyfans',
                'profile_url': 'https://onlyfans.com/test_creator',
                'face_encodings': [],
                'keywords': ['test_creator', 'exclusive content']
            }
        ]
        
    async def _get_priority_profiles(self) -> List[Dict[str, Any]]:
        """Get priority/premium profiles"""
        # Placeholder - would query database for premium tier users
        return []
        
    async def _get_pending_delistings(self) -> List[Dict[str, Any]]:
        """Get pending delisting requests"""
        # Placeholder - would query database
        return []
        
    async def _update_delisting_status(self, delisting_id: int, status: str):
        """Update delisting status in database"""
        # Placeholder - would update database
        pass
        
    async def _store_scan_results(self, job: ScanJob, results: Dict[str, Any]):
        """Store scan results in database"""
        # Placeholder - would store in database
        logger.info(f"Storing results for job {job.job_id}: {results['matches_found']} matches")
        
    async def _send_scan_notifications(self, job: ScanJob, results: Dict[str, Any]):
        """Send notifications about scan results"""
        # Placeholder - would send email/push notifications
        logger.info(f"Sending notifications for {len(results['infringements'])} infringements")
        
    async def trigger_manual_scan(
        self,
        profile_id: int,
        profile_data: Dict[str, Any]
    ) -> str:
        """Trigger a manual scan for a profile"""
        job = ScanJob(
            job_id=f"manual_{profile_id}_{datetime.utcnow().timestamp()}",
            profile_id=profile_id,
            profile_data=profile_data,
            scan_type='manual',
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        
        await self.queue_scan_job(job)
        
        return job.job_id
        
    def get_job_status(self, job_id: str) -> Optional[ScanJob]:
        """Get status of a specific job"""
        return self.active_jobs.get(job_id)
        
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        queue_size = 0
        if self.redis_client:
            queue_size = await self.redis_client.llen('scan_queue')
            
        return {
            'queue_size': queue_size,
            'active_jobs': len(self.active_jobs),
            'workers': len(self.workers),
            'scheduled_jobs': len(self.scheduler.get_jobs())
        }


import os
import aiohttp