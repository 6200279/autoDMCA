"""
Main DMCA Service

Orchestrates the complete DMCA takedown process including WHOIS lookup,
notice generation, email dispatch, search delisting, and status tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from ..models.takedown import TakedownRequest, TakedownStatus, TakedownBatch
from ..models.hosting import DMCAAgent, HostingProvider
from ..services.whois_service import WHOISService
from ..services.email_service import EmailService
from ..services.search_delisting_service import SearchDelistingService, SearchEngineType
from ..templates.template_renderer import TemplateRenderer
from ..utils.cache import CacheManager
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class DMCAServiceConfig:
    """Configuration for DMCA service."""
    
    def __init__(
        self,
        max_concurrent_requests: int = 5,
        followup_interval_days: int = 7,
        max_followup_attempts: int = 3,
        auto_search_delisting: bool = True,
        search_delisting_delay_hours: int = 72,
        batch_size: int = 10,
        enable_anonymity: bool = True
    ):
        """
        Initialize DMCA service configuration.
        
        Args:
            max_concurrent_requests: Maximum concurrent takedown processes
            followup_interval_days: Days to wait before sending follow-up
            max_followup_attempts: Maximum number of follow-up attempts
            auto_search_delisting: Whether to automatically request search delisting
            search_delisting_delay_hours: Hours to wait before search delisting
            batch_size: Default batch size for bulk operations
            enable_anonymity: Whether to enable anonymity protection by default
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.followup_interval_days = followup_interval_days
        self.max_followup_attempts = max_followup_attempts
        self.auto_search_delisting = auto_search_delisting
        self.search_delisting_delay_hours = search_delisting_delay_hours
        self.batch_size = batch_size
        self.enable_anonymity = enable_anonymity


