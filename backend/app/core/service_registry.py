"""
Service Registry for AutoDMCA Application

This module configures and registers all services in the dependency injection container.
It provides a centralized place to configure service lifetimes, dependencies, and
initialization logic for the entire application.
"""

import logging
from typing import Optional
from app.core.container import container, ServiceLifetime
from app.core.config import settings

logger = logging.getLogger(__name__)


async def configure_services():
    """
    Configure and register all application services in the DI container.
    
    This function sets up the complete service graph including:
    - Database services and repositories
    - Business services (DMCA, content processing, etc.)
    - External integrations (Stripe, email services)
    - Infrastructure services (caching, logging, monitoring)
    """
    
    logger.info("Configuring application services...")
    
    # =============================================================================
    # Infrastructure Services
    # =============================================================================
    
    # Enhanced Database Service
    from app.core.database_service import DatabaseService, database_service
    container.register_singleton(DatabaseService, database_service)
    
    # Database Session Factory  
    from app.core.database_service import AsyncSessionFactory
    container.register_singleton(AsyncSessionFactory, AsyncSessionFactory())
    
    # Redis Client
    from redis import Redis
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    container.register_singleton(Redis, redis_client)
    
    # Cache Service
    from app.services.cache.multi_level_cache import MultiLevelCache
    container.register_singleton(MultiLevelCache, MultiLevelCache)
    
    # =============================================================================
    # Authentication & Security Services  
    # =============================================================================
    
    # Password Service
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    container.register_singleton(CryptContext, pwd_context)
    
    # JWT Service  
    from app.services.auth.jwt_service import JWTService
    container.register_singleton(JWTService, JWTService)
    
    # Email Service
    from app.services.auth.email_service import EmailService
    container.register_singleton(EmailService, EmailService)
    
    # Rate Limiter
    from app.services.auth.rate_limiter import RateLimiter
    container.register_singleton(RateLimiter, RateLimiter)
    
    # =============================================================================
    # Verification Services
    # =============================================================================
    
    # Account Verification System
    from app.services.verification.account_verification import account_verification, AccountVerificationService
    container.register_singleton(AccountVerificationService, account_verification)
    
    # =============================================================================
    # Business Domain Services
    # =============================================================================
    
    # User Service
    from app.services.user_service import UserService
    container.register_scoped(UserService, UserService)
    
    # Profile Service
    from app.services.profile_service import ProfileService  
    container.register_scoped(ProfileService, ProfileService)
    
    # DMCA Services
    from app.services.dmca.takedown_processor import TakedownProcessor
    from app.services.dmca.integration import DMCAIntegrationService
    container.register_scoped(TakedownProcessor, TakedownProcessor)
    container.register_scoped(DMCAIntegrationService, DMCAIntegrationService)
    
    # Template Service
    from app.services.dmca_template_service import DMCATemplateService
    container.register_scoped(DMCATemplateService, DMCATemplateService)
    
    # Content Processing Services
    from app.services.ai.content_matcher import ContentMatcher
    from app.services.ai.enhanced_content_matcher import EnhancedContentMatcher
    from app.services.content.watermarking import WatermarkingService
    container.register_singleton(ContentMatcher, ContentMatcher)  # Singleton for model caching
    container.register_singleton(EnhancedContentMatcher, EnhancedContentMatcher)
    container.register_scoped(WatermarkingService, WatermarkingService)
    
    # Scanning Services
    from app.services.scanning.orchestrator import ScanningOrchestrator
    from app.services.scanning.web_crawler import WebCrawler
    from app.services.scanning.search_engines import SearchEngineService
    from app.services.scanning.automated_scheduler import automated_scheduler, AutomatedScanScheduler
    from app.services.scanning.initial_user_scanner import initial_user_scanner, InitialUserScanner
    from app.services.scanning.piracy_sites_database import piracy_sites_db, PiracySiteDatabase
    from app.services.scanning.official_search_apis import OfficialSearchAPIs
    container.register_scoped(ScanningOrchestrator, ScanningOrchestrator)
    container.register_scoped(WebCrawler, WebCrawler)
    container.register_singleton(SearchEngineService, SearchEngineService)
    container.register_singleton(AutomatedScanScheduler, automated_scheduler)
    container.register_singleton(InitialUserScanner, initial_user_scanner)
    container.register_singleton(PiracySiteDatabase, piracy_sites_db)
    container.register_singleton(OfficialSearchAPIs, OfficialSearchAPIs)
    
    # Social Media Services
    from app.services.social_media.monitoring_service import SocialMediaMonitoringService
    from app.services.social_media.api_clients import SocialMediaAPIClients
    container.register_scoped(SocialMediaMonitoringService, SocialMediaMonitoringService)
    container.register_singleton(SocialMediaAPIClients, SocialMediaAPIClients)
    
    # =============================================================================
    # Billing & Subscription Services
    # =============================================================================
    
    # Stripe Services
    from app.services.billing.stripe_service import StripeService
    from app.services.billing.subscription_service import SubscriptionService
    from app.services.billing.usage_service import UsageService
    from app.services.billing.webhook_service import WebhookService
    container.register_singleton(StripeService, StripeService)
    container.register_scoped(SubscriptionService, SubscriptionService)
    container.register_scoped(UsageService, UsageService)
    container.register_singleton(WebhookService, WebhookService)
    
    # Gift Subscription Service
    from app.services.billing.gift_subscription_service import GiftSubscriptionService
    container.register_scoped(GiftSubscriptionService, GiftSubscriptionService)
    
    # Addon Services
    from app.services.billing.addon_service import AddonService
    container.register_scoped(AddonService, AddonService)
    
    # Subscription Tier Enforcement
    from app.services.billing.subscription_tier_enforcement import subscription_enforcement, SubscriptionTierEnforcement
    container.register_singleton(SubscriptionTierEnforcement, subscription_enforcement)
    
    # =============================================================================
    # File & Storage Services
    # =============================================================================
    
    # File Storage Service
    from app.services.file.storage import FileStorageService
    container.register_singleton(FileStorageService, FileStorageService)
    
    # =============================================================================
    # Notification Services
    # =============================================================================
    
    # Alert System
    from app.services.notifications.alert_system import alert_system, RealTimeAlertSystem
    container.register_singleton(RealTimeAlertSystem, alert_system)
    
    # Email Reports System
    from app.services.notifications.comprehensive_email_reports import email_reports, ComprehensiveEmailReports
    container.register_singleton(ComprehensiveEmailReports, email_reports)
    
    # =============================================================================
    # Monitoring & Performance Services
    # =============================================================================
    
    # Performance Monitor
    from app.services.monitoring.performance_monitor import PerformanceMonitor
    from app.services.performance.production_monitor import ProductionMonitor
    container.register_singleton(PerformanceMonitor, PerformanceMonitor)
    container.register_singleton(ProductionMonitor, ProductionMonitor)
    
    # Health Monitor
    from app.services.monitoring.health_monitor import health_monitor, HealthMonitor
    container.register_singleton(HealthMonitor, health_monitor)
    
    # Dashboard Service
    from app.services.dashboard.dashboard_service import dashboard_service, DashboardService
    container.register_singleton(DashboardService, dashboard_service)
    
    # Content Processing Service
    from app.services.content.content_processing_service import content_processing_service, ContentProcessingService
    container.register_singleton(ContentProcessingService, content_processing_service)
    
    # Enhanced Billing Services
    from app.services.billing.invoice_service import invoice_service, InvoiceService
    from app.services.billing.billing_portal_service import billing_portal_service, BillingPortalService
    from app.services.billing.checkout_service import checkout_service, CheckoutService
    
    container.register_singleton(InvoiceService, invoice_service)
    container.register_singleton(BillingPortalService, billing_portal_service)
    container.register_singleton(CheckoutService, checkout_service)
    
    # =============================================================================
    # Repository Layer (Data Access)
    # =============================================================================
    
    # Configure repositories if they exist
    try:
        from app.repositories.user_repository import UserRepository
        from app.repositories.profile_repository import ProfileRepository
        from app.repositories.takedown_repository import TakedownRepository
        from app.repositories.template_repository import TemplateRepository
        
        container.register_scoped(UserRepository, UserRepository)
        container.register_scoped(ProfileRepository, ProfileRepository) 
        container.register_scoped(TakedownRepository, TakedownRepository)
        container.register_scoped(TemplateRepository, TemplateRepository)
        
        logger.info("Registered repository layer services")
    except ImportError as e:
        logger.warning(f"Repository layer not available: {e}")
    
    # =============================================================================
    # External Integration Services
    # =============================================================================
    
    # Configure external services based on settings
    if settings.STRIPE_SECRET_KEY:
        logger.info("Stripe integration enabled")
        
    if settings.SMTP_HOST:
        logger.info("SMTP email service enabled")
        
    # SendGrid Integration
    if hasattr(settings, 'SENDGRID_API_KEY') and settings.SENDGRID_API_KEY:
        from app.services.integrations.sendgrid_service import SendGridService, sendgrid_service
        container.register_singleton(SendGridService, sendgrid_service)
        logger.info("SendGrid integration enabled")
    
    # Google Vision API Integration
    if (hasattr(settings, 'GOOGLE_VISION_API_KEY') and settings.GOOGLE_VISION_API_KEY) or \
       (hasattr(settings, 'GOOGLE_VISION_CREDENTIALS_PATH') and settings.GOOGLE_VISION_CREDENTIALS_PATH) or \
       (hasattr(settings, 'GOOGLE_VISION_CREDENTIALS_JSON') and settings.GOOGLE_VISION_CREDENTIALS_JSON):
        from app.services.integrations.google_vision_service import GoogleVisionService, google_vision_service
        container.register_singleton(GoogleVisionService, google_vision_service)
        logger.info("Google Vision API integration enabled")
    
    # PayPal Integration
    if hasattr(settings, 'PAYPAL_CLIENT_ID') and settings.PAYPAL_CLIENT_ID:
        from app.services.integrations.paypal_service import PayPalService, paypal_service
        container.register_singleton(PayPalService, paypal_service)
        logger.info("PayPal integration enabled")
    
    # =============================================================================
    # Health Check Configuration
    # =============================================================================
    
    # Configure health checks for critical services
    container.add_health_check(Redis, lambda: redis_client.ping())
    container.add_health_check(MultiLevelCache, lambda: True)  # Add actual health check
    
    # =============================================================================
    # Startup/Shutdown Hooks
    # =============================================================================
    
    # Database initialization hook
    async def initialize_database():
        """Initialize database connections and run migrations if needed."""
        logger.info("Initializing enhanced database service...")
        
        # Initialize the database service
        db_service = await container.get(DatabaseService)
        await db_service.initialize()
        
        # Run database schema initialization
        from app.db.init_db import init_db
        await init_db()
        
        logger.info("Database initialization complete")
    
    container.add_startup_hook(initialize_database)
    
    # Cache warming hook
    async def warm_caches():
        """Pre-warm important caches."""
        logger.info("Warming application caches...")
        try:
            cache_service = await container.get(MultiLevelCache)
            await cache_service.warm_cache()
            logger.info("Cache warming complete")
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")
    
    container.add_startup_hook(warm_caches)
    
    # Performance monitoring hook
    async def start_monitoring():
        """Start performance monitoring services."""
        logger.info("Starting performance monitoring...")
        try:
            monitor = await container.get(PerformanceMonitor)
            await monitor.start_monitoring()
            logger.info("Performance monitoring started")
        except Exception as e:
            logger.warning(f"Failed to start monitoring: {e}")
    
    container.add_startup_hook(start_monitoring)
    
    # Health monitoring hook
    async def start_health_monitoring():
        """Start health monitoring services."""
        logger.info("Starting health monitoring...")
        try:
            health_monitor = await container.get(HealthMonitor)
            await health_monitor.initialize()
            logger.info("Health monitoring started")
        except Exception as e:
            logger.warning(f"Failed to start health monitoring: {e}")
    
    container.add_startup_hook(start_health_monitoring)
    
    # Cleanup hook
    async def cleanup_resources():
        """Clean up resources during shutdown."""
        logger.info("Cleaning up application resources...")
        
        # Shutdown database service
        try:
            db_service = await container.get(DatabaseService)
            await db_service.close()
            logger.info("Database service shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down database service: {e}")
        
        # Shutdown monitoring services
        try:
            health_monitor = await container.get(HealthMonitor)
            await health_monitor.stop_monitoring()
            logger.info("Health monitoring shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down health monitoring: {e}")
        
        try:
            performance_monitor = await container.get(PerformanceMonitor)
            await performance_monitor.stop_monitoring()
            logger.info("Performance monitoring shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down performance monitoring: {e}")
        
        logger.info("Resource cleanup complete")
    
    container.add_shutdown_hook(cleanup_resources)
    
    logger.info(f"Service registration complete - {len(container._services)} services registered")


