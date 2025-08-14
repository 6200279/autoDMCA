"""
Content Protection Platform Specific Security Implementation.

This module provides security measures tailored for:
- AI model protection and secure inference
- DMCA takedown data handling with PII protection
- Watermarking security and anti-tampering
- Search API key security
- Browser extension security
- Content fingerprinting security
"""

import os
import json
import hashlib
import secrets
import base64
import io
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
import magic
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis
import jwt

from app.core.config import settings
from app.core.security import log_security_event
from app.security.owasp_protection import owasp_protection


class AIModelSecurity:
    """Security measures for AI/ML models and inference."""
    
    def __init__(self):
        self._setup_model_encryption()
        self.model_integrity_hashes = {}
        self.inference_rate_limits = {}
        
        # Model access control
        self.model_permissions = {
            'face_recognition': ['user', 'api_user', 'admin'],
            'content_similarity': ['user', 'api_user', 'admin'],
            'content_watermarking': ['user', 'admin'],
            'fake_detection': ['user', 'api_user', 'admin', 'moderator'],
            'advanced_analytics': ['admin', 'super_admin']
        }
    
    def _setup_model_encryption(self):
        """Setup encryption for AI model protection."""
        model_key = os.getenv("AI_MODEL_ENCRYPTION_KEY")
        if not model_key:
            key = Fernet.generate_key()
            self.model_cipher = Fernet(key)
            print("WARNING: Generated new AI model encryption key. Set AI_MODEL_ENCRYPTION_KEY in production!")
        else:
            self.model_cipher = Fernet(model_key.encode())
    
    def encrypt_model_weights(self, model_data: bytes) -> bytes:
        """Encrypt AI model weights for secure storage."""
        try:
            return self.model_cipher.encrypt(model_data)
        except Exception as e:
            log_security_event(
                "ai_model_encryption_failed",
                "HIGH",
                {"error": str(e)},
                None,
                None
            )
            raise
    
    def decrypt_model_weights(self, encrypted_data: bytes) -> bytes:
        """Decrypt AI model weights for inference."""
        try:
            return self.model_cipher.decrypt(encrypted_data)
        except Exception as e:
            log_security_event(
                "ai_model_decryption_failed",
                "HIGH",
                {"error": str(e)},
                None,
                None
            )
            raise
    
    def verify_model_integrity(self, model_name: str, model_data: bytes) -> bool:
        """Verify AI model integrity using checksums."""
        model_hash = hashlib.sha256(model_data).hexdigest()
        
        # Check against known good hash
        expected_hash = self.model_integrity_hashes.get(model_name)
        if expected_hash:
            if model_hash != expected_hash:
                log_security_event(
                    "ai_model_integrity_violation",
                    "CRITICAL",
                    {
                        "model": model_name,
                        "expected_hash": expected_hash,
                        "actual_hash": model_hash
                    },
                    None,
                    None
                )
                return False
        else:
            # Store hash for future verification
            self.model_integrity_hashes[model_name] = model_hash
        
        return True
    
    def secure_model_inference(
        self,
        model_name: str,
        input_data: Any,
        user_role: str,
        user_id: str,
        ip_address: str
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """Perform secure AI model inference with access control."""
        
        # Check permissions
        allowed_roles = self.model_permissions.get(model_name, [])
        if user_role not in allowed_roles:
            log_security_event(
                "unauthorized_ai_model_access",
                "HIGH",
                {
                    "model": model_name,
                    "user_role": user_role,
                    "user_id": user_id
                },
                user_id,
                ip_address
            )
            return False, None, "Access denied: insufficient privileges"
        
        # Check rate limits
        if not self._check_inference_rate_limit(user_id, ip_address):
            return False, None, "Rate limit exceeded for AI inference"
        
        # Sanitize input data
        sanitized_input = self._sanitize_inference_input(input_data, model_name)
        if sanitized_input is None:
            return False, None, "Invalid or potentially malicious input"
        
        # Log inference request
        log_security_event(
            "ai_inference_request",
            "LOW",
            {
                "model": model_name,
                "input_type": type(input_data).__name__,
                "user_role": user_role
            },
            user_id,
            ip_address
        )
        
        # Perform inference (actual inference would happen here)
        # For now, return success with sanitized input
        return True, sanitized_input, None
    
    def _check_inference_rate_limit(self, user_id: str, ip_address: str) -> bool:
        """Check rate limits for AI inference."""
        current_time = datetime.utcnow()
        hour_window = current_time.replace(minute=0, second=0, microsecond=0)
        
        # User-based rate limit
        user_key = f"{user_id}:{hour_window.isoformat()}"
        user_count = self.inference_rate_limits.get(user_key, 0)
        
        # IP-based rate limit
        ip_key = f"{ip_address}:{hour_window.isoformat()}"
        ip_count = self.inference_rate_limits.get(ip_key, 0)
        
        # Limits: 1000 per user per hour, 100 per IP per hour
        if user_count >= 1000 or ip_count >= 100:
            return False
        
        # Increment counters
        self.inference_rate_limits[user_key] = user_count + 1
        self.inference_rate_limits[ip_key] = ip_count + 1
        
        # Clean old entries
        self._cleanup_rate_limits(current_time)
        
        return True
    
    def _cleanup_rate_limits(self, current_time: datetime):
        """Clean up old rate limit entries."""
        cutoff_time = current_time - timedelta(hours=2)
        keys_to_remove = []
        
        for key in self.inference_rate_limits:
            try:
                key_time_str = key.split(':', 1)[1]
                key_time = datetime.fromisoformat(key_time_str)
                if key_time < cutoff_time:
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.inference_rate_limits[key]
    
    def _sanitize_inference_input(self, input_data: Any, model_name: str) -> Any:
        """Sanitize input data for AI model inference."""
        
        if model_name == 'face_recognition':
            # Validate image input
            if isinstance(input_data, (str, bytes)):
                return self._validate_image_input(input_data)
        
        elif model_name == 'content_similarity':
            # Validate text or image input
            if isinstance(input_data, str):
                # Text similarity - sanitize text
                is_valid, sanitized = owasp_protection.sanitize_input(input_data, 'general')
                return sanitized if is_valid else None
            elif isinstance(input_data, (str, bytes)):
                # Image similarity
                return self._validate_image_input(input_data)
        
        elif model_name == 'fake_detection':
            # Validate media input
            return self._validate_media_input(input_data)
        
        # Default validation
        return input_data
    
    def _validate_image_input(self, image_data: Union[str, bytes]) -> Optional[bytes]:
        """Validate image input for security."""
        try:
            # If base64 string, decode it
            if isinstance(image_data, str):
                if image_data.startswith('data:image/'):
                    # Remove data URL prefix
                    image_data = image_data.split(',', 1)[1]
                image_data = base64.b64decode(image_data)
            
            # Check file size (max 10MB)
            if len(image_data) > 10 * 1024 * 1024:
                return None
            
            # Validate file type using python-magic
            file_type = magic.from_buffer(image_data, mime=True)
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if file_type not in allowed_types:
                return None
            
            # Additional validation with PIL
            try:
                image = Image.open(io.BytesIO(image_data))
                image.verify()  # Verify it's a valid image
                
                # Check image dimensions (prevent DOS via huge images)
                if image.width > 4096 or image.height > 4096:
                    return None
                
                return image_data
            except Exception:
                return None
                
        except Exception as e:
            log_security_event(
                "image_validation_failed",
                "MEDIUM",
                {"error": str(e)},
                None,
                None
            )
            return None
    
    def _validate_media_input(self, media_data: Any) -> Optional[Any]:
        """Validate media input (images, videos) for security."""
        # Similar validation as image but extended for video
        return self._validate_image_input(media_data)


class DMCADataSecurity:
    """Security measures for DMCA takedown data with PII protection."""
    
    def __init__(self):
        self._setup_pii_encryption()
        self.pii_fields = [
            'full_name', 'email', 'phone', 'address', 'ssn',
            'company_name', 'copyright_holder_name', 'agent_name'
        ]
        self.data_retention_policies = {
            'takedown_notices': timedelta(days=2555),  # 7 years
            'infringement_reports': timedelta(days=1095),  # 3 years
            'user_data': timedelta(days=2190),  # 6 years
            'communication_logs': timedelta(days=1095)  # 3 years
        }
    
    def _setup_pii_encryption(self):
        """Setup encryption specifically for PII data."""
        pii_key = os.getenv("PII_ENCRYPTION_KEY")
        if not pii_key:
            # Generate a new key (derive from master key)
            master_key = os.getenv("ENCRYPTION_KEY", settings.SECRET_KEY).encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'dmca_pii_salt_2024',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key))
            self.pii_cipher = Fernet(key)
        else:
            self.pii_cipher = Fernet(pii_key.encode())
    
    def encrypt_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PII fields in DMCA data."""
        encrypted_data = data.copy()
        
        for field in self.pii_fields:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    # Encrypt the field
                    encrypted_value = self.pii_cipher.encrypt(
                        str(encrypted_data[field]).encode()
                    )
                    encrypted_data[field] = base64.b64encode(encrypted_value).decode()
                    encrypted_data[f"{field}_encrypted"] = True
                except Exception as e:
                    log_security_event(
                        "pii_encryption_failed",
                        "HIGH",
                        {"field": field, "error": str(e)},
                        None,
                        None
                    )
                    # Don't store unencrypted PII if encryption fails
                    encrypted_data[field] = "[ENCRYPTION_FAILED]"
        
        return encrypted_data
    
    def decrypt_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt PII fields in DMCA data."""
        decrypted_data = data.copy()
        
        for field in self.pii_fields:
            if field in decrypted_data and decrypted_data.get(f"{field}_encrypted"):
                try:
                    # Decrypt the field
                    encrypted_value = base64.b64decode(decrypted_data[field].encode())
                    decrypted_value = self.pii_cipher.decrypt(encrypted_value)
                    decrypted_data[field] = decrypted_value.decode()
                    del decrypted_data[f"{field}_encrypted"]
                except Exception as e:
                    log_security_event(
                        "pii_decryption_failed",
                        "HIGH",
                        {"field": field, "error": str(e)},
                        None,
                        None
                    )
                    decrypted_data[field] = "[DECRYPTION_FAILED]"
        
        return decrypted_data
    
    def anonymize_dmca_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize DMCA data for analytics/reporting."""
        anonymized = data.copy()
        
        # Remove or hash PII fields
        for field in self.pii_fields:
            if field in anonymized:
                if field in ['email', 'full_name']:
                    # Create anonymous hash
                    hash_value = hashlib.sha256(str(anonymized[field]).encode()).hexdigest()[:8]
                    anonymized[field] = f"anon_{hash_value}"
                else:
                    # Remove completely
                    del anonymized[field]
        
        # Remove IP addresses
        if 'ip_address' in anonymized:
            ip_parts = anonymized['ip_address'].split('.')
            if len(ip_parts) == 4:
                # Mask last octet
                anonymized['ip_address'] = f"{'.'.join(ip_parts[:3])}.xxx"
        
        return anonymized
    
    def validate_dmca_data_access(
        self,
        user_role: str,
        user_id: str,
        data_type: str,
        access_reason: str
    ) -> Tuple[bool, str]:
        """Validate access to DMCA data with audit logging."""
        
        # Define access levels
        access_matrix = {
            'takedown_notices': ['admin', 'super_admin', 'legal'],
            'infringement_reports': ['user', 'moderator', 'admin', 'super_admin'],
            'user_data': ['admin', 'super_admin'],
            'communication_logs': ['admin', 'super_admin', 'legal']
        }
        
        allowed_roles = access_matrix.get(data_type, [])
        
        if user_role not in allowed_roles:
            log_security_event(
                "unauthorized_dmca_data_access",
                "HIGH",
                {
                    "data_type": data_type,
                    "user_role": user_role,
                    "access_reason": access_reason
                },
                user_id,
                None
            )
            return False, "Access denied: insufficient privileges for DMCA data"
        
        # Log authorized access for audit trail
        log_security_event(
            "authorized_dmca_data_access",
            "MEDIUM",
            {
                "data_type": data_type,
                "user_role": user_role,
                "access_reason": access_reason
            },
            user_id,
            None
        )
        
        return True, "Access granted"
    
    def check_data_retention(self, data_type: str, created_at: datetime) -> Dict[str, Any]:
        """Check data retention policies and suggest cleanup."""
        retention_period = self.data_retention_policies.get(data_type)
        if not retention_period:
            return {"action": "review", "reason": "No retention policy defined"}
        
        age = datetime.utcnow() - created_at
        
        if age > retention_period:
            return {
                "action": "delete",
                "reason": f"Data exceeds retention period of {retention_period.days} days",
                "age_days": age.days
            }
        elif age > retention_period * 0.9:  # 90% of retention period
            return {
                "action": "warning",
                "reason": f"Data approaching retention limit",
                "days_remaining": (retention_period - age).days
            }
        else:
            return {
                "action": "keep",
                "days_remaining": (retention_period - age).days
            }


class WatermarkSecurity:
    """Security measures for content watermarking."""
    
    def __init__(self):
        self._setup_watermark_keys()
        self.watermark_integrity_checks = {}
    
    def _setup_watermark_keys(self):
        """Setup cryptographic keys for watermarking."""
        watermark_key = os.getenv("WATERMARK_MASTER_KEY")
        if not watermark_key:
            # Generate master key for watermark operations
            self.watermark_master_key = secrets.token_bytes(32)
            print("WARNING: Generated new watermark master key. Set WATERMARK_MASTER_KEY in production!")
        else:
            self.watermark_master_key = watermark_key.encode()[:32]
    
    def generate_secure_watermark(
        self,
        content_id: str,
        user_id: str,
        timestamp: datetime = None
    ) -> Dict[str, str]:
        """Generate secure watermark with anti-tampering features."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Create watermark payload
        payload = {
            'content_id': content_id,
            'user_id': user_id,
            'timestamp': timestamp.isoformat(),
            'nonce': secrets.token_hex(16)
        }
        
        # Create HMAC signature for integrity
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hashlib.hmac.new(
            self.watermark_master_key,
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Create the actual watermark
        watermark_data = {
            'payload': base64.b64encode(payload_json.encode()).decode(),
            'signature': signature,
            'version': '1.0'
        }
        
        # Store integrity check
        watermark_id = hashlib.sha256(f"{content_id}{user_id}{timestamp}".encode()).hexdigest()[:16]
        self.watermark_integrity_checks[watermark_id] = {
            'signature': signature,
            'created_at': timestamp.isoformat()
        }
        
        return {
            'watermark_id': watermark_id,
            'watermark_data': base64.b64encode(json.dumps(watermark_data).encode()).decode()
        }
    
    def verify_watermark_integrity(self, watermark_data: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify watermark integrity and extract metadata."""
        try:
            # Decode watermark
            decoded_data = json.loads(base64.b64decode(watermark_data.encode()).decode())
            
            # Extract components
            payload_b64 = decoded_data['payload']
            signature = decoded_data['signature']
            version = decoded_data.get('version', '1.0')
            
            # Decode payload
            payload_json = base64.b64decode(payload_b64.encode()).decode()
            payload = json.loads(payload_json)
            
            # Verify signature
            expected_signature = hashlib.hmac.new(
                self.watermark_master_key,
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not secrets.compare_digest(signature, expected_signature):
                log_security_event(
                    "watermark_tampering_detected",
                    "HIGH",
                    {
                        "content_id": payload.get('content_id'),
                        "user_id": payload.get('user_id')
                    },
                    payload.get('user_id'),
                    None
                )
                return False, {"error": "Watermark signature verification failed"}
            
            # Verify timestamp (not too old or in future)
            watermark_time = datetime.fromisoformat(payload['timestamp'])
            current_time = datetime.utcnow()
            
            if watermark_time > current_time + timedelta(minutes=5):
                return False, {"error": "Watermark timestamp in future"}
            
            if current_time - watermark_time > timedelta(days=3650):  # 10 years
                return False, {"error": "Watermark too old"}
            
            return True, payload
            
        except Exception as e:
            log_security_event(
                "watermark_verification_error",
                "MEDIUM",
                {"error": str(e)},
                None,
                None
            )
            return False, {"error": f"Watermark verification failed: {str(e)}"}
    
    def apply_visual_watermark(
        self,
        image_path: str,
        watermark_text: str,
        opacity: float = 0.3
    ) -> str:
        """Apply visual watermark to image with security considerations."""
        try:
            # Load and validate image
            image = Image.open(image_path)
            
            # Security check: reasonable image dimensions
            if image.width > 8192 or image.height > 8192:
                raise ValueError("Image too large for watermarking")
            
            # Create watermark
            watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
            
            # Add text (simplified - in production use proper font rendering)
            # This would use ImageDraw.Draw(watermark).text() with proper fonts
            
            # Apply watermark
            watermarked = Image.alpha_composite(
                image.convert('RGBA'),
                watermark
            )
            
            # Save with new filename
            output_path = image_path.replace('.', '_watermarked.')
            watermarked.save(output_path, 'PNG')
            
            return output_path
            
        except Exception as e:
            log_security_event(
                "visual_watermark_failed",
                "MEDIUM",
                {"image_path": image_path, "error": str(e)},
                None,
                None
            )
            raise


class SearchAPISecurity:
    """Security measures for search API integrations (Google, Bing)."""
    
    def __init__(self):
        self._setup_api_security()
        self.api_usage_limits = {
            'google': {'daily': 10000, 'hourly': 500},
            'bing': {'daily': 3000, 'hourly': 150}
        }
        self.api_usage_tracking = {}
    
    def _setup_api_security(self):
        """Setup secure storage for API keys."""
        # Encrypt API keys in environment
        self.encrypted_keys = {}
        
        google_key = os.getenv("GOOGLE_API_KEY")
        bing_key = os.getenv("BING_API_KEY")
        
        if google_key:
            self.encrypted_keys['google'] = self._encrypt_api_key(google_key)
        if bing_key:
            self.encrypted_keys['bing'] = self._encrypt_api_key(bing_key)
    
    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage."""
        key_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            settings.SECRET_KEY.encode(),
            b'api_key_salt',
            100000
        )
        cipher = Fernet(base64.urlsafe_b64encode(key_bytes))
        return cipher.encrypt(api_key.encode()).decode()
    
    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use."""
        key_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            settings.SECRET_KEY.encode(),
            b'api_key_salt',
            100000
        )
        cipher = Fernet(base64.urlsafe_b64encode(key_bytes))
        return cipher.decrypt(encrypted_key.encode()).decode()
    
    def get_secure_api_key(self, provider: str) -> Optional[str]:
        """Get decrypted API key with usage tracking."""
        if provider not in self.encrypted_keys:
            return None
        
        # Check usage limits
        if not self._check_api_usage_limits(provider):
            log_security_event(
                "api_usage_limit_exceeded",
                "MEDIUM",
                {"provider": provider},
                None,
                None
            )
            return None
        
        # Track usage
        self._track_api_usage(provider)
        
        # Return decrypted key
        return self._decrypt_api_key(self.encrypted_keys[provider])
    
    def _check_api_usage_limits(self, provider: str) -> bool:
        """Check API usage against limits."""
        limits = self.api_usage_limits.get(provider, {})
        current_time = datetime.utcnow()
        
        # Check daily limit
        daily_key = f"{provider}:{current_time.strftime('%Y-%m-%d')}"
        daily_usage = self.api_usage_tracking.get(daily_key, 0)
        if daily_usage >= limits.get('daily', float('inf')):
            return False
        
        # Check hourly limit
        hourly_key = f"{provider}:{current_time.strftime('%Y-%m-%d-%H')}"
        hourly_usage = self.api_usage_tracking.get(hourly_key, 0)
        if hourly_usage >= limits.get('hourly', float('inf')):
            return False
        
        return True
    
    def _track_api_usage(self, provider: str):
        """Track API usage for rate limiting."""
        current_time = datetime.utcnow()
        
        # Track daily usage
        daily_key = f"{provider}:{current_time.strftime('%Y-%m-%d')}"
        self.api_usage_tracking[daily_key] = self.api_usage_tracking.get(daily_key, 0) + 1
        
        # Track hourly usage
        hourly_key = f"{provider}:{current_time.strftime('%Y-%m-%d-%H')}"
        self.api_usage_tracking[hourly_key] = self.api_usage_tracking.get(hourly_key, 0) + 1
        
        # Clean old tracking data
        self._cleanup_usage_tracking(current_time)
    
    def _cleanup_usage_tracking(self, current_time: datetime):
        """Clean up old usage tracking data."""
        cutoff_time = current_time - timedelta(days=2)
        keys_to_remove = []
        
        for key in self.api_usage_tracking:
            try:
                # Extract date from key
                date_str = key.split(':', 1)[1]
                if len(date_str) == 10:  # Daily format
                    key_date = datetime.strptime(date_str, '%Y-%m-%d')
                else:  # Hourly format
                    key_date = datetime.strptime(date_str, '%Y-%m-%d-%H')
                
                if key_date < cutoff_time:
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.api_usage_tracking[key]
    
    def validate_search_query(self, query: str, provider: str) -> Tuple[bool, str]:
        """Validate search query for security issues."""
        # Check query length
        if len(query) > 500:
            return False, "Search query too long"
        
        # Check for injection attempts
        injection_patterns = [
            r'[<>"\']',  # Potential XSS
            r'(union|select|insert|delete|drop|create|alter)',  # SQL injection
            r'(\||&|;|`|\$)',  # Command injection
            r'(javascript:|data:|file:)',  # Protocol injection
        ]
        
        for pattern in injection_patterns:
            import re
            if re.search(pattern, query, re.IGNORECASE):
                log_security_event(
                    "malicious_search_query",
                    "HIGH",
                    {"query": query, "provider": provider, "pattern": pattern},
                    None,
                    None
                )
                return False, "Potentially malicious search query detected"
        
        return True, "Query validated"


class BrowserExtensionSecurity:
    """Security measures for browser extension."""
    
    def __init__(self):
        self.extension_permissions = [
            'activeTab',
            'storage',
            'contextMenus'
        ]
        self.allowed_origins = [
            'https://*.yourdomain.com/*',
            'https://api.yourdomain.com/*'
        ]
    
    def generate_extension_token(self, user_id: str, extension_id: str) -> str:
        """Generate secure token for browser extension communication."""
        payload = {
            'user_id': user_id,
            'extension_id': extension_id,
            'issued_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    def validate_extension_request(
        self,
        token: str,
        origin: str,
        action: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate request from browser extension."""
        try:
            # Decode and verify token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload['expires_at'])
            if datetime.utcnow() > expires_at:
                return False, {"error": "Token expired"}
            
            # Validate origin
            if not any(origin.startswith(allowed.replace('*', '')) for allowed in self.allowed_origins):
                log_security_event(
                    "unauthorized_extension_origin",
                    "HIGH",
                    {"origin": origin, "action": action},
                    payload.get('user_id'),
                    None
                )
                return False, {"error": "Unauthorized origin"}
            
            return True, payload
            
        except jwt.InvalidTokenError as e:
            log_security_event(
                "invalid_extension_token",
                "MEDIUM",
                {"error": str(e), "action": action},
                None,
                None
            )
            return False, {"error": "Invalid token"}
    
    def get_csp_headers_for_extension(self) -> Dict[str, str]:
        """Get Content Security Policy headers for extension integration."""
        return {
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://extension-api.yourdomain.com; "
                "connect-src 'self' wss://api.yourdomain.com https://api.yourdomain.com; "
                "frame-ancestors 'none'; "
                "object-src 'none';"
            )
        }


# Global instances
ai_model_security = AIModelSecurity()
dmca_data_security = DMCADataSecurity()
watermark_security = WatermarkSecurity()
search_api_security = SearchAPISecurity()
browser_extension_security = BrowserExtensionSecurity()