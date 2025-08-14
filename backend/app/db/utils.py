"""
Database utility functions for health checks, connection management, and monitoring.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.pool import Pool

from app.core.config import settings
from app.db.session import engine, AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseHealthChecker:
    """Database health monitoring and connection management."""
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.last_check = 0
        self.is_healthy = True
        self.error_count = 0
        self.max_retries = settings.DATABASE_MAX_RETRIES
        self.retry_delay = settings.DATABASE_RETRY_DELAY
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check.
        
        Returns:
            Dictionary containing health status and metrics
        """
        start_time = time.time()
        health_info = {
            "healthy": False,
            "timestamp": start_time,
            "response_time": 0,
            "pool_info": {},
            "error": None,
            "version": None,
            "active_connections": 0
        }
        
        try:
            # Test basic connectivity with a simple query
            async with AsyncSessionLocal() as session:
                # Get database version
                version_result = await session.execute(text("SELECT version()"))
                health_info["version"] = version_result.scalar()
                
                # Test a simple query
                test_result = await session.execute(text("SELECT 1 as test"))
                if test_result.scalar() == 1:
                    health_info["healthy"] = True
                    self.is_healthy = True
                    self.error_count = 0
                
                # Get active connection count
                connection_count_result = await session.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                health_info["active_connections"] = connection_count_result.scalar()
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_info["error"] = str(e)
            self.is_healthy = False
            self.error_count += 1
        
        # Get connection pool information
        if hasattr(self.engine, 'pool'):
            pool: Pool = self.engine.pool
            health_info["pool_info"] = {
                "size": getattr(pool, 'size', lambda: None)(),
                "checked_in": getattr(pool, 'checkedin', lambda: None)(),
                "checked_out": getattr(pool, 'checkedout', lambda: None)(),
                "overflow": getattr(pool, 'overflow', lambda: None)(),
                "invalid": getattr(pool, 'invalidated', lambda: None)(),
            }
        
        health_info["response_time"] = (time.time() - start_time) * 1000
        self.last_check = time.time()
        
        return health_info
    
    async def wait_for_connection(self, timeout: int = 60) -> bool:
        """
        Wait for database to become available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if connection is established, False otherwise
        """
        start_time = time.time()
        retry_count = 0
        
        while time.time() - start_time < timeout and retry_count < self.max_retries:
            try:
                health_info = await self.check_connection()
                if health_info["healthy"]:
                    logger.info(f"Database connection established after {retry_count} retries")
                    return True
                    
            except Exception as e:
                logger.warning(f"Database connection attempt {retry_count + 1} failed: {e}")
            
            retry_count += 1
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay)
        
        logger.error(f"Failed to establish database connection after {timeout} seconds")
        return False


# Global health checker instance
health_checker = DatabaseHealthChecker(engine)


async def get_database_health() -> Dict[str, Any]:
    """Get current database health status."""
    return await health_checker.check_connection()


async def wait_for_database(timeout: int = 60) -> bool:
    """Wait for database to become available."""
    return await health_checker.wait_for_connection(timeout)


@asynccontextmanager
async def get_db_with_retry(max_retries: int = 3) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with automatic retry on connection failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Yields:
        AsyncSession instance
        
    Raises:
        SQLAlchemyError: If all retry attempts fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            async with AsyncSessionLocal() as session:
                # Test the connection
                await session.execute(text("SELECT 1"))
                yield session
                await session.commit()
                return
                
        except (SQLAlchemyError, DisconnectionError) as e:
            last_exception = e
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries:
                await asyncio.sleep(settings.DATABASE_RETRY_DELAY)
                continue
            else:
                logger.error(f"All {max_retries + 1} database connection attempts failed")
                raise
        
        except Exception as e:
            # For non-database errors, don't retry
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
    
    if last_exception:
        raise last_exception


async def execute_with_retry(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> Any:
    """
    Execute a database query with automatic retry on failures.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        max_retries: Maximum number of retry attempts
        
    Returns:
        Query result
        
    Raises:
        SQLAlchemyError: If all retry attempts fail
    """
    async with get_db_with_retry(max_retries) as session:
        if params:
            result = await session.execute(text(query), params)
        else:
            result = await session.execute(text(query))
        return result


class DatabaseMetrics:
    """Database performance metrics collector."""
    
    @staticmethod
    async def get_connection_stats() -> Dict[str, Any]:
        """Get database connection statistics."""
        async with AsyncSessionLocal() as session:
            # Get active connections
            active_conn_query = text("""
                SELECT count(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active' AND pid != pg_backend_pid()
            """)
            
            # Get connection states
            conn_states_query = text("""
                SELECT state, count(*) as count
                FROM pg_stat_activity 
                WHERE pid != pg_backend_pid()
                GROUP BY state
            """)
            
            # Get slow queries
            slow_queries_query = text(f"""
                SELECT query, query_start, state, waiting
                FROM pg_stat_activity 
                WHERE state != 'idle' 
                AND query_start < now() - interval '{settings.DATABASE_SLOW_QUERY_THRESHOLD} seconds'
                AND pid != pg_backend_pid()
                LIMIT 10
            """)
            
            active_result = await session.execute(active_conn_query)
            states_result = await session.execute(conn_states_query)
            slow_result = await session.execute(slow_queries_query)
            
            return {
                "active_connections": active_result.scalar(),
                "connection_states": {row.state: row.count for row in states_result},
                "slow_queries": [
                    {
                        "query": row.query[:200] + "..." if len(row.query) > 200 else row.query,
                        "started": row.query_start,
                        "state": row.state,
                        "waiting": row.waiting
                    }
                    for row in slow_result
                ]
            }
    
    @staticmethod
    async def get_database_size() -> Dict[str, Any]:
        """Get database size information."""
        async with AsyncSessionLocal() as session:
            db_size_query = text(f"""
                SELECT pg_size_pretty(pg_database_size('{settings.POSTGRES_DB}')) as size,
                       pg_database_size('{settings.POSTGRES_DB}') as size_bytes
            """)
            
            table_sizes_query = text("""
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                       pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
            
            db_result = await session.execute(db_size_query)
            tables_result = await session.execute(table_sizes_query)
            
            db_info = db_result.fetchone()
            
            return {
                "database_size": db_info.size,
                "database_size_bytes": db_info.size_bytes,
                "largest_tables": [
                    {
                        "schema": row.schemaname,
                        "table": row.tablename,
                        "size": row.size,
                        "size_bytes": row.size_bytes
                    }
                    for row in tables_result
                ]
            }


# Initialize metrics collector
db_metrics = DatabaseMetrics()


async def log_query_performance(query: str, duration: float):
    """Log slow query performance."""
    if duration > settings.DATABASE_SLOW_QUERY_THRESHOLD:
        logger.warning(
            f"Slow query detected (took {duration:.2f}s): "
            f"{query[:200]}{'...' if len(query) > 200 else ''}"
        )


async def cleanup_connections():
    """Clean up database connections and pool."""
    try:
        # Dispose of the connection pool
        await engine.dispose()
        logger.info("Database connections cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up database connections: {e}")


async def initialize_database():
    """Initialize database connection and perform startup checks."""
    logger.info("Initializing database connection...")
    
    try:
        # Wait for database to be available
        if not await wait_for_database():
            raise RuntimeError("Database is not available")
        
        # Perform initial health check
        health_info = await get_database_health()
        if not health_info["healthy"]:
            raise RuntimeError(f"Database health check failed: {health_info['error']}")
        
        logger.info(
            f"Database initialized successfully. "
            f"Version: {health_info['version']}, "
            f"Response time: {health_info['response_time']:.2f}ms"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise