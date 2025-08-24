import time
import json
from typing import Dict, Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis
from datetime import datetime, timedelta

from app.core.config import settings


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            # Fallback to in-memory rate limiting
            self.redis_client = None
            self._memory_store = {}
    
    def _get_key(self, identifier: str, window: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{identifier}:{window}"
    
    def _memory_cleanup(self):
        """Clean up expired entries from memory store."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._memory_store.items()
            if current_time - timestamp > 3600  # Clean up entries older than 1 hour
        ]
        for key in expired_keys:
            del self._memory_store[key]
    
    def is_allowed(
        self, 
        identifier: str, 
        limit: int, 
        window_seconds: int,
        endpoint: str = "default"
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed and return rate limit info."""
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        key = self._get_key(f"{identifier}:{endpoint}", str(window_start))
        
        if self.redis_client:
            return self._redis_check(key, limit, window_seconds, current_time)
        else:
            return self._memory_check(key, limit, window_seconds, current_time)
    
    def _redis_check(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int, 
        current_time: int
    ) -> Tuple[bool, Dict]:
        """Redis-based rate limiting check."""
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = pipe.execute()
            
            current_requests = results[0]
            
            # Calculate remaining and reset time
            remaining = max(0, limit - current_requests)
            reset_time = current_time + window_seconds
            
            rate_limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "retry_after": window_seconds if current_requests > limit else 0
            }
            
            return current_requests <= limit, rate_limit_info
            
        except Exception as e:
            print(f"Redis rate limiting error: {e}")
            # Fallback: allow request if Redis fails
            return True, {"limit": limit, "remaining": limit, "reset": current_time + window_seconds}
    
    def _memory_check(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int, 
        current_time: int
    ) -> Tuple[bool, Dict]:
        """Memory-based rate limiting check (fallback)."""
        # Clean up old entries periodically
        if len(self._memory_store) > 1000:
            self._memory_cleanup()
        
        if key not in self._memory_store:
            self._memory_store[key] = (1, current_time)
            current_requests = 1
        else:
            count, timestamp = self._memory_store[key]
            
            # Check if window has expired
            if current_time - timestamp >= window_seconds:
                self._memory_store[key] = (1, current_time)
                current_requests = 1
            else:
                current_requests = count + 1
                self._memory_store[key] = (current_requests, timestamp)
        
        remaining = max(0, limit - current_requests)
        reset_time = current_time + window_seconds
        
        rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": window_seconds if current_requests > limit else 0
        }
        
        return current_requests <= limit, rate_limit_info


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        default_window: int = 3600,  # 1 hour
        rate_limits: Dict[str, Dict] = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter()
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Define rate limits for different endpoints - RELAXED FOR TESTING
        self.rate_limits = rate_limits or {
            "/api/v1/auth/login": {"limit": 50, "window": 600},  # 50 per 10 minutes - RELAXED
            "/api/v1/auth/register": {"limit": 10, "window": 3600},  # 10 per hour - RELAXED
            "/api/v1/auth/forgot-password": {"limit": 10, "window": 3600},  # 10 per hour - RELAXED
            "/api/v1/infringements": {"limit": 100, "window": 3600},  # 100 per hour
            "/api/v1/takedowns": {"limit": 50, "window": 3600},  # 50 per hour
            "/api/v1/profiles/*/scan": {"limit": 10, "window": 3600},  # 10 scans per hour
            "/api/v1/users/me/avatar": {"limit": 5, "window": 3600},  # 5 uploads per hour
        }
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from token first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import verify_token
                token = auth_header[7:]
                payload = verify_token(token)
                if payload and payload.get("sub"):
                    return f"user:{payload['sub']}"
            except Exception:
                pass
        
        # Fallback to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_endpoint_pattern(self, path: str, method: str) -> str:
        """Get endpoint pattern for rate limiting rules."""
        # Normalize path by replacing numeric IDs with wildcards
        import re
        normalized_path = re.sub(r'/\d+', '/*', path)
        return f"{method}:{normalized_path}"
    
    def _get_rate_limit_config(self, request: Request) -> Tuple[int, int]:
        """Get rate limit configuration for the request."""
        path = request.url.path
        method = request.method
        
        # Check for exact path match first
        if path in self.rate_limits:
            config = self.rate_limits[path]
            return config["limit"], config["window"]
        
        # Check for pattern match
        endpoint_pattern = self._get_endpoint_pattern(path, method)
        for pattern, config in self.rate_limits.items():
            if "*" in pattern and self._pattern_matches(pattern, endpoint_pattern):
                return config["limit"], config["window"]
        
        # Return default limits
        return self.default_limit, self.default_window
    
    def _pattern_matches(self, pattern: str, endpoint: str) -> bool:
        """Check if endpoint matches pattern with wildcards."""
        import re
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", r"[^/]+")
        return re.match(f"^{regex_pattern}$", endpoint) is not None
    
    def _create_rate_limit_response(self, rate_limit_info: Dict) -> Response:
        """Create rate limit exceeded response."""
        headers = {
            "X-RateLimit-Limit": str(rate_limit_info["limit"]),
            "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
            "X-RateLimit-Reset": str(rate_limit_info["reset"]),
            "Retry-After": str(rate_limit_info["retry_after"])
        }
        
        error_response = {
            "detail": "Rate limit exceeded",
            "rate_limit": {
                "limit": rate_limit_info["limit"],
                "remaining": rate_limit_info["remaining"],
                "reset_time": datetime.fromtimestamp(rate_limit_info["reset"]).isoformat(),
                "retry_after_seconds": rate_limit_info["retry_after"]
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_info: Dict):
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier and rate limit config
        identifier = self._get_client_identifier(request)
        limit, window = self._get_rate_limit_config(request)
        endpoint = f"{request.method}:{request.url.path}"
        
        # Check rate limit
        is_allowed, rate_limit_info = self.limiter.is_allowed(
            identifier, limit, window, endpoint
        )
        
        if not is_allowed:
            return self._create_rate_limit_response(rate_limit_info)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, rate_limit_info)
        
        return response