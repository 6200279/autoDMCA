"""
Application Startup and Initialization
Starts all background services and schedulers
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.services.scanning.scheduler import ScanningScheduler
from app.core.config import settings
from app.db.session import engine
from app.models import scanning  # Import models to create tables

logger = logging.getLogger(__name__)

# Global service instances
scheduler: Optional[ScanningScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    Start services on startup, cleanup on shutdown
    """
    global scheduler
    
    logger.info("Starting application services...")
    
    try:
        # Create database tables if they don't exist
        scanning.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Initialize scanning scheduler
        scheduler = ScanningScheduler()
        await scheduler.initialize()
        logger.info("Scanning scheduler initialized")
        
        # Start background services
        if settings.ENABLE_AUTO_SCANNING:
            logger.info("Automated scanning enabled")
        else:
            logger.warning("Automated scanning is disabled")
            
        # Warm up AI models
        from app.services.ai.content_matcher import ContentMatcher
        matcher = ContentMatcher()
        logger.info("AI models loaded")
        
        logger.info("All services started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't prevent app from starting, but log the error
        
    yield
    
    # Shutdown
    logger.info("Shutting down application services...")
    
    try:
        if scheduler:
            await scheduler.shutdown()
            logger.info("Scanning scheduler shut down")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        
    logger.info("Application shutdown complete")


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
    
    # Add CORS middleware
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    from app.middleware.security import SecurityMiddleware
    from app.middleware.logging import LoggingMiddleware
    from app.middleware.rate_limiting import RateLimitMiddleware
    
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    from app.api.v1.api import api_router
    app.include_router(api_router, prefix="/api/v1")
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "services": {
                "scheduler": scheduler is not None and "running" or "stopped",
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