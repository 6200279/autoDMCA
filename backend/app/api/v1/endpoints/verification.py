"""
Account Verification API Endpoints
Provides endpoints for users to verify ownership of their social media accounts

Security Features:
- Multiple verification methods per platform
- Time-limited verification challenges
- Attempt limiting to prevent abuse
- Comprehensive audit logging
"""

import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator

from app.db.session import get_async_session
from app.db.models.user import User
from app.api.deps.auth import get_current_verified_user
from app.services.verification.account_verification import (
    account_verification,
    VerificationMethod,
    PlatformType
)

logger = logging.getLogger(__name__)
router = APIRouter()


class StartVerificationRequest(BaseModel):
    """Request to start account verification"""
    platform: PlatformType
    platform_username: str
    method: Optional[VerificationMethod] = None
    
    @validator('platform_username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Platform username is required')
        return v.strip()


class StartVerificationResponse(BaseModel):
    """Response when starting verification"""
    success: bool
    challenge_id: Optional[str] = None
    method: Optional[str] = None
    verification_code: Optional[str] = None
    instructions: Optional[str] = None
    expires_at: Optional[str] = None
    available_methods: List[str] = []
    error: Optional[str] = None
    message: Optional[str] = None


class CheckVerificationResponse(BaseModel):
    """Response when checking verification"""
    success: bool
    status: Optional[str] = None
    platform: Optional[str] = None
    username: Optional[str] = None
    attempts_remaining: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    reason: Optional[str] = None


class VerificationStatusResponse(BaseModel):
    """Response for verification status check"""
    verified: bool
    platform: str
    username: str
    status: Optional[str] = None
    challenge_id: Optional[str] = None
    expires_at: Optional[str] = None
    attempts_remaining: Optional[int] = None


class PlatformMethodsResponse(BaseModel):
    """Response listing available verification methods for platforms"""
    platform: str
    available_methods: List[str]
    descriptions: dict


@router.post("/start", response_model=StartVerificationResponse)
async def start_verification(
    request: StartVerificationRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Start account verification process
    
    This endpoint initiates the verification process for a social media account.
    Users must prove they own the account by completing platform-specific challenges.
    """
    
    logger.info(f"Starting verification for user {current_user.id}: {request.platform.value}@{request.platform_username}")
    
    try:
        result = await account_verification.start_verification(
            db=db,
            user_id=current_user.id,
            platform=request.platform,
            platform_username=request.platform_username,
            method=request.method
        )
        
        if not result["success"]:
            # Handle specific error cases
            if result.get("error") == "already_verified":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": result["error"],
                        "message": result["message"]
                    }
                )
            elif result.get("error") == "verification_pending":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": result["error"],
                        "message": result["message"],
                        "challenge_id": result.get("challenge_id"),
                        "expires_at": result.get("expires_at")
                    }
                )
            elif result.get("error") in ["invalid_username_format", "platform_not_supported", "method_not_supported"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": result["error"],
                        "message": result["message"],
                        "available_methods": result.get("available_methods", [])
                    }
                )
        
        return StartVerificationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start verification for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "verification_start_failed",
                "message": "Failed to start verification process. Please try again."
            }
        )


@router.post("/check/{challenge_id}", response_model=CheckVerificationResponse)
async def check_verification(
    challenge_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Check if verification challenge has been completed
    
    This endpoint checks if the user has completed the required verification steps
    (posting code, updating bio, etc.) and validates the verification.
    """
    
    logger.info(f"Checking verification for user {current_user.id}, challenge: {challenge_id}")
    
    try:
        result = await account_verification.check_verification(challenge_id)
        
        if not result["success"]:
            # Handle specific error cases
            if result.get("error") == "challenge_not_found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": result["error"],
                        "message": result["message"]
                    }
                )
            elif result.get("error") == "verification_expired":
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail={
                        "error": result["error"],
                        "message": result["message"]
                    }
                )
            elif result.get("error") == "too_many_attempts":
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": result["error"],
                        "message": result["message"]
                    }
                )
        
        return CheckVerificationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check verification for challenge {challenge_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "verification_check_failed",
                "message": "Failed to check verification status. Please try again."
            }
        )


