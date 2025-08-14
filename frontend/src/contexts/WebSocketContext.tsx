import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { WebSocketService, getWebSocketService, WebSocketState, MessageType, WebSocketMessage, SubscriptionConfig, ConnectionHealth } from '../services/websocket';
import { useAuth } from './AuthContext';

// Context state interface
interface WebSocketContextState {
  // Connection state
  state: WebSocketState;
  isConnected: boolean;
  health: ConnectionHealth;
  error: string | null;
  
  // Message handling
  lastMessage: WebSocketMessage | null;
  
  // Subscription management
  subscribe: (subscriptionId: string, config: SubscriptionConfig, handler: (message: WebSocketMessage) => void) => void;
  unsubscribe: (subscriptionId: string) => void;
  
  // Connection control
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  
  // Message sending
  sendMessage: (message: Omit<WebSocketMessage, 'timestamp'>) => boolean;
  
  // Real-time data access
  dashboardStats: any;
  submissionUpdates: Map<string, any>;
  profileActivities: any[];
  aiDetectionResults: any[];
  socialMediaIncidents: any[];
  templateUpdates: Map<string, any>;
  delistingUpdates: Map<string, any>;
  notifications: any[];
}

// Context
const WebSocketContext = createContext<WebSocketContextState | null>(null);

// Provider props
interface WebSocketProviderProps {
  children: React.ReactNode;
  autoConnect?: boolean;
  reconnectOnError?: boolean;
  maxReconnectAttempts?: number;
  debug?: boolean;
}

