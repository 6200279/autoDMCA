"""
DMCA-Delisting Integration Service
Orchestrates parallel DMCA takedown and search engine delisting workflows
PRD: "Parallel DMCA + delisting workflow", "Fall back to search engine delisting"
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from app.services.dmca.takedown_processor import DMCATakedownProcessor, TakedownRequest, TakedownStatus
from app.services.scanning.delisting_manager import delisting_manager
from app.services.scanning.delisting_monitor import delisting_monitor
from app.services.scanning.delisting_service import SearchEngine, DelistingStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

class IntegrationStrategy(str, Enum):
    """Integration strategies for DMCA and delisting"""
    PARALLEL = "parallel"  # Run DMCA and delisting simultaneously
    SEQUENTIAL = "sequential"  # Try DMCA first, then delisting if failed
    DELISTING_ONLY = "delisting_only"  # Skip DMCA, go straight to delisting
    DMCA_ONLY = "dmca_only"  # Only attempt DMCA takedown

class WorkflowStatus(str, Enum):
    """Overall workflow status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DMCA_SUCCESSFUL = "dmca_successful"
    DELISTING_SUCCESSFUL = "delisting_successful"
    BOTH_SUCCESSFUL = "both_successful"
    PARTIALLY_SUCCESSFUL = "partially_successful"
    FAILED = "failed"
    COMPLETED = "completed"

@dataclass
class IntegrationResult:
    """Result of integrated DMCA + delisting workflow"""
    workflow_id: str
    url: str
    strategy: IntegrationStrategy
    status: WorkflowStatus
    
    # DMCA results
    dmca_request: Optional[TakedownRequest] = None
    dmca_successful: bool = False
    dmca_message: str = ""
    
    # Delisting results
    delisting_request_id: Optional[str] = None
    delisting_results: Dict[SearchEngine, Any] = field(default_factory=dict)
    delisting_successful: bool = False
    delisting_message: str = ""
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: float = 0.0
    
    # Overall effectiveness
    url_accessible: bool = True
    search_engine_indexed: Dict[SearchEngine, bool] = field(default_factory=dict)
    overall_success: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

