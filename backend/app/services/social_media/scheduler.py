"""
Scheduled monitoring tasks and queue management for social media monitoring.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import heapq
import uuid
import json

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.db.models.social_media import SocialMediaPlatform, MonitoringStatus
from app.db.models.profile import ProtectedProfile
from .monitoring_service import SocialMediaMonitoringService, MonitoringJob
from .config import MonitoringConfig


logger = structlog.get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    EMERGENCY = 5


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ScheduledTask:
    """Represents a scheduled monitoring task."""
    task_id: str
    profile_id: int
    platforms: List[SocialMediaPlatform]
    task_type: str  # periodic, one_time, emergency
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Scheduling
    schedule_expression: Optional[str] = None  # Cron expression
    interval_minutes: Optional[int] = None
    next_run: Optional[datetime] = None
    
    # Execution
    max_retries: int = 3
    retry_count: int = 0
    retry_delay_minutes: int = 15
    timeout_minutes: int = 30
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Results tracking
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    
    # Configuration
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Enable priority queue comparison."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # Higher priority first
        return self.next_run < other.next_run if self.next_run and other.next_run else False


@dataclass 
class TaskExecution:
    """Represents a task execution instance."""
    execution_id: str
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.RUNNING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get execution duration."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None


class TaskQueue:
    """Priority queue for managing monitoring tasks."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue = []
        self._task_index = {}  # task_id -> heap_index for fast lookup
        self._lock = asyncio.Lock()
        
    async def put(self, task: ScheduledTask) -> bool:
        """Add task to queue."""
        async with self._lock:
            if len(self._queue) >= self.max_size:
                logger.warning("Task queue is full", max_size=self.max_size)
                return False
            
            # Remove existing task with same ID if present
            await self._remove_task_by_id(task.task_id)
            
            # Add new task
            heapq.heappush(self._queue, task)
            self._task_index[task.task_id] = len(self._queue) - 1
            
            logger.debug("Task added to queue", task_id=task.task_id, priority=task.priority.name)
            return True
    
    async def get(self) -> Optional[ScheduledTask]:
        """Get highest priority task from queue."""
        async with self._lock:
            while self._queue:
                task = heapq.heappop(self._queue)
                
                # Update index
                if task.task_id in self._task_index:
                    del self._task_index[task.task_id]
                
                # Check if task should run now
                if task.next_run and task.next_run <= datetime.now():
                    logger.debug("Task retrieved from queue", task_id=task.task_id)
                    return task
                elif task.task_type == "emergency":
                    return task
                else:
                    # Put back if not ready to run
                    heapq.heappush(self._queue, task)
                    self._task_index[task.task_id] = len(self._queue) - 1
                    return None
            
            return None
    
    async def _remove_task_by_id(self, task_id: str) -> bool:
        """Remove task by ID from queue."""
        if task_id not in self._task_index:
            return False
        
        # Mark task as removed (lazy deletion)
        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                task.status = TaskStatus.CANCELLED
                break
        
        if task_id in self._task_index:
            del self._task_index[task_id]
        
        return True
    
    async def remove_task(self, task_id: str) -> bool:
        """Remove task from queue."""
        async with self._lock:
            return await self._remove_task_by_id(task_id)
    
    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID without removing from queue."""
        async with self._lock:
            for task in self._queue:
                if task.task_id == task_id:
                    return task
            return None
    
    async def size(self) -> int:
        """Get current queue size."""
        async with self._lock:
            return len([t for t in self._queue if t.status != TaskStatus.CANCELLED])
    
    async def clear(self) -> None:
        """Clear all tasks from queue."""
        async with self._lock:
            self._queue.clear()
            self._task_index.clear()


class WorkerPool:
    """Pool of workers for executing monitoring tasks."""
    
    def __init__(self, pool_size: int, monitoring_service: SocialMediaMonitoringService):
        self.pool_size = pool_size
        self.monitoring_service = monitoring_service
        self.workers: List[asyncio.Task] = []
        self.active_executions: Dict[str, TaskExecution] = {}
        self.completed_executions: List[TaskExecution] = []
        self.shutdown_event = asyncio.Event()
        
    async def start(self, task_queue: TaskQueue) -> None:
        """Start worker pool."""
        logger.info("Starting worker pool", pool_size=self.pool_size)
        
        for i in range(self.pool_size):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}", task_queue))
            self.workers.append(worker)
        
        logger.info("Worker pool started", active_workers=len(self.workers))
    
    async def stop(self) -> None:
        """Stop worker pool."""
        logger.info("Stopping worker pool")
        
        self.shutdown_event.set()
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        logger.info("Worker pool stopped")
    
    async def _worker_loop(self, worker_id: str, task_queue: TaskQueue) -> None:
        """Main worker loop."""
        logger.info("Worker started", worker_id=worker_id)
        
        while not self.shutdown_event.is_set():
            try:
                # Get next task
                task = await task_queue.get()
                
                if not task:
                    await asyncio.sleep(1)  # No tasks available
                    continue
                
                # Execute task
                await self._execute_task(worker_id, task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(5)  # Brief pause after error
        
        logger.info("Worker stopped", worker_id=worker_id)
    
    async def _execute_task(self, worker_id: str, task: ScheduledTask) -> None:
        """Execute a monitoring task."""
        execution_id = str(uuid.uuid4())
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            started_at=datetime.now(),
            worker_id=worker_id
        )
        
        self.active_executions[execution_id] = execution
        task.status = TaskStatus.RUNNING
        task.total_runs += 1
        task.last_run = datetime.now()
        
        logger.info(
            "Executing task",
            task_id=task.task_id,
            execution_id=execution_id,
            worker_id=worker_id,
            profile_id=task.profile_id
        )
        
        try:
            # Set timeout
            timeout_seconds = task.timeout_minutes * 60
            
            # Execute monitoring
            result = await asyncio.wait_for(
                self.monitoring_service.monitor_profile(task.profile_id, task.platforms),
                timeout=timeout_seconds
            )
            
            # Task completed successfully
            execution.status = TaskStatus.COMPLETED
            execution.result = self._serialize_result(result)
            execution.completed_at = datetime.now()
            
            task.status = TaskStatus.COMPLETED
            task.successful_runs += 1
            task.last_success = datetime.now()
            task.retry_count = 0  # Reset retry count on success
            
            logger.info(
                "Task completed successfully",
                task_id=task.task_id,
                execution_id=execution_id,
                duration=execution.duration.total_seconds() if execution.duration else None
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Task timed out after {task.timeout_minutes} minutes"
            await self._handle_task_failure(task, execution, error_msg)
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            await self._handle_task_failure(task, execution, error_msg)
        
        finally:
            # Move execution to completed list
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            self.completed_executions.append(execution)
            
            # Keep only recent executions to prevent memory growth
            if len(self.completed_executions) > 1000:
                self.completed_executions = self.completed_executions[-500:]
    
    async def _handle_task_failure(self, task: ScheduledTask, execution: TaskExecution, error_message: str) -> None:
        """Handle task execution failure."""
        execution.status = TaskStatus.FAILED
        execution.error_message = error_message
        execution.completed_at = datetime.now()
        
        task.failed_runs += 1
        task.last_error = error_message
        
        # Check if should retry
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            task.next_run = datetime.now() + timedelta(minutes=task.retry_delay_minutes)
            
            logger.warning(
                "Task failed, will retry",
                task_id=task.task_id,
                retry_count=task.retry_count,
                max_retries=task.max_retries,
                next_retry=task.next_run,
                error=error_message
            )
        else:
            task.status = TaskStatus.FAILED
            
            logger.error(
                "Task failed permanently",
                task_id=task.task_id,
                retry_count=task.retry_count,
                max_retries=task.max_retries,
                error=error_message
            )
    
    def _serialize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize monitoring result for storage."""
        serialized = {}
        
        for platform, monitoring_result in result.items():
            serialized[platform] = {
                "success": monitoring_result.success,
                "accounts_found": len(monitoring_result.accounts_found),
                "impersonations_detected": len(monitoring_result.impersonations_detected),
                "fake_accounts": len(monitoring_result.fake_accounts),
                "reports_created": len(monitoring_result.reports_created),
                "execution_time": monitoring_result.execution_time,
                "error_message": monitoring_result.error_message
            }
        
        return serialized
    
    def get_worker_statistics(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        return {
            "pool_size": self.pool_size,
            "active_workers": len([w for w in self.workers if not w.done()]),
            "active_executions": len(self.active_executions),
            "completed_executions": len(self.completed_executions),
            "total_executions": len(self.completed_executions) + len(self.active_executions)
        }


class MonitoringScheduler:
    """Main scheduler for social media monitoring tasks."""
    
    def __init__(self, config: MonitoringConfig, monitoring_service: SocialMediaMonitoringService):
        self.config = config
        self.monitoring_service = monitoring_service
        self.scheduler = AsyncIOScheduler()
        self.task_queue = TaskQueue(max_size=5000)
        self.worker_pool = WorkerPool(pool_size=5, monitoring_service=monitoring_service)
        
        # Task registry
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.profile_schedules: Dict[int, List[str]] = {}  # profile_id -> task_ids
        
        self.logger = logger.bind(service="monitoring_scheduler")
        
        # Setup scheduler event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    async def start(self) -> None:
        """Start the monitoring scheduler."""
        self.logger.info("Starting monitoring scheduler")
        
        # Start components
        await self.worker_pool.start(self.task_queue)
        self.scheduler.start()
        
        # Schedule periodic task queue processing
        self.scheduler.add_job(
            self._process_task_queue,
            IntervalTrigger(seconds=10),
            id="task_queue_processor",
            name="Process Task Queue"
        )
        
        # Schedule periodic cleanup
        self.scheduler.add_job(
            self._cleanup_old_tasks,
            CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id="daily_cleanup",
            name="Daily Cleanup"
        )
        
        self.logger.info("Monitoring scheduler started")
    
    async def stop(self) -> None:
        """Stop the monitoring scheduler."""
        self.logger.info("Stopping monitoring scheduler")
        
        self.scheduler.shutdown(wait=True)
        await self.worker_pool.stop()
        
        self.logger.info("Monitoring scheduler stopped")
    
    async def schedule_profile_monitoring(
        self,
        profile_id: int,
        platforms: List[SocialMediaPlatform],
        schedule_type: str = "daily",
        custom_schedule: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Schedule regular monitoring for a profile."""
        
        task_id = f"profile_{profile_id}_{uuid.uuid4().hex[:8]}"
        
        # Determine schedule
        schedule_expression = None
        interval_minutes = None
        
        if custom_schedule:
            schedule_expression = custom_schedule
        else:
            # Predefined schedules
            if schedule_type == "hourly":
                interval_minutes = 60
            elif schedule_type == "daily":
                schedule_expression = "0 9 * * *"  # Daily at 9 AM
            elif schedule_type == "weekly":
                schedule_expression = "0 9 * * 1"  # Monday at 9 AM
            else:
                interval_minutes = 60  # Default to hourly
        
        # Create scheduled task
        task = ScheduledTask(
            task_id=task_id,
            profile_id=profile_id,
            platforms=platforms,
            task_type="periodic",
            priority=priority,
            schedule_expression=schedule_expression,
            interval_minutes=interval_minutes,
            next_run=datetime.now() + timedelta(minutes=1),  # Start in 1 minute
            metadata={
                "schedule_type": schedule_type,
                "created_by": "scheduler"
            }
        )
        
        # Register task
        self.scheduled_tasks[task_id] = task
        
        if profile_id not in self.profile_schedules:
            self.profile_schedules[profile_id] = []
        self.profile_schedules[profile_id].append(task_id)
        
        # Add to APScheduler
        if schedule_expression:
            self.scheduler.add_job(
                self._queue_task,
                CronTrigger.from_crontab(schedule_expression),
                args=[task_id],
                id=task_id,
                name=f"Monitor Profile {profile_id}",
                replace_existing=True
            )
        elif interval_minutes:
            self.scheduler.add_job(
                self._queue_task,
                IntervalTrigger(minutes=interval_minutes),
                args=[task_id],
                id=task_id,
                name=f"Monitor Profile {profile_id}",
                replace_existing=True
            )
        
        self.logger.info(
            "Profile monitoring scheduled",
            task_id=task_id,
            profile_id=profile_id,
            schedule_type=schedule_type,
            platforms=[p.value for p in platforms]
        )
        
        return task_id
    
    async def schedule_one_time_monitoring(
        self,
        profile_id: int,
        platforms: List[SocialMediaPlatform],
        run_at: Optional[datetime] = None,
        priority: TaskPriority = TaskPriority.HIGH
    ) -> str:
        """Schedule one-time monitoring for a profile."""
        
        task_id = f"onetime_{profile_id}_{uuid.uuid4().hex[:8]}"
        
        if not run_at:
            run_at = datetime.now() + timedelta(minutes=1)
        
        task = ScheduledTask(
            task_id=task_id,
            profile_id=profile_id,
            platforms=platforms,
            task_type="one_time",
            priority=priority,
            next_run=run_at,
            metadata={"created_by": "scheduler"}
        )
        
        self.scheduled_tasks[task_id] = task
        
        # Queue task immediately if it should run now or soon
        if run_at <= datetime.now() + timedelta(minutes=5):
            await self.task_queue.put(task)
        else:
            # Schedule with APScheduler for future execution
            self.scheduler.add_job(
                self._queue_task,
                "date",
                run_date=run_at,
                args=[task_id],
                id=task_id,
                name=f"One-time Monitor Profile {profile_id}"
            )
        
        self.logger.info(
            "One-time monitoring scheduled",
            task_id=task_id,
            profile_id=profile_id,
            run_at=run_at
        )
        
        return task_id
    
    async def schedule_emergency_monitoring(
        self,
        profile_id: int,
        platforms: List[SocialMediaPlatform],
        reason: str = "Emergency"
    ) -> str:
        """Schedule emergency monitoring with highest priority."""
        
        task_id = f"emergency_{profile_id}_{uuid.uuid4().hex[:8]}"
        
        task = ScheduledTask(
            task_id=task_id,
            profile_id=profile_id,
            platforms=platforms,
            task_type="emergency",
            priority=TaskPriority.EMERGENCY,
            next_run=datetime.now(),  # Run immediately
            max_retries=1,  # Limited retries for emergency
            timeout_minutes=15,  # Shorter timeout
            metadata={
                "reason": reason,
                "created_by": "emergency_scheduler"
            }
        )
        
        self.scheduled_tasks[task_id] = task
        
        # Queue immediately
        await self.task_queue.put(task)
        
        self.logger.warning(
            "Emergency monitoring scheduled",
            task_id=task_id,
            profile_id=profile_id,
            reason=reason
        )
        
        return task_id
    
    async def _queue_task(self, task_id: str) -> None:
        """Queue a task for execution."""
        task = self.scheduled_tasks.get(task_id)
        if not task:
            self.logger.warning("Task not found for queueing", task_id=task_id)
            return
        
        if not task.enabled:
            self.logger.debug("Task disabled, skipping", task_id=task_id)
            return
        
        # Update next run time for periodic tasks
        if task.task_type == "periodic" and task.interval_minutes:
            task.next_run = datetime.now() + timedelta(minutes=task.interval_minutes)
        
        task.status = TaskStatus.QUEUED
        success = await self.task_queue.put(task)
        
        if success:
            self.logger.debug("Task queued", task_id=task_id)
        else:
            self.logger.warning("Failed to queue task", task_id=task_id)
    
    async def _process_task_queue(self) -> None:
        """Process tasks from queue (scheduled job)."""
        # This runs periodically to ensure tasks are processed
        # The actual processing is handled by the worker pool
        queue_size = await self.task_queue.size()
        
        if queue_size > 0:
            self.logger.debug("Processing task queue", queue_size=queue_size)
    
    async def _cleanup_old_tasks(self) -> None:
        """Clean up old completed tasks (scheduled job)."""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # Remove old completed/failed tasks
        tasks_to_remove = []
        for task_id, task in self.scheduled_tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.last_run and task.last_run < cutoff_date):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.scheduled_tasks[task_id]
            
            # Remove from profile schedules
            for profile_id, task_list in self.profile_schedules.items():
                if task_id in task_list:
                    task_list.remove(task_id)
        
        self.logger.info("Cleaned up old tasks", removed_count=len(tasks_to_remove))
    
    def _job_executed(self, event):
        """Handle job execution event."""
        self.logger.debug("Scheduled job executed", job_id=event.job_id)
    
    def _job_error(self, event):
        """Handle job error event."""
        self.logger.error(
            "Scheduled job error",
            job_id=event.job_id,
            exception=str(event.exception)
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self.scheduled_tasks.get(task_id)
        if not task:
            return False
        
        # Remove from APScheduler
        try:
            self.scheduler.remove_job(task_id)
        except:
            pass  # Job might not exist in scheduler
        
        # Remove from queue
        await self.task_queue.remove_task(task_id)
        
        # Update task status
        task.status = TaskStatus.CANCELLED
        task.enabled = False
        
        self.logger.info("Task cancelled", task_id=task_id)
        return True
    
    async def pause_profile_monitoring(self, profile_id: int) -> int:
        """Pause all monitoring for a profile."""
        task_ids = self.profile_schedules.get(profile_id, [])
        paused_count = 0
        
        for task_id in task_ids:
            task = self.scheduled_tasks.get(task_id)
            if task and task.enabled:
                task.enabled = False
                try:
                    self.scheduler.pause_job(task_id)
                    paused_count += 1
                except:
                    pass
        
        self.logger.info("Paused profile monitoring", profile_id=profile_id, tasks_paused=paused_count)
        return paused_count
    
    async def resume_profile_monitoring(self, profile_id: int) -> int:
        """Resume all monitoring for a profile."""
        task_ids = self.profile_schedules.get(profile_id, [])
        resumed_count = 0
        
        for task_id in task_ids:
            task = self.scheduled_tasks.get(task_id)
            if task and not task.enabled:
                task.enabled = True
                try:
                    self.scheduler.resume_job(task_id)
                    resumed_count += 1
                except:
                    pass
        
        self.logger.info("Resumed profile monitoring", profile_id=profile_id, tasks_resumed=resumed_count)
        return resumed_count
    
    def get_scheduler_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        task_status_counts = {}
        task_type_counts = {}
        
        for task in self.scheduled_tasks.values():
            # Count by status
            status = task.status.value
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
            
            # Count by type
            task_type = task.task_type
            task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
        
        return {
            "total_tasks": len(self.scheduled_tasks),
            "active_profiles": len(self.profile_schedules),
            "task_status_distribution": task_status_counts,
            "task_type_distribution": task_type_counts,
            "scheduler_running": self.scheduler.running,
            "scheduled_jobs": len(self.scheduler.get_jobs()),
            "worker_statistics": self.worker_pool.get_worker_statistics()
        }
    
    async def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a task."""
        task = self.scheduled_tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "profile_id": task.profile_id,
            "platforms": [p.value for p in task.platforms],
            "task_type": task.task_type,
            "priority": task.priority.name,
            "status": task.status.value,
            "enabled": task.enabled,
            "schedule_expression": task.schedule_expression,
            "interval_minutes": task.interval_minutes,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "created_at": task.created_at.isoformat(),
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_success": task.last_success.isoformat() if task.last_success else None,
            "last_error": task.last_error,
            "total_runs": task.total_runs,
            "successful_runs": task.successful_runs,
            "failed_runs": task.failed_runs,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "metadata": task.metadata
        }
    
    async def list_profile_tasks(self, profile_id: int) -> List[Dict[str, Any]]:
        """List all tasks for a specific profile."""
        task_ids = self.profile_schedules.get(profile_id, [])
        tasks = []
        
        for task_id in task_ids:
            task_details = await self.get_task_details(task_id)
            if task_details:
                tasks.append(task_details)
        
        return tasks