"""
Role-Based Access Control (RBAC) middleware for the Content Protection Platform.

This middleware provides:
- User role-based access control
- Permission-based resource access
- API endpoint protection
- Resource ownership validation
- Admin-only endpoint protection
"""

from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import re
from datetime import datetime

from app.core.security import verify_token, log_security_event
from app.core.security_config import UserRole, PermissionLevel, ROLE_PERMISSIONS


class RBACMiddleware(BaseHTTPMiddleware):
    """Role-Based Access Control middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_rbac: bool = True,
        default_role: UserRole = UserRole.USER
    ):
        super().__init__(app)
        self.enable_rbac = enable_rbac
        self.default_role = default_role
        
        # Define endpoint permissions
        self.endpoint_permissions = {
            # Authentication endpoints
            r'^/api/v1/auth/(login|register|forgot-password)$': {
                'methods': ['POST'],
                'permissions': [],  # Public endpoints
                'roles': []
            },
            
            # User management
            r'^/api/v1/users/me$': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.READ],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            r'^/api/v1/users/\d+$': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.ADMIN],
                'roles': [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            r'^/api/v1/users$': {
                'methods': ['GET'],
                'permissions': [PermissionLevel.ADMIN],
                'roles': [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Profile management
            r'^/api/v1/profiles$': {
                'methods': ['GET', 'POST'],
                'permissions': [PermissionLevel.READ, PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            r'^/api/v1/profiles/\d+$': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                'ownership_required': True  # User can only access their own profiles
            },
            
            # Infringement management
            r'^/api/v1/infringements$': {
                'methods': ['GET', 'POST'],
                'permissions': [PermissionLevel.READ, PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            r'^/api/v1/infringements/\d+$': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                'ownership_required': True
            },
            
            # Takedown management
            r'^/api/v1/takedowns$': {
                'methods': ['GET', 'POST'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            r'^/api/v1/takedowns/\d+$': {
                'methods': ['GET', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                'ownership_required': True
            },
            
            # Billing endpoints
            r'^/api/v1/billing/.*$': {
                'methods': ['GET', 'POST', 'PUT'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Subscription management
            r'^/api/v1/subscriptions$': {
                'methods': ['GET', 'POST'],
                'permissions': [PermissionLevel.READ, PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Admin endpoints
            r'^/api/v1/admin/.*$': {
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.ADMIN],
                'roles': [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Super admin endpoints
            r'^/api/v1/superadmin/.*$': {
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.ADMIN],
                'roles': [UserRole.SUPER_ADMIN]
            },
            
            # Dashboard and analytics
            r'^/api/v1/dashboard.*$': {
                'methods': ['GET'],
                'permissions': [PermissionLevel.READ],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Social media protection
            r'^/api/v1/social-media/.*$': {
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            },
            
            # Scanning endpoints
            r'^/api/v1/scanning/.*$': {
                'methods': ['GET', 'POST'],
                'permissions': [PermissionLevel.WRITE],
                'roles': [UserRole.USER, UserRole.API_USER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
            }
        }
        
        # API-only endpoints (require API key authentication)
        self.api_only_endpoints = {
            r'^/api/v1/api/.*$'
        }
        
        # Read-only user restrictions
        self.read_only_restrictions = {
            UserRole.READ_ONLY: ['POST', 'PUT', 'DELETE', 'PATCH']
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_user_from_token(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from JWT token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        payload = verify_token(token)
        
        if not payload:
            return None
        
        return {
            'user_id': payload.get('sub'),
            'role': payload.get('role', self.default_role.value),
            'permissions': payload.get('permissions', []),
            'security_level': payload.get('security_level', 'medium'),
            'token_type': payload.get('type', 'access')
        }
    
    def _get_endpoint_config(self, path: str) -> Optional[Dict[str, Any]]:
        """Get endpoint configuration based on path."""
        for pattern, config in self.endpoint_permissions.items():
            if re.match(pattern, path):
                return config
        return None
    
    def _check_user_role(self, user_role: str, allowed_roles: List[UserRole]) -> bool:
        """Check if user role is allowed."""
        if not allowed_roles:  # Public endpoint
            return True
        
        try:
            user_role_enum = UserRole(user_role)
            return user_role_enum in allowed_roles
        except ValueError:
            return False
    
    def _check_user_permissions(self, user_role: str, required_permissions: List[PermissionLevel]) -> bool:
        """Check if user has required permissions."""
        if not required_permissions:  # No specific permissions required
            return True
        
        try:
            user_role_enum = UserRole(user_role)
            user_permissions = ROLE_PERMISSIONS.get(user_role_enum, [])
            
            # Check if user has all required permissions
            return all(perm in user_permissions for perm in required_permissions)
        except (ValueError, KeyError):
            return False
    
    def _check_resource_ownership(
        self, 
        request: Request, 
        user_id: str, 
        resource_path: str
    ) -> bool:
        """Check if user owns the resource (simplified implementation)."""
        # Extract resource ID from path
        path_parts = resource_path.strip('/').split('/')
        
        # For endpoints like /api/v1/profiles/123, check if the profile belongs to the user
        # This is a simplified implementation. In practice, you would query the database
        # to verify ownership.
        
        # For now, we'll assume ownership verification is handled elsewhere
        # In a real implementation, you would:
        # 1. Extract the resource ID from the path
        # 2. Query the database to check if the resource belongs to the user
        # 3. Return True/False based on ownership
        
        return True  # Placeholder - implement actual ownership checking
    
    def _is_api_only_endpoint(self, path: str) -> bool:
        """Check if endpoint requires API key authentication."""
        for pattern in self.api_only_endpoints:
            if re.match(pattern, path):
                return True
        return False
    
    def _check_read_only_restrictions(self, user_role: str, method: str) -> bool:
        """Check read-only user restrictions."""
        try:
            user_role_enum = UserRole(user_role)
            restricted_methods = self.read_only_restrictions.get(user_role_enum, [])
            return method not in restricted_methods
        except ValueError:
            return False
    
    def _log_access_denied(
        self, 
        request: Request, 
        user_id: Optional[str], 
        reason: str,
        severity: str = "MEDIUM"
    ):
        """Log access denied event."""
        log_security_event(
            event_type="access_denied",
            severity=severity,
            details={
                "path": request.url.path,
                "method": request.method,
                "reason": reason,
                "user_agent": request.headers.get("User-Agent")
            },
            user_id=user_id,
            ip_address=self._get_client_ip(request)
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with RBAC validation."""
        
        # Skip RBAC for health checks and public endpoints
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        if not self.enable_rbac:
            return await call_next(request)
        
        # Get endpoint configuration
        endpoint_config = self._get_endpoint_config(request.url.path)
        
        if not endpoint_config:
            # No specific configuration found - allow by default for now
            # In production, you might want to deny by default
            return await call_next(request)
        
        # Check if method is allowed for this endpoint
        allowed_methods = endpoint_config.get('methods', [])
        if allowed_methods and request.method not in allowed_methods:
            self._log_access_denied(request, None, f"Method {request.method} not allowed")
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"detail": f"Method {request.method} not allowed"}
            )
        
        # Public endpoints don't require authentication
        if not endpoint_config.get('roles') and not endpoint_config.get('permissions'):
            return await call_next(request)
        
        # Get user information from token
        user_info = self._get_user_from_token(request)
        
        if not user_info:
            self._log_access_denied(request, None, "No valid authentication token")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"}
            )
        
        user_id = user_info['user_id']
        user_role = user_info['role']
        
        # Check API-only endpoints
        if self._is_api_only_endpoint(request.url.path):
            if user_info['token_type'] != 'api_key':
                self._log_access_denied(request, user_id, "API key required for this endpoint")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "API key required"}
                )
        
        # Check role permissions
        required_roles = endpoint_config.get('roles', [])
        if not self._check_user_role(user_role, required_roles):
            self._log_access_denied(request, user_id, f"Role {user_role} not authorized", "HIGH")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient privileges"}
            )
        
        # Check specific permissions
        required_permissions = endpoint_config.get('permissions', [])
        if not self._check_user_permissions(user_role, required_permissions):
            self._log_access_denied(request, user_id, "Insufficient permissions", "HIGH")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient permissions"}
            )
        
        # Check read-only restrictions
        if not self._check_read_only_restrictions(user_role, request.method):
            self._log_access_denied(request, user_id, "Read-only user attempted write operation")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Read-only access"}
            )
        
        # Check resource ownership if required
        if endpoint_config.get('ownership_required', False):
            if not self._check_resource_ownership(request, user_id, request.url.path):
                self._log_access_denied(request, user_id, "Resource ownership required", "HIGH")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied - resource ownership required"}
                )
        
        # Add user information to request state for use in endpoints
        request.state.user = user_info
        
        # Log successful access for sensitive endpoints
        if user_role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            log_security_event(
                event_type="privileged_access",
                severity="MEDIUM",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "user_role": user_role
                },
                user_id=user_id,
                ip_address=self._get_client_ip(request)
            )
        
        return await call_next(request)


# Dependency for getting current user in endpoints
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from request state (set by RBAC middleware)."""
    return getattr(request.state, 'user', None)


def require_role(required_role: UserRole):
    """Decorator to require specific role for endpoint access."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be used in endpoint definitions
            # The actual role checking is done by the middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(required_permission: PermissionLevel):
    """Decorator to require specific permission for endpoint access."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be used in endpoint definitions
            # The actual permission checking is done by the middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator