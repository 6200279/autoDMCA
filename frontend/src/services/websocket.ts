// Browser-compatible event emitter implementation
class SimpleEventEmitter {
  private listeners: { [key: string]: Function[] } = {};

  on(event: string, listener: Function) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(listener);
  }

  off(event: string, listener: Function) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(l => l !== listener);
  }

  emit(event: string, ...args: any[]) {
    if (!this.listeners[event]) return;
    this.listeners[event].forEach(listener => listener(...args));
  }

  removeAllListeners(event?: string) {
    if (event) {
      delete this.listeners[event];
    } else {
      this.listeners = {};
    }
  }

  setMaxListeners(n: number) {
    // Browser implementation - just a no-op for compatibility
    // In browser environment we don't have the same memory pressure concerns as Node.js
    return this;
  }
}

// WebSocket connection states
export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

// Message types for real-time updates
export enum MessageType {
  // Dashboard updates
  DASHBOARD_STATS_UPDATE = 'dashboard_stats_update',
  
  // Submission updates
  SUBMISSION_PROGRESS = 'submission_progress',
  SUBMISSION_STATUS_CHANGE = 'submission_status_change',
  
  // Profile updates
  PROFILE_ACTIVITY = 'profile_activity',
  PROFILE_SCAN_UPDATE = 'profile_scan_update',
  
  // AI Content Matching updates
  AI_DETECTION_RESULT = 'ai_detection_result',
  AI_MODEL_TRAINING_UPDATE = 'ai_model_training_update',
  AI_BATCH_JOB_STATUS = 'ai_batch_job_status',
  
  // Social Media Protection updates
  SOCIAL_MEDIA_INCIDENT = 'social_media_incident',
  SOCIAL_MEDIA_SCAN_STATUS = 'social_media_scan_status',
  SOCIAL_MEDIA_PLATFORM_STATUS = 'social_media_platform_status',
  
  // DMCA Template updates
  TEMPLATE_VALIDATION = 'template_validation',
  TEMPLATE_APPROVAL = 'template_approval',
  TEMPLATE_USAGE = 'template_usage',
  
  // Search Engine Delisting updates
  DELISTING_REQUEST_STATUS = 'delisting_request_status',
  VISIBILITY_CHANGE = 'visibility_change',
  ENGINE_RESPONSE = 'engine_response',
  
  // System notifications
  SYSTEM_NOTIFICATION = 'system_notification',
  USER_NOTIFICATION = 'user_notification',
  
  // Connection management
  CONNECTION_ESTABLISHED = 'connection_established',
  CONNECTION_LOST = 'connection_lost',
  HEARTBEAT = 'heartbeat',
  ERROR = 'error',
}

// WebSocket message structure
export interface WebSocketMessage {
  type: MessageType;
  payload: any;
  timestamp: string;
  id?: string;
  userId?: number;
  metadata?: Record<string, any>;
}

// Connection configuration
export interface WebSocketConfig {
  url: string;
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  authToken?: string;
  protocols?: string[];
  debug?: boolean;
}

// Subscription configuration
export interface SubscriptionConfig {
  types: MessageType[];
  filters?: {
    userId?: number;
    profileIds?: number[];
    platforms?: string[];
    [key: string]: any;
  };
}

// Connection health metrics
export interface ConnectionHealth {
  state: WebSocketState;
  connectedAt?: Date;
  lastMessageAt?: Date;
  reconnectAttempts: number;
  messagesReceived: number;
  messagesSent: number;
  latency?: number;
}

// Default configuration
const DEFAULT_CONFIG: WebSocketConfig = {
  url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  debug: import.meta.env.DEV,
};

export class WebSocketService extends SimpleEventEmitter {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectTimeoutId: NodeJS.Timeout | null = null;
  private heartbeatIntervalId: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private subscriptions = new Map<string, SubscriptionConfig>();
  private messageQueue: WebSocketMessage[] = [];
  private health: ConnectionHealth;
  private isManualDisconnect = false;

  constructor(config: Partial<WebSocketConfig> = {}) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.health = {
      state: WebSocketState.DISCONNECTED,
      reconnectAttempts: 0,
      messagesReceived: 0,
      messagesSent: 0,
    };
    
