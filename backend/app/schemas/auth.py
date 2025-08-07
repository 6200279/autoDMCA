from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .common import BaseSchema


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    type: str = "access"  # access or refresh


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    remember_me: bool = False


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    accept_terms: bool = Field(..., description="Must accept terms of service")


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class TwoFactorSetupResponse(BaseSchema):
    """2FA setup response."""
    qr_code_url: str
    secret_key: str
    backup_codes: list[str]


class TwoFactorVerifyRequest(BaseModel):
    """2FA verification request."""
    code: str = Field(..., min_length=6, max_length=6)


class TwoFactorLoginRequest(LoginRequest):
    """2FA login request."""
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)