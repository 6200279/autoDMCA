"""
Configuration management for social media monitoring system.
"""

import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import structlog
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings, validator

from app.db.models.social_media import SocialMediaPlatform


logger = structlog.get_logger(__name__)


class UserAgentRotation(str, Enum):
    """User agent rotation strategies."""
    DISABLED = "disabled"
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    SMART = "smart"  # Based on platform requirements


class ProxyStrategy(str, Enum):
    """Proxy usage strategies."""
    DISABLED = "disabled"
    REQUIRED = "required"
    OPTIONAL = "optional"
    PLATFORM_SPECIFIC = "platform_specific"


class SocialMediaSettings(BaseSettings):
    """Environment-based configuration settings for social media monitoring."""
    
    # Database
    database_url: str = "postgresql://localhost/autodmca"
    redis_url: str = "redis://localhost:6379/1"  # Different DB from main scanner
    
    # API Keys - Instagram
    instagram_app_id: Optional[str] = None
    instagram_app_secret: Optional[str] = None
    instagram_access_token: Optional[str] = None
    
    # API Keys - Twitter/X
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    
    # API Keys - Facebook
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_access_token: Optional[str] = None
    
    # API Keys - TikTok
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    
    # API Keys - Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "AutoDMCA/1.0"
    
    # Rate Limiting - Global
    global_requests_per_minute: int = 300
    global_requests_per_hour: int = 10000
    concurrent_requests: int = 20
    
    # Rate Limiting - Platform Specific
    instagram_requests_per_hour: int = 200
    twitter_requests_per_minute: int = 300
    facebook_requests_per_hour: int = 600
    tiktok_requests_per_minute: int = 100
    reddit_requests_per_minute: int = 60
    
    # Anti-Detection Settings
    user_agent_rotation: UserAgentRotation = UserAgentRotation.SMART
    proxy_strategy: ProxyStrategy = ProxyStrategy.PLATFORM_SPECIFIC
    request_delay_min: float = 1.0
    request_delay_max: float = 5.0
    session_rotation_interval: int = 1800  # 30 minutes
    
    # Proxy Configuration
    proxy_providers: List[str] = field(default_factory=lambda: ["rotating_proxies", "free_proxies"])
    proxy_rotation_interval: int = 600  # 10 minutes
    proxy_timeout_seconds: int = 30
    max_proxy_failures: int = 3
    
    # Face Recognition Settings
    face_recognition_tolerance: float = 0.6
    face_detection_model: str = "hog"  # or "cnn"
    max_faces_per_image: int = 10
    face_encoding_dimensions: int = 128
    
    # Image Processing
    max_image_size_mb: int = 10
    supported_image_formats: Set[str] = field(
        default_factory=lambda: {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".avif"}
    )
    image_similarity_threshold: float = 0.85
    
    # Profile Analysis
    profile_similarity_threshold: float = 0.75
    username_similarity_threshold: float = 0.8
    bio_similarity_threshold: float = 0.7
    content_similarity_threshold: float = 0.8
    
    # Monitoring Intervals
    default_check_interval_minutes: int = 60
    priority_check_interval_minutes: int = 15
    low_priority_check_interval_hours: int = 4
    
    # Storage Settings
    screenshot_storage_path: str = "/tmp/autodmca/screenshots"
    profile_images_storage_path: str = "/tmp/autodmca/profile_images"
    max_storage_size_gb: int = 5
    cleanup_files_older_than_days: int = 7
    
    # Detection Thresholds
    minimum_confidence_score: float = 0.7
    auto_report_confidence_threshold: float = 0.9
    human_review_confidence_threshold: float = 0.8
    
    # Reporting Settings
    auto_reporting_enabled: bool = False
    report_evidence_screenshots: bool = True
    max_evidence_files_per_report: int = 10
    report_retry_attempts: int = 3
    report_retry_delay_minutes: int = 30
    
    # Monitoring and Logging
    sentry_dsn: Optional[str] = None
    log_level: str = "INFO"
    metrics_enabled: bool = True
    performance_monitoring: bool = True
    
    # Security Settings
    encrypt_credentials: bool = True
    credential_rotation_days: int = 90
    session_security_headers: bool = True
    
    class Config:
        env_prefix = "SOCIAL_MEDIA_"
        env_file = ".env"


