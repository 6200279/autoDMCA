import { useEffect, useRef, useCallback } from 'react';
import { SocialMediaWebSocketMessage } from '../types/api';
import { useWebSocket as useWebSocketContext } from '../contexts/WebSocketContext';

interface UseWebSocketOptions {
  url?: string; // Optional, for backward compatibility
  onMessage?: (message: SocialMediaWebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

export const useWebSocket = ({
  url, // Ignored - using centralized service
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  autoReconnect = true,
  reconnectDelay = 3000
}: UseWebSocketOptions) => {
  // Use the centralized WebSocket context
  const { isConnected, sendMessage, subscribe, unsubscribe, socialMediaIncidents } = useWebSocketContext();
  
  const subscriptionIdRef = useRef<string>('social-media-legacy-hook');

  // Handle connection state changes
  useEffect(() => {
    if (isConnected && onConnect) {
      onConnect();
    } else if (!isConnected && onDisconnect) {
      onDisconnect();
    }
  }, [isConnected, onConnect, onDisconnect]);

  // Subscribe to social media messages
  useEffect(() => {
    const subscriptionId = subscriptionIdRef.current;
    
    subscribe(subscriptionId, {
      types: [
        'social_media_incident' as any,
        'social_media_scan_status' as any,
        'social_media_platform_status' as any,
      ],
    }, (message) => {
      // Convert to the expected format for backward compatibility
      const socialMediaMessage: SocialMediaWebSocketMessage = {
        type: message.type as any,
        payload: message.payload,
        timestamp: message.timestamp,
      };
      
      if (onMessage) {
        onMessage(socialMediaMessage);
      }
    });

    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, onMessage]);

  // Legacy connect/disconnect methods (no-op since handled by context)
  const connect = useCallback(() => {
    console.log('WebSocket connect called (handled by context)');
  }, []);

  const disconnect = useCallback(() => {
    console.log('WebSocket disconnect called (handled by context)');
  }, []);

  // Convert sendMessage to match expected signature
  const legacySendMessage = useCallback((message: any) => {
    return sendMessage({
      type: message.type || 'social_media_incident',
      payload: message,
    });
  }, [sendMessage]);

  return {
    isConnected,
    connect,
    disconnect,
    sendMessage: legacySendMessage
  };
};