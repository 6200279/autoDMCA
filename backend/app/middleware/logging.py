import time
import json
import uuid
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
import logging

from app.core.config import settings


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        logger_name: str = "app.requests",
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: set = None,
        max_body_size: int = 1024 * 10  # 10KB
    ):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        
        # Headers to exclude from logging for security
        self.sensitive_headers = sensitive_headers or {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "set-cookie"
        }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return str(uuid.uuid4())
    
    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request."""
        # Get real IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return {
            "ip": client_ip,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "host": request.headers.get("Host", "")
        }
    
    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter out sensitive headers from logging."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() not in self.sensitive_headers:
                filtered[key] = value
            else:
                filtered[key] = "[REDACTED]"
        return filtered
    
    def _get_user_context(self, request: Request) -> Dict[str, Any]:
        """Extract user context from request."""
        user_context = {"user_id": None, "authenticated": False}
        
        # Try to extract user info from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import verify_token
                token = auth_header[7:]
                payload = verify_token(token)
                if payload:
                    user_context["user_id"] = payload.get("sub")
                    user_context["authenticated"] = True
                    user_context["token_type"] = payload.get("type", "access")
            except Exception:
                pass
        
        return user_context
    
    async def _read_body(self, request: Request) -> str:
        """Safely read request body for logging."""
        try:
            body = await request.body()
            if len(body) > self.max_body_size:
                return f"[BODY TOO LARGE: {len(body)} bytes]"
            
            # Try to decode as JSON for pretty printing
            try:
                body_json = json.loads(body)
                # Remove sensitive fields
                sensitive_fields = ["password", "token", "secret", "key", "credit_card"]
                for field in sensitive_fields:
                    if field in body_json:
                        body_json[field] = "[REDACTED]"
                return json.dumps(body_json, indent=2)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return as string if not JSON
                try:
                    return body.decode('utf-8')[:self.max_body_size]
                except UnicodeDecodeError:
                    return f"[BINARY DATA: {len(body)} bytes]"
        except Exception:
            return "[ERROR READING BODY]"
    
    def _log_request(self, request: Request, request_id: str, start_time: float):
        """Log incoming request."""
        if not self.log_requests:
            return
        
        client_info = self._get_client_info(request)
        user_context = self._get_user_context(request)
        
        log_data = {
            "event": "request",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": self._filter_headers(dict(request.headers)),
            "client": client_info,
            "user": user_context,
            "start_time": start_time
        }
        
        self.logger.info(f"Request: {request.method} {request.url.path}", extra=log_data)
    
    async def _log_request_body(self, request: Request, request_id: str):
        """Log request body if enabled."""
        if not self.log_request_body:
            return
        
        body = await self._read_body(request)
        if body:
            log_data = {
                "event": "request_body",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "body": body
            }
            self.logger.debug("Request body", extra=log_data)
    
    def _log_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str, 
        duration: float
    ):
        """Log outgoing response."""
        if not self.log_responses:
            return
        
        log_data = {
            "event": "response",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "response_headers": self._filter_headers(dict(response.headers)),
            "duration_ms": round(duration * 1000, 2)
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        self.logger.log(
            log_level,
            f"Response: {response.status_code} in {duration:.3f}s",
            extra=log_data
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with logging."""
        start_time = time.time()
        request_id = self._generate_request_id()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log incoming request
        self._log_request(request, request_id, start_time)
        
        # Log request body if enabled
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            await self._log_request_body(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            duration = time.time() - start_time
            log_data = {
                "event": "exception",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "path": request.url.path,
                "exception": str(exc),
                "exception_type": type(exc).__name__,
                "duration_ms": round(duration * 1000, 2)
            }
            self.logger.error(f"Request failed: {exc}", extra=log_data)
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add request ID and timing to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        # Log response
        self._log_response(request, response, request_id, duration)
        
        return response


# Configure structured logging
def setup_logging():
    """Setup structured logging configuration."""
    import logging.config
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "app": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "app.requests": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False
            },
            "app.security": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    }
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    logging.config.dictConfig(logging_config)