class DMCADelistingIntegration:
    """
    Orchestrates parallel DMCA takedown and search engine delisting workflows
    PRD: "Reduces visibility of pirated content even if can't be taken down at source"
    """
    
    def __init__(self):
        self.dmca_processor = DMCATakedownProcessor()
        self.active_workflows = {}  # workflow_id -> IntegrationResult
        self.completed_workflows = {}  # workflow_id -> IntegrationResult
        
        # Configuration
        self.default_strategy = IntegrationStrategy.PARALLEL
        self.dmca_timeout_minutes = 30  # Time to wait for DMCA response
        self.delisting_timeout_minutes = 60  # Time to wait for delisting
        self.verification_delay_hours = 2  # Wait before verifying success
        
        # Success rate targets (PRD: 100% success rate goal)
        self.target_overall_success_rate = 0.90  # 90%+ target
        self.target_search_delisting_rate = 0.95  # 95%+ for search engines
        
    async def process_infringement(
        self,
        infringement_url: str,
        profile_data: Dict[str, Any],
        original_content_url: Optional[str] = None,
        strategy: Optional[IntegrationStrategy] = None,
        priority: bool = False,
        search_engines: Optional[List[SearchEngine]] = None
    ) -> IntegrationResult:
        """
        Main entry point for integrated infringement processing
        PRD: "Automatically submitting requests to Google, Bing, etc., to remove the offending URLs"
        """
        workflow_id = f"workflow_{int(datetime.utcnow().timestamp())}"
        
        if strategy is None:
            strategy = await self._determine_optimal_strategy(infringement_url, profile_data)
        
        if search_engines is None:
            search_engines = [SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.YANDEX]
        
        # Initialize workflow result
        result = IntegrationResult(
            workflow_id=workflow_id,
            url=infringement_url,
            strategy=strategy,
            status=WorkflowStatus.PENDING,
            started_at=datetime.utcnow(),
            metadata={
                'profile_data': profile_data,
                'original_content_url': original_content_url,
                'priority': priority,
                'search_engines': [engine.value for engine in search_engines]
            }
        )
        
        self.active_workflows[workflow_id] = result
        
        try:
            if strategy == IntegrationStrategy.PARALLEL:
                result = await self._execute_parallel_workflow(result, profile_data, search_engines)
            elif strategy == IntegrationStrategy.SEQUENTIAL:
                result = await self._execute_sequential_workflow(result, profile_data, search_engines)
            elif strategy == IntegrationStrategy.DELISTING_ONLY:
                result = await self._execute_delisting_only(result, profile_data, search_engines)
            elif strategy == IntegrationStrategy.DMCA_ONLY:
                result = await self._execute_dmca_only(result, profile_data)
            
            # Post-processing: verification and final status
            result = await self._finalize_workflow(result)
            
        except Exception as e:
            logger.error(f"Error in workflow {workflow_id}: {e}")
            result.status = WorkflowStatus.FAILED
            result.metadata['error'] = str(e)
        
        # Move to completed
        result.completed_at = datetime.utcnow()
        if result.started_at:
            result.processing_time = (result.completed_at - result.started_at).total_seconds()
        
        self.completed_workflows[workflow_id] = result
        self.active_workflows.pop(workflow_id, None)
        
        logger.info(f"Workflow {workflow_id} completed with status: {result.status}")
        return result
    
    async def _determine_optimal_strategy(
        self,
        url: str,
        profile_data: Dict[str, Any]
    ) -> IntegrationStrategy:
        """
        Determine optimal strategy based on URL and historical success rates
        PRD: Intelligent routing for maximum success rate
        """
        try:
            # Check if we can identify a host provider for DMCA
            host_provider, abuse_email = await self.dmca_processor._identify_host_provider(url)
            
            # Get historical success rates for this type of content/host
            dmca_success_rate = await self._get_historical_dmca_success_rate(host_provider)
            delisting_success_rate = await self._get_historical_delisting_success_rate()
            
            # Decision logic
            if not abuse_email:
                # No DMCA contact available
                logger.info(f"No DMCA contact found for {url}, using delisting only")
                return IntegrationStrategy.DELISTING_ONLY
            
            if dmca_success_rate > 0.8 and delisting_success_rate > 0.8:
                # Both methods have good success rates - run in parallel
                return IntegrationStrategy.PARALLEL
            elif dmca_success_rate > delisting_success_rate:
                # DMCA more likely to succeed
                return IntegrationStrategy.SEQUENTIAL
            else:
                # Delisting more reliable
                return IntegrationStrategy.DELISTING_ONLY
                
        except Exception as e:
            logger.error(f"Error determining strategy: {e}")
            return IntegrationStrategy.PARALLEL  # Default fallback
    
    async def _execute_parallel_workflow(
        self,
        result: IntegrationResult,
        profile_data: Dict[str, Any],
        search_engines: List[SearchEngine]
    ) -> IntegrationResult:
        """
        Execute parallel DMCA + delisting workflow
        PRD: "Parallel DMCA + delisting workflow"
        """
        result.status = WorkflowStatus.IN_PROGRESS
        
        # Start both processes concurrently
        dmca_task = asyncio.create_task(
            self._execute_dmca_takedown(result.url, profile_data, result.metadata.get('original_content_url'))
        )
        
        delisting_task = asyncio.create_task(
            self._execute_delisting_request(result.url, profile_data, search_engines)
        )
        
        # Wait for both to complete
        try:
            dmca_result, delisting_result = await asyncio.gather(
                dmca_task, delisting_task, return_exceptions=True
            )
            
            # Process DMCA result
            if isinstance(dmca_result, Exception):
                logger.error(f"DMCA task failed: {dmca_result}")
                result.dmca_message = str(dmca_result)
            else:
                result.dmca_request = dmca_result
                result.dmca_successful = dmca_result.status in [TakedownStatus.SENT, TakedownStatus.REMOVED]
                result.dmca_message = f"DMCA status: {dmca_result.status}"
            
            # Process delisting result
            if isinstance(delisting_result, Exception):
                logger.error(f"Delisting task failed: {delisting_result}")
                result.delisting_message = str(delisting_result)
            else:
                result.delisting_request_id, result.delisting_results = delisting_result
                result.delisting_successful = any(
                    res.success for res in result.delisting_results.values()
                )
                result.delisting_message = f"Delisting submitted to {len(result.delisting_results)} engines"
            
            # Determine overall status
            if result.dmca_successful and result.delisting_successful:
                result.status = WorkflowStatus.BOTH_SUCCESSFUL
                result.overall_success = True
            elif result.dmca_successful:
                result.status = WorkflowStatus.DMCA_SUCCESSFUL
                result.overall_success = True
            elif result.delisting_successful:
                result.status = WorkflowStatus.DELISTING_SUCCESSFUL
                result.overall_success = True
            else:
                result.status = WorkflowStatus.FAILED
                result.overall_success = False
                
        except Exception as e:
            logger.error(f"Error in parallel workflow: {e}")
            result.status = WorkflowStatus.FAILED
            result.metadata['workflow_error'] = str(e)
        
        return result
    
    async def _execute_sequential_workflow(
        self,
        result: IntegrationResult,
        profile_data: Dict[str, Any],
        search_engines: List[SearchEngine]
    ) -> IntegrationResult:
        """
        Execute sequential DMCA-first workflow with delisting fallback
        PRD: "Fall back to search engine delisting"
        """
        result.status = WorkflowStatus.IN_PROGRESS
        
        try:
            # Step 1: Try DMCA first
            dmca_result = await self._execute_dmca_takedown(
                result.url, profile_data, result.metadata.get('original_content_url')
            )
            
            result.dmca_request = dmca_result
            result.dmca_successful = dmca_result.status in [TakedownStatus.SENT, TakedownStatus.REMOVED]
            result.dmca_message = f"DMCA status: {dmca_result.status}"
            
            if result.dmca_successful:
                result.status = WorkflowStatus.DMCA_SUCCESSFUL
                result.overall_success = True
                
                # Still submit delisting for comprehensive coverage
                try:
                    delisting_id, delisting_results = await self._execute_delisting_request(
                        result.url, profile_data, search_engines
                    )
                    result.delisting_request_id = delisting_id
                    result.delisting_results = delisting_results
                    result.delisting_message = "Delisting submitted as backup"
                except Exception as e:
                    logger.warning(f"Backup delisting failed: {e}")
            else:
                # Step 2: DMCA failed, try delisting
                logger.info(f"DMCA failed for {result.url}, falling back to delisting")
                
                delisting_id, delisting_results = await self._execute_delisting_request(
                    result.url, profile_data, search_engines
                )
                
                result.delisting_request_id = delisting_id
                result.delisting_results = delisting_results
                result.delisting_successful = any(
                    res.success for res in delisting_results.values()
                )
                
                if result.delisting_successful:
                    result.status = WorkflowStatus.DELISTING_SUCCESSFUL
                    result.overall_success = True
                    result.delisting_message = "Delisting successful after DMCA failure"
                else:
                    result.status = WorkflowStatus.FAILED
                    result.overall_success = False
                    result.delisting_message = "Both DMCA and delisting failed"
                    
        except Exception as e:
            logger.error(f"Error in sequential workflow: {e}")
            result.status = WorkflowStatus.FAILED
            result.metadata['workflow_error'] = str(e)
        
        return result
    
    async def _execute_delisting_only(
        self,
        result: IntegrationResult,
        profile_data: Dict[str, Any],
        search_engines: List[SearchEngine]
    ) -> IntegrationResult:
        """
        Execute delisting-only workflow
        Used when DMCA is not viable or delisting is preferred
        """
        result.status = WorkflowStatus.IN_PROGRESS
        
        try:
            delisting_id, delisting_results = await self._execute_delisting_request(
                result.url, profile_data, search_engines
            )
            
            result.delisting_request_id = delisting_id
            result.delisting_results = delisting_results
            result.delisting_successful = any(
                res.success for res in delisting_results.values()
            )
            
            if result.delisting_successful:
                result.status = WorkflowStatus.DELISTING_SUCCESSFUL
                result.overall_success = True
                result.delisting_message = "Delisting submitted successfully"
            else:
                result.status = WorkflowStatus.FAILED
                result.overall_success = False
                result.delisting_message = "Delisting failed"
                
        except Exception as e:
            logger.error(f"Error in delisting-only workflow: {e}")
            result.status = WorkflowStatus.FAILED
            result.metadata['workflow_error'] = str(e)
        
        return result
    
    async def _execute_dmca_only(
        self,
        result: IntegrationResult,
        profile_data: Dict[str, Any]
    ) -> IntegrationResult:
        """
        Execute DMCA-only workflow
        Used when delisting is not desired or not applicable
        """
        result.status = WorkflowStatus.IN_PROGRESS
        
        try:
            dmca_result = await self._execute_dmca_takedown(
                result.url, profile_data, result.metadata.get('original_content_url')
            )
            
            result.dmca_request = dmca_result
            result.dmca_successful = dmca_result.status in [TakedownStatus.SENT, TakedownStatus.REMOVED]
            result.dmca_message = f"DMCA status: {dmca_result.status}"
            
            if result.dmca_successful:
                result.status = WorkflowStatus.DMCA_SUCCESSFUL
                result.overall_success = True
            else:
                result.status = WorkflowStatus.FAILED
                result.overall_success = False
                
        except Exception as e:
            logger.error(f"Error in DMCA-only workflow: {e}")
            result.status = WorkflowStatus.FAILED
            result.metadata['workflow_error'] = str(e)
        
        return result
    
    async def _execute_dmca_takedown(
        self,
        url: str,
        profile_data: Dict[str, Any],
        original_content_url: Optional[str]
    ) -> TakedownRequest:
        """Execute DMCA takedown process"""
        return await self.dmca_processor.process_infringement(
            infringement_url=url,
            profile_data=profile_data,
            original_content_url=original_content_url
        )
    
    async def _execute_delisting_request(
        self,
        url: str,
        profile_data: Dict[str, Any],
        search_engines: List[SearchEngine]
    ) -> Tuple[str, Dict[SearchEngine, Any]]:
        """Execute delisting request process"""
        request_id = await delisting_manager.submit_url_removal(
            url=url,
            search_engines=search_engines,
            reason="Copyright infringement - automated DMCA integration",
            evidence_url=profile_data.get('profile_url')
        )
        
        # Get initial results
        results = await delisting_manager.get_request_status(request_id)
        
        return request_id, results.get('results', {})
    
    async def _finalize_workflow(self, result: IntegrationResult) -> IntegrationResult:
        """
        Finalize workflow with verification and final status determination
        PRD: "100% success in removing reported content from search indices"
        """
        try:
            # Schedule verification for later
            if result.overall_success:
                verification_time = datetime.utcnow() + timedelta(hours=self.verification_delay_hours)
                result.metadata['verification_scheduled'] = verification_time.isoformat()
                
                # Queue verification task
                asyncio.create_task(self._schedule_verification(result))
            
            # Update final status
            if result.status in [WorkflowStatus.DMCA_SUCCESSFUL, WorkflowStatus.DELISTING_SUCCESSFUL, WorkflowStatus.BOTH_SUCCESSFUL]:
                result.status = WorkflowStatus.COMPLETED
            
            # Log success metrics
            await self._record_workflow_metrics(result)
            
        except Exception as e:
            logger.error(f"Error finalizing workflow: {e}")
        
        return result
    
    async def _schedule_verification(self, result: IntegrationResult):
        """Schedule verification of workflow success"""
        try:
            await asyncio.sleep(self.verification_delay_hours * 3600)  # Wait specified hours
            
            # Verify DMCA success (check if URL is still accessible)
            if result.dmca_successful and result.dmca_request:
                updated_status = await self.dmca_processor.check_takedown_status(result.dmca_request)
                result.url_accessible = updated_status != TakedownStatus.REMOVED
            
            # Verify delisting success (check if URL still appears in search results)
            if result.delisting_successful and result.delisting_request_id:
                from app.services.scanning.delisting_service import SearchEngineDelistingService
                
                async with SearchEngineDelistingService() as service:
                    search_results = await service.verify_url_removal(result.url)
                    result.search_engine_indexed = search_results
                    
                    # Update overall success based on verification
                    if all(not indexed for indexed in search_results.values()):
                        result.overall_success = True
                        logger.info(f"Verification confirmed: {result.url} successfully delisted")
                    else:
                        logger.warning(f"Verification failed: {result.url} still indexed in some search engines")
            
        except Exception as e:
            logger.error(f"Error in verification: {e}")
    
    async def _get_historical_dmca_success_rate(self, host_provider: str) -> float:
        """Get historical DMCA success rate for a host provider"""
        # This would query historical data
        # For now, return estimated rates based on provider type
        provider_rates = {
            'cloudflare.com': 0.85,
            'google.com': 0.90,
            'facebook.com': 0.75,
            'reddit.com': 0.70,
            'unknown': 0.60
        }
        return provider_rates.get(host_provider, 0.60)
    
    async def _get_historical_delisting_success_rate(self) -> float:
        """Get historical delisting success rate"""
        # This would query actual performance metrics
        metrics = await delisting_monitor.get_performance_metrics()
        return metrics.success_rate if metrics.success_rate > 0 else 0.85
    
    async def _record_workflow_metrics(self, result: IntegrationResult):
        """Record workflow metrics for analysis and reporting"""
        metrics = {
            'workflow_id': result.workflow_id,
            'url': result.url,
            'strategy': result.strategy.value,
            'status': result.status.value,
            'dmca_successful': result.dmca_successful,
            'delisting_successful': result.delisting_successful,
            'overall_success': result.overall_success,
            'processing_time': result.processing_time,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # This would be stored in a metrics database
        logger.info(f"Workflow metrics: {metrics}")
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[IntegrationResult]:
        """Get status of a specific workflow"""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
        elif workflow_id in self.completed_workflows:
            return self.completed_workflows[workflow_id]
        return None
    
    async def get_workflow_statistics(self, time_window: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """
        Get comprehensive workflow statistics
        PRD: "Report success rates to users"
        """
        cutoff_time = datetime.utcnow() - time_window
        
        # Filter recent workflows
        recent_workflows = [
            workflow for workflow in self.completed_workflows.values()
            if workflow.completed_at and workflow.completed_at >= cutoff_time
        ]
        
        if not recent_workflows:
            return {
                'total_workflows': 0,
                'success_rate': 0.0,
                'dmca_success_rate': 0.0,
                'delisting_success_rate': 0.0,
                'average_processing_time': 0.0,
                'strategy_breakdown': {}
            }
        
        # Calculate statistics
        total = len(recent_workflows)
        successful = len([w for w in recent_workflows if w.overall_success])
        dmca_successful = len([w for w in recent_workflows if w.dmca_successful])
        delisting_successful = len([w for w in recent_workflows if w.delisting_successful])
        
        avg_processing_time = sum(w.processing_time for w in recent_workflows) / total
        
        # Strategy breakdown
        strategy_breakdown = {}
        for strategy in IntegrationStrategy:
            strategy_workflows = [w for w in recent_workflows if w.strategy == strategy]
            if strategy_workflows:
                strategy_success = len([w for w in strategy_workflows if w.overall_success])
                strategy_breakdown[strategy.value] = {
                    'total': len(strategy_workflows),
                    'successful': strategy_success,
                    'success_rate': strategy_success / len(strategy_workflows)
                }
        
        return {
            'total_workflows': total,
            'success_rate': successful / total,
            'dmca_success_rate': dmca_successful / total,
            'delisting_success_rate': delisting_successful / total,
            'average_processing_time': avg_processing_time,
            'strategy_breakdown': strategy_breakdown,
            'time_window': str(time_window)
        }


# Global instance
dmca_delisting_integration = DMCADelistingIntegration()