// Provider component
export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  autoConnect = true,
  reconnectOnError = true,
  maxReconnectAttempts = 10,
  debug = false,
}) => {
  const { user, token } = useAuth();
  const wsServiceRef = useRef<WebSocketService | null>(null);
  
  // Connection state
  const [state, setState] = useState<WebSocketState>(WebSocketState.DISCONNECTED);
  const [health, setHealth] = useState<ConnectionHealth>({
    state: WebSocketState.DISCONNECTED,
    reconnectAttempts: 0,
    messagesReceived: 0,
    messagesSent: 0,
  });
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  // Subscription handlers
  const subscriptionHandlersRef = useRef<Map<string, (message: WebSocketMessage) => void>>(new Map());
  
  // Real-time data state
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [submissionUpdates, setSubmissionUpdates] = useState<Map<string, any>>(new Map());
  const [profileActivities, setProfileActivities] = useState<any[]>([]);
  const [aiDetectionResults, setAiDetectionResults] = useState<any[]>([]);
  const [socialMediaIncidents, setSocialMediaIncidents] = useState<any[]>([]);
  const [templateUpdates, setTemplateUpdates] = useState<Map<string, any>>(new Map());
  const [delistingUpdates, setDelistingUpdates] = useState<Map<string, any>>(new Map());
  const [notifications, setNotifications] = useState<any[]>([]);
  
  // Initialize WebSocket service
  useEffect(() => {
    wsServiceRef.current = getWebSocketService({
      authToken: token,
      maxReconnectAttempts,
      debug,
    });
    
    const ws = wsServiceRef.current;
    
    // Setup event listeners
    const handleStateChange = ({ to }: { from: WebSocketState; to: WebSocketState }) => {
      setState(to);
      setHealth(ws.getHealth());
      
      if (to === WebSocketState.CONNECTED) {
        setError(null);
      }
    };
    
    const handleError = (error: Error) => {
      setError(error.message);
      setHealth(ws.getHealth());
    };
    
    const handleMessage = (message: WebSocketMessage) => {
      setLastMessage(message);
      setHealth(ws.getHealth());
      
      // Route message to specific handlers
      handleRealtimeMessage(message);
      
      // Call subscription handlers
      const handler = subscriptionHandlersRef.current.get(message.type);
      if (handler) {
        handler(message);
      }
    };
    
    const handleConnected = () => {
      setHealth(ws.getHealth());
      setError(null);
    };
    
    const handleDisconnected = () => {
      setHealth(ws.getHealth());
    };
    
    const handleReconnecting = ({ attempt, delay }: { attempt: number; delay: number }) => {
      setHealth(ws.getHealth());
      console.log(`WebSocket reconnecting (attempt ${attempt}) in ${delay}ms`);
    };
    
    const handleMaxReconnectAttempts = () => {
      setError('Maximum reconnection attempts reached');
      if (reconnectOnError) {
        // Try to reconnect after a longer delay
        setTimeout(() => {
          ws.connect();
        }, 30000);
      }
    };
    
    // Attach listeners
    ws.on('stateChanged', handleStateChange);
    ws.on('error', handleError);
    ws.on('message', handleMessage);
    ws.on('connected', handleConnected);
    ws.on('disconnected', handleDisconnected);
    ws.on('reconnecting', handleReconnecting);
    ws.on('maxReconnectAttemptsReached', handleMaxReconnectAttempts);
    
    // Auto-connect if enabled and user is authenticated
    if (autoConnect && user && token) {
      ws.connect();
    }
    
    // Cleanup on unmount
    return () => {
      ws.removeAllListeners();
      ws.disconnect();
    };
  }, [user, token, autoConnect, reconnectOnError, maxReconnectAttempts, debug]);
  
  // Update auth token when it changes
  useEffect(() => {
    if (wsServiceRef.current && token) {
      wsServiceRef.current.updateAuthToken(token);
    }
  }, [token]);
  
  // Handle real-time messages and update state
  const handleRealtimeMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case MessageType.DASHBOARD_STATS_UPDATE:
        setDashboardStats(message.payload);
        break;
        
      case MessageType.SUBMISSION_PROGRESS:
      case MessageType.SUBMISSION_STATUS_CHANGE:
        setSubmissionUpdates(prev => {
          const newMap = new Map(prev);
          newMap.set(message.payload.id, message.payload);
          return newMap;
        });
        break;
        
      case MessageType.PROFILE_ACTIVITY:
      case MessageType.PROFILE_SCAN_UPDATE:
        setProfileActivities(prev => {
          const activities = [...prev];
          activities.unshift(message.payload);
          return activities.slice(0, 100); // Keep last 100 activities
        });
        break;
        
      case MessageType.AI_DETECTION_RESULT:
      case MessageType.AI_MODEL_TRAINING_UPDATE:
      case MessageType.AI_BATCH_JOB_STATUS:
        setAiDetectionResults(prev => {
          const results = [...prev];
          results.unshift(message.payload);
          return results.slice(0, 50); // Keep last 50 results
        });
        break;
        
      case MessageType.SOCIAL_MEDIA_INCIDENT:
      case MessageType.SOCIAL_MEDIA_SCAN_STATUS:
      case MessageType.SOCIAL_MEDIA_PLATFORM_STATUS:
        setSocialMediaIncidents(prev => {
          const incidents = [...prev];
          incidents.unshift(message.payload);
          return incidents.slice(0, 50); // Keep last 50 incidents
        });
        break;
        
      case MessageType.TEMPLATE_VALIDATION:
      case MessageType.TEMPLATE_APPROVAL:
      case MessageType.TEMPLATE_USAGE:
        setTemplateUpdates(prev => {
          const newMap = new Map(prev);
          newMap.set(message.payload.templateId || message.payload.id, message.payload);
          return newMap;
        });
        break;
        
      case MessageType.DELISTING_REQUEST_STATUS:
      case MessageType.VISIBILITY_CHANGE:
      case MessageType.ENGINE_RESPONSE:
        setDelistingUpdates(prev => {
          const newMap = new Map(prev);
          newMap.set(message.payload.requestId || message.payload.id, message.payload);
          return newMap;
        });
        break;
        
      case MessageType.SYSTEM_NOTIFICATION:
      case MessageType.USER_NOTIFICATION:
        setNotifications(prev => {
          const newNotifications = [...prev];
          newNotifications.unshift(message.payload);
          return newNotifications.slice(0, 100); // Keep last 100 notifications
        });
        break;
    }
  }, []);
  
  // Connection control methods
  const connect = useCallback(() => {
    wsServiceRef.current?.connect();
  }, []);
  
  const disconnect = useCallback(() => {
    wsServiceRef.current?.disconnect();
  }, []);
  
  const reconnect = useCallback(() => {
    wsServiceRef.current?.disconnect();
    setTimeout(() => {
      wsServiceRef.current?.connect();
    }, 1000);
  }, []);
  
  // Subscription management
  const subscribe = useCallback((
    subscriptionId: string,
    config: SubscriptionConfig,
    handler: (message: WebSocketMessage) => void
  ) => {
    // Store handler for message routing
    config.types.forEach(type => {
      subscriptionHandlersRef.current.set(type, handler);
    });
    
    // Subscribe through WebSocket service
    wsServiceRef.current?.subscribe(subscriptionId, config);
  }, []);
  
  const unsubscribe = useCallback((subscriptionId: string) => {
    // Remove handlers (this is simplified - in a real implementation you'd track which handlers belong to which subscription)
    subscriptionHandlersRef.current.clear();
    
    // Unsubscribe through WebSocket service
    wsServiceRef.current?.unsubscribe(subscriptionId);
  }, []);
  
  // Message sending
  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'timestamp'>): boolean => {
    return wsServiceRef.current?.send(message) || false;
  }, []);
  
  // Context value
  const contextValue: WebSocketContextState = {
    // Connection state
    state,
    isConnected: state === WebSocketState.CONNECTED,
    health,
    error,
    
    // Message handling
    lastMessage,
    
    // Subscription management
    subscribe,
    unsubscribe,
    
    // Connection control
    connect,
    disconnect,
    reconnect,
    
    // Message sending
    sendMessage,
    
    // Real-time data
    dashboardStats,
    submissionUpdates,
    profileActivities,
    aiDetectionResults,
    socialMediaIncidents,
    templateUpdates,
    delistingUpdates,
    notifications,
  };
  
  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Hook to use WebSocket context
