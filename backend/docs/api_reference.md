# Content Protection Platform API Reference

## Overview

The Content Protection Platform API provides AI-powered content protection, DMCA takedown automation, and social media monitoring capabilities. This reference covers all available endpoints, authentication methods, and integration patterns.

**Base URL**: `https://api.contentprotection.ai`
**API Version**: v1
**Format**: JSON

## Authentication

### JWT Bearer Authentication

All API requests require authentication using JWT (JSON Web Tokens). Include the access token in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Obtaining Tokens

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "remember_me": true
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Token Refresh

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Rate Limiting

All endpoints are rate limited to ensure fair usage:

| Endpoint Category | Rate Limit | Scope |
|------------------|------------|-------|
| Authentication | 5 per 15 min | Per IP |
| Scanning (Free) | 10 per day | Per user |
| Scanning (Premium) | 50 per day | Per user |
| Scanning (Enterprise) | Unlimited | Per user |
| API Calls | 1000 per hour | Per user |

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 3600
```

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR", 
  "error_id": "err_12345abc",
  "timestamp": "2024-01-15T10:30:00Z",
  "path": "/api/v1/auth/login"
}
```

### HTTP Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input, validation error |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Semantic validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

## Endpoints

### Authentication

#### POST /api/v1/auth/login
Authenticate user and obtain JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "remember_me": false
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401` - Invalid credentials
- `429` - Too many login attempts

---

#### POST /api/v1/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "SecureP@ssw0rd123",
  "full_name": "Content Creator",
  "company": "Creator Studios LLC",
  "phone": "+1-555-123-4567",
  "accept_terms": true
}
```

**Response (201):**
```json
{
  "id": 123,
  "email": "newuser@example.com",
  "full_name": "Content Creator",
  "company": "Creator Studios LLC",
  "phone": "+1-555-123-4567",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400` - Email already registered, weak password
- `422` - Validation error

