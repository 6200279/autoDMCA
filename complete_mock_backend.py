from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any, Dict
import uvicorn
from datetime import datetime, timedelta
import json
import uuid
import random
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002', 'http://localhost:3003', 'http://localhost:3004', 'http://localhost:3005', 'http://localhost:3006', 'http://localhost:3007', 'http://localhost:3008', 'http://localhost:3009', 'http://localhost:3010'],
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

# Data Models
class CreateSubmission(BaseModel):
    title: str
    type: str  # ContentType
    priority: str  # PriorityLevel
    urls: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    category: Optional[str] = None
    description: Optional[str] = None
    auto_monitoring: Optional[bool] = False
    notify_on_infringement: Optional[bool] = False
    profile_id: Optional[int] = None

class BulkSubmission(BaseModel):
    submissions: List[CreateSubmission]
    apply_to_all: Optional[Dict[str, Any]] = {}

# Mock Data Storage
mock_submissions = {}
mock_profiles = [
    {
        'id': 1, 
        'name': 'Photography Portfolio', 
        'description': 'Professional photography work',
        'platforms': ['Instagram', 'Flickr', 'SmugMug'],
        'image': 'https://via.placeholder.com/40x40/4F46E5/FFFFFF?text=PP',
        'status': 'active',
        'customColor': '#4F46E5',
        'lastScan': '2025-08-24T16:30:00Z',
        'scanFrequency': '6 hours',
        'analytics': {
            'totalContentProtected': 1247,
            'infringementsFound': 23,
            'takedownsSuccessful': 19
        }
    },
    {
        'id': 2, 
        'name': 'Digital Art Collection', 
        'description': 'Original digital artwork',
        'platforms': ['DeviantArt', 'Behance'],
        'image': 'https://via.placeholder.com/40x40/7C3AED/FFFFFF?text=DA',
        'status': 'active',
        'customColor': '#7C3AED',
        'lastScan': '2025-08-24T17:15:00Z',
        'scanFrequency': '12 hours',
        'analytics': {
            'totalContentProtected': 856,
            'infringementsFound': 12,
            'takedownsSuccessful': 11
        }
    },
    {
        'id': 3, 
        'name': 'Brand Assets', 
        'description': 'Company logos and branding materials',
        'platforms': ['LinkedIn', 'Twitter', 'Facebook'],
        'image': 'https://via.placeholder.com/40x40/059669/FFFFFF?text=BA',
        'status': 'active',
        'customColor': '#059669',
        'lastScan': '2025-08-24T18:00:00Z',
        'scanFrequency': '4 hours',
        'analytics': {
            'totalContentProtected': 432,
            'infringementsFound': 7,
            'takedownsSuccessful': 7
        }
    },
    {
        'id': 4, 
        'name': 'Personal Content', 
        'description': 'Personal photos and videos',
        'platforms': ['TikTok', 'YouTube'],
        'image': 'https://via.placeholder.com/40x40/DC2626/FFFFFF?text=PC',
        'status': 'paused',
        'customColor': '#DC2626',
        'lastScan': '2025-08-23T14:20:00Z',
        'scanFrequency': '24 hours',
        'analytics': {
            'totalContentProtected': 289,
            'infringementsFound': 3,
            'takedownsSuccessful': 2
        }
    }
]