export const useWebSocket = (): WebSocketContextState => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// Hook for dashboard real-time updates
export const useDashboardRealtime = () => {
  const { dashboardStats, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'dashboard-realtime';
    
    subscribe(subscriptionId, {
      types: [MessageType.DASHBOARD_STATS_UPDATE],
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe]);
  
  return { dashboardStats };
};

// Hook for submission progress tracking
export const useSubmissionRealtime = (submissionIds?: string[]) => {
  const { submissionUpdates, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'submission-realtime';
    
    subscribe(subscriptionId, {
      types: [MessageType.SUBMISSION_PROGRESS, MessageType.SUBMISSION_STATUS_CHANGE],
      filters: submissionIds ? { submissionIds } : undefined,
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, submissionIds]);
  
  return { 
    submissionUpdates,
    getSubmissionUpdate: (id: string) => submissionUpdates.get(id),
  };
};

// Hook for profile activity monitoring
export const useProfileRealtime = (profileIds?: number[]) => {
  const { profileActivities, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'profile-realtime';
    
    subscribe(subscriptionId, {
      types: [MessageType.PROFILE_ACTIVITY, MessageType.PROFILE_SCAN_UPDATE],
      filters: profileIds ? { profileIds } : undefined,
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, profileIds]);
  
  return { profileActivities };
};

// Hook for AI content matching updates
export const useAIContentRealtime = () => {
  const { aiDetectionResults, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'ai-content-realtime';
    
    subscribe(subscriptionId, {
      types: [
        MessageType.AI_DETECTION_RESULT,
        MessageType.AI_MODEL_TRAINING_UPDATE,
        MessageType.AI_BATCH_JOB_STATUS,
      ],
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe]);
  
  return { aiDetectionResults };
};

// Hook for social media protection updates
export const useSocialMediaRealtime = (platforms?: string[]) => {
  const { socialMediaIncidents, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'social-media-realtime';
    
    subscribe(subscriptionId, {
      types: [
        MessageType.SOCIAL_MEDIA_INCIDENT,
        MessageType.SOCIAL_MEDIA_SCAN_STATUS,
        MessageType.SOCIAL_MEDIA_PLATFORM_STATUS,
      ],
      filters: platforms ? { platforms } : undefined,
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, platforms]);
  
  return { socialMediaIncidents };
};

// Hook for DMCA template updates
export const useTemplateRealtime = (templateIds?: string[]) => {
  const { templateUpdates, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'template-realtime';
    
    subscribe(subscriptionId, {
      types: [
        MessageType.TEMPLATE_VALIDATION,
        MessageType.TEMPLATE_APPROVAL,
        MessageType.TEMPLATE_USAGE,
      ],
      filters: templateIds ? { templateIds } : undefined,
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, templateIds]);
  
  return {
    templateUpdates,
    getTemplateUpdate: (id: string) => templateUpdates.get(id),
  };
};

// Hook for search engine delisting updates
export const useDelistingRealtime = (requestIds?: string[]) => {
  const { delistingUpdates, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'delisting-realtime';
    
    subscribe(subscriptionId, {
      types: [
        MessageType.DELISTING_REQUEST_STATUS,
        MessageType.VISIBILITY_CHANGE,
        MessageType.ENGINE_RESPONSE,
      ],
      filters: requestIds ? { requestIds } : undefined,
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, requestIds]);
  
  return {
    delistingUpdates,
    getDelistingUpdate: (id: string) => delistingUpdates.get(id),
  };
};

// Hook for system notifications
export const useNotificationsRealtime = () => {
  const { notifications, subscribe, unsubscribe } = useWebSocket();
  
  useEffect(() => {
    const subscriptionId = 'notifications-realtime';
    
    subscribe(subscriptionId, {
      types: [MessageType.SYSTEM_NOTIFICATION, MessageType.USER_NOTIFICATION],
    }, () => {
      // Handler is managed by context
    });
    
    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe]);
  
  return { notifications };
};

// Hook for connection status monitoring
export const useConnectionStatus = () => {
  const { state, isConnected, health, error, connect, disconnect, reconnect } = useWebSocket();
  
  return {
    state,
    isConnected,
    health,
    error,
    connect,
    disconnect,
    reconnect,
  };
};

export default WebSocketContext;