"""
Rate limiting utilities for AutoDMCA system.

Provides rate limiting for external API calls to comply with service
limitations and avoid being blocked.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    max_calls: int  # Maximum calls allowed
    time_window: int  # Time window in seconds
    burst_limit: Optional[int] = None  # Burst limit (optional)
    backoff_factor: float = 1.5  # Exponential backoff factor


class RateLimiter:
    """
    Token bucket rate limiter with burst support and backoff.
    """
    
    def __init__(
        self,
        max_calls: int = 60,
        time_window: int = 60,
        burst_limit: Optional[int] = None,
        backoff_factor: float = 1.5
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds
            burst_limit: Optional burst limit for short periods
            backoff_factor: Exponential backoff factor on rate limit hits
        """
        self.config = RateLimitConfig(max_calls, time_window, burst_limit, backoff_factor)
        self.call_times: deque = deque()
        self.burst_times: deque = deque()
        self.backoff_until: float = 0
        self.consecutive_limits: int = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire rate limit token. Blocks until token is available.
        """
        async with self._lock:
            await self._wait_if_needed()
            self._record_call()
    
    async def try_acquire(self) -> bool:
        """
        Try to acquire rate limit token without blocking.
        
        Returns:
            True if token acquired, False if rate limited
        """
        async with self._lock:
            if self._is_rate_limited():
                return False
            
            self._record_call()
            return True
    
    async def _wait_if_needed(self) -> None:
        """Wait if rate limited."""
        while self._is_rate_limited():
            wait_time = self._calculate_wait_time()
            if wait_time > 0:
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    def _is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        current_time = time.time()
        
        # Check backoff period
        if current_time < self.backoff_until:
            return True
        
        # Clean old call times
        self._cleanup_old_calls(current_time)
        
        # Check regular rate limit
        if len(self.call_times) >= self.config.max_calls:
            return True
        
        # Check burst limit if configured
        if self.config.burst_limit is not None:
            # Clean old burst times (last 10 seconds)
            while self.burst_times and current_time - self.burst_times[0] > 10:
                self.burst_times.popleft()
            
            if len(self.burst_times) >= self.config.burst_limit:
                return True
        
        return False
    
    def _calculate_wait_time(self) -> float:
        """Calculate how long to wait before next attempt."""
        current_time = time.time()
        
        # If in backoff period
        if current_time < self.backoff_until:
            return self.backoff_until - current_time
        
        # Calculate time until oldest call expires
        if self.call_times:
            oldest_call = self.call_times[0]
            time_to_wait = self.config.time_window - (current_time - oldest_call)
            return max(0, time_to_wait)
        
        return 0
    
    def _record_call(self) -> None:
        """Record a successful call."""
        current_time = time.time()
        
        self.call_times.append(current_time)
        
        if self.config.burst_limit is not None:
            self.burst_times.append(current_time)
        
        # Reset consecutive limits on successful call
        self.consecutive_limits = 0
    
    def _cleanup_old_calls(self, current_time: float) -> None:
        """Remove calls outside the time window."""
        window_start = current_time - self.config.time_window
        
        while self.call_times and self.call_times[0] < window_start:
            self.call_times.popleft()
    
    def handle_rate_limit_error(self, retry_after: Optional[int] = None) -> None:
        """
        Handle rate limit error from external service.
        
        Args:
            retry_after: Retry-After header value in seconds
        """
        self.consecutive_limits += 1
        
        # Calculate backoff time
        if retry_after:
            backoff_time = retry_after
        else:
            # Exponential backoff
            backoff_time = min(
                300,  # Max 5 minutes
                self.config.time_window * (self.config.backoff_factor ** self.consecutive_limits)
            )
        
        self.backoff_until = time.time() + backoff_time
        logger.warning(f"Rate limited, backing off for {backoff_time:.2f}s")
    
    def get_stats(self) -> Dict[str, float]:
        """Get rate limiter statistics."""
        current_time = time.time()
        self._cleanup_old_calls(current_time)
        
        return {
            'calls_in_window': len(self.call_times),
            'max_calls': self.config.max_calls,
            'time_window': self.config.time_window,
            'backoff_until': self.backoff_until,
            'consecutive_limits': self.consecutive_limits,
            'utilization': len(self.call_times) / self.config.max_calls,
        }
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        with asyncio.Lock():
            self.call_times.clear()
            self.burst_times.clear()
            self.backoff_until = 0
            self.consecutive_limits = 0


class MultiServiceRateLimiter:
    """
    Rate limiter that manages multiple services with different limits.
    """
    
    def __init__(self, service_configs: Dict[str, RateLimitConfig]):
        """
        Initialize multi-service rate limiter.
        
        Args:
            service_configs: Dict mapping service names to rate limit configs
        """
        self.limiters: Dict[str, RateLimiter] = {}
        
        for service, config in service_configs.items():
            self.limiters[service] = RateLimiter(
                config.max_calls,
                config.time_window,
                config.burst_limit,
                config.backoff_factor
            )
    
    async def acquire(self, service: str) -> None:
        """
        Acquire token for specific service.
        
        Args:
            service: Service name
        """
        if service not in self.limiters:
            raise ValueError(f"Unknown service: {service}")
        
        await self.limiters[service].acquire()
    
    async def try_acquire(self, service: str) -> bool:
        """
        Try to acquire token for specific service.
        
        Args:
            service: Service name
            
        Returns:
            True if token acquired, False if rate limited
        """
        if service not in self.limiters:
            return False
        
        return await self.limiters[service].try_acquire()
    
    def handle_rate_limit_error(self, service: str, retry_after: Optional[int] = None) -> None:
        """
        Handle rate limit error for specific service.
        
        Args:
            service: Service name
            retry_after: Retry-After header value
        """
        if service in self.limiters:
            self.limiters[service].handle_rate_limit_error(retry_after)
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all services."""
        return {
            service: limiter.get_stats()
            for service, limiter in self.limiters.items()
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts to service responses and adjusts limits dynamically.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize adaptive rate limiter."""
        super().__init__(*args, **kwargs)
        self.success_count = 0
        self.error_count = 0
        self.adaptation_window = 100  # Adapt every N requests
        self.original_max_calls = self.config.max_calls
    
    def record_success(self) -> None:
        """Record a successful API call."""
        self.success_count += 1
        self._adapt_if_needed()
    
    def record_error(self, is_rate_limit: bool = False) -> None:
        """
        Record an API error.
        
        Args:
            is_rate_limit: Whether the error was due to rate limiting
        """
        self.error_count += 1
        
        if is_rate_limit:
            self.handle_rate_limit_error()
        
        self._adapt_if_needed()
    
    def _adapt_if_needed(self) -> None:
        """Adapt rate limits based on success/error rates."""
        total_requests = self.success_count + self.error_count
        
        if total_requests % self.adaptation_window == 0:
            success_rate = self.success_count / total_requests
            
            # Increase limit if high success rate
            if success_rate > 0.95 and self.consecutive_limits == 0:
                new_limit = min(
                    int(self.config.max_calls * 1.1),
                    self.original_max_calls * 2
                )
                if new_limit > self.config.max_calls:
                    self.config.max_calls = new_limit
                    logger.info(f"Increased rate limit to {new_limit} due to high success rate")
            
            # Decrease limit if low success rate
            elif success_rate < 0.8:
                new_limit = max(
                    int(self.config.max_calls * 0.8),
                    self.original_max_calls // 4
                )
                if new_limit < self.config.max_calls:
                    self.config.max_calls = new_limit
                    logger.info(f"Decreased rate limit to {new_limit} due to low success rate")
            
            # Reset counters
            self.success_count = 0
            self.error_count = 0