def generate_mock_submission(data: CreateSubmission = None, submission_id: str = None) -> Dict[str, Any]:
    """Generate realistic mock submission data"""
    if not submission_id:
        submission_id = str(uuid.uuid4())
    
    statuses = ['pending', 'processing', 'active', 'completed', 'failed', 'cancelled']
    status = random.choice(statuses) if not data else random.choice(statuses[:3])  # New submissions start with earlier statuses
    
    # Calculate progress based on status
    progress = 0
    if status == 'pending':
        progress = 0
    elif status == 'processing':
        progress = random.randint(1, 85)
    elif status == 'active':
        progress = random.randint(85, 99)
    elif status == 'completed':
        progress = 100
    elif status == 'failed':
        progress = random.randint(10, 70)
    elif status == 'cancelled':
        progress = random.randint(5, 50)
    
    created_at = datetime.now() - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    
    # Mock URLs if not provided
    urls = []
    if data and data.urls:
        urls = data.urls
    else:
        url_templates = [
            'https://example-social.com/user/profile123',
            'https://photo-sharing-site.com/gallery/456',
            'https://video-platform.com/watch/789',
            'https://blog-site.com/post/my-content',
            'https://marketplace.com/listing/content-item'
        ]
        urls = random.sample(url_templates, random.randint(1, 3))
    
    total_urls = len(urls)
    processed_urls = int(total_urls * (progress / 100))
    if status == 'failed' and processed_urls > 0:
        valid_urls = max(0, processed_urls - random.randint(1, max(1, processed_urls)))
    else:
        valid_urls = processed_urls
    invalid_urls = processed_urls - valid_urls
    
    return {
        'id': submission_id,
        'user_id': 1,
        'profile_id': data.profile_id if data else random.choice(mock_profiles)['id'],
        'type': data.type if data else random.choice(['images', 'videos', 'documents', 'urls']),
        'priority': data.priority if data else random.choice(['normal', 'high', 'urgent']),
        'status': status,
        'title': data.title if data else f'Content Submission {random.randint(100, 999)}',
        'urls': urls,
        'files': [f'https://cdn.example.com/files/{uuid.uuid4()}.jpg'] if random.choice([True, False]) else [],
        'tags': data.tags if data else random.sample(['copyright', 'infringement', 'brand', 'personal', 'commercial'], random.randint(1, 3)),
        'category': data.category if data else random.choice(['Photography', 'Artwork', 'Branding', 'Personal', 'Commercial']),
        'description': data.description if data else f'Protection for {random.choice(["personal", "commercial", "artistic"])} content against unauthorized usage',
        'progress_percentage': progress,
        'estimated_completion': (created_at + timedelta(hours=random.randint(2, 48))).isoformat() if status in ['pending', 'processing'] else None,
        'auto_monitoring': data.auto_monitoring if data else random.choice([True, False]),
        'notify_on_infringement': data.notify_on_infringement if data else random.choice([True, False]),
        'created_at': created_at.isoformat(),
        'updated_at': (created_at + timedelta(minutes=random.randint(1, 60))).isoformat(),
        'completed_at': (created_at + timedelta(hours=random.randint(1, 24))).isoformat() if status == 'completed' else None,
        'error_message': random.choice([
            'Failed to access protected URL',
            'Invalid file format detected',
            'Network timeout during processing',
            'Service temporarily unavailable'
        ]) if status == 'failed' else None,
        'total_urls': total_urls,
        'processed_urls': processed_urls,
        'valid_urls': valid_urls,
        'invalid_urls': invalid_urls
    }

# Generate initial mock submissions
for i in range(15):
    submission_id = str(uuid.uuid4())
    mock_submissions[submission_id] = generate_mock_submission(submission_id=submission_id)

# Profile endpoints
@app.get('/api/v1/profiles')
async def get_profiles():
    return mock_profiles

# Core Submission Endpoints
@app.get('/api/v1/submissions')
async def get_submissions(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: Optional[int] = Query(1),
    limit: Optional[int] = Query(10)
):
    submissions = list(mock_submissions.values())
    
    # Apply filters
    if status:
        submissions = [s for s in submissions if s['status'] == status]
    if type:
        submissions = [s for s in submissions if s['type'] == type]
    if priority:
        submissions = [s for s in submissions if s['priority'] == priority]
    
    # Sort by creation date (newest first)
    submissions.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_submissions = submissions[start_idx:end_idx]
    
    return {
        'items': paginated_submissions,
        'total': len(submissions),
        'page': page,
        'per_page': limit,
        'pages': (len(submissions) + limit - 1) // limit
    }

@app.post('/api/v1/submissions')
async def create_submission(submission: CreateSubmission):
    submission_id = str(uuid.uuid4())
    new_submission = generate_mock_submission(submission, submission_id)
    mock_submissions[submission_id] = new_submission
    return new_submission

@app.get('/api/v1/submissions/{submission_id}')
async def get_submission(submission_id: str):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    return mock_submissions[submission_id]

@app.put('/api/v1/submissions/{submission_id}')
async def update_submission(submission_id: str, update_data: Dict[str, Any]):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission = mock_submissions[submission_id]
    # Update fields
    for key, value in update_data.items():
        if key in submission:
            submission[key] = value
    
    submission['updated_at'] = datetime.now().isoformat()
    return submission

@app.delete('/api/v1/submissions/{submission_id}')
async def delete_submission(submission_id: str):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    del mock_submissions[submission_id]
    return {'message': 'Submission deleted successfully'}

# Submission Actions
@app.post('/api/v1/submissions/{submission_id}/cancel')
async def cancel_submission(submission_id: str):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission = mock_submissions[submission_id]
    if submission['status'] in ['completed', 'cancelled', 'failed']:
        raise HTTPException(status_code=400, detail="Cannot cancel submission in current status")
    
    submission['status'] = 'cancelled'
    submission['updated_at'] = datetime.now().isoformat()
    return submission

@app.post('/api/v1/submissions/{submission_id}/retry')
async def retry_submission(submission_id: str):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission = mock_submissions[submission_id]
    if submission['status'] != 'failed':
        raise HTTPException(status_code=400, detail="Can only retry failed submissions")
    
    submission['status'] = 'pending'
    submission['progress_percentage'] = 0
    submission['error_message'] = None
    submission['updated_at'] = datetime.now().isoformat()
    submission['estimated_completion'] = (datetime.now() + timedelta(hours=random.randint(2, 24))).isoformat()
    return submission