@router.get("/status/{platform}/{username}", response_model=VerificationStatusResponse)
async def get_verification_status(
    platform: PlatformType,
    username: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get verification status for a specific account
    
    Returns the current verification status for a platform/username combination.
    """
    
    logger.info(f"Getting verification status for user {current_user.id}: {platform.value}@{username}")
    
    try:
        result = await account_verification.get_verification_status(
            user_id=current_user.id,
            platform=platform,
            username=username
        )
        
        return VerificationStatusResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to get verification status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "status_check_failed",
                "message": "Failed to check verification status."
            }
        )


@router.get("/methods/{platform}", response_model=PlatformMethodsResponse)
async def get_platform_verification_methods(
    platform: PlatformType,
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Get available verification methods for a specific platform
    
    Returns the list of verification methods supported for the given platform
    along with descriptions of each method.
    """
    
    logger.info(f"Getting verification methods for platform: {platform.value}")
    
    try:
        # Get methods from verification service
        available_methods = account_verification.platform_methods.get(platform, [])
        
        # Method descriptions
        method_descriptions = {
            VerificationMethod.POST_VERIFICATION.value: "Create a public post containing a verification code",
            VerificationMethod.BIO_VERIFICATION.value: "Add a verification code to your profile bio/about section",
            VerificationMethod.EMAIL_VERIFICATION.value: "Send verification email from your registered account email",
            VerificationMethod.FILE_VERIFICATION.value: "Upload a verification file to your website",
            VerificationMethod.DNS_VERIFICATION.value: "Add a DNS TXT record to your domain",
            VerificationMethod.META_TAG_VERIFICATION.value: "Add a meta tag to your website's HTML"
        }
        
        return PlatformMethodsResponse(
            platform=platform.value,
            available_methods=[method.value for method in available_methods],
            descriptions={
                method.value: method_descriptions[method.value] 
                for method in available_methods 
                if method.value in method_descriptions
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get platform methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "methods_fetch_failed",
                "message": "Failed to get verification methods."
            }
        )


@router.get("/platforms")
async def get_supported_platforms(
    current_user: User = Depends(get_current_verified_user)
) -> Any:
    """
    Get list of all supported platforms for verification
    
    Returns information about all platforms that support account verification.
    """
    
    try:
        platforms_info = []
        
        for platform in PlatformType:
            methods = account_verification.platform_methods.get(platform, [])
            
            platform_info = {
                "platform": platform.value,
                "display_name": platform.value.replace("_", " ").title(),
                "supported": len(methods) > 0,
                "methods_count": len(methods),
                "available_methods": [method.value for method in methods]
            }
            
            # Add platform-specific information
            if platform == PlatformType.INSTAGRAM:
                platform_info["description"] = "Verify your Instagram account ownership"
                platform_info["username_format"] = "@username (without @)"
            elif platform == PlatformType.TWITTER:
                platform_info["description"] = "Verify your Twitter account ownership"
                platform_info["username_format"] = "@username (without @)"
            elif platform == PlatformType.ONLYFANS:
                platform_info["description"] = "Verify your OnlyFans account ownership"
                platform_info["username_format"] = "username or profile URL"
            elif platform == PlatformType.WEBSITE:
                platform_info["description"] = "Verify ownership of your website or domain"
                platform_info["username_format"] = "domain.com"
            elif platform == PlatformType.EMAIL:
                platform_info["description"] = "Verify email address ownership"
                platform_info["username_format"] = "email@domain.com"
            
            platforms_info.append(platform_info)
        
        return {
            "supported_platforms": platforms_info,
            "total_platforms": len(platforms_info),
            "active_platforms": len([p for p in platforms_info if p["supported"]])
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "platforms_fetch_failed",
                "message": "Failed to get supported platforms."
            }
        )


@router.delete("/cancel/{challenge_id}")
async def cancel_verification(
    challenge_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Cancel an active verification challenge
    
    Cancels a verification challenge and cleans up associated resources.
    """
    
    logger.info(f"Canceling verification challenge {challenge_id} for user {current_user.id}")
    
    try:
        # Check if challenge exists and belongs to user
        if challenge_id not in account_verification.active_challenges:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "challenge_not_found",
                    "message": "Verification challenge not found."
                }
            )
        
        challenge = account_verification.active_challenges[challenge_id]
        
        # Verify ownership
        if challenge.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "access_denied",
                    "message": "You can only cancel your own verification challenges."
                }
            )
        
        # Cancel the challenge
        del account_verification.active_challenges[challenge_id]
        
        logger.info(f"Verification challenge {challenge_id} canceled")
        
        return {
            "success": True,
            "message": "Verification challenge canceled successfully."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel verification challenge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "cancellation_failed",
                "message": "Failed to cancel verification challenge."
            }
        )


@router.get("/history")
async def get_verification_history(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """
    Get user's verification history
    
    Returns a list of all verification attempts by the user.
    """
    
    logger.info(f"Getting verification history for user {current_user.id}")
    
    try:
        # In production, this would query the database
        # For now, return cached verifications and active challenges
        
        verified_accounts = []
        active_challenges = []
        
        # Get verified accounts from cache
        for cache_key, is_verified in account_verification.verification_cache.items():
            if is_verified:
                platform, username = cache_key.split(':', 1)
                verified_accounts.append({
                    "platform": platform,
                    "username": username,
                    "verified": True,
                    "verified_at": None  # Would be stored in database
                })
        
        # Get active challenges for this user
        for challenge in account_verification.active_challenges.values():
            if challenge.user_id == current_user.id:
                active_challenges.append({
                    "challenge_id": challenge.challenge_id,
                    "platform": challenge.platform.value,
                    "username": challenge.platform_username,
                    "method": challenge.method.value,
                    "status": challenge.status.value,
                    "created_at": challenge.created_at.isoformat(),
                    "expires_at": challenge.expires_at.isoformat(),
                    "attempts": challenge.attempts,
                    "max_attempts": challenge.max_attempts
                })
        
        return {
            "verified_accounts": verified_accounts,
            "active_challenges": active_challenges,
            "total_verified": len(verified_accounts),
            "total_pending": len(active_challenges)
        }
        
    except Exception as e:
        logger.error(f"Failed to get verification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "history_fetch_failed",
                "message": "Failed to get verification history."
            }
        )


__all__ = ['router']