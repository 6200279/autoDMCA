"""
Main content scanner that coordinates all scanning operations.
"""

import asyncio
import signal
import sys
from typing import Dict, List, Optional, Any
import structlog

from .config import ScannerConfig
from .scheduler.task_manager import TaskManager
from .processors.content_matcher import ContentMatch


logger = structlog.get_logger(__name__)


class ContentScanner:
    """Main content scanning engine for AutoDMCA platform."""
    
    def __init__(self, config: ScannerConfig = None):
        self.config = config or ScannerConfig()
        self.task_manager = TaskManager(self.config)
        self._running = False
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize the content scanner."""
        try:
            await self.task_manager.initialize()
            
            # Schedule system tasks
            await self.task_manager.schedule_system_tasks()
            
            self._running = True
            
            logger.info(
                "Content scanner initialized successfully",
                face_recognition_enabled=self.config.enable_face_recognition,
                image_hashing_enabled=self.config.enable_image_hashing,
                piracy_sites_count=len(self.config.piracy_sites)
            )
            
        except Exception as e:
            logger.error("Failed to initialize content scanner", error=str(e))
            raise
    
    async def close(self):
        """Shut down the content scanner."""
        self._running = False
        
        try:
            await self.task_manager.close()
            logger.info("Content scanner shut down successfully")
        except Exception as e:
            logger.error("Error during scanner shutdown", error=str(e))
    
    async def add_person(
        self,
        person_id: str,
        reference_images: List[str],
        usernames: List[str],
        email: str,
        additional_keywords: List[str] = None,
        scan_interval_hours: int = None,
        priority_protection: bool = False
    ) -> bool:
        """Add a person to be monitored for content protection."""
        try:
            success = await self.task_manager.add_person_profile(
                person_id=person_id,
                reference_images=reference_images,
                usernames=usernames,
                additional_keywords=additional_keywords,
                scan_interval_hours=scan_interval_hours,
                priority_scan=priority_protection
            )
            
            if success:
                logger.info(
                    f"Person added for content protection: {person_id}",
                    usernames=usernames,
                    scan_interval_hours=scan_interval_hours,
                    priority_protection=priority_protection
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add person: {person_id}", error=str(e))
            return False
    
    async def remove_person(self, person_id: str) -> bool:
        """Remove a person from content monitoring."""
        try:
            # Cancel all tasks for this person
            person_tasks = await self.task_manager.scheduler.get_tasks_for_person(person_id)
            for task in person_tasks:
                await self.task_manager.scheduler.cancel_task(task.task_id)
            
            # Remove from content matcher
            await self.task_manager.content_matcher.remove_person(person_id)
            
            logger.info(f"Person removed from content protection: {person_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove person: {person_id}", error=str(e))
            return False
    
    async def trigger_immediate_scan(
        self,
        person_id: str,
        scan_type: str = "full",
        priority: bool = True
    ) -> str:
        """Trigger an immediate scan for a person."""
        try:
            task_id = await self.task_manager.scheduler.schedule_task(
                task_type=scan_type + "_scan" if not scan_type.endswith("_scan") else scan_type,
                person_id=person_id,
                parameters={'priority': priority, 'immediate': True},
                schedule_type='once',
                priority=self.task_manager.scheduler.TaskPriority.IMMEDIATE if priority else self.task_manager.scheduler.TaskPriority.HIGH
            )
            
            logger.info(
                f"Immediate scan triggered for {person_id}",
                task_id=task_id,
                scan_type=scan_type
            )
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to trigger immediate scan for {person_id}", error=str(e))
            return None
    
    async def get_person_status(self, person_id: str) -> Dict[str, Any]:
        """Get comprehensive status for a person's content protection."""
        try:
            # Get person statistics
            stats = await self.task_manager.content_matcher.get_person_statistics(person_id)
            
            # Get active tasks
            tasks = await self.task_manager.scheduler.get_tasks_for_person(person_id)
            
            # Get recent DMCA requests
            # This would typically query a database for recent DMCA activity
            
            status = {
                'person_id': person_id,
                'profile_stats': stats,
                'active_tasks': len(tasks),
                'task_details': [
                    {
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'status': task.status.value,
                        'last_run': task.last_run_at,
                        'next_run': task.next_run_at,
                        'success_rate': task.success_count / max(task.run_count, 1)
                    }
                    for task in tasks
                ],
                'protection_active': len([t for t in tasks if t.status.value in ['pending', 'running']]) > 0
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get person status: {person_id}", error=str(e))
            return {'error': str(e)}
    
    async def get_recent_matches(
        self,
        person_id: str,
        hours: int = 24,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """Get recent content matches for a person."""
        try:
            # This would typically query a database for recent matches
            # For now, return placeholder data
            
            logger.info(f"Retrieved recent matches for {person_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get recent matches for {person_id}", error=str(e))
            return []
    
    async def get_dmca_status(self, person_id: str = None) -> Dict[str, Any]:
        """Get DMCA processing status."""
        try:
            queue_status = await self.task_manager.dmca_queue.get_queue_status()
            
            status = {
                'queue_status': queue_status,
                'total_pending': queue_status.get('pending', 0) + queue_status.get('processing', 0),
                'total_completed': queue_status.get('completed', 0),
                'total_failed': queue_status.get('failed', 0)
            }
            
            if person_id:
                # Add person-specific DMCA status
                # This would query database for person's DMCA requests
                pass
            
            return status
            
        except Exception as e:
            logger.error("Failed to get DMCA status", error=str(e))
            return {'error': str(e)}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        try:
            return await self.task_manager.get_system_status()
        except Exception as e:
            logger.error("Failed to get system health", error=str(e))
            return {
                'system_status': 'error',
                'error': str(e)
            }
    
    async def run_forever(self):
        """Run the scanner in daemon mode."""
        if not self._running:
            await self.initialize()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Content scanner running in daemon mode")
        
        try:
            # Main event loop
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Health check every 5 minutes
                    health = await self.get_system_health()
                    
                    if health.get('system_status') == 'error':
                        logger.warning("System health check failed", health=health)
                    
                    # Wait for shutdown event or timeout
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=300)
                        break
                    except asyncio.TimeoutError:
                        continue
                        
                except Exception as e:
                    logger.error("Error in main loop", error=str(e))
                    await asyncio.sleep(60)  # Wait before retrying
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        finally:
            await self.close()
    
    async def manual_scan_url(
        self,
        url: str,
        person_id: str = None
    ) -> List[ContentMatch]:
        """Manually scan a specific URL for content matches."""
        try:
            from .crawlers.web_crawler import WebCrawler
            from .crawlers.piracy_crawler import InfringingContent
            
            # Crawl the URL
            crawler = WebCrawler(self.config.settings)
            await crawler.initialize()
            
            try:
                crawl_result = await crawler.crawl(url)
                
                if not crawl_result.is_success:
                    logger.warning(f"Failed to crawl URL: {url}", error=crawl_result.error)
                    return []
                
                # Create InfringingContent object
                content = InfringingContent(
                    title=crawl_result.title or "Manual scan",
                    url=url,
                    site_name=crawl_result.url,
                    content_type='manual',
                    description=crawl_result.text_content[:500] if crawl_result.text_content else "",
                    thumbnail_url=crawl_result.images[0] if crawl_result.images else None,
                    download_urls=crawl_result.images[:5]  # First 5 images
                )
                
                # Match against all persons or specific person
                person_ids = [person_id] if person_id else None
                matches = await self.task_manager.content_matcher.match_content(
                    content, person_ids
                )
                
                logger.info(
                    f"Manual URL scan completed: {url}",
                    matches_found=len(matches),
                    positive_matches=len([m for m in matches if m.is_positive_match])
                )
                
                return matches
                
            finally:
                await crawler.close()
            
        except Exception as e:
            logger.error(f"Manual URL scan failed: {url}", error=str(e))
            return []
    
    async def export_person_data(self, person_id: str) -> Dict[str, Any]:
        """Export all data for a person (for GDPR compliance, etc.)."""
        try:
            export_data = {
                'person_id': person_id,
                'export_timestamp': asyncio.get_event_loop().time(),
                'profile_statistics': await self.task_manager.content_matcher.get_person_statistics(person_id),
                'active_tasks': [],
                'recent_scans': [],
                'dmca_requests': [],
                'matches_found': []
            }
            
            # Get tasks
            tasks = await self.task_manager.scheduler.get_tasks_for_person(person_id)
            export_data['active_tasks'] = [task.to_dict() for task in tasks]
            
            # This would include more comprehensive data from database
            
            logger.info(f"Data export completed for {person_id}")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export data for {person_id}", error=str(e))
            return {'error': str(e)}


# Convenience function for creating and running scanner
async def run_scanner(config_path: str = None):
    """Run the content scanner with configuration."""
    try:
        # Load configuration
        if config_path:
            # Load from file (implementation depends on config format)
            config = ScannerConfig()
        else:
            config = ScannerConfig()
        
        # Create and run scanner
        scanner = ContentScanner(config)
        await scanner.run_forever()
        
    except Exception as e:
        logger.error("Scanner failed to start", error=str(e))
        sys.exit(1)


# Entry point for running as script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoDMCA Content Scanner")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if args.daemon else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Run scanner
    asyncio.run(run_scanner(args.config))