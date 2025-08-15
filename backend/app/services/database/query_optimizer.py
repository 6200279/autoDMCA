"""
Database Query Optimization Service
Advanced query optimization, connection pooling, and performance monitoring
"""
import asyncio
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps

import sqlalchemy
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy.sql import Select
import redis.asyncio as redis

from app.core.config import settings
from app.services.cache.multi_level_cache import cache_manager

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    query_text: str
    execution_time_ms: float
    result_count: int
    cache_hit: bool
    timestamp: datetime
    connection_pool_size: int
    errors: int = 0


@dataclass
class ConnectionPoolMetrics:
    """Connection pool metrics"""
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int
    avg_checkout_time_ms: float


class QueryCache:
    """Intelligent query result caching with invalidation"""
    
    def __init__(self):
        self.cache_rules = {
            # Table -> TTL (seconds)
            'profiles': 1800,  # 30 minutes
            'scan_results': 600,  # 10 minutes
            'dmca_requests': 300,  # 5 minutes
            'content_matches': 600,
            'watermarks': 3600,  # 1 hour
            'billing_plans': 7200,  # 2 hours
            'settings': 3600
        }
        
        self.invalidation_patterns = {
            'profiles': ['profile:*', 'user:*'],
            'scan_results': ['scan:*', 'profile:*'],
            'dmca_requests': ['dmca:*', 'profile:*'],
            'content_matches': ['match:*', 'scan:*'],
            'watermarks': ['watermark:*'],
            'billing_plans': ['billing:*'],
            'settings': ['settings:*']
        }
    
    def get_cache_key(self, query_hash: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key for query"""
        key_parts = [f"query:{query_hash}"]
        if params:
            # Sort params for consistent key generation
            param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_parts.append(param_str)
        return ":".join(key_parts)
    
    def get_ttl_for_tables(self, tables: List[str]) -> int:
        """Get TTL based on tables involved in query"""
        if not tables:
            return 300  # Default 5 minutes
        
        # Use shortest TTL among involved tables
        ttls = [self.cache_rules.get(table, 300) for table in tables]
        return min(ttls)
    
    async def invalidate_for_table(self, table_name: str):
        """Invalidate cache entries for a specific table"""
        patterns = self.invalidation_patterns.get(table_name, [])
        for pattern in patterns:
            await cache_manager.invalidate_pattern(pattern, cache_type="database")


class OptimizedDatabase:
    """
    High-performance database service with advanced optimizations:
    
    - Connection pooling with intelligent sizing
    - Query result caching with smart invalidation
    - Slow query detection and optimization suggestions
    - Read/write replica support
    - Batch operation optimization
    - Connection health monitoring
    - Automatic index suggestion
    """
    
    def __init__(self):
        self.engines: Dict[str, AsyncEngine] = {}
        self.session_makers: Dict[str, async_sessionmaker] = {}
        self.query_cache = QueryCache()
        
        # Performance tracking
        self.query_metrics: List[QueryMetrics] = []
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 1000)
        self.enable_query_logging = getattr(settings, 'ENABLE_QUERY_LOGGING', False)
        
        # Connection pool configuration
        self.pool_config = {
            'pool_size': getattr(settings, 'DB_POOL_SIZE', 20),
            'max_overflow': getattr(settings, 'DB_MAX_OVERFLOW', 30),
            'pool_timeout': getattr(settings, 'DB_POOL_TIMEOUT', 30),
            'pool_recycle': getattr(settings, 'DB_POOL_RECYCLE', 3600),
            'pool_pre_ping': True
        }
        
        # Read/write separation
        self.read_replicas = getattr(settings, 'DB_READ_REPLICAS', [])
        self.write_preference = getattr(settings, 'DB_WRITE_PREFERENCE', 'primary')
        
        logger.info("Database optimizer initialized")
    
    async def initialize(self):
        """Initialize database connections and optimizations"""
        
        # Create primary engine (read/write)
        primary_engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI,
            poolclass=QueuePool,
            echo=self.enable_query_logging,
            **self.pool_config
        )
        
        self.engines['primary'] = primary_engine
        self.session_makers['primary'] = async_sessionmaker(
            primary_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create read replica engines
        for i, replica_uri in enumerate(self.read_replicas):
            engine_name = f'replica_{i}'
            replica_engine = create_async_engine(
                replica_uri,
                poolclass=QueuePool,
                echo=self.enable_query_logging,
                **self.pool_config
            )
            
            self.engines[engine_name] = replica_engine
            self.session_makers[engine_name] = async_sessionmaker(
                replica_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        
        # Set up query monitoring
        await self._setup_query_monitoring()
        
        # Test connections
        await self._test_connections()
        
        logger.info(f"Database initialized with {len(self.engines)} connections")
    
    async def _setup_query_monitoring(self):
        """Set up query performance monitoring"""
        
        @event.listens_for(sqlalchemy.Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(sqlalchemy.Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                execution_time = (time.time() - context._query_start_time) * 1000
                
                # Log slow queries
                if execution_time > self.slow_query_threshold:
                    logger.warning(
                        f"Slow query detected: {execution_time:.2f}ms\n"
                        f"Statement: {statement[:200]}..."
                    )
                    
                    # Store for analysis
                    asyncio.create_task(self._analyze_slow_query(statement, execution_time))
        
        logger.info("Query monitoring enabled")
    
    async def _test_connections(self):
        """Test all database connections"""
        for engine_name, engine in self.engines.items():
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    await result.fetchone()
                logger.info(f"Database connection '{engine_name}' tested successfully")
            except Exception as e:
                logger.error(f"Database connection '{engine_name}' test failed: {e}")
                raise
    
    async def _analyze_slow_query(self, statement: str, execution_time: float):
        """Analyze slow query and suggest optimizations"""
        suggestions = []
        
        statement_lower = statement.lower()
        
        # Basic optimization suggestions
        if 'select *' in statement_lower:
            suggestions.append("Consider selecting specific columns instead of '*'")
        
        if 'where' not in statement_lower and ('select' in statement_lower and 'from' in statement_lower):
            suggestions.append("Consider adding WHERE clause to limit results")
        
        if 'order by' in statement_lower and 'limit' not in statement_lower:
            suggestions.append("Consider adding LIMIT clause for ORDER BY queries")
        
        if 'join' in statement_lower and 'where' not in statement_lower:
            suggestions.append("Consider adding WHERE clause to filter joined results")
        
        # Log suggestions
        if suggestions:
            logger.info(f"Query optimization suggestions for {execution_time:.2f}ms query:")
            for suggestion in suggestions:
                logger.info(f"  - {suggestion}")
    
    def get_engine(self, operation: str = 'read') -> AsyncEngine:
        """Get appropriate engine based on operation type"""
        if operation == 'write' or not self.read_replicas:
            return self.engines['primary']
        
        # Round-robin for read operations
        replica_count = len(self.read_replicas)
        if replica_count > 0:
            replica_index = hash(time.time()) % replica_count
            return self.engines[f'replica_{replica_index}']
        
        return self.engines['primary']
    
    def get_session_maker(self, operation: str = 'read') -> async_sessionmaker:
        """Get appropriate session maker based on operation type"""
        if operation == 'write' or not self.read_replicas:
            return self.session_makers['primary']
        
        replica_count = len(self.read_replicas)
        if replica_count > 0:
            replica_index = hash(time.time()) % replica_count
            return self.session_makers[f'replica_{replica_index}']
        
        return self.session_makers['primary']
    
    @asynccontextmanager
    async def get_session(self, operation: str = 'read'):
        """Get database session with automatic selection"""
        session_maker = self.get_session_maker(operation)
        
        async with session_maker() as session:
            try:
                yield session
                if operation == 'write':
                    await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_cached_query(
        self,
        query: Union[str, Select],
        params: Dict[str, Any] = None,
        cache_ttl: Optional[int] = None,
        tables: List[str] = None,
        operation: str = 'read'
    ) -> Any:
        """Execute query with intelligent caching"""
        
        # Generate query hash for caching
        if isinstance(query, str):
            query_text = query
        else:
            query_text = str(query.compile(compile_kwargs={"literal_binds": True}))
        
        query_hash = str(hash(query_text))
        cache_key = self.query_cache.get_cache_key(query_hash, params)
        
        # Try cache first
        cached_result = await cache_manager.get(cache_key, cache_type="database")
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query_hash[:8]}...")
            return cached_result
        
        # Execute query
        start_time = time.time()
        
        async with self.get_session(operation) as session:
            if isinstance(query, str):
                result = await session.execute(text(query), params or {})
                rows = result.fetchall()
            else:
                result = await session.execute(query, params or {})
                rows = result.fetchall()
            
            # Convert to serializable format
            result_data = [dict(row) for row in rows] if rows else []
        
        execution_time = (time.time() - start_time) * 1000
        
        # Store metrics
        metrics = QueryMetrics(
            query_hash=query_hash,
            query_text=query_text[:200],
            execution_time_ms=execution_time,
            result_count=len(result_data),
            cache_hit=False,
            timestamp=datetime.utcnow(),
            connection_pool_size=self.pool_config['pool_size']
        )
        self.query_metrics.append(metrics)
        
        # Keep only recent metrics
        if len(self.query_metrics) > 1000:
            self.query_metrics = self.query_metrics[-500:]
        
        # Cache result
        if cache_ttl is None:
            cache_ttl = self.query_cache.get_ttl_for_tables(tables or [])
        
        await cache_manager.set(
            cache_key,
            result_data,
            ttl=cache_ttl,
            cache_type="database"
        )
        
        logger.debug(f"Query executed in {execution_time:.2f}ms: {query_hash[:8]}...")
        
        return result_data
    
    async def execute_batch_operation(
        self,
        operations: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Any]:
        """Execute batch operations efficiently"""
        results = []
        
        async with self.get_session('write') as session:
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                batch_results = []
                
                for operation in batch:
                    op_type = operation.get('type')
                    query = operation.get('query')
                    params = operation.get('params', {})
                    
                    if op_type == 'insert':
                        result = await session.execute(query, params)
                        batch_results.append(result.lastrowid)
                    elif op_type == 'update':
                        result = await session.execute(query, params)
                        batch_results.append(result.rowcount)
                    elif op_type == 'delete':
                        result = await session.execute(query, params)
                        batch_results.append(result.rowcount)
                    else:
                        result = await session.execute(query, params)
                        rows = result.fetchall()
                        batch_results.append([dict(row) for row in rows])
                
                # Flush batch
                await session.flush()
                results.extend(batch_results)
                
                logger.debug(f"Processed batch {i//batch_size + 1}: {len(batch)} operations")
        
        return results
    
    async def optimize_table_indexes(self, table_name: str) -> List[str]:
        """Suggest index optimizations for a table"""
        suggestions = []
        
        # Get table statistics
        async with self.get_session('read') as session:
            # Check for missing indexes on foreign keys
            fk_query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = :table_name 
                AND tc.constraint_type = 'FOREIGN KEY'
            """
            
            result = await session.execute(text(fk_query), {'table_name': table_name})
            fk_columns = [row.column_name for row in result.fetchall()]
            
            # Check existing indexes
            index_query = """
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = :table_name
            """
            
            result = await session.execute(text(index_query), {'table_name': table_name})
            existing_indexes = [row.indexdef for row in result.fetchall()]
            
            # Suggest indexes for foreign key columns without indexes
            for column in fk_columns:
                if not any(column in idx for idx in existing_indexes):
                    suggestions.append(f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column})")
        
        return suggestions
    
    async def get_connection_pool_metrics(self) -> Dict[str, ConnectionPoolMetrics]:
        """Get connection pool metrics for all engines"""
        metrics = {}
        
        for engine_name, engine in self.engines.items():
            pool = engine.pool
            
            metrics[engine_name] = ConnectionPoolMetrics(
                pool_size=pool.size(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
                checked_in=pool.checkedin(),
                total_connections=pool.size() + pool.overflow(),
                avg_checkout_time_ms=0.0  # Would need more detailed tracking
            )
        
        return metrics
    
    async def get_query_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive query performance report"""
        if not self.query_metrics:
            return {'status': 'no_data'}
        
        # Calculate statistics
        execution_times = [m.execution_time_ms for m in self.query_metrics]
        result_counts = [m.result_count for m in self.query_metrics]
        
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        slow_query_count = len([t for t in execution_times if t > self.slow_query_threshold])
        
        # Top slow queries
        slow_queries = sorted(
            [m for m in self.query_metrics if m.execution_time_ms > self.slow_query_threshold],
            key=lambda x: x.execution_time_ms,
            reverse=True
        )[:10]
        
        # Query frequency analysis
        query_frequency = {}
        for metric in self.query_metrics:
            query_frequency[metric.query_hash] = query_frequency.get(metric.query_hash, 0) + 1
        
        most_frequent = sorted(query_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Connection pool metrics
        pool_metrics = await self.get_connection_pool_metrics()
        
        return {
            'summary': {
                'total_queries': len(self.query_metrics),
                'avg_execution_time_ms': avg_execution_time,
                'max_execution_time_ms': max_execution_time,
                'slow_query_count': slow_query_count,
                'slow_query_threshold_ms': self.slow_query_threshold
            },
            'slow_queries': [
                {
                    'query_hash': q.query_hash[:8],
                    'execution_time_ms': q.execution_time_ms,
                    'result_count': q.result_count,
                    'query_preview': q.query_text,
                    'timestamp': q.timestamp.isoformat()
                }
                for q in slow_queries
            ],
            'most_frequent_queries': [
                {
                    'query_hash': hash_val[:8],
                    'frequency': freq
                }
                for hash_val, freq in most_frequent
            ],
            'connection_pools': {
                name: {
                    'pool_size': metrics.pool_size,
                    'checked_out': metrics.checked_out,
                    'overflow': metrics.overflow,
                    'utilization_percent': (metrics.checked_out / metrics.pool_size) * 100
                }
                for name, metrics in pool_metrics.items()
            }
        }
    
    async def cleanup(self):
        """Cleanup database connections"""
        for engine in self.engines.values():
            await engine.dispose()
        
        logger.info("Database connections cleaned up")


# Global database optimizer instance
db_optimizer = OptimizedDatabase()


# Decorators for query optimization
def cached_query(ttl: int = None, tables: List[str] = None):
    """Decorator for automatic query caching"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function to get query and params
            query, params = await func(*args, **kwargs)
            
            # Execute with caching
            return await db_optimizer.execute_cached_query(
                query=query,
                params=params,
                cache_ttl=ttl,
                tables=tables
            )
        return wrapper
    return decorator


def read_replica(func):
    """Decorator to force read replica usage"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Inject read operation preference
        kwargs['operation'] = 'read'
        return await func(*args, **kwargs)
    return wrapper


def write_primary(func):
    """Decorator to force primary database usage"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Inject write operation preference
        kwargs['operation'] = 'write'
        return await func(*args, **kwargs)
    return wrapper