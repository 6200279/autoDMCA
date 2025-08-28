"""
Account Verification System
Implements secure verification to ensure users own the profiles they're claiming

Security Requirements:
- Prevent false claims and abuse
- Verify ownership of social media accounts
- Support multiple verification methods
- Maintain audit trail for legal compliance
"""

import logging
import asyncio
import secrets
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlparse
import re
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.session import get_async_session
from app.services.notifications.alert_system import alert_system

logger = logging.getLogger(__name__)


class VerificationMethod(str, Enum):
    """Available verification methods"""
    POST_VERIFICATION = "post_verification"      # Post a code on the platform
    BIO_VERIFICATION = "bio_verification"        # Add code to profile bio
    EMAIL_VERIFICATION = "email_verification"    # Send from registered email
    FILE_VERIFICATION = "file_verification"      # Upload verification file
    DNS_VERIFICATION = "dns_verification"        # Add DNS TXT record (websites)
    META_TAG_VERIFICATION = "meta_tag_verification"  # Add meta tag (websites)


class VerificationStatus(str, Enum):
    """Verification status options"""
    PENDING = "pending"              # Verification requested, awaiting completion
    IN_PROGRESS = "in_progress"      # User completed step, system checking
    VERIFIED = "verified"            # Successfully verified
    FAILED = "failed"               # Verification failed
    EXPIRED = "expired"             # Verification code/window expired
    REJECTED = "rejected"           # Manually rejected (suspicious activity)


class PlatformType(str, Enum):
    """Supported platform types for verification"""
    ONLYFANS = "onlyfans"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    WEBSITE = "website"
    EMAIL = "email"


@dataclass
class VerificationChallenge:
    """Verification challenge data"""
    challenge_id: str
    user_id: int
    platform: PlatformType
    platform_username: str
    method: VerificationMethod
    verification_code: str
    instructions: str
    status: VerificationStatus
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    metadata: Dict[str, Any] = None


