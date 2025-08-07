from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os

from app.api.v1.api import api_router
from app.api.websocket import websocket_endpoint
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.security import SecurityMiddleware
from app.middleware.logging import LoggingMiddleware, setup_logging

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add security middleware (first)
app.add_middleware(
    SecurityMiddleware,
    enable_csrf_protection=True,
    enable_request_logging=True,
    enable_ip_blocking=True,
    max_request_size=50 * 1024 * 1024  # 50MB
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitingMiddleware,
    default_limit=100,  # 100 requests per hour by default
    default_window=3600,
    rate_limits={
        "/api/v1/auth/login": {"limit": 5, "window": 900},  # 5 per 15 minutes
        "/api/v1/auth/register": {"limit": 3, "window": 3600},  # 3 per hour
        "/api/v1/auth/forgot-password": {"limit": 3, "window": 3600},  # 3 per hour
        "/api/v1/infringements": {"limit": 100, "window": 3600},  # 100 per hour
        "/api/v1/takedowns": {"limit": 50, "window": 3600},  # 50 per hour
    }
)

# Add request/response logging middleware
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=settings.DEBUG,
    log_response_body=False
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add trusted host middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time updates."""
    await websocket_endpoint(websocket, token, db)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Initialize database
    await init_db()
    print("Database initialized")
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"Upload directory ready: {settings.UPLOAD_DIR}")
    
    print("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    print("Application shutting down...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Content Protection Platform API",
        "version": settings.VERSION,
        "docs": "/docs",
        "websocket": "/ws?token=YOUR_JWT_TOKEN"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "api_version": "v1",
        "features": {
            "authentication": "JWT",
            "websockets": True,
            "rate_limiting": True,
            "security_headers": True,
            "request_logging": True,
            "api_documentation": "/docs"
        },
        "endpoints": {
            "auth": f"{settings.API_V1_STR}/auth",
            "users": f"{settings.API_V1_STR}/users",
            "profiles": f"{settings.API_V1_STR}/profiles",
            "infringements": f"{settings.API_V1_STR}/infringements",
            "takedowns": f"{settings.API_V1_STR}/takedowns",
            "dashboard": f"{settings.API_V1_STR}/dashboard",
            "subscriptions": f"{settings.API_V1_STR}/subscriptions"
        }
    }