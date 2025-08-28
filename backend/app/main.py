import os
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.api import api_router
from app.api.websocket import websocket_endpoint
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_async_session
from app.db.utils import (
    initialize_database, cleanup_connections, get_database_health,
    db_metrics, health_checker
)
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.security import SecurityMiddleware
from app.middleware.logging import LoggingMiddleware, setup_logging
from app.middleware.input_validation import InputValidationMiddleware
from app.middleware.rbac import RBACMiddleware

logger = logging.getLogger(__name__)

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    # Enhanced OpenAPI metadata for professional documentation
    summary="AI-Powered Content Protection and DMCA Management Platform",
    terms_of_service="https://contentprotection.ai/terms",
    contact={
        "name": "Content Protection Platform API Support",
        "url": "https://contentprotection.ai/support",
        "email": "api-support@contentprotection.ai",
    },
    license_info={
        "name": "Commercial License",
        "url": "https://contentprotection.ai/license",
    },
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User authentication and JWT token management. Includes login, registration, 2FA, and password management.",
            "externalDocs": {
                "description": "Authentication Guide",
                "url": "https://docs.contentprotection.ai/auth"
            }
        },
        {
            "name": "users",
            "description": "User profile management and account operations.",
        },
        {
            "name": "protected-profiles",
            "description": "Manage protected creator profiles with AI signature generation and monitoring settings.",
            "externalDocs": {
                "description": "Profile Setup Guide",
                "url": "https://docs.contentprotection.ai/profiles"
            }
        },
        {
            "name": "content-scanning", 
            "description": "AI-powered content scanning and monitoring across platforms. Includes manual scans, scheduled monitoring, and real-time detection.",
            "externalDocs": {
                "description": "Scanning Guide",
                "url": "https://docs.contentprotection.ai/scanning"
            }
        },
        {
            "name": "infringements",
            "description": "Content infringement detection and management. View detected violations and manage takedown workflows.",
        },
        {
            "name": "takedown-requests",
            "description": "DMCA takedown request management. Submit, track, and automate copyright enforcement actions.",
            "externalDocs": {
                "description": "DMCA Guide", 
                "url": "https://docs.contentprotection.ai/dmca"
            }
        },
        {
            "name": "social-media-monitoring",
            "description": "Social media platform monitoring for impersonation and unauthorized content sharing.",
            "externalDocs": {
                "description": "Social Media Monitoring",
                "url": "https://docs.contentprotection.ai/social"
            }
        },
        {
            "name": "subscriptions",
            "description": "Subscription and billing management with Stripe integration.",
        },
        {
            "name": "dashboard",
            "description": "Analytics dashboard with metrics, insights, and reporting.",
        },
    ],
    servers=[
        {
            "url": "https://api.contentprotection.ai",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.contentprotection.ai", 
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        }
    ]
)

# Security middleware stack (order matters - most restrictive first)

# CORS MUST be added FIRST to handle preflight requests
if settings.BACKEND_CORS_ORIGINS:
    logger.info(f"Adding CORS middleware with origins: {settings.BACKEND_CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    # Fallback for local development - allow specific origins
    logger.warning("No CORS origins configured - using local development CORS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:13000", 
            "http://localhost:3000", 
            "http://127.0.0.1:13000", 
            "http://127.0.0.1:3000",
            "http://frontend:8080"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# 1. Input validation middleware (first line of defense)
app.add_middleware(
    InputValidationMiddleware,
    max_request_size=50 * 1024 * 1024,  # 50MB
    max_json_depth=10,
    max_array_length=1000,
    max_file_size=10 * 1024 * 1024,  # 10MB
    enable_strict_validation=not settings.DEBUG
)

# 2. Security headers and attack prevention
app.add_middleware(
    SecurityMiddleware,
    enable_csrf_protection=True,
    enable_request_logging=True,
    enable_ip_blocking=True,
    max_request_size=50 * 1024 * 1024  # 50MB
)

# 3. Role-based access control
app.add_middleware(
    RBACMiddleware,
    enable_rbac=True
)

# 4. Rate limiting middleware
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
        "/api/v1/admin/*": {"limit": 50, "window": 3600},  # Admin endpoints
        "/api/v1/api/*": {"limit": 1000, "window": 3600},  # API key endpoints
    }
)