class DMCAService:
    """
    Main service for managing the complete DMCA takedown process.
    """
    
    def __init__(
        self,
        whois_service: WHOISService,
        email_service: EmailService,
        search_delisting_service: SearchDelistingService,
        agent_contact: DMCAAgent,
        config: Optional[DMCAServiceConfig] = None,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize DMCA service.
        
        Args:
            whois_service: WHOIS lookup service
            email_service: Email dispatch service
            search_delisting_service: Search delisting service
            agent_contact: Default DMCA agent contact information
            config: Service configuration
            cache_manager: Cache manager
            rate_limiter: Rate limiter
        """
        self.whois_service = whois_service
        self.email_service = email_service
        self.search_delisting_service = search_delisting_service
        self.agent_contact = agent_contact
        self.config = config or DMCAServiceConfig()
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=30, time_window=60)
        
        # Template renderer
        self.template_renderer = TemplateRenderer()
        
        # Status tracking
        self.active_requests: Dict[UUID, TakedownRequest] = {}
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_takedowns': 0,
            'failed_takedowns': 0,
            'emails_sent': 0,
            'search_delistings': 0,
            'followups_sent': 0
        }
    
    async def process_takedown_request(
        self,
        takedown_request: TakedownRequest,
        custom_agent: Optional[DMCAAgent] = None
    ) -> Dict[str, Any]:
        """
        Process a single takedown request through the complete workflow.
        
        Args:
            takedown_request: The takedown request to process
            custom_agent: Optional custom DMCA agent (overrides default)
        
        Returns:
            Dict with processing results and status
        """
        request_id = takedown_request.id
        agent = custom_agent or self.agent_contact
        
        try:
            # Track the request
            self.active_requests[request_id] = takedown_request
            self.metrics['total_requests'] += 1
            
            logger.info(f"Starting takedown process for request {request_id}")
            
            # Step 1: WHOIS lookup to identify hosting provider
            takedown_request.update_status(TakedownStatus.WHOIS_LOOKUP)
            hosting_provider = await self._perform_whois_lookup(takedown_request)
            
            if not hosting_provider:
                logger.warning(f"WHOIS lookup failed for {request_id}")
                takedown_request.update_status(TakedownStatus.FAILED)
                return self._create_result(False, "WHOIS lookup failed")
            
            # Step 2: Generate and send DMCA notice
            takedown_request.update_status(TakedownStatus.NOTICE_GENERATED)
            email_result = await self._send_dmca_notice(takedown_request, hosting_provider, agent)
            
            if not email_result.get('success'):
                logger.error(f"Email sending failed for {request_id}")
                takedown_request.update_status(TakedownStatus.FAILED)
                return self._create_result(False, "Email sending failed", email_result)
            
            # Step 3: Schedule search delisting if enabled
            if self.config.auto_search_delisting:
                await self._schedule_search_delisting(takedown_request)
            
            # Step 4: Set up follow-up tracking
            await self._schedule_followup_check(takedown_request)
            
            takedown_request.update_status(TakedownStatus.UNDER_REVIEW)
            
            result = self._create_result(
                True, 
                "Takedown request processed successfully",
                {
                    'hosting_provider': hosting_provider.name,
                    'email_sent': True,
                    'message_id': email_result.get('message_id'),
                    'search_delisting_scheduled': self.config.auto_search_delisting
                }
            )
            
            self.metrics['successful_takedowns'] += 1
            logger.info(f"Takedown request {request_id} processed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Takedown processing failed for {request_id}: {str(e)}")
            takedown_request.update_status(TakedownStatus.FAILED)
            self.metrics['failed_takedowns'] += 1
            
            return self._create_result(False, f"Processing failed: {str(e)}")
        
        finally:
            # Remove from active tracking
            self.active_requests.pop(request_id, None)
    
    async def process_batch_takedowns(
        self,
        takedown_batch: TakedownBatch,
        custom_agent: Optional[DMCAAgent] = None
    ) -> Dict[str, Any]:
        """
        Process multiple takedown requests in batch.
        
        Args:
            takedown_batch: Batch of takedown requests
            custom_agent: Optional custom DMCA agent
        
        Returns:
            Dict with batch processing results
        """
        try:
            logger.info(f"Processing batch {takedown_batch.batch_id} with {len(takedown_batch.requests)} requests")
            
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
            
            async def process_single(request: TakedownRequest) -> Tuple[str, Dict[str, Any]]:
                async with semaphore:
                    result = await self.process_takedown_request(request, custom_agent)
                    return str(request.id), result
            
            # Process all requests
            tasks = [process_single(req) for req in takedown_batch.requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Categorize results
            successful = []
            failed = []
            
            for result in results:
                if isinstance(result, Exception):
                    failed.append({
                        'error': str(result),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    request_id, process_result = result
                    if process_result.get('success'):
                        successful.append({'request_id': request_id, **process_result})
                    else:
                        failed.append({'request_id': request_id, **process_result})
            
            return {
                'batch_id': str(takedown_batch.batch_id),
                'total_requests': len(takedown_batch.requests),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(takedown_batch.requests) * 100,
                'results': {
                    'successful': successful,
                    'failed': failed
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return {
                'batch_id': str(takedown_batch.batch_id),
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def send_followup(
        self,
        takedown_request: TakedownRequest,
        custom_agent: Optional[DMCAAgent] = None,
        followup_type: str = "followup"
    ) -> Dict[str, Any]:
        """
        Send a follow-up notice for an existing takedown request.
        
        Args:
            takedown_request: Original takedown request
            custom_agent: Optional custom DMCA agent
            followup_type: Type of follow-up (followup, final)
        
        Returns:
            Dict with follow-up results
        """
        try:
            agent = custom_agent or self.agent_contact
            
            if takedown_request.followup_count >= self.config.max_followup_attempts:
                return self._create_result(
                    False, 
                    "Maximum follow-up attempts reached"
                )
            
            # Get original hosting provider contact
            if not takedown_request.abuse_email:
                return self._create_result(
                    False,
                    "No contact email available for follow-up"
                )
            
            # Send follow-up email
            followup_result = await self.email_service.send_followup_notice(
                takedown_request,
                takedown_request.abuse_email,
                agent,
                followup_type
            )
            
            if followup_result.get('success'):
                takedown_request.update_status(TakedownStatus.FOLLOWUP_REQUIRED)
                self.metrics['followups_sent'] += 1
                
                logger.info(f"Follow-up sent for request {takedown_request.id}")
                
                return self._create_result(
                    True,
                    "Follow-up sent successfully",
                    followup_result
                )
            else:
                return self._create_result(
                    False,
                    "Follow-up sending failed",
                    followup_result
                )
            
        except Exception as e:
            logger.error(f"Follow-up failed for {takedown_request.id}: {str(e)}")
            return self._create_result(False, f"Follow-up failed: {str(e)}")
    
    async def request_search_delisting(
        self,
        takedown_requests: List[TakedownRequest],
        search_engines: List[str] = None,
        custom_agent: Optional[DMCAAgent] = None
    ) -> Dict[str, Any]:
        """
        Request search engine delisting for takedown requests.
        
        Args:
            takedown_requests: List of takedown requests to delist
            search_engines: List of search engines (defaults to Google and Bing)
            custom_agent: Optional custom DMCA agent
        
        Returns:
            Dict with delisting results
        """
        try:
            if search_engines is None:
                search_engines = [SearchEngineType.GOOGLE, SearchEngineType.BING]
            
            agent = custom_agent or self.agent_contact
            results = {}
            
            for engine in search_engines:
                delisting_result = await self.search_delisting_service.submit_delisting_request(
                    takedown_requests,
                    engine,
                    agent,
                    self.config.batch_size
                )
                results[engine] = delisting_result
                
                if delisting_result.get('success'):
                    # Update request statuses
                    for request in takedown_requests:
                        request.update_status(TakedownStatus.SEARCH_DELISTING_REQUESTED)
            
            self.metrics['search_delistings'] += 1
            
            return {
                'success': any(r.get('success') for r in results.values()),
                'results': results,
                'total_requests': len(takedown_requests),
                'search_engines': search_engines,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Search delisting failed: {str(e)}")
            return self._create_result(False, f"Search delisting failed: {str(e)}")
    
    async def check_takedown_status(self, takedown_request: TakedownRequest) -> Dict[str, Any]:
        """
        Check the current status of a takedown request and update accordingly.
        
        Args:
            takedown_request: Takedown request to check
        
        Returns:
            Dict with current status information
        """
        try:
            status_info = {
                'request_id': str(takedown_request.id),
                'current_status': takedown_request.status.value,
                'created_at': takedown_request.created_at.isoformat(),
                'updated_at': takedown_request.updated_at.isoformat(),
                'followup_count': takedown_request.followup_count,
                'email_sent': bool(takedown_request.notice_sent_at),
                'content_removed': takedown_request.content_removed,
                'delisted_from_search': takedown_request.delisted_from_search
            }
            
            # Check if follow-up is needed
            if takedown_request.should_followup(
                self.config.followup_interval_days,
                self.config.max_followup_attempts
            ):
                status_info['needs_followup'] = True
                status_info['next_action'] = 'Send follow-up notice'
            else:
                status_info['needs_followup'] = False
                status_info['next_action'] = takedown_request.get_next_action()
            
            # Check if expired
            if takedown_request.is_expired(30):
                status_info['expired'] = True
                status_info['recommendation'] = 'Consider escalation or manual review'
            
            # Get email delivery status if available
            if takedown_request.email_message_id:
                email_status = await self.email_service.get_delivery_status(
                    takedown_request.email_message_id
                )
                if email_status:
                    status_info['email_status'] = email_status
            
            return status_info
            
        except Exception as e:
            logger.error(f"Status check failed for {takedown_request.id}: {str(e)}")
            return {
                'request_id': str(takedown_request.id),
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _perform_whois_lookup(self, takedown_request: TakedownRequest) -> Optional[HostingProvider]:
        """Perform WHOIS lookup and update takedown request."""
        try:
            url = str(takedown_request.infringement_data.infringing_url)
            hosting_provider = await self.whois_service.lookup_domain(url)
            
            if hosting_provider:
                # Update takedown request with hosting info
                takedown_request.hosting_provider = hosting_provider.name
                takedown_request.abuse_email = hosting_provider.primary_contact_email
                takedown_request.dmca_contact_info = {
                    'dmca_email': hosting_provider.dmca_email,
                    'best_contact': hosting_provider.get_best_contact().model_dump() if hosting_provider.get_best_contact() else None
                }
                takedown_request.whois_data = hosting_provider.metadata
                
                logger.info(f"WHOIS lookup successful: {hosting_provider.name}")
            
            return hosting_provider
            
        except Exception as e:
            logger.error(f"WHOIS lookup failed: {str(e)}")
            return None
    
    async def _send_dmca_notice(
        self,
        takedown_request: TakedownRequest,
        hosting_provider: HostingProvider,
        agent: DMCAAgent
    ) -> Dict[str, Any]:
        """Send DMCA notice email."""
        try:
            # Determine recipient email
            recipient_email = (
                hosting_provider.dmca_email or 
                hosting_provider.abuse_email or 
                hosting_provider.primary_contact_email
            )
            
            if not recipient_email:
                raise ValueError("No contact email available for hosting provider")
            
            # Send DMCA notice
            email_result = await self.email_service.send_dmca_notice(
                takedown_request,
                recipient_email,
                agent,
                "standard",
                track_delivery=True
            )
            
            if email_result.get('success'):
                self.metrics['emails_sent'] += 1
                
                # Update hosting provider performance metrics
                hosting_provider.total_notices_sent += 1
            
            return email_result
            
        except Exception as e:
            logger.error(f"DMCA notice sending failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _schedule_search_delisting(self, takedown_request: TakedownRequest) -> None:
        """Schedule search delisting request."""
        try:
            # In a production system, this would use a job queue like Celery
            # For now, we'll store the scheduling information in cache
            
            schedule_time = datetime.utcnow() + timedelta(hours=self.config.search_delisting_delay_hours)
            
            schedule_data = {
                'request_id': str(takedown_request.id),
                'scheduled_for': schedule_time.isoformat(),
                'status': 'scheduled'
            }
            
            cache_key = f"search_delisting_schedule:{takedown_request.id}"
            await self.cache_manager.set(
                cache_key,
                schedule_data,
                ttl=timedelta(days=7)
            )
            
            logger.info(f"Search delisting scheduled for {takedown_request.id} at {schedule_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule search delisting: {str(e)}")
    
    async def _schedule_followup_check(self, takedown_request: TakedownRequest) -> None:
        """Schedule follow-up status check."""
        try:
            followup_time = datetime.utcnow() + timedelta(days=self.config.followup_interval_days)
            
            followup_data = {
                'request_id': str(takedown_request.id),
                'followup_due': followup_time.isoformat(),
                'status': 'scheduled'
            }
            
            cache_key = f"followup_schedule:{takedown_request.id}"
            await self.cache_manager.set(
                cache_key,
                followup_data,
                ttl=timedelta(days=30)
            )
            
            logger.info(f"Follow-up scheduled for {takedown_request.id} at {followup_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule follow-up: {str(e)}")
    
    def _create_result(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standardized result dictionary."""
        result = {
            'success': success,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data:
            result.update(data)
        
        return result
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        return {
            **self.metrics,
            'active_requests': len(self.active_requests),
            'success_rate': (
                self.metrics['successful_takedowns'] / max(1, self.metrics['total_requests']) * 100
            ),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_pending_followups(self) -> List[Dict[str, Any]]:
        """Get list of requests pending follow-up."""
        # In a production system, this would query the database
        # For now, return empty list
        return []
    
    async def get_scheduled_search_delistings(self) -> List[Dict[str, Any]]:
        """Get list of scheduled search delisting requests."""
        # In a production system, this would query the job queue
        # For now, return empty list
        return []
    
    async def cleanup_completed_requests(self, days_old: int = 30) -> int:
        """
        Clean up old completed requests from active tracking.
        
        Args:
            days_old: Remove requests completed more than this many days ago
        
        Returns:
            Number of requests cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cleaned_count = 0
            
            # Remove completed requests older than cutoff
            to_remove = []
            for request_id, request in self.active_requests.items():
                if (request.completed_at and 
                    request.completed_at < cutoff_date and
                    request.status in (TakedownStatus.COMPLETED, TakedownStatus.CONTENT_REMOVED)):
                    to_remove.append(request_id)
            
            for request_id in to_remove:
                del self.active_requests[request_id]
                cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} completed requests")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return 0