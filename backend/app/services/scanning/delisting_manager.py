"""
Search Engine Delisting Request Management System
Handles batch processing, queuing, and lifecycle management of delisting requests
PRD: "Request queuing and rate limiting", "Retry logic for failed submissions"
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from collections import defaultdict, deque
import heapq

from app.services.scanning.delisting_service import (
    SearchEngineDelistingService, 
    DelistingRequest, 
    DelistingResult, 
    DelistingStatus, 
    SearchEngine
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestPriority(str, Enum):
    """Priority levels for delisting requests"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class QueuedRequest:
    """Queued delisting request with priority and scheduling"""
    id: str
    url: str
    search_engines: List[SearchEngine]
    priority: RequestPriority
    scheduled_time: datetime
    created_time: datetime
    retry_count: int = 0
    max_retries: int = 3
    reason: str = "Copyright infringement"
    evidence_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering"""
        priority_order = {
            RequestPriority.URGENT: 0,
            RequestPriority.HIGH: 1,
            RequestPriority.NORMAL: 2,
            RequestPriority.LOW: 3
        }
        return (
            priority_order[self.priority],
            self.scheduled_time
        ) < (
            priority_order[other.priority],
            other.scheduled_time
        )


@dataclass
class BatchRequest:
    """Batch of related delisting requests"""
    id: str
    requests: List[QueuedRequest]
    created_time: datetime
    status: str = "pending"
    batch_size: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)


class DelistingRequestManager:
    """
    Manages the lifecycle of delisting requests with queuing, batching, and retry logic
    PRD: "Batch processing", "Request queuing and rate limiting", "Retry logic"
    """
    
    def __init__(self):
        self.delisting_service = None
        
        # Request queues by priority
        self.request_queue = []  # Priority queue
        self.processing_queue = set()  # Currently processing
        self.completed_requests = {}  # Request ID -> Results
        self.failed_requests = {}  # Request ID -> Error info
        
        # Batch management
        self.pending_batches = {}  # Batch ID -> BatchRequest
        self.active_batches = {}  # Batch ID -> BatchRequest
        self.completed_batches = {}  # Batch ID -> Results
        
        # Rate limiting and scheduling
        self.rate_limiters = {
            engine: {
                'requests_per_hour': deque(),
                'requests_per_day': deque(),
                'last_request': None
            } for engine in SearchEngine
        }
        
        # Configuration
        self.max_concurrent_requests = 50
        self.default_batch_size = 10
        self.retry_delays = [300, 900, 3600]  # 5min, 15min, 1hour
        self.request_timeout = 60
        
        # Statistics
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retried': 0,
            'success_rate': 0.0,
            'average_processing_time': 0.0
        }
        
        # Background task control
        self._running = False
        self._processor_task = None
        self._monitor_task = None
        
    async def start(self):
        """Start the delisting request manager"""
        if self._running:
            return
            
        self._running = True
        self.delisting_service = SearchEngineDelistingService()
        await self.delisting_service.__aenter__()
        
        # Start background processors
        self._processor_task = asyncio.create_task(self._process_queue())
        self._monitor_task = asyncio.create_task(self._monitor_requests())
        
        logger.info("Delisting request manager started")
        
    async def stop(self):
        """Stop the delisting request manager"""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel background tasks
        if self._processor_task:
            self._processor_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
            
        # Cleanup delisting service
        if self.delisting_service:
            await self.delisting_service.__aexit__(None, None, None)
            
        logger.info("Delisting request manager stopped")

    async def submit_url_removal(
        self,
        url: str,
        search_engines: List[SearchEngine] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        reason: str = "Copyright infringement",
        evidence_url: Optional[str] = None,
        schedule_delay: Optional[timedelta] = None
    ) -> str:
        """
        Submit a single URL for removal with priority and scheduling
        Returns: Request ID for tracking
        """
        if search_engines is None:
            search_engines = [SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.YANDEX]
            
        request_id = str(uuid.uuid4())
        scheduled_time = datetime.utcnow()
        
        if schedule_delay:
            scheduled_time += schedule_delay
            
        request = QueuedRequest(
            id=request_id,
            url=url,
            search_engines=search_engines,
            priority=priority,
            scheduled_time=scheduled_time,
            created_time=datetime.utcnow(),
            reason=reason,
            evidence_url=evidence_url
        )
        
        # Add to priority queue
        heapq.heappush(self.request_queue, request)
        
        logger.info(f"Queued delisting request {request_id} for {url} with priority {priority}")
        return request_id

    async def submit_batch_removal(
        self,
        urls: List[str],
        search_engines: List[SearchEngine] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        reason: str = "Copyright infringement",
        evidence_url: Optional[str] = None,
        batch_size: int = None
    ) -> str:
        """
        Submit multiple URLs for removal as a batch
        Returns: Batch ID for tracking
        """
        if search_engines is None:
            search_engines = [SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.YANDEX]
            
        if batch_size is None:
            batch_size = self.default_batch_size
            
        batch_id = str(uuid.uuid4())
        
        # Create individual requests for each URL
        requests = []
        for url in urls:
            request = QueuedRequest(
                id=str(uuid.uuid4()),
                url=url,
                search_engines=search_engines,
                priority=priority,
                scheduled_time=datetime.utcnow(),
                created_time=datetime.utcnow(),
                reason=reason,
                evidence_url=evidence_url,
                metadata={'batch_id': batch_id}
            )
            requests.append(request)
            
        # Create batch
        batch = BatchRequest(
            id=batch_id,
            requests=requests,
            created_time=datetime.utcnow(),
            batch_size=batch_size
        )
        
        self.pending_batches[batch_id] = batch
        
        # Add requests to queue in chunks
        for i in range(0, len(requests), batch_size):
            chunk = requests[i:i + batch_size]
            for request in chunk:
                heapq.heappush(self.request_queue, request)
                
        logger.info(f"Queued batch {batch_id} with {len(urls)} URLs")
        return batch_id

    async def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get the status of a specific request"""
        # Check if completed
        if request_id in self.completed_requests:
            return {
                'status': 'completed',
                'results': self.completed_requests[request_id],
                'request_id': request_id
            }
            
        # Check if failed
        if request_id in self.failed_requests:
            return {
                'status': 'failed',
                'error': self.failed_requests[request_id],
                'request_id': request_id
            }
            
        # Check if processing
        if request_id in self.processing_queue:
            return {
                'status': 'processing',
                'request_id': request_id
            }
            
        # Check if still in queue
        for request in self.request_queue:
            if request.id == request_id:
                return {
                    'status': 'queued',
                    'scheduled_time': request.scheduled_time.isoformat(),
                    'priority': request.priority,
                    'request_id': request_id
                }
                
        return {
            'status': 'not_found',
            'request_id': request_id
        }

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get the status of a batch request"""
        # Check completed batches
        if batch_id in self.completed_batches:
            return {
                'status': 'completed',
                'results': self.completed_batches[batch_id],
                'batch_id': batch_id
            }
            
        # Check active batches
        if batch_id in self.active_batches:
            batch = self.active_batches[batch_id]
            completed_count = 0
            failed_count = 0
            
            for request in batch.requests:
                if request.id in self.completed_requests:
                    completed_count += 1
                elif request.id in self.failed_requests:
                    failed_count += 1
                    
            return {
                'status': 'processing',
                'total_requests': len(batch.requests),
                'completed': completed_count,
                'failed': failed_count,
                'remaining': len(batch.requests) - completed_count - failed_count,
                'batch_id': batch_id
            }
            
        # Check pending batches
        if batch_id in self.pending_batches:
            return {
                'status': 'pending',
                'total_requests': len(self.pending_batches[batch_id].requests),
                'batch_id': batch_id
            }
            
        return {
            'status': 'not_found',
            'batch_id': batch_id
        }

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending or queued request"""
        # Remove from queue if still there
        new_queue = []
        found = False
        
        while self.request_queue:
            request = heapq.heappop(self.request_queue)
            if request.id != request_id:
                new_queue.append(request)
            else:
                found = True
                
        # Rebuild queue
        for request in new_queue:
            heapq.heappush(self.request_queue, request)
            
        if found:
            logger.info(f"Cancelled request {request_id}")
            
        return found

    async def retry_failed_requests(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Retry failed requests that are within the max age
        PRD: "Retry logic for failed submissions"
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        retried_count = 0
        
        failed_to_retry = []
        
        for request_id, error_info in list(self.failed_requests.items()):
            if error_info.get('timestamp', cutoff_time) < cutoff_time:
                continue
                
            original_request = error_info.get('original_request')
            if not original_request or original_request.retry_count >= original_request.max_retries:
                continue
                
            # Schedule retry with exponential backoff
            delay_index = min(original_request.retry_count, len(self.retry_delays) - 1)
            retry_delay = timedelta(seconds=self.retry_delays[delay_index])
            
            # Update request
            original_request.retry_count += 1
            original_request.scheduled_time = datetime.utcnow() + retry_delay
            
            # Re-queue
            heapq.heappush(self.request_queue, original_request)
            failed_to_retry.append(request_id)
            retried_count += 1
            
        # Remove from failed requests
        for request_id in failed_to_retry:
            del self.failed_requests[request_id]
            
        self.stats['total_retried'] += retried_count
        
        logger.info(f"Retried {retried_count} failed requests")
        
        return {
            'retried_count': retried_count,
            'total_failed': len(self.failed_requests)
        }

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue and processing statistics"""
        return {
            'queue_length': len(self.request_queue),
            'processing_count': len(self.processing_queue),
            'completed_count': len(self.completed_requests),
            'failed_count': len(self.failed_requests),
            'pending_batches': len(self.pending_batches),
            'active_batches': len(self.active_batches),
            'completed_batches': len(self.completed_batches),
            'rate_limits': self._get_rate_limit_status(),
            'statistics': self.stats.copy()
        }

    async def _process_queue(self):
        """Background task to process the request queue"""
        while self._running:
            try:
                # Process ready requests
                current_time = datetime.utcnow()
                ready_requests = []
                
                # Get all requests that are ready to process
                temp_queue = []
                while self.request_queue:
                    request = heapq.heappop(self.request_queue)
                    if request.scheduled_time <= current_time and len(self.processing_queue) < self.max_concurrent_requests:
                        if self._can_process_request(request):
                            ready_requests.append(request)
                        else:
                            # Reschedule for later
                            request.scheduled_time = current_time + timedelta(minutes=5)
                            temp_queue.append(request)
                    else:
                        temp_queue.append(request)
                        
                # Put back unprocessed requests
                for request in temp_queue:
                    heapq.heappush(self.request_queue, request)
                    
                # Process ready requests
                if ready_requests:
                    await self._process_requests_batch(ready_requests)
                    
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(10)

    async def _process_requests_batch(self, requests: List[QueuedRequest]):
        """Process a batch of ready requests"""
        for request in requests:
            self.processing_queue.add(request.id)
            
        # Create tasks for concurrent processing
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._process_single_request(request))
            tasks.append(task)
            
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for request, result in zip(requests, results):
            self.processing_queue.discard(request.id)
            
            if isinstance(result, Exception):
                self._handle_request_failure(request, str(result))
            else:
                self._handle_request_success(request, result)

    async def _process_single_request(self, request: QueuedRequest) -> Dict[SearchEngine, DelistingResult]:
        """Process a single delisting request"""
        try:
            start_time = datetime.utcnow()
            
            # Submit to search engines
            results = await self.delisting_service.submit_url_removal(
                url=request.url,
                search_engines=request.search_engines,
                reason=request.reason,
                evidence_url=request.evidence_url,
                priority=(request.priority in [RequestPriority.HIGH, RequestPriority.URGENT])
            )
            
            # Update rate limiting
            for engine in request.search_engines:
                self._update_rate_limit(engine)
                
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_processing_stats(processing_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing request {request.id}: {e}")
            raise

    def _handle_request_success(self, request: QueuedRequest, results: Dict[SearchEngine, DelistingResult]):
        """Handle successful request completion"""
        self.completed_requests[request.id] = {
            'request': request,
            'results': results,
            'completed_time': datetime.utcnow()
        }
        
        # Update batch status if applicable
        batch_id = request.metadata.get('batch_id')
        if batch_id:
            self._update_batch_status(batch_id)
            
        self.stats['total_completed'] += 1
        
        # Calculate success rate
        successful_engines = sum(1 for result in results.values() if result.success)
        if successful_engines > 0:
            logger.info(f"Request {request.id} completed successfully for {successful_engines}/{len(results)} engines")

    def _handle_request_failure(self, request: QueuedRequest, error: str):
        """Handle request failure"""
        self.failed_requests[request.id] = {
            'request': request,
            'original_request': request,
            'error': error,
            'timestamp': datetime.utcnow()
        }
        
        # Update batch status if applicable
        batch_id = request.metadata.get('batch_id')
        if batch_id:
            self._update_batch_status(batch_id)
            
        self.stats['total_failed'] += 1
        
        logger.error(f"Request {request.id} failed: {error}")

    def _can_process_request(self, request: QueuedRequest) -> bool:
        """Check if request can be processed based on rate limits"""
        for engine in request.search_engines:
            if not self._check_rate_limit(engine):
                return False
        return True

    def _check_rate_limit(self, engine: SearchEngine) -> bool:
        """Check rate limit for specific search engine"""
        now = datetime.utcnow()
        limiter = self.rate_limiters[engine]
        
        # Clean old requests
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        limiter['requests_per_hour'] = deque([
            req_time for req_time in limiter['requests_per_hour'] 
            if req_time > hour_ago
        ])
        
        limiter['requests_per_day'] = deque([
            req_time for req_time in limiter['requests_per_day'] 
            if req_time > day_ago
        ])
        
        # Check limits (these would be configurable)
        hourly_limit = 100  # Requests per hour
        daily_limit = 1000  # Requests per day
        
        if len(limiter['requests_per_hour']) >= hourly_limit:
            return False
        if len(limiter['requests_per_day']) >= daily_limit:
            return False
            
        return True

    def _update_rate_limit(self, engine: SearchEngine):
        """Update rate limit tracking for engine"""
        now = datetime.utcnow()
        limiter = self.rate_limiters[engine]
        
        limiter['requests_per_hour'].append(now)
        limiter['requests_per_day'].append(now)
        limiter['last_request'] = now

    def _get_rate_limit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current rate limit status for all engines"""
        status = {}
        for engine in SearchEngine:
            limiter = self.rate_limiters[engine]
            status[engine.value] = {
                'requests_last_hour': len(limiter['requests_per_hour']),
                'requests_last_day': len(limiter['requests_per_day']),
                'last_request': limiter['last_request'].isoformat() if limiter['last_request'] else None
            }
        return status

    def _update_batch_status(self, batch_id: str):
        """Update batch status based on individual request completion"""
        if batch_id in self.pending_batches:
            # Move to active if not already there
            if batch_id not in self.active_batches:
                self.active_batches[batch_id] = self.pending_batches.pop(batch_id)
                
        if batch_id in self.active_batches:
            batch = self.active_batches[batch_id]
            completed_count = 0
            failed_count = 0
            
            for request in batch.requests:
                if request.id in self.completed_requests:
                    completed_count += 1
                elif request.id in self.failed_requests:
                    failed_count += 1
                    
            # Check if batch is complete
            if completed_count + failed_count >= len(batch.requests):
                # Move to completed
                batch_results = {
                    'batch': batch,
                    'completed_requests': completed_count,
                    'failed_requests': failed_count,
                    'total_requests': len(batch.requests),
                    'success_rate': completed_count / len(batch.requests) if batch.requests else 0,
                    'completed_time': datetime.utcnow()
                }
                
                self.completed_batches[batch_id] = batch_results
                del self.active_batches[batch_id]
                
                logger.info(f"Batch {batch_id} completed: {completed_count}/{len(batch.requests)} successful")

    def _update_processing_stats(self, processing_time: float):
        """Update processing statistics"""
        self.stats['total_submitted'] += 1
        
        # Update average processing time
        total_requests = self.stats['total_submitted']
        current_avg = self.stats['average_processing_time']
        self.stats['average_processing_time'] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        # Update success rate
        completed = self.stats['total_completed']
        failed = self.stats['total_failed']
        if completed + failed > 0:
            self.stats['success_rate'] = completed / (completed + failed)

    async def _monitor_requests(self):
        """Background task to monitor request status and update statistics"""
        while self._running:
            try:
                # Check status of submitted requests
                await self._update_request_statuses()
                
                # Clean up old completed requests
                await self._cleanup_old_requests()
                
                # Log periodic statistics
                if self.stats['total_submitted'] > 0:
                    logger.info(f"Delisting stats: {self.stats}")
                    
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in request monitor: {e}")
                await asyncio.sleep(60)

    async def _update_request_statuses(self):
        """Update status of submitted requests by checking with search engines"""
        # Check status of requests that were submitted but not yet completed
        for request_id, request_data in list(self.completed_requests.items()):
            results = request_data['results']
            needs_update = False
            
            for engine, result in results.items():
                if result.status in [DelistingStatus.SUBMITTED, DelistingStatus.IN_PROGRESS]:
                    if result.request_id:
                        try:
                            updated_result = await self.delisting_service.check_removal_status(
                                result.request_id, engine
                            )
                            if updated_result.status != result.status:
                                results[engine] = updated_result
                                needs_update = True
                        except Exception as e:
                            logger.error(f"Error checking status for {request_id}/{engine}: {e}")
                            
            if needs_update:
                request_data['updated_time'] = datetime.utcnow()

    async def _cleanup_old_requests(self):
        """Clean up old completed and failed requests to prevent memory leaks"""
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        # Clean completed requests
        to_remove = []
        for request_id, request_data in self.completed_requests.items():
            if request_data.get('completed_time', datetime.utcnow()) < cutoff_time:
                to_remove.append(request_id)
                
        for request_id in to_remove:
            del self.completed_requests[request_id]
            
        # Clean failed requests
        to_remove = []
        for request_id, request_data in self.failed_requests.items():
            if request_data.get('timestamp', datetime.utcnow()) < cutoff_time:
                to_remove.append(request_id)
                
        for request_id in to_remove:
            del self.failed_requests[request_id]
            
        # Clean completed batches
        to_remove = []
        for batch_id, batch_data in self.completed_batches.items():
            if batch_data.get('completed_time', datetime.utcnow()) < cutoff_time:
                to_remove.append(batch_id)
                
        for batch_id in to_remove:
            del self.completed_batches[batch_id]
            
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old requests/batches")


# Global instance
delisting_manager = DelistingRequestManager()