import { useEffect, useCallback, useRef } from 'react';
import { useSnackbar } from 'notistack';
import { wsService } from '@services/websocket';
import { useAuth } from './useAuth';

interface UseWebSocketOptions {
  onInfringementDetected?: (data: any) => void;
  onStatusUpdate?: (data: any) => void;
  onTakedownSuccess?: (data: any) => void;
  onSystemAlert?: (data: any) => void;
  onAnalyticsUpdate?: (data: any) => void;
  enableNotifications?: boolean;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { user, isAuthenticated } = useAuth();
  const { enqueueSnackbar } = useSnackbar();
  const listenersRef = useRef<Map<string, (data: any) => void>>(new Map());
  const {
    onInfringementDetected,
    onStatusUpdate,
    onTakedownSuccess,
    onSystemAlert,
    onAnalyticsUpdate,
    enableNotifications = true,
  } = options;

  // Connection status handler
  const handleConnectionStatus = useCallback((data: { connected: boolean; reason?: string }) => {
    if (enableNotifications) {
      if (data.connected) {
        enqueueSnackbar('Connected to real-time updates', { 
          variant: 'success',
          anchorOrigin: { vertical: 'bottom', horizontal: 'right' }
        });
      } else {
        enqueueSnackbar('Disconnected from real-time updates', { 
          variant: 'warning',
          anchorOrigin: { vertical: 'bottom', horizontal: 'right' }
        });
      }
    }
  }, [enqueueSnackbar, enableNotifications]);

  // Infringement detection handler
  const handleInfringementDetected = useCallback((data: any) => {
    if (enableNotifications) {
      enqueueSnackbar(`New infringement detected on ${data.platform}`, {
        variant: 'info',
        anchorOrigin: { vertical: 'top', horizontal: 'right' },
        action: (
          <button 
            onClick={() => window.location.href = '/infringements'}
            style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            View
          </button>
        ),
      });
    }
    onInfringementDetected?.(data);
  }, [enqueueSnackbar, enableNotifications, onInfringementDetected]);

  // Status update handler
  const handleStatusUpdate = useCallback((data: any) => {
    if (enableNotifications && data.status === 'removed') {
      enqueueSnackbar('Content successfully removed!', {
        variant: 'success',
        anchorOrigin: { vertical: 'top', horizontal: 'right' },
      });
    }
    onStatusUpdate?.(data);
  }, [enqueueSnackbar, enableNotifications, onStatusUpdate]);

  // Takedown success handler
  const handleTakedownSuccess = useCallback((data: any) => {
    if (enableNotifications) {
      enqueueSnackbar(`Takedown successful: ${data.url}`, {
        variant: 'success',
        anchorOrigin: { vertical: 'top', horizontal: 'right' },
      });
    }
    onTakedownSuccess?.(data);
  }, [enqueueSnackbar, enableNotifications, onTakedownSuccess]);

  // System alert handler
  const handleSystemAlert = useCallback((data: any) => {
    if (enableNotifications) {
      const variant = data.level === 'error' ? 'error' : 
                    data.level === 'warning' ? 'warning' : 'info';
      
      enqueueSnackbar(data.message, {
        variant,
        anchorOrigin: { vertical: 'top', horizontal: 'center' },
        persist: data.level === 'error',
      });
    }
    onSystemAlert?.(data);
  }, [enqueueSnackbar, enableNotifications, onSystemAlert]);

  // Analytics update handler
  const handleAnalyticsUpdate = useCallback((data: any) => {
    onAnalyticsUpdate?.(data);
  }, [onAnalyticsUpdate]);

  // Setup WebSocket connection and listeners
  useEffect(() => {
    if (!isAuthenticated || !user) return;

    // Connect to WebSocket if not already connected
    if (!wsService.isConnected()) {
      wsService.connect();
      wsService.joinUserRoom(user.id);
    }

    // Set up event listeners
    const listeners = new Map([
      ['connection_status', handleConnectionStatus],
      ['infringement_detected', handleInfringementDetected],
      ['status_update', handleStatusUpdate],
      ['takedown_success', handleTakedownSuccess],
      ['system_alert', handleSystemAlert],
      ['analytics_update', handleAnalyticsUpdate],
    ]);

    // Register all listeners
    listeners.forEach((handler, event) => {
      wsService.on(event, handler);
    });

    // Store listeners for cleanup
    listenersRef.current = listeners;

    // Cleanup function
    return () => {
      listeners.forEach((handler, event) => {
        wsService.off(event, handler);
      });
      listenersRef.current.clear();
    };
  }, [
    isAuthenticated,
    user,
    handleConnectionStatus,
    handleInfringementDetected,
    handleStatusUpdate,
    handleTakedownSuccess,
    handleSystemAlert,
    handleAnalyticsUpdate,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (user) {
        wsService.leaveUserRoom(user.id);
      }
    };
  }, [user]);

  return {
    isConnected: wsService.isConnected(),
    send: wsService.send.bind(wsService),
    subscribeToStats: wsService.subscribeToStats.bind(wsService),
    unsubscribeFromStats: wsService.unsubscribeFromStats.bind(wsService),
    subscribeToInfringements: wsService.subscribeToInfringements.bind(wsService),
    unsubscribeFromInfringements: wsService.unsubscribeFromInfringements.bind(wsService),
  };
};