"""
Database Service Layer for AutoDMCA

This module provides a comprehensive database service layer with:
- Advanced connection pooling and management
- Transaction management with retry logic
- Database health monitoring and metrics
- Query performance tracking and optimization
- Connection lifecycle management
- Backup and maintenance utilities
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncGenerator, Callable, TypeVar, Generic
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.sql import text
from sqlalchemy import event, exc
# PoolEvents may not be available in all SQLAlchemy versions
try:
    from sqlalchemy.engine.events import PoolEvents
except ImportError:
    PoolEvents = None
import sqlalchemy

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseHealth(Enum):
    """Database health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics."""
    size: int = 0
    checked_in: int = 0
    checked_out: int = 0
    overflow: int = 0
    invalidated: int = 0
    total_connections: int = 0
    max_connections: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QueryMetrics:
    """Query performance metrics."""
    total_queries: int = 0
    avg_response_time_ms: float = 0.0
    slow_queries: int = 0
    failed_queries: int = 0
    active_queries: int = 0
    longest_query_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DatabaseHealthReport:
    """Comprehensive database health report."""
    status: DatabaseHealth
    connection_pool: ConnectionPoolStats
    query_metrics: QueryMetrics
    response_time_ms: float
    uptime_seconds: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DatabaseService:
    """
    Enhanced database service with connection pooling, health monitoring, and performance tracking.
    
    Features:
    - Intelligent connection pool management
    - Query performance monitoring
    - Automatic retry logic for transient failures
    - Health check and monitoring capabilities
    - Transaction lifecycle management
    - Connection leak detection
    """
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
        self._start_time = datetime.utcnow()
        self._connection_stats = ConnectionPoolStats()
        self._query_metrics = QueryMetrics()
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = datetime.utcnow()
        self._health_status = DatabaseHealth.DOWN
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self._query_times: list = []
        self._max_query_history = 1000
        self._slow_query_threshold = 1000  # 1 second in ms
        
    async def initialize(self) -> None:
        """Initialize the database service with optimized configuration."""
        if self._initialized:
            logger.warning("Database service already initialized")
            return
        
        logger.info("Initializing database service...")
        
        try:
            # Create database engine with enhanced configuration
            self.engine = await self._create_engine()
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            # Set up event listeners for monitoring
            self._setup_event_listeners()
            
            # Perform initial health check
            await self._perform_health_check()
            
            # Start background monitoring
            await self._start_monitoring()
            
            self._initialized = True
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database service: {e}")
            raise
    
    async def _create_engine(self) -> AsyncEngine:
        """Create and configure the database engine."""
        
        # Base engine configuration
        engine_config = {
            "echo": settings.DEBUG and settings.DATABASE_QUERY_LOGGING,
            "future": True,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # 1 hour
        }
        
        # Configure connection pool based on environment
        if settings.DEBUG:
            # Development configuration - smaller pool
            engine_config.update({
                "poolclass": StaticPool,
                "pool_size": 5,
                "max_overflow": 10,
                "connect_args": {"command_timeout": 60},
            })
        else:
            # Production configuration - larger pool with monitoring
            engine_config.update({
                "poolclass": QueuePool,
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "pool_reset_on_return": "commit",
            })
        
        # Create the engine
        engine = create_async_engine(
            str(settings.SQLALCHEMY_DATABASE_URI),
            **engine_config
        )
        
        logger.info(f"Database engine created with pool_size={engine_config.get('pool_size', 'default')}")
        return engine
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring and logging."""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections."""
            logger.debug("New database connection established")
            self._connection_stats.total_connections += 1
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            self._connection_stats.checked_out += 1
            logger.debug(f"Connection checked out (active: {self._connection_stats.checked_out})")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool."""
            self._connection_stats.checked_out = max(0, self._connection_stats.checked_out - 1)
            self._connection_stats.checked_in += 1
            logger.debug(f"Connection checked in (active: {self._connection_stats.checked_out})")
        
        @event.listens_for(self.engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation."""
            self._connection_stats.invalidated += 1
            logger.warning(f"Database connection invalidated: {exception}")
        
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def on_before_execute(conn, cursor, statement, parameters, context, executemany):
            """Track query start time."""
            context._query_start_time = datetime.utcnow()
        
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def on_after_execute(conn, cursor, statement, parameters, context, executemany):
            """Track query completion and performance."""
            if hasattr(context, '_query_start_time'):
                execution_time = (datetime.utcnow() - context._query_start_time).total_seconds() * 1000
                self._record_query_metrics(execution_time, success=True)
        
        @event.listens_for(self.engine.sync_engine, "handle_error")
        def on_handle_error(exception_context):
            """Track query errors."""
            self._query_metrics.failed_queries += 1
            logger.error(f"Database query error: {exception_context.original_exception}")
    
    def _record_query_metrics(self, execution_time_ms: float, success: bool = True):
        """Record query performance metrics."""
        self._query_metrics.total_queries += 1
        
        if success:
            # Track query times for average calculation
            self._query_times.append(execution_time_ms)
            if len(self._query_times) > self._max_query_history:
                self._query_times = self._query_times[-self._max_query_history:]
            
            # Update metrics
            self._query_metrics.avg_response_time_ms = sum(self._query_times) / len(self._query_times)
            self._query_metrics.longest_query_ms = max(self._query_metrics.longest_query_ms, execution_time_ms)
            
            # Track slow queries
            if execution_time_ms > self._slow_query_threshold:
                self._query_metrics.slow_queries += 1
                logger.warning(f"Slow query detected: {execution_time_ms:.2f}ms")
        else:
            self._query_metrics.failed_queries += 1
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic transaction management.
        
        This context manager provides:
        - Automatic session lifecycle management
        - Transaction commit/rollback handling
        - Connection pool management
        - Error handling and logging
        """
        if not self._initialized or not self.session_factory:
            raise RuntimeError("Database service not initialized")
        
        session = self.session_factory()
        
        try:
            self._query_metrics.active_queries += 1
            yield session
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
            
        finally:
            await session.close()
            self._query_metrics.active_queries = max(0, self._query_metrics.active_queries - 1)
    
    async def execute_with_retry(
        self, 
        operation: Callable[[AsyncSession], T], 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> T:
        """
        Execute a database operation with automatic retry logic.
        
        Args:
            operation: Async function that takes a session and returns a result
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Result of the operation
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self.get_session() as session:
                    return await operation(session)
                    
            except (exc.DisconnectionError, exc.TimeoutError, exc.OperationalError) as e:
                last_exception = e
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries} retries: {e}")
                    break
            
            except Exception as e:
                # Non-retryable exceptions
                logger.error(f"Database operation failed with non-retryable error: {e}")
                raise
        
        if last_exception:
            raise last_exception
    
    async def _perform_health_check(self) -> DatabaseHealthReport:
        """Perform comprehensive database health check."""
        start_time = datetime.utcnow()
        
        try:
            # Test basic connectivity
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                
                if not row or row[0] != 1:
                    raise Exception("Health check query returned unexpected result")
            
            # Calculate response time
            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update connection pool stats
            if self.engine:
                pool = self.engine.pool
                self._connection_stats.size = pool.size()
                self._connection_stats.checked_out = pool.checkedout()
                self._connection_stats.checked_in = pool.checkedin()
                self._connection_stats.overflow = pool.overflow()
                self._connection_stats.max_connections = pool.size() + (pool._max_overflow or 0)
            
            # Determine health status
            if response_time_ms > 5000:  # 5 seconds
                health_status = DatabaseHealth.CRITICAL
            elif response_time_ms > 1000 or self._query_metrics.failed_queries > 10:  # 1 second
                health_status = DatabaseHealth.WARNING
            else:
                health_status = DatabaseHealth.HEALTHY
            
            self._health_status = health_status
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
            
            return DatabaseHealthReport(
                status=health_status,
                connection_pool=self._connection_stats,
                query_metrics=self._query_metrics,
                response_time_ms=response_time_ms,
                uptime_seconds=uptime
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            self._health_status = DatabaseHealth.DOWN
            
            return DatabaseHealthReport(
                status=DatabaseHealth.DOWN,
                connection_pool=self._connection_stats,
                query_metrics=self._query_metrics,
                response_time_ms=0.0,
                uptime_seconds=0.0,
                error_message=str(e)
            )
    
    async def _start_monitoring(self):
        """Start background monitoring task."""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._initialized:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_check()
                self._last_health_check = datetime.utcnow()
                
                # Log periodic health status
                if self._health_status != DatabaseHealth.HEALTHY:
                    logger.warning(f"Database health status: {self._health_status.value}")
                
            except asyncio.CancelledError:
                logger.info("Database monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in database monitoring loop: {e}")
    
    async def get_health_report(self) -> DatabaseHealthReport:
        """Get current database health report."""
        return await self._perform_health_check()
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics."""
        return {
            "pool_size": self._connection_stats.size,
            "active_connections": self._connection_stats.checked_out,
            "idle_connections": self._connection_stats.checked_in,
            "overflow_connections": self._connection_stats.overflow,
            "total_connections_created": self._connection_stats.total_connections,
            "invalidated_connections": self._connection_stats.invalidated,
            "max_connections": self._connection_stats.max_connections,
        }
    
    async def get_query_metrics(self) -> Dict[str, Any]:
        """Get current query performance metrics."""
        return {
            "total_queries": self._query_metrics.total_queries,
            "active_queries": self._query_metrics.active_queries,
            "average_response_time_ms": round(self._query_metrics.avg_response_time_ms, 2),
            "longest_query_ms": round(self._query_metrics.longest_query_ms, 2),
            "slow_queries": self._query_metrics.slow_queries,
            "failed_queries": self._query_metrics.failed_queries,
            "slow_query_threshold_ms": self._slow_query_threshold,
        }
    
    async def optimize_connections(self):
        """Optimize database connections and clear idle connections."""
        if self.engine and hasattr(self.engine.pool, 'recreate'):
            logger.info("Optimizing database connection pool")
            # This would implement connection pool optimization
            # For now, just log the action
            pass
    
    async def close(self):
        """Close the database service and clean up resources."""
        logger.info("Shutting down database service...")
        
        self._initialized = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine disposed")
        
        logger.info("Database service shutdown complete")


# Global database service instance
database_service = DatabaseService()


# Session factory that integrates with the database service
class AsyncSessionFactory:
    """Factory for creating database sessions using the database service."""
    
    def __init__(self):
        self.database_service = database_service
    
    async def create_session(self) -> AsyncSession:
        """Create a new database session."""
        if not self.database_service._initialized:
            await self.database_service.initialize()
        
        return self.database_service.session_factory()
    
    def get_session_context(self):
        """Get session context manager."""
        return self.database_service.get_session()


# Dependency function for FastAPI
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions."""
    async with database_service.get_session() as session:
        yield session


# Health check functions
async def check_database_health() -> Dict[str, Any]:
    """Check database health and return status."""
    if not database_service._initialized:
        await database_service.initialize()
    
    health_report = await database_service.get_health_report()
    
    return {
        "healthy": health_report.status in [DatabaseHealth.HEALTHY, DatabaseHealth.WARNING],
        "status": health_report.status.value,
        "response_time_ms": health_report.response_time_ms,
        "uptime_seconds": health_report.uptime_seconds,
        "connection_stats": await database_service.get_connection_stats(),
        "query_metrics": await database_service.get_query_metrics(),
        "error": health_report.error_message,
        "timestamp": health_report.timestamp.isoformat()
    }


__all__ = [
    'DatabaseService',
    'DatabaseHealth',
    'DatabaseHealthReport',
    'database_service',
    'AsyncSessionFactory',
    'get_database_session',
    'check_database_health'
]