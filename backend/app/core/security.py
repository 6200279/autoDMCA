from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import string
import pyotp
from email_validator import validate_email, EmailNotValidError

from app.core.config import settings
from app.core.security_config import (
    jwt_manager, 
    api_key_manager, 
    security_monitor, 
    InputValidator,
    SecurityLevel
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    token_type: str = "access",
    additional_claims: Optional[dict] = None,
    security_level: SecurityLevel = SecurityLevel.MEDIUM
) -> str:
    """Create enhanced JWT access token with additional security features."""
    return jwt_manager.create_access_token(
        subject=subject,
        expires_delta=expires_delta,
        additional_claims=additional_claims,
        security_level=security_level
    )


def create_refresh_token(subject: Union[str, Any], additional_claims: Optional[dict] = None) -> str:
    """Create JWT refresh token."""
    return jwt_manager.create_refresh_token(
        subject=subject,
        additional_claims=additional_claims
    )


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token with blacklist checking."""
    return jwt_manager.verify_token(token)


def blacklist_token(token: str) -> bool:
    """Blacklist a JWT token."""
    return jwt_manager.blacklist_token(token)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not all([has_upper, has_lower, has_digit, has_special]):
        return False, "Password must contain uppercase, lowercase, number, and special character"
    
    return True, "Password is strong"


def generate_password_reset_token() -> str:
    """Generate secure password reset token."""
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """Generate API key."""
    return "ak_" + secrets.token_urlsafe(32)


def validate_email_address(email: str) -> tuple[bool, str]:
    """Validate email address format."""
    try:
        validation = validate_email(email)
        return True, validation.email
    except EmailNotValidError:
        return False, "Invalid email address format"


def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA."""
    return pyotp.random_base32()


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code for 2FA."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=window)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for 2FA."""
    codes = []
    for _ in range(count):
        code = ''.join(secrets.choice(string.digits) for _ in range(8))
        codes.append(f"{code[:4]}-{code[4:]}")
    return codes


def create_email_verification_token(email: str) -> str:
    """Create email verification token."""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "exp": expire,
        "email": email,
        "type": "email_verification",
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_email_token(token: str) -> Optional[str]:
    """Verify email verification token and return email."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("email")
    except JWTError:
        return None


# Enhanced security functions using the new security system

def validate_and_sanitize_input(
    value: str,
    max_length: int = 1000,
    allow_html: bool = False,
    check_patterns: bool = True
) -> tuple[bool, str]:
    """Validate and sanitize user input."""
    return InputValidator.validate_string(
        value=value,
        max_length=max_length,
        allow_html=allow_html,
        check_patterns=check_patterns
    )


def generate_api_key(
    name: str,
    user_id: str,
    permissions: list,
    expires_in_days: Optional[int] = None,
    rate_limit: int = 1000
) -> dict:
    """Generate a new API key."""
    return api_key_manager.generate_api_key(
        name=name,
        user_id=user_id,
        permissions=permissions,
        expires_in_days=expires_in_days,
        rate_limit=rate_limit
    )


def validate_api_key(api_key: str, secret: str) -> Optional[dict]:
    """Validate an API key and secret."""
    return api_key_manager.validate_api_key(api_key, secret)


def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    return api_key_manager.revoke_api_key(api_key)


def log_security_event(
    event_type: str,
    severity: str,
    details: dict,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """Log a security event."""
    security_monitor.log_security_event(
        event_type=event_type,
        severity=severity,
        details=details,
        user_id=user_id,
        ip_address=ip_address
    )


def detect_security_anomalies(user_id: str, ip_address: str) -> list:
    """Detect security anomalies for a user."""
    return security_monitor.detect_anomalies(user_id, ip_address)