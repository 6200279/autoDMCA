"""
Scan scheduler for automated content monitoring and DMCA processing.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
import aioredis
import structlog

from ..config import ScannerSettings


logger = structlog.get_logger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    IMMEDIATE = 5


@dataclass
class ScanTask:
    """Represents a scanning task."""
    
    # Identification
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    person_id: str = ""
    
    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Scheduling
    schedule_type: str = "interval"  # interval, cron, once
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    next_run_time: Optional[float] = None
    
    # State
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    
    # Execution tracking
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None
    execution_time: Optional[float] = None
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: int = 300  # 5 minutes
    retry_count: int = 0
    
    # Results
    last_results: Optional[Dict] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.next_run_time and not self.next_run_at:
            self.next_run_at = self.next_run_time
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries
        )
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        return (
            self.next_run_at and
            time.time() > self.next_run_at + 3600  # 1 hour grace period
        )
    
    def update_status(self, status: TaskStatus, error: str = None):
        """Update task status."""
        self.status = status
        self.updated_at = time.time()
        
        if error:
            self.last_error = error
            self.failure_count += 1
        
        if status == TaskStatus.RUNNING:
            self.last_run_at = time.time()
            self.run_count += 1
        elif status == TaskStatus.COMPLETED:
            self.success_count += 1
            self.retry_count = 0
        elif status == TaskStatus.FAILED:
            if self.can_retry:
                self.status = TaskStatus.RETRY
                self.retry_count += 1
                # Schedule retry
                self.next_run_at = time.time() + self.retry_delay
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScanTask':
        """Create from dictionary."""
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = TaskPriority(data['priority'])
        
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        
        return cls(**data)


class ScanScheduler:
    """Advanced task scheduler for content scanning operations."""
    
    def __init__(self, settings: ScannerSettings):
        self.settings = settings
        self.redis: Optional[aioredis.Redis] = None
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.tasks: Dict[str, ScanTask] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the scheduler."""
        # Connect to Redis
        self.redis = aioredis.from_url(
            self.settings.redis_url,
            encoding='utf-8',
            decode_responses=True
        )
        
        # Configure scheduler
        jobstores = {
            'default': RedisJobStore(
                host=self.settings.redis_url.split('@')[-1].split(':')[0] if '@' in self.settings.redis_url else 'localhost',
                port=int(self.settings.redis_url.split(':')[-1].split('/')[0]) if ':' in self.settings.redis_url else 6379,
                db=1
            )
        }
        
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5 minutes
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Load existing tasks
        await self._load_tasks()
        
        # Start scheduler
        self.scheduler.start()
        self._running = True
        
        logger.info("Scan scheduler initialized")
    
    async def close(self):
        """Shut down the scheduler."""
        self._running = False
        
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Scan scheduler shut down")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type."""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered task handler: {task_type}")
    
    async def schedule_task(
        self,
        task_type: str,
        person_id: str,
        parameters: Dict[str, Any] = None,
        schedule_type: str = "interval",
        interval_seconds: int = None,
        cron_expression: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        task_id: str = None
    ) -> str:
        """Schedule a new task."""
        task = ScanTask(
            task_id=task_id or str(uuid.uuid4()),
            task_type=task_type,
            person_id=person_id,
            parameters=parameters or {},
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            priority=priority,
            max_retries=max_retries
        )
        
        async with self._lock:
            # Store task
            self.tasks[task.task_id] = task
            await self._persist_task(task)
            
            # Schedule with APScheduler
            await self._schedule_with_apscheduler(task)
        
        logger.info(
            f"Task scheduled: {task.task_id}",
            task_type=task_type,
            person_id=person_id,
            schedule_type=schedule_type
        )
        
        return task.task_id
    
    async def _schedule_with_apscheduler(self, task: ScanTask):
        """Schedule task with APScheduler."""
        job_id = f"task_{task.task_id}"
        
        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Set up trigger
        trigger = None
        
        if task.schedule_type == "interval" and task.interval_seconds:
            trigger = IntervalTrigger(seconds=task.interval_seconds)
        elif task.schedule_type == "cron" and task.cron_expression:
            # Parse cron expression
            parts = task.cron_expression.split()
            if len(parts) >= 5:
                trigger = CronTrigger(
                    second=parts[0] if parts[0] != '*' else None,
                    minute=parts[1] if parts[1] != '*' else None,
                    hour=parts[2] if parts[2] != '*' else None,
                    day=parts[3] if parts[3] != '*' else None,
                    month=parts[4] if parts[4] != '*' else None,
                    day_of_week=parts[5] if len(parts) > 5 and parts[5] != '*' else None
                )
        elif task.schedule_type == "once":
            # Schedule for immediate execution
            next_run = datetime.now() + timedelta(seconds=5)
            self.scheduler.add_job(
                self._execute_task,
                'date',
                run_date=next_run,
                args=[task.task_id],
                id=job_id,
                max_instances=1
            )
            return
        
        if trigger:
            self.scheduler.add_job(
                self._execute_task,
                trigger,
                args=[task.task_id],
                id=job_id,
                max_instances=1
            )
    
    async def _execute_task(self, task_id: str):
        """Execute a scheduled task."""
        async with self._lock:
            task = self.tasks.get(task_id)
        
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Task already running: {task_id}")
            return
        
        # Update task status
        task.update_status(TaskStatus.RUNNING)
        await self._persist_task(task)
        
        start_time = time.time()
        
        try:
            # Get handler for task type
            handler = self.task_handlers.get(task.task_type)
            
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type}")
            
            # Execute task
            result = await handler(task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            task.execution_time = execution_time
            task.last_results = result
            
            # Update status
            task.update_status(TaskStatus.COMPLETED)
            
            logger.info(
                f"Task completed successfully: {task_id}",
                task_type=task.task_type,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            task.execution_time = execution_time
            
            error_msg = str(e)
            task.update_status(TaskStatus.FAILED, error_msg)
            
            logger.error(
                f"Task execution failed: {task_id}",
                task_type=task.task_type,
                error=error_msg,
                execution_time=execution_time
            )
            
            # Schedule retry if applicable
            if task.status == TaskStatus.RETRY:
                await self._schedule_retry(task)
        
        # Update task in storage
        await self._persist_task(task)
    
    async def _schedule_retry(self, task: ScanTask):
        """Schedule a task retry."""
        retry_job_id = f"retry_{task.task_id}_{task.retry_count}"
        
        retry_time = datetime.now() + timedelta(seconds=task.retry_delay)
        
        self.scheduler.add_job(
            self._execute_task,
            'date',
            run_date=retry_time,
            args=[task.task_id],
            id=retry_job_id,
            max_instances=1
        )
        
        logger.info(
            f"Task retry scheduled: {task.task_id}",
            retry_count=task.retry_count,
            retry_time=retry_time.isoformat()
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        async with self._lock:
            task = self.tasks.get(task_id)
            
            if not task:
                return False
            
            # Update task status
            task.update_status(TaskStatus.CANCELLED)
            await self._persist_task(task)
            
            # Remove from scheduler
            job_id = f"task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Remove retry jobs
            for i in range(task.retry_count + 1):
                retry_job_id = f"retry_{task_id}_{i}"
                if self.scheduler.get_job(retry_job_id):
                    self.scheduler.remove_job(retry_job_id)
        
        logger.info(f"Task cancelled: {task_id}")
        return True
    
    async def get_task(self, task_id: str) -> Optional[ScanTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    async def get_tasks_for_person(self, person_id: str) -> List[ScanTask]:
        """Get all tasks for a person."""
        return [task for task in self.tasks.values() if task.person_id == person_id]
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[ScanTask]:
        """Get tasks by status."""
        return [task for task in self.tasks.values() if task.status == status]
    
    async def get_overdue_tasks(self) -> List[ScanTask]:
        """Get overdue tasks."""
        return [task for task in self.tasks.values() if task.is_overdue]
    
    async def update_task_schedule(
        self,
        task_id: str,
        interval_seconds: int = None,
        cron_expression: str = None
    ) -> bool:
        """Update task schedule."""
        async with self._lock:
            task = self.tasks.get(task_id)
            
            if not task:
                return False
            
            # Update schedule parameters
            if interval_seconds:
                task.schedule_type = "interval"
                task.interval_seconds = interval_seconds
                task.cron_expression = None
            elif cron_expression:
                task.schedule_type = "cron"
                task.cron_expression = cron_expression
                task.interval_seconds = None
            
            task.updated_at = time.time()
            
            # Reschedule
            await self._schedule_with_apscheduler(task)
            await self._persist_task(task)
        
        logger.info(f"Task schedule updated: {task_id}")
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """Pause a task."""
        job_id = f"task_{task_id}"
        
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)
            
            async with self._lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus.PENDING
                    task.updated_at = time.time()
                    await self._persist_task(task)
            
            logger.info(f"Task paused: {task_id}")
            return True
        
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        job_id = f"task_{task_id}"
        
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            
            async with self._lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = TaskStatus.PENDING
                    task.updated_at = time.time()
                    await self._persist_task(task)
            
            logger.info(f"Task resumed: {task_id}")
            return True
        
        return False
    
    async def get_scheduler_stats(self) -> Dict:
        """Get scheduler statistics."""
        total_tasks = len(self.tasks)
        
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = len([
                t for t in self.tasks.values() if t.status == status
            ])
        
        # Job stats from APScheduler
        jobs = self.scheduler.get_jobs()
        
        stats = {
            'total_tasks': total_tasks,
            'status_counts': status_counts,
            'scheduled_jobs': len(jobs),
            'overdue_tasks': len(await self.get_overdue_tasks()),
            'scheduler_running': self.scheduler.running if self.scheduler else False,
            'task_types': {}
        }
        
        # Count by task type
        for task in self.tasks.values():
            task_type = task.task_type
            if task_type not in stats['task_types']:
                stats['task_types'][task_type] = 0
            stats['task_types'][task_type] += 1
        
        return stats
    
    async def _persist_task(self, task: ScanTask):
        """Persist task to Redis."""
        try:
            task_data = json.dumps(task.to_dict())
            await self.redis.hset("scanner:tasks", task.task_id, task_data)
        except Exception as e:
            logger.error(f"Failed to persist task: {task.task_id}", error=str(e))
    
    async def _load_tasks(self):
        """Load tasks from Redis."""
        try:
            task_data = await self.redis.hgetall("scanner:tasks")
            
            for task_id, data in task_data.items():
                try:
                    task_dict = json.loads(data)
                    task = ScanTask.from_dict(task_dict)
                    self.tasks[task_id] = task
                except Exception as e:
                    logger.error(f"Failed to load task: {task_id}", error=str(e))
            
            logger.info(f"Loaded {len(self.tasks)} tasks from storage")
            
        except Exception as e:
            logger.error("Failed to load tasks", error=str(e))
    
    async def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Clean up old completed/failed tasks."""
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        cleaned_count = 0
        
        async with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if (
                    task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.updated_at < cutoff_time
                ):
                    tasks_to_remove.append(task_id)
            
            # Remove old tasks
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                
                # Remove from Redis
                await self.redis.hdel("scanner:tasks", task_id)
                
                # Remove any scheduled jobs
                job_id = f"task_{task_id}"
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old tasks")
        
        return cleaned_count
    
    async def health_check(self) -> Dict:
        """Perform health check on scheduler."""
        health = {
            'scheduler_running': self.scheduler.running if self.scheduler else False,
            'redis_connected': False,
            'task_count': len(self.tasks),
            'active_jobs': 0,
            'overdue_count': 0,
            'errors': []
        }
        
        # Check Redis connection
        try:
            await self.redis.ping()
            health['redis_connected'] = True
        except Exception as e:
            health['errors'].append(f"Redis connection failed: {str(e)}")
        
        # Check scheduled jobs
        try:
            jobs = self.scheduler.get_jobs()
            health['active_jobs'] = len(jobs)
        except Exception as e:
            health['errors'].append(f"Failed to get jobs: {str(e)}")
        
        # Check for overdue tasks
        try:
            overdue_tasks = await self.get_overdue_tasks()
            health['overdue_count'] = len(overdue_tasks)
        except Exception as e:
            health['errors'].append(f"Failed to check overdue tasks: {str(e)}")
        
        health['healthy'] = len(health['errors']) == 0
        
        return health