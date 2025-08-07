"""
Task manager that coordinates all scanning operations and integrates components.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
import structlog

from .scan_scheduler import ScanScheduler, ScanTask, TaskPriority, TaskStatus
from ..config import ScannerConfig
from ..crawlers.search_engine_api import SearchEngineManager
from ..crawlers.piracy_crawler import PiracySiteCrawler
from ..processors.content_matcher import ContentMatcher, ContentMatch
from ..queue.dmca_queue import DMCAQueue, DMCARequest
from ..queue.notification_sender import NotificationSender, NotificationLevel


logger = structlog.get_logger(__name__)


class TaskManager:
    """Main task manager that orchestrates all scanning operations."""
    
    def __init__(self, config: ScannerConfig):
        self.config = config
        self.scheduler = ScanScheduler(config.settings)
        self.search_manager = SearchEngineManager(config.settings)
        self.piracy_crawler = PiracySiteCrawler(config.settings)
        self.content_matcher = ContentMatcher(config.settings)
        self.dmca_queue = DMCAQueue(config.settings)
        self.notification_sender = NotificationSender(config.settings)
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all components."""
        if self._initialized:
            return
        
        # Initialize all components
        await self.scheduler.initialize()
        await self.piracy_crawler.initialize()
        await self.content_matcher.initialize()
        await self.dmca_queue.initialize()
        await self.notification_sender.initialize()
        
        # Register task handlers
        self._register_task_handlers()
        
        self._initialized = True
        logger.info("Task manager initialized successfully")
    
    async def close(self):
        """Clean up all components."""
        await self.scheduler.close()
        await self.piracy_crawler.close()
        await self.content_matcher.close()
        await self.dmca_queue.close()
        await self.notification_sender.close()
        
        logger.info("Task manager shut down")
    
    def _register_task_handlers(self):
        """Register task handlers with the scheduler."""
        self.scheduler.register_task_handler('full_scan', self._handle_full_scan)
        self.scheduler.register_task_handler('search_engine_scan', self._handle_search_engine_scan)
        self.scheduler.register_task_handler('piracy_site_scan', self._handle_piracy_site_scan)
        self.scheduler.register_task_handler('process_dmca_queue', self._handle_process_dmca_queue)
        self.scheduler.register_task_handler('send_notifications', self._handle_send_notifications)
        self.scheduler.register_task_handler('maintenance', self._handle_maintenance)
    
    async def add_person_profile(
        self,
        person_id: str,
        reference_images: List[str],
        usernames: List[str],
        additional_keywords: List[str] = None,
        scan_interval_hours: int = None,
        priority_scan: bool = False
    ) -> bool:
        """Add a person's profile and set up scanning tasks."""
        try:
            # Add profile to content matcher
            success = await self.content_matcher.add_person_profile(
                person_id, reference_images, usernames, additional_keywords
            )
            
            if not success:
                logger.error(f"Failed to add person profile: {person_id}")
                return False
            
            # Update search terms in config
            self.config.update_search_terms(usernames[0], additional_keywords)
            
            # Schedule scanning tasks
            await self._schedule_person_tasks(
                person_id, 
                scan_interval_hours or self.config.settings.scan_interval_hours,
                priority_scan
            )
            
            logger.info(f"Person profile added and scanning scheduled: {person_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add person profile: {person_id}", error=str(e))
            return False
    
    async def _schedule_person_tasks(
        self,
        person_id: str,
        scan_interval_hours: int,
        priority_scan: bool = False
    ):
        """Schedule scanning tasks for a person."""
        priority = TaskPriority.HIGH if priority_scan else TaskPriority.NORMAL
        
        # Full scan (comprehensive)
        await self.scheduler.schedule_task(
            task_type='full_scan',
            person_id=person_id,
            parameters={'comprehensive': True},
            schedule_type='interval',
            interval_seconds=scan_interval_hours * 3600,
            priority=priority
        )
        
        # Quick search engine scans (more frequent)
        await self.scheduler.schedule_task(
            task_type='search_engine_scan',
            person_id=person_id,
            parameters={'quick_scan': True},
            schedule_type='interval',
            interval_seconds=self.config.settings.quick_scan_interval_minutes * 60,
            priority=priority
        )
        
        # Priority scan for high-priority users
        if priority_scan:
            await self.scheduler.schedule_task(
                task_type='full_scan',
                person_id=person_id,
                parameters={'priority': True},
                schedule_type='interval',
                interval_seconds=self.config.settings.priority_scan_interval_hours * 3600,
                priority=TaskPriority.HIGH
            )
    
    async def _handle_full_scan(self, task: ScanTask) -> Dict[str, Any]:
        """Handle comprehensive scanning task."""
        person_id = task.person_id
        parameters = task.parameters
        
        logger.info(f"Starting full scan for {person_id}")
        start_time = time.time()
        
        results = {
            'person_id': person_id,
            'scan_type': 'full',
            'start_time': start_time,
            'search_results': [],
            'piracy_results': [],
            'content_matches': [],
            'dmca_requests_created': 0,
            'processing_time': 0.0
        }
        
        try:
            # Get search terms for this person
            search_terms = self._get_search_terms_for_person(person_id)
            
            # 1. Search Engine Scan
            search_results = await self._perform_search_engine_scan(
                person_id, search_terms, comprehensive=parameters.get('comprehensive', False)
            )
            results['search_results'] = search_results
            
            # 2. Piracy Site Scan
            piracy_results = await self._perform_piracy_site_scan(
                person_id, search_terms, comprehensive=parameters.get('comprehensive', False)
            )
            results['piracy_results'] = piracy_results
            
            # 3. Content Matching
            all_content = search_results + piracy_results
            if all_content:
                matches = await self.content_matcher.bulk_match_content(
                    all_content, [person_id]
                )
                
                # Process matches
                positive_matches = []
                for url, match_list in matches.items():
                    for match in match_list:
                        if match.is_positive_match:
                            positive_matches.append(match)
                
                results['content_matches'] = len(positive_matches)
                
                # 4. Create DMCA requests for high-confidence matches
                dmca_count = await self._create_dmca_requests(positive_matches)
                results['dmca_requests_created'] = dmca_count
                
                # 5. Send notifications if matches found
                if positive_matches:
                    await self._send_match_notifications(person_id, positive_matches)
            
            results['processing_time'] = time.time() - start_time
            
            logger.info(
                f"Full scan completed for {person_id}",
                search_results=len(results['search_results']),
                piracy_results=len(results['piracy_results']),
                matches=results['content_matches'],
                dmca_requests=results['dmca_requests_created'],
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error(f"Full scan failed for {person_id}", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    async def _handle_search_engine_scan(self, task: ScanTask) -> Dict[str, Any]:
        """Handle search engine scanning task."""
        person_id = task.person_id
        parameters = task.parameters
        
        logger.info(f"Starting search engine scan for {person_id}")
        start_time = time.time()
        
        results = {
            'person_id': person_id,
            'scan_type': 'search_engine',
            'start_time': start_time,
            'results': [],
            'processing_time': 0.0
        }
        
        try:
            search_terms = self._get_search_terms_for_person(person_id)
            
            # Perform search
            search_results = await self._perform_search_engine_scan(
                person_id, 
                search_terms, 
                quick_scan=parameters.get('quick_scan', False)
            )
            
            results['results'] = search_results
            results['processing_time'] = time.time() - start_time
            
            # Quick content matching for immediate threats
            if search_results:
                matches = await self.content_matcher.bulk_match_content(
                    search_results, [person_id]
                )
                
                high_confidence_matches = []
                for url, match_list in matches.items():
                    for match in match_list:
                        if match.is_high_confidence:
                            high_confidence_matches.append(match)
                
                if high_confidence_matches:
                    # Immediate DMCA processing for high-confidence matches
                    await self._create_dmca_requests(high_confidence_matches, priority=True)
                    
                    # Send urgent notification
                    await self._send_match_notifications(
                        person_id, 
                        high_confidence_matches,
                        level=NotificationLevel.HIGH
                    )
            
            logger.info(
                f"Search engine scan completed for {person_id}",
                results_count=len(search_results),
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error(f"Search engine scan failed for {person_id}", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    async def _handle_piracy_site_scan(self, task: ScanTask) -> Dict[str, Any]:
        """Handle piracy site scanning task."""
        person_id = task.person_id
        
        logger.info(f"Starting piracy site scan for {person_id}")
        start_time = time.time()
        
        results = {
            'person_id': person_id,
            'scan_type': 'piracy_site',
            'start_time': start_time,
            'results': [],
            'processing_time': 0.0
        }
        
        try:
            search_terms = self._get_search_terms_for_person(person_id)
            
            # Perform piracy site scan
            piracy_results = await self._perform_piracy_site_scan(person_id, search_terms)
            
            results['results'] = piracy_results
            results['processing_time'] = time.time() - start_time
            
            logger.info(
                f"Piracy site scan completed for {person_id}",
                results_count=len(piracy_results),
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error(f"Piracy site scan failed for {person_id}", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    async def _handle_process_dmca_queue(self, task: ScanTask) -> Dict[str, Any]:
        """Handle DMCA queue processing."""
        logger.info("Processing DMCA queue")
        start_time = time.time()
        
        results = {
            'task_type': 'process_dmca_queue',
            'start_time': start_time,
            'processed_count': 0,
            'processing_time': 0.0
        }
        
        try:
            # Process pending DMCA requests
            processed_count = await self.dmca_queue.process_pending_requests(
                max_requests=task.parameters.get('max_requests', 20)
            )
            
            results['processed_count'] = processed_count
            results['processing_time'] = time.time() - start_time
            
            logger.info(
                "DMCA queue processing completed",
                processed_count=processed_count,
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error("DMCA queue processing failed", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    async def _handle_send_notifications(self, task: ScanTask) -> Dict[str, Any]:
        """Handle notification sending."""
        logger.info("Processing notification queue")
        start_time = time.time()
        
        results = {
            'task_type': 'send_notifications',
            'start_time': start_time,
            'sent_count': 0,
            'processing_time': 0.0
        }
        
        try:
            # Process notification queue
            sent_count = await self.notification_sender.process_notification_queue(
                batch_size=task.parameters.get('batch_size', 10)
            )
            
            results['sent_count'] = sent_count
            results['processing_time'] = time.time() - start_time
            
            logger.info(
                "Notification processing completed",
                sent_count=sent_count,
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error("Notification processing failed", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    async def _handle_maintenance(self, task: ScanTask) -> Dict[str, Any]:
        """Handle maintenance tasks."""
        logger.info("Running maintenance tasks")
        start_time = time.time()
        
        results = {
            'task_type': 'maintenance',
            'start_time': start_time,
            'tasks_cleaned': 0,
            'dmca_cleaned': 0,
            'notifications_cleaned': 0,
            'processing_time': 0.0
        }
        
        try:
            # Clean up old tasks
            tasks_cleaned = await self.scheduler.cleanup_old_tasks(
                days_old=task.parameters.get('days_old', 30)
            )
            results['tasks_cleaned'] = tasks_cleaned
            
            # Clean up old DMCA requests
            dmca_cleaned = await self.dmca_queue.cleanup_old_requests(
                days_old=task.parameters.get('dmca_days_old', 90)
            )
            results['dmca_cleaned'] = dmca_cleaned
            
            # Clean up old notifications
            notifications_cleaned = await self.notification_sender.cleanup_old_notifications(
                hours_old=task.parameters.get('notification_hours_old', 48)
            )
            results['notifications_cleaned'] = notifications_cleaned
            
            results['processing_time'] = time.time() - start_time
            
            logger.info(
                "Maintenance completed",
                tasks_cleaned=tasks_cleaned,
                dmca_cleaned=dmca_cleaned,
                notifications_cleaned=notifications_cleaned,
                processing_time=results['processing_time']
            )
            
        except Exception as e:
            logger.error("Maintenance failed", error=str(e))
            results['error'] = str(e)
            raise
        
        return results
    
    def _get_search_terms_for_person(self, person_id: str) -> List[str]:
        """Get search terms for a specific person."""
        # This would typically come from a database or config
        # For now, use the global search terms
        return self.config.search_keywords[:20]  # Limit terms to avoid API limits
    
    async def _perform_search_engine_scan(
        self,
        person_id: str,
        search_terms: List[str],
        comprehensive: bool = False,
        quick_scan: bool = False
    ) -> List:
        """Perform search engine scanning."""
        try:
            results_per_term = 5 if quick_scan else 10
            if comprehensive:
                results_per_term = 20
            
            # Perform searches across all engines
            all_results = []
            for term in search_terms[:10 if quick_scan else 20]:  # Limit terms based on scan type
                try:
                    search_results = await self.search_manager.search_all(
                        term, results_per_term
                    )
                    
                    # Convert search results to InfringingContent format
                    for result in search_results:
                        # This is a simplified conversion - you'd want more sophisticated parsing
                        from ..crawlers.piracy_crawler import InfringingContent
                        
                        content = InfringingContent(
                            title=result.title,
                            url=result.url,
                            site_name=result.domain,
                            content_type='unknown',
                            description=result.snippet,
                            thumbnail_url=result.thumbnail_url,
                            matched_keywords=[term]
                        )
                        all_results.append(content)
                
                except Exception as e:
                    logger.error(f"Search failed for term: {term}", error=str(e))
                    continue
                
                # Rate limiting between searches
                await asyncio.sleep(0.5)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Search engine scan failed for {person_id}", error=str(e))
            return []
    
    async def _perform_piracy_site_scan(
        self,
        person_id: str,
        search_terms: List[str],
        comprehensive: bool = False
    ) -> List:
        """Perform piracy site scanning."""
        try:
            max_pages = 3 if comprehensive else 1
            
            # Scan all configured piracy sites
            sessions = await self.piracy_crawler.bulk_crawl(
                self.config.piracy_sites,
                search_terms[:10],  # Limit terms
                max_pages=max_pages,
                max_results=50 if comprehensive else 20
            )
            
            # Collect all results
            all_results = []
            for site_name, session in sessions.items():
                all_results.extend(session.results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Piracy site scan failed for {person_id}", error=str(e))
            return []
    
    async def _create_dmca_requests(
        self,
        matches: List[ContentMatch],
        priority: bool = False
    ) -> int:
        """Create DMCA requests for content matches."""
        created_count = 0
        
        for match in matches:
            try:
                # Create DMCA request
                request = DMCARequest(
                    person_id=match.person_id,
                    content_match=match,
                    infringing_url=match.content.url,
                    original_work_title=f"Original content by {match.person_id}",
                    copyright_owner=match.person_id,
                    priority=1 if priority else 3
                )
                
                # Enqueue for processing
                success = await self.dmca_queue.enqueue_request(request)
                if success:
                    created_count += 1
                
            except Exception as e:
                logger.error(f"Failed to create DMCA request for {match.content.url}", error=str(e))
                continue
        
        return created_count
    
    async def _send_match_notifications(
        self,
        person_id: str,
        matches: List[ContentMatch],
        level: NotificationLevel = NotificationLevel.MEDIUM
    ):
        """Send notifications about content matches."""
        try:
            # This would get the user's email from database
            # For now, using a placeholder
            recipient_email = f"{person_id}@example.com"
            
            await self.notification_sender.send_content_match_alert(
                person_id, matches, recipient_email, level
            )
            
        except Exception as e:
            logger.error(f"Failed to send match notifications for {person_id}", error=str(e))
    
    async def schedule_system_tasks(self):
        """Schedule recurring system tasks."""
        # DMCA queue processing
        await self.scheduler.schedule_task(
            task_type='process_dmca_queue',
            person_id='system',
            parameters={'max_requests': 50},
            schedule_type='interval',
            interval_seconds=300,  # Every 5 minutes
            priority=TaskPriority.HIGH
        )
        
        # Notification sending
        await self.scheduler.schedule_task(
            task_type='send_notifications',
            person_id='system',
            parameters={'batch_size': 20},
            schedule_type='interval',
            interval_seconds=120,  # Every 2 minutes
            priority=TaskPriority.HIGH
        )
        
        # Maintenance tasks
        await self.scheduler.schedule_task(
            task_type='maintenance',
            person_id='system',
            parameters={
                'days_old': 30,
                'dmca_days_old': 90,
                'notification_hours_old': 48
            },
            schedule_type='cron',
            cron_expression='0 2 * * *',  # Daily at 2 AM
            priority=TaskPriority.LOW
        )
        
        logger.info("System tasks scheduled")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            # Scheduler stats
            scheduler_stats = await self.scheduler.get_scheduler_stats()
            
            # DMCA queue stats
            dmca_stats = await self.dmca_queue.get_queue_status()
            
            # Notification stats
            notification_stats = await self.notification_sender.get_queue_stats()
            
            # Health checks
            scheduler_health = await self.scheduler.health_check()
            
            return {
                'system_status': 'operational' if scheduler_health.get('healthy', False) else 'degraded',
                'scheduler': scheduler_stats,
                'dmca_queue': dmca_stats,
                'notifications': notification_stats,
                'health': scheduler_health,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error("Failed to get system status", error=str(e))
            return {
                'system_status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }