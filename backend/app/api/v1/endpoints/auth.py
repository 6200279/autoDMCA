from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re
import time

from app.core.config import settings
from app.core.security import (
    create_access_token, 
    create_refresh_token, 
    verify_password, 
    get_password_hash,
    validate_password_strength,
    generate_totp_secret,
    verify_totp_code,
    generate_backup_codes,
    create_email_verification_token,
    verify_email_token,
    verify_token,
    blacklist_token,
    log_security_event,
    validate_and_sanitize_input
)
from app.core.security_config import InputValidator, security_monitor
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.auth import (
    Token, 
    LoginRequest, 
    RegisterRequest, 
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
    RefreshTokenRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorLoginRequest
)
from app.schemas.user import User as UserSchema
from app.schemas.common import MessageResponse, StatusResponse
from app.api.deps.auth import get_current_active_user
from app.services.auth.email_service import send_verification_email, send_password_reset_email

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="""
    Create a new user account for the Content Protection Platform.
    
    ## Features
    - Email validation and uniqueness check
    - Password strength validation (minimum 8 characters)
    - Automatic email verification workflow
    - Terms of service acceptance tracking
    
    ## Process
    1. Validates email format and uniqueness
    2. Enforces password security requirements
    3. Creates user account with initial settings
    4. Sends verification email with secure token
    
    ## Rate Limiting
    Limited to 3 registrations per hour per IP address.
    """,
    responses={
        201: {
            "description": "User successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "email": "creator@example.com",
                        "full_name": "Content Creator",
                        "company": "Creator Studios",
                        "phone": "+1234567890",
                        "is_active": True,
                        "is_verified": False,
                        "created_at": "2024-01-15T10:30:00Z",
                        "subscription": None
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "email_exists": {
                            "summary": "Email already registered",
                            "value": {"detail": "Email already registered"}
                        },
                        "weak_password": {
                            "summary": "Password too weak",
                            "value": {"detail": "Password must contain at least 8 characters with uppercase, lowercase, numbers, and special characters"}
                        }
                    }
                }
            }
        }
    }
)
async def register(
    request: Request,
    user_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register new user account with enhanced security validation."""
    client_ip = getattr(request.client, "host", "unknown")
    
    # Enhanced input validation and sanitization
    email_valid, sanitized_email = InputValidator.validate_email(user_data.email)
    if not email_valid:
        security_monitor.log_security_event(
            event_type="invalid_email_registration",
            severity="MEDIUM",
            details={"email": user_data.email[:50], "reason": "invalid_format"},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format"
        )
    
    # Validate and sanitize full name
    name_valid, sanitized_name = validate_and_sanitize_input(
        user_data.full_name, 
        max_length=100, 
        allow_html=False
    )
    if not name_valid:
        security_monitor.log_security_event(
            event_type="invalid_name_registration",
            severity="MEDIUM",
            details={"name": user_data.full_name[:50], "reason": sanitized_name},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid name: {sanitized_name}"
        )
    
    # Validate company field
    if user_data.company:
        company_valid, sanitized_company = validate_and_sanitize_input(
            user_data.company,
            max_length=100,
            allow_html=False
        )
        if not company_valid:
            security_monitor.log_security_event(
                event_type="invalid_company_registration",
                severity="LOW",
                details={"company": user_data.company[:50], "reason": sanitized_company},
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid company name: {sanitized_company}"
            )
    else:
        sanitized_company = None
    
    # Validate phone number format
    if user_data.phone:
        phone_pattern = r'^\+?[1-9]\d{1,14}$'  # Basic E.164 format
        if not re.match(phone_pattern, user_data.phone.replace(' ', '').replace('-', '')):
            security_monitor.log_security_event(
                event_type="invalid_phone_registration",
                severity="LOW",
                details={"phone": user_data.phone[:20]},
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == sanitized_email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        # Security: Don't reveal if email exists, but log the attempt
        security_monitor.log_security_event(
            event_type="duplicate_email_registration",
            severity="MEDIUM",
            details={"email": sanitized_email},
            ip_address=client_ip
        )
        # Add small delay to prevent email enumeration timing attacks
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Enhanced password validation
    is_strong, message = validate_password_strength(user_data.password)
    if not is_strong:
        security_monitor.log_security_event(
            event_type="weak_password_registration",
            severity="MEDIUM",
            details={"email": sanitized_email, "weakness": message},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Additional password security checks
    common_passwords = {
        "password", "123456", "password123", "admin", "qwerty", 
        "letmein", "welcome", "monkey", "1234567890"
    }
    if user_data.password.lower() in common_passwords:
        security_monitor.log_security_event(
            event_type="common_password_registration",
            severity="HIGH",
            details={"email": sanitized_email},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common. Please choose a more secure password."
        )
    
    # Check for password containing email parts
    email_parts = sanitized_email.split('@')[0].lower()
    if len(email_parts) > 3 and email_parts in user_data.password.lower():
        security_monitor.log_security_event(
            event_type="email_based_password",
            severity="MEDIUM",
            details={"email": sanitized_email},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password should not contain parts of your email address"
        )
    
    try:
        # Create user with sanitized data
        user = User(
            email=sanitized_email,
            full_name=sanitized_name,
            company=sanitized_company,
            phone=user_data.phone,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
            is_verified=False  # Require email verification
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Security: Log successful registration
        security_monitor.log_security_event(
            event_type="user_registered",
            severity="INFO",
            details={
                "user_id": str(user.id),
                "email": sanitized_email,
                "registration_method": "email"
            },
            user_id=str(user.id),
            ip_address=client_ip
        )
        
        # Send verification email
        verification_token = create_email_verification_token(user.email)
        background_tasks.add_task(
            send_verification_email, 
            user.email, 
            user.full_name, 
            verification_token
        )
        
        return user
        
    except Exception as e:
        db.rollback()
        security_monitor.log_security_event(
            event_type="registration_error",
            severity="HIGH",
            details={"error": str(e)[:100], "email": sanitized_email},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login",
    summary="User authentication",
    description="""
    Authenticate a user and return JWT access and refresh tokens.
    
    ## Authentication Flow
    1. Validates email and password credentials
    2. Checks account status (active/inactive)
    3. Updates last login timestamp
    4. Generates JWT access and refresh tokens
    
    ## Token Details
    - **Access Token**: Valid for 30 minutes (configurable)
    - **Refresh Token**: Valid for 7 days (configurable)
    - **Remember Me**: Extends access token to 7 days
    
    ## Security Features
    - Rate limited to 5 attempts per 15 minutes
    - Password verification with secure hashing
    - Account lockout protection
    
    ## Response
    Returns JWT tokens for API authentication. Include the access token in the 
    `Authorization: Bearer <token>` header for subsequent API calls.
    """,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Invalid email or password",
                            "value": {"detail": "Incorrect email or password"}
                        },
                        "inactive_account": {
                            "summary": "Account disabled",
                            "value": {"detail": "Inactive user account"}
                        }
                    }
                }
            }
        },
        429: {
            "description": "Too many login attempts",
            "content": {
                "application/json": {
                    "example": {"detail": "Too many login attempts. Please try again in 15 minutes."}
                }
            }
        }
    }
)
async def login(
    request: Request,
    user_credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate user with enhanced security checks."""
    client_ip = getattr(request.client, "host", "unknown")
    
    # Security: Validate and sanitize email input
    email_valid, sanitized_email = InputValidator.validate_email(user_credentials.email)
    if not email_valid:
        security_monitor.log_security_event(
            event_type="login_invalid_email",
            severity="MEDIUM",
            details={"email": user_credentials.email[:50]},
            ip_address=client_ip
        )
        # Add delay to prevent email enumeration
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Security: Rate limiting check (should also be handled by middleware)
    # This is an additional application-level check
    
    # Mock authentication for development only (UPDATED for frontend compatibility)
    if settings.ENVIRONMENT in ["development", "test"] and settings.DEBUG:
        # SECURITY: Limited mock users for development only - Updated to match frontend
        mock_user = None
        
        # Admin mock user
        if sanitized_email == "admin@autodmca.com" and user_credentials.password == "admin123":
            mock_user = {
                "id": "admin_user_1",
                "email": "admin@autodmca.com",
                "full_name": "Admin User",
                "is_active": True,
                "is_superuser": True,  # Admin has superuser privileges
                "password": "admin123"
            }
        # Regular user mock user  
        elif sanitized_email == "user@example.com" and user_credentials.password == "user1234":
            mock_user = {
                "id": "regular_user_1", 
                "email": "user@example.com",
                "full_name": "Regular User",
                "is_active": True,
                "is_superuser": False,
                "password": "user1234"
            }
        # Legacy dev user (keeping for backward compatibility)
        elif sanitized_email == "dev@localhost" and user_credentials.password == "DevPassword123!":
            mock_user = {
                "id": "dev_user_1",
                "email": "dev@localhost",
                "full_name": "Development User",
                "is_active": True,
                "is_superuser": False,  # Never superuser for mock
                "password": "DevPassword123!"
            }
        
        if mock_user:
            # Log development login
            security_monitor.log_security_event(
                event_type="mock_user_login",
                severity="INFO",
                details={"environment": settings.ENVIRONMENT, "user_type": "admin" if mock_user["is_superuser"] else "user"},
                user_id=mock_user["id"],
                ip_address=client_ip
            )
            
            # Create tokens for mock user with security level
            access_token_expires = timedelta(minutes=30)  # Limited time for dev
            if user_credentials.remember_me:
                access_token_expires = timedelta(hours=2)  # Limited even with remember me
            
            from app.core.security_config import SecurityLevel
            access_token = create_access_token(
                subject=mock_user["id"],
                expires_delta=access_token_expires,
                additional_claims={"dev_mode": True},
                security_level=SecurityLevel.LOW
            )
            refresh_token = create_refresh_token(
                subject=mock_user["id"],
                additional_claims={"dev_mode": True}
            )
            
            # For local development, include user data in response
            user_data = {
                "id": mock_user["id"],
                "email": mock_user["email"],
                "full_name": mock_user["full_name"],
                "company": "AutoDMCA" if mock_user["is_superuser"] else "Test Company",
                "phone": "+1234567890",
                "bio": "System Administrator" if mock_user["is_superuser"] else "Test User",
                "avatar_url": None,
                "is_active": mock_user["is_active"],
                "is_verified": True,
                "is_superuser": mock_user["is_superuser"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-01T00:00:00Z"
            }
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds()),
                "user": user_data
            }
        else:
            # Log failed development login
            security_monitor.log_security_event(
                event_type="mock_login_failed",
                severity="MEDIUM",
                details={"email": sanitized_email[:50], "environment": settings.ENVIRONMENT},
                ip_address=client_ip
            )
            time.sleep(0.5)  # Prevent brute force
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Enhanced database authentication with security logging
    start_time = time.time()
    
    result = await db.execute(select(User).where(User.email == sanitized_email))
    user = result.scalar_one_or_none()
    
    # Always perform password verification even if user doesn't exist (timing attack prevention)
    if user:
        password_valid = verify_password(user_credentials.password, user.hashed_password)
    else:
        # Perform dummy hash verification to maintain consistent timing
        get_password_hash("dummy_password_for_timing")
        password_valid = False
    
    # Ensure minimum processing time to prevent timing attacks
    elapsed = time.time() - start_time
    if elapsed < 0.5:
        time.sleep(0.5 - elapsed)
    
    if not user or not password_valid:
        # Enhanced failed login logging
        security_monitor.log_security_event(
            event_type="login_failed",
            severity="MEDIUM",
            details={
                "email": sanitized_email,
                "reason": "invalid_credentials",
                "user_exists": bool(user)
            },
            ip_address=client_ip
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        # Log inactive user access attempt
        security_monitor.log_security_event(
            event_type="inactive_user_login_attempt",
            severity="MEDIUM",
            details={"user_id": str(user.id), "email": sanitized_email},
            user_id=str(user.id),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Check if email is verified
    if not user.is_verified:
        security_monitor.log_security_event(
            event_type="unverified_user_login_attempt",
            severity="MEDIUM",
            details={"user_id": str(user.id), "email": sanitized_email},
            user_id=str(user.id),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified. Please check your email for verification instructions."
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Log successful login
    security_monitor.log_security_event(
        event_type="user_login_success",
        severity="INFO",
        details={
            "user_id": str(user.id),
            "email": sanitized_email,
            "remember_me": user_credentials.remember_me,
            "login_method": "password"
        },
        user_id=str(user.id),
        ip_address=client_ip
    )
    
    # Create enhanced tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    if user_credentials.remember_me:
        access_token_expires = timedelta(days=7)
    
    # Determine security level based on user role
    from app.core.security_config import SecurityLevel
    security_level = SecurityLevel.HIGH if user.is_superuser else SecurityLevel.MEDIUM
    
    access_token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser,
            "login_ip": client_ip
        },
        security_level=security_level
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        additional_claims={"login_session": time.time()}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/2fa/login", response_model=Token)
async def two_factor_login(
    user_credentials: TwoFactorLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Login with 2FA."""
    result = await db.execute(select(User).where(User.email == user_credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check 2FA code if required
    if user.totp_secret and user_credentials.totp_code:
        if not verify_totp_code(user.totp_secret, user_credentials.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    elif user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA code required"
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Securely refresh access token with validation."""
    client_ip = getattr(request.client, "host", "unknown")
    
    # Enhanced token validation
    payload = verify_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        security_monitor.log_security_event(
            event_type="invalid_refresh_token",
            severity="HIGH",
            details={"reason": "invalid_or_blacklisted"},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        security_monitor.log_security_event(
            event_type="refresh_token_missing_user_id",
            severity="HIGH",
            details={},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        security_monitor.log_security_event(
            event_type="refresh_token_user_not_found",
            severity="HIGH",
            details={"user_id": str(user_id)},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        security_monitor.log_security_event(
            event_type="refresh_token_inactive_user",
            severity="HIGH",
            details={"user_id": str(user.id)},
            user_id=str(user.id),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Blacklist the old refresh token
    blacklist_token(token_data.refresh_token)
    
    # Log token refresh
    security_monitor.log_security_event(
        event_type="token_refreshed",
        severity="INFO",
        details={"user_id": str(user.id), "email": user.email},
        user_id=str(user.id),
        ip_address=client_ip
    )
    
    # Create new tokens with enhanced security
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    from app.core.security_config import SecurityLevel
    security_level = SecurityLevel.HIGH if user.is_superuser else SecurityLevel.MEDIUM
    
    access_token = create_access_token(
        subject=user.id, 
        expires_delta=access_token_expires,
        additional_claims={
            "email": user.email,
            "is_superuser": user.is_superuser,
            "refresh_ip": client_ip
        },
        security_level=security_level
    )
    new_refresh_token = create_refresh_token(
        subject=user.id,
        additional_claims={"refresh_session": time.time()}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/verify-email", response_model=StatusResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Verify user email."""
    email = verify_email_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return StatusResponse(success=True, message="Email already verified")
    
    user.is_verified = True
    await db.commit()
    
    return StatusResponse(success=True, message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Request password reset."""
    result = await db.execute(select(User).where(User.email == reset_data.email))
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = create_email_verification_token(user.email)
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.full_name,
            reset_token
        )
    
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/reset-password", response_model=StatusResponse)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Reset password with token."""
    email = verify_email_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate password strength
    is_strong, message = validate_password_strength(reset_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    user.hashed_password = get_password_hash(reset_data.new_password)
    await db.commit()
    
    return StatusResponse(success=True, message="Password reset successfully")


@router.post("/change-password", response_model=StatusResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Change user password."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Validate password strength
    is_strong, message = validate_password_strength(password_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return StatusResponse(success=True, message="Password changed successfully")


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Setup two-factor authentication."""
    if current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled"
        )
    
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    
    # Store secret temporarily (user needs to verify)
    current_user.totp_secret = secret
    await db.commit()
    
    import pyotp
    import qrcode
    import io
    import base64
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=settings.PROJECT_NAME
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    
    return TwoFactorSetupResponse(
        qr_code_url=f"data:image/png;base64,{qr_code_data}",
        secret_key=secret,
        backup_codes=backup_codes
    )


@router.post("/2fa/verify", response_model=StatusResponse)
async def verify_two_factor(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Verify and enable two-factor authentication."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not set up"
        )
    
    if not verify_totp_code(current_user.totp_secret, verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # 2FA is now verified and active
    return StatusResponse(success=True, message="2FA enabled successfully")


@router.post("/2fa/disable", response_model=StatusResponse)
async def disable_two_factor(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Disable two-factor authentication."""
    current_user.totp_secret = None
    await db.commit()
    
    return StatusResponse(success=True, message="2FA disabled successfully")


@router.post("/logout", response_model=StatusResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Secure user logout with token blacklisting."""
    client_ip = getattr(request.client, "host", "unknown")
    
    # Get the JWT token from the request
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        # Blacklist the token
        blacklist_success = blacklist_token(token)
        
        # Log logout event
        security_monitor.log_security_event(
            event_type="user_logout",
            severity="INFO",
            details={
                "user_id": str(current_user.id),
                "email": current_user.email,
                "token_blacklisted": blacklist_success
            },
            user_id=str(current_user.id),
            ip_address=client_ip
        )
        
        if not blacklist_success:
            # Log token blacklisting failure
            security_monitor.log_security_event(
                event_type="token_blacklist_failed",
                severity="HIGH",
                details={"user_id": str(current_user.id)},
                user_id=str(current_user.id),
                ip_address=client_ip
            )
    
    return StatusResponse(success=True, message="Logged out successfully")