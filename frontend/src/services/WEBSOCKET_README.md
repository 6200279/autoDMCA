# AutoDMCA Real-time WebSocket System

This document provides comprehensive documentation for the AutoDMCA application's real-time WebSocket system.

## Overview

The WebSocket system provides real-time communication between the client and server, enabling live updates for various application features including dashboard statistics, submission progress, profile activities, AI detection results, social media incidents, template updates, search engine delisting, and system notifications.

## Architecture

### Core Components

1. **WebSocketService** (`/services/websocket.ts`)
   - Centralized WebSocket connection management
   - Automatic reconnection with exponential backoff
   - Authentication handling
   - Message routing and subscription management
   - Connection health monitoring

2. **WebSocketContext** (`/contexts/WebSocketContext.tsx`)
   - React context for global state management
   - Real-time data state management
   - Subscription lifecycle management
   - React hooks for specific feature areas

3. **WebSocketStatus** (`/components/common/WebSocketStatus.tsx`)
   - Connection status monitoring component
   - Health metrics display
   - Connection control interface

## Features

### Connection Management
- **Automatic Connection**: Connects automatically when user is authenticated
- **Auto-reconnection**: Attempts to reconnect with exponential backoff on connection loss
- **Authentication**: JWT token-based authentication with automatic token updates
- **Health Monitoring**: Tracks connection metrics including latency, message counts, and uptime

### Real-time Updates
- **Dashboard Statistics**: Live dashboard metrics and analytics updates
- **Submission Progress**: Real-time submission status and progress tracking
- **Profile Activities**: Live profile scan updates and activity notifications
- **AI Content Matching**: Detection results, model training updates, and batch job status
- **Social Media Protection**: Incident detection, scan status, and platform updates
- **DMCA Templates**: Template validation, approval status, and usage tracking
- **Search Engine Delisting**: Request status updates, visibility changes, and engine responses
- **System Notifications**: User and system-wide notifications

### Error Handling
- **Graceful Degradation**: Application continues to function when WebSocket is unavailable
- **Reconnection Logic**: Automatic reconnection with configurable retry limits
- **Fallback Mechanisms**: Can fall back to polling when WebSocket fails
- **Error Notifications**: User-friendly error messages and status indicators

## Usage

### Basic Setup

The WebSocket system is automatically initialized in `App.tsx`:

```tsx
<WebSocketProvider
  autoConnect={true}
  reconnectOnError={true}
  maxReconnectAttempts={10}
  debug={process.env.NODE_ENV === 'development'}
>
  <LayoutProvider>
    <AppContent />
  </LayoutProvider>
</WebSocketProvider>
```

### Using Real-time Hooks

#### Dashboard Updates
```tsx
import { useDashboardRealtime } from '../contexts/WebSocketContext';

function DashboardComponent() {
  const { dashboardStats } = useDashboardRealtime();
  
  return (
    <div>
      {dashboardStats && (
        <div>
          <p>Total Profiles: {dashboardStats.totalProfiles}</p>
          <p>Active Scans: {dashboardStats.activeScans}</p>
          {/* ... other stats */}
        </div>
      )}
    </div>
  );
}
```

#### Submission Progress Tracking
```tsx
import { useSubmissionRealtime } from '../contexts/WebSocketContext';

function SubmissionsPage() {
  const { submissionUpdates, getSubmissionUpdate } = useSubmissionRealtime();
  
  const handleSubmissionUpdate = (submissionId: string) => {
    const update = getSubmissionUpdate(submissionId);
    if (update) {
      console.log(`Submission ${submissionId} progress:`, update.progress);
    }
  };
  
  return (
    <div>
      {/* Submission components */}
    </div>
  );
}
```

#### Connection Status Monitoring
```tsx
import { useConnectionStatus } from '../contexts/WebSocketContext';
import WebSocketStatus from '../components/common/WebSocketStatus';

function Header() {
  const { isConnected } = useConnectionStatus();
  
  return (
    <header>
      <h1>AutoDMCA</h1>
      <WebSocketStatus showDetails={true} />
      {!isConnected && (
        <span className="connection-warning">Offline Mode</span>
      )}
    </header>
  );
}
```

### Advanced Usage

#### Custom Message Handling
```tsx
import { useWebSocket } from '../contexts/WebSocketContext';
import { MessageType } from '../services/websocket';

function CustomComponent() {
  const { subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'custom-component';
    
    subscribe(subscriptionId, {
      types: [MessageType.USER_NOTIFICATION],
    }, (message) => {
      console.log('Received notification:', message.payload);
      // Handle custom logic
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe]);
  
  return <div>Custom Component</div>;
}
```

#### Sending Messages
```tsx
import { useWebSocket } from '../contexts/WebSocketContext';
import { MessageType } from '../services/websocket';

function ActionComponent() {
  const { sendMessage } = useWebSocket();
  
  const handleAction = () => {
    const success = sendMessage({
      type: MessageType.USER_NOTIFICATION,
      payload: {
        action: 'custom_action',
        data: { /* action data */ },
      },
    });
    
    if (!success) {
      console.log('Message queued for sending when connected');
    }
  };
  
  return (
    <button onClick={handleAction}>
      Perform Action
    </button>
  );
}
```

