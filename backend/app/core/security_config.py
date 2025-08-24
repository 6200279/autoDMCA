"""
Advanced security configuration and utilities for the Content Protection Platform.

This module provides enterprise-grade security configurations including:
- Enhanced JWT security with blacklisting
- API key management
- Role-based access control (RBAC)
- Input validation and sanitization
- Encryption utilities for sensitive data
- Security monitoring and alerting
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, Any, Union
from enum import Enum
import redis
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
from jose import JWTError, jwt
import pyotp
import re
from ipaddress import ip_address, ip_network

from app.core.config import settings


class UserRole(Enum):
    """User role enumeration for RBAC."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    API_USER = "api_user"
    READ_ONLY = "read_only"


class PermissionLevel(Enum):
    """Permission levels for resources."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class SecurityLevel(Enum):
    """Security levels for different operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE, PermissionLevel.ADMIN],
    UserRole.ADMIN: [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
    UserRole.MODERATOR: [PermissionLevel.READ, PermissionLevel.WRITE],
    UserRole.USER: [PermissionLevel.READ, PermissionLevel.WRITE],
    UserRole.API_USER: [PermissionLevel.READ, PermissionLevel.WRITE],
    UserRole.READ_ONLY: [PermissionLevel.READ]
}


class SecurityConfig:
    """Advanced security configuration manager."""
    
    def __init__(self):
        self.redis_client = None
        self._encryption_key = None
        self._setup_redis()
        self._setup_encryption()
    
    def _setup_redis(self):
        """Setup Redis connection for security operations."""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def _setup_encryption(self):
        """Setup encryption key for sensitive data."""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            # Generate a new key if not provided (for development only)
            key = Fernet.generate_key()
            self._encryption_key = key
            print("WARNING: Generated new encryption key. Set ENCRYPTION_KEY in production!")
        else:
            self._encryption_key = encryption_key.encode()
    
    def get_fernet_cipher(self) -> Fernet:
        """Get Fernet cipher for data encryption."""
        return Fernet(self._encryption_key)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        cipher = self.get_fernet_cipher()
        encrypted = cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        cipher = self.get_fernet_cipher()
        decoded = base64.b64decode(encrypted_data.encode())
        decrypted = cipher.decrypt(decoded)
        return decrypted.decode()


