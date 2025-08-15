# Content Protection Platform API Documentation

## Overview

This directory contains comprehensive API documentation for the Content Protection Platform - an AI-powered content protection and DMCA takedown automation service.

## Documentation Structure

### 📖 Core Documentation

- **[Developer Guide](developer_guide.md)** - Complete getting started guide with examples and best practices
- **[API Reference](api_reference.md)** - Detailed endpoint documentation with request/response examples  
- **[Webhooks & Real-Time](webhooks_and_realtime.md)** - WebSocket and webhook integration guide

### 🛠 SDK Examples

- **[Python SDK](sdk_examples/python_sdk.py)** - Comprehensive Python client with async support
- **[JavaScript SDK](sdk_examples/javascript_sdk.js)** - Node.js and browser-compatible client

### 🧪 Testing & Integration

- **[Postman Collection](postman/ContentProtectionPlatform.postman_collection.json)** - Complete API testing collection
- **[OpenAPI Enhancements](openapi_enhancements.py)** - Advanced OpenAPI schema configuration

## Quick Start

### 1. Authentication

```bash
# Get JWT tokens
curl -X POST "https://api.contentprotection.ai/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

### 2. Create Protected Profile

```bash
# Create a profile for content protection
curl -X POST "https://api.contentprotection.ai/api/v1/profiles" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Creator Profile","platform":"onlyfans","username":"creator"}'
```

### 3. Trigger Content Scan

```bash
# Scan for unauthorized content
curl -X POST "https://api.contentprotection.ai/api/v1/scanning/scan/manual?profile_id=42" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Key Features

### 🔐 Authentication
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Two-factor authentication (2FA) support
- API key authentication for server-to-server

### 🔍 AI-Powered Scanning
- Facial recognition matching
- Content similarity analysis
- Visual hash comparison
- Cross-platform monitoring

### ⚖️ DMCA Automation
- Automated takedown request generation
- Template-based legal notices
- Status tracking and reporting
- Platform-specific integrations

### 📱 Social Media Monitoring
- Impersonation detection
- Username monitoring
- Profile verification
- Multi-platform support

### 📊 Analytics & Reporting
- Real-time dashboard metrics
- Scan performance analytics
- Takedown success rates
- Custom reporting

### 🔔 Real-Time Updates
- WebSocket connections for live updates
- Webhook notifications for events
- Progress tracking for long-running operations
- Event-driven architecture

## API Endpoints Overview

### Authentication (`/api/v1/auth`)
- `POST /login` - User authentication
- `POST /register` - User registration
- `POST /refresh` - Token refresh
- `POST /2fa/setup` - Enable 2FA
- `POST /change-password` - Password change

### Profiles (`/api/v1/profiles`)
- `POST /` - Create protected profile
- `GET /` - List profiles
- `GET /{id}` - Get profile details
- `PUT /{id}` - Update profile

### Scanning (`/api/v1/scanning`)
- `POST /scan/manual` - Trigger manual scan
- `GET /scan/status/{job_id}` - Check scan status
- `POST /scan/url` - Scan specific URL
- `POST /profile/signatures` - Generate AI signatures

### Infringements (`/api/v1/infringements`)
- `GET /` - List detected infringements
- `GET /{id}` - Get infringement details
- `PUT /{id}` - Update infringement status
- `POST /bulk` - Bulk process infringements

### Takedowns (`/api/v1/takedowns`)
- `POST /` - Submit DMCA takedown
- `GET /{id}` - Get takedown status
- `GET /` - List takedowns
- `POST /{id}/cancel` - Cancel takedown

### Social Media (`/api/v1/social-media`)
- `POST /scan` - Scan social platforms
- `GET /incidents` - Get impersonation incidents
- `POST /report` - Report impersonation

### Webhooks (`/api/v1/webhooks`)
- `POST /` - Create webhook
- `GET /` - List webhooks
- `DELETE /{id}` - Delete webhook

## Rate Limits

