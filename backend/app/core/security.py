from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import string
import pyotp
from email_validator import validate_email, EmailNotValidError

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    token_type: str = "access"
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire, 
        "sub": str(subject),
        "type": token_type,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


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