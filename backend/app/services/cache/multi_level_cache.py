"""
Multi-Level Caching System
Implements L1 (in-memory) -> L2 (Redis) -> L3 (Database) caching strategy
"""
import asyncio
import json
import pickle
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import logging

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)


class CacheLevel(str, Enum):
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    ttl: int
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage_mb: float = 0.0
    redis_connections: int = 0
    avg_response_time_ms: float = 0.0


class LRUCache:
    """High-performance in-memory LRU cache"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self.total_size_bytes = 0
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with LRU update"""
        if key in self.cache:
            entry = self.cache[key]
            
            # Check TTL
            if entry.ttl > 0:
                age = (datetime.utcnow() - entry.created_at).total_seconds()
                if age > entry.ttl:
                    self._remove(key)
                    self.stats.misses += 1
                    return None
            
            # Update access info
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            
            self.stats.hits += 1
            return entry.value
        
        self.stats.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = 0) -> bool:
        """Set item in cache with automatic eviction"""
        try:
            # Estimate size
            size = self._estimate_size(value)
            
            # Check if we need to evict
            while (len(self.cache) >= self.max_size or 
                   self.total_size_bytes + size > self.max_memory_bytes):
                if not self._evict_lru():
                    break
            
            # Remove existing entry if present
            if key in self.cache:
                self._remove(key)
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                created_at=datetime.utcnow(),
                size_bytes=size
            )
            
            self.cache[key] = entry
            self.access_order.append(key)
            self.total_size_bytes += size
            
            return True
            
        except Exception as e:
            logger.error(f"LRU cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        if key in self.cache:
            self._remove(key)
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
        self.total_size_bytes = 0
        self.stats = CacheStats()
    
    def _remove(self, key: str):
        """Remove entry and update stats"""
        if key in self.cache:
            entry = self.cache[key]
            self.total_size_bytes -= entry.size_bytes
            del self.cache[key]
            self.access_order.remove(key)
    
    def _evict_lru(self) -> bool:
        """Evict least recently used item"""
        if not self.access_order:
            return False
        
        lru_key = self.access_order[0]
        self._remove(lru_key)
        self.stats.evictions += 1
        return True
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            return len(pickle.dumps(value))
        except:
            return 1024  # Default estimate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = 0.0
        total_requests = self.stats.hits + self.stats.misses
        if total_requests > 0:
            hit_rate = self.stats.hits / total_requests
        
        return {
            'hit_rate': hit_rate,
            'entries': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_mb': self.total_size_bytes / 1024 / 1024,
            'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
            'evictions': self.stats.evictions,
            'total_requests': total_requests
        }


class MultiLevelCache:
    """
    Multi-level cache system with automatic failover and population
    
    Cache Hierarchy:
    L1: In-memory LRU cache (fastest, smallest)
    L2: Redis cache (fast, medium size)
    L3: Database cache (slower, largest)
    """
    
    def __init__(self):
        # L1 Cache - In-memory
        self.l1_cache = LRUCache(
            max_size=getattr(settings, 'L1_CACHE_SIZE', 1000),
            max_memory_mb=getattr(settings, 'L1_CACHE_MEMORY_MB', 100)
        )
        
        # L2 Cache - Redis
        self.redis_client: Optional[redis.Redis] = None
        self.redis_pool_size = getattr(settings, 'REDIS_POOL_SIZE', 20)
        
        # Cache configuration
        self.default_ttl = getattr(settings, 'DEFAULT_CACHE_TTL', 3600)
        self.redis_ttl = getattr(settings, 'REDIS_CACHE_TTL', 7200)
        self.enable_l3_cache = getattr(settings, 'ENABLE_L3_CACHE', True)
        
        # Performance tracking
        self.global_stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0,
            'write_operations': 0,
            'average_response_time_ms': 0.0
        }
        
        # Key prefixes for organization
        self.key_prefixes = {
            'face_encoding': 'face:',
            'image_feature': 'img:',
            'hash_match': 'hash:',
            'api_response': 'api:',
            'scan_result': 'scan:',
            'profile_data': 'profile:'
        }
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=self.redis_pool_size,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Multi-level cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None
    
    async def get(
        self, 
        key: str, 
        cache_type: str = "default",
        fallback_factory: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Get value from cache with multi-level fallback
        
        Args:
            key: Cache key
            cache_type: Type of cache for key prefixing
            fallback_factory: Async function to generate value if not in cache
        """
        start_time = time.time()
        full_key = self._build_key(key, cache_type)
        
        try:
            # L1 Cache (in-memory)
            value = self.l1_cache.get(full_key)
            if value is not None:
                self.global_stats['l1_hits'] += 1
                self._update_response_time(start_time)
                return value
            
            self.global_stats['l1_misses'] += 1
            
            # L2 Cache (Redis)
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.get(full_key)
                    if cached_data:
                        value = pickle.loads(cached_data)
                        
                        # Populate L1 cache
                        self.l1_cache.set(full_key, value, ttl=self.default_ttl)
                        
                        self.global_stats['l2_hits'] += 1
                        self._update_response_time(start_time)
                        return value
                except Exception as e:
                    logger.warning(f"Redis cache error: {e}")
            
            self.global_stats['l2_misses'] += 1
            
            # L3 Cache (Database) or Fallback Factory
            if fallback_factory:
                value = await fallback_factory()
                if value is not None:
                    # Populate all cache levels
                    await self.set(key, value, cache_type=cache_type)
                    self.global_stats['l3_hits'] += 1
                    self._update_response_time(start_time)
                    return value
            
            self.global_stats['l3_misses'] += 1
            self._update_response_time(start_time)
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {full_key}: {e}")
            self._update_response_time(start_time)
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        cache_type: str = "default",
        levels: List[CacheLevel] = None
    ) -> bool:
        """
        Set value in cache across multiple levels
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            cache_type: Type of cache for key prefixing
            levels: Specific cache levels to write to
        """
        if ttl is None:
            ttl = self.default_ttl
        
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]
        
        full_key = self._build_key(key, cache_type)
        success = True
        
        try:
            # L1 Cache
            if CacheLevel.L1_MEMORY in levels:
                self.l1_cache.set(full_key, value, ttl=ttl)
            
            # L2 Cache (Redis)
            if CacheLevel.L2_REDIS in levels and self.redis_client:
                try:
                    redis_ttl = min(ttl, self.redis_ttl) if ttl > 0 else self.redis_ttl
                    await self.redis_client.setex(
                        full_key, 
                        redis_ttl, 
                        pickle.dumps(value)
                    )
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
                    success = False
            
            self.global_stats['write_operations'] += 1
            return success
            
        except Exception as e:
            logger.error(f"Cache set error for key {full_key}: {e}")
            return False
    
    async def delete(self, key: str, cache_type: str = "default") -> bool:
        """Delete key from all cache levels"""
        full_key = self._build_key(key, cache_type)
        success = True
        
        try:
            # L1 Cache
            self.l1_cache.delete(full_key)
            
            # L2 Cache
            if self.redis_client:
                try:
                    await self.redis_client.delete(full_key)
                except Exception as e:
                    logger.warning(f"Redis delete error: {e}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Cache delete error for key {full_key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str, cache_type: str = "default"):
        """Invalidate all keys matching pattern"""
        full_pattern = self._build_key(pattern, cache_type)
        
        try:
            # L1 Cache - manual iteration
            keys_to_delete = [k for k in self.l1_cache.cache.keys() if self._matches_pattern(k, full_pattern)]
            for key in keys_to_delete:
                self.l1_cache.delete(key)
            
            # L2 Cache - Redis pattern deletion
            if self.redis_client:
                try:
                    async for key in self.redis_client.scan_iter(match=full_pattern):
                        await self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis pattern delete error: {e}")
            
        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
    
    def _build_key(self, key: str, cache_type: str) -> str:
        """Build full cache key with prefix"""
        prefix = self.key_prefixes.get(cache_type, "default:")
        return f"{prefix}{key}"
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for cache keys"""
        # Convert glob-style pattern to simple matching
        if '*' in pattern:
            parts = pattern.split('*')
            if len(parts) == 2:
                return key.startswith(parts[0]) and key.endswith(parts[1])
        return key == pattern
    
    def _update_response_time(self, start_time: float):
        """Update average response time"""
        response_time = (time.time() - start_time) * 1000
        current_avg = self.global_stats['average_response_time_ms']
        self.global_stats['average_response_time_ms'] = (current_avg + response_time) / 2
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        l1_stats = self.l1_cache.get_stats()
        
        # Calculate global hit rates
        total_l1 = self.global_stats['l1_hits'] + self.global_stats['l1_misses']
        total_l2 = self.global_stats['l2_hits'] + self.global_stats['l2_misses']
        total_l3 = self.global_stats['l3_hits'] + self.global_stats['l3_misses']
        
        l1_hit_rate = self.global_stats['l1_hits'] / total_l1 if total_l1 > 0 else 0
        l2_hit_rate = self.global_stats['l2_hits'] / total_l2 if total_l2 > 0 else 0
        l3_hit_rate = self.global_stats['l3_hits'] / total_l3 if total_l3 > 0 else 0
        
        # Overall hit rate (weighted by cache level)
        total_hits = self.global_stats['l1_hits'] + self.global_stats['l2_hits'] + self.global_stats['l3_hits']
        total_requests = total_l1 + total_l2 + total_l3
        overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0
        
        stats = {
            'overall': {
                'hit_rate': overall_hit_rate,
                'total_requests': total_requests,
                'average_response_time_ms': self.global_stats['average_response_time_ms'],
                'write_operations': self.global_stats['write_operations']
            },
            'l1_memory': {
                'hit_rate': l1_hit_rate,
                'hits': self.global_stats['l1_hits'],
                'misses': self.global_stats['l1_misses'],
                **l1_stats
            },
            'l2_redis': {
                'hit_rate': l2_hit_rate,
                'hits': self.global_stats['l2_hits'],
                'misses': self.global_stats['l2_misses'],
                'connected': self.redis_client is not None
            },
            'l3_database': {
                'hit_rate': l3_hit_rate,
                'hits': self.global_stats['l3_hits'],
                'misses': self.global_stats['l3_misses'],
                'enabled': self.enable_l3_cache
            }
        }
        
        # Add Redis-specific stats
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info('memory')
                stats['l2_redis'].update({
                    'memory_usage_mb': redis_info.get('used_memory', 0) / 1024 / 1024,
                    'connections': redis_info.get('connected_clients', 0)
                })
            except Exception:
                pass
        
        return stats
    
    async def warm_cache(self, warm_data: Dict[str, Any]):
        """Pre-populate cache with frequently accessed data"""
        logger.info("Starting cache warm-up...")
        
        for cache_type, items in warm_data.items():
            for key, value in items.items():
                await self.set(
                    key, 
                    value, 
                    cache_type=cache_type,
                    ttl=self.default_ttl * 2  # Longer TTL for warm data
                )
        
        logger.info(f"Cache warm-up completed: {len(warm_data)} categories")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()


# Global cache instance
cache_manager = MultiLevelCache()


# Decorator for automatic caching
def cached(
    ttl: int = 3600,
    cache_type: str = "default",
    key_generator: Optional[Callable] = None
):
    """
    Decorator for automatic function result caching
    
    Args:
        ttl: Time to live in seconds
        cache_type: Cache type for key prefixing
        key_generator: Custom function to generate cache key
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            result = await cache_manager.get(cache_key, cache_type=cache_type)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl=ttl, cache_type=cache_type)
            
            return result
        
        return wrapper
    return decorator


# Specialized cache functions for common use cases
async def cache_face_encoding(profile_id: int, image_hash: str, encoding: Any, ttl: int = 7200):
    """Cache face encoding for a profile"""
    key = f"{profile_id}:{image_hash}"
    await cache_manager.set(key, encoding, ttl=ttl, cache_type="face_encoding")


async def get_cached_face_encoding(profile_id: int, image_hash: str) -> Optional[Any]:
    """Get cached face encoding"""
    key = f"{profile_id}:{image_hash}"
    return await cache_manager.get(key, cache_type="face_encoding")


async def cache_image_features(image_hash: str, features: Any, ttl: int = 7200):
    """Cache image features"""
    await cache_manager.set(image_hash, features, ttl=ttl, cache_type="image_feature")


async def get_cached_image_features(image_hash: str) -> Optional[Any]:
    """Get cached image features"""
    return await cache_manager.get(image_hash, cache_type="image_feature")


async def cache_api_response(endpoint: str, params_hash: str, response: Any, ttl: int = 300):
    """Cache API response"""
    key = f"{endpoint}:{params_hash}"
    await cache_manager.set(key, response, ttl=ttl, cache_type="api_response")


async def get_cached_api_response(endpoint: str, params_hash: str) -> Optional[Any]:
    """Get cached API response"""
    key = f"{endpoint}:{params_hash}"
    return await cache_manager.get(key, cache_type="api_response")