from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002', 'http://localhost:3003', 'http://localhost:3004', 'http://localhost:3005', 'http://localhost:3006', 'http://localhost:3007'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# Auth endpoints
@app.post('/api/v1/auth/login')
async def login():
    return {
        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzI0NTMzOTg3fQ.test',
        'refresh_token': 'mock-refresh-token-67890',
        'user': {
            'id': '1',
            'email': 'user@example.com',
            'name': 'Test User'
        }
    }

@app.post('/api/v1/auth/refresh')
async def refresh_token():
    return {
        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzI0NTMzOTg3fQ.new',
        'refresh_token': 'mock-refresh-token-67890-new'
    }

@app.get('/api/v1/users/me')
async def get_user():
    return {
        'id': '1',
        'email': 'user@example.com',
        'name': 'Test User'
    }

# Dashboard endpoints
@app.get('/api/v1/dashboard/stats')
async def get_stats():
    return {
        'total_infringements': 1247,
        'active_takedowns': 89,
        'successful_removals': 934,
        'pending_requests': 45,
        'success_rate': 85.2
    }

@app.get('/api/v1/dashboard/usage')
async def get_usage():
    return {
        'api_calls': 2450,
        'scans_performed': 156,
        'notifications_sent': 23,
        'monthly_limit': 5000,
        'usage_percentage': 49.0
    }

@app.get('/api/v1/dashboard/activity')
async def get_activity():
    return [
        {
            'id': '1',
            'type': 'takedown_sent',
            'description': 'DMCA notice sent to example-site.com',
            'timestamp': '2024-08-24T14:30:00Z'
        },
        {
            'id': '2', 
            'type': 'content_removed',
            'description': 'Content removed from social-platform.com',
            'timestamp': '2024-08-24T13:15:00Z'
        },
        {
            'id': '3',
            'type': 'scan_completed',
            'description': 'Weekly content scan completed',
            'timestamp': '2024-08-24T12:00:00Z'
        }
    ]

@app.get('/api/v1/dashboard/analytics')
async def get_analytics():
    return {
        'takedown_trends': [
            {'date': '2024-08-20', 'count': 12},
            {'date': '2024-08-21', 'count': 8},
            {'date': '2024-08-22', 'count': 15},
            {'date': '2024-08-23', 'count': 9},
            {'date': '2024-08-24', 'count': 7}
        ],
        'success_metrics': {
            'total_sent': 234,
            'successful': 198,
            'pending': 23,
            'failed': 13
        }
    }

@app.get('/api/v1/dashboard/platform-distribution')
async def get_platform_distribution():
    return [
        {'platform': 'Google Images', 'count': 45, 'percentage': 32.1},
        {'platform': 'Social Media', 'count': 38, 'percentage': 27.1},
        {'platform': 'File Sharing', 'count': 29, 'percentage': 20.7},
        {'platform': 'Forums', 'count': 18, 'percentage': 12.9},
        {'platform': 'Other', 'count': 10, 'percentage': 7.1}
    ]

@app.get('/api/v1/dashboard/preferences')
async def get_preferences():
    return {
        'theme': 'light',
        'notifications_enabled': True,
        'email_reports': True,
        'dashboard_layout': 'grid'
    }

@app.get('/api/v1/dashboard/quick-actions')
async def get_quick_actions():
    return {
        'pending_reviews': 5,
        'new_matches': 12,
        'urgent_takedowns': 2,
        'recent_removals': 8
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)