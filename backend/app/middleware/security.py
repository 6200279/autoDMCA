import time
import hashlib
import secrets
from typing import Optional, Dict, Set
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime, timedelta
import user_agents
from ipaddress import ip_address, ip_network

from app.core.config import settings


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware with various protection features."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_csrf_protection: bool = True,
        enable_request_logging: bool = True,
        enable_ip_blocking: bool = True,
        max_request_size: int = 50 * 1024 * 1024,  # 50MB
        trusted_proxies: Set[str] = None
    ):
        super().__init__(app)
        self.enable_csrf_protection = enable_csrf_protection
        self.enable_request_logging = enable_request_logging
        self.enable_ip_blocking = enable_ip_blocking
        self.max_request_size = max_request_size
        self.trusted_proxies = trusted_proxies or set()
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), payment=(), usb=()"
            )
        }
        
        # Blocked IPs and suspicious activity tracking
        self.blocked_ips: Set[str] = set()
        self.suspicious_activity: Dict[str, Dict] = {}
        self.failed_auth_attempts: Dict[str, int] = {}
        
        # Common attack patterns
        self.malicious_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"on\w+\s*=",
            r"expression\s*\(",
            r"url\s*\(",
            r"import\s+",
            r"eval\s*\(",
            r"exec\s*\(",
            r"\.\./",
            r"\\x[0-9a-f]{2}",
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into"
        ]
    
    def _get_real_ip(self, request: Request) -> str:
        """Get real client IP address."""
        # Check for forwarded headers from trusted proxies
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            for ip in ips:
                try:
                    # Return first non-private IP
                    ip_obj = ip_address(ip)
                    if not ip_obj.is_private:
                        return ip
                except ValueError:
                    continue
            # If all IPs are private, return the first one
            return ips[0] if ips else request.client.host
        
        # Check other forwarded headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client IP
        return request.client.host if request.client else "unknown"
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        return ip in self.blocked_ips
    
    def _block_ip(self, ip: str, reason: str = "suspicious activity"):
        """Block an IP address."""
        self.blocked_ips.add(ip)
        print(f"Blocked IP {ip}: {reason}")
    
    def _check_malicious_content(self, content: str) -> bool:
        """Check if content contains malicious patterns."""
        import re
        content_lower = content.lower()
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(32)
    
    def _validate_csrf_token(self, request: Request) -> bool:
        """Validate CSRF token."""
        # Skip CSRF validation for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        
        # Skip for API endpoints with proper authentication
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return True
        
        # Check CSRF token in headers or form data
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            # For form submissions, token might be in form data
            # This would require reading the body, which is complex in middleware
            # For now, we'll skip CSRF for JSON API requests
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return True
        
        return bool(csrf_token)
    
    def _track_suspicious_activity(self, ip: str, activity_type: str):
        """Track suspicious activity for an IP."""
        current_time = time.time()
        
        if ip not in self.suspicious_activity:
            self.suspicious_activity[ip] = {"count": 0, "first_seen": current_time}
        
        self.suspicious_activity[ip]["count"] += 1
        self.suspicious_activity[ip]["last_seen"] = current_time
        self.suspicious_activity[ip]["activities"] = self.suspicious_activity[ip].get("activities", [])
        self.suspicious_activity[ip]["activities"].append({
            "type": activity_type,
            "timestamp": current_time
        })
        
        # Block IP if too many suspicious activities
        if self.suspicious_activity[ip]["count"] >= 10:
            self._block_ip(ip, f"multiple suspicious activities: {activity_type}")
    
    def _detect_bot_traffic(self, request: Request) -> bool:
        """Detect if request is from a bot."""
        user_agent = request.headers.get("User-Agent", "")
        
        # Parse user agent
        ua = user_agents.parse(user_agent)
        
        # Check for common bot patterns
        bot_patterns = [
            "bot", "crawler", "spider", "scraper", "wget", "curl",
            "python-requests", "go-http-client", "okhttp"
        ]
        
        for pattern in bot_patterns:
            if pattern in user_agent.lower():
                return True
        
        # Check for suspicious user agent patterns
        if not user_agent or len(user_agent) < 10:
            return True
        
        # Check if it's a legitimate browser
        if ua.is_bot:
            return True
        
        return False
    
    def _validate_request_headers(self, request: Request) -> bool:
        """Validate request headers for suspicious patterns."""
        suspicious_headers = []
        
        # Check for missing required headers
        if request.method in ["POST", "PUT", "PATCH"]:
            if not request.headers.get("Content-Type"):
                suspicious_headers.append("missing_content_type")
        
        # Check for suspicious header values
        for name, value in request.headers.items():
            if self._check_malicious_content(value):
                suspicious_headers.append(f"malicious_header_{name}")
        
        return len(suspicious_headers) == 0
    
    def _log_security_event(self, ip: str, event_type: str, details: Dict):
        """Log security event."""
        if self.enable_request_logging:
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "ip": ip,
                "event_type": event_type,
                "details": details
            }
            # In production, this should go to a proper logging system
            print(f"Security Event: {event}")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security checks."""
        start_time = time.time()
        ip = self._get_real_ip(request)
        
        # Check if IP is blocked
        if self._is_ip_blocked(ip):
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_request_size:
            self._track_suspicious_activity(ip, "large_request")
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"}
            )
        
        # Validate headers
        if not self._validate_request_headers(request):
            self._track_suspicious_activity(ip, "malicious_headers")
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request headers"}
            )
        
        # Check for bot traffic (optional blocking)
        is_bot = self._detect_bot_traffic(request)
        if is_bot and request.url.path.startswith("/api/"):
            # Log but don't block API access for bots (might be legitimate automation)
            self._log_security_event(ip, "bot_detected", {
                "user_agent": request.headers.get("User-Agent"),
                "path": request.url.path
            })
        
        # CSRF protection
        if self.enable_csrf_protection and not self._validate_csrf_token(request):
            self._track_suspicious_activity(ip, "csrf_violation")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"}
            )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            self._log_security_event(ip, "request_error", {"error": str(e)})
            raise
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add CSRF token to response if needed
        if self.enable_csrf_protection and request.method == "GET":
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
        
        # Add custom headers
        response.headers["X-Request-ID"] = secrets.token_hex(16)
        response.headers["X-Response-Time"] = f"{(time.time() - start_time):.3f}s"
        
        # Log successful request
        if self.enable_request_logging:
            self._log_security_event(ip, "request_completed", {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
                "user_agent": request.headers.get("User-Agent")
            })
        
        return response