class AccountVerificationService:
    """
    Comprehensive account verification service
    
    Prevents abuse by ensuring users actually own the accounts they claim
    Supports multiple verification methods based on platform capabilities
    """
    
    def __init__(self):
        self.active_challenges: Dict[str, VerificationChallenge] = {}
        self.verification_cache: Dict[str, bool] = {}  # Cache verified accounts
        
        # Platform-specific verification methods
        self.platform_methods = {
            PlatformType.INSTAGRAM: [VerificationMethod.POST_VERIFICATION, VerificationMethod.BIO_VERIFICATION],
            PlatformType.TWITTER: [VerificationMethod.POST_VERIFICATION, VerificationMethod.BIO_VERIFICATION],
            PlatformType.TIKTOK: [VerificationMethod.BIO_VERIFICATION],
            PlatformType.ONLYFANS: [VerificationMethod.BIO_VERIFICATION, VerificationMethod.EMAIL_VERIFICATION],
            PlatformType.REDDIT: [VerificationMethod.POST_VERIFICATION],
            PlatformType.YOUTUBE: [VerificationMethod.BIO_VERIFICATION],
            PlatformType.TWITCH: [VerificationMethod.BIO_VERIFICATION],
            PlatformType.WEBSITE: [VerificationMethod.DNS_VERIFICATION, VerificationMethod.META_TAG_VERIFICATION, VerificationMethod.FILE_VERIFICATION],
            PlatformType.EMAIL: [VerificationMethod.EMAIL_VERIFICATION]
        }
    
    async def start_verification(
        self,
        db: AsyncSession,
        user_id: int,
        platform: PlatformType,
        platform_username: str,
        method: Optional[VerificationMethod] = None
    ) -> Dict[str, Any]:
        """
        Start account verification process for a user
        """
        
        logger.info(f"Starting verification for user {user_id}, platform: {platform}, username: {platform_username}")
        
        try:
            # Validate platform and username
            if not self._validate_platform_username(platform, platform_username):
                return {
                    "success": False,
                    "error": "invalid_username_format",
                    "message": f"Invalid username format for {platform.value}"
                }
            
            # Check if already verified
            cache_key = f"{platform.value}:{platform_username.lower()}"
            if cache_key in self.verification_cache and self.verification_cache[cache_key]:
                return {
                    "success": False,
                    "error": "already_verified",
                    "message": "This account is already verified"
                }
            
            # Check for existing pending verification
            existing_challenge = self._get_active_challenge(user_id, platform, platform_username)
            if existing_challenge and existing_challenge.status == VerificationStatus.PENDING:
                return {
                    "success": False,
                    "error": "verification_pending",
                    "message": "A verification is already in progress for this account",
                    "challenge_id": existing_challenge.challenge_id,
                    "expires_at": existing_challenge.expires_at.isoformat()
                }
            
            # Determine verification method
            available_methods = self.platform_methods.get(platform, [])
            if not available_methods:
                return {
                    "success": False,
                    "error": "platform_not_supported",
                    "message": f"Verification not yet supported for {platform.value}"
                }
            
            if method and method not in available_methods:
                return {
                    "success": False,
                    "error": "method_not_supported",
                    "message": f"Method {method.value} not supported for {platform.value}",
                    "available_methods": [m.value for m in available_methods]
                }
            
            selected_method = method or available_methods[0]  # Default to first available method
            
            # Generate verification challenge
            challenge = await self._generate_verification_challenge(
                user_id, platform, platform_username, selected_method
            )
            
            # Store challenge
            self.active_challenges[challenge.challenge_id] = challenge
            
            # Send instructions to user
            await alert_system.send_alert(
                user_id=user_id,
                alert_type="verification_started",
                title="Account Verification Required",
                message=f"Please complete the verification steps for your {platform.value} account.",
                metadata={
                    "challenge_id": challenge.challenge_id,
                    "platform": platform.value,
                    "username": platform_username,
                    "method": selected_method.value,
                    "instructions": challenge.instructions,
                    "verification_code": challenge.verification_code,
                    "expires_at": challenge.expires_at.isoformat()
                }
            )
            
            logger.info(f"Verification challenge created: {challenge.challenge_id}")
            
            return {
                "success": True,
                "challenge_id": challenge.challenge_id,
                "method": selected_method.value,
                "verification_code": challenge.verification_code,
                "instructions": challenge.instructions,
                "expires_at": challenge.expires_at.isoformat(),
                "available_methods": [m.value for m in available_methods]
            }
            
        except Exception as e:
            logger.error(f"Failed to start verification: {e}")
            return {
                "success": False,
                "error": "verification_start_failed",
                "message": str(e)
            }
    
    async def _generate_verification_challenge(
        self,
        user_id: int,
        platform: PlatformType,
        platform_username: str,
        method: VerificationMethod
    ) -> VerificationChallenge:
        """Generate verification challenge with appropriate instructions"""
        
        challenge_id = f"verify_{secrets.token_urlsafe(16)}"
        verification_code = self._generate_verification_code(method)
        
        # Generate platform-specific instructions
        instructions = self._generate_instructions(platform, platform_username, method, verification_code)
        
        return VerificationChallenge(
            challenge_id=challenge_id,
            user_id=user_id,
            platform=platform,
            platform_username=platform_username,
            method=method,
            verification_code=verification_code,
            instructions=instructions,
            status=VerificationStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),  # 24-hour window
            metadata={}
        )
    
    def _generate_verification_code(self, method: VerificationMethod) -> str:
        """Generate appropriate verification code based on method"""
        
        if method in [VerificationMethod.POST_VERIFICATION, VerificationMethod.BIO_VERIFICATION]:
            # Human-readable code for social media
            return f"AUTODMCA-{secrets.token_urlsafe(8).upper()}"
        elif method == VerificationMethod.DNS_VERIFICATION:
            # DNS TXT record value
            return f"autodmca-verification={secrets.token_urlsafe(16)}"
        elif method == VerificationMethod.META_TAG_VERIFICATION:
            # Meta tag content
            return secrets.token_urlsafe(20)
        elif method == VerificationMethod.FILE_VERIFICATION:
            # File content
            return secrets.token_urlsafe(32)
        else:
            return secrets.token_urlsafe(12)
    
    def _generate_instructions(
        self,
        platform: PlatformType,
        username: str,
        method: VerificationMethod,
        verification_code: str
    ) -> str:
        """Generate platform-specific verification instructions"""
        
        if platform == PlatformType.INSTAGRAM:
            if method == VerificationMethod.POST_VERIFICATION:
                return f"""
To verify your Instagram account @{username}:

1. Create a new post on your Instagram account
2. In the caption, include this exact verification code: {verification_code}
3. You can add other text, but the code must be visible
4. Make sure the post is public (not private)
5. Click "Check Verification" below once posted

The post can be deleted after verification is complete.
                """.strip()
            elif method == VerificationMethod.BIO_VERIFICATION:
                return f"""
To verify your Instagram account @{username}:

1. Go to your Instagram profile
2. Tap "Edit Profile"
3. Add this verification code to your bio: {verification_code}
4. Save your profile
5. Click "Check Verification" below

You can remove the code from your bio after verification is complete.
                """.strip()
        
        elif platform == PlatformType.TWITTER:
            if method == VerificationMethod.POST_VERIFICATION:
                return f"""
To verify your Twitter account @{username}:

1. Create a new tweet from your account
2. Include this exact verification code in the tweet: {verification_code}
3. You can add other text, but the code must be visible
4. Make sure your account is public (not protected)
5. Click "Check Verification" below once tweeted

The tweet can be deleted after verification is complete.
                """.strip()
            elif method == VerificationMethod.BIO_VERIFICATION:
                return f"""
To verify your Twitter account @{username}:

1. Go to your Twitter profile
2. Click "Edit Profile"
3. Add this verification code to your bio: {verification_code}
4. Save your profile
5. Click "Check Verification" below

You can remove the code from your bio after verification is complete.
                """.strip()
        
        elif platform == PlatformType.ONLYFANS:
            if method == VerificationMethod.BIO_VERIFICATION:
                return f"""
To verify your OnlyFans account {username}:

1. Go to your OnlyFans profile settings
2. Add this verification code to your bio/about section: {verification_code}
3. Save your profile
4. Click "Check Verification" below

You can remove the code from your bio after verification is complete.

Note: We only check public profile information. Your content remains private.
                """.strip()
            elif method == VerificationMethod.EMAIL_VERIFICATION:
                return f"""
To verify your OnlyFans account {username}:

1. Send an email from your OnlyFans registered email address
2. Send it to: verify@autodmca.com
3. Subject line: Account Verification - {username}
4. Message body must include: {verification_code}
5. Include your AutoDMCA account email in the message

We'll process your verification within 24 hours.
                """.strip()
        
        elif platform == PlatformType.WEBSITE:
            if method == VerificationMethod.DNS_VERIFICATION:
                return f"""
To verify your website {username}:

1. Add this TXT record to your domain's DNS:
   Name: _autodmca-verification
   Value: {verification_code}
   
2. Wait for DNS propagation (up to 24 hours)
3. Click "Check Verification" below

DNS changes can take time to propagate worldwide.
                """.strip()
            elif method == VerificationMethod.META_TAG_VERIFICATION:
                return f"""
To verify your website {username}:

1. Add this meta tag to your website's <head> section:
   <meta name="autodmca-verification" content="{verification_code}" />
   
2. Upload the updated page to your website
3. Click "Check Verification" below

The meta tag should be on your homepage or the specific page you're claiming.
                """.strip()
        
        return f"Add this verification code to your {platform.value} profile: {verification_code}"
    
    async def check_verification(
        self,
        challenge_id: str
    ) -> Dict[str, Any]:
        """
        Check if verification has been completed
        """
        
        logger.info(f"Checking verification for challenge: {challenge_id}")
        
        try:
            # Get challenge
            if challenge_id not in self.active_challenges:
                return {
                    "success": False,
                    "error": "challenge_not_found",
                    "message": "Verification challenge not found or expired"
                }
            
            challenge = self.active_challenges[challenge_id]
            
            # Check if expired
            if datetime.utcnow() > challenge.expires_at:
                challenge.status = VerificationStatus.EXPIRED
                return {
                    "success": False,
                    "error": "verification_expired",
                    "message": "Verification window has expired. Please start a new verification."
                }
            
            # Check if too many attempts
            if challenge.attempts >= challenge.max_attempts:
                challenge.status = VerificationStatus.FAILED
                return {
                    "success": False,
                    "error": "too_many_attempts",
                    "message": "Maximum verification attempts exceeded. Please start a new verification."
                }
            
            # Update attempt counter
            challenge.attempts += 1
            challenge.status = VerificationStatus.IN_PROGRESS
            
            # Perform verification check based on method
            verification_result = await self._perform_verification_check(challenge)
            
            if verification_result["success"]:
                # Verification successful
                challenge.status = VerificationStatus.VERIFIED
                
                # Cache the verification
                cache_key = f"{challenge.platform.value}:{challenge.platform_username.lower()}"
                self.verification_cache[cache_key] = True
                
                # Send success notification
                await alert_system.send_alert(
                    user_id=challenge.user_id,
                    alert_type="verification_success",
                    title="Account Verification Successful",
                    message=f"Your {challenge.platform.value} account @{challenge.platform_username} has been successfully verified!",
                    metadata={
                        "challenge_id": challenge_id,
                        "platform": challenge.platform.value,
                        "username": challenge.platform_username
                    }
                )
                
                # Clean up challenge
                del self.active_challenges[challenge_id]
                
                logger.info(f"Verification successful for challenge: {challenge_id}")
                
                return {
                    "success": True,
                    "status": "verified",
                    "message": f"Account @{challenge.platform_username} successfully verified!",
                    "platform": challenge.platform.value,
                    "username": challenge.platform_username
                }
            else:
                # Verification failed
                if challenge.attempts >= challenge.max_attempts:
                    challenge.status = VerificationStatus.FAILED
                    
                    # Send failure notification
                    await alert_system.send_alert(
                        user_id=challenge.user_id,
                        alert_type="verification_failed",
                        title="Account Verification Failed",
                        message=f"We couldn't verify your {challenge.platform.value} account. Please check the instructions and try again.",
                        metadata={
                            "challenge_id": challenge_id,
                            "platform": challenge.platform.value,
                            "username": challenge.platform_username,
                            "reason": verification_result.get("reason", "Unknown")
                        }
                    )
                
                return {
                    "success": False,
                    "status": challenge.status.value,
                    "error": "verification_failed",
                    "message": verification_result.get("message", "Verification failed"),
                    "reason": verification_result.get("reason"),
                    "attempts_remaining": challenge.max_attempts - challenge.attempts
                }
                
        except Exception as e:
            logger.error(f"Failed to check verification: {e}")
            return {
                "success": False,
                "error": "verification_check_failed",
                "message": str(e)
            }
    
    async def _perform_verification_check(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """
        Perform the actual verification check based on method and platform
        """
        
        try:
            if challenge.method == VerificationMethod.POST_VERIFICATION:
                return await self._check_post_verification(challenge)
            elif challenge.method == VerificationMethod.BIO_VERIFICATION:
                return await self._check_bio_verification(challenge)
            elif challenge.method == VerificationMethod.DNS_VERIFICATION:
                return await self._check_dns_verification(challenge)
            elif challenge.method == VerificationMethod.META_TAG_VERIFICATION:
                return await self._check_meta_tag_verification(challenge)
            elif challenge.method == VerificationMethod.EMAIL_VERIFICATION:
                return await self._check_email_verification(challenge)
            else:
                return {
                    "success": False,
                    "reason": "unsupported_method",
                    "message": f"Verification method {challenge.method.value} not implemented"
                }
                
        except Exception as e:
            logger.error(f"Verification check failed: {e}")
            return {
                "success": False,
                "reason": "check_error",
                "message": f"Error during verification: {str(e)}"
            }
    
    async def _check_post_verification(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """Check for verification code in recent posts"""
        
        # This would integrate with platform APIs or web scraping
        # For now, mock implementation showing the structure
        
        try:
            if challenge.platform == PlatformType.INSTAGRAM:
                # Would use Instagram Basic Display API or scraping
                posts = await self._fetch_recent_instagram_posts(challenge.platform_username)
            elif challenge.platform == PlatformType.TWITTER:
                # Would use Twitter API v2
                posts = await self._fetch_recent_twitter_posts(challenge.platform_username)
            elif challenge.platform == PlatformType.REDDIT:
                # Would use Reddit API
                posts = await self._fetch_recent_reddit_posts(challenge.platform_username)
            else:
                return {"success": False, "reason": "platform_not_supported"}
            
            # Check if verification code appears in any recent post
            for post in posts:
                if challenge.verification_code in post.get('text', ''):
                    return {"success": True, "found_in": "post"}
            
            return {
                "success": False,
                "reason": "code_not_found",
                "message": f"Verification code not found in recent posts. Make sure the post is public and contains: {challenge.verification_code}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "reason": "api_error",
                "message": f"Could not check posts: {str(e)}"
            }
    
    async def _check_bio_verification(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """Check for verification code in profile bio"""
        
        try:
            # Fetch profile information
            if challenge.platform == PlatformType.INSTAGRAM:
                bio = await self._fetch_instagram_bio(challenge.platform_username)
            elif challenge.platform == PlatformType.TWITTER:
                bio = await self._fetch_twitter_bio(challenge.platform_username)
            elif challenge.platform == PlatformType.ONLYFANS:
                bio = await self._fetch_onlyfans_bio(challenge.platform_username)
            else:
                return {"success": False, "reason": "platform_not_supported"}
            
            if challenge.verification_code in bio:
                return {"success": True, "found_in": "bio"}
            
            return {
                "success": False,
                "reason": "code_not_found",
                "message": f"Verification code not found in profile bio. Please add: {challenge.verification_code}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "reason": "api_error",
                "message": f"Could not check profile: {str(e)}"
            }
    
    async def _check_dns_verification(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """Check DNS TXT record for verification"""
        
        try:
            import dns.resolver
            
            # Query DNS TXT record
            domain = challenge.platform_username
            query_name = f"_autodmca-verification.{domain}"
            
            try:
                answers = dns.resolver.resolve(query_name, 'TXT')
                for answer in answers:
                    txt_record = str(answer).strip('"')
                    if txt_record == challenge.verification_code:
                        return {"success": True, "found_in": "dns"}
            except dns.resolver.NXDOMAIN:
                pass
            except dns.resolver.NoAnswer:
                pass
            
            return {
                "success": False,
                "reason": "dns_record_not_found",
                "message": f"DNS TXT record not found. Please add: {challenge.verification_code}"
            }
            
        except ImportError:
            return {
                "success": False,
                "reason": "dns_check_unavailable",
                "message": "DNS verification not available"
            }
        except Exception as e:
            return {
                "success": False,
                "reason": "dns_error",
                "message": f"DNS check failed: {str(e)}"
            }
    
    async def _check_meta_tag_verification(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """Check website meta tag for verification"""
        
        try:
            url = f"https://{challenge.platform_username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "reason": "website_not_accessible",
                            "message": f"Could not access website: HTTP {response.status}"
                        }
                    
                    html = await response.text()
                    
                    # Look for meta tag
                    meta_pattern = rf'<meta\s+name=["\']autodmca-verification["\']\s+content=["\']({re.escape(challenge.verification_code)})["\']'
                    if re.search(meta_pattern, html, re.IGNORECASE):
                        return {"success": True, "found_in": "meta_tag"}
                    
                    return {
                        "success": False,
                        "reason": "meta_tag_not_found",
                        "message": f"Meta tag not found. Please add: <meta name=\"autodmca-verification\" content=\"{challenge.verification_code}\" />"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "reason": "website_error",
                "message": f"Could not check website: {str(e)}"
            }
    
    async def _check_email_verification(self, challenge: VerificationChallenge) -> Dict[str, Any]:
        """Check email verification (manual process)"""
        
        # Email verification would be handled by a separate email processing system
        # This is a placeholder showing the structure
        
        return {
            "success": False,
            "reason": "manual_review_required",
            "message": "Email verification requires manual review. We'll process your request within 24 hours."
        }
    
    def _validate_platform_username(self, platform: PlatformType, username: str) -> bool:
        """Validate username format for specific platforms"""
        
        if not username or len(username) < 1:
            return False
        
        if platform in [PlatformType.INSTAGRAM, PlatformType.TWITTER, PlatformType.TIKTOK]:
            # Social media usernames: alphanumeric, underscore, dot, 1-30 chars
            return bool(re.match(r'^[a-zA-Z0-9._]{1,30}$', username))
        elif platform == PlatformType.WEBSITE:
            # Domain names
            return bool(re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', username))
        elif platform == PlatformType.EMAIL:
            # Email addresses
            return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', username))
        else:
            return True  # Allow other formats
    
    def _get_active_challenge(
        self, 
        user_id: int, 
        platform: PlatformType, 
        username: str
    ) -> Optional[VerificationChallenge]:
        """Get active challenge for user/platform/username combination"""
        
        for challenge in self.active_challenges.values():
            if (challenge.user_id == user_id and 
                challenge.platform == platform and 
                challenge.platform_username.lower() == username.lower() and
                challenge.status in [VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]):
                return challenge
        
        return None
    
    async def get_verification_status(
        self,
        user_id: int,
        platform: PlatformType,
        username: str
    ) -> Dict[str, Any]:
        """Get verification status for a specific account"""
        
        # Check cache first
        cache_key = f"{platform.value}:{username.lower()}"
        if cache_key in self.verification_cache:
            return {
                "verified": self.verification_cache[cache_key],
                "platform": platform.value,
                "username": username
            }
        
        # Check active challenges
        active_challenge = self._get_active_challenge(user_id, platform, username)
        if active_challenge:
            return {
                "verified": False,
                "status": active_challenge.status.value,
                "challenge_id": active_challenge.challenge_id,
                "expires_at": active_challenge.expires_at.isoformat(),
                "attempts_remaining": active_challenge.max_attempts - active_challenge.attempts
            }
        
        return {
            "verified": False,
            "status": "not_started"
        }
    
    # Mock API methods (would be replaced with real integrations)
    async def _fetch_recent_instagram_posts(self, username: str) -> List[Dict[str, Any]]:
        """Mock: Fetch recent Instagram posts"""
        # Would use Instagram Basic Display API
        return [{"text": "Sample post content"}]
    
    async def _fetch_recent_twitter_posts(self, username: str) -> List[Dict[str, Any]]:
        """Mock: Fetch recent Twitter posts"""
        # Would use Twitter API v2
        return [{"text": "Sample tweet content"}]
    
    async def _fetch_recent_reddit_posts(self, username: str) -> List[Dict[str, Any]]:
        """Mock: Fetch recent Reddit posts"""
        # Would use Reddit API
        return [{"text": "Sample Reddit post"}]
    
    async def _fetch_instagram_bio(self, username: str) -> str:
        """Mock: Fetch Instagram bio"""
        # Would use Instagram Basic Display API
        return "Sample Instagram bio"
    
    async def _fetch_twitter_bio(self, username: str) -> str:
        """Mock: Fetch Twitter bio"""
        # Would use Twitter API v2
        return "Sample Twitter bio"
    
    async def _fetch_onlyfans_bio(self, username: str) -> str:
        """Mock: Fetch OnlyFans bio"""
        # OnlyFans doesn't have public API - would need special handling
        return "Sample OnlyFans bio"


# Global instance
account_verification = AccountVerificationService()


__all__ = [
    'AccountVerificationService',
    'VerificationMethod',
    'VerificationStatus', 
    'PlatformType',
    'VerificationChallenge',
    'account_verification'
]