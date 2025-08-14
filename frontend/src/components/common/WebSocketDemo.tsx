import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Divider } from 'primereact/divider';
import { 
  useConnectionStatus, 
  useDashboardRealtime,
  useSubmissionRealtime,
  useNotificationsRealtime,
  useWebSocket 
} from '../../contexts/WebSocketContext';
import WebSocketStatus from './WebSocketStatus';
import { MessageType } from '../../services/websocket';

/**
 * Demo component showing WebSocket system usage
 */
const WebSocketDemo: React.FC = () => {
  const { isConnected, health, connect, disconnect, reconnect } = useConnectionStatus();
  const { sendMessage } = useWebSocket();
  const { dashboardStats } = useDashboardRealtime();
  const { submissionUpdates } = useSubmissionRealtime();
  const { notifications } = useNotificationsRealtime();
  
  const [testMessageCount, setTestMessageCount] = useState(0);

  const sendTestMessage = () => {
    const success = sendMessage({
      type: MessageType.USER_NOTIFICATION,
      payload: {
        title: 'Test Notification',
        message: `Test message #${testMessageCount + 1}`,
        type: 'info',
        timestamp: new Date().toISOString(),
      },
    });
    
    if (success) {
      setTestMessageCount(prev => prev + 1);
    }
  };

  const getConnectionBadgeSeverity = () => {
    if (isConnected) return 'success';
    if (health.reconnectAttempts > 0) return 'warning';
    return 'danger';
  };

  const formatDuration = (date?: Date) => {
    if (!date) return 'N/A';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const submissionData = Array.from(submissionUpdates.entries()).map(([id, update]) => ({
    id,
    status: update.status || 'unknown',
    progress: update.progress || 0,
    lastUpdate: update.lastUpdate || new Date().toISOString(),
  }));

  const statusBodyTemplate = (rowData: any) => (
    <Tag 
      value={rowData.status} 
      severity={rowData.status === 'completed' ? 'success' : 
               rowData.status === 'failed' ? 'danger' : 'info'} 
    />
  );

  const progressBodyTemplate = (rowData: any) => (
    <div className="flex align-items-center">
      <div className="mr-2">{rowData.progress}%</div>
      <div 
        className="surface-300 border-round" 
        style={{ width: '100px', height: '8px', background: '#e0e0e0' }}
      >
        <div 
          className="bg-primary border-round" 
          style={{ 
            width: `${rowData.progress}%`, 
            height: '100%',
            transition: 'width 0.3s ease'
          }}
        />
      </div>
    </div>
  );

  return (
    <div className="websocket-demo p-4">
      <div className="grid">
        {/* Connection Status */}
        <div className="col-12 md:col-6">
          <Card title="Connection Status" className="h-full">
            <div className="flex align-items-center justify-content-between mb-3">
              <div className="flex align-items-center">
                <Badge 
                  value={isConnected ? 'Connected' : 'Disconnected'} 
                  severity={getConnectionBadgeSeverity()}
                  className="mr-2"
                />
                <WebSocketStatus showDetails={false} />
              </div>
              <div className="flex gap-2">
                <Button 
                  icon="pi pi-play" 
                  size="small" 
                  severity="success"
                  onClick={connect}
                  disabled={isConnected}
                  tooltip="Connect"
                />
                <Button 
                  icon="pi pi-pause" 
                  size="small" 
                  severity="danger"
                  onClick={disconnect}
                  disabled={!isConnected}
                  tooltip="Disconnect"
                />
                <Button 
                  icon="pi pi-refresh" 
                  size="small" 
                  severity="info"
                  onClick={reconnect}
                  tooltip="Reconnect"
                />
              </div>
            </div>
            
            <div className="grid text-sm">
              <div className="col-6">
                <strong>Uptime:</strong><br />
                {formatDuration(health.connectedAt)}
              </div>
              <div className="col-6">
                <strong>Messages:</strong><br />
                ↑{health.messagesSent} ↓{health.messagesReceived}
              </div>
              <div className="col-6">
                <strong>Latency:</strong><br />
                {health.latency ? `${health.latency}ms` : 'N/A'}
              </div>
              <div className="col-6">
                <strong>Reconnects:</strong><br />
                {health.reconnectAttempts}
              </div>
            </div>
          </Card>
        </div>

        {/* Dashboard Stats */}
        <div className="col-12 md:col-6">
          <Card title="Dashboard Statistics" className="h-full">
            {dashboardStats ? (
              <div className="grid text-sm">
                <div className="col-6">
                  <strong>Total Profiles:</strong><br />
                  <span className="text-2xl font-bold text-primary">
                    {dashboardStats.totalProfiles || 0}
                  </span>
                </div>
                <div className="col-6">
                  <strong>Active Scans:</strong><br />
                  <span className="text-2xl font-bold text-orange-500">
                    {dashboardStats.activeScans || 0}
                  </span>
                </div>
                <div className="col-6">
                  <strong>Infringements:</strong><br />
                  <span className="text-2xl font-bold text-red-500">
                    {dashboardStats.infringementsFound || 0}
                  </span>
                </div>
                <div className="col-6">
                  <strong>Takedowns:</strong><br />
                  <span className="text-2xl font-bold text-green-500">
                    {dashboardStats.takedownsSent || 0}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center text-color-secondary py-4">
                No dashboard data available
              </div>
            )}
          </Card>
        </div>

        {/* Test Controls */}
        <div className="col-12">
          <Card title="Test Controls">
            <div className="flex align-items-center justify-content-between">
              <div>
                <Button
                  label="Send Test Message"
                  icon="pi pi-send"
                  onClick={sendTestMessage}
                  disabled={!isConnected}
                  className="mr-3"
                />
                <span className="text-sm text-color-secondary">
                  Messages sent: {testMessageCount}
                </span>
              </div>
              <Badge 
                value={`${notifications.length} notifications`} 
                severity="info" 
              />
            </div>
          </Card>
        </div>

        {/* Submission Updates */}
        <div className="col-12 lg:col-8">
          <Card title="Live Submission Updates">
            {submissionData.length > 0 ? (
              <DataTable 
                value={submissionData} 
                size="small"
                className="p-datatable-sm"
              >
                <Column field="id" header="Submission ID" />
                <Column 
                  field="status" 
                  header="Status" 
                  body={statusBodyTemplate}
                />
                <Column 
                  field="progress" 
                  header="Progress" 
                  body={progressBodyTemplate}
                />
                <Column 
                  field="lastUpdate" 
                  header="Last Update" 
                  body={(rowData) => new Date(rowData.lastUpdate).toLocaleTimeString()}
                />
              </DataTable>
            ) : (
              <div className="text-center text-color-secondary py-4">
                No active submissions
              </div>
            )}
          </Card>
        </div>

        {/* Recent Notifications */}
        <div className="col-12 lg:col-4">
          <Card title="Recent Notifications" className="h-full">
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {notifications.length > 0 ? (
                notifications.slice(0, 10).map((notification, index) => (
                  <div key={index} className="border-bottom-1 surface-border pb-2 mb-2">
                    <div className="flex align-items-start justify-content-between">
                      <div className="flex-1">
                        <div className="font-semibold text-sm">
                          {notification.title || 'Notification'}
                        </div>
                        <div className="text-sm text-color-secondary mt-1">
                          {notification.message || notification.description}
                        </div>
                      </div>
                      <Tag 
                        value={notification.type || 'info'} 
                        severity={notification.type === 'error' ? 'danger' : 'info'}
                        className="ml-2"
                      />
                    </div>
                    <div className="text-xs text-color-secondary mt-1">
                      {new Date(notification.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-color-secondary py-4">
                  No notifications
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      <Divider />

      {/* Usage Instructions */}
      <Card title="Usage Instructions" className="mt-4">
        <div className="grid">
          <div className="col-12 md:col-6">
            <h6>Real-time Hooks Available:</h6>
            <ul className="text-sm">
              <li><code>useDashboardRealtime()</code> - Dashboard statistics</li>
              <li><code>useSubmissionRealtime()</code> - Submission progress</li>
              <li><code>useProfileRealtime()</code> - Profile activities</li>
              <li><code>useAIContentRealtime()</code> - AI detection results</li>
              <li><code>useSocialMediaRealtime()</code> - Social media incidents</li>
              <li><code>useTemplateRealtime()</code> - DMCA template updates</li>
              <li><code>useDelistingRealtime()</code> - Search engine delisting</li>
              <li><code>useNotificationsRealtime()</code> - System notifications</li>
            </ul>
          </div>
          <div className="col-12 md:col-6">
            <h6>Connection Management:</h6>
            <ul className="text-sm">
              <li><code>useConnectionStatus()</code> - Connection state and health</li>
              <li><code>useWebSocket()</code> - Send messages and custom subscriptions</li>
              <li><code>&lt;WebSocketStatus /&gt;</code> - Status indicator component</li>
              <li><code>&lt;WebSocketHealthMonitor /&gt;</code> - Health warning component</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default WebSocketDemo;