# 5. Request/response logging middleware (last for complete context)
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=settings.DEBUG,
    log_response_body=False
)

# CORS middleware already added at the beginning of the stack

# Add trusted host middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket, token: str, db: AsyncSession = Depends(get_async_session)):
    """WebSocket endpoint for real-time updates."""
    await websocket_endpoint(websocket, token, db)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup with comprehensive database setup and service container."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    try:
        # Configure and register all services in the DI container
        from app.core.service_registry import configure_services
        await configure_services()
        logger.info("Service container configuration completed")
        
        # Start the service container (initializes singletons and runs startup hooks)
        from app.core.container import container
        await container.start_services()
        logger.info("Service container started successfully")
        
        # Initialize database with health checks (this may now be handled by service container)
        await initialize_database()
        logger.info("Database initialization completed successfully")
        
        # Initialize database schema
        await init_db()
        logger.info("Database schema initialization completed")
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.info(f"Upload directory ready: {settings.UPLOAD_DIR}")
        
        # Perform initial health check
        health_info = await get_database_health()
        if health_info["healthy"]:
            logger.info(f"Database health check passed - Response time: {health_info['response_time']:.2f}ms")
        else:
            logger.warning(f"Database health check failed: {health_info.get('error', 'Unknown error')}")
        
        # Check service container health
        service_health = await container.check_health()
        if service_health["overall_healthy"]:
            logger.info(f"Service container health check passed - {len(service_health['services'])} services healthy")
        else:
            logger.warning("Some services failed health check")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Comprehensive cleanup on application shutdown."""
    logger.info("Application shutting down...")
    
    try:
        # Stop the service container (runs shutdown hooks and cleans up services)
        from app.core.container import container
        await container.stop_services()
        logger.info("Service container stopped successfully")
        
        # Clean up database connections
        await cleanup_connections()
        logger.info("Database connections cleaned up")
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


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
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint with integrated monitoring."""
    try:
        from app.core.container import container
        
        # Get health monitor from container
        health_monitor = await container.get('HealthMonitor')
        health_summary = await health_monitor.get_health_summary()
        
        return {
            "status": health_summary.get("status", "unknown"),
            "version": settings.VERSION,
            "timestamp": health_summary.get("timestamp", datetime.utcnow().isoformat()),
            "uptime_hours": health_summary.get("uptime_hours", 0),
            "environment": "development" if settings.DEBUG else "production",
            "services": health_summary.get("services", {}),
            "system_metrics": health_summary.get("system_metrics", {}),
            "alerts_triggered": health_summary.get("alerts_triggered", [])
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Fallback to basic health check
        try:
            from app.core.container import container
            service_health = await container.check_health()
            db_health = await get_database_health()
            
            overall_healthy = db_health.get("healthy", False) and service_health.get("overall_healthy", False)
            
            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "version": settings.VERSION,
                "timestamp": datetime.utcnow().isoformat(),
                "environment": "development" if settings.DEBUG else "production",
                "error": "Health monitor unavailable, using fallback",
                "services": {
                    "database": {"status": "healthy" if db_health.get("healthy", False) else "unhealthy"},
                    "container": {"status": "healthy" if service_health.get("overall_healthy", False) else "unhealthy"}
                }
            }
        except Exception as fallback_error:
            logger.error(f"Fallback health check also failed: {fallback_error}")
            raise HTTPException(
                status_code=503,
                detail={"status": "unhealthy", "error": str(e), "fallback_error": str(fallback_error)}
            )


