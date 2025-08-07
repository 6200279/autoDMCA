"""
Configuration management for the content scanning engine.
"""

import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from pydantic import BaseSettings, validator


logger = structlog.get_logger(__name__)


class ScannerSettings(BaseSettings):
    """Environment-based configuration settings."""
    
    # Database
    database_url: str = "postgresql://localhost/autodmca"
    redis_url: str = "redis://localhost:6379/0"
    
    # Search APIs
    google_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None 
    bing_api_key: Optional[str] = None
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    concurrent_requests: int = 10
    
    # Proxy settings
    proxy_enabled: bool = False
    proxy_rotation_interval: int = 300  # 5 minutes
    proxy_providers: List[str] = field(default_factory=lambda: ["free-proxy-list"])
    
    # Face recognition
    face_recognition_tolerance: float = 0.6
    face_detection_model: str = "hog"  # or "cnn"
    max_faces_per_image: int = 5
    
    # Image hashing
    hash_size: int = 8
    similarity_threshold: float = 0.85
    supported_image_formats: Set[str] = field(
        default_factory=lambda: {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    )
    
    # Scanning intervals
    scan_interval_hours: int = 24
    priority_scan_interval_hours: int = 6
    quick_scan_interval_minutes: int = 30
    
    # Storage
    temp_storage_path: str = "/tmp/autodmca"
    max_temp_storage_mb: int = 1000
    cleanup_temp_files_hours: int = 24
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    log_level: str = "INFO"
    metrics_enabled: bool = True
    
    class Config:
        env_prefix = "SCANNER_"
        env_file = ".env"


@dataclass
class PiracySiteConfig:
    """Configuration for piracy site crawling."""
    
    name: str
    base_url: str
    search_patterns: List[str]
    content_selectors: Dict[str, str]
    rate_limit_delay: float = 1.0
    requires_proxy: bool = False
    cloudflare_protection: bool = False
    user_agent_rotation: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid base_url for {self.name}: {self.base_url}")


@dataclass 
class ScannerConfig:
    """Main configuration class for the content scanning engine."""
    
    settings: ScannerSettings = field(default_factory=ScannerSettings)
    
    # Known piracy sites with crawling configurations
    piracy_sites: List[PiracySiteConfig] = field(default_factory=list)
    
    # Search terms and patterns
    search_keywords: List[str] = field(default_factory=list)
    username_variations: List[str] = field(default_factory=list)
    
    # Content matching settings
    enable_face_recognition: bool = True
    enable_image_hashing: bool = True
    enable_text_matching: bool = True
    
    # DMCA processing
    dmca_sender_email: str = "takedown@autodmca.com"
    dmca_sender_name: str = "AutoDMCA Legal Team"
    dmca_template_path: str = "templates/dmca_notice.html"
    
    def __post_init__(self):
        """Initialize configuration and setup logging."""
        self._setup_logging()
        self._load_piracy_sites()
        self._validate_configuration()
    
    def _setup_logging(self) -> None:
        """Configure structured logging."""
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
    
    def _load_piracy_sites(self) -> None:
        """Load piracy site configurations from data files."""
        # Known piracy sites (anonymized/example configurations)
        default_sites = [
            PiracySiteConfig(
                name="generic_leak_forum_1",
                base_url="https://example-leak-forum.com",
                search_patterns=[
                    "/search?q={username}",
                    "/search?q={username}+leaked",
                    "/search?q={username}+onlyfans"
                ],
                content_selectors={
                    "title": ".post-title",
                    "content": ".post-content", 
                    "images": "img.content-image",
                    "links": "a[href*='download']"
                },
                rate_limit_delay=2.0,
                requires_proxy=True,
                cloudflare_protection=True
            ),
            PiracySiteConfig(
                name="generic_file_host_1", 
                base_url="https://example-filehost.com",
                search_patterns=[
                    "/search/{username}",
                    "/files?search={username}"
                ],
                content_selectors={
                    "title": ".file-title",
                    "thumbnail": ".file-thumbnail img",
                    "download_link": ".download-button"
                },
                rate_limit_delay=1.5,
                requires_proxy=False
            ),
            PiracySiteConfig(
                name="social_media_mirror",
                base_url="https://example-social-mirror.com", 
                search_patterns=[
                    "/user/{username}",
                    "/search?user={username}"
                ],
                content_selectors={
                    "posts": ".post-item",
                    "images": ".post-image img",
                    "videos": ".post-video video"
                },
                rate_limit_delay=1.0,
                user_agent_rotation=True
            )
        ]
        
        if not self.piracy_sites:
            self.piracy_sites = default_sites
            logger.info(
                "Loaded default piracy site configurations",
                site_count=len(default_sites)
            )
    
    def _validate_configuration(self) -> None:
        """Validate the configuration settings."""
        if not self.settings.google_api_key and not self.settings.bing_api_key:
            logger.warning("No search API keys configured - search functionality will be limited")
        
        # Ensure temp storage directory exists
        temp_path = Path(self.settings.temp_storage_path)
        temp_path.mkdir(parents=True, exist_ok=True)
        
        # Validate DMCA template exists
        if not Path(self.dmca_template_path).exists():
            logger.warning(f"DMCA template not found: {self.dmca_template_path}")
        
        logger.info(
            "Scanner configuration validated",
            piracy_sites=len(self.piracy_sites),
            search_apis_configured=bool(self.settings.google_api_key or self.settings.bing_api_key),
            face_recognition_enabled=self.enable_face_recognition,
            proxy_enabled=self.settings.proxy_enabled
        )
    
    def add_piracy_site(self, site_config: PiracySiteConfig) -> None:
        """Add a new piracy site configuration."""
        self.piracy_sites.append(site_config)
        logger.info(f"Added piracy site configuration: {site_config.name}")
    
    def get_piracy_site(self, name: str) -> Optional[PiracySiteConfig]:
        """Get piracy site configuration by name."""
        for site in self.piracy_sites:
            if site.name == name:
                return site
        return None
    
    def update_search_terms(self, username: str, additional_terms: List[str] = None) -> None:
        """Update search terms for a specific username."""
        # Generate username variations
        variations = [
            username,
            username.lower(),
            username.upper(), 
            username.replace('_', ''),
            username.replace('-', ''),
            f"{username}_leaked",
            f"{username} leaked",
            f"{username} onlyfans",
            f"{username} content"
        ]
        
        if additional_terms:
            variations.extend(additional_terms)
        
        self.username_variations = list(set(variations))
        
        # Generate search keywords
        keywords = []
        for variation in self.username_variations:
            keywords.extend([
                f'"{variation}"',
                f"{variation} leak",
                f"{variation} leaked",
                f"{variation} pirated", 
                f"{variation} stolen",
                f"{variation} download",
                f"{variation} free",
                f"{variation} premium content"
            ])
        
        self.search_keywords = list(set(keywords))
        
        logger.info(
            "Updated search terms",
            username=username,
            variations_count=len(self.username_variations),
            keywords_count=len(self.search_keywords)
        )