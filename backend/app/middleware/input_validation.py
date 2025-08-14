"""
Enhanced input validation middleware for comprehensive security protection.

This middleware provides:
- SQL injection prevention
- XSS protection
- Command injection prevention
- Path traversal protection
- Content type validation
- Request size limits
- File upload security
"""

import json
import re
from typing import Dict, Any, Optional, List, Set
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import mimetypes
import hashlib

from app.core.security_config import InputValidator, security_monitor


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Comprehensive input validation middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = 50 * 1024 * 1024,  # 50MB
        max_json_depth: int = 10,
        max_array_length: int = 1000,
        allowed_file_types: Set[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        enable_strict_validation: bool = True
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_json_depth = max_json_depth
        self.max_array_length = max_array_length
        self.max_file_size = max_file_size
        self.enable_strict_validation = enable_strict_validation
        
        # Default allowed file types
        self.allowed_file_types = allowed_file_types or {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/csv',
            'application/json', 'text/xml'
        }
        
        # Sensitive endpoints that require strict validation
        self.sensitive_endpoints = {
            '/api/v1/auth',
            '/api/v1/users',
            '/api/v1/admin',
            '/api/v1/billing',
            '/api/v1/takedowns'
        }
        
        # File upload endpoints
        self.file_upload_endpoints = {
            '/api/v1/users/me/avatar',
            '/api/v1/profiles/*/documents',
            '/api/v1/infringements/*/evidence'
        }
        
        # JSON validation rules
        self.json_validation_rules = {
            'email': self._validate_email_field,
            'password': self._validate_password_field,
            'url': self._validate_url_field,
            'phone': self._validate_phone_field,
            'name': self._validate_name_field,
            'description': self._validate_description_field
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _validate_content_type(self, request: Request) -> bool:
        """Validate request content type."""
        content_type = request.headers.get("Content-Type", "")
        
        # For file uploads
        if "multipart/form-data" in content_type:
            return self._is_file_upload_endpoint(request.url.path)
        
        # For JSON requests
        if request.method in ["POST", "PUT", "PATCH"]:
            if not content_type.startswith("application/json"):
                return False
        
        return True
    
    def _is_file_upload_endpoint(self, path: str) -> bool:
        """Check if the endpoint allows file uploads."""
        for pattern in self.file_upload_endpoints:
            if pattern.replace('*', '').rstrip('/') in path:
                return True
        return False
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if the endpoint is sensitive and requires strict validation."""
        for pattern in self.sensitive_endpoints:
            if path.startswith(pattern):
                return True
        return False
    
    def _validate_json_depth(self, obj: Any, current_depth: int = 0) -> bool:
        """Validate JSON depth to prevent deeply nested objects."""
        if current_depth > self.max_json_depth:
            return False
        
        if isinstance(obj, dict):
            for value in obj.values():
                if not self._validate_json_depth(value, current_depth + 1):
                    return False
        elif isinstance(obj, list):
            if len(obj) > self.max_array_length:
                return False
            for item in obj:
                if not self._validate_json_depth(item, current_depth + 1):
                    return False
        
        return True
    
    def _validate_json_structure(self, data: Dict[str, Any], path: str) -> List[str]:
        """Validate JSON data structure and content."""
        errors = []
        
        # Check JSON depth and array lengths
        if not self._validate_json_depth(data):
            errors.append("JSON structure too complex")
        
        # Validate specific fields based on their names
        for field_name, value in data.items():
            if isinstance(value, str):
                # Apply field-specific validation rules
                if field_name in self.json_validation_rules:
                    field_errors = self.json_validation_rules[field_name](value)
                    errors.extend([f"{field_name}: {error}" for error in field_errors])
                
                # General string validation
                is_valid, error_msg = InputValidator.validate_string(
                    value,
                    max_length=10000,
                    allow_html=field_name in ['description', 'content', 'bio'],
                    check_patterns=self._is_sensitive_endpoint(path)
                )
                
                if not is_valid:
                    errors.append(f"{field_name}: {error_msg}")
        
        return errors
    
    def _validate_email_field(self, email: str) -> List[str]:
        """Validate email field."""
        errors = []
        is_valid, _ = InputValidator.validate_email(email)
        if not is_valid:
            errors.append("Invalid email format")
        return errors
    
    def _validate_password_field(self, password: str) -> List[str]:
        """Validate password field."""
        errors = []
        if len(password) < 8:
            errors.append("Password too short (minimum 8 characters)")
        if len(password) > 128:
            errors.append("Password too long (maximum 128 characters)")
        return errors
    
    def _validate_url_field(self, url: str) -> List[str]:
        """Validate URL field."""
        errors = []
        is_valid, _ = InputValidator.validate_url(url)
        if not is_valid:
            errors.append("Invalid URL format")
        return errors
    
    def _validate_phone_field(self, phone: str) -> List[str]:
        """Validate phone field."""
        errors = []
        # Simple phone validation
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, phone.replace(' ', '').replace('-', '')):
            errors.append("Invalid phone number format")
        return errors
    
    def _validate_name_field(self, name: str) -> List[str]:
        """Validate name field."""
        errors = []
        if len(name) > 100:
            errors.append("Name too long (maximum 100 characters)")
        
        # Check for suspicious characters
        if re.search(r'[<>"\'\&]', name):
            errors.append("Name contains invalid characters")
        
        return errors
    
    def _validate_description_field(self, description: str) -> List[str]:
        """Validate description field."""
        errors = []
        if len(description) > 5000:
            errors.append("Description too long (maximum 5000 characters)")
        
        # Allow HTML but sanitize it
        sanitized = InputValidator.sanitize_html(description)
        if sanitized != description:
            errors.append("Description contains potentially unsafe HTML")
        
        return errors
    
    def _validate_file_upload(self, content_type: str, content_length: int, filename: str = None) -> List[str]:
        """Validate file upload."""
        errors = []
        
        # Check file size
        if content_length > self.max_file_size:
            errors.append(f"File too large (maximum {self.max_file_size // (1024*1024)}MB)")
        
        # Check content type
        if content_type not in self.allowed_file_types:
            errors.append(f"File type not allowed: {content_type}")
        
        # Check filename if provided
        if filename:
            # Check for path traversal attempts
            if '..' in filename or '/' in filename or '\\' in filename:
                errors.append("Invalid filename")
            
            # Check file extension
            if '.' in filename:
                extension = filename.rsplit('.', 1)[1].lower()
                allowed_extensions = {
                    'jpg', 'jpeg', 'png', 'gif', 'webp',
                    'pdf', 'txt', 'csv', 'json', 'xml'
                }
                if extension not in allowed_extensions:
                    errors.append(f"File extension not allowed: {extension}")
            
            # Check for suspicious filenames
            suspicious_patterns = [
                r'(exe|bat|cmd|scr|vbs|js|jar|com|pif)$',
                r'\.php\.|\.asp\.|\.jsp\.',
                r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)'
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, filename.lower()):
                    errors.append("Suspicious filename detected")
                    break
        
        return errors
    
    def _log_validation_failure(self, request: Request, errors: List[str], severity: str = "MEDIUM"):
        """Log input validation failure."""
        security_monitor.log_security_event(
            event_type="input_validation_failure",
            severity=severity,
            details={
                "path": request.url.path,
                "method": request.method,
                "errors": errors,
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type")
            },
            ip_address=self._get_client_ip(request)
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with input validation."""
        
        # Skip validation for certain endpoints
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        validation_errors = []
        
        # Validate content type
        if not self._validate_content_type(request):
            validation_errors.append("Invalid content type")
        
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    validation_errors.append(f"Request too large (maximum {self.max_request_size // (1024*1024)}MB)")
            except ValueError:
                validation_errors.append("Invalid Content-Length header")
        
        # Validate JSON data for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("Content-Type", "")
            
            if content_type.startswith("application/json"):
                try:
                    # Read and parse JSON body
                    body = await request.body()
                    if body:
                        try:
                            json_data = json.loads(body)
                            json_errors = self._validate_json_structure(json_data, request.url.path)
                            validation_errors.extend(json_errors)
                        except json.JSONDecodeError:
                            validation_errors.append("Invalid JSON format")
                        
                        # Recreate the request with the body
                        # Note: This is a simplified approach. In production, you might want to
                        # use a more sophisticated method to preserve the request body.
                        request._body = body
                
                except Exception as e:
                    validation_errors.append(f"Error processing request: {str(e)}")
            
            elif content_type.startswith("multipart/form-data"):
                # Validate file upload
                file_errors = self._validate_file_upload(
                    content_type,
                    int(content_length) if content_length else 0
                )
                validation_errors.extend(file_errors)
        
        # Check for validation errors
        if validation_errors:
            severity = "HIGH" if self._is_sensitive_endpoint(request.url.path) else "MEDIUM"
            self._log_validation_failure(request, validation_errors, severity)
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Input validation failed",
                    "errors": validation_errors if self.enable_strict_validation else ["Invalid input"]
                }
            )
        
        # Process the request
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log unexpected errors
            security_monitor.log_security_event(
                event_type="request_processing_error",
                severity="HIGH",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e)
                },
                ip_address=self._get_client_ip(request)
            )
            raise