    this.setMaxListeners(100); // Allow many subscribers
  }

  /**
   * Connect to WebSocket server
   */
  public connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.debug('Already connected to WebSocket');
      return;
    }

    this.isManualDisconnect = false;
    this.setState(WebSocketState.CONNECTING);
    
    try {
      const wsUrl = this.buildWebSocketUrl();
      this.ws = new WebSocket(wsUrl, this.config.protocols);
      
      this.setupEventHandlers();
      this.debug(`Connecting to WebSocket: ${wsUrl}`);
    } catch (error) {
      this.handleError('Connection failed', error);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    this.isManualDisconnect = true;
    this.clearTimeouts();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.setState(WebSocketState.DISCONNECTED);
    this.debug('Manually disconnected from WebSocket');
  }

  /**
   * Send message to server
   */
  public send(message: Omit<WebSocketMessage, 'timestamp'>): boolean {
    const fullMessage: WebSocketMessage = {
      ...message,
      timestamp: new Date().toISOString(),
      id: this.generateMessageId(),
    };

    if (!this.isConnected()) {
      this.debug('WebSocket not connected, queuing message');
      this.messageQueue.push(fullMessage);
      return false;
    }

    try {
      this.ws!.send(JSON.stringify(fullMessage));
      this.health.messagesSent++;
      this.debug('Message sent:', fullMessage.type);
      return true;
    } catch (error) {
      this.handleError('Failed to send message', error);
      return false;
    }
  }

  /**
   * Subscribe to specific message types
   */
  public subscribe(subscriptionId: string, config: SubscriptionConfig): void {
    this.subscriptions.set(subscriptionId, config);
    
    // Send subscription request to server if connected
    if (this.isConnected()) {
      this.send({
        type: MessageType.CONNECTION_ESTABLISHED,
        payload: {
          action: 'subscribe',
          subscriptionId,
          config,
        },
      });
    }
    
    this.debug(`Subscribed to ${config.types.join(', ')} with ID: ${subscriptionId}`);
  }

  /**
   * Unsubscribe from message types
   */
  public unsubscribe(subscriptionId: string): void {
    if (this.subscriptions.has(subscriptionId)) {
      this.subscriptions.delete(subscriptionId);
      
      if (this.isConnected()) {
        this.send({
          type: MessageType.CONNECTION_ESTABLISHED,
          payload: {
            action: 'unsubscribe',
            subscriptionId,
          },
        });
      }
      
      this.debug(`Unsubscribed from: ${subscriptionId}`);
    }
  }

  /**
   * Get connection state
   */
  public getState(): WebSocketState {
    return this.state;
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && this.state === WebSocketState.CONNECTED;
  }

  /**
   * Get connection health metrics
   */
  public getHealth(): ConnectionHealth {
    return {
      ...this.health,
      state: this.state,
    };
  }

  /**
   * Update authentication token
   */
  public updateAuthToken(token: string): void {
    this.config.authToken = token;
    
    if (this.isConnected()) {
      this.send({
        type: MessageType.CONNECTION_ESTABLISHED,
        payload: {
          action: 'auth_update',
          token,
        },
      });
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.setState(WebSocketState.CONNECTED);
      this.health.connectedAt = new Date();
      this.reconnectAttempts = 0;
      
      this.debug('WebSocket connected');
      this.emit('connected');
      
      // Send authentication if token available
      this.authenticate();
      
      // Re-establish subscriptions
      this.reestablishSubscriptions();
      
      // Send queued messages
      this.processMessageQueue();
      
      // Start heartbeat
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      this.health.lastMessageAt = new Date();
      this.health.messagesReceived++;
      
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        this.handleError('Failed to parse message', error);
      }
    };

    this.ws.onclose = (event) => {
      this.clearTimeouts();
      
      if (event.code === 1000 && this.isManualDisconnect) {
        this.setState(WebSocketState.DISCONNECTED);
        this.debug('WebSocket closed normally');
      } else {
        this.setState(WebSocketState.DISCONNECTED);
        this.debug(`WebSocket closed: ${event.code} - ${event.reason}`);
        
        if (!this.isManualDisconnect) {
          this.scheduleReconnect();
        }
      }
      
      this.emit('disconnected', { code: event.code, reason: event.reason });
    };

    this.ws.onerror = (error) => {
      this.handleError('WebSocket error', error);
    };
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(message: WebSocketMessage): void {
    this.debug('Message received:', message.type);
    
    // Handle system messages
    switch (message.type) {
      case MessageType.HEARTBEAT:
        this.handleHeartbeat(message);
        break;
        
      case MessageType.ERROR:
        this.handleServerError(message);
        break;
        
      default:
        // Emit message for subscribers
        this.emit('message', message);
        this.emit(message.type, message.payload);
    }
  }

  /**
   * Handle heartbeat messages
   */
  private handleHeartbeat(message: WebSocketMessage): void {
    if (message.payload?.timestamp) {
      const sent = new Date(message.payload.timestamp);
      const now = new Date();
      this.health.latency = now.getTime() - sent.getTime();
    }
    
    // Send heartbeat response
    this.send({
      type: MessageType.HEARTBEAT,
      payload: {
        timestamp: new Date().toISOString(),
        response: true,
      },
    });
  }

  /**
   * Handle server error messages
   */
  private handleServerError(message: WebSocketMessage): void {
    this.debug('Server error:', message.payload);
    this.emit('error', new Error(message.payload?.message || 'Server error'));
  }

  /**
   * Authenticate with server
   */
  private authenticate(): void {
    if (this.config.authToken) {
      this.send({
        type: MessageType.CONNECTION_ESTABLISHED,
        payload: {
          action: 'authenticate',
          token: this.config.authToken,
        },
      });
    }
  }

  /**
   * Re-establish subscriptions after reconnection
   */
  private reestablishSubscriptions(): void {
    for (const [subscriptionId, config] of this.subscriptions.entries()) {
      this.send({
        type: MessageType.CONNECTION_ESTABLISHED,
        payload: {
          action: 'subscribe',
          subscriptionId,
          config,
        },
      });
    }
  }

  /**
   * Process queued messages
   */
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift()!;
      this.ws!.send(JSON.stringify(message));
      this.health.messagesSent++;
    }
  }

  /**
   * Start heartbeat interval
   */
  private startHeartbeat(): void {
    this.heartbeatIntervalId = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: MessageType.HEARTBEAT,
          payload: {
            timestamp: new Date().toISOString(),
          },
        });
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.setState(WebSocketState.ERROR);
      this.debug('Max reconnect attempts reached');
      this.emit('maxReconnectAttemptsReached');
      return;
    }

    this.setState(WebSocketState.RECONNECTING);
    this.reconnectAttempts++;
    this.health.reconnectAttempts = this.reconnectAttempts;
    
    const delay = this.config.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
    this.debug(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeoutId = setTimeout(() => {
      this.debug(`Reconnect attempt ${this.reconnectAttempts}`);
      this.connect();
    }, delay);
    
    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });
  }

  /**
   * Set connection state
   */
  private setState(state: WebSocketState): void {
    if (this.state !== state) {
      const previousState = this.state;
      this.state = state;
      this.health.state = state;
      this.debug(`State changed: ${previousState} -> ${state}`);
      this.emit('stateChanged', { from: previousState, to: state });
    }
  }

  /**
   * Clear all timeouts
   */
  private clearTimeouts(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    
    if (this.heartbeatIntervalId) {
      clearInterval(this.heartbeatIntervalId);
      this.heartbeatIntervalId = null;
    }
  }

  /**
   * Handle errors
   */
  private handleError(message: string, error?: any): void {
    const errorMessage = `${message}: ${error?.message || error}`;
    this.debug(errorMessage);
    this.emit('error', new Error(errorMessage));
    
    if (this.state !== WebSocketState.ERROR) {
      this.setState(WebSocketState.ERROR);
    }
  }

  /**
   * Build WebSocket URL with authentication
   */
  private buildWebSocketUrl(): string {
    const url = new URL(this.config.url);
    
    if (this.config.authToken) {
      url.searchParams.set('token', this.config.authToken);
    }
    
    return url.toString();
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Debug logging
   */
  private debug(message: string, ...args: any[]): void {
    if (this.config.debug) {
      console.log(`[WebSocket] ${message}`, ...args);
    }
  }
}

// Singleton instance
let webSocketServiceInstance: WebSocketService | null = null;

/**
 * Get singleton WebSocket service instance
 */
export const getWebSocketService = (config?: Partial<WebSocketConfig>): WebSocketService => {
  if (!webSocketServiceInstance) {
    webSocketServiceInstance = new WebSocketService(config);
  }
  return webSocketServiceInstance;
};

/**
 * Reset WebSocket service (for testing)
 */
export const resetWebSocketService = (): void => {
  if (webSocketServiceInstance) {
    webSocketServiceInstance.disconnect();
    webSocketServiceInstance = null;
  }
};

export default WebSocketService;