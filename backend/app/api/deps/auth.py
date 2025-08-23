from typing import Optional
import time
import hashlib
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import verify_token, log_security_event
from app.core.config import settings
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth import TokenData
from datetime import datetime

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user with enhanced security checks."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Security: Get client IP for logging
    client_ip = _get_client_ip(request)
    
    try:
        # Security: Add timing attack protection
        start_time = time.time()
        
        # Verify token (includes blacklist checking)
        payload = verify_token(credentials.credentials)
        if payload is None:
            # Log failed authentication attempt
            log_security_event(
                event_type="authentication_failed",
                severity="medium",
                details={"reason": "invalid_token"},
                ip_address=client_ip
            )
            raise credentials_exception
            
        token_type = payload.get("type")
        if token_type != "access":
            log_security_event(
                event_type="authentication_failed",
                severity="medium",
                details={"reason": "invalid_token_type", "type": token_type},
                ip_address=client_ip
            )
            raise credentials_exception
            
        user_id: str = payload.get("sub")
        if user_id is None:
            log_security_event(
                event_type="authentication_failed",
                severity="medium",
                details={"reason": "missing_user_id"},
                ip_address=client_ip
            )
            raise credentials_exception
        
        # Security: Normalize timing to prevent timing attacks
        elapsed = time.time() - start_time
        if elapsed < 0.01:  # Minimum processing time
            time.sleep(0.01 - elapsed)
            
    except HTTPException:
        raise
    except Exception as e:
        log_security_event(
            event_type="authentication_error",
            severity="high",
            details={"error": str(e)},
            ip_address=client_ip
        )
        raise credentials_exception
    
    # SECURITY FIX: Remove mock users for production
    # Mock users are now only available in development/test environments
    if settings.ENVIRONMENT in ["development", "test"] and settings.DEBUG:
        # Limited mock user for development only
        if user_id == "dev_user_1":
            class MockUser:
                def __init__(self):
                    self.id = 1
                    self.email = "dev@localhost"
                    self.full_name = "Development User"
                    self.company = "Development"
                    self.phone = "+1234567890"
                    self.bio = "Development User - Not for Production"
                    self.hashed_password = "dev"
                    self.is_active = True
                    self.is_verified = True
                    self.is_superuser = False  # Never superuser for mock
                    self.created_at = datetime.utcnow()
                    self.updated_at = datetime.utcnow()
                    self.last_login = datetime.utcnow()
                    self.avatar_url = None
            
            log_security_event(
                event_type="mock_user_authenticated",
                severity="info",
                details={"environment": settings.ENVIRONMENT},
                user_id=user_id,
                ip_address=client_ip
            )
            return MockUser()
    
    # Regular database lookup
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            log_security_event(
                event_type="user_not_found",
                severity="medium",
                details={"user_id": user_id},
                ip_address=client_ip
            )
            raise credentials_exception
        
        # Security: Log successful authentication
        log_security_event(
            event_type="user_authenticated",
            severity="info",
            details={"user_id": user_id},
            user_id=str(user.id),
            ip_address=client_ip
        )
        
        return user
        
    except ValueError:
        log_security_event(
            event_type="invalid_user_id",
            severity="medium",
            details={"user_id": user_id},
            ip_address=client_ip
        )
        raise credentials_exception
    except Exception as e:
        log_security_event(
            event_type="database_error",
            severity="high",
            details={"error": str(e), "user_id": user_id},
            ip_address=client_ip
        )
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user with additional security checks."""
    if not current_user.is_active:
        # Security: Log inactive user access attempt
        log_security_event(
            event_type="inactive_user_access",
            severity="medium",
            details={"user_id": str(current_user.id)},
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Account is inactive"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current verified user."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current superuser with security logging."""
    if not current_user.is_superuser:
        # Security: Log privilege escalation attempts
        log_security_event(
            event_type="privilege_escalation_attempt",
            severity="high",
            details={"user_id": str(current_user.id), "email": current_user.email},
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    
    # Security: Log superuser access
    log_security_event(
        event_type="superuser_access",
        severity="info",
        details={"user_id": str(current_user.id)},
        user_id=str(current_user.id)
    )
    
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    client_ip = _get_client_ip(request)
        
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            return None
            
        token_type = payload.get("type")
        if token_type != "access":
            return None
            
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Security: Mock users only in development
        if (settings.ENVIRONMENT in ["development", "test"] and 
            settings.DEBUG and user_id == "dev_user_1"):
            class MockUser:
                def __init__(self):
                    self.id = 1
                    self.email = "dev@localhost"
                    self.full_name = "Development User"
                    self.is_active = True
                    self.is_verified = True
                    self.is_superuser = False
            return MockUser()
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user if user and user.is_active else None
        
    except Exception as e:
        # Security: Log optional auth failures at lower severity
        log_security_event(
            event_type="optional_auth_failed",
            severity="low",
            details={"error": str(e)[:100]},  # Limit error message length
            ip_address=client_ip
        )
        return None


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request headers."""
    # Check for forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in case of multiple proxies
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return getattr(request.client, "host", "unknown")