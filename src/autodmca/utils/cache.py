"""
Cache management for AutoDMCA system.

Provides Redis-based caching with fallback to in-memory cache
for improved performance and reduced external API calls.
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Union
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Unified cache manager supporting both Redis and in-memory caching.
    """
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL (optional)
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Initialize Redis connection if available and URL provided
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.redis_client = None
        
        if not self.redis_client:
            logger.info("Using in-memory cache (no Redis available)")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        try:
            # Try Redis first
            if self.redis_client:
                value = await self.redis_client.get(key)
                if value is not None:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            
            # Fallback to memory cache
            cache_entry = self.memory_cache.get(key)
            if cache_entry:
                # Check expiration
                if cache_entry['expires_at'] > datetime.utcnow():
                    return cache_entry['value']
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (seconds or timedelta)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert ttl to seconds
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            elif isinstance(ttl, int):
                ttl_seconds = ttl
            else:
                ttl_seconds = self.default_ttl
            
            # Try Redis first
            if self.redis_client:
                try:
                    serialized_value = json.dumps(value) if not isinstance(value, str) else value
                    await self.redis_client.setex(key, ttl_seconds, serialized_value)
                    return True
                except Exception as e:
                    logger.warning(f"Redis set failed for key '{key}': {e}")
            
            # Fallback to memory cache
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            self.memory_cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            
            # Clean up expired entries periodically
            await self._cleanup_memory_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            deleted = False
            
            # Delete from Redis
            if self.redis_client:
                result = await self.redis_client.delete(key)
                deleted = deleted or bool(result)
            
            # Delete from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                deleted = True
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        value = await self.get(key)
        return value is not None
    
    async def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            success = True
            
            # Clear Redis
            if self.redis_client:
                await self.redis_client.flushdb()
            
            # Clear memory cache
            self.memory_cache.clear()
            
            return success
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'backend': 'redis' if self.redis_client else 'memory',
            'memory_cache_size': len(self.memory_cache),
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info('memory')
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'Unknown'),
                    'redis_connected': True,
                })
            except Exception as e:
                stats['redis_connected'] = False
                stats['redis_error'] = str(e)
        
        return stats
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a consistent cache key from parameters.
        
        Args:
            prefix: Key prefix
            *args: Positional arguments for key
            **kwargs: Keyword arguments for key
            
        Returns:
            Generated cache key
        """
        # Create deterministic key from arguments
        key_parts = [str(arg) for arg in args]
        
        # Sort kwargs for consistency
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        key_string = ":".join([prefix] + key_parts)
        
        # Hash long keys to keep them manageable
        if len(key_string) > 200:
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            return f"{prefix}:hash:{key_hash}"
        
        return key_string
    
    async def _cleanup_memory_cache(self) -> None:
        """Clean up expired entries from memory cache."""
        try:
            current_time = datetime.utcnow()
            expired_keys = []
            
            for key, entry in self.memory_cache.items():
                if entry['expires_at'] <= current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            logger.error(f"Memory cache cleanup error: {e}")
    
    async def close(self) -> None:
        """Close cache connections."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


class CacheDecorator:
    """
    Decorator for caching function results.
    """
    
    def __init__(
        self, 
        cache_manager: CacheManager, 
        ttl: Optional[Union[int, timedelta]] = None,
        key_prefix: str = "func"
    ):
        """
        Initialize cache decorator.
        
        Args:
            cache_manager: Cache manager instance
            ttl: Time-to-live for cached results
            key_prefix: Prefix for cache keys
        """
        self.cache_manager = cache_manager
        self.ttl = ttl
        self.key_prefix = key_prefix
    
    def __call__(self, func):
        """Decorate function with caching."""
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self.cache_manager.generate_key(
                f"{self.key_prefix}:{func.__name__}",
                *args,
                **kwargs
            )
            
            # Try to get cached result
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await self.cache_manager.set(cache_key, result, self.ttl)
            
            return result
        
        return wrapper


# Global cache instance for convenience
_global_cache: Optional[CacheManager] = None

def get_cache() -> CacheManager:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache

def cache_result(ttl: Optional[Union[int, timedelta]] = None, key_prefix: str = "func"):
    """
    Decorator for caching function results using global cache.
    
    Args:
        ttl: Time-to-live for cached results
        key_prefix: Prefix for cache keys
    """
    return CacheDecorator(get_cache(), ttl, key_prefix)