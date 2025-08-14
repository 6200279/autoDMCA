"""
Social Media Impersonation Detection System
Monitors and detects fake accounts across major platforms
"""
import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urlparse

from app.services.ai.content_matcher import ContentMatcher
from app.services.dmca.takedown_processor import DMCATakedownProcessor
from app.core.config import settings

logger = logging.getLogger(__name__)


class PlatformType(str, Enum):
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    REDDIT = "reddit"
    YOUTUBE = "youtube"


class ImpersonationRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImpersonationProfile:
    """Detected impersonation profile"""
    platform: PlatformType
    profile_url: str
    username: str
    display_name: str
    bio: str
    profile_image_url: Optional[str]
    follower_count: int
    post_count: int
    creation_date: Optional[datetime]
    verification_status: bool
    risk_score: float  # 0.0 to 1.0
    risk_level: ImpersonationRisk
    detected_indicators: List[str]
    confidence: float
    metadata: Dict[str, Any]


class SocialMediaImpersonationDetector:
    """
    Detects fake accounts and impersonation across social media platforms
    PRD: "Social Media & Impersonation Protection"
    """
    
    def __init__(self):
        self.content_matcher = ContentMatcher()
        self.takedown_processor = DMCATakedownProcessor()
        
        # Platform-specific configurations
        self.platform_configs = {
            PlatformType.INSTAGRAM: {
                'base_url': 'https://www.instagram.com',
                'search_url': 'https://www.instagram.com/web/search/topsearch/',
                'profile_pattern': r'instagram\.com/([^/\?]+)',
                'indicators': ['using_photos', 'similar_bio', 'name_variation']
            },
            PlatformType.TWITTER: {
                'base_url': 'https://twitter.com',
                'search_url': 'https://api.twitter.com/2/users/by/username/',
                'profile_pattern': r'twitter\.com/([^/\?]+)',
                'indicators': ['using_photos', 'similar_handle', 'impersonating_content']
            },
            PlatformType.TIKTOK: {
                'base_url': 'https://www.tiktok.com',
                'search_url': 'https://www.tiktok.com/api/search/user/',
                'profile_pattern': r'tiktok\.com/@([^/\?]+)',
                'indicators': ['using_videos', 'similar_username', 'copied_bio']
            },
            PlatformType.FACEBOOK: {
                'base_url': 'https://www.facebook.com',
                'search_url': 'https://graph.facebook.com/search',
                'profile_pattern': r'facebook\.com/([^/\?]+)',
                'indicators': ['using_photos', 'similar_name', 'fake_relationship']
            }
        }
        
        # Rate limiting
        self.request_delays = {
            PlatformType.INSTAGRAM: 2.0,
            PlatformType.TWITTER: 1.0,
            PlatformType.TIKTOK: 1.5,
            PlatformType.FACEBOOK: 2.0
        }
        
    async def scan_for_impersonations(
        self,
        profile_data: Dict[str, Any],
        platforms: List[PlatformType] = None
    ) -> List[ImpersonationProfile]:
        """
        Main entry point for impersonation detection
        PRD: "periodically search major social networks for accounts that use the creator's identity"
        """
        if platforms is None:
            platforms = [
                PlatformType.INSTAGRAM,
                PlatformType.TWITTER,
                PlatformType.TIKTOK,
                PlatformType.FACEBOOK
            ]
            
        all_impersonations = []
        
        for platform in platforms:
            try:
                logger.info(f"Scanning {platform.value} for impersonations of {profile_data.get('username')}")
                
                # Search for potential impersonation accounts
                potential_accounts = await self._search_platform(platform, profile_data)
                
                # Analyze each account for impersonation indicators
                for account in potential_accounts:
                    impersonation = await self._analyze_account_for_impersonation(
                        platform, account, profile_data
                    )
                    
                    if impersonation and impersonation.risk_score > 0.6:
                        all_impersonations.append(impersonation)
                        
                # Rate limiting between platforms
                await asyncio.sleep(self.request_delays.get(platform, 1.0))
                
            except Exception as e:
                logger.error(f"Error scanning {platform.value}: {e}")
                
        # Sort by risk score (highest first)
        all_impersonations.sort(key=lambda x: x.risk_score, reverse=True)
        
        logger.info(f"Found {len(all_impersonations)} potential impersonations")
        return all_impersonations
        
    async def _search_platform(
        self,
        platform: PlatformType,
        profile_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search a platform for accounts matching the profile"""
        username = profile_data.get('username', '')
        display_name = profile_data.get('display_name', '')
        
        search_terms = self._generate_search_variations(username, display_name)
        accounts = []
        
        async with aiohttp.ClientSession() as session:
            for term in search_terms[:5]:  # Limit search terms
                try:
                    platform_accounts = await self._platform_specific_search(
                        session, platform, term
                    )
                    accounts.extend(platform_accounts)
                    
                    # Rate limiting
                    await asyncio.sleep(self.request_delays.get(platform, 1.0))
                    
                except Exception as e:
                    logger.error(f"Search error on {platform.value}: {e}")
                    
        # Deduplicate accounts
        unique_accounts = {}
        for account in accounts:
            key = account.get('username', '') + account.get('profile_url', '')
            if key not in unique_accounts:
                unique_accounts[key] = account
                
        return list(unique_accounts.values())
        
    def _generate_search_variations(
        self,
        username: str,
        display_name: str = ""
    ) -> List[str]:
        """Generate search term variations for finding impersonations"""
        variations = []
        
        if username:
            # Exact username
            variations.append(username)
            
            # Common variations
            variations.append(username.replace('_', ''))  # Remove underscores
            variations.append(username.replace('.', ''))  # Remove dots
            variations.append(username + '_')  # Add underscore
            variations.append(username + '.')  # Add dot
            variations.append(username + 'official')  # Add "official"
            variations.append('real' + username)  # Add "real"
            
            # Number variations
            for i in range(1, 10):
                variations.append(f"{username}{i}")
                variations.append(f"{username}_{i}")
                
        if display_name:
            variations.append(display_name)
            variations.append(display_name.replace(' ', ''))
            variations.append(display_name.replace(' ', '_'))
            
        return list(set(variations))  # Remove duplicates
        
    async def _platform_specific_search(
        self,
        session: aiohttp.ClientSession,
        platform: PlatformType,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Perform platform-specific search"""
        accounts = []
        
        try:
            if platform == PlatformType.INSTAGRAM:
                accounts = await self._search_instagram(session, search_term)
            elif platform == PlatformType.TWITTER:
                accounts = await self._search_twitter(session, search_term)
            elif platform == PlatformType.TIKTOK:
                accounts = await self._search_tiktok(session, search_term)
            elif platform == PlatformType.FACEBOOK:
                accounts = await self._search_facebook(session, search_term)
                
        except Exception as e:
            logger.error(f"Platform search error for {platform.value}: {e}")
            
        return accounts
        
    async def _search_instagram(
        self,
        session: aiohttp.ClientSession,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Search Instagram for accounts"""
        accounts = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Instagram web search (public profiles only)
            search_url = f"https://www.instagram.com/web/search/topsearch/?query={search_term}"
            
            async with session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for user in data.get('users', []):
                        user_data = user.get('user', {})
                        
                        accounts.append({
                            'platform': PlatformType.INSTAGRAM,
                            'username': user_data.get('username', ''),
                            'display_name': user_data.get('full_name', ''),
                            'profile_url': f"https://www.instagram.com/{user_data.get('username', '')}",
                            'profile_image_url': user_data.get('profile_pic_url', ''),
                            'follower_count': user_data.get('follower_count', 0),
                            'verification_status': user_data.get('is_verified', False),
                            'bio': '',  # Would need additional request to get bio
                            'post_count': 0  # Would need additional request
                        })
                        
        except Exception as e:
            logger.error(f"Instagram search error: {e}")
            
        return accounts
        
    async def _search_twitter(
        self,
        session: aiohttp.ClientSession,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Search Twitter for accounts"""
        accounts = []
        
        try:
            # Note: Twitter API requires authentication
            # This is a placeholder implementation
            
            # For production, would use Twitter API v2
            headers = {
                'Authorization': f'Bearer {os.getenv("TWITTER_BEARER_TOKEN", "")}',
                'User-Agent': 'ContentProtectionBot/1.0'
            }
            
            search_url = f"https://api.twitter.com/2/users/by/username/{search_term}"
            
            async with session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    user_data = data.get('data', {})
                    
                    if user_data:
                        accounts.append({
                            'platform': PlatformType.TWITTER,
                            'username': user_data.get('username', ''),
                            'display_name': user_data.get('name', ''),
                            'profile_url': f"https://twitter.com/{user_data.get('username', '')}",
                            'profile_image_url': user_data.get('profile_image_url', ''),
                            'follower_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                            'verification_status': user_data.get('verified', False),
                            'bio': user_data.get('description', ''),
                            'post_count': user_data.get('public_metrics', {}).get('tweet_count', 0)
                        })
                        
        except Exception as e:
            logger.error(f"Twitter search error: {e}")
            
        return accounts
        
    async def _search_tiktok(
        self,
        session: aiohttp.ClientSession,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Search TikTok for accounts"""
        # TikTok search would require web scraping or unofficial APIs
        # This is a placeholder implementation
        return []
        
    async def _search_facebook(
        self,
        session: aiohttp.ClientSession,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """Search Facebook for accounts"""
        # Facebook search would require Graph API access
        # This is a placeholder implementation
        return []
        
    async def _analyze_account_for_impersonation(
        self,
        platform: PlatformType,
        account: Dict[str, Any],
        original_profile: Dict[str, Any]
    ) -> Optional[ImpersonationProfile]:
        """Analyze an account to determine if it's impersonating the original profile"""
        
        risk_score = 0.0
        indicators = []
        confidence = 0.0
        
        original_username = original_profile.get('username', '').lower()
        account_username = account.get('username', '').lower()
        
        # Username similarity check
        username_similarity = self._calculate_username_similarity(
            original_username, account_username
        )
        
        if username_similarity > 0.8:
            risk_score += 0.4
            indicators.append('similar_username')
            
        # Display name similarity
        original_name = original_profile.get('display_name', '').lower()
        account_name = account.get('display_name', '').lower()
        
        if original_name and account_name:
            name_similarity = self._calculate_text_similarity(original_name, account_name)
            if name_similarity > 0.7:
                risk_score += 0.3
                indicators.append('similar_display_name')
                
        # Profile image similarity (if available)
        if account.get('profile_image_url') and original_profile.get('profile_image_url'):
            try:
                image_similarity = await self._compare_profile_images(
                    account['profile_image_url'],
                    original_profile['profile_image_url']
                )
                
                if image_similarity > 0.8:
                    risk_score += 0.5
                    indicators.append('using_original_photos')
                    
            except Exception as e:
                logger.error(f"Error comparing profile images: {e}")
                
        # Bio similarity
        if account.get('bio') and original_profile.get('bio'):
            bio_similarity = self._calculate_text_similarity(
                account['bio'].lower(),
                original_profile['bio'].lower()
            )
            
            if bio_similarity > 0.6:
                risk_score += 0.2
                indicators.append('similar_bio')
                
        # Verification status (fake accounts are rarely verified)
        if not account.get('verification_status', False):
            risk_score += 0.1
            
        # Follower count analysis (suspicious if very low or very high)
        follower_count = account.get('follower_count', 0)
        if follower_count < 100:
            risk_score += 0.1
            indicators.append('low_followers')
        elif follower_count > 100000:  # Suspiciously high for new fake account
            risk_score -= 0.1
            
        # Account age (newer accounts are more suspicious)
        creation_date = account.get('creation_date')
        if creation_date:
            days_old = (datetime.utcnow() - creation_date).days
            if days_old < 30:
                risk_score += 0.2
                indicators.append('new_account')
                
        # Calculate overall confidence
        confidence = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.9:
            risk_level = ImpersonationRisk.CRITICAL
        elif risk_score >= 0.7:
            risk_level = ImpersonationRisk.HIGH
        elif risk_score >= 0.5:
            risk_level = ImpersonationRisk.MEDIUM
        else:
            risk_level = ImpersonationRisk.LOW
            
        # Only return if risk score is significant
        if risk_score < 0.4:
            return None
            
        return ImpersonationProfile(
            platform=platform,
            profile_url=account['profile_url'],
            username=account['username'],
            display_name=account['display_name'],
            bio=account.get('bio', ''),
            profile_image_url=account.get('profile_image_url'),
            follower_count=account.get('follower_count', 0),
            post_count=account.get('post_count', 0),
            creation_date=account.get('creation_date'),
            verification_status=account.get('verification_status', False),
            risk_score=risk_score,
            risk_level=risk_level,
            detected_indicators=indicators,
            confidence=confidence,
            metadata={
                'username_similarity': username_similarity,
                'analysis_date': datetime.utcnow().isoformat()
            }
        )
        
    def _calculate_username_similarity(self, username1: str, username2: str) -> float:
        """Calculate similarity between usernames"""
        if not username1 or not username2:
            return 0.0
            
        # Levenshtein distance
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
                
            if len(s2) == 0:
                return len(s1)
                
            prev_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
                
            return prev_row[-1]
            
        distance = levenshtein_distance(username1.lower(), username2.lower())
        max_len = max(len(username1), len(username2))
        
        if max_len == 0:
            return 1.0
            
        return 1.0 - (distance / max_len)
        
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between text strings"""
        if not text1 or not text2:
            return 0.0
            
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
        
    async def _compare_profile_images(
        self,
        image_url1: str,
        image_url2: str
    ) -> float:
        """Compare two profile images for similarity"""
        try:
            async with aiohttp.ClientSession() as session:
                # Download both images
                async with session.get(image_url1) as response1:
                    if response1.status != 200:
                        return 0.0
                    image1_data = await response1.read()
                    
                async with session.get(image_url2) as response2:
                    if response2.status != 200:
                        return 0.0
                    image2_data = await response2.read()
                    
                # Use content matcher to compare images
                from app.services.ai.content_matcher import ContentMatcher
                matcher = ContentMatcher()
                
                # This would use the image comparison logic from content_matcher
                # For now, returning a placeholder
                return 0.0
                
        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return 0.0
            
    async def report_impersonation(
        self,
        impersonation: ImpersonationProfile,
        original_profile: Dict[str, Any]
    ) -> bool:
        """
        Report an impersonation account to the platform
        PRD: "filing an impersonation report to the platform"
        """
        try:
            if impersonation.platform == PlatformType.INSTAGRAM:
                return await self._report_instagram_impersonation(
                    impersonation, original_profile
                )
            elif impersonation.platform == PlatformType.TWITTER:
                return await self._report_twitter_impersonation(
                    impersonation, original_profile
                )
            # Add other platforms as needed
            
        except Exception as e:
            logger.error(f"Error reporting impersonation: {e}")
            
        return False
        
    async def _report_instagram_impersonation(
        self,
        impersonation: ImpersonationProfile,
        original_profile: Dict[str, Any]
    ) -> bool:
        """Report impersonation to Instagram"""
        # Instagram has a web form for impersonation reports
        # This would integrate with their reporting system
        logger.info(f"Would report Instagram impersonation: {impersonation.profile_url}")
        return True
        
    async def _report_twitter_impersonation(
        self,
        impersonation: ImpersonationProfile,
        original_profile: Dict[str, Any]
    ) -> bool:
        """Report impersonation to Twitter"""
        # Twitter has an API and web form for impersonation reports
        logger.info(f"Would report Twitter impersonation: {impersonation.profile_url}")
        return True


import os