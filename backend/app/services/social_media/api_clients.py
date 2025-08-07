"""
Social Media API clients for various platforms.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urljoin, quote
from dataclasses import dataclass

import aiohttp
import structlog
from aiohttp import ClientSession, ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry

from app.db.models.social_media import SocialMediaPlatform
from .config import PlatformConfig, SocialMediaSettings
from ..auth.rate_limiter import RateLimiter


logger = structlog.get_logger(__name__)


@dataclass
class ProfileData:
    """Standardized profile data structure."""
    username: str
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    profile_image_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_verified: bool = False
    is_private: bool = False
    url: Optional[str] = None
    created_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Standardized search result structure."""
    profiles: List[ProfileData]
    total_results: int
    has_more: bool = False
    next_cursor: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SocialMediaAPIError(Exception):
    """Base exception for social media API errors."""
    
    def __init__(self, message: str, platform: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.platform = platform
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class RateLimitError(SocialMediaAPIError):
    """Exception raised when API rate limit is exceeded."""
    
    def __init__(self, platform: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {platform}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, platform)


class AuthenticationError(SocialMediaAPIError):
    """Exception raised when API authentication fails."""
    pass


class SocialMediaAPIClient(ABC):
    """Abstract base class for social media API clients."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        self.config = config
        self.settings = settings
        self.platform = config.platform
        self.rate_limiter = RateLimiter(
            max_requests=config.requests_per_minute,
            time_window=60
        )
        self.session: Optional[ClientSession] = None
        self.logger = logger.bind(platform=self.platform.value)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self) -> None:
        """Initialize the API client."""
        timeout = ClientTimeout(total=30, connect=10)
        retry_options = ExponentialRetry(attempts=3, start_timeout=1, max_timeout=10)
        
        self.session = RetryClient(
            timeout=timeout,
            retry_options=retry_options,
            raise_for_status=False
        )
        
        # Set default headers
        headers = {
            "User-Agent": self._get_user_agent(),
            **self.config.required_headers
        }
        
        if hasattr(self.session, '_default_headers'):
            self.session._default_headers.update(headers)
        
        self.logger.info("API client initialized")
        
    async def close(self) -> None:
        """Close the API client and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("API client closed")
    
    def _get_user_agent(self) -> str:
        """Get user agent string for requests."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        return user_agents[0]  # For now, use the first one
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Tuple[Dict, int]:
        """Make API request with rate limiting and error handling."""
        if not self.session:
            await self.initialize()
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Add delay for anti-detection
        if self.config.request_delay_seconds > 0:
            await asyncio.sleep(self.config.request_delay_seconds)
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                response_data = {}
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}
                
                self.logger.debug(
                    "API request completed",
                    method=method,
                    url=url,
                    status=response.status,
                    response_size=len(str(response_data))
                )
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitError(self.platform.value, retry_after)
                elif response.status == 401:
                    raise AuthenticationError("Authentication failed", self.platform.value, response.status, response_data)
                elif response.status >= 400:
                    raise SocialMediaAPIError(
                        f"API request failed: {response.status}",
                        self.platform.value,
                        response.status,
                        response_data
                    )
                
                return response_data, response.status
                
        except aiohttp.ClientError as e:
            self.logger.error("Client error during API request", error=str(e))
            raise SocialMediaAPIError(f"Network error: {str(e)}", self.platform.value)
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform API."""
        pass
    
    @abstractmethod
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get profile information for a username."""
        pass
    
    @abstractmethod
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search for profiles matching the query."""
        pass
    
    async def get_profile_image(self, profile_image_url: str) -> Optional[bytes]:
        """Download profile image."""
        if not profile_image_url or not self.session:
            return None
        
        try:
            async with self.session.get(profile_image_url) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as e:
            self.logger.warning("Failed to download profile image", error=str(e), url=profile_image_url)
        
        return None


class InstagramClient(SocialMediaAPIClient):
    """Instagram API client using Instagram Basic Display API and Graph API."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        super().__init__(config, settings)
        self.app_id = settings.instagram_app_id
        self.app_secret = settings.instagram_app_secret
        self.access_token = settings.instagram_access_token
        
    async def authenticate(self) -> bool:
        """Authenticate with Instagram API."""
        if not self.access_token:
            self.logger.warning("No Instagram access token provided")
            return False
        
        # Test the token by making a simple request
        try:
            url = f"{self.config.api_base_url}/v17.0/me"
            params = {"access_token": self.access_token, "fields": "id,username"}
            
            data, status = await self._make_request("GET", url, params=params)
            
            if status == 200 and "id" in data:
                self.logger.info("Instagram authentication successful", user_id=data.get("id"))
                return True
            else:
                self.logger.error("Instagram authentication failed", response=data)
                return False
                
        except Exception as e:
            self.logger.error("Instagram authentication error", error=str(e))
            return False
    
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get Instagram profile information."""
        if not await self.authenticate():
            return None
        
        try:
            # Instagram Graph API doesn't support username lookup directly
            # We need to use Instagram Basic Display API or scraping
            self.logger.warning("Instagram profile lookup by username not supported in current API version")
            return None
            
        except Exception as e:
            self.logger.error("Failed to get Instagram profile", username=username, error=str(e))
            return None
    
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search Instagram profiles."""
        # Instagram doesn't provide public search API
        self.logger.warning("Instagram profile search not supported via API")
        return SearchResult(profiles=[], total_results=0)


class TwitterClient(SocialMediaAPIClient):
    """Twitter API v2 client."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        super().__init__(config, settings)
        self.bearer_token = settings.twitter_bearer_token
        self.api_key = settings.twitter_api_key
        self.api_secret = settings.twitter_api_secret
        
    async def authenticate(self) -> bool:
        """Authenticate with Twitter API."""
        if not self.bearer_token:
            self.logger.warning("No Twitter bearer token provided")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            url = f"{self.config.api_base_url}/2/users/me"
            
            data, status = await self._make_request("GET", url, headers=headers)
            
            if status == 200 and "data" in data:
                self.logger.info("Twitter authentication successful", user_id=data["data"].get("id"))
                return True
            else:
                self.logger.error("Twitter authentication failed", response=data)
                return False
                
        except Exception as e:
            self.logger.error("Twitter authentication error", error=str(e))
            return False
    
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get Twitter profile information."""
        if not await self.authenticate():
            return None
        
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            url = f"{self.config.api_base_url}/2/users/by/username/{username}"
            params = {
                "user.fields": "id,name,username,description,public_metrics,profile_image_url,verified,protected,created_at"
            }
            
            data, status = await self._make_request("GET", url, params=params, headers=headers)
            
            if status == 200 and "data" in data:
                user_data = data["data"]
                metrics = user_data.get("public_metrics", {})
                
                return ProfileData(
                    username=user_data["username"],
                    user_id=user_data["id"],
                    display_name=user_data.get("name"),
                    bio=user_data.get("description"),
                    follower_count=metrics.get("followers_count"),
                    following_count=metrics.get("following_count"),
                    post_count=metrics.get("tweet_count"),
                    profile_image_url=user_data.get("profile_image_url"),
                    is_verified=user_data.get("verified", False),
                    is_private=user_data.get("protected", False),
                    url=f"https://twitter.com/{username}",
                    created_date=user_data.get("created_at"),
                    metadata=user_data
                )
            else:
                self.logger.warning("Twitter profile not found", username=username, response=data)
                return None
                
        except Exception as e:
            self.logger.error("Failed to get Twitter profile", username=username, error=str(e))
            return None
    
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search Twitter profiles."""
        if not await self.authenticate():
            return SearchResult(profiles=[], total_results=0)
        
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            url = f"{self.config.api_base_url}/2/tweets/search/recent"
            params = {
                "query": f"from:{query} OR @{query}",
                "max_results": min(limit, 100),
                "expansions": "author_id",
                "user.fields": "id,name,username,description,public_metrics,profile_image_url,verified,protected"
            }
            
            data, status = await self._make_request("GET", url, params=params, headers=headers)
            
            profiles = []
            if status == 200 and "includes" in data and "users" in data["includes"]:
                for user_data in data["includes"]["users"]:
                    metrics = user_data.get("public_metrics", {})
                    
                    profile = ProfileData(
                        username=user_data["username"],
                        user_id=user_data["id"],
                        display_name=user_data.get("name"),
                        bio=user_data.get("description"),
                        follower_count=metrics.get("followers_count"),
                        following_count=metrics.get("following_count"),
                        post_count=metrics.get("tweet_count"),
                        profile_image_url=user_data.get("profile_image_url"),
                        is_verified=user_data.get("verified", False),
                        is_private=user_data.get("protected", False),
                        url=f"https://twitter.com/{user_data['username']}",
                        metadata=user_data
                    )
                    profiles.append(profile)
            
            return SearchResult(
                profiles=profiles,
                total_results=len(profiles),
                has_more=False,  # Twitter API doesn't provide this info easily
                metadata=data
            )
            
        except Exception as e:
            self.logger.error("Failed to search Twitter profiles", query=query, error=str(e))
            return SearchResult(profiles=[], total_results=0)


class FacebookClient(SocialMediaAPIClient):
    """Facebook Graph API client."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        super().__init__(config, settings)
        self.app_id = settings.facebook_app_id
        self.app_secret = settings.facebook_app_secret
        self.access_token = settings.facebook_access_token
    
    async def authenticate(self) -> bool:
        """Authenticate with Facebook API."""
        if not self.access_token:
            self.logger.warning("No Facebook access token provided")
            return False
        
        try:
            url = f"{self.config.api_base_url}/v18.0/me"
            params = {"access_token": self.access_token, "fields": "id,name"}
            
            data, status = await self._make_request("GET", url, params=params)
            
            if status == 200 and "id" in data:
                self.logger.info("Facebook authentication successful", user_id=data.get("id"))
                return True
            else:
                self.logger.error("Facebook authentication failed", response=data)
                return False
                
        except Exception as e:
            self.logger.error("Facebook authentication error", error=str(e))
            return False
    
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get Facebook profile information."""
        # Facebook doesn't allow profile lookup by username for privacy reasons
        self.logger.warning("Facebook profile lookup by username not supported")
        return None
    
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search Facebook profiles."""
        # Facebook severely restricts profile search for privacy reasons
        self.logger.warning("Facebook profile search not supported")
        return SearchResult(profiles=[], total_results=0)


class TikTokClient(SocialMediaAPIClient):
    """TikTok API client."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        super().__init__(config, settings)
        self.client_key = settings.tiktok_client_key
        self.client_secret = settings.tiktok_client_secret
        
    async def authenticate(self) -> bool:
        """Authenticate with TikTok API."""
        if not self.client_key or not self.client_secret:
            self.logger.warning("No TikTok credentials provided")
            return False
        
        # TikTok uses OAuth 2.0 - this would require user consent flow
        # For now, just validate credentials exist
        self.logger.info("TikTok credentials found")
        return True
    
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get TikTok profile information."""
        # TikTok API requires user consent and has limited public access
        self.logger.warning("TikTok profile lookup requires user consent flow")
        return None
    
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search TikTok profiles."""
        self.logger.warning("TikTok profile search not supported via API")
        return SearchResult(profiles=[], total_results=0)


class RedditClient(SocialMediaAPIClient):
    """Reddit API client."""
    
    def __init__(self, config: PlatformConfig, settings: SocialMediaSettings):
        super().__init__(config, settings)
        self.client_id = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.user_agent = settings.reddit_user_agent
        self.access_token: Optional[str] = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Reddit API."""
        if not self.client_id or not self.client_secret:
            self.logger.warning("No Reddit credentials provided")
            return False
        
        try:
            # Get application-only access token
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            headers = {"User-Agent": self.user_agent}
            data = {"grant_type": "client_credentials"}
            
            url = "https://www.reddit.com/api/v1/access_token"
            
            if not self.session:
                await self.initialize()
            
            async with self.session.post(url, auth=auth, data=data, headers=headers) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get("access_token")
                    
                    if self.access_token:
                        self.logger.info("Reddit authentication successful")
                        return True
                
                self.logger.error("Reddit authentication failed", status=response.status)
                return False
                
        except Exception as e:
            self.logger.error("Reddit authentication error", error=str(e))
            return False
    
    async def get_profile(self, username: str) -> Optional[ProfileData]:
        """Get Reddit user profile information."""
        if not await self.authenticate():
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
            
            url = f"{self.config.api_base_url}/user/{username}/about"
            data, status = await self._make_request("GET", url, headers=headers)
            
            if status == 200 and "data" in data:
                user_data = data["data"]
                
                return ProfileData(
                    username=user_data["name"],
                    user_id=user_data["id"],
                    display_name=user_data.get("subreddit", {}).get("title"),
                    bio=user_data.get("subreddit", {}).get("public_description"),
                    post_count=user_data.get("link_karma", 0) + user_data.get("comment_karma", 0),
                    profile_image_url=user_data.get("icon_img"),
                    is_verified=user_data.get("verified", False),
                    url=f"https://www.reddit.com/user/{username}",
                    created_date=str(user_data.get("created_utc")),
                    metadata=user_data
                )
            else:
                self.logger.warning("Reddit user not found", username=username, response=data)
                return None
                
        except Exception as e:
            self.logger.error("Failed to get Reddit profile", username=username, error=str(e))
            return None
    
    async def search_profiles(self, query: str, limit: int = 20) -> SearchResult:
        """Search Reddit users."""
        if not await self.authenticate():
            return SearchResult(profiles=[], total_results=0)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent
            }
            
            url = f"{self.config.api_base_url}/search"
            params = {
                "q": f"author:{query}",
                "type": "user",
                "limit": min(limit, 100)
            }
            
            data, status = await self._make_request("GET", url, params=params, headers=headers)
            
            profiles = []
            if status == 200 and "data" in data and "children" in data["data"]:
                for item in data["data"]["children"]:
                    if item["kind"] == "t2":  # User
                        user_data = item["data"]
                        
                        profile = ProfileData(
                            username=user_data["name"],
                            user_id=user_data["id"],
                            profile_image_url=user_data.get("icon_img"),
                            is_verified=user_data.get("verified", False),
                            url=f"https://www.reddit.com/user/{user_data['name']}",
                            created_date=str(user_data.get("created_utc")),
                            metadata=user_data
                        )
                        profiles.append(profile)
            
            return SearchResult(
                profiles=profiles,
                total_results=len(profiles),
                has_more=data.get("data", {}).get("after") is not None if status == 200 else False,
                next_cursor=data.get("data", {}).get("after") if status == 200 else None,
                metadata=data
            )
            
        except Exception as e:
            self.logger.error("Failed to search Reddit profiles", query=query, error=str(e))
            return SearchResult(profiles=[], total_results=0)


# Factory function for creating API clients
def create_api_client(platform: SocialMediaPlatform, config: PlatformConfig, settings: SocialMediaSettings) -> SocialMediaAPIClient:
    """Factory function to create appropriate API client for platform."""
    
    client_map = {
        SocialMediaPlatform.INSTAGRAM: InstagramClient,
        SocialMediaPlatform.TWITTER: TwitterClient,
        SocialMediaPlatform.FACEBOOK: FacebookClient,
        SocialMediaPlatform.TIKTOK: TikTokClient,
        SocialMediaPlatform.REDDIT: RedditClient,
    }
    
    client_class = client_map.get(platform)
    if not client_class:
        raise ValueError(f"No API client available for platform: {platform}")
    
    return client_class(config, settings)