@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with all metrics and service details."""
    try:
        from app.core.container import container
        
        health_monitor = await container.get('HealthMonitor')
        detailed_report = await health_monitor.get_detailed_health_report()
        
        return detailed_report
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )


@app.get("/health/performance")  
async def performance_metrics() -> Dict[str, Any]:
    """Get performance metrics from the monitoring system."""
    try:
        from app.core.container import container
        
        performance_monitor = await container.get('PerformanceMonitor')
        performance_summary = performance_monitor.get_performance_summary()
        
        return performance_summary
        
    except Exception as e:
        logger.error(f"Performance metrics check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "error": str(e)}
        )


@app.get("/services")
async def service_registry_info() -> Dict[str, Any]:
    """Get information about all registered services in the container."""
    try:
        from app.core.service_registry import get_service_registry_info
        
        service_info = get_service_registry_info()
        return {
            "total_services": len(service_info),
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_info
        }
        
    except Exception as e:
        logger.error(f"Service registry info failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)}
        )


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
            "subscriptions": f"{settings.API_V1_STR}/subscriptions",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/services")
async def services_info() -> Dict[str, Any]:
    """Get detailed information about all registered services."""
    try:
        from app.core.service_registry import get_service_registry_info
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": get_service_registry_info()
        }
    except Exception as e:
        logger.error(f"Services info collection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Services info collection failed", "message": str(e)}
        )


@app.get("/metrics")
async def database_metrics() -> Dict[str, Any]:
    """Database performance metrics endpoint."""
    try:
        # Get connection statistics
        connection_stats = await db_metrics.get_connection_stats()
        
        # Get database size information
        size_info = await db_metrics.get_database_size()
        
        # Get health information
        health_info = await get_database_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database_health": {
                "healthy": health_info["healthy"],
                "response_time_ms": round(health_info["response_time"], 2),
                "last_check": health_info["timestamp"]
            },
            "connections": connection_stats,
            "storage": size_info,
            "pool_status": health_info.get("pool_info", {})
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "Metrics collection failed", "message": str(e)}
        )


# Enhanced OpenAPI Configuration
def custom_openapi():
    """Generate enhanced OpenAPI schema with comprehensive documentation"""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=[
            {
                "url": "https://api.contentprotection.ai",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.contentprotection.ai", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Local development server"
            }
        ]
    )

    # Enhanced API Information
    openapi_schema["info"].update({
        "x-logo": {
            "url": "https://contentprotection.ai/logo.png",
            "altText": "Content Protection Platform"
        },
        "x-apisguru-categories": ["media", "security", "ai"],
        "x-providerName": "contentprotection.ai",
        "x-serviceName": "content-protection-api"
    })

    # Add comprehensive security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from `/auth/login` endpoint"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for server-to-server authentication"
        }
    }

    # Enhanced error responses
    if "responses" not in openapi_schema["components"]:
        openapi_schema["components"]["responses"] = {}
    
    openapi_schema["components"]["responses"].update({
        "ValidationError": {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "loc": {"type": "array", "items": {"type": "string"}},
                                        "msg": {"type": "string"},
                                        "type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "AuthenticationError": {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string"}
                        }
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string"},
                            "retry_after": {"type": "integer"}
                        }
                    }
                }
            }
        }
    })

    # Add webhook documentation
    openapi_schema["webhooks"] = {
        "scan_completed": {
            "post": {
                "summary": "Scan Completed Webhook",
                "description": "Triggered when a content scan is completed",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "event": {"type": "string", "example": "scan.completed"},
                                    "job_id": {"type": "string", "example": "scan_12345abc"},
                                    "profile_id": {"type": "integer", "example": 42},
                                    "results": {
                                        "type": "object",
                                        "properties": {
                                            "infringements_found": {"type": "integer"},
                                            "new_infringements": {"type": "integer"},
                                            "scanned_urls": {"type": "integer"}
                                        }
                                    },
                                    "timestamp": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Webhook received successfully"
                    }
                }
            }
        },
        "takedown_status": {
            "post": {
                "summary": "Takedown Status Update Webhook",
                "description": "Triggered when a takedown request status changes",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "event": {"type": "string", "example": "takedown.status_changed"},
                                    "takedown_id": {"type": "string", "example": "td_12345"},
                                    "old_status": {"type": "string", "example": "pending"},
                                    "new_status": {"type": "string", "example": "completed"},
                                    "platform": {"type": "string", "example": "google"},
                                    "timestamp": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Webhook received successfully"
                    }
                }
            }
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set custom OpenAPI schema
app.openapi = custom_openapi