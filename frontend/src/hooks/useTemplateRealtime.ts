import { useEffect, useRef, useState, useCallback } from 'react';
import { dmcaTemplatesApi } from '../services/api';
import { TemplateRealtimeUpdate, TemplateRealtimeSubscription } from '../types/api';
import { useTemplateRealtime as useWebSocketTemplateRealtime } from '../contexts/WebSocketContext';

interface UseTemplateRealtimeOptions {
  templateIds?: string[];
  categories?: string[];
  updateTypes?: ('validation' | 'compliance' | 'usage' | 'approval')[];
  onUpdate?: (update: TemplateRealtimeUpdate) => void;
  enabled?: boolean;
}

export const useTemplateRealtime = ({
  templateIds,
  categories,
  updateTypes = ['validation', 'compliance', 'usage', 'approval'],
  onUpdate,
  enabled = true
}: UseTemplateRealtimeOptions = {}) => {
  // Use the centralized WebSocket service for template updates
  const { templateUpdates, getTemplateUpdate } = useWebSocketTemplateRealtime(templateIds);
  
  const [lastUpdate, setLastUpdate] = useState<TemplateRealtimeUpdate | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const lastUpdateRef = useRef<TemplateRealtimeUpdate | null>(null);

  // Convert WebSocket template updates to the expected format
  useEffect(() => {
    if (templateUpdates.size > 0) {
      // Get the most recent update
      const updates = Array.from(templateUpdates.values());
      const mostRecentUpdate = updates[updates.length - 1];
      
      if (mostRecentUpdate && mostRecentUpdate !== lastUpdateRef.current) {
        // Convert to expected format
        const update: TemplateRealtimeUpdate = {
          subscription_id: 'template-realtime', // Default subscription ID
          update_type: mostRecentUpdate.type || 'validation',
          template_id: mostRecentUpdate.templateId || mostRecentUpdate.id,
          data: {
            template_name: mostRecentUpdate.name || mostRecentUpdate.title,
            category: mostRecentUpdate.category,
            status: mostRecentUpdate.status,
            changes: mostRecentUpdate.changes,
            user: mostRecentUpdate.user,
            message: mostRecentUpdate.message,
            severity: mostRecentUpdate.severity,
          },
          timestamp: mostRecentUpdate.timestamp || new Date().toISOString(),
        };
        
        setLastUpdate(update);
        lastUpdateRef.current = update;
        
        if (onUpdate && enabled) {
          onUpdate(update);
        }
      }
    }
  }, [templateUpdates, onUpdate, enabled]);

  // Simple connection status based on WebSocket context
  const isConnected = templateUpdates.size >= 0; // We have access to the updates map
  
  return {
    isConnected,
    subscription: null, // Not using individual subscriptions anymore
    lastUpdate,
    connectionError,
    reconnect: () => {}, // Handled by WebSocket context
    disconnect: () => {}, // Handled by WebSocket context
    // Additional methods for accessing specific template updates
    getTemplateUpdate,
    templateUpdates,
  };
};

export default useTemplateRealtime;