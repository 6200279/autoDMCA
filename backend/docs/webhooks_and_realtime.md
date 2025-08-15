# Webhooks and Real-Time Integration Guide

## Overview

The Content Protection Platform provides webhooks and WebSocket connections for real-time event notifications. This allows your application to receive immediate updates about scan results, infringement detections, and takedown status changes.

## Table of Contents

1. [Webhooks](#webhooks)
2. [WebSocket Integration](#websocket-integration)
3. [Event Types](#event-types)
4. [Security](#security)
5. [Implementation Examples](#implementation-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Webhooks

Webhooks allow the Content Protection Platform to send HTTP POST requests to your application when specific events occur. This eliminates the need for constant polling and provides real-time updates.

### Setting Up Webhooks

#### 1. Create a Webhook Endpoint

```http
POST /api/v1/webhooks
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/contentprotection",
  "events": [
    "scan.completed",
    "infringement.detected",
    "takedown.status_changed",
    "profile.updated"
  ],
  "secret": "your-webhook-secret-key"
}
```

**Response:**
```json
{
  "id": "wh_abc123def456",
  "url": "https://your-app.com/webhooks/contentprotection",
  "events": [
    "scan.completed",
    "infringement.detected",
    "takedown.status_changed",
    "profile.updated"
  ],
  "secret": "wh_sec_***",
  "status": "active",
  "created_at": "2024-01-15T11:00:00Z",
  "last_delivery": null,
  "delivery_stats": {
    "total_deliveries": 0,
    "successful_deliveries": 0,
    "failed_deliveries": 0,
    "last_success": null,
    "last_failure": null
  }
}
```

#### 2. Webhook Requirements

Your webhook endpoint must:
- Accept HTTP POST requests
- Respond with 2xx status code (200-299) for successful processing
- Respond within 10 seconds
- Handle duplicate events (implement idempotency)
- Verify webhook signatures for security

### Webhook Payload Structure

All webhook payloads follow this structure:

```json
{
  "id": "evt_12345abc",
  "event": "scan.completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "api_version": "v1",
  "data": {
    // Event-specific data
  },
  "delivery_attempt": 1,
  "webhook_id": "wh_abc123def456"
}
```

### Event Types

#### Scan Events

**scan.started**
```json
{
  "id": "evt_scan_001",
  "event": "scan.started",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "profile_name": "Content Creator Profile",
    "scan_type": "manual",
    "platforms": ["google", "bing", "social_media"],
    "estimated_duration": "5-15 minutes"
  }
}
```

**scan.progress**
```json
{
  "id": "evt_scan_002",
  "event": "scan.progress",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "progress": {
      "completed": 75,
      "total": 150,
      "percentage": 50,
      "current_platform": "google"
    },
    "intermediate_results": {
      "potential_matches": 3,
      "platforms_completed": ["bing"]
    }
  }
}
```

**scan.completed**
```json
{
  "id": "evt_scan_003",
  "event": "scan.completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "profile_name": "Content Creator Profile",
    "status": "completed",
    "results": {
      "infringements_found": 5,
      "new_infringements": 3,
      "updated_infringements": 2,
      "scanned_urls": 150,
      "platforms_scanned": ["google", "bing", "social_media"],
      "processing_time": 14.5,
      "high_confidence_matches": 2,
      "medium_confidence_matches": 3
    },
    "scan_summary": {
      "total_duration": "14m 30s",
      "start_time": "2024-01-15T10:31:00Z",
      "end_time": "2024-01-15T10:45:00Z"
    }
  }
}
```

**scan.failed**
```json
{
  "id": "evt_scan_004",
  "event": "scan.failed",
  "timestamp": "2024-01-15T10:40:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "profile_id": 42,
    "error": {
      "code": "PLATFORM_UNAVAILABLE",
      "message": "Unable to connect to Google Search API",
      "details": "Service temporarily unavailable"
    },
    "partial_results": {
      "platforms_completed": ["bing"],
      "infringements_found": 2
    },
    "retry_scheduled": true,
    "retry_at": "2024-01-15T11:40:00Z"
  }
}
```

#### Infringement Events

**infringement.detected**
```json
{
  "id": "evt_inf_001",
  "event": "infringement.detected",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "infringement_id": 12345,
    "profile_id": 42,
    "profile_name": "Content Creator Profile",
    "url": "https://unauthorized-site.com/stolen-content",
    "platform": "unauthorized-site",
    "confidence_score": 0.95,
    "match_type": "facial_recognition",
    "evidence": {
      "screenshot_url": "https://storage.contentprotection.ai/evidence/12345.jpg",
      "thumbnail_url": "https://storage.contentprotection.ai/thumbs/12345.jpg",
      "metadata": {
        "page_title": "Stolen Content Page",
        "detected_elements": ["face", "watermark"]
      }
    },
    "scan_context": {
      "job_id": "scan_12345abc",
      "platform_scanned": "google",
      "search_query": "creator name content"
    }
  }
}
```

**infringement.updated**
```json
{
  "id": "evt_inf_002",
  "event": "infringement.updated",
  "timestamp": "2024-01-15T11:00:00Z",
  "data": {
    "infringement_id": 12345,
    "profile_id": 42,
    "old_status": "detected",
    "new_status": "confirmed",
    "updated_by": {
      "id": 123,
      "name": "Content Creator",
      "type": "user"
    },
    "notes": "Verified unauthorized use of copyrighted content",
    "confidence_score": 0.95
  }
}
```

#### Takedown Events

**takedown.submitted**
```json
{
  "id": "evt_td_001",
  "event": "takedown.submitted",
  "timestamp": "2024-01-15T11:00:00Z",
  "data": {
    "takedown_id": "td_12345",
    "infringement_id": 12345,
    "profile_id": 42,
    "platform": "google",
    "urgency": "high",
    "status": "pending",
    "evidence_package": {
      "dmca_notice_url": "https://storage.contentprotection.ai/notices/td_12345.pdf",
      "evidence_count": 3
    },
    "estimated_response_time": "7 days"
  }
}
```

**takedown.status_changed**
```json
{
  "id": "evt_td_002",
  "event": "takedown.status_changed",
  "timestamp": "2024-01-18T14:30:00Z",
  "data": {
    "takedown_id": "td_12345",
    "infringement_id": 12345,
    "profile_id": 42,
    "platform": "google",
    "old_status": "in_progress",
    "new_status": "completed",
    "platform_response": {
      "reference_number": "DMC-2024-12345",
      "response_url": "https://google.com/dmca/response/12345",
      "action_taken": "Content removed from search results"
    },
    "timeline": {
      "submitted_at": "2024-01-15T11:00:00Z",
      "acknowledged_at": "2024-01-16T09:15:00Z",
      "completed_at": "2024-01-18T14:30:00Z",
      "total_duration": "3d 3h 30m"
    }
  }
}
```

#### Profile Events

**profile.updated**
```json
{
  "id": "evt_prof_001",
  "event": "profile.updated",
  "timestamp": "2024-01-15T12:00:00Z",
  "data": {
    "profile_id": 42,
    "changes": {
      "keywords": {
        "old": ["creator name", "username"],
        "new": ["creator name", "username", "exclusive content"]
      },
      "monitoring_enabled": {
        "old": false,
        "new": true
      }
    },
    "updated_by": {
      "id": 123,
      "name": "Content Creator"
    }
  }
}
```

#### System Events

**system.maintenance**
```json
{
  "id": "evt_sys_001",
  "event": "system.maintenance",
  "timestamp": "2024-01-15T02:00:00Z",
  "data": {
    "maintenance_type": "scheduled",
    "affected_services": ["scanning", "takedowns"],
    "start_time": "2024-01-16T02:00:00Z",
    "end_time": "2024-01-16T04:00:00Z",
    "impact": "Scanning services will be temporarily unavailable",
    "notification_id": "maint_20240116"
  }
}
```

## WebSocket Integration

For real-time updates during active sessions, the platform provides WebSocket connections.

### Connecting to WebSocket

```javascript
const ws = new WebSocket('wss://api.contentprotection.ai/ws?token=YOUR_JWT_TOKEN');

ws.onopen = function(event) {
    console.log('WebSocket connected');
    
    // Subscribe to specific events
    ws.send(JSON.stringify({
        action: 'subscribe',
        events: ['scan.progress', 'infringement.detected']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    handleRealTimeEvent(data);
};

ws.onclose = function(event) {
    console.log('WebSocket disconnected');
    // Implement reconnection logic
};
```

### WebSocket Message Format

```json
{
  "type": "event",
  "event": "scan.progress",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "job_id": "scan_12345abc",
    "progress": {
      "completed": 75,
      "total": 150,
      "percentage": 50
    }
  }
}
```

### WebSocket Commands

**Subscribe to Events**
```json
{
  "action": "subscribe",
  "events": ["scan.progress", "infringement.detected"],
  "filters": {
    "profile_id": 42
  }
}
```

**Unsubscribe from Events**
```json
{
  "action": "unsubscribe",
  "events": ["scan.progress"]
}
```

**Ping/Pong for Connection Health**
```json
{
  "action": "ping"
}
```

## Security

### Webhook Signature Verification

All webhooks include a signature header for security verification:

```http
X-ContentProtection-Signature: sha256=f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8
```

#### Verifying Signatures

**Python Example:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature for security"""
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(
        f"sha256={expected_signature}",
        signature
    )

# Usage
payload = request.body
signature = request.headers.get('X-ContentProtection-Signature')
secret = 'your-webhook-secret'

if verify_webhook_signature(payload, signature, secret):
    # Process webhook
    process_webhook(json.loads(payload))
else:
    # Invalid signature
    return 401
```

**Node.js Example:**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
    const expectedSignature = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    
    return crypto.timingSafeEqual(
        Buffer.from(`sha256=${expectedSignature}`),
        Buffer.from(signature)
    );
}
```

### WebSocket Authentication

WebSocket connections require JWT authentication:

```javascript
const token = 'YOUR_JWT_TOKEN';
const ws = new WebSocket(`wss://api.contentprotection.ai/ws?token=${token}`);
```

## Implementation Examples

### Flask (Python) Webhook Handler

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)
WEBHOOK_SECRET = 'your-webhook-secret'

def verify_signature(payload, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

@app.route('/webhooks/contentprotection', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-ContentProtection-Signature')
    payload = request.get_data(as_text=True)
    
    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    event = json.loads(payload)
    event_type = event['event']
    
    # Handle different event types
    if event_type == 'scan.completed':
        handle_scan_completed(event['data'])
    elif event_type == 'infringement.detected':
        handle_infringement_detected(event['data'])
    elif event_type == 'takedown.status_changed':
        handle_takedown_status_changed(event['data'])
    
    return jsonify({'status': 'received'}), 200

def handle_scan_completed(data):
    job_id = data['job_id']
    results = data['results']
    
    print(f"Scan {job_id} completed with {results['infringements_found']} matches")
    
    # Send notification to user
    send_notification(
        f"Scan completed: {results['infringements_found']} potential infringements found"
    )
    
    # Auto-submit high-confidence takedowns
    if results['high_confidence_matches'] > 0:
        auto_submit_takedowns(job_id)

def handle_infringement_detected(data):
    infringement_id = data['infringement_id']
    confidence = data['confidence_score']
    url = data['url']
    
    print(f"New infringement detected: {url} (confidence: {confidence})")
    
    # High confidence - auto-submit takedown
    if confidence > 0.9:
        submit_takedown(infringement_id, urgency='high')
    # Medium confidence - flag for review
    elif confidence > 0.7:
        flag_for_manual_review(infringement_id)

def handle_takedown_status_changed(data):
    takedown_id = data['takedown_id']
    new_status = data['new_status']
    platform = data['platform']
    
    print(f"Takedown {takedown_id} on {platform}: {new_status}")
    
    if new_status == 'completed':
        send_success_notification(takedown_id)
    elif new_status == 'rejected':
        handle_takedown_rejection(takedown_id, data.get('rejection_reason'))

if __name__ == '__main__':
    app.run(debug=True)
```

### Express.js (Node.js) Webhook Handler

```javascript
const express = require('express');
const crypto = require('crypto');
const app = express();

const WEBHOOK_SECRET = 'your-webhook-secret';

// Middleware to capture raw body
app.use('/webhooks', express.raw({ type: 'application/json' }));

function verifySignature(payload, signature) {
    const expectedSignature = crypto
        .createHmac('sha256', WEBHOOK_SECRET)
        .update(payload)
        .digest('hex');
    
    return crypto.timingSafeEqual(
        Buffer.from(`sha256=${expectedSignature}`),
        Buffer.from(signature)
    );
}

app.post('/webhooks/contentprotection', (req, res) => {
    const signature = req.headers['x-contentprotection-signature'];
    const payload = req.body.toString();
    
    if (!verifySignature(payload, signature)) {
        return res.status(401).json({ error: 'Invalid signature' });
    }
    
    const event = JSON.parse(payload);
    
    // Handle events
    switch (event.event) {
        case 'scan.completed':
            handleScanCompleted(event.data);
            break;
        case 'infringement.detected':
            handleInfringementDetected(event.data);
            break;
        case 'takedown.status_changed':
            handleTakedownStatusChanged(event.data);
            break;
        default:
            console.log(`Unhandled event: ${event.event}`);
    }
    
    res.status(200).json({ status: 'received' });
});

async function handleScanCompleted(data) {
    const { job_id, results, profile_id } = data;
    
    console.log(`Scan ${job_id} completed for profile ${profile_id}`);
    
    // Update database
    await updateScanResults(job_id, results);
    
    // Send real-time update to connected clients
    io.to(`profile_${profile_id}`).emit('scan_completed', {
        job_id,
        results
    });
    
    // Auto-process high-confidence matches
    if (results.high_confidence_matches > 0) {
        await autoProcessHighConfidenceMatches(profile_id);
    }
}

async function handleInfringementDetected(data) {
    const { infringement_id, confidence_score, profile_id } = data;
    
    // Store in database
    await storeInfringement(data);
    
    // Send real-time notification
    io.to(`profile_${profile_id}`).emit('infringement_detected', data);
    
    // Auto-submit if high confidence
    if (confidence_score > 0.9) {
        await submitAutoTakedown(infringement_id);
    }
}

app.listen(3000, () => {
    console.log('Webhook server running on port 3000');
});
```

### React Frontend Real-Time Updates

```javascript
import React, { useState, useEffect } from 'react';
import { ContentProtectionClient } from '@contentprotection/api-client';

const RealTimeDashboard = () => {
    const [scans, setScans] = useState([]);
    const [infringements, setInfringements] = useState([]);
    const [takedowns, setTakedowns] = useState([]);
    const [ws, setWs] = useState(null);
    
    useEffect(() => {
        const client = new ContentProtectionClient();
        
        // Connect WebSocket
        const connectWebSocket = () => {
            const token = localStorage.getItem('access_token');
            const websocket = new WebSocket(`wss://api.contentprotection.ai/ws?token=${token}`);
            
            websocket.onopen = () => {
                console.log('WebSocket connected');
                
                // Subscribe to events
                websocket.send(JSON.stringify({
                    action: 'subscribe',
                    events: ['scan.progress', 'scan.completed', 'infringement.detected', 'takedown.status_changed']
                }));
            };
            
            websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleRealTimeEvent(data);
            };
            
            websocket.onclose = () => {
                console.log('WebSocket disconnected');
                // Reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
            
            setWs(websocket);
        };
        
        connectWebSocket();
        
        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, []);
    
    const handleRealTimeEvent = (data) => {
        switch (data.event) {
            case 'scan.progress':
                updateScanProgress(data.data);
                break;
            case 'scan.completed':
                updateScanCompleted(data.data);
                break;
            case 'infringement.detected':
                addNewInfringement(data.data);
                break;
            case 'takedown.status_changed':
                updateTakedownStatus(data.data);
                break;
        }
    };
    
    const updateScanProgress = (data) => {
        setScans(prev => prev.map(scan => 
            scan.job_id === data.job_id 
                ? { ...scan, progress: data.progress }
                : scan
        ));
    };
    
    const updateScanCompleted = (data) => {
        setScans(prev => prev.map(scan => 
            scan.job_id === data.job_id 
                ? { ...scan, status: 'completed', results: data.results }
                : scan
        ));
        
        // Show notification
        showNotification(`Scan completed: ${data.results.infringements_found} matches found`);
    };
    
    const addNewInfringement = (data) => {
        setInfringements(prev => [data, ...prev]);
        
        // Show notification for high confidence matches
        if (data.confidence_score > 0.9) {
            showNotification(`High confidence infringement detected: ${data.url}`, 'warning');
        }
    };
    
    const updateTakedownStatus = (data) => {
        setTakedowns(prev => prev.map(takedown => 
            takedown.takedown_id === data.takedown_id 
                ? { ...takedown, status: data.new_status }
                : takedown
        ));
        
        if (data.new_status === 'completed') {
            showNotification(`Takedown completed successfully!`, 'success');
        }
    };
    
    const showNotification = (message, type = 'info') => {
        // Implement your notification system
        console.log(`[${type.toUpperCase()}] ${message}`);
    };
    
    return (
        <div className="real-time-dashboard">
            <h1>Content Protection Dashboard</h1>
            
            {/* Active Scans */}
            <section className="active-scans">
                <h2>Active Scans</h2>
                {scans.filter(scan => scan.status === 'running').map(scan => (
                    <div key={scan.job_id} className="scan-item">
                        <div className="scan-info">
                            <span>{scan.profile_name}</span>
                            <span>{scan.job_id}</span>
                        </div>
                        <div className="progress-bar">
                            <div 
                                className="progress-fill"
                                style={{ width: `${scan.progress?.percentage || 0}%` }}
                            />
                        </div>
                        <span>{scan.progress?.percentage || 0}%</span>
                    </div>
                ))}
            </section>
            
            {/* Recent Infringements */}
            <section className="recent-infringements">
                <h2>Recent Infringements</h2>
                {infringements.slice(0, 10).map(infringement => (
                    <div key={infringement.infringement_id} className="infringement-item">
                        <div className="infringement-info">
                            <a href={infringement.url} target="_blank" rel="noopener noreferrer">
                                {infringement.url}
                            </a>
                            <span className={`confidence ${getConfidenceClass(infringement.confidence_score)}`}>
                                {(infringement.confidence_score * 100).toFixed(0)}%
                            </span>
                        </div>
                        <div className="infringement-meta">
                            <span>{infringement.platform}</span>
                            <span>{new Date(infringement.detected_at).toLocaleString()}</span>
                        </div>
                    </div>
                ))}
            </section>
            
            {/* Takedown Status */}
            <section className="takedown-status">
                <h2>Takedown Requests</h2>
                {takedowns.slice(0, 10).map(takedown => (
                    <div key={takedown.takedown_id} className="takedown-item">
                        <div className="takedown-info">
                            <span>{takedown.takedown_id}</span>
                            <span className={`status ${takedown.status}`}>
                                {takedown.status}
                            </span>
                        </div>
                        <div className="takedown-meta">
                            <span>{takedown.platform}</span>
                            <span>{new Date(takedown.submitted_at).toLocaleString()}</span>
                        </div>
                    </div>
                ))}
            </section>
        </div>
    );
};

const getConfidenceClass = (confidence) => {
    if (confidence > 0.9) return 'high';
    if (confidence > 0.7) return 'medium';
    return 'low';
};

export default RealTimeDashboard;
```

## Best Practices

### Webhook Implementation

1. **Idempotency**: Store event IDs to prevent duplicate processing
2. **Timeout Handling**: Respond within 10 seconds to avoid retries
3. **Error Handling**: Return appropriate HTTP status codes
4. **Signature Verification**: Always verify webhook signatures
5. **Graceful Degradation**: Handle missing or malformed data

### WebSocket Implementation

1. **Reconnection Logic**: Implement automatic reconnection with exponential backoff
2. **Heartbeat**: Use ping/pong to detect connection issues
3. **Subscription Management**: Track active subscriptions
4. **Error Recovery**: Handle connection errors gracefully
5. **Resource Cleanup**: Close connections properly

### Performance Optimization

1. **Async Processing**: Process webhooks asynchronously to avoid blocking
2. **Queue Management**: Use message queues for high-volume events
3. **Batching**: Batch similar operations when possible
4. **Caching**: Cache frequently accessed data
5. **Rate Limiting**: Implement client-side rate limiting

### Security Considerations

1. **HTTPS Only**: Always use HTTPS for webhook endpoints
2. **Signature Verification**: Verify all webhook signatures
3. **IP Whitelisting**: Whitelist platform IP addresses if possible
4. **Token Security**: Securely store and rotate webhook secrets
5. **Access Control**: Limit webhook endpoint access

## Troubleshooting

### Common Issues

**Webhook Not Receiving Events**
- Check webhook URL accessibility
- Verify webhook is active in dashboard
- Check firewall and proxy settings
- Ensure endpoint responds with 2xx status

**WebSocket Connection Issues**
- Verify JWT token validity
- Check network connectivity
- Implement proper reconnection logic
- Monitor connection health with ping/pong

**Event Processing Errors**
- Check event payload structure
- Implement proper error handling
- Log detailed error information
- Monitor processing performance

### Debugging Tools

**Webhook Testing**
```bash
# Test webhook endpoint
curl -X POST "https://your-app.com/webhooks/contentprotection" \
  -H "Content-Type: application/json" \
  -H "X-ContentProtection-Signature: sha256=test" \
  -d '{"event":"test","data":{}}'
```

**WebSocket Testing**
```javascript
// Test WebSocket connection
const ws = new WebSocket('wss://api.contentprotection.ai/ws?token=test');
ws.onopen = () => console.log('Connected');
ws.onerror = (error) => console.error('Error:', error);
```

### Support

For webhook and real-time integration support:
- **Documentation**: https://docs.contentprotection.ai/webhooks
- **API Support**: api-support@contentprotection.ai
- **Discord Community**: https://discord.gg/contentprotection
- **GitHub Issues**: https://github.com/contentprotection/api-examples/issues