class JWTSecurityManager:
    """Enhanced JWT security manager with token blacklisting and advanced features."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.blacklisted_tokens: Set[str] = set()
        
        # Enhanced JWT settings
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30))
        self.refresh_token_expire = timedelta(days=getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 7))
    
    def create_access_token(
        self,
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM
    ) -> str:
        """Create enhanced JWT access token with additional security features."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + self.access_token_expire
        
        # Generate unique token ID for blacklisting
        token_id = secrets.token_hex(16)
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access",
            "iat": datetime.utcnow(),
            "jti": token_id,  # JWT ID for blacklisting
            "security_level": security_level.value,
            "nbf": datetime.utcnow(),  # Not before
        }
        
        # Add additional claims if provided
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        subject: Union[str, Any],
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + self.refresh_token_expire
        token_id = secrets.token_hex(16)
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": token_id,
            "nbf": datetime.utcnow(),
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token with blacklist checking."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[self.algorithm])
            
            # Check if token is blacklisted
            if self.is_token_blacklisted(payload.get("jti")):
                return None
            
            return payload
        except JWTError:
            return None
    
    def blacklist_token(self, token: str) -> bool:
        """Blacklist a JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[self.algorithm])
            token_id = payload.get("jti")
            
            if not token_id:
                return False
            
            # Calculate TTL based on token expiration
            exp = payload.get("exp")
            if exp:
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    if self.redis_client:
                        self.redis_client.setex(f"blacklisted_token:{token_id}", ttl, "1")
                    else:
                        self.blacklisted_tokens.add(token_id)
                    return True
            return False
        except JWTError:
            return False
    
    def is_token_blacklisted(self, token_id: str) -> bool:
        """Check if a token is blacklisted."""
        if not token_id:
            return False
        
        if self.redis_client:
            return bool(self.redis_client.get(f"blacklisted_token:{token_id}"))
        else:
            return token_id in self.blacklisted_tokens


class APIKeyManager:
    """API key management system for external integrations."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.api_keys: Dict[str, Dict] = {}
    
    def generate_api_key(
        self,
        name: str,
        user_id: str,
        permissions: List[str],
        expires_in_days: Optional[int] = None,
        rate_limit: int = 1000
    ) -> Dict[str, Any]:
        """Generate a new API key with specified permissions."""
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        secret = secrets.token_urlsafe(64)
        
        # Hash the secret for storage
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        
        key_data = {
            "name": name,
            "user_id": user_id,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "last_used": None,
            "usage_count": 0,
            "secret_hash": secret_hash,
            "active": True
        }
        
        # Store in Redis or memory
        if self.redis_client:
            self.redis_client.hset(f"api_key:{api_key}", mapping=key_data)
        else:
            self.api_keys[api_key] = key_data
        
        return {
            "api_key": api_key,
            "secret": secret,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "expires_at": expires_at
        }
    
    def validate_api_key(self, api_key: str, secret: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and secret."""
        if self.redis_client:
            key_data = self.redis_client.hgetall(f"api_key:{api_key}")
        else:
            key_data = self.api_keys.get(api_key)
        
        if not key_data or not key_data.get("active"):
            return None
        
        # Check expiration
        expires_at = key_data.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
            return None
        
        # Verify secret
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        if secret_hash != key_data.get("secret_hash"):
            return None
        
        # Update usage stats
        self._update_api_key_usage(api_key, key_data)
        
        return key_data
    
    def _update_api_key_usage(self, api_key: str, key_data: Dict[str, Any]):
        """Update API key usage statistics."""
        usage_count = int(key_data.get("usage_count", 0)) + 1
        last_used = datetime.utcnow().isoformat()
        
        if self.redis_client:
            self.redis_client.hset(f"api_key:{api_key}", "usage_count", usage_count)
            self.redis_client.hset(f"api_key:{api_key}", "last_used", last_used)
        else:
            key_data["usage_count"] = usage_count
            key_data["last_used"] = last_used
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if self.redis_client:
            return bool(self.redis_client.hset(f"api_key:{api_key}", "active", False))
        else:
            if api_key in self.api_keys:
                self.api_keys[api_key]["active"] = False
                return True
            return False


class InputValidator:
    """Enhanced input validation and sanitization."""
    
    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|;|/\*|\*/|xp_|sp_)",
        r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
        r"('|\"|`)(.*?)(\1)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"alert\s*\(",
        r"eval\s*\(",
        r"expression\s*\("
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"(\||&|;|`|\$\(|\$\{)",
        r"(nc|netcat|curl|wget|python|perl|ruby|sh|bash)",
        r"(rm\s+-rf|mkfifo|cat\s+/etc/passwd)"
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\\\",
        r"~",
        r"/etc/",
        r"/proc/",
        r"C:\\\\",
        r"\\\\windows\\\\"
    ]
    
    @classmethod
    def validate_string(
        cls,
        value: str,
        max_length: int = 1000,
        allow_html: bool = False,
        check_patterns: bool = True
    ) -> tuple[bool, str]:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            return False, "Input must be a string"
        
        if len(value) > max_length:
            return False, f"Input too long (max {max_length} characters)"
        
        if check_patterns:
            # Check for malicious patterns
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    return False, "Potentially malicious SQL pattern detected"
            
            if not allow_html:
                for pattern in cls.XSS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        return False, "Potentially malicious XSS pattern detected"
            
            for pattern in cls.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    return False, "Potentially malicious command injection pattern detected"
            
            for pattern in cls.PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    return False, "Potentially malicious path traversal pattern detected"
        
        return True, value
    
    @classmethod
    def sanitize_html(cls, value: str) -> str:
        """Basic HTML sanitization."""
        # Remove potentially dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'style', 'meta']
        for tag in dangerous_tags:
            value = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(f'<{tag}[^>]*/?>', '', value, flags=re.IGNORECASE)
        
        # Remove javascript: and vbscript: URLs
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        value = re.sub(r'vbscript:', '', value, flags=re.IGNORECASE)
        
        # Remove event handlers
        event_handlers = ['onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout']
        for handler in event_handlers:
            value = re.sub(f'{handler}\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
        
        return value
    
    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, str]:
        """Validate email address with enhanced security checks."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\.+',  # Multiple consecutive dots
            r'^\.|\.$',  # Starting or ending with dot
            r'@.*@',  # Multiple @ symbols
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email):
                return False, "Invalid email format"
        
        return True, email.lower()
    
    @classmethod
    def validate_ip_address(cls, ip: str) -> tuple[bool, str]:
        """Validate IP address."""
        try:
            ip_obj = ip_address(ip)
            return True, str(ip_obj)
        except ValueError:
            return False, "Invalid IP address format"
    
    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """Validate URL with security checks."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        
        if not re.match(url_pattern, url):
            return False, "Invalid URL format"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'javascript:',
            r'data:',
            r'file:',
            r'ftp:',
            r'localhost',
            r'127\.0\.0\.1',
            r'::1'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False, "Potentially unsafe URL"
        
        return True, url


class SecurityMonitor:
    """Security event monitoring and alerting system."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.events: List[Dict] = []
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a security event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "user_id": user_id,
            "ip_address": ip_address,
            "event_id": secrets.token_hex(8)
        }
        
        # Store in Redis or memory
        if self.redis_client:
            self.redis_client.lpush("security_events", json.dumps(event))
            # Keep only last 1000 events
            self.redis_client.ltrim("security_events", 0, 999)
        else:
            self.events.append(event)
            # Keep only last 100 events in memory
            if len(self.events) > 100:
                self.events.pop(0)
        
        # Check for critical events that need immediate attention
        if severity in ["HIGH", "CRITICAL"]:
            self._handle_critical_event(event)
    
    def _handle_critical_event(self, event: Dict[str, Any]):
        """Handle critical security events."""
        # In production, this would trigger alerts (email, Slack, etc.)
        print(f"CRITICAL SECURITY EVENT: {event['event_type']} - {event['details']}")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent security events."""
        if self.redis_client:
            events = self.redis_client.lrange("security_events", 0, limit - 1)
            return [json.loads(event) for event in events]
        else:
            return self.events[-limit:]
    
    def detect_anomalies(self, user_id: str, ip_address: str) -> List[str]:
        """Detect security anomalies for a user."""
        anomalies = []
        
        # Check for multiple failed login attempts
        failed_logins = self._count_events("failed_login", user_id, hours=1)
        if failed_logins >= 5:
            anomalies.append("Multiple failed login attempts detected")
        
        # Check for login from new location
        if self._is_new_location(user_id, ip_address):
            anomalies.append("Login from new location detected")
        
        # Check for unusual activity patterns
        unusual_activity = self._detect_unusual_activity(user_id)
        if unusual_activity:
            anomalies.extend(unusual_activity)
        
        return anomalies
    
    def _count_events(self, event_type: str, user_id: str, hours: int) -> int:
        """Count events of a specific type for a user in the last N hours."""
        # Implementation would depend on storage backend
        # This is a simplified version
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        count = 0
        
        for event in self.get_recent_events(200):
            if (event["event_type"] == event_type and 
                event["user_id"] == user_id and
                datetime.fromisoformat(event["timestamp"]) > cutoff_time):
                count += 1
        
        return count
    
    def _is_new_location(self, user_id: str, ip_address: str) -> bool:
        """Check if the IP address is new for the user."""
        # In production, this would check against a database of known IPs
        # This is a simplified version
        return False
    
    def _detect_unusual_activity(self, user_id: str) -> List[str]:
        """Detect unusual activity patterns."""
        # This would implement ML-based anomaly detection in production
        return []


# Global security instances
security_config = SecurityConfig()
jwt_manager = JWTSecurityManager(security_config.redis_client)
api_key_manager = APIKeyManager(security_config.redis_client)
security_monitor = SecurityMonitor(security_config.redis_client)