@app.get('/api/v1/submissions/{submission_id}/progress')
async def get_submission_progress(submission_id: str):
    if submission_id not in mock_submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission = mock_submissions[submission_id]
    
    # Generate realistic progress data
    progress_data = {
        'submission_id': submission_id,
        'status': submission['status'],
        'progress_percentage': submission['progress_percentage'],
        'current_stage': {
            'pending': 'Queued for processing',
            'processing': 'Analyzing content and URLs',
            'active': 'Monitoring for infringements',
            'completed': 'Monitoring complete',
            'failed': 'Processing failed',
            'cancelled': 'Processing cancelled'
        }.get(submission['status'], 'Unknown'),
        'estimated_completion': submission['estimated_completion'],
        'processed_items': submission['processed_urls'],
        'total_items': submission['total_urls'],
        'stages': [
            {'name': 'Validation', 'status': 'completed', 'progress': 100},
            {'name': 'Content Analysis', 'status': 'completed' if submission['progress_percentage'] > 25 else 'pending', 'progress': min(100, submission['progress_percentage'] * 4)},
            {'name': 'URL Processing', 'status': 'completed' if submission['progress_percentage'] > 50 else ('active' if submission['progress_percentage'] > 25 else 'pending'), 'progress': max(0, min(100, (submission['progress_percentage'] - 25) * 4))},
            {'name': 'Monitoring Setup', 'status': 'completed' if submission['progress_percentage'] > 75 else ('active' if submission['progress_percentage'] > 50 else 'pending'), 'progress': max(0, min(100, (submission['progress_percentage'] - 50) * 4))},
            {'name': 'Activation', 'status': 'completed' if submission['progress_percentage'] == 100 else ('active' if submission['progress_percentage'] > 75 else 'pending'), 'progress': max(0, (submission['progress_percentage'] - 75) * 4)}
        ],
        'last_updated': submission['updated_at']
    }
    
    if submission['error_message']:
        progress_data['error'] = submission['error_message']
    
    return progress_data

# File Upload Endpoints
@app.post('/api/v1/submissions/upload')
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        # Mock file processing
        file_id = str(uuid.uuid4())
        file_url = f'https://cdn.example.com/uploads/{file_id}/{file.filename}'
        
        uploaded_files.append({
            'id': file_id,
            'filename': file.filename,
            'size': random.randint(100000, 10000000),  # Mock file size
            'content_type': file.content_type,
            'url': file_url,
            'thumbnail_url': f'{file_url}_thumb.jpg',
            'upload_date': datetime.now().isoformat(),
            'status': 'uploaded'
        })
    
    return {
        'files': uploaded_files,
        'total_count': len(uploaded_files),
        'total_size': sum(f['size'] for f in uploaded_files)
    }

@app.post('/api/v1/submissions/validate-urls')
async def validate_urls(request: Dict[str, List[str]]):
    urls = request.get('urls', [])
    results = []
    
    for url in urls:
        # Mock URL validation
        is_valid = not any(invalid in url.lower() for invalid in ['invalid', 'broken', '404'])
        domain = url.split('//')[1].split('/')[0] if '//' in url else url.split('/')[0]
        
        validation_result = {
            'url': url,
            'is_valid': is_valid,
            'domain': domain,
            'platform': random.choice(['Facebook', 'Instagram', 'Twitter', 'YouTube', 'Generic']) if is_valid else None,
            'content_type': random.choice(['profile', 'image', 'video', 'post']) if is_valid else None,
            'error_message': random.choice([
                'URL is not accessible',
                'Invalid URL format',
                'Domain not found',
                'Connection timeout'
            ]) if not is_valid else None
        }
        results.append(validation_result)
    
    return {
        'results': results,
        'summary': {
            'total': len(results),
            'valid': len([r for r in results if r['is_valid']]),
            'invalid': len([r for r in results if not r['is_valid']])
        }
    }

@app.post('/api/v1/submissions/bulk')
async def bulk_create_submissions(bulk_request: BulkSubmission):
    created_submissions = []
    
    for submission_data in bulk_request.submissions:
        # Apply bulk settings if provided
        if bulk_request.apply_to_all:
            for key, value in bulk_request.apply_to_all.items():
                if not hasattr(submission_data, key) or getattr(submission_data, key) is None:
                    setattr(submission_data, key, value)
        
        submission_id = str(uuid.uuid4())
        new_submission = generate_mock_submission(submission_data, submission_id)
        mock_submissions[submission_id] = new_submission
        created_submissions.append(new_submission)
    
    return {
        'submissions': created_submissions,
        'total_created': len(created_submissions),
        'batch_id': str(uuid.uuid4())
    }

