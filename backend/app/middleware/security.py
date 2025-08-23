import time
import hashlib
import secrets
import json
import re
from typing import Optional, Dict, Set, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime, timedelta
import user_agents
from ipaddress import ip_address, ip_network
import structlog

from app.core.config import settings
from app.core.security_config import security_monitor, InputValidator


logger = structlog.get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with comprehensive protection and monitoring."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_csrf_protection: bool = True,
        enable_request_logging: bool = True,
        enable_ip_blocking: bool = True,
        max_request_size: int = 50 * 1024 * 1024,  # 50MB
        trusted_proxies: Set[str] = None,
        enable_advanced_monitoring: bool = True
    ):
        super().__init__(app)
        self.enable_csrf_protection = enable_csrf_protection
        self.enable_request_logging = enable_request_logging
        self.enable_ip_blocking = enable_ip_blocking
        self.enable_advanced_monitoring = enable_advanced_monitoring
        self.max_request_size = max_request_size
        self.trusted_proxies = trusted_proxies or set()
        
        # Rate limiting configuration
        self.rate_limit_window = 60  # 1 minute
        self.rate_limit_requests = 100  # per window
        self.burst_limit = 20  # per 10 seconds
        
        # Request tracking
        self.request_counts: Dict[str, Dict[str, int]] = {}  # IP -> {timestamp_window: count}
        self.burst_tracking: Dict[str, List[float]] = {}  # IP -> [request_timestamps]
        
        # Enhanced security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://unpkg.com; "
                "connect-src 'self' ws: wss: http://localhost:18000 https://localhost:18000; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), payment=(), usb=(), "
                "accelerometer=(), ambient-light-sensor=(), autoplay=(), "
                "battery=(), display-capture=(), document-domain=(), "
                "encrypted-media=(), fullscreen=(), midi=(), "
                "navigation-override=(), picture-in-picture=(), "
                "publickey-credentials-get=(), sync-xhr=(), "
                "wake-lock=(), xr-spatial-tracking=()"
            ),
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }
        
        # Enhanced threat tracking
        self.blocked_ips: Set[str] = set()
        self.suspicious_activity: Dict[str, Dict] = {}
        self.failed_auth_attempts: Dict[str, int] = {}
        self.active_sessions: Dict[str, Set[str]] = {}  # IP -> set of session IDs
        
        # Comprehensive attack pattern detection
        self.malicious_patterns = [
            # XSS patterns
            r"<script[^>]*>",
            r"</script>",
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"on\w+\s*=",
            r"expression\s*\(",
            r"url\s*\(",
            r"eval\s*\(",
            r"setTimeout\s*\(",
            r"setInterval\s*\(",
            r"Function\s*\(",
            r"alert\s*\(",
            r"confirm\s*\(",
            r"prompt\s*\(",
            
            # SQL injection patterns
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+\w+\s+set",
            r"alter\s+table",
            r"create\s+table",
            r"exec\s*\(",
            r"execute\s*\(",
            r"sp_\w+",
            r"xp_\w+",
            r"--[\s\r\n]",
            r"/\*.*\*/",
            r"'\s*(or|and)\s*'?",
            r"'\s*(union|select|insert|delete|update|drop|create|alter)\s+",
            
            # Command injection patterns
            r"[;&|`$]\s*(cat|ls|dir|type|echo|wget|curl|nc|netcat|chmod|rm|del)\s+",
            r"\$\([^)]*\)",
            r"`[^`]*`",
            r"\|\s*(cat|ls|dir|type|echo|wget|curl|nc|netcat|chmod|rm|del)",
            
            # Path traversal patterns
            r"\.\./",
            r"\.\.\\\\?",
            r"%2e%2e%2f",
            r"%2e%2e/",
            r"..%2f",
            r"..%c0%af",
            r"..%c1%9c",
            
            # File inclusion patterns
            r"(file|php|data|expect|zip|compress\.zlib|compress\.bzip2|ogg)://",
            r"\\x[0-9a-f]{2}",
            r"%[0-9a-f]{2}",
            
            # Server-side includes
            r"<!--\s*#\s*(include|exec|config|echo)",
            
            # LDAP injection
            r"\(\|\(",
            r"\)\(\|",
            r"\(\&\(",
            
            # XML/XXE patterns
            r"<!ENTITY",
            r"SYSTEM\s+["'][^"']*["']",
            
            # NoSQL injection
            r"\$ne\s*:",
            r"\$gt\s*:",
            r"\$lt\s*:",
            r"\$or\s*:",
            r"\$and\s*:",
            r"\$where\s*:",
            
            # Template injection
            r"\{\{.*\}\}",
            r"\{%.*%\}",
            r"\$\{.*\}",
        ]
        
        # Sensitive endpoints that require extra protection
        self.sensitive_endpoints = {
            '/api/v1/auth/login',
            '/api/v1/auth/register', 
            '/api/v1/auth/reset-password',
            '/api/v1/users/profile',
            '/api/v1/admin',
            '/api/v1/billing',
            '/api/v1/dmca/submit'
        }
    
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
        """Enhanced IP blocking with detailed logging."""
        self.blocked_ips.add(ip)
        
        # Log the block event
        self._log_security_event(
            ip, "ip_blocked",
            {
                "reason": reason,
                "activities_count": self.suspicious_activity.get(ip, {}).get("count", 0),
                "severity_score": self.suspicious_activity.get(ip, {}).get("severity_score", 0),
                "first_seen": self.suspicious_activity.get(ip, {}).get("first_seen", time.time()),
                "block_timestamp": time.time()
            },
            "critical"
        )
        
        logger.warning(
            "IP address blocked",
            ip=ip,
            reason=reason,
            activity_count=self.suspicious_activity.get(ip, {}).get("count", 0)
        )
    
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
    
    def _track_suspicious_activity(self, ip: str, activity_type: str, request: Request = None):
        """Enhanced suspicious activity tracking with detailed logging."""
        current_time = time.time()
        
        if ip not in self.suspicious_activity:
            self.suspicious_activity[ip] = {
                "count": 0,
                "first_seen": current_time,
                "activities": [],
                "severity_score": 0
            }
        
        # Calculate severity based on activity type
        severity_scores = {
            "malicious_headers": 3,
            "malicious_content": 5,
            "sql_injection": 8,
            "xss_attempt": 6,
            "command_injection": 9,
            "path_traversal": 7,
            "csrf_violation": 4,
            "large_request": 2,
            "excessive_requests": 3,
            "bot_detection": 1,
            "failed_authentication": 4,
            "privilege_escalation": 9,
            "suspicious_file_upload": 6
        }
        
        severity = severity_scores.get(activity_type, 3)
        
        self.suspicious_activity[ip]["count"] += 1
        self.suspicious_activity[ip]["last_seen"] = current_time
        self.suspicious_activity[ip]["severity_score"] += severity
        
        # Collect request metadata
        request_metadata = {}
        if request:
            request_metadata = {
                "method": request.method,
                "path": str(request.url.path),
                "user_agent": request.headers.get("User-Agent", "unknown")[:200],
                "referer": request.headers.get("Referer", "unknown")[:200],
                "content_type": request.headers.get("Content-Type", "unknown")
            }
        
        activity_record = {
            "type": activity_type,
            "timestamp": current_time,
            "severity": severity,
            "metadata": request_metadata
        }
        
        self.suspicious_activity[ip]["activities"].append(activity_record)
        
        # Keep only last 50 activities per IP
        if len(self.suspicious_activity[ip]["activities"]) > 50:
            self.suspicious_activity[ip]["activities"] = self.suspicious_activity[ip]["activities"][-50:]
        
        # Log to security monitor
        if self.enable_advanced_monitoring:
            security_monitor.log_security_event(
                event_type=f"suspicious_activity_{activity_type}",
                severity="medium" if severity < 5 else "high",
                details={
                    "activity_type": activity_type,
                    "severity_score": severity,
                    "total_activities": self.suspicious_activity[ip]["count"],
                    "cumulative_severity": self.suspicious_activity[ip]["severity_score"],
                    **request_metadata
                },
                ip_address=ip
            )
        
        # Enhanced blocking logic based on severity score
        total_severity = self.suspicious_activity[ip]["severity_score"]
        activity_count = self.suspicious_activity[ip]["count"]
        
        # Block conditions:
        # 1. High severity score (indicates serious threats)
        # 2. Many low-severity activities
        # 3. Recent spike in activities
        should_block = (
            total_severity >= 20 or  # High cumulative severity
            activity_count >= 15 or  # Too many activities
            (severity >= 8 and activity_count >= 3)  # Critical activities
        )
        
        if should_block and ip not in self.blocked_ips:
            self._block_ip(ip, f"cumulative suspicious activities (score: {total_severity}, count: {activity_count})")
    
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
    
    def _check_rate_limiting(self, ip: str) -> tuple[bool, str]:
        """Enhanced rate limiting with burst detection."""
        current_time = time.time()
        current_minute = int(current_time // 60)
        current_10s = int(current_time // 10)
        
        # Initialize tracking for this IP
        if ip not in self.request_counts:
            self.request_counts[ip] = {}
        if ip not in self.burst_tracking:
            self.burst_tracking[ip] = []
        
        # Clean old entries
        self.request_counts[ip] = {
            k: v for k, v in self.request_counts[ip].items() 
            if k >= current_minute - 5  # Keep last 5 minutes
        }
        
        # Clean old burst tracking (keep last 60 seconds)
        self.burst_tracking[ip] = [
            ts for ts in self.burst_tracking[ip] 
            if current_time - ts < 60
        ]
        
        # Check burst limit (20 requests in 10 seconds)
        recent_requests = [ts for ts in self.burst_tracking[ip] if current_time - ts < 10]
        if len(recent_requests) >= self.burst_limit:
            return False, "burst_limit_exceeded"
        
        # Check rate limit (100 requests per minute)
        minute_count = self.request_counts[ip].get(current_minute, 0)
        if minute_count >= self.rate_limit_requests:
            return False, "rate_limit_exceeded"
        
        # Update counters
        self.request_counts[ip][current_minute] = minute_count + 1
        self.burst_tracking[ip].append(current_time)
        
        return True, "within_limits"
    
    def _analyze_request_content(self, request: Request) -> List[str]:
        """Analyze request for malicious content patterns."""
        threats_detected = []
        
        # Analyze URL path
        path = str(request.url.path).lower()
        query = str(request.url.query).lower() if request.url.query else ""
        
        # Check path and query for malicious patterns
        content_to_check = f"{path} {query}"
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, content_to_check, re.IGNORECASE):
                if "union\s+select" in pattern:
                    threats_detected.append("sql_injection")
                elif "<script" in pattern or "javascript:" in pattern:
                    threats_detected.append("xss_attempt")
                elif "\.\./" in pattern or "\.\.\\\\" in pattern:
                    threats_detected.append("path_traversal")
                elif any(cmd in pattern for cmd in ["cat", "ls", "dir", "wget", "curl"]):
                    threats_detected.append("command_injection")
                else:
                    threats_detected.append("malicious_content")
        
        # Check headers for malicious content
        for header_name, header_value in request.headers.items():
            header_content = f"{header_name.lower()}: {header_value.lower()}"
            for pattern in self.malicious_patterns[:10]:  # Check first 10 patterns for headers
                if re.search(pattern, header_content, re.IGNORECASE):
                    threats_detected.append("malicious_headers")
                    break
        
        return list(set(threats_detected))  # Remove duplicates
    
    def _log_security_event(self, ip: str, event_type: str, details: Dict, severity: str = "info"):
        """Enhanced security event logging."""
        if self.enable_request_logging:
            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "ip": ip,
                "event_type": event_type,
                "severity": severity,
                "details": details,
                "environment": settings.ENVIRONMENT
            }
            
            # Log to structured logger
            logger.info(
                "Security middleware event",
                event_type=event_type,
                ip=ip,
                severity=severity,
                details=details
            )
            
            # Log to security monitor if available
            if self.enable_advanced_monitoring:
                security_monitor.log_security_event(
                    event_type=event_type,
                    severity=severity.upper(),
                    details=details,
                    ip_address=ip
                )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security checks."""
        start_time = time.time()
        ip = self._get_real_ip(request)
        
        # Skip security checks for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            try:
                response = await call_next(request)
                # Add basic security headers even for OPTIONS
                response.headers["X-Request-ID"] = secrets.token_hex(16)
                response.headers["X-Response-Time"] = f"{(time.time() - start_time):.3f}s"
                return response
            except Exception as e:
                self._log_security_event(ip, "options_request_error", {"error": str(e)})
                raise
        
        # Enhanced IP blocking check with logging
        if self._is_ip_blocked(ip):
            self._log_security_event(
                ip, "blocked_ip_access_attempt",
                {
                    "path": str(request.url.path),
                    "method": request.method,
                    "user_agent": request.headers.get("User-Agent", "unknown")[:100],
                    "attempt_timestamp": time.time()
                },
                "high"
            )
            
            # Return generic access denied without revealing that IP is blocked
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
                headers={
                    "X-Request-ID": secrets.token_hex(16),
                    "X-Content-Type-Options": "nosniff"
                }
            )
        
        # Enhanced rate limiting check
        rate_limit_ok, rate_limit_reason = self._check_rate_limiting(ip)
        if not rate_limit_ok:
            self._track_suspicious_activity(ip, "excessive_requests", request)
            self._log_security_event(
                ip, "rate_limit_exceeded", 
                {
                    "reason": rate_limit_reason,
                    "path": str(request.url.path),
                    "method": request.method
                },
                "high"
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_request_size:
            self._track_suspicious_activity(ip, "large_request", request)
            self._log_security_event(
                ip, "large_request", 
                {"content_length": content_length, "max_allowed": self.max_request_size},
                "medium"
            )
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"}
            )
        
        # Advanced content analysis
        threats_detected = self._analyze_request_content(request)
        if threats_detected:
            for threat in threats_detected:
                self._track_suspicious_activity(ip, threat, request)
            
            self._log_security_event(
                ip, "malicious_content_detected",
                {
                    "threats": threats_detected,
                    "path": str(request.url.path),
                    "method": request.method,
                    "user_agent": request.headers.get("User-Agent", "unknown")[:100]
                },
                "high"
            )
            
            # Block request with malicious content
            return JSONResponse(
                status_code=400,
                content={"detail": "Request contains potentially malicious content"}
            )
        
        # Validate headers
        if not self._validate_request_headers(request):
            self._track_suspicious_activity(ip, "malicious_headers", request)
            self._log_security_event(
                ip, "invalid_headers", 
                {"path": str(request.url.path), "method": request.method},
                "medium"
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request headers"}
            )
        
        # Enhanced protection for sensitive endpoints
        if str(request.url.path) in self.sensitive_endpoints:
            # Additional checks for sensitive endpoints
            user_agent = request.headers.get("User-Agent", "")
            if not user_agent or len(user_agent) < 10:
                self._track_suspicious_activity(ip, "suspicious_sensitive_access", request)
                self._log_security_event(
                    ip, "sensitive_endpoint_suspicious_access",
                    {"path": str(request.url.path), "user_agent": user_agent},
                    "high"
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request"}
                )
            
            # Log access to sensitive endpoints
            self._log_security_event(
                ip, "sensitive_endpoint_access",
                {
                    "path": str(request.url.path),
                    "method": request.method,
                    "user_agent": user_agent[:100]
                },
                "info"
            )
        
        # Enhanced bot detection and handling
        is_bot = self._detect_bot_traffic(request)
        if is_bot:
            # Different handling based on endpoint type
            if str(request.url.path).startswith("/api/"):
                # More strict for API endpoints
                self._track_suspicious_activity(ip, "bot_detection", request)
                self._log_security_event(ip, "bot_api_access", {
                    "user_agent": request.headers.get("User-Agent", "unknown")[:100],
                    "path": str(request.url.path),
                    "method": request.method
                }, "medium")
                
                # Block bots from sensitive API endpoints
                if str(request.url.path) in self.sensitive_endpoints:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Automated access not permitted"}
                    )
            else:
                # Log but allow bots for non-API endpoints
                self._log_security_event(ip, "bot_detected", {
                    "user_agent": request.headers.get("User-Agent", "unknown")[:100],
                    "path": str(request.url.path)
                }, "info")
        
        # CSRF protection
        if self.enable_csrf_protection and not self._validate_csrf_token(request):
            self._track_suspicious_activity(ip, "csrf_violation", request)
            self._log_security_event(
                ip, "csrf_violation",
                {
                    "path": str(request.url.path),
                    "method": request.method,
                    "referer": request.headers.get("Referer", "unknown")
                },
                "medium"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"}
            )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Enhanced error logging with context
            error_context = {
                "error": str(e)[:200],  # Limit error message length
                "path": str(request.url.path),
                "method": request.method,
                "user_agent": request.headers.get("User-Agent", "unknown")[:100],
                "processing_time": time.time() - start_time,
                "error_type": type(e).__name__
            }
            
            self._log_security_event(ip, "request_processing_error", error_context, "high")
            
            # Track as suspicious activity if error rate is high
            if ip in self.suspicious_activity:
                recent_errors = [
                    activity for activity in self.suspicious_activity[ip].get("activities", [])
                    if (activity.get("type") == "request_error" and 
                        time.time() - activity.get("timestamp", 0) < 300)  # Last 5 minutes
                ]
                if len(recent_errors) >= 5:
                    self._track_suspicious_activity(ip, "excessive_errors", request)
            
            raise
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add CSRF token to response if needed
        if self.enable_csrf_protection and request.method == "GET":
            csrf_token = self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
        
        # Add enhanced custom headers
        request_id = secrets.token_hex(16)
        processing_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{processing_time:.3f}s"
        response.headers["X-Content-Type-Options"] = "nosniff"  # Reinforce content type security
        response.headers["X-Robots-Tag"] = "noindex, nofollow, nosnippet, noarchive"  # Prevent indexing of API responses
        
        # Add security monitoring header for debugging (only in development)
        if settings.ENVIRONMENT in ["development", "test"]:
            threat_count = len(self.suspicious_activity.get(ip, {}).get("activities", []))
            if threat_count > 0:
                response.headers["X-Security-Threats"] = str(threat_count)
        
        # Rate limiting headers
        if ip in self.request_counts:
            current_minute = int(time.time() // 60)
            requests_this_minute = self.request_counts[ip].get(current_minute, 0)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit_requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.rate_limit_requests - requests_this_minute))
            response.headers["X-RateLimit-Reset"] = str((current_minute + 1) * 60)
        
        # Enhanced response logging
        if self.enable_request_logging:
            processing_time = time.time() - start_time
            
            # Log different severities based on response
            severity = "info"
            if response.status_code >= 500:
                severity = "high"
            elif response.status_code >= 400:
                severity = "medium"
            elif processing_time > 5.0:  # Slow requests
                severity = "medium"
            
            self._log_security_event(ip, "request_completed", {
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "response_time": processing_time,
                "user_agent": request.headers.get("User-Agent", "unknown")[:100],
                "content_length": request.headers.get("Content-Length", "0"),
                "is_sensitive_endpoint": str(request.url.path) in self.sensitive_endpoints
            }, severity)
            
            # Alert on suspicious patterns in successful requests
            if (response.status_code == 200 and 
                str(request.url.path) in self.sensitive_endpoints and 
                processing_time < 0.1):
                # Very fast access to sensitive endpoints might indicate automated attacks
                self._log_security_event(ip, "fast_sensitive_access", {
                    "path": str(request.url.path),
                    "response_time": processing_time
                }, "medium")
        
        return response