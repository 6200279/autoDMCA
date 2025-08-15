"""
OpenAPI Enhancement Module
Provides enhanced documentation, examples, and metadata for the Content Protection Platform API
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    Generate enhanced OpenAPI schema with comprehensive documentation,
    examples, and metadata for professional API documentation.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=getattr(app, 'servers', [])
    )

    # Enhanced API Information
    openapi_schema["info"].update({
        "x-logo": {
            "url": "https://contentprotection.ai/logo.png",
            "altText": "Content Protection Platform"
        },
        "x-apisguru-categories": ["media", "security", "ai"],
        "x-providerName": "contentprotection.ai",
        "x-serviceName": "content-protection-api",
        "x-preferred": True,
        "x-unofficial": False
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
        },
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://api.contentprotection.ai/oauth/authorize",
                    "tokenUrl": "https://api.contentprotection.ai/oauth/token",
                    "scopes": {
                        "read": "Read access to your data",
                        "write": "Write access to your data",
                        "admin": "Administrative access"
                    }
                }
            }
        }
    }

    # Global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []},
        {"OAuth2": ["read", "write"]}
    ]

    # Enhanced examples for common schemas
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}

    # Add comprehensive examples
    openapi_schema["components"]["examples"].update({
        "UserRegistrationExample": {
            "summary": "Complete user registration",
            "description": "Example of a complete user registration with all optional fields",
            "value": {
                "email": "creator@example.com",
                "password": "SecureP@ssw0rd123",
                "full_name": "Content Creator",
                "company": "Creator Studios LLC",
                "phone": "+1-555-123-4567",
                "accept_terms": True
            }
        },
        "LoginExample": {
            "summary": "User login request",
            "description": "Standard login with remember me option",
            "value": {
                "email": "creator@example.com",
                "password": "SecureP@ssw0rd123",
                "remember_me": True
            }
        },
        "TokenResponseExample": {
            "summary": "JWT token response",
            "description": "Response after successful authentication",
            "value": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE1MTYyMzkwMjJ9.abc123def456",
                "token_type": "bearer",
                "expires_in": 1800
            }
        },
        "ScanJobExample": {
            "summary": "Scan job response",
            "description": "Response from triggering a manual scan",
            "value": {
                "status": "success",
                "message": "Scan initiated",
                "job_id": "scan_12345abc",
                "profile_id": 42,
                "estimated_duration": "5-15 minutes",
                "platforms": ["google", "bing", "onlyfans", "pornhub"],
                "created_at": "2024-01-15T10:30:00Z"
            }
        },
        "InfringementExample": {
            "summary": "Content infringement detection",
            "description": "Example of detected content infringement",
            "value": {
                "id": 12345,
                "url": "https://example.com/stolen-content",
                "platform": "unauthorized-site",
                "confidence_score": 0.95,
                "match_type": "facial_recognition",
                "detected_at": "2024-01-15T10:30:00Z",
                "status": "detected",
                "evidence": {
                    "image_url": "https://storage.contentprotection.ai/evidence/12345.jpg",
                    "thumbnail": "https://storage.contentprotection.ai/thumbs/12345.jpg"
                }
            }
        },
        "TakedownRequestExample": {
            "summary": "DMCA takedown request",
            "description": "Example takedown request submission",
            "value": {
                "infringement_id": 12345,
                "urgency": "high",
                "additional_info": "This content was stolen from our premium OnlyFans account",
                "evidence_urls": [
                    "https://storage.contentprotection.ai/evidence/12345.jpg",
                    "https://original-platform.com/proof-of-ownership"
                ]
            }
        }
    })

    # Enhanced error responses
    openapi_schema["components"]["responses"] = {
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
                    },
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
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
                    },
                    "example": {"detail": "Could not validate credentials"}
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
                    },
                    "example": {
                        "detail": "Rate limit exceeded",
                        "retry_after": 900
                    }
                }
            }
        },
        "ServerError": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {"type": "string"},
                            "error_id": {"type": "string"}
                        }
                    },
                    "example": {
                        "detail": "An unexpected error occurred",
                        "error_id": "err_12345abc"
                    }
                }
            }
        }
    }

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


def add_api_route_examples(app: FastAPI) -> None:
    """Add enhanced examples to API routes."""
    
    # This function can be called after all routes are added
    # to inject additional examples and documentation
    
    pass


# Rate limiting documentation
RATE_LIMITS = {
    "authentication": {
        "login": "5 requests per 15 minutes",
        "register": "3 requests per hour",
        "password_reset": "3 requests per hour"
    },
    "scanning": {
        "manual_scan": {
            "free": "10 per day",
            "premium": "50 per day", 
            "enterprise": "unlimited"
        },
        "url_scan": {
            "free": "100 per day",
            "premium": "500 per day",
            "enterprise": "unlimited"
        }
    },
    "takedowns": {
        "submit": {
            "free": "10 per month",
            "premium": "100 per month",
            "enterprise": "unlimited"
        }
    }
}

# Common HTTP status codes and their meanings in our API
HTTP_STATUS_CODES = {
    200: "Success - Request completed successfully",
    201: "Created - Resource created successfully",
    202: "Accepted - Request accepted for processing",
    400: "Bad Request - Invalid input or request format",
    401: "Unauthorized - Authentication required or invalid",
    403: "Forbidden - Insufficient permissions",
    404: "Not Found - Resource not found",
    409: "Conflict - Resource already exists or conflict",
    422: "Unprocessable Entity - Validation error",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - Server error occurred",
    503: "Service Unavailable - Service temporarily unavailable"
}