---

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer", 
  "expires_in": 1800
}
```

---

#### GET /api/v1/auth/me
Get current authenticated user information.

**Response (200):**
```json
{
  "id": 123,
  "email": "user@example.com",
  "full_name": "Content Creator",
  "company": "Creator Studios LLC",
  "subscription": {
    "plan": "premium",
    "status": "active",
    "expires_at": "2024-12-31T23:59:59Z"
  },
  "permissions": ["profile:read", "profile:write", "scan:trigger"]
}
```

### Protected Profiles

#### POST /api/v1/profiles
Create a new protected profile.

**Request Body:**
```json
{
  "name": "Content Creator Profile",
  "platform": "onlyfans",
  "username": "creator_username", 
  "keywords": ["creator name", "username", "exclusive content"],
  "monitoring_enabled": true
}
```

**Response (201):**
```json
{
  "id": 42,
  "name": "Content Creator Profile",
  "platform": "onlyfans",
  "username": "creator_username",
  "keywords": ["creator name", "username", "exclusive content"],
  "monitoring_enabled": true,
  "ai_signatures": {
    "face_encodings": 0,
    "content_hashes": 0,
    "status": "pending_upload"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

#### GET /api/v1/profiles
List all protected profiles.

**Query Parameters:**
- `limit` (integer, default: 50): Number of results to return
- `offset` (integer, default: 0): Number of results to skip
- `platform` (string, optional): Filter by platform
- `monitoring_enabled` (boolean, optional): Filter by monitoring status

**Response (200):**
```json
{
  "total": 5,
  "items": [
    {
      "id": 42,
      "name": "Content Creator Profile",
      "platform": "onlyfans",
      "username": "creator_username",
      "monitoring_enabled": true,
      "ai_signatures": {
        "face_encodings": 3,
        "content_hashes": 15,
        "status": "ready"
      },
      "last_scan": "2024-01-15T08:00:00Z",
      "infringements_count": 12
    }
  ],
  "limit": 50,
  "offset": 0
}
```

---

#### GET /api/v1/profiles/{profile_id}
Get detailed profile information.

**Path Parameters:**
- `profile_id` (integer): Profile ID

**Response (200):**
```json
{
  "id": 42,
  "name": "Content Creator Profile",
  "platform": "onlyfans",
  "username": "creator_username",
  "keywords": ["creator name", "username", "exclusive content"],
  "monitoring_enabled": true,
  "scan_schedule": {
    "frequency": "daily",
    "time": "02:00",
    "platforms": ["google", "bing", "social_media"]
  },
  "ai_signatures": {
    "face_encodings": 3,
    "content_hashes": 15,
    "image_features": 8,
    "status": "ready",
    "last_updated": "2024-01-10T12:00:00Z"
  },
  "statistics": {
    "total_scans": 45,
    "infringements_found": 23,
    "takedowns_sent": 18,
    "takedowns_successful": 15
  },
  "created_at": "2024-01-01T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Content Scanning

#### POST /api/v1/scanning/profile/signatures
Generate AI signatures from reference content.

**Request Body:**
```json
{
  "profile_id": 42,
  "image_urls": [
    "https://example.com/reference1.jpg",
    "https://example.com/reference2.jpg",
    "https://example.com/reference3.jpg"
  ]
}
```

**Response (200):**
```json
{
  "profile_id": 42,
  "signatures_generated": {
    "face_encodings": 3,
    "image_features": 8,
    "content_hashes": 12
  },
  "processing_time": 15.2,
  "status": "completed"
}
```

---

#### POST /api/v1/scanning/scan/manual
Trigger a manual scan for unauthorized content.

**Query Parameters:**
- `profile_id` (integer): Profile to scan for

**Response (200):**
```json
{
  "status": "success",
  "message": "Scan initiated",
  "job_id": "scan_12345abc",
  "profile_id": 42,
  "estimated_duration": "5-15 minutes",
  "platforms": ["google", "bing", "onlyfans", "pornhub"],
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400` - Profile not found, no AI signatures
- `429` - Daily scan limit reached

---

#### GET /api/v1/scanning/scan/status/{job_id}
Get scan job status and results.

**Path Parameters:**
- `job_id` (string): Scan job ID

**Response (200):**
```json
{
  "job_id": "scan_12345abc",
  "status": "completed",
  "progress": {
    "completed": 150,
    "total": 150,
    "percentage": 100
  },
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "results": {
    "infringements_found": 5,
    "new_infringements": 3,
    "scanned_urls": 150,
    "platforms_scanned": ["google", "bing", "social_media"],
    "processing_time": 14.5
  }
}
```

**Status Values:**
- `pending`: Job queued for processing
- `running`: Scan in progress
- `completed`: Scan finished successfully
- `failed`: Scan failed due to error
- `cancelled`: Scan was cancelled

---

#### POST /api/v1/scanning/scan/url
Scan specific URL for content matches.

**Query Parameters:**
- `url` (string): URL to scan
- `profile_id` (integer): Profile to match against

**Response (200):**
```json
{
  "url": "https://suspicious-site.com/content",
  "scanned": true,
  "matches_found": 2,
  "matches": [
    {
      "url": "https://suspicious-site.com/image1.jpg",
      "type": "image",
      "confidence": 0.95,
      "match_type": "facial_recognition"
    },
    {
      "url": "https://suspicious-site.com/image2.jpg", 
      "type": "image",
      "confidence": 0.87,
      "match_type": "content_similarity"
    }
  ],
  "scan_duration": 3.2
}
```

### Infringements

#### GET /api/v1/infringements
List detected infringements with filtering.

**Query Parameters:**
- `profile_id` (integer, optional): Filter by profile
- `status` (string, optional): Filter by status (`detected`, `confirmed`, `false_positive`, `ignored`)
- `min_confidence` (float, optional): Minimum confidence score (0.0-1.0)
- `platform` (string, optional): Filter by platform
- `limit` (integer, default: 50): Number of results
- `offset` (integer, default: 0): Results offset

**Response (200):**
```json
{
  "total": 23,
  "items": [
    {
      "id": 12345,
      "url": "https://unauthorized-site.com/stolen-content",
      "platform": "unauthorized-site",
      "confidence_score": 0.95,
      "match_type": "facial_recognition",
      "status": "detected",
      "detected_at": "2024-01-15T10:30:00Z",
      "profile": {
        "id": 42,
        "name": "Content Creator Profile"
      },
      "evidence": {
        "screenshot_url": "https://storage.contentprotection.ai/evidence/12345.jpg",
        "thumbnail_url": "https://storage.contentprotection.ai/thumbs/12345.jpg"
      },
      "takedown": null
    }
  ],
  "limit": 50,
  "offset": 0
}
```

---

#### PUT /api/v1/infringements/{infringement_id}
Update infringement status.

**Path Parameters:**
- `infringement_id` (integer): Infringement ID

**Request Body:**
```json
{
  "status": "confirmed",
  "notes": "Verified unauthorized use of copyrighted content"
}
```

**Response (200):**
```json
{
  "id": 12345,
  "status": "confirmed",
  "notes": "Verified unauthorized use of copyrighted content",
  "updated_at": "2024-01-15T11:00:00Z",
  "updated_by": {
    "id": 123,
    "name": "Content Creator"
  }
}
```

### DMCA Takedowns

#### POST /api/v1/takedowns
Submit a DMCA takedown request.

**Request Body:**
```json
{
  "infringement_id": 12345,
  "urgency": "high",
  "additional_info": "High-confidence match found through AI analysis",
  "evidence_urls": [
    "https://storage.contentprotection.ai/evidence/12345.jpg",
    "https://original-platform.com/proof-of-ownership"
  ],
  "template_id": 1
}
```

**Response (201):**
```json
{
  "id": "td_12345",
  "status": "pending",
  "platform": "google",
  "urgency": "high",
  "infringement": {
    "id": 12345,
    "url": "https://unauthorized-site.com/stolen-content",
    "confidence_score": 0.95
  },
  "evidence_package": {
    "dmca_notice_url": "https://storage.contentprotection.ai/notices/td_12345.pdf",
    "evidence_urls": [
      "https://storage.contentprotection.ai/evidence/12345.jpg"
    ]
  },
  "submitted_at": "2024-01-15T11:00:00Z",
  "estimated_response_time": "7 days"
}
```

---

#### GET /api/v1/takedowns/{takedown_id}
Get takedown request status and details.

**Path Parameters:**
- `takedown_id` (string): Takedown ID

**Response (200):**
```json
{
  "id": "td_12345",
  "status": "completed",
  "platform": "google",
  "urgency": "high",
  "infringement": {
    "id": 12345,
    "url": "https://unauthorized-site.com/stolen-content",
    "confidence_score": 0.95
  },
  "timeline": [
    {
      "status": "pending",
      "timestamp": "2024-01-15T11:00:00Z",
      "note": "Takedown request submitted"
    },
    {
      "status": "acknowledged",
      "timestamp": "2024-01-16T09:15:00Z", 
      "note": "Request acknowledged by platform"
    },
    {
      "status": "completed",
      "timestamp": "2024-01-18T14:30:00Z",
      "note": "Content successfully removed"
    }
  ],
  "evidence_package": {
    "dmca_notice_url": "https://storage.contentprotection.ai/notices/td_12345.pdf",
    "evidence_urls": [
      "https://storage.contentprotection.ai/evidence/12345.jpg"
    ]
  },
  "platform_response": {
    "reference_number": "DMC-2024-12345",
    "response_url": "https://google.com/dmca/response/12345"
  },
  "submitted_at": "2024-01-15T11:00:00Z",
  "completed_at": "2024-01-18T14:30:00Z"
}
```

**Status Values:**
- `pending`: Submitted to platform, awaiting response
- `acknowledged`: Platform confirmed receipt
- `in_progress`: Platform is reviewing
- `completed`: Content successfully removed
- `rejected`: Takedown request was denied
- `cancelled`: Request was cancelled

### Webhooks

#### POST /api/v1/webhooks
Create a webhook endpoint.

**Request Body:**
```json
{
  "url": "https://your-app.com/webhooks/contentprotection",
  "events": [
    "scan.completed",
    "infringement.detected",
    "takedown.status_changed"
  ],
  "secret": "your-webhook-secret-key"
}
```

**Response (201):**
```json
{
  "id": "wh_abc123",
  "url": "https://your-app.com/webhooks/contentprotection",
  "events": [
    "scan.completed",
    "infringement.detected", 
    "takedown.status_changed"
  ],
  "secret": "wh_sec_***",
  "status": "active",
  "created_at": "2024-01-15T11:00:00Z"
}
```

#### Webhook Events

**Scan Completed**
```json
{
  "event": "scan.completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "results": {
      "infringements_found": 5,
      "new_infringements": 3,
      "scanned_urls": 150
    }
  }
}
```

**Infringement Detected**
```json
{
  "event": "infringement.detected",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "infringement_id": 12345,
    "profile_id": 42,
    "url": "https://unauthorized-site.com/content",
    "confidence_score": 0.95,
    "match_type": "facial_recognition"
  }
}
```

**Takedown Status Changed**
```json
{
  "event": "takedown.status_changed",
  "timestamp": "2024-01-18T14:30:00Z",
  "data": {
    "takedown_id": "td_12345",
    "old_status": "in_progress",
    "new_status": "completed",
    "platform": "google",
    "infringement_id": 12345
  }
}
```

## SDK Integration

### Python

```python
from contentprotection import ContentProtectionClient