| Category | Free | Premium | Enterprise |
|----------|------|---------|------------|
| API Calls | 1,000/hour | 5,000/hour | Unlimited |
| Manual Scans | 10/day | 50/day | Unlimited |
| URL Scans | 100/day | 500/day | Unlimited |
| Takedowns | 10/month | 100/month | Unlimited |

## Error Handling

All API responses follow standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Server Error

Error responses include detailed information:

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "error_id": "err_12345abc",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## SDK Integration

### Python

```python
from contentprotection import ContentProtectionClient

client = ContentProtectionClient()
client.authenticate('user@example.com', 'password')

# Create profile and trigger scan
profile = client.profiles.create(name='Creator', platform='onlyfans')
scan = client.scanning.manual_scan(profile_id=profile.id)
results = scan.wait_for_completion()
```

### JavaScript

```javascript
import { ContentProtectionClient } from '@contentprotection/api-client';

const client = new ContentProtectionClient();
await client.authenticate('user@example.com', 'password');

// Create profile and trigger scan
const profile = await client.profiles.create({
  name: 'Creator',
  platform: 'onlyfans'
});

const scan = await client.scanning.manualScan({
  profileId: profile.id
});
```

## Webhook Events

The platform sends webhooks for key events:

- `scan.completed` - Scan finished
- `infringement.detected` - New violation found
- `takedown.status_changed` - DMCA status update
- `profile.updated` - Profile configuration changed

Example webhook payload:

```json
{
  "event": "scan.completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "results": {
      "infringements_found": 5,
      "new_infringements": 3
    }
  }
}
```

## Testing with Postman

1. Import the [Postman collection](postman/ContentProtectionPlatform.postman_collection.json)
2. Set environment variables:
   - `base_url`: https://api.contentprotection.ai
   - `email`: Your account email
   - `password`: Your account password
3. Run the "Login" request to authenticate
4. Test other endpoints with automatic token management

## Security

### Authentication Security
- JWT tokens with short expiration (30 minutes)
- Secure refresh token rotation
- Password strength validation
- Account lockout protection

### API Security
- Rate limiting on all endpoints
- Input validation and sanitization
- CORS protection
- Security headers (HSTS, CSP, etc.)

### Webhook Security
- HMAC signature verification
- HTTPS-only delivery
- Automatic retry with exponential backoff
- Delivery attempt tracking

## Performance

### Optimization Features
- Response caching for static data
- Database query optimization
- Connection pooling
- Async processing for long operations

### Monitoring
- Real-time metrics collection
- Performance analytics
- Error tracking and alerting
- Uptime monitoring

## Support

### Documentation
- **API Reference**: https://api.contentprotection.ai/docs
- **Interactive Docs**: https://api.contentprotection.ai/redoc
- **Developer Portal**: https://docs.contentprotection.ai

### Support Channels
- **Email**: api-support@contentprotection.ai
- **Discord**: https://discord.gg/contentprotection
- **GitHub**: https://github.com/contentprotection/api-examples
- **Status Page**: https://status.contentprotection.ai

### Response Times
- **Priority Support**: 4 hours (Enterprise)
- **Standard Support**: 24 hours (Premium)
- **Community Support**: 48-72 hours (Free)

## Changelog

### v1.0.0 (Current)
- Initial API release
- Complete authentication system
- AI-powered content scanning
- DMCA takedown automation
- Social media monitoring
- Real-time webhooks and WebSockets
- Comprehensive SDKs and documentation

## Legal

### Terms of Service
- API usage subject to platform Terms of Service
- Commercial use permitted with appropriate subscription
- Rate limits enforced per plan tier

### Data Protection
- GDPR compliant data handling
- SOC 2 Type II certified infrastructure
- End-to-end encryption for sensitive data
- Regular security audits and penetration testing

### Content Policy
- AI detection for copyright infringement only
- User responsible for takedown request accuracy
- Platform acts as intermediary for DMCA processes
- No liability for false positive detections

---

For the most up-to-date information, visit our [developer portal](https://docs.contentprotection.ai) or contact our support team.