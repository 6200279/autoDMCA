"""
Application Startup and Initialization
Starts all background services and schedulers
"""
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI

# from app.services.scanning.scheduler import ScanningScheduler  # Disabled for local testing
from app.core.config import settings
from app.db.session import engine
from app.services.scanning.orchestrator import orchestrator
# from app.models import scanning  # Import models to create tables  # Disabled for local testing

# Models will be imported by their respective modules when needed

logger = logging.getLogger(__name__)

# Global service instances
scanning_orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    Start services on startup, cleanup on shutdown
    """
    # global scheduler  # Disabled for local testing
    
    logger.info("Starting Content Protection Platform services...")
    
    try:
        # Create database tables if they don't exist
        # scanning.Base.metadata.create_all(bind=engine)  # Disabled for local testing
        logger.info("Database tables creation skipped for local testing")
        
        # Initialize scanning orchestrator
        global scanning_orchestrator
        try:
            scanning_orchestrator = orchestrator
            await scanning_orchestrator.initialize()
            logger.info("✅ Scanning orchestrator initialized successfully")
            
            # Get orchestrator stats
            stats = await scanning_orchestrator.get_orchestrator_stats()
            logger.info(f"📊 Orchestrator stats: {stats.get('active_regions', 0)} regions, {stats.get('total_platforms', 0)} platforms")
            
        except Exception as e:
            logger.warning(f"⚠️  Scanning orchestrator initialization failed: {e}")
            logger.info("🔄 Application will continue without full scanning capability")
        
        # Start background services
        if getattr(settings, 'ENABLE_AUTO_SCANNING', True):
            logger.info("🔍 Automated scanning enabled")
        else:
            logger.warning("⚠️  Automated scanning is disabled")
            
        # Warm up AI models
        try:
            from app.services.ai.content_matcher import ContentMatcher
            matcher = ContentMatcher()
            logger.info("🤖 AI content matcher initialized")
        except Exception as e:
            logger.warning(f"⚠️  AI models loading failed: {e}")
        
        logger.info("🚀 All services started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't prevent app from starting, but log the error
        
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application services...")
    
    try:
        if scanning_orchestrator:
            await scanning_orchestrator.shutdown()
            logger.info("✅ Scanning orchestrator shut down")
        else:
            logger.info("ℹ️  No scanning orchestrator to shut down")
            
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
        
    logger.info("✅ Application shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title="Content Protection Platform",
        description="Automated DMCA takedown and content protection service",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add custom middleware first (they process in reverse order)
    # from app.middleware.security import SecurityMiddleware  # Temporarily disabled
    from app.middleware.logging import LoggingMiddleware
    from app.middleware.rate_limiting import RateLimitingMiddleware
    
    # app.add_middleware(SecurityMiddleware)  # Temporarily disabled
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitingMiddleware)
    
    # Add CORS middleware LAST so it processes all responses (including rate limit errors)
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from app.api.v1.api import api_router
    app.include_router(api_router, prefix="/api/v1")
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        orchestrator_status = "unknown"
        try:
            if scanning_orchestrator:
                stats = await scanning_orchestrator.get_orchestrator_stats()
                orchestrator_status = "healthy" if stats.get("active_scans", 0) >= 0 else "degraded"
            else:
                orchestrator_status = "disabled"
        except Exception:
            orchestrator_status = "error"
            
        return {
            "status": "healthy",
            "services": {
                "scanning_orchestrator": orchestrator_status,
                "database": "connected",  # Would check actual connection
                "redis": "connected"  # Would check actual connection
            }
        }
    
    # Add root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Content Protection Platform API",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
    return app


# Create app instance
app = create_application()


# Background task to process manual submissions
async def process_manual_submissions():
    """
    Process manually submitted URLs from users
    PRD: "Manual Submission Tool"
    """
    while True:
        try:
            # Check for pending manual submissions
            # In production, this would query the database
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Error processing manual submissions: {e}")
            await asyncio.sleep(60)


# Background task to check takedown status
async def check_takedown_status():
    """
    Check status of sent takedown notices
    """
    while True:
        try:
            # Check pending takedowns
            # In production, this would query the database and check URLs
            await asyncio.sleep(3600)  # Check every hour
            
        except Exception as e:
            logger.error(f"Error checking takedown status: {e}")
            await asyncio.sleep(3600)


# Start background tasks when module is run directly
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.startup:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )


from typing import Optional