client = ContentProtectionClient()
client.authenticate('user@example.com', 'password')

# Create profile
profile = client.profiles.create(
    name='Creator Profile',
    platform='onlyfans',
    username='creator'
)

# Trigger scan
scan = client.scanning.manual_scan(profile_id=profile.id)
results = scan.wait_for_completion()
```

### JavaScript

```javascript
import { ContentProtectionClient } from '@contentprotection/api-client';

const client = new ContentProtectionClient();
await client.authenticate('user@example.com', 'password');

// Create profile
const profile = await client.profiles.create({
  name: 'Creator Profile',
  platform: 'onlyfans',
  username: 'creator'
});

// Trigger scan
const scan = await client.scanning.manualScan({
  profileId: profile.id
});
```

### cURL Examples

**Authentication:**
```bash
curl -X POST "https://api.contentprotection.ai/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

**Create Profile:**
```bash
curl -X POST "https://api.contentprotection.ai/api/v1/profiles" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Creator Profile","platform":"onlyfans","username":"creator"}'
```

**Trigger Scan:**
```bash
curl -X POST "https://api.contentprotection.ai/api/v1/scanning/scan/manual?profile_id=42" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Best Practices

### Security
- Store API credentials securely
- Use HTTPS for all requests
- Verify webhook signatures
- Implement proper error handling
- Log security events

### Performance
- Implement token refresh logic
- Use appropriate request timeouts
- Handle rate limiting gracefully
- Cache frequently accessed data
- Monitor API usage

### Error Handling
- Always check HTTP status codes
- Parse error responses for details
- Implement retry logic for transient failures
- Log errors with context
- Provide user-friendly error messages

### Monitoring
- Track API response times
- Monitor rate limit usage
- Set up alerts for failures
- Log important events
- Monitor webhook delivery

## Support

- **API Documentation**: https://api.contentprotection.ai/docs
- **Developer Portal**: https://docs.contentprotection.ai
- **Support Email**: api-support@contentprotection.ai
- **Status Page**: https://status.contentprotection.ai
- **GitHub**: https://github.com/contentprotection/api-examples