## Message Types

The system supports various message types defined in `MessageType` enum:

### Dashboard Updates
- `DASHBOARD_STATS_UPDATE`: Real-time dashboard statistics

### Submission Updates
- `SUBMISSION_PROGRESS`: Submission processing progress
- `SUBMISSION_STATUS_CHANGE`: Status changes (pending, processing, completed, etc.)

### Profile Updates
- `PROFILE_ACTIVITY`: Profile-related activities and events
- `PROFILE_SCAN_UPDATE`: Scan progress and results

### AI Content Matching
- `AI_DETECTION_RESULT`: Content detection results
- `AI_MODEL_TRAINING_UPDATE`: Model training progress
- `AI_BATCH_JOB_STATUS`: Batch processing job status

### Social Media Protection
- `SOCIAL_MEDIA_INCIDENT`: New incidents detected
- `SOCIAL_MEDIA_SCAN_STATUS`: Platform scan status updates
- `SOCIAL_MEDIA_PLATFORM_STATUS`: Platform connection status

### DMCA Templates
- `TEMPLATE_VALIDATION`: Template validation results
- `TEMPLATE_APPROVAL`: Approval workflow updates
- `TEMPLATE_USAGE`: Usage statistics and tracking

### Search Engine Delisting
- `DELISTING_REQUEST_STATUS`: Request processing status
- `VISIBILITY_CHANGE`: URL visibility changes
- `ENGINE_RESPONSE`: Search engine responses

### System Notifications
- `SYSTEM_NOTIFICATION`: System-wide notifications
- `USER_NOTIFICATION`: User-specific notifications

## Configuration

### Environment Variables
```env
# WebSocket server URL
REACT_APP_WS_URL=wss://your-domain.com/ws

# Alternative WebSocket host (if different from main domain)
REACT_APP_WS_HOST=ws.your-domain.com

# Enable debug logging in development
NODE_ENV=development
```

### WebSocket Service Configuration
```typescript
const config = {
  url: 'wss://your-domain.com/ws',
  reconnectInterval: 3000,        // Reconnect interval in ms
  maxReconnectAttempts: 10,       // Maximum reconnection attempts
  heartbeatInterval: 30000,       // Heartbeat interval in ms
  authToken: 'your-jwt-token',    // JWT authentication token
  debug: true,                    // Enable debug logging
};
```

## Connection States

The WebSocket connection can be in one of the following states:

- **CONNECTING**: Initial connection attempt in progress
- **CONNECTED**: Successfully connected and ready for communication
- **DISCONNECTED**: Not connected (initial state or after manual disconnect)
- **RECONNECTING**: Attempting to reconnect after connection loss
- **ERROR**: Connection failed and maximum retry attempts reached

## Health Monitoring

The system tracks various health metrics:

```typescript
interface ConnectionHealth {
  state: WebSocketState;
  connectedAt?: Date;           // When connection was established
  lastMessageAt?: Date;         // Last message received timestamp
  reconnectAttempts: number;    // Number of reconnection attempts
  messagesReceived: number;     // Total messages received
  messagesSent: number;         // Total messages sent
  latency?: number;             // Connection latency in ms
}
```

## Error Handling

### Automatic Recovery
- **Connection Loss**: Automatically attempts to reconnect with exponential backoff
- **Message Queuing**: Messages sent while disconnected are queued and sent when reconnected
- **Graceful Degradation**: Application remains functional without real-time features

### Error Notifications
- **Connection Status**: Visual indicators show connection state
- **User Notifications**: Inform users when connection issues occur
- **Health Warnings**: Persistent warnings for extended connection issues

### Fallback Strategies
```typescript
// Example: Fallback to polling when WebSocket fails
useEffect(() => {
  if (!isConnected && retryCount > maxRetries) {
    // Fall back to polling
    const interval = setInterval(() => {
      fetchDataFromAPI();
    }, 5000);
    
    return () => clearInterval(interval);
  }
}, [isConnected, retryCount]);
```

## Best Practices

### Performance
1. **Selective Subscriptions**: Only subscribe to message types you need
2. **Efficient State Updates**: Use Map/Set for frequently updated collections
3. **Debounce Updates**: Debounce rapid state updates to prevent excessive re-renders
4. **Memory Management**: Unsubscribe from events when components unmount

### Error Handling
1. **Graceful Degradation**: Ensure application works without real-time features
2. **User Feedback**: Provide clear feedback about connection status
3. **Retry Logic**: Implement appropriate retry strategies with backoff
4. **Logging**: Log connection events and errors for debugging

### Security
1. **Authentication**: Always authenticate WebSocket connections
2. **Token Refresh**: Handle JWT token expiration and refresh
3. **Message Validation**: Validate incoming messages on both client and server
4. **Rate Limiting**: Implement rate limiting to prevent abuse

## Debugging

### Debug Logging
Enable debug logging by setting `debug: true` in the WebSocket configuration:

```typescript
const wsService = getWebSocketService({
  debug: process.env.NODE_ENV === 'development',
});
```

### Connection Status Component
Use the `WebSocketStatus` component to monitor connection health:

```tsx
<WebSocketStatus showDetails={true} />
```

### Browser Developer Tools
- **Network Tab**: Monitor WebSocket connection in the Network tab
- **Console**: View debug logs and error messages
- **Application Tab**: Check WebSocket frames and message history

### Common Issues

1. **Connection Refused**: Check WebSocket server URL and availability
2. **Authentication Errors**: Verify JWT token validity and format
3. **Message Not Received**: Check subscription configuration and message types
4. **High Memory Usage**: Ensure proper cleanup of subscriptions and state

## Server Integration

### Expected Server Endpoints
- `GET /ws`: WebSocket endpoint for establishing connections
- `POST /ws/subscribe`: Subscription management (if using HTTP-based subscriptions)
- `DELETE /ws/subscribe/{id}`: Unsubscribe from updates

### Message Format
```json
{
  "type": "dashboard_stats_update",
  "payload": {
    "totalProfiles": 150,
    "activeScans": 12,
    "infringementsFound": 245
  },
  "timestamp": "2023-12-07T10:30:00Z",
  "id": "msg_1701944200_abc123",
  "userId": 12345
}
```

### Authentication
Server should expect JWT token in:
1. WebSocket URL query parameter: `wss://domain.com/ws?token=jwt_token`
2. Initial authentication message after connection

### Heartbeat Protocol
- Client sends heartbeat every 30 seconds
- Server responds with heartbeat acknowledgment
- Connection considered dead if no response within 60 seconds

## Migration from Legacy Hooks

The system maintains backward compatibility with existing hooks:

### `useWebSocket` Hook
```tsx
// Old usage (still works)
const { isConnected, sendMessage } = useWebSocket({
  url: 'ws://localhost:8000/ws/social-media',
  onMessage: handleMessage,
});

// New usage (recommended)
const { socialMediaIncidents } = useSocialMediaRealtime();
```

### `useTemplateRealtime` Hook
```tsx
// Old usage (still works)
const { lastUpdate } = useTemplateRealtime({
  templateIds: ['template-1', 'template-2'],
  onUpdate: handleTemplateUpdate,
});

// New usage (recommended)
const { templateUpdates } = useTemplateRealtime(['template-1', 'template-2']);
```

## Testing

### Unit Tests
Test individual components and hooks with mocked WebSocket context:

```tsx
import { WebSocketContext } from '../contexts/WebSocketContext';

const mockContextValue = {
  isConnected: true,
  dashboardStats: { totalProfiles: 100 },
  // ... other mock values
};

test('component renders with WebSocket data', () => {
  render(
    <WebSocketContext.Provider value={mockContextValue}>
      <MyComponent />
    </WebSocketContext.Provider>
  );
  
  expect(screen.getByText('100 profiles')).toBeInTheDocument();
});
```

### Integration Tests
Test WebSocket functionality with a test server:

```javascript
// Test server setup
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    const data = JSON.parse(message);
    // Echo back test responses
    ws.send(JSON.stringify({
      type: 'test_response',
      payload: data.payload,
    }));
  });
});
```

## Troubleshooting

### Common Problems

1. **"WebSocket connection failed"**
   - Check WebSocket server is running and accessible
   - Verify URL configuration
   - Check for proxy/firewall blocking WebSocket connections

2. **"Authentication failed"**
   - Verify JWT token is valid and not expired
   - Check token format and signing key
   - Ensure user has necessary permissions

3. **"Messages not received"**
   - Verify subscription configuration
   - Check message type matching
   - Ensure WebSocket connection is established

4. **"High CPU usage"**
   - Check for excessive re-renders due to state updates
   - Implement proper memoization
   - Optimize subscription filters

5. **"Memory leaks"**
   - Ensure all subscriptions are properly cleaned up
   - Check for retained references in closures
   - Use React DevTools Profiler to identify issues

### Performance Monitoring

Monitor WebSocket performance using:
- Connection health metrics
- Message throughput
- Reconnection frequency
- Memory usage patterns

## Future Enhancements

Planned improvements for the WebSocket system:

1. **Message Persistence**: Store messages locally for offline access
2. **Advanced Filtering**: More sophisticated subscription filtering
3. **Compression**: Message compression for reduced bandwidth
4. **Clustering**: Support for multiple WebSocket servers
5. **Metrics Dashboard**: Real-time monitoring of WebSocket health
6. **A/B Testing**: Framework for testing WebSocket features

## Support

For issues or questions regarding the WebSocket system:

1. Check this documentation first
2. Review browser console for error messages
3. Check network tab for WebSocket connection issues
4. Enable debug logging for detailed information
5. Contact the development team with specific error details

---

This WebSocket system provides a robust, scalable foundation for real-time features in the AutoDMCA application. It handles the complexities of WebSocket connections while providing a simple, React-friendly interface for consuming real-time data.