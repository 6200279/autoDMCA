import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '@types/index';

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, ((data: any) => void)[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(token?: string) {
    if (this.socket?.connected) return;

    const url = process.env.REACT_APP_WS_URL || 'ws://localhost:3001';
    
    this.socket = io(url, {
      auth: {
        token: token || localStorage.getItem('authToken'),
      },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('connection_status', { connected: false, reason });
    });

    this.socket.on('reconnect_attempt', (attempt) => {
      console.log(`WebSocket reconnection attempt ${attempt}`);
      this.reconnectAttempts = attempt;
    });

    this.socket.on('reconnect_failed', () => {
      console.error('WebSocket reconnection failed');
      this.emit('connection_failed', { 
        message: 'Failed to reconnect to server' 
      });
    });

    // Listen for different types of real-time updates
    this.socket.on('infringement_detected', (data) => {
      this.emit('infringement_detected', data);
    });

    this.socket.on('status_update', (data) => {
      this.emit('status_update', data);
    });

    this.socket.on('takedown_success', (data) => {
      this.emit('takedown_success', data);
    });

    this.socket.on('system_alert', (data) => {
      this.emit('system_alert', data);
    });

    this.socket.on('analytics_update', (data) => {
      this.emit('analytics_update', data);
    });

    this.socket.on('user_activity', (data) => {
      this.emit('user_activity', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.listeners.clear();
    }
  }

  // Subscribe to specific events
  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  // Unsubscribe from events
  off(event: string, callback?: (data: any) => void) {
    if (!this.listeners.has(event)) return;

    if (callback) {
      const callbacks = this.listeners.get(event)!;
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    } else {
      this.listeners.delete(event);
    }
  }

  // Emit events to listeners
  private emit(event: string, data: any) {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket event handler for ${event}:`, error);
        }
      });
    }
  }

  // Send messages to server
  send(event: string, data: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('WebSocket not connected. Cannot send message:', event, data);
    }
  }

  // Get connection status
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  // Join user-specific room for personalized updates
  joinUserRoom(userId: string) {
    this.send('join_room', { room: `user_${userId}` });
  }

  // Leave user room
  leaveUserRoom(userId: string) {
    this.send('leave_room', { room: `user_${userId}` });
  }

  // Request real-time dashboard updates
  subscribeToStats() {
    this.send('subscribe', { type: 'dashboard_stats' });
  }

  // Unsubscribe from dashboard updates
  unsubscribeFromStats() {
    this.send('unsubscribe', { type: 'dashboard_stats' });
  }

  // Subscribe to infringement updates for specific filters
  subscribeToInfringements(filters?: any) {
    this.send('subscribe', { 
      type: 'infringements',
      filters 
    });
  }

  unsubscribeFromInfringements() {
    this.send('unsubscribe', { type: 'infringements' });
  }
}

// Create and export singleton instance
export const wsService = new WebSocketService();
export default WebSocketService;