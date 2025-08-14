"""
OWASP Top 10 2021 Protection Implementation for Content Protection Platform.

This module implements comprehensive protection against the OWASP Top 10 security risks:

A01:2021 – Broken Access Control
A02:2021 – Cryptographic Failures  
A03:2021 – Injection
A04:2021 – Insecure Design
A05:2021 – Security Misconfiguration
A06:2021 – Vulnerable and Outdated Components
A07:2021 – Identification and Authentication Failures
A08:2021 – Software and Data Integrity Failures
A09:2021 – Security Logging and Monitoring Failures
A10:2021 – Server-Side Request Forgery (SSRF)
"""

import re
import hashlib
import secrets
import base64
import json
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse
import ipaddress
from pathlib import Path
import mimetypes
import subprocess
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis
from fastapi import Request, HTTPException, status
import requests

from app.core.config import settings
from app.core.security import log_security_event


class OWASPProtection:
    """Comprehensive OWASP Top 10 protection implementation."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self._setup_encryption()
        self._setup_integrity_checking()
        
        # A01: Broken Access Control - Access patterns tracking
        self.suspicious_access_patterns = {}
        
        # A03: Injection - Pattern detection
        self.injection_patterns = self._load_injection_patterns()
        
        # A05: Security Misconfiguration - Security headers
        self.security_headers = self._get_security_headers()
        
        # A06: Vulnerable Components - Known vulnerable patterns
        self.vulnerable_patterns = self._load_vulnerable_patterns()
        
        # A10: SSRF - Allowed domains and IP ranges
        self.allowed_domains = self._get_allowed_domains()
        self.blocked_ips = self._get_blocked_ip_ranges()
    
    def _setup_encryption(self):
        """A02: Cryptographic Failures - Setup proper encryption."""
        # Generate or load encryption keys
        encryption_key = os.getenv("OWASP_ENCRYPTION_KEY")
        if not encryption_key:
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            print("WARNING: Generated new OWASP encryption key. Set OWASP_ENCRYPTION_KEY in production!")
        else:
            self.fernet = Fernet(encryption_key.encode())
        
        # Setup RSA keys for sensitive operations
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.rsa_public_key = self.rsa_private_key.public_key()
    
    def _setup_integrity_checking(self):
        """A08: Software and Data Integrity Failures - Setup integrity checking."""
        self.integrity_keys = {}
        self.signed_data_cache = {}
    
    def _load_injection_patterns(self) -> Dict[str, List[str]]:
        """A03: Injection - Load injection detection patterns."""
        return {
            'sql': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
                r"(--|;|/\*|\*/|xp_|sp_)",
                r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
                r"('|\"|`)([^'\"]*?)(\1)",
                r"(BENCHMARK|SLEEP|WAITFOR|DELAY)\s*\(",
                r"(INFORMATION_SCHEMA|MYSQL\.|SYS\.)",
                r"(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)"
            ],
            'xss': [
                r"<script[^>]*>.*?</script>",
                r"javascript:\s*[^;]*",
                r"vbscript:\s*[^;]*",
                r"on\w+\s*=\s*[\"'][^\"']*[\"']",
                r"<iframe[^>]*>.*?</iframe>",
                r"<object[^>]*>.*?</object>",
                r"<embed[^>]*>",
                r"<link[^>]*>",
                r"<meta[^>]*>",
                r"alert\s*\([^)]*\)",
                r"eval\s*\([^)]*\)",
                r"expression\s*\([^)]*\)"
            ],
            'ldap': [
                r"(\*|\|\||\&\&|\!)",
                r"(\(\w*\=\*\))",
                r"(\)\(\w*\=)",
                r"(\|\(\w*\=)",
                r"(\&\(\w*\=)"
            ],
            'xpath': [
                r"(\[|\]|\@|\|)",
                r"(ancestor|descendant|following|preceding)",
                r"(position\(\)|last\(\)|count\(\))",
                r"(text\(\)|node\(\))"
            ],
            'command': [
                r"(\||&|;|`|\$\(|\$\{|>|<)",
                r"(nc|netcat|curl|wget|python|perl|ruby|sh|bash|cmd|powershell)",
                r"(rm\s+-rf|del\s+/f|format\s+c:)",
                r"(cat\s+/etc/passwd|type\s+c:\\windows\\system32\\config\\sam)",
                r"(chmod|chown|sudo|su\s+root)"
            ],
            'nosql': [
                r"(\$where|\$regex|\$gt|\$lt|\$ne|\$in|\$nin)",
                r"(\{\s*\$\w+\s*:)",
                r"(this\.\w+|function\s*\(\s*\))",
                r"(sleep\s*\(|benchmark\s*\()"
            ]
        }
    
    def _get_security_headers(self) -> Dict[str, str]:
        """A05: Security Misconfiguration - Comprehensive security headers."""
        return {
            # XSS Protection
            "X-XSS-Protection": "1; mode=block",
            
            # Content Type Options
            "X-Content-Type-Options": "nosniff",
            
            # Frame Options
            "X-Frame-Options": "DENY",
            
            # HTTP Strict Transport Security
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://checkout.stripe.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "connect-src 'self' ws: wss: https://api.stripe.com; "
                "media-src 'self' data: https:; "
                "object-src 'none'; "
                "child-src 'none'; "
                "frame-src https://js.stripe.com https://checkout.stripe.com; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "manifest-src 'self';"
            ),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), gyroscope=(), "
                "magnetometer=(), payment=(), usb=(), interest-cohort=(), "
                "fullscreen=(self), picture-in-picture=(), display-capture=()"
            ),
            
            # Cross-Origin Policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-site",
            
            # Cache Control for sensitive responses
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
            
            # Custom security headers
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Robots-Tag": "none",
            "Server": "ContentProtectionPlatform"  # Hide server details
        }
    
    def _load_vulnerable_patterns(self) -> Dict[str, List[str]]:
        """A06: Vulnerable Components - Known vulnerable patterns."""
        return {
            'user_agents': [
                r'sqlmap',
                r'nmap',
                r'nikto',
                r'acunetix',
                r'w3af',
                r'burpsuite',
                r'owasp\s*zap',
                r'masscan',
                r'nessus',
                r'openvas'
            ],
            'headers': [
                r'x-forwarded-proto:\s*http',  # Insecure protocol
                r'x-forwarded-host:\s*[^a-zA-Z0-9.-]',  # Suspicious forwarded host
                r'x-real-ip:\s*(127\.|10\.|192\.168\.|169\.254\.)'  # Internal IP forwarding
            ],
            'paths': [
                r'/\.well-known/security\.txt',
                r'/robots\.txt',
                r'/sitemap\.xml',
                r'/admin',
                r'/administrator',
                r'/wp-admin',
                r'/phpmyadmin',
                r'/management',
                r'/console'
            ]
        }
    
    def _get_allowed_domains(self) -> Set[str]:
        """A10: SSRF - Define allowed domains for external requests."""
        return {
            'api.stripe.com',
            'checkout.stripe.com',
            'www.google.com',
            'www.bing.com',
            'api.dmca.com',
            # Add your legitimate external domains here
        }
    
    def _get_blocked_ip_ranges(self) -> List[ipaddress.IPv4Network]:
        """A10: SSRF - Define blocked IP ranges."""
        return [
            ipaddress.IPv4Network('0.0.0.0/8'),      # "This" network
            ipaddress.IPv4Network('10.0.0.0/8'),     # Private network
            ipaddress.IPv4Network('127.0.0.0/8'),    # Loopback
            ipaddress.IPv4Network('169.254.0.0/16'), # Link-local
            ipaddress.IPv4Network('172.16.0.0/12'),  # Private network
            ipaddress.IPv4Network('192.168.0.0/16'), # Private network
            ipaddress.IPv4Network('224.0.0.0/4'),    # Multicast
            ipaddress.IPv4Network('240.0.0.0/4'),    # Reserved
        ]
    
    # A01: Broken Access Control Protection
    def detect_access_anomalies(self, user_id: str, resource: str, action: str, ip: str) -> List[str]:
        """Detect suspicious access patterns that might indicate broken access control."""
        anomalies = []
        current_time = datetime.utcnow()
        
        # Track access patterns
        key = f"{user_id}:{ip}"
        if key not in self.suspicious_access_patterns:
            self.suspicious_access_patterns[key] = {
                'resources': [],
                'actions': [],
                'timestamps': [],
                'failed_attempts': 0
            }
        
        pattern = self.suspicious_access_patterns[key]
        pattern['resources'].append(resource)
        pattern['actions'].append(action)
        pattern['timestamps'].append(current_time)
        
        # Keep only recent data (last hour)
        cutoff_time = current_time - timedelta(hours=1)
        pattern['timestamps'] = [ts for ts in pattern['timestamps'] if ts > cutoff_time]
        
        # Detect anomalies
        if len(pattern['timestamps']) > 100:  # Too many requests
            anomalies.append("Excessive access attempts detected")
        
        # Check for privilege escalation attempts
        admin_resources = [r for r in pattern['resources'] if 'admin' in r.lower()]
        if len(admin_resources) > 5:
            anomalies.append("Potential privilege escalation attempt")
        
        # Check for horizontal access attempts (accessing many different resources)
        unique_resources = set(pattern['resources'][-50:])  # Last 50 requests
        if len(unique_resources) > 20:
            anomalies.append("Potential horizontal access violation")
        
        return anomalies
    
    # A02: Cryptographic Failures Protection
    def encrypt_sensitive_data(self, data: str, additional_entropy: str = None) -> str:
        """Encrypt sensitive data with proper key management."""
        try:
            # Add additional entropy if provided
            if additional_entropy:
                data = f"{data}:{additional_entropy}"
            
            encrypted = self.fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            log_security_event(
                "encryption_failure",
                "HIGH",
                {"error": str(e)},
                None,
                None
            )
            raise HTTPException(status_code=500, detail="Encryption failed")
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            log_security_event(
                "decryption_failure",
                "HIGH",
                {"error": str(e)},
                None,
                None
            )
            raise HTTPException(status_code=400, detail="Decryption failed")
    
    def hash_password_secure(self, password: str, salt: bytes = None) -> tuple[str, str]:
        """Secure password hashing with proper salt."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        
        key = kdf.derive(password.encode())
        hash_value = base64.b64encode(key).decode()
        salt_value = base64.b64encode(salt).decode()
        
        return hash_value, salt_value
    
    # A03: Injection Protection
    def detect_injection_attempts(self, input_data: str, input_type: str = "generic") -> List[str]:
        """Detect various types of injection attempts."""
        detected_attacks = []
        
        # Check all injection types if no specific type given
        types_to_check = [input_type] if input_type != "generic" else self.injection_patterns.keys()
        
        for attack_type in types_to_check:
            if attack_type not in self.injection_patterns:
                continue
            
            patterns = self.injection_patterns[attack_type]
            for pattern in patterns:
                if re.search(pattern, input_data, re.IGNORECASE | re.MULTILINE):
                    detected_attacks.append(f"{attack_type}_injection")
                    break  # One detection per type is enough
        
        return detected_attacks
    
    def sanitize_input(self, input_data: str, context: str = "general") -> str:
        """Sanitize input based on context."""
        if not isinstance(input_data, str):
            return str(input_data)
        
        sanitized = input_data
        
        if context == "html":
            # HTML context - remove dangerous tags and attributes
            dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
            for tag in dangerous_tags:
                sanitized = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
                sanitized = re.sub(f'<{tag}[^>]*/?>', '', sanitized, flags=re.IGNORECASE)
            
            # Remove dangerous attributes
            dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'javascript:', 'vbscript:']
            for attr in dangerous_attrs:
                sanitized = re.sub(f'{attr}[^\\s>]*', '', sanitized, flags=re.IGNORECASE)
        
        elif context == "sql":
            # SQL context - escape single quotes and remove SQL keywords
            sanitized = sanitized.replace("'", "''")
            sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', 'UNION', 'EXEC']
            for keyword in sql_keywords:
                sanitized = re.sub(f'\\b{keyword}\\b', f'_{keyword}_', sanitized, flags=re.IGNORECASE)
        
        elif context == "shell":
            # Shell context - remove dangerous characters
            dangerous_chars = ['|', '&', ';', '`', '$', '(', ')', '<', '>', '!']
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, f'_{ord(char)}_')
        
        # General sanitization
        sanitized = sanitized.replace('\x00', '')  # Remove null bytes
        sanitized = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', sanitized)  # Remove control characters
        
        return sanitized
    
    # A04: Insecure Design Protection
    def validate_business_logic(self, operation: str, user_data: Dict[str, Any]) -> List[str]:
        """Validate business logic to prevent insecure design issues."""
        violations = []
        
        if operation == "user_registration":
            # Business rule: Limit registrations per IP
            if user_data.get('registrations_from_ip', 0) > 5:
                violations.append("Too many registrations from this IP")
            
            # Business rule: Check email domain
            email = user_data.get('email', '')
            if email.endswith(('@tempmail.com', '@10minutemail.com', '@guerrillamail.com')):
                violations.append("Temporary email addresses not allowed")
        
        elif operation == "dmca_submission":
            # Business rule: User must own the content they're protecting
            if not user_data.get('content_ownership_verified', False):
                violations.append("Content ownership must be verified")
            
            # Business rule: Limit submissions per day
            if user_data.get('submissions_today', 0) > 100:
                violations.append("Daily submission limit exceeded")
        
        elif operation == "payment_processing":
            # Business rule: Validate payment amount
            amount = user_data.get('amount', 0)
            if amount <= 0 or amount > 10000:  # $10,000 max
                violations.append("Invalid payment amount")
            
            # Business rule: Check for duplicate transactions
            if user_data.get('duplicate_transaction', False):
                violations.append("Duplicate transaction detected")
        
        return violations
    
    # A05: Security Misconfiguration Protection
    def get_secure_headers(self, request_path: str) -> Dict[str, str]:
        """Get appropriate security headers based on request path."""
        headers = self.security_headers.copy()
        
        # Adjust CSP for specific paths
        if request_path.startswith('/api/'):
            # API endpoints don't need script/style sources
            headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        
        elif request_path.startswith('/admin/'):
            # Admin paths need stricter CSP
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        
        # Add cache headers for sensitive data
        if any(sensitive in request_path for sensitive in ['/auth/', '/admin/', '/billing/']):
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            })
        
        return headers
    
    def validate_server_configuration(self) -> List[str]:
        """Validate server configuration for security issues."""
        issues = []
        
        # Check if debug mode is enabled in production
        if not settings.DEBUG and os.getenv('DEBUG', '').lower() == 'true':
            issues.append("Debug mode should not be enabled in production")
        
        # Check if default secret key is being used
        if settings.SECRET_KEY == "dev-secret-key-change-in-production":
            issues.append("Default secret key is being used")
        
        # Check if HTTPS is enforced
        if not os.getenv('FORCE_HTTPS', '').lower() == 'true':
            issues.append("HTTPS enforcement is not configured")
        
        # Check database connection security
        if 'sslmode=disable' in settings.SQLALCHEMY_DATABASE_URI:
            issues.append("Database SSL is disabled")
        
        return issues
    
    # A06: Vulnerable Components Protection
    def detect_vulnerable_patterns(self, request: Request) -> List[str]:
        """Detect patterns associated with vulnerable components."""
        vulnerabilities = []
        
        # Check User-Agent for scanning tools
        user_agent = request.headers.get('User-Agent', '').lower()
        for pattern in self.vulnerable_patterns['user_agents']:
            if re.search(pattern, user_agent):
                vulnerabilities.append(f"Scanning tool detected: {pattern}")
        
        # Check for suspicious headers
        for header_name, header_value in request.headers.items():
            for pattern in self.vulnerable_patterns['headers']:
                if re.search(pattern, f"{header_name}: {header_value}", re.IGNORECASE):
                    vulnerabilities.append(f"Suspicious header: {header_name}")
        
        # Check for vulnerable path access attempts
        path = request.url.path.lower()
        for pattern in self.vulnerable_patterns['paths']:
            if re.search(pattern, path):
                vulnerabilities.append(f"Vulnerable path access: {path}")
        
        return vulnerabilities
    
    # A07: Authentication Failures Protection
    def validate_authentication_strength(self, auth_data: Dict[str, Any]) -> List[str]:
        """Validate authentication implementation strength."""
        issues = []
        
        # Check password strength
        password = auth_data.get('password', '')
        if len(password) < 12:
            issues.append("Password too short (minimum 12 characters)")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letters")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letters")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain numbers")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password):
            issues.append("Password must contain special characters")
        
        # Check for common passwords
        common_passwords = ['password', '123456', 'admin', 'letmein', 'welcome']
        if password.lower() in common_passwords:
            issues.append("Common password detected")
        
        # Check 2FA requirement for privileged accounts
        if auth_data.get('role') in ['admin', 'super_admin'] and not auth_data.get('mfa_enabled'):
            issues.append("Multi-factor authentication required for privileged accounts")
        
        return issues
    
    def track_failed_authentication(self, identifier: str, ip_address: str) -> bool:
        """Track failed authentication attempts and implement account lockout."""
        key = f"failed_auth:{identifier}:{ip_address}"
        
        if self.redis_client:
            # Increment failure count
            current_failures = self.redis_client.incr(key)
            if current_failures == 1:
                # Set expiration for first failure
                self.redis_client.expire(key, 3600)  # 1 hour
            
            # Check if account should be locked
            if current_failures >= 5:  # 5 failed attempts
                lock_key = f"account_locked:{identifier}"
                self.redis_client.setex(lock_key, 1800, "locked")  # 30 minute lockout
                return True
        
        return False
    
    # A08: Software and Data Integrity Protection
    def sign_data(self, data: str, key_id: str = "default") -> str:
        """Sign data for integrity verification."""
        if key_id not in self.integrity_keys:
            self.integrity_keys[key_id] = secrets.token_bytes(32)
        
        signature = hashlib.hmac.new(
            self.integrity_keys[key_id],
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_data_integrity(self, data: str, signature: str, key_id: str = "default") -> bool:
        """Verify data integrity using signature."""
        if key_id not in self.integrity_keys:
            return False
        
        expected_signature = hashlib.hmac.new(
            self.integrity_keys[key_id],
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return secrets.compare_digest(signature, expected_signature)
    
    def validate_file_integrity(self, file_path: str, expected_hash: str = None) -> bool:
        """Validate uploaded file integrity."""
        if not os.path.exists(file_path):
            return False
        
        # Calculate file hash
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        file_hash = sha256_hash.hexdigest()
        
        if expected_hash:
            return secrets.compare_digest(file_hash, expected_hash)
        
        # Store hash for future verification
        hash_key = f"file_hash:{os.path.basename(file_path)}"
        if self.redis_client:
            self.redis_client.setex(hash_key, 86400, file_hash)  # 24 hour expiry
        
        return True
    
    # A09: Security Logging and Monitoring
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        user_id: str = None,
        ip_address: str = None,
        request: Request = None
    ):
        """Enhanced security logging with structured data."""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "user_id": user_id,
            "ip_address": ip_address,
            "event_id": secrets.token_hex(16)
        }
        
        if request:
            event_data.update({
                "method": request.method,
                "path": request.url.path,
                "user_agent": request.headers.get("User-Agent"),
                "referer": request.headers.get("Referer"),
                "content_type": request.headers.get("Content-Type")
            })
        
        # Log to multiple destinations
        self._log_to_siem(event_data)
        self._log_to_file(event_data)
        
        # Trigger alerts for critical events
        if severity in ["HIGH", "CRITICAL"]:
            self._trigger_security_alert(event_data)
    
    def _log_to_siem(self, event_data: Dict[str, Any]):
        """Log security events to SIEM system."""
        # In production, this would integrate with your SIEM
        if self.redis_client:
            self.redis_client.lpush("security_events", json.dumps(event_data))
            self.redis_client.ltrim("security_events", 0, 9999)  # Keep last 10k events
    
    def _log_to_file(self, event_data: Dict[str, Any]):
        """Log security events to file."""
        log_dir = Path("logs/security")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"security_{datetime.utcnow().strftime('%Y-%m-%d')}.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(event_data) + "\n")
    
    def _trigger_security_alert(self, event_data: Dict[str, Any]):
        """Trigger security alerts for critical events."""
        # In production, this would send alerts via email, Slack, etc.
        print(f"SECURITY ALERT: {event_data['event_type']} - {event_data['details']}")
    
    # A10: SSRF Protection
    def validate_external_request(self, url: str) -> tuple[bool, str]:
        """Validate external request to prevent SSRF attacks."""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False, "Invalid URL scheme"
            
            # Check domain whitelist
            if parsed.netloc not in self.allowed_domains:
                return False, f"Domain not in whitelist: {parsed.netloc}"
            
            # Resolve IP and check against blocked ranges
            try:
                import socket
                ip = socket.gethostbyname(parsed.netloc)
                ip_obj = ipaddress.IPv4Address(ip)
                
                for blocked_range in self.blocked_ips:
                    if ip_obj in blocked_range:
                        return False, f"IP address in blocked range: {ip}"
                
            except (socket.gaierror, ValueError):
                return False, "Unable to resolve domain"
            
            # Check for URL redirects (basic check)
            if len(parsed.path) > 2000:  # Suspicious long path
                return False, "URL path too long"
            
            return True, "URL validated"
            
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    def make_safe_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """Make a safe external request with SSRF protection."""
        is_valid, error_msg = self.validate_external_request(url)
        
        if not is_valid:
            log_security_event(
                "ssrf_attempt",
                "HIGH",
                {"url": url, "error": error_msg},
                None,
                None
            )
            raise HTTPException(status_code=400, detail=f"Request blocked: {error_msg}")
        
        # Set safe timeout and other parameters
        safe_kwargs = {
            "timeout": 10,
            "allow_redirects": False,
            "verify": True,  # SSL verification
            "headers": {
                "User-Agent": "ContentProtectionPlatform/1.0",
                "Accept": "application/json, text/plain"
            }
        }
        safe_kwargs.update(kwargs)
        
        try:
            response = requests.request(method, url, **safe_kwargs)
            
            # Log successful external request
            log_security_event(
                "external_request",
                "LOW",
                {"url": url, "method": method, "status_code": response.status_code},
                None,
                None
            )
            
            return response
            
        except requests.RequestException as e:
            log_security_event(
                "external_request_failed",
                "MEDIUM",
                {"url": url, "method": method, "error": str(e)},
                None,
                None
            )
            raise HTTPException(status_code=500, detail="External request failed")


# Global OWASP protection instance
owasp_protection = OWASPProtection()