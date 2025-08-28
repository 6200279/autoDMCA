#!/usr/bin/env python3
"""
Dashboard Mock API Server for AutoDMCA Frontend
Provides missing dashboard endpoints as mock data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from datetime import datetime, timedelta
import math
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
    """Mock profiles endpoint with comprehensive data"""
    statuses = ["active", "inactive", "scanning", "paused", "error"]
    platform_names = ["instagram", "tiktok", "youtube", "onlyfans", "twitter", "snapchat"]
    profile_images = [
        "https://picsum.photos/64/64?random=1",
        "https://picsum.photos/64/64?random=2", 
        "https://picsum.photos/64/64?random=3",
        "https://picsum.photos/64/64?random=4",
        "https://picsum.photos/64/64?random=5"
    ]
    
    profiles = []
    for i in range(5):
        selected_platforms = random.sample(platform_names, random.randint(2, 4))
        platform_accounts = []
        
        for platform in selected_platforms:
            platform_accounts.append({
                "id": f"{platform}_{i}",
                "name": platform.title(),
                "username": f"@creator{i+1}_{platform}",
                "isConnected": random.choice([True, False]),
                "followers": random.randint(1000, 100000),
                "platform": platform,
                "lastSync": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat() + "Z",
                "scanEnabled": random.choice([True, False])
            })
        
        last_scan = datetime.now() - timedelta(hours=random.randint(1, 168))
        created_at = datetime.now() - timedelta(days=random.randint(30, 365))
        
        profile = {
            "id": str(i + 1),
            "name": f"Creator Profile {i + 1}",
            "stageName": f"@creator{i+1}",
            "description": f"Professional content creator specializing in {random.choice(['lifestyle', 'fitness', 'beauty', 'gaming', 'music'])} content",
            "image": profile_images[i],
            "status": random.choice(statuses),
            "platforms": platform_accounts,
            "totalScans": random.randint(10, 100),
            "infringementsFound": random.randint(0, 25),
            "lastScan": last_scan.isoformat() + "Z",
            "createdAt": created_at.isoformat() + "Z", 
            "successRate": round(random.uniform(75, 98), 1),
            "scanFrequency": random.choice(["daily", "weekly", "monthly"]),
            "tags": random.sample(["premium", "verified", "new", "high-volume", "protected"], random.randint(1, 3)),
            
            # Additional profile data for enhanced UI
            "category": random.choice(["Adult Entertainment", "Fitness", "Lifestyle", "Gaming", "Music"]),
            "priority": random.choice(["low", "normal", "high"]),
            "scanCost": round(random.uniform(5.99, 29.99), 2),
            "nextScan": (datetime.now() + timedelta(hours=random.randint(1, 24))).isoformat() + "Z",
            "totalInfringements": random.randint(5, 150),
            "resolvedInfringements": random.randint(3, 120),
            "pendingInfringements": random.randint(0, 15),
            
            # Analytics data
            "monthlyStats": {
                "scansPerformed": random.randint(4, 30),
                "infringementsFound": random.randint(0, 20),
                "takedownsSent": random.randint(0, 18),
                "successfulRemovals": random.randint(0, 15)
            },
            
            # Billing and subscription
            "subscriptionStatus": random.choice(["active", "paused", "cancelled"]),
            "lastBillingDate": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat() + "Z",
            "nextBillingDate": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat() + "Z",
            
            # Settings
            "notifications": {
                "email": random.choice([True, False]),
                "sms": random.choice([True, False]),
                "inApp": random.choice([True, False]),
                "frequency": random.choice(["immediate", "daily", "weekly"]),
                "infringementAlert": random.choice([True, False]),
                "scanComplete": random.choice([True, False]),
                "weeklyReport": random.choice([True, False])
            },
            
            # Performance metrics
            "avgResponseTime": round(random.uniform(2.5, 8.5), 1),
            "topInfringingPlatforms": random.sample(platform_names, 3),
            "protectedContent": random.randint(50, 500),
            "monitoredUrls": random.randint(10, 100)
        }
        
        profiles.append(profile)
    
    return {
        "items": profiles,
        "total": len(profiles),
        "page": 1,
        "pages": 1, 
        "size": 20
    }

# Mock infringements endpoint
@app.get("/api/v1/infringements")
async def get_infringements(page: int = 1, limit: int = 20, include_stats: bool = False):
    """Mock infringements endpoint"""
    # Generate a larger set of infringements to support pagination
    total_infringements = 25
    infringements = []
    
    for i in range(total_infringements):
        infringements.append({
            "id": i + 1,
            "profile_id": random.randint(1, 5),
            "platform": random.choice(["instagram", "tiktok", "youtube", "twitter", "facebook"]),
            "url": f"https://example.com/content/{i + 1}",
            "original_url": f"https://yoursite.com/original/{i + 1}",
            "status": random.choice(["detected", "submitted", "resolved", "pending"]),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "confidence": round(random.uniform(0.7, 0.99), 2),
            "detected_at": (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat() + "Z",
            "description": f"Potential copyright infringement detected on {random.choice(['Instagram', 'TikTok', 'YouTube'])}",
            "evidence_urls": [f"https://evidence.com/screenshot_{i + 1}.jpg"],
            "takedown_sent": random.choice([True, False]),
            "response_received": random.choice([True, False, None])
        })
    
    # Apply pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_infringements = infringements[start_idx:end_idx]
    
    total_pages = math.ceil(total_infringements / limit)
    
    result = {
        "items": paginated_infringements,
        "total": total_infringements,
        "page": page,
        "pages": total_pages,
        "size": limit,
        "has_next": page < total_pages,
        "has_prev": page > 1
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

# Search Engine Delisting Mock Endpoints
def generate_mock_delisting_requests():
    """Generate mock delisting requests"""
    statuses = ["pending", "processing", "submitted", "completed", "failed", "cancelled"]
    search_engines = ["google", "bing", "yahoo", "yandex"]
    priorities = ["low", "normal", "high", "urgent"]
    
    requests = []
    for i in range(25):  # Generate 25 mock requests
        created_at = datetime.now() - timedelta(hours=random.randint(1, 168))  # Last 7 days
        updated_at = created_at + timedelta(minutes=random.randint(5, 1440))
        
        status = random.choice(statuses)
        priority = random.choice(priorities)
        
        # Generate realistic URLs
        domains = ["example-infringing-site.com", "pirate-content.net", "stolen-media.org", "copyright-violation.site"]
        url = f"https://{random.choice(domains)}/content-{random.randint(1000, 9999)}"
        
        # Search engine responses
        selected_engines = random.sample(search_engines, random.randint(2, 4))
        engine_responses = []
        for engine in selected_engines:
            engine_responses.append({
                "engine": engine,
                "status": random.choice(statuses),
                "requestId": f"req_{engine}_{i}_{random.randint(1000, 9999)}",
                "submittedAt": created_at.isoformat() + "Z",
                "completedAt": updated_at.isoformat() + "Z" if status == "completed" else None
            })
        
        request = {
            "id": f"req_{i+1:03d}",
            "url": url,
            "originalContentUrl": f"https://original-creator.com/content-{i+1}",
            "reason": "Copyright infringement - unauthorized distribution",
            "evidenceUrl": f"https://evidence.creator.com/proof-{i+1}" if random.choice([True, False]) else None,
            "priority": priority,
            "status": status,
            "userId": "user_123",
            "profileId": f"profile_{random.randint(1, 5)}",
            "createdAt": created_at.isoformat() + "Z",
            "updatedAt": updated_at.isoformat() + "Z",
            "submittedAt": (created_at + timedelta(minutes=5)).isoformat() + "Z" if status != "pending" else None,
            "completedAt": updated_at.isoformat() + "Z" if status == "completed" else None,
            "errorMessage": "Temporary network error - will retry" if status == "failed" else None,
            "retryCount": random.randint(0, 3) if status in ["failed", "retrying"] else 0,
            "searchEngineResponses": engine_responses
        }
        requests.append(request)
    
    return requests

def generate_delisting_statistics():
    """Generate mock delisting statistics"""
    # Generate search engine breakdown
    engines = ["google", "bing", "yahoo", "yandex"]
    engine_breakdown = {}
    
    for engine in engines:
        total = random.randint(50, 200)
        successful = random.randint(int(total * 0.6), int(total * 0.9))
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        engine_breakdown[engine] = {
            "total": total,
            "successful": successful, 
            "failed": failed,
            "successRate": round(success_rate, 1)
        }
    
    # Calculate overall stats
    total_requests = sum(data["total"] for data in engine_breakdown.values())
    completed_requests = sum(data["successful"] for data in engine_breakdown.values())
    failed_requests = sum(data["failed"] for data in engine_breakdown.values())
    pending_requests = random.randint(5, 25)
    
    overall_success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
    
    # Generate recent activity
    recent_activity = []
    activity_types = ["submitted", "completed", "failed", "retry"]
    for i in range(10):
        activity = {
            "id": f"activity_{i+1}",
            "url": f"https://example-site-{i+1}.com/content",
            "status": random.choice(["completed", "failed", "processing", "pending"]),
            "searchEngine": random.choice(engines),
            "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat() + "Z",
            "type": random.choice(activity_types)
        }
        recent_activity.append(activity)
    
    return {
        "totalRequests": total_requests,
        "pendingRequests": pending_requests,
        "completedRequests": completed_requests,
        "failedRequests": failed_requests,
        "successRate": round(overall_success_rate, 1),
        "averageProcessingTime": round(random.uniform(30, 180), 1),  # minutes
        "searchEngineBreakdown": engine_breakdown,
        "recentActivity": recent_activity
    }

def generate_dashboard_metrics():
    """Generate mock dashboard metrics"""
    return {
        "activeRequests": random.randint(5, 20),
        "completedToday": random.randint(3, 15),
        "successRateToday": round(random.uniform(75, 95), 1),
        "avgResponseTime": round(random.uniform(45, 120), 1),  # minutes
        "systemAlerts": [
            {
                "id": "alert_1",
                "type": "Rate Limit Warning",
                "severity": "medium",
                "message": "Google API approaching rate limit",
                "triggeredAt": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
                "isActive": True
            },
            {
                "id": "alert_2", 
                "type": "Success Rate",
                "severity": "low",
                "message": "Yahoo delisting success rate below 80%",
                "triggeredAt": (datetime.now() - timedelta(hours=6)).isoformat() + "Z",
                "isActive": True
            }
        ],
        "recentActivity": [
            {
                "id": f"recent_{i}",
                "url": f"https://example-{i}.com/content",
                "status": random.choice(["completed", "failed", "processing"]),
                "createdAt": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat() + "Z"
            }
            for i in range(5)
        ]
    }

# Delisting API endpoints
@app.get("/api/v1/delisting/requests")
async def get_delisting_requests(
    page: int = 1,
    size: int = 10,
    status: str = None,
    search_engine: str = None,
    priority: str = None,
    date_from: str = None,
    date_to: str = None
):
    """Get paginated list of delisting requests"""
    all_requests = generate_mock_delisting_requests()
    
    # Apply filters
    filtered_requests = all_requests
    if status:
        filtered_requests = [r for r in filtered_requests if r["status"] == status]
    if search_engine:
        filtered_requests = [r for r in filtered_requests 
                           if any(resp["engine"] == search_engine for resp in r["searchEngineResponses"])]
    if priority:
        filtered_requests = [r for r in filtered_requests if r["priority"] == priority]
    
    # Pagination
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_requests = filtered_requests[start_idx:end_idx]
    
    return {
        "items": paginated_requests,
        "total": len(all_requests),
        "page": page,
        "pageSize": size,
        "totalPages": (len(all_requests) + size - 1) // size
    }

@app.get("/api/v1/delisting/requests/{request_id}")
async def get_delisting_request(request_id: str):
    """Get specific delisting request"""
    # Generate single request based on ID
    return {
        "id": request_id,
        "url": f"https://example-site.com/content-{request_id}",
        "status": "processing",
        "searchEngines": ["google", "bing"],
        "submittedAt": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
        "message": "Request is being processed"
    }

@app.post("/api/v1/delisting/requests")
async def submit_delisting_request(request_data: dict):
    """Submit new delisting request"""
    request_id = f"req_{random.randint(10000, 99999)}"
    
    return JSONResponse(
        status_code=201,
        content={
            "id": request_id,
            "url": request_data.get("url"),
            "status": "pending",
            "searchEngines": request_data.get("searchEngines", []),
            "submittedAt": datetime.now().isoformat() + "Z",
            "message": "Request submitted successfully"
        }
    )

@app.post("/api/v1/delisting/batch")
async def submit_batch_delisting(batch_data: dict):
    """Submit batch delisting request"""
    batch_id = f"batch_{random.randint(10000, 99999)}"
    urls = batch_data.get("urls", [])
    
    return JSONResponse(
        status_code=201,
        content={
            "id": batch_id,
            "totalUrls": len(urls),
            "processedUrls": 0,
            "successfulUrls": 0,
            "failedUrls": 0,
            "status": "pending",
            "createdAt": datetime.now().isoformat() + "Z",
            "updatedAt": datetime.now().isoformat() + "Z",
            "requests": []
        }
    )

@app.post("/api/v1/delisting/requests/{request_id}/cancel")
async def cancel_delisting_request(request_id: str):
    """Cancel delisting request"""
    return {
        "id": request_id,
        "url": f"https://example-site.com/content-{request_id}",
        "status": "cancelled",
        "searchEngines": ["google", "bing"],
        "submittedAt": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
        "message": "Request cancelled successfully"
    }

@app.post("/api/v1/delisting/requests/{request_id}/retry")
async def retry_delisting_request(request_id: str):
    """Retry failed delisting request"""
    return {
        "id": request_id,
        "url": f"https://example-site.com/content-{request_id}",
        "status": "pending",
        "searchEngines": ["google", "bing"],
        "submittedAt": datetime.now().isoformat() + "Z",
        "message": "Request retry initiated"
    }

@app.get("/api/v1/delisting/statistics")
async def get_delisting_statistics(
    date_from: str = None,
    date_to: str = None,
    search_engine: str = None
):
    """Get delisting statistics and analytics"""
    return generate_delisting_statistics()

@app.get("/api/v1/delisting/dashboard")  
async def get_delisting_dashboard():
    """Get real-time dashboard data"""
    return generate_dashboard_metrics()

@app.get("/api/v1/delisting/requests/{request_id}/verification")
async def get_verification_results(request_id: str):
    """Get verification results for a request"""
    engines = ["google", "bing", "yahoo", "yandex"]
    results = []
    
    for engine in random.sample(engines, 3):
        results.append({
            "searchEngine": engine,
            "url": f"https://example-site.com/content-{request_id}",
            "isDelisted": random.choice([True, False]),
            "lastSeen": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat() + "Z",
            "notes": f"Verified via {engine} search API"
        })
    
    return {
        "requestId": request_id,
        "verificationStatus": "completed",
        "results": results,
        "lastChecked": datetime.now().isoformat() + "Z"
    }

@app.post("/api/v1/delisting/requests/{request_id}/verify")
async def trigger_verification(request_id: str):
    """Trigger verification for a request"""
    return {"message": f"Verification triggered for request {request_id}"}

@app.post("/api/v1/delisting/bulk/cancel")
async def bulk_cancel_requests(request_data: dict):
    """Cancel multiple requests"""
    request_ids = request_data.get("request_ids", [])
    return {
        "cancelled": len(request_ids),
        "failed": 0
    }

@app.post("/api/v1/delisting/bulk/retry")
async def bulk_retry_requests(request_data: dict):
    """Retry multiple failed requests"""
    request_ids = request_data.get("request_ids", [])
    return {
        "retried": len(request_ids),
        "failed": 0
    }

@app.post("/api/v1/delisting/bulk/update-status")
async def bulk_update_status(request_data: dict):
    """Update status for multiple requests"""
    request_ids = request_data.get("request_ids", [])
    return {
        "updated": len(request_ids)
    }

# Submissions Mock Endpoints
@app.get("/api/v1/submissions")
async def get_submissions(page: int = 1, limit: int = 20):
    """Mock submissions endpoint"""
    mock_submissions = [
        {
            "id": f"sub_{i}",
            "title": f"Content Submission {i}",
            "description": f"Mock submission {i} for testing",
            "content_type": ["image", "video", "audio", "text"][i % 4],
            "status": ["pending", "processing", "completed", "failed"][i % 4],
            "upload_date": "2024-01-01T00:00:00Z",
            "file_count": 5 + i,
            "profile_id": f"profile_{i % 3}",
            "profile_name": f"Test Profile {i % 3}",
            "progress": min(100, 20 * i),
            "metadata": {
                "total_files": 5 + i,
                "processed_files": min(5 + i, int((5 + i) * 0.7)),
                "failed_files": 0,
                "estimated_completion": "2024-01-01T01:00:00Z"
            }
        }
        for i in range(1, 16)
    ]
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_submissions = mock_submissions[start_idx:end_idx]
    
    return {
        "submissions": paginated_submissions,
        "total": len(mock_submissions),
        "page": page,
        "limit": limit,
        "total_pages": (len(mock_submissions) + limit - 1) // limit
    }

@app.post("/api/v1/submissions")
async def create_submission(submission_data: dict):
    """Mock create submission endpoint"""
    return {
        "id": "sub_new",
        "message": "Submission created successfully",
        "status": "pending",
        "upload_url": "https://mock-upload-url.com/upload"
    }

@app.get("/api/v1/submissions/{submission_id}")
async def get_submission(submission_id: str):
    """Mock get single submission endpoint"""
    return {
        "id": submission_id,
        "title": f"Submission {submission_id}",
        "description": f"Mock submission {submission_id}",
        "content_type": "image",
        "status": "completed",
        "upload_date": "2024-01-01T00:00:00Z",
        "file_count": 10,
        "profile_id": "profile_1",
        "profile_name": "Test Profile 1",
        "progress": 100
    }

# Templates Mock Endpoints
@app.get("/api/v1/templates")
async def get_templates(
    page: int = 1, 
    limit: int = 20, 
    sort_by: str = "updated_at", 
    sort_order: str = "desc",
    category: str = None
):
    """Mock templates endpoint"""
    mock_templates = [
        {
            "id": f"tmpl_{i}",
            "name": f"DMCA Template {i}",
            "description": f"Professional DMCA takedown template {i}",
            "category": ["standard", "image", "video", "audio", "social_media"][i % 5],
            "content": f"This is the content of template {i}...",
            "is_active": True,
            "is_default": i == 1,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "usage_count": 50 - i * 2,
            "success_rate": 85 + (i % 15),
            "platform_specific": i % 2 == 0,
            "supported_platforms": ["YouTube", "Instagram", "TikTok", "Facebook"][:i % 4 + 1],
            "variables": [
                {"name": "infringer_name", "description": "Name of the infringer"},
                {"name": "infringement_url", "description": "URL of infringing content"},
                {"name": "original_content", "description": "Description of original content"}
            ]
        }
        for i in range(1, 26)
    ]
    
    # Filter by category if provided
    if category:
        mock_templates = [t for t in mock_templates if t["category"] == category]
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_templates = mock_templates[start_idx:end_idx]
    
    return {
        "templates": paginated_templates,
        "total": len(mock_templates),
        "page": page,
        "limit": limit,
        "total_pages": (len(mock_templates) + limit - 1) // limit
    }

@app.get("/api/v1/templates/categories")
async def get_template_categories():
    """Mock template categories endpoint"""
    return [
        {
            "id": "standard",
            "name": "Standard DMCA",
            "description": "General purpose DMCA templates",
            "template_count": 8
        },
        {
            "id": "image", 
            "name": "Image Copyright",
            "description": "Templates for image copyright infringement",
            "template_count": 5
        },
        {
            "id": "video",
            "name": "Video Copyright", 
            "description": "Templates for video copyright infringement",
            "template_count": 6
        },
        {
            "id": "audio",
            "name": "Audio Copyright",
            "description": "Templates for audio copyright infringement", 
            "template_count": 4
        },
        {
            "id": "social_media",
            "name": "Social Media",
            "description": "Platform-specific social media templates",
            "template_count": 7
        }
    ]

@app.post("/api/v1/templates")
async def create_template(template_data: dict):
    """Mock create template endpoint"""
    return {
        "id": "tmpl_new",
        "message": "Template created successfully",
        **template_data
    }

@app.get("/api/v1/templates/{template_id}")
async def get_template(template_id: str):
    """Mock get single template endpoint"""
    return {
        "id": template_id,
        "name": f"DMCA Template {template_id}",
        "description": f"Professional template {template_id}",
        "category": "standard",
        "content": "Template content here...",
        "is_active": True,
        "variables": [
            {"name": "infringer_name", "description": "Name of the infringer"},
            {"name": "infringement_url", "description": "URL of infringing content"}
        ]
    }

@app.put("/api/v1/templates/{template_id}")
async def update_template(template_id: str, template_data: dict):
    """Mock update template endpoint"""
    return {
        "id": template_id,
        "message": "Template updated successfully",
        **template_data
    }

@app.delete("/api/v1/templates/{template_id}")
async def delete_template(template_id: str):
    """Mock delete template endpoint"""
    return {
        "message": f"Template {template_id} deleted successfully"
    }

# Placeholder image endpoint for missing images
@app.get("/api/placeholder/{width}/{height}")
async def get_placeholder_image(width: int, height: int):
    """Generate placeholder image URL - redirect to external service"""
    return RedirectResponse(f"https://via.placeholder.com/{width}x{height}/e2e8f0/64748b?text=Image")

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
    print("- GET /api/v1/submissions")
    print("- POST /api/v1/submissions")
    print("- GET /api/v1/templates")
    print("- POST /api/v1/templates")
    print("- GET /api/v1/templates/categories")
    print("- GET /health")
    print("")
    print("Access at: http://localhost:8080")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)