# Mock DMCA Templates endpoints
@app.get('/api/v1/templates')
async def get_templates(
    page: int = Query(1, description="Page number"),
    limit: int = Query(12, description="Items per page"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    language: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    sort_by: str = Query('updated_at'),
    sort_order: str = Query('desc')
):
    return await _get_templates_internal(page, limit, category, search, is_active, language, jurisdiction, sort_by, sort_order)

async def _get_templates_internal(
    page: int = 1,
    limit: int = 12,
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    language: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    sort_by: str = 'updated_at',
    sort_order: str = 'desc'
):
    # Mock template data
    templates = [
        {
            'id': 'tmpl_1',
            'name': 'Standard DMCA Takedown Notice',
            'description': 'A comprehensive DMCA takedown notice template for general use',
            'category': 'General DMCA',
            'content': '''Dear Copyright Agent,

I am writing to notify you of copyright infringement occurring on your platform. I am the copyright owner of the material described below, and I have a good faith belief that the use of this material is not authorized by me, my agent, or the law.

**Copyrighted Work:** {{work_title}}
**Copyright Owner:** {{copyright_owner}}
**Infringed Content URL:** {{infringing_url}}
**Description of Infringement:** {{infringement_description}}

I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner, or am authorized to act on behalf of the owner, of an exclusive right that is allegedly infringed.

Best regards,
{{sender_name}}
{{contact_information}}''',
            'variables': [
                {'name': 'work_title', 'label': 'Work Title', 'type': 'text', 'required': True, 'placeholder': 'Enter the title of your copyrighted work'},
                {'name': 'copyright_owner', 'label': 'Copyright Owner', 'type': 'text', 'required': True, 'placeholder': 'Your name or company name'},
                {'name': 'infringing_url', 'label': 'Infringing URL', 'type': 'url', 'required': True, 'placeholder': 'https://example.com/infringing-content'},
                {'name': 'infringement_description', 'label': 'Description of Infringement', 'type': 'textarea', 'required': True, 'placeholder': 'Describe how your work is being infringed'},
                {'name': 'sender_name', 'label': 'Your Name', 'type': 'text', 'required': True, 'placeholder': 'Your full name'},
                {'name': 'contact_information', 'label': 'Contact Information', 'type': 'textarea', 'required': True, 'placeholder': 'Email, phone, and address'}
            ],
            'is_active': True,
            'is_system': True,
            'created_at': '2024-01-15T08:00:00Z',
            'updated_at': '2024-08-20T14:30:00Z',
            'usage_count': 342,
            'tags': ['standard', 'general', 'takedown'],
            'language': 'en',
            'jurisdiction': 'US'
        },
        {
            'id': 'tmpl_2',
            'name': 'YouTube DMCA Takedown',
            'description': 'Specialized template for YouTube copyright takedown requests',
            'category': 'Video Platforms',
            'content': '''To YouTube Copyright Team,

I am submitting a copyright takedown request under the Digital Millennium Copyright Act for content hosted on your platform.

**Video URL:** {{video_url}}
**Video Title:** {{video_title}}
**Uploader:** {{uploader_name}}
**My Original Work:** {{original_work}}
**First Published:** {{publication_date}}

**Infringement Details:**
The video contains my copyrighted material without permission. {{infringement_details}}

**Good Faith Statement:**
I have a good faith belief that the use of the material is not authorized by the copyright owner, its agent, or the law.

**Accuracy Statement:**
I swear under penalty of perjury that the information in this notification is accurate and that I am the copyright owner or authorized to act on behalf of the copyright owner.

Signature: {{digital_signature}}
Date: {{current_date}}

Contact Information:
{{sender_name}}
{{email_address}}
{{phone_number}}
{{mailing_address}}''',
            'variables': [
                {'name': 'video_url', 'label': 'YouTube Video URL', 'type': 'url', 'required': True, 'placeholder': 'https://youtube.com/watch?v=...'},
                {'name': 'video_title', 'label': 'Video Title', 'type': 'text', 'required': True, 'placeholder': 'Title of the infringing video'},
                {'name': 'uploader_name', 'label': 'Uploader Name', 'type': 'text', 'required': False, 'placeholder': 'YouTube channel name'},
                {'name': 'original_work', 'label': 'Your Original Work', 'type': 'text', 'required': True, 'placeholder': 'Title of your copyrighted work'},
                {'name': 'publication_date', 'label': 'Publication Date', 'type': 'date', 'required': True, 'placeholder': 'When you first published the work'},
                {'name': 'infringement_details', 'label': 'Infringement Details', 'type': 'textarea', 'required': True, 'placeholder': 'Detailed description of the infringement'},
                {'name': 'digital_signature', 'label': 'Digital Signature', 'type': 'text', 'required': True, 'placeholder': 'Type your full name as signature'},
                {'name': 'current_date', 'label': 'Current Date', 'type': 'date', 'required': True, 'default_value': datetime.now().strftime('%Y-%m-%d')},
                {'name': 'sender_name', 'label': 'Your Name', 'type': 'text', 'required': True, 'placeholder': 'Your full legal name'},
                {'name': 'email_address', 'label': 'Email Address', 'type': 'email', 'required': True, 'placeholder': 'your@email.com'},
                {'name': 'phone_number', 'label': 'Phone Number', 'type': 'text', 'required': False, 'placeholder': '+1 (555) 123-4567'},
                {'name': 'mailing_address', 'label': 'Mailing Address', 'type': 'textarea', 'required': True, 'placeholder': 'Your complete mailing address'}
            ],
            'is_active': True,
            'is_system': True,
            'created_at': '2024-02-10T10:15:00Z',
            'updated_at': '2024-08-22T16:45:00Z',
            'usage_count': 156,
            'tags': ['youtube', 'video', 'platform-specific'],
            'language': 'en',
            'jurisdiction': 'US'
        },
        {
            'id': 'tmpl_3',
            'name': 'Social Media DMCA Notice',
            'description': 'Template for social media platforms like Instagram, Facebook, Twitter',
            'category': 'Social Media',
            'content': '''Dear {{platform_name}} Legal Team,

I am writing to report copyright infringement on your platform under the Digital Millennium Copyright Act (DMCA).

**Platform:** {{platform_name}}
**Infringing Content:** {{content_url}}
**Account:** {{infringing_account}}
**Post Date:** {{post_date}}

**My Copyrighted Work:**
- Title: {{work_title}}
- Description: {{work_description}}
- Original Publication: {{original_publication_date}}
- Copyright Registration: {{copyright_registration}}

**Infringement Description:**
{{infringement_description}}

I have a good faith belief that use of the copyrighted materials described above is not authorized by the copyright owner, its agent, or the law.

I swear, under penalty of perjury, that the information in the notification is accurate and that I am the copyright owner or am authorized to act on behalf of the copyright owner.

Please remove or disable access to the infringing material immediately.

{{sender_name}}
{{title_position}}
{{company_organization}}
{{contact_email}}
{{phone_number}}
{{date}}''',
            'variables': [
                {'name': 'platform_name', 'label': 'Platform Name', 'type': 'select', 'required': True, 'options': ['Instagram', 'Facebook', 'Twitter', 'LinkedIn', 'TikTok', 'Snapchat', 'Other']},
                {'name': 'content_url', 'label': 'Infringing Content URL', 'type': 'url', 'required': True, 'placeholder': 'Direct link to the infringing post'},
                {'name': 'infringing_account', 'label': 'Account Name', 'type': 'text', 'required': False, 'placeholder': '@username or account name'},
                {'name': 'post_date', 'label': 'Post Date', 'type': 'date', 'required': False, 'placeholder': 'When was the infringing content posted'},
                {'name': 'work_title', 'label': 'Your Work Title', 'type': 'text', 'required': True, 'placeholder': 'Title of your original work'},
                {'name': 'work_description', 'label': 'Work Description', 'type': 'textarea', 'required': True, 'placeholder': 'Brief description of your original work'},
                {'name': 'original_publication_date', 'label': 'Original Publication Date', 'type': 'date', 'required': True, 'placeholder': 'When you first published your work'},
                {'name': 'copyright_registration', 'label': 'Copyright Registration', 'type': 'text', 'required': False, 'placeholder': 'Registration number if applicable'},
                {'name': 'infringement_description', 'label': 'Infringement Description', 'type': 'textarea', 'required': True, 'placeholder': 'Explain how your work is being infringed'},
                {'name': 'sender_name', 'label': 'Your Name', 'type': 'text', 'required': True, 'placeholder': 'Your full legal name'},
                {'name': 'title_position', 'label': 'Title/Position', 'type': 'text', 'required': False, 'placeholder': 'Your job title or position'},
                {'name': 'company_organization', 'label': 'Company/Organization', 'type': 'text', 'required': False, 'placeholder': 'Your company or organization'},
                {'name': 'contact_email', 'label': 'Contact Email', 'type': 'email', 'required': True, 'placeholder': 'your@email.com'},
                {'name': 'phone_number', 'label': 'Phone Number', 'type': 'text', 'required': False, 'placeholder': 'Your phone number'},
                {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True, 'default_value': datetime.now().strftime('%Y-%m-%d')}
            ],
            'is_active': True,
            'is_system': True,
            'created_at': '2024-03-05T12:20:00Z',
            'updated_at': '2024-08-18T09:30:00Z',
            'usage_count': 89,
            'tags': ['social-media', 'instagram', 'facebook', 'twitter'],
            'language': 'en',
            'jurisdiction': 'US'
        },
        {
            'id': 'tmpl_4',
            'name': 'Search Engine Delisting Request',
            'description': 'Template for requesting removal from search engine results',
            'category': 'Search Engines',
            'content': '''Dear {{search_engine}} Legal Team,

I am requesting removal of search results that contain my copyrighted material without authorization.

**Search Query:** "{{search_query}}"
**Infringing Results:**
{{infringing_results}}

**My Copyrighted Work:**
{{copyrighted_work_details}}

**Evidence of Copyright:**
{{copyright_evidence}}

I request that you remove these results from your search index as they violate my copyright.

Thank you for your prompt attention to this matter.

{{sender_name}}
{{contact_details}}
{{date}}''',
            'variables': [
                {'name': 'search_engine', 'label': 'Search Engine', 'type': 'select', 'required': True, 'options': ['Google', 'Bing', 'Yahoo', 'DuckDuckGo', 'Other']},
                {'name': 'search_query', 'label': 'Search Query', 'type': 'text', 'required': True, 'placeholder': 'The search terms that show infringing results'},
                {'name': 'infringing_results', 'label': 'Infringing Results', 'type': 'textarea', 'required': True, 'placeholder': 'List the URLs and descriptions of infringing search results'},
                {'name': 'copyrighted_work_details', 'label': 'Copyrighted Work Details', 'type': 'textarea', 'required': True, 'placeholder': 'Details about your original copyrighted work'},
                {'name': 'copyright_evidence', 'label': 'Copyright Evidence', 'type': 'textarea', 'required': True, 'placeholder': 'Evidence proving your copyright ownership'},
                {'name': 'sender_name', 'label': 'Your Name', 'type': 'text', 'required': True, 'placeholder': 'Your full name'},
                {'name': 'contact_details', 'label': 'Contact Details', 'type': 'textarea', 'required': True, 'placeholder': 'Your email, phone, and address'},
                {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True, 'default_value': datetime.now().strftime('%Y-%m-%d')}
            ],
            'is_active': True,
            'is_system': False,
            'created_at': '2024-04-12T15:45:00Z',
            'updated_at': '2024-08-15T11:20:00Z',
            'usage_count': 23,
            'tags': ['search-engines', 'delisting', 'google'],
            'language': 'en',
            'jurisdiction': 'US'
        },
        {
            'id': 'tmpl_5',
            'name': 'E-commerce Platform DMCA',
            'description': 'Template for e-commerce platforms like Amazon, eBay, Etsy',
            'category': 'E-commerce',
            'content': '''To the Designated Agent for {{platform_name}},

I am submitting this notice under the Digital Millennium Copyright Act regarding unauthorized sale/display of my copyrighted work on your platform.

**Platform:** {{platform_name}}
**Infringing Listing:** {{listing_url}}
**Seller:** {{seller_name}}
**Listing Title:** {{listing_title}}

**My Original Work:**
{{original_work_description}}

**Copyright Information:**
- Registration: {{copyright_registration}}
- First Published: {{publication_date}}
- Ownership Proof: {{ownership_proof}}

**Infringement Details:**
{{infringement_details}}

I have a good faith belief that the use described above is not authorized by the copyright owner, its agent, or the law.

The information in this notification is accurate, and under penalty of perjury, I am authorized to act on behalf of the copyright owner.

Please remove the infringing listing immediately.

{{sender_signature}}
{{contact_information}}''',
            'variables': [
                {'name': 'platform_name', 'label': 'Platform Name', 'type': 'select', 'required': True, 'options': ['Amazon', 'eBay', 'Etsy', 'Shopify', 'Other']},
                {'name': 'listing_url', 'label': 'Infringing Listing URL', 'type': 'url', 'required': True, 'placeholder': 'Direct link to the infringing product listing'},
                {'name': 'seller_name', 'label': 'Seller Name', 'type': 'text', 'required': False, 'placeholder': 'Name or username of the seller'},
                {'name': 'listing_title', 'label': 'Listing Title', 'type': 'text', 'required': True, 'placeholder': 'Title of the infringing product listing'},
                {'name': 'original_work_description', 'label': 'Original Work Description', 'type': 'textarea', 'required': True, 'placeholder': 'Detailed description of your original copyrighted work'},
                {'name': 'copyright_registration', 'label': 'Copyright Registration', 'type': 'text', 'required': False, 'placeholder': 'Registration number if available'},
                {'name': 'publication_date', 'label': 'Publication Date', 'type': 'date', 'required': True, 'placeholder': 'When you first published the work'},
                {'name': 'ownership_proof', 'label': 'Ownership Proof', 'type': 'textarea', 'required': True, 'placeholder': 'Evidence of your copyright ownership'},
                {'name': 'infringement_details', 'label': 'Infringement Details', 'type': 'textarea', 'required': True, 'placeholder': 'How your work is being infringed'},
                {'name': 'sender_signature', 'label': 'Digital Signature', 'type': 'text', 'required': True, 'placeholder': 'Type your full name'},
                {'name': 'contact_information', 'label': 'Contact Information', 'type': 'textarea', 'required': True, 'placeholder': 'Email, phone, and mailing address'}
            ],
            'is_active': True,
            'is_system': True,
            'created_at': '2024-05-08T09:15:00Z',
            'updated_at': '2024-08-19T13:10:00Z',
            'usage_count': 67,
            'tags': ['ecommerce', 'amazon', 'ebay', 'etsy'],
            'language': 'en',
            'jurisdiction': 'US'
        }
    ]
    
    # Apply filters
    filtered_templates = templates
    
    if category and category != "":
        filtered_templates = [t for t in filtered_templates if t['category'].lower() == category.lower()]
    
    if search and search != "":
        search_lower = search.lower()
        filtered_templates = [
            t for t in filtered_templates 
            if search_lower in t['name'].lower() 
            or search_lower in t['description'].lower()
            or any(search_lower in tag.lower() for tag in t.get('tags', []))
        ]
    
    if is_active is not None:
        filtered_templates = [t for t in filtered_templates if t['is_active'] == is_active]
    
    if language and language != "":
        filtered_templates = [t for t in filtered_templates if t.get('language', 'en') == language]
    
    if jurisdiction and jurisdiction != "":
        filtered_templates = [t for t in filtered_templates if t.get('jurisdiction', 'US') == jurisdiction]
    
    # Sort templates
    reverse = sort_order == 'desc'
    if sort_by == 'name':
        filtered_templates.sort(key=lambda x: x['name'].lower(), reverse=reverse)
    elif sort_by == 'created_at':
        filtered_templates.sort(key=lambda x: x['created_at'], reverse=reverse)
    elif sort_by == 'updated_at':
        filtered_templates.sort(key=lambda x: x['updated_at'], reverse=reverse)
    elif sort_by == 'usage_count':
        filtered_templates.sort(key=lambda x: x['usage_count'], reverse=reverse)
    
    # Pagination
    total = len(filtered_templates)
    page_num = page if page else 1
    limit_num = limit if limit else 12
    start_idx = (page_num - 1) * limit_num
    end_idx = start_idx + limit_num
    paginated_templates = filtered_templates[start_idx:end_idx]
    
    return {
        'templates': paginated_templates,
        'total': total,
        'page': page_num,
        'limit': limit_num,
        'total_pages': (total + limit_num - 1) // limit_num,
        'has_next': end_idx < total,
        'has_prev': page_num > 1
    }

@app.get('/api/v1/templates/categories')
async def get_template_categories():
    return [
        {'id': 'general-dmca', 'name': 'General DMCA', 'description': 'Standard DMCA takedown templates', 'template_count': 1, 'icon': 'pi-file', 'color': '#3b82f6'},
        {'id': 'video-platforms', 'name': 'Video Platforms', 'description': 'Templates for YouTube, Vimeo, etc.', 'template_count': 1, 'icon': 'pi-video', 'color': '#ef4444'},
        {'id': 'social-media', 'name': 'Social Media', 'description': 'Templates for social media platforms', 'template_count': 1, 'icon': 'pi-users', 'color': '#8b5cf6'},
        {'id': 'search-engines', 'name': 'Search Engines', 'description': 'Templates for search engine delisting', 'template_count': 1, 'icon': 'pi-search', 'color': '#10b981'},
        {'id': 'e-commerce', 'name': 'E-commerce', 'description': 'Templates for e-commerce platforms', 'template_count': 1, 'icon': 'pi-shopping-cart', 'color': '#f59e0b'}
    ]

@app.get('/api/v1/templates/mock')
async def get_mock_templates():
    # Returns the same mock data as the main templates endpoint
    return await get_templates()

@app.get('/api/v1/templates/{template_id}')
async def get_template(template_id: str):
    # Get all templates and find the one with matching ID
    all_templates = (await _get_templates_internal(limit=100))['templates']
    template = next((t for t in all_templates if t['id'] == template_id), None)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@app.post('/api/v1/templates/preview')
async def preview_template(request: Dict[str, Any]):
    content = request.get('content', '')
    variables = request.get('variables', {})
    template_id = request.get('template_id')
    
    if template_id:
        # Get template content if template_id provided
        template = await get_template(template_id)
        content = template['content']
    
    # Simple variable substitution
    rendered_content = content
    missing_variables = []
    validation_errors = {}
    
    # Find all variables in the content
    import re
    variable_pattern = r'\{\{(\w+)\}\}'
    found_variables = re.findall(variable_pattern, content)
    
    for var_name in found_variables:
        if var_name in variables and variables[var_name]:
            # Replace the variable
            rendered_content = rendered_content.replace(f'{{{{{var_name}}}}}', str(variables[var_name]))
        else:
            missing_variables.append(var_name)
            # Leave placeholder for missing variables
            rendered_content = rendered_content.replace(f'{{{{{var_name}}}}}', f'[{var_name.upper()}_MISSING]')
    
    # Convert newlines to HTML breaks for display
    rendered_content = rendered_content.replace('\n', '<br>')
    
    return {
        'rendered_content': rendered_content,
        'missing_variables': missing_variables,
        'validation_errors': validation_errors
    }

@app.post('/api/v1/templates')
async def create_template(template_data: Dict[str, Any]):
    # Create a new template
    template_id = f"tmpl_{random.randint(1000, 9999)}"
    
    new_template = {
        'id': template_id,
        'name': template_data.get('name', ''),
        'description': template_data.get('description', ''),
        'category': template_data.get('category', ''),
        'content': template_data.get('content', ''),
        'variables': template_data.get('variables', []),
        'is_active': template_data.get('is_active', True),
        'is_system': False,
        'created_at': datetime.now().isoformat() + 'Z',
        'updated_at': datetime.now().isoformat() + 'Z',
        'usage_count': 0,
        'tags': template_data.get('tags', []),
        'language': template_data.get('language', 'en'),
        'jurisdiction': template_data.get('jurisdiction', 'US')
    }
    
    return new_template

@app.put('/api/v1/templates/{template_id}')
async def update_template(template_id: str, template_data: Dict[str, Any]):
    # Update existing template
    updated_template = {
        'id': template_id,
        'name': template_data.get('name', ''),
        'description': template_data.get('description', ''),
        'category': template_data.get('category', ''),
        'content': template_data.get('content', ''),
        'variables': template_data.get('variables', []),
        'is_active': template_data.get('is_active', True),
        'is_system': False,
        'created_at': '2024-01-15T08:00:00Z',  # Mock creation date
        'updated_at': datetime.now().isoformat() + 'Z',
        'usage_count': random.randint(0, 50),
        'tags': template_data.get('tags', []),
        'language': template_data.get('language', 'en'),
        'jurisdiction': template_data.get('jurisdiction', 'US')
    }
    
    return updated_template

@app.delete('/api/v1/templates/{template_id}')
async def delete_template(template_id: str):
    return {'message': 'Template deleted successfully', 'id': template_id}

@app.post('/api/v1/templates/{template_id}/duplicate')
async def duplicate_template(template_id: str, request: Dict[str, Any] = None):
    # Get the original template
    original = await get_template(template_id)
    
    # Create duplicate
    new_id = f"tmpl_{random.randint(1000, 9999)}"
    new_name = request.get('name') if request else f"{original['name']} (Copy)"
    
    duplicate = {
        **original,
        'id': new_id,
        'name': new_name,
        'is_system': False,
        'created_at': datetime.now().isoformat() + 'Z',
        'updated_at': datetime.now().isoformat() + 'Z',
        'usage_count': 0
    }
    
    return duplicate

@app.post('/api/v1/templates/bulk/activate')
async def bulk_activate_templates(request: Dict[str, Any]):
    template_ids = request.get('template_ids', [])
    return {'message': f'Successfully activated {len(template_ids)} templates', 'template_ids': template_ids}

@app.post('/api/v1/templates/bulk/deactivate')
async def bulk_deactivate_templates(request: Dict[str, Any]):
    template_ids = request.get('template_ids', [])
    return {'message': f'Successfully deactivated {len(template_ids)} templates', 'template_ids': template_ids}

@app.delete('/api/v1/templates/bulk')
async def bulk_delete_templates(request: Dict[str, Any]):
    template_ids = request.get('template_ids', [])
    return {'message': f'Successfully deleted {len(template_ids)} templates', 'template_ids': template_ids}

# Takedown requests endpoint (to fix 404 error)
@app.get('/api/v1/takedowns')
async def get_takedowns(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    include_stats: bool = Query(False)
):
    # Mock takedown requests data
    mock_takedowns = [
        {
            'id': 'td_001',
            'title': 'Copyright Infringement - Photography Portfolio',
            'description': 'Unauthorized use of copyrighted photography',
            'status': 'completed',
            'platform': 'Instagram',
            'infringing_url': 'https://instagram.com/fake_account/post123',
            'created_at': (datetime.now() - timedelta(days=2)).isoformat() + 'Z',
            'updated_at': (datetime.now() - timedelta(hours=6)).isoformat() + 'Z',
            'success': True,
            'response_time_hours': 18
        },
        {
            'id': 'td_002', 
            'title': 'DMCA Takedown - YouTube Video',
            'description': 'Copyrighted music used without permission',
            'status': 'in_progress',
            'platform': 'YouTube',
            'infringing_url': 'https://youtube.com/watch?v=fake123',
            'created_at': (datetime.now() - timedelta(days=1)).isoformat() + 'Z',
            'updated_at': (datetime.now() - timedelta(hours=2)).isoformat() + 'Z',
            'success': None,
            'response_time_hours': None
        },
        {
            'id': 'td_003',
            'title': 'Trademark Violation - Brand Logo',
            'description': 'Unauthorized use of company logo',
            'status': 'pending',
            'platform': 'Facebook',
            'infringing_url': 'https://facebook.com/fake_business',
            'created_at': datetime.now().isoformat() + 'Z',
            'updated_at': datetime.now().isoformat() + 'Z',
            'success': None,
            'response_time_hours': None
        }
    ]
    
    # Calculate pagination
    total_items = len(mock_takedowns)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_items = mock_takedowns[start_idx:end_idx]
    
    response = {
        'items': paginated_items,
        'total': total_items,
        'page': page,
        'limit': limit,
        'pages': (total_items + limit - 1) // limit
    }
    
    if include_stats:
        response['stats'] = {
            'total_requests': total_items,
            'completed': 1,
            'in_progress': 1,
            'pending': 1,
            'success_rate': 0.5,
            'average_response_time_hours': 18
        }
    
    return response

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8082)