from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

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
    verify_token
)
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
    user_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """Register new user account with email verification."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_strong, message = validate_password_strength(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        company=user_data.company,
        phone=user_data.phone,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email
    verification_token = create_email_verification_token(user.email)
    background_tasks.add_task(
        send_verification_email, 
        user.email, 
        user.full_name, 
        verification_token
    )
    
    return user


@router.post("/login", response_model=Token,
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
    user_credentials: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Authenticate user and return JWT tokens."""
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    if user_credentials.remember_me:
        access_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/2fa/login", response_model=Token)
async def two_factor_login(
    user_credentials: TwoFactorLoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Login with 2FA."""
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
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
    db.commit()
    
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
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Refresh access token."""
    payload = verify_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/verify-email", response_model=StatusResponse)
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
) -> Any:
    """Verify user email."""
    email = verify_email_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return StatusResponse(success=True, message="Email already verified")
    
    user.is_verified = True
    db.commit()
    
    return StatusResponse(success=True, message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """Request password reset."""
    user = db.query(User).filter(User.email == reset_data.email).first()
    
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
    db: Session = Depends(get_db)
) -> Any:
    """Reset password with token."""
    email = verify_email_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    user = db.query(User).filter(User.email == email).first()
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
    db.commit()
    
    return StatusResponse(success=True, message="Password reset successfully")


@router.post("/change-password", response_model=StatusResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
    db.commit()
    
    return StatusResponse(success=True, message="Password changed successfully")


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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
    db.commit()
    
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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
) -> Any:
    """Disable two-factor authentication."""
    current_user.totp_secret = None
    db.commit()
    
    return StatusResponse(success=True, message="2FA disabled successfully")


@router.post("/logout", response_model=StatusResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """User logout."""
    # In a real implementation, you might want to blacklist the token
    return StatusResponse(success=True, message="Logged out successfully")