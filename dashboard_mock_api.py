#!/usr/bin/env python3
"""
Dashboard Mock API Server for AutoDMCA Frontend
Provides missing dashboard endpoints as mock data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import random
import uvicorn

app = FastAPI(
    title="AutoDMCA Dashboard Mock API",
    description="Mock API server for missing dashboard endpoints",
    version="1.0.0"
)

# CORS middleware - Allow localhost ports for development
origins = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
    "http://localhost:3006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
    "http://127.0.0.1:3004",
    "http://127.0.0.1:3005",
    "http://127.0.0.1:3006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data generators
def generate_mock_stats():
    """Generate mock dashboard statistics"""
    return {
        "total_profiles": random.randint(5, 25),
        "active_scans": random.randint(2, 8),
        "infringements_found": random.randint(15, 150),
        "takedowns_sent": random.randint(8, 75),
        "success_rate": round(random.uniform(75, 95), 1),
        "scan_coverage": round(random.uniform(80, 99), 1)
    }

def generate_mock_activity():
    """Generate mock recent activity"""
    activities = [
        "New infringement detected on Instagram",
        "DMCA takedown sent to YouTube",
        "Profile scan completed for @username",
        "Takedown successful - content removed",
        "Weekly scan report generated",
        "New infringement on TikTok detected",
        "Copyright claim filed",
        "Content monitoring activated"
    ]
    
    result = []
    for i in range(10):
        result.append({
            "id": i + 1,
            "type": random.choice(["infringement", "takedown", "scan", "report"]),
            "title": random.choice(activities),
            "description": f"Activity {i + 1} details",
            "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat() + "Z",
            "status": random.choice(["completed", "pending", "in_progress"])
        })
    return result

def generate_mock_analytics():
    """Generate mock analytics data"""
    data = []
    for i in range(30):
        date = datetime.now() - timedelta(days=i)
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "infringements": random.randint(0, 12),
            "takedowns": random.randint(0, 8),
            "removals": random.randint(0, 6)
        })
    return list(reversed(data))

# Dashboard endpoints
@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    base_stats = generate_mock_stats()
    return {
        "period": {
            "start": start_date.isoformat() + "Z",
            "end": end_date.isoformat() + "Z"
        },
        # Map API response to match frontend expectations
        "totalProfiles": base_stats["total_profiles"],
        "activeScans": base_stats["active_scans"],
        "infringementsFound": base_stats["infringements_found"],
        "takedownsSent": base_stats["takedowns_sent"],
        "successRate": base_stats["success_rate"],
        "scanCoverage": base_stats["scan_coverage"],
        # Add change percentages that frontend expects
        "profilesChange": round(random.uniform(-5, 15), 1),
        "scansChange": round(random.uniform(-10, 25), 1),
        "infringementsChange": round(random.uniform(-20, 30), 1),
        "takedownsChange": round(random.uniform(-15, 40), 1)
    }

@app.get("/api/v1/dashboard/activity")
async def get_dashboard_activity(limit: int = 10):
    """Get recent activity"""
    activities = generate_mock_activity()
    return {
        "activities": activities[:limit],
        "total": len(activities)
    }

@app.get("/api/v1/dashboard/analytics")
async def get_dashboard_analytics(granularity: str = "day"):
    """Get analytics data"""
    raw_data = generate_mock_analytics()
    
    # Transform raw data to Chart.js compatible format
    dates = [item["date"] for item in raw_data]
    infringements = [item["infringements"] for item in raw_data]
    takedowns = [item["takedowns"] for item in raw_data]
    removals = [item["removals"] for item in raw_data]
    
    # Generate platform distribution data for doughnut chart
    platforms = ["Instagram", "TikTok", "YouTube", "Facebook", "Twitter"]
    platform_data = [random.randint(5, 30) for _ in platforms]
    platform_colors = [
        "#E1306C",  # Instagram
        "#000000",  # TikTok
        "#FF0000",  # YouTube
        "#1877F2",  # Facebook
        "#1DA1F2"   # Twitter
    ]
    
    # Generate success rate data for bar chart
    success_rates = [round(random.uniform(70, 95), 1) for _ in platforms]
    
    return {
        "granularity": granularity,
        "data": raw_data,
        # Chart.js compatible data structures
        "monthlyTrends": {
            "labels": dates,
            "datasets": [
                {
                    "label": "Threats Detected",
                    "data": infringements,
                    "borderColor": "#ff6384",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "tension": 0.4
                },
                {
                    "label": "Actions Taken",
                    "data": takedowns,
                    "borderColor": "#36a2eb",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "tension": 0.4
                },
                {
                    "label": "Content Removed",
                    "data": removals,
                    "borderColor": "#4bc0c0",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.4
                }
            ]
        },
        "platformDistribution": {
            "labels": platforms,
            "datasets": [{
                "data": platform_data,
                "backgroundColor": platform_colors,
                "borderColor": platform_colors,
                "borderWidth": 1
            }]
        },
        "successRateByPlatform": {
            "labels": platforms,
            "datasets": [{
                "label": "Success Rate (%)",
                "data": success_rates,
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }]
        }
    }

@app.get("/api/v1/dashboard/usage")
async def get_dashboard_usage():
    """Get usage statistics"""
    scans_used = random.randint(45, 95)
    scans_limit = 100
    success_rate = round(random.uniform(75, 95), 1)
    
    return {
        # Map to frontend expectations
        "scansUsed": scans_used,
        "scansLimit": scans_limit,
        "profilesUsed": random.randint(3, 8),
        "profilesLimit": 10,
        "storageUsed": round(random.uniform(1.2, 4.8), 1),
        "storageLimit": 5.0,
        "successRate": success_rate,
        "monthlySuccessRate": success_rate,
        "resetDate": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat() + "Z",
        "billingPeriod": {
            "start": (datetime.now().replace(day=1)).isoformat() + "Z",
            "end": (datetime.now().replace(day=28)).isoformat() + "Z"
        }
    }

@app.get("/api/v1/dashboard/quick-actions")
async def get_quick_actions():
    """Get quick actions"""
    return [
        {
            "id": "new_scan",
            "title": "Start New Scan",
            "description": "Scan for new infringements",
            "icon": "pi-search",
            "action": "/profiles?action=scan"
        },
        {
            "id": "create_profile",
            "title": "Add Profile",
            "description": "Create a new protected profile",
            "icon": "pi-user-plus",
            "action": "/profiles?action=create"
        },
        {
            "id": "view_reports",
            "title": "View Reports",
            "description": "Check latest reports",
            "icon": "pi-chart-line",
            "action": "/reports"
        }
    ]

@app.get("/api/v1/dashboard/preferences")
async def get_dashboard_preferences():
    """Get dashboard preferences"""
    return {
        "theme": "light",
        "auto_refresh": True,
        "refresh_interval": 300,
        "show_notifications": True,
        "compact_view": False
    }

@app.put("/api/v1/dashboard/preferences")
async def update_dashboard_preferences(preferences: dict):
    """Update dashboard preferences"""
    return preferences

@app.get("/api/v1/dashboard/platform-stats")
async def get_platform_stats():
    """Get platform statistics"""
    platforms = ["instagram", "tiktok", "youtube", "facebook", "twitter"]
    stats = {}
    for platform in platforms:
        stats[platform] = {
            "infringements": random.randint(5, 50),
            "takedowns": random.randint(2, 25),
            "success_rate": round(random.uniform(70, 95), 1)
        }
    return stats

@app.get("/api/v1/dashboard/platform-distribution")
async def get_platform_distribution():
    """Get platform distribution statistics"""
    platforms = ["instagram", "tiktok", "youtube", "facebook", "twitter"]
    total = random.randint(80, 120)
    distribution = []
    
    for platform in platforms:
        count = random.randint(5, 30)
        percentage = round((count / total) * 100, 1)
        distribution.append({
            "platform": platform,
            "count": count,
            "percentage": percentage
        })
    
    return {
        "platforms": distribution,
        "total": total
    }

# Mock profiles endpoint
@app.get("/api/v1/profiles")
async def get_profiles():
    """Mock profiles endpoint"""
    profiles = []
    for i in range(5):
        profiles.append({
            "id": i + 1,
            "name": f"Profile {i + 1}",
            "stage_name": f"@user{i + 1}",
            "description": f"Content creator profile {i + 1}",
            "status": random.choice(["active", "inactive", "scanning"]),
            "platforms": random.sample(["instagram", "tiktok", "youtube"], 2),
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat() + "Z"
        })
    
    return {
        "items": profiles,
        "total": len(profiles),
        "page": 1,
        "pages": 1,
        "size": 20
    }

# Mock infringements endpoint
@app.get("/api/v1/infringements")
async def get_infringements(include_stats: bool = False):
    """Mock infringements endpoint"""
    infringements = []
    for i in range(8):
        infringements.append({
            "id": i + 1,
            "profile_id": random.randint(1, 5),
            "platform": random.choice(["instagram", "tiktok", "youtube"]),
            "url": f"https://example.com/content/{i + 1}",
            "status": random.choice(["detected", "submitted", "resolved"]),
            "severity": random.choice(["low", "medium", "high"]),
            "confidence": round(random.uniform(0.7, 0.99), 2),
            "detected_at": (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat() + "Z"
        })
    
    result = {
        "items": infringements,
        "total": len(infringements),
        "page": 1,
        "pages": 1,
        "size": 20
    }
    
    if include_stats:
        result["stats"] = {
            "total": len(infringements),
            "by_status": {
                "detected": 3,
                "submitted": 3,
                "resolved": 2
            },
            "by_platform": {
                "instagram": 3,
                "tiktok": 3,
                "youtube": 2
            }
        }
    
    return result

# Mock takedowns endpoint
@app.get("/api/v1/takedowns")
async def get_takedowns(include_stats: bool = False):
    """Mock takedowns endpoint"""
    takedowns = []
    for i in range(6):
        takedowns.append({
            "id": i + 1,
            "infringement_id": i + 1,
            "platform": random.choice(["instagram", "tiktok", "youtube"]),
            "status": random.choice(["pending", "sent", "successful", "rejected"]),
            "submitted_at": (datetime.now() - timedelta(hours=random.randint(1, 120))).isoformat() + "Z"
        })
    
    result = {
        "items": takedowns,
        "total": len(takedowns),
        "page": 1,
        "pages": 1,
        "size": 20
    }
    
    if include_stats:
        result["stats"] = {
            "total": len(takedowns),
            "success_rate": 75.5,
            "by_status": {
                "pending": 1,
                "sent": 2,
                "successful": 2,
                "rejected": 1
            }
        }
    
    return result

# Auth endpoints
@app.post("/api/v1/auth/login")
async def login(credentials: dict):
    """Mock login endpoint"""
    return {
        "accessToken": "mock-access-token-12345",
        "refreshToken": "mock-refresh-token-67890",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True
        }
    }

@app.post("/api/v1/auth/register")
async def register(user_data: dict):
    """Mock register endpoint"""
    return {
        "message": "Registration successful",
        "user": {
            "id": 2,
            "email": user_data.get("email", "new@example.com"),
            "full_name": user_data.get("full_name", "New User"),
            "is_active": True,
            "is_verified": False
        }
    }

@app.get("/api/v1/users/me")
async def get_current_user():
    """Mock current user endpoint"""
    return {
        "id": 1,
        "email": "user@example.com",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
        "phone": "+1234567890",
        "company": "Test Company",
        "created_at": "2024-01-01T00:00:00Z"
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat() + "Z",
        "service": "dashboard-mock-api"
    }

if __name__ == "__main__":
    print("Starting Dashboard Mock API server on port 8080...")
    print("This provides missing dashboard endpoints for the frontend")
    print("Available endpoints:")
    print("- POST /api/v1/auth/login")
    print("- POST /api/v1/auth/register")
    print("- GET /api/v1/users/me")
    print("- GET /api/v1/dashboard/stats")
    print("- GET /api/v1/dashboard/activity") 
    print("- GET /api/v1/dashboard/analytics")
    print("- GET /api/v1/dashboard/usage")
    print("- GET /api/v1/dashboard/quick-actions")
    print("- GET /api/v1/dashboard/preferences")
    print("- GET /api/v1/dashboard/platform-stats")
    print("- GET /api/v1/dashboard/platform-distribution")
    print("- GET /api/v1/profiles")
    print("- GET /api/v1/infringements")
    print("- GET /api/v1/takedowns")
    print("- GET /health")
    print("")
    print("Access at: http://localhost:8080")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)