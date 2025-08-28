"""
Base worker functionality and shared utilities for all AutoDMCA background tasks.

This module provides common functionality, error handling patterns, and base classes
that all worker modules inherit from to ensure consistency and reliability.
"""

import logging
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Type, Callable
from functools import wraps
from celery import Task
from celery.exceptions import Retry, Ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app, TaskPriority
from app.db.session import get_async_session
from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseWorkerTask(Task):
    """Base task class with enhanced error handling and database session management."""
    
    # Task configuration
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True
    
    def __init__(self):
        self.db_session: Optional[AsyncSession] = None
    
    async def get_db_session(self) -> AsyncSession:
        """Get database session for this task."""
        if self.db_session is None:
            self.db_session = await get_async_session().__anext__()
        return self.db_session
    
    async def close_db_session(self):
        """Close database session."""
        if self.db_session:
            await self.db_session.close()
            self.db_session = None
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict):
        """Called on task success."""
        logger.info(f"Task {self.name} [{task_id}] completed successfully")
        
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any):
        """Called on task failure."""
        logger.error(
            f"Task {self.name} [{task_id}] failed: {exc}\n"
            f"Args: {args}\n"
            f"Kwargs: {kwargs}\n"
            f"Traceback: {einfo}"
        )
        
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any):
        """Called on task retry."""
        logger.warning(
            f"Task {self.name} [{task_id}] retrying due to: {exc}\n"
            f"Retry count: {self.request.retries}"
        )


def worker_task(
    priority: int = TaskPriority.NORMAL,
    queue: Optional[str] = None,
    max_retries: int = 3,
    countdown: int = 60,
    time_limit: int = 300,  # 5 minutes default
    soft_time_limit: int = 240,  # 4 minutes soft limit
    bind: bool = True
):
    """
    Decorator for creating AutoDMCA worker tasks with consistent configuration.
    
    Args:
        priority: Task priority level (use TaskPriority constants)
        queue: Specific queue to route task to (auto-determined if None)
        max_retries: Maximum number of retry attempts
        countdown: Delay before retry in seconds
        time_limit: Hard time limit for task execution
        soft_time_limit: Soft time limit before SIGTERM is sent
        bind: Whether to bind task instance as first argument
    """
    def decorator(func: Callable) -> Callable:
        # Determine queue from function name if not specified
        task_queue = queue
        if not task_queue:
            from app.core.celery_app import route_task
            routing = route_task(func.__name__, priority)
            task_queue = routing['queue']
        
        @wraps(func)
        @celery_app.task(
            bind=bind,
            base=BaseWorkerTask,
            queue=task_queue,
            priority=priority,
            max_retries=max_retries,
            default_retry_delay=countdown,
            time_limit=time_limit,
            soft_time_limit=soft_time_limit,
            acks_late=True,
            reject_on_worker_lost=True
        )
        async def wrapper(self, *args, **kwargs):
            """Task wrapper with error handling and session management."""
            task_id = self.request.id
            start_time = datetime.utcnow()
            
            logger.info(
                f"Starting task {func.__name__} [{task_id}] "
                f"with args={args}, kwargs={kwargs}"
            )
            
            try:
                # Execute the actual task function
                result = await func(self, *args, **kwargs)
                
                # Log execution time
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"Task {func.__name__} [{task_id}] completed in {execution_time:.2f}s"
                )
                
                return result
                
            except Exception as exc:
                # Log the error
                logger.error(
                    f"Task {func.__name__} [{task_id}] failed after "
                    f"{(datetime.utcnow() - start_time).total_seconds():.2f}s: {exc}\n"
                    f"Traceback: {traceback.format_exc()}"
                )
                
                # Determine if we should retry
                if self.request.retries < max_retries:
                    logger.warning(f"Retrying task {func.__name__} [{task_id}] in {countdown}s")
                    raise self.retry(countdown=countdown, exc=exc)
                
                # Max retries reached, mark as failed
                logger.error(f"Task {func.__name__} [{task_id}] failed permanently after {max_retries} retries")
                raise exc
                
            finally:
                # Always clean up database session
                await self.close_db_session()
        
        return wrapper
    return decorator


class WorkerContext:
    """Context manager for worker tasks with database session and error handling."""
    
    def __init__(self, task_name: str, task_id: str):
        self.task_name = task_name
        self.task_id = task_id
        self.db_session: Optional[AsyncSession] = None
        self.start_time = datetime.utcnow()
    
    async def __aenter__(self):
        """Enter the context manager."""
        logger.info(f"Starting worker context for {self.task_name} [{self.task_id}]")
        self.db_session = await get_async_session().__anext__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager with cleanup."""
        try:
            if self.db_session:
                if exc_type is None:
                    # Success - commit any pending transactions
                    await self.db_session.commit()
                else:
                    # Error - rollback any pending transactions
                    await self.db_session.rollback()
                
                await self.db_session.close()
            
            execution_time = (datetime.utcnow() - self.start_time).total_seconds()
            
            if exc_type is None:
                logger.info(
                    f"Worker context for {self.task_name} [{self.task_id}] "
                    f"completed successfully in {execution_time:.2f}s"
                )
            else:
                logger.error(
                    f"Worker context for {self.task_name} [{self.task_id}] "
                    f"failed after {execution_time:.2f}s: {exc_val}"
                )
        
        except Exception as cleanup_exc:
            logger.error(f"Error during context cleanup: {cleanup_exc}")
        
        # Don't suppress exceptions
        return False


def create_task_context(task_name: str, task_id: str) -> WorkerContext:
    """Create a worker context for the given task."""
    return WorkerContext(task_name, task_id)


class TaskStatus:
    """Constants for task status tracking."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class WorkerMetrics:
    """Utility class for tracking worker performance metrics."""
    
    @staticmethod
    async def record_task_execution(
        task_name: str,
        task_id: str,
        execution_time: float,
        status: str,
        error_message: Optional[str] = None
    ):
        """Record task execution metrics."""
        # This would integrate with monitoring service (DataDog, New Relic, etc.)
        metric_data = {
            'task_name': task_name,
            'task_id': task_id,
            'execution_time': execution_time,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if error_message:
            metric_data['error_message'] = error_message
        
        # Log metrics for now (would send to monitoring service)
        logger.info(f"Task metrics: {metric_data}")
    
    @staticmethod
    async def record_queue_metrics():
        """Record queue length and processing metrics."""
        from app.core.celery_app import celery_manager
        
        try:
            queue_lengths = celery_manager.get_queue_lengths()
            worker_stats = celery_manager.get_worker_stats()
            
            metrics = {
                'queue_lengths': queue_lengths,
                'worker_stats': worker_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Queue metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Error recording queue metrics: {e}")


# Health check utilities
async def check_redis_connection() -> bool:
    """Check if Redis connection is healthy."""
    try:
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL or 'redis://localhost:6379/0')
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


async def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        async with create_task_context("health_check", "db_check") as ctx:
            # Simple query to test connection
            result = await ctx.db_session.execute("SELECT 1")
            return result is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Export commonly used items
__all__ = [
    'BaseWorkerTask',
    'worker_task',
    'WorkerContext',
    'create_task_context',
    'TaskStatus',
    'WorkerMetrics',
    'check_redis_connection',
    'check_database_connection'
]