# Factory functions for commonly used services

async def get_database_session():
    """Get a database session from the container."""
    session_factory = await container.get(AsyncSessionFactory)
    return session_factory.create_session()


async def get_user_service(scope_id: Optional[str] = None):
    """Get the user service with proper scope."""
    return await container.get(UserService, scope_id)


async def get_takedown_processor(scope_id: Optional[str] = None):
    """Get the DMCA takedown processor."""
    return await container.get(TakedownProcessor, scope_id)


async def get_content_matcher():
    """Get the AI content matcher service."""
    return await container.get(ContentMatcher)


async def get_billing_service(scope_id: Optional[str] = None):
    """Get the billing/subscription service."""
    return await container.get(SubscriptionService, scope_id)


async def get_sendgrid_service():
    """Get the SendGrid email service."""
    try:
        from app.services.integrations.sendgrid_service import SendGridService
        return await container.get(SendGridService)
    except Exception:
        return None


async def get_google_vision_service():
    """Get the Google Vision API service."""
    try:
        from app.services.integrations.google_vision_service import GoogleVisionService
        return await container.get(GoogleVisionService)
    except Exception:
        return None


async def get_paypal_service():
    """Get the PayPal payment service."""
    try:
        from app.services.integrations.paypal_service import PayPalService
        return await container.get(PayPalService)
    except Exception:
        return None


# Service health check endpoint
async def check_all_services():
    """Check health of all registered services."""
    return await container.check_health()


# Service information endpoint
def get_service_registry_info():
    """Get information about all registered services."""
    return container.get_service_info()


__all__ = [
    'configure_services',
    'get_database_session',
    'get_user_service', 
    'get_takedown_processor',
    'get_content_matcher',
    'get_billing_service',
    'get_sendgrid_service',
    'get_google_vision_service',
    'get_paypal_service',
    'check_all_services',
    'get_service_registry_info'
]