@dataclass
class PlatformConfig:
    """Configuration for specific social media platforms."""
    
    platform: SocialMediaPlatform
    base_url: str
    api_base_url: Optional[str] = None
    
    # Authentication
    requires_api_key: bool = True
    supports_oauth: bool = False
    supports_public_access: bool = False
    
    # Rate Limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10
    
    # Features Support
    supports_profile_search: bool = True
    supports_username_search: bool = True
    supports_content_search: bool = False
    supports_bulk_operations: bool = False
    supports_real_time_monitoring: bool = False
    
    # Scraping Configuration
    user_agents: List[str] = field(default_factory=list)
    required_headers: Dict[str, str] = field(default_factory=dict)
    session_cookies_required: bool = False
    javascript_rendering_required: bool = False
    
    # Anti-Detection
    requires_proxy: bool = False
    cloudflare_protection: bool = False
    bot_detection_active: bool = True
    request_delay_seconds: float = 2.0
    
    # Content Selectors (for web scraping)
    profile_selectors: Dict[str, str] = field(default_factory=dict)
    content_selectors: Dict[str, str] = field(default_factory=dict)
    
    # API Endpoints
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid base_url for {self.platform}: {self.base_url}")


@dataclass
class MonitoringConfig:
    """Configuration for social media monitoring operations."""
    
    settings: SocialMediaSettings = field(default_factory=SocialMediaSettings)
    
    # Platform configurations
    platform_configs: Dict[SocialMediaPlatform, PlatformConfig] = field(default_factory=dict)
    
    # Search Configuration
    search_terms_templates: List[str] = field(default_factory=list)
    username_variations_patterns: List[str] = field(default_factory=list)
    
    # Detection Algorithms
    enabled_detection_methods: Set[str] = field(
        default_factory=lambda: {
            "face_recognition",
            "image_hashing", 
            "username_similarity",
            "profile_similarity",
            "content_analysis"
        }
    )
    
    # Reporting Templates
    report_templates: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize configuration and setup platform configs."""
        self._setup_logging()
        self._load_platform_configs()
        self._load_search_templates()
        self._validate_configuration()
    
    def _setup_logging(self) -> None:
        """Configure structured logging for social media monitoring."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _load_platform_configs(self) -> None:
        """Load platform-specific configurations."""
        
        # Instagram Configuration
        instagram_config = PlatformConfig(
            platform=SocialMediaPlatform.INSTAGRAM,
            base_url="https://www.instagram.com",
            api_base_url="https://graph.instagram.com",
            requires_api_key=True,
            supports_oauth=True,
            requests_per_hour=200,
            supports_profile_search=True,
            supports_username_search=True,
            supports_content_search=False,
            javascript_rendering_required=True,
            cloudflare_protection=False,
            bot_detection_active=True,
            request_delay_seconds=2.0,
            profile_selectors={
                "username": "h2._7UhW9",
                "display_name": "h1._7UhW9",
                "bio": "div.-vDIg span",
                "follower_count": "a[href*='/followers/'] span",
                "following_count": "a[href*='/following/'] span",
                "post_count": "div.g47SY span",
                "profile_image": "img[alt*='profile picture']",
                "posts": "div.Nnq7C a"
            },
            api_endpoints={
                "user_info": "/v17.0/{user_id}",
                "user_media": "/v17.0/{user_id}/media",
                "search_users": "/v17.0/ig_hashtag_search"
            }
        )
        
        # Twitter/X Configuration
        twitter_config = PlatformConfig(
            platform=SocialMediaPlatform.TWITTER,
            base_url="https://twitter.com",
            api_base_url="https://api.twitter.com",
            requires_api_key=True,
            supports_oauth=True,
            requests_per_minute=300,
            supports_profile_search=True,
            supports_username_search=True,
            supports_content_search=True,
            supports_real_time_monitoring=True,
            javascript_rendering_required=True,
            bot_detection_active=True,
            request_delay_seconds=1.0,
            profile_selectors={
                "username": "[data-testid='UserName'] span",
                "display_name": "[data-testid='UserName'] span:first-child",
                "bio": "[data-testid='UserDescription']",
                "follower_count": "a[href*='/followers'] span",
                "following_count": "a[href*='/following'] span",
                "profile_image": "[data-testid='UserAvatar-Container-unknown'] img",
                "tweets": "[data-testid='tweet']"
            },
            api_endpoints={
                "user_lookup": "/2/users/by",
                "user_tweets": "/2/users/{id}/tweets",
                "search_users": "/2/users/by/username/{username}",
                "search_tweets": "/2/tweets/search/recent"
            }
        )
        
        # Facebook Configuration
        facebook_config = PlatformConfig(
            platform=SocialMediaPlatform.FACEBOOK,
            base_url="https://www.facebook.com",
            api_base_url="https://graph.facebook.com",
            requires_api_key=True,
            supports_oauth=True,
            requests_per_hour=600,
            supports_profile_search=True,
            supports_username_search=True,
            javascript_rendering_required=True,
            cloudflare_protection=False,
            bot_detection_active=True,
            request_delay_seconds=3.0,
            api_endpoints={
                "user_info": "/v18.0/{user_id}",
                "page_info": "/v18.0/{page_id}",
                "search": "/v18.0/search"
            }
        )
        
        # TikTok Configuration
        tiktok_config = PlatformConfig(
            platform=SocialMediaPlatform.TIKTOK,
            base_url="https://www.tiktok.com",
            api_base_url="https://open-api.tiktok.com",
            requires_api_key=True,
            supports_oauth=True,
            requests_per_minute=100,
            supports_profile_search=True,
            supports_username_search=True,
            supports_content_search=True,
            javascript_rendering_required=True,
            cloudflare_protection=True,
            bot_detection_active=True,
            requires_proxy=True,
            request_delay_seconds=3.0,
            profile_selectors={
                "username": "[data-e2e='user-title']",
                "display_name": "[data-e2e='user-subtitle']",
                "bio": "[data-e2e='user-bio']",
                "follower_count": "[data-e2e='followers-count']",
                "following_count": "[data-e2e='following-count']",
                "likes_count": "[data-e2e='likes-count']",
                "profile_image": "[data-e2e='user-avatar'] img",
                "videos": "[data-e2e='user-post-item']"
            }
        )
        
        # Reddit Configuration
        reddit_config = PlatformConfig(
            platform=SocialMediaPlatform.REDDIT,
            base_url="https://www.reddit.com",
            api_base_url="https://oauth.reddit.com",
            requires_api_key=True,
            supports_oauth=True,
            requests_per_minute=60,
            supports_profile_search=True,
            supports_username_search=True,
            supports_content_search=True,
            supports_bulk_operations=True,
            javascript_rendering_required=False,
            bot_detection_active=False,
            request_delay_seconds=1.0,
            api_endpoints={
                "user_info": "/user/{username}/about",
                "user_posts": "/user/{username}/submitted",
                "search_users": "/users/search",
                "search_posts": "/search"
            }
        )
        
        self.platform_configs = {
            SocialMediaPlatform.INSTAGRAM: instagram_config,
            SocialMediaPlatform.TWITTER: twitter_config,
            SocialMediaPlatform.FACEBOOK: facebook_config,
            SocialMediaPlatform.TIKTOK: tiktok_config,
            SocialMediaPlatform.REDDIT: reddit_config
        }
        
        logger.info(
            "Loaded platform configurations",
            platforms=list(self.platform_configs.keys())
        )
    
    def _load_search_templates(self) -> None:
        """Load search term templates."""
        self.search_terms_templates = [
            "{username}",
            "{username}_leaked",
            "{username} leaked",
            "{username} onlyfans",
            "{username} premium",
            "{username} content",
            "{username} free",
            "{username} download",
            "{stage_name}",
            "{stage_name} leaked",
            "{stage_name} content"
        ]
        
        self.username_variations_patterns = [
            "{username}",
            "{username}_",
            "_{username}",
            "{username}2023",
            "{username}2024", 
            "{username}official",
            "{username}real",
            "real{username}",
            "{username}vip",
            "{username}premium"
        ]
        
        # Report templates for different platforms
        self.report_templates = {
            "impersonation": """
Subject: Impersonation Report - {platform}

Dear {platform} Support Team,

I am reporting an account that is impersonating me and using my copyrighted content without permission.

Impersonating Account:
- Username: {fake_username}
- URL: {fake_url}
- User ID: {fake_user_id}

Original Account:
- Username: {original_username}  
- URL: {original_url}

The impersonating account is using my profile pictures, bio content, and posting my copyrighted images/videos without permission. This constitutes both impersonation and copyright infringement.

Evidence attached includes screenshots and similarity analysis.

Please remove this account and its content immediately.

Thank you,
{reporter_name}
{contact_email}
            """,
            "copyright": """
Subject: Copyright Infringement Report - {platform}

Dear {platform} Support Team,

I am the copyright holder of content being shared without permission on your platform.

Infringing Account:
- Username: {username}
- URL: {url}

The account is posting my copyrighted images and videos without permission. I have never authorized this use.

Please remove the infringing content and take appropriate action against the account.

Evidence and ownership proof attached.

Regards,
{reporter_name}
{contact_email}
            """
        }
    
    def _validate_configuration(self) -> None:
        """Validate the monitoring configuration."""
        # Check API credentials
        api_configured_platforms = []
        
        if self.settings.instagram_access_token:
            api_configured_platforms.append("Instagram")
        if self.settings.twitter_bearer_token:
            api_configured_platforms.append("Twitter")
        if self.settings.facebook_access_token:
            api_configured_platforms.append("Facebook")
        if self.settings.tiktok_client_key:
            api_configured_platforms.append("TikTok")
        if self.settings.reddit_client_id:
            api_configured_platforms.append("Reddit")
        
        if not api_configured_platforms:
            logger.warning("No platform API credentials configured - monitoring will be limited to scraping")
        else:
            logger.info("API credentials configured", platforms=api_configured_platforms)
        
        # Ensure storage directories exist
        for path in [self.settings.screenshot_storage_path, self.settings.profile_images_storage_path]:
            Path(path).mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Social media monitoring configuration validated",
            platforms=len(self.platform_configs),
            detection_methods=len(self.enabled_detection_methods),
            search_templates=len(self.search_terms_templates)
        )
    
    def get_platform_config(self, platform: SocialMediaPlatform) -> Optional[PlatformConfig]:
        """Get configuration for specific platform."""
        return self.platform_configs.get(platform)
    
    def is_platform_supported(self, platform: SocialMediaPlatform) -> bool:
        """Check if platform is supported."""
        return platform in self.platform_configs
    
    def get_search_terms(self, username: str, stage_name: Optional[str] = None) -> List[str]:
        """Generate search terms for monitoring."""
        terms = []
        
        for template in self.search_terms_templates:
            if "{stage_name}" in template and stage_name:
                terms.append(template.format(username=username, stage_name=stage_name))
            elif "{stage_name}" not in template:
                terms.append(template.format(username=username))
        
        return list(set(terms))  # Remove duplicates
    
    def get_username_variations(self, username: str) -> List[str]:
        """Generate username variations for monitoring."""
        variations = []
        
        for pattern in self.username_variations_patterns:
            variations.append(pattern.format(username=username))
        
        return list(set(variations))  # Remove duplicates