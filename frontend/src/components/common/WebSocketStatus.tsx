import React, { useState, useEffect } from 'react';
import { Badge } from 'primereact/badge';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Divider } from 'primereact/divider';
import { Message } from 'primereact/message';
import { useConnectionStatus, useWebSocket } from '../../contexts/WebSocketContext';
import { WebSocketState } from '../../services/websocket';
import './WebSocketStatus.css';

interface WebSocketStatusProps {
  showDetails?: boolean;
  className?: string;
}

const WebSocketStatus: React.FC<WebSocketStatusProps> = ({ 
  showDetails = false, 
  className = '' 
}) => {
  const { state, isConnected, health, error, connect, disconnect, reconnect } = useConnectionStatus();
  const { lastMessage } = useWebSocket();
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [lastMessageTime, setLastMessageTime] = useState<Date | null>(null);

  // Update last message time
  useEffect(() => {
    if (lastMessage) {
      setLastMessageTime(new Date());
    }
  }, [lastMessage]);

  const getStatusInfo = () => {
    switch (state) {
      case WebSocketState.CONNECTED:
        return {
          icon: 'pi-wifi',
          severity: 'success' as const,
          label: 'Connected',
          color: '#22c55e',
        };
      case WebSocketState.CONNECTING:
        return {
          icon: 'pi-spin pi-spinner',
          severity: 'info' as const,
          label: 'Connecting...',
          color: '#3b82f6',
        };
      case WebSocketState.RECONNECTING:
        return {
          icon: 'pi-spin pi-refresh',
          severity: 'warning' as const,
          label: `Reconnecting (${health.reconnectAttempts})`,
          color: '#f59e0b',
        };
      case WebSocketState.ERROR:
        return {
          icon: 'pi-exclamation-triangle',
          severity: 'danger' as const,
          label: 'Error',
          color: '#ef4444',
        };
      default:
        return {
          icon: 'pi-times-circle',
          severity: 'secondary' as const,
          label: 'Disconnected',
          color: '#6b7280',
        };
    }
  };

  const statusInfo = getStatusInfo();

  const formatDuration = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ago`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s ago`;
    } else {
      return `${seconds}s ago`;
    }
  };

  const formatLatency = (latency?: number) => {
    if (!latency) return 'N/A';
    if (latency < 100) return `${latency}ms (Excellent)`;
    if (latency < 300) return `${latency}ms (Good)`;
    if (latency < 1000) return `${latency}ms (Fair)`;
    return `${latency}ms (Poor)`;
  };

  const renderStatusBadge = () => (
    <Badge
      value=""
      severity={statusInfo.severity}
      className={`websocket-status-badge ${className}`}
    >
      <i className={`pi ${statusInfo.icon}`} style={{ color: statusInfo.color }} />
      {showDetails && <span className="ml-2">{statusInfo.label}</span>}
    </Badge>
  );

  const renderDetailsDialog = () => (
    <Dialog
      header="WebSocket Connection Status"
      visible={detailsVisible}
      onHide={() => setDetailsVisible(false)}
      style={{ width: '500px' }}
      modal
      closable
    >
      <div className="websocket-details">
        {/* Connection Status */}
        <div className="field">
          <label className="font-semibold">Status:</label>
          <div className="flex align-items-center mt-2">
            {state === WebSocketState.CONNECTING || state === WebSocketState.RECONNECTING ? (
              <ProgressSpinner size="20" strokeWidth="8" />
            ) : (
              <i className={`pi ${statusInfo.icon}`} style={{ color: statusInfo.color, fontSize: '1.2rem' }} />
            )}
            <span className="ml-2">{statusInfo.label}</span>
          </div>
        </div>

        <Divider />

        {/* Error Message */}
        {error && (
          <>
            <Message severity="error" text={error} className="mb-3" />
            <Divider />
          </>
        )}

        {/* Connection Details */}
        <div className="grid">
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Connected At:</label>
              <div className="mt-1">
                {health.connectedAt ? formatDuration(health.connectedAt) : 'Never'}
              </div>
            </div>
          </div>
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Last Message:</label>
              <div className="mt-1">
                {lastMessageTime ? formatDuration(lastMessageTime) : 'Never'}
              </div>
            </div>
          </div>
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Latency:</label>
              <div className="mt-1">{formatLatency(health.latency)}</div>
            </div>
          </div>
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Reconnect Attempts:</label>
              <div className="mt-1">{health.reconnectAttempts}</div>
            </div>
          </div>
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Messages Received:</label>
              <div className="mt-1">{health.messagesReceived}</div>
            </div>
          </div>
          <div className="col-6">
            <div className="field">
              <label className="font-semibold">Messages Sent:</label>
              <div className="mt-1">{health.messagesSent}</div>
            </div>
          </div>
        </div>

        <Divider />

        {/* Connection Controls */}
        <div className="flex justify-content-between align-items-center">
          <div className="flex gap-2">
            {!isConnected ? (
              <Button
                label="Connect"
                icon="pi pi-play"
                onClick={connect}
                size="small"
                severity="success"
              />
            ) : (
              <Button
                label="Disconnect"
                icon="pi pi-pause"
                onClick={disconnect}
                size="small"
                severity="danger"
              />
            )}
            <Button
              label="Reconnect"
              icon="pi pi-refresh"
              onClick={reconnect}
              size="small"
              severity="info"
            />
          </div>
        </div>

        {/* Last Message Info */}
        {lastMessage && (
          <>
            <Divider />
            <div className="field">
              <label className="font-semibold">Last Message:</label>
              <div className="mt-2 p-3 surface-100 border-round">
                <div className="grid">
                  <div className="col-6">
                    <strong>Type:</strong> {lastMessage.type}
                  </div>
                  <div className="col-6">
                    <strong>Time:</strong> {new Date(lastMessage.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                {lastMessage.id && (
                  <div className="mt-2">
                    <strong>ID:</strong> <code className="text-sm">{lastMessage.id}</code>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </Dialog>
  );

  return (
    <div className="websocket-status">
      <div 
        onClick={() => setDetailsVisible(true)}
        className="cursor-pointer"
        title={`WebSocket: ${statusInfo.label}${error ? ` - ${error}` : ''}`}
      >
        {renderStatusBadge()}
      </div>
      {renderDetailsDialog()}
    </div>
  );
};

// Minimal status indicator for header/footer
export const WebSocketStatusIndicator: React.FC = () => {
  const { isConnected } = useConnectionStatus();
  
  return (
    <div className="websocket-indicator">
      <i 
        className={`pi ${isConnected ? 'pi-circle-fill' : 'pi-circle'}`}
        style={{ 
          color: isConnected ? '#22c55e' : '#ef4444',
          fontSize: '8px'
        }}
        title={isConnected ? 'Connected' : 'Disconnected'}
      />
    </div>
  );
};

// Connection health monitor component
export const WebSocketHealthMonitor: React.FC = () => {
  const { state, health, error } = useConnectionStatus();
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    // Show warning if disconnected for more than 30 seconds or multiple reconnect attempts
    const shouldWarn = (
      state === WebSocketState.DISCONNECTED ||
      state === WebSocketState.ERROR ||
      health.reconnectAttempts > 3
    );
    
    if (shouldWarn && !showWarning) {
      setShowWarning(true);
    } else if (!shouldWarn && showWarning) {
      setShowWarning(false);
    }
  }, [state, health.reconnectAttempts, showWarning]);

  if (!showWarning) return null;

  return (
    <Message
      severity="warn"
      className="websocket-health-warning mb-3"
      content={
        <div>
          <strong>Connection Issue:</strong> {error || 'WebSocket connection is unstable'}
          {health.reconnectAttempts > 0 && ` (${health.reconnectAttempts} reconnect attempts)`}
        </div>
      }
    />
  );
};

export default WebSocketStatus;