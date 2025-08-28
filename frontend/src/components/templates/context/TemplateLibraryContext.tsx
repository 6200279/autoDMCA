import React, { createContext, useContext, useCallback, useMemo } from 'react';
import { useTemplateLibrary } from '../hooks/useTemplateLibrary';
import { templatesApi } from '../../../services/api';
import { 
  DMCATemplate, 
  TemplateCategory 
} from '../../../types/templates';
import { 
  EnhancedDMCATemplate,
  TemplateViewPreferences,
  TemplateAction,
  BulkAction,
  FilterPreset,
  TemplateLibraryEvent
} from '../types/enhanced';
import { enhanceTemplates } from '../utils/templateUtils';

interface TemplateLibraryContextValue {
  // State from useTemplateLibrary hook
  templates: EnhancedDMCATemplate[];
  categories: TemplateCategory[];
  loading: boolean;
  error: string | null;
  totalRecords: number;
  filters: ReturnType<typeof useTemplateLibrary>['filters'];
  pagination: ReturnType<typeof useTemplateLibrary>['pagination'];
  sorting: ReturnType<typeof useTemplateLibrary>['sorting'];
  
  // Enhanced state
  viewPreferences: TemplateViewPreferences;
  filterPresets: FilterPreset[];
  recentlyViewed: string[];
  
  // Additional properties
  availableTags: string[];
  searchSuggestions: string[];
  selection: ReturnType<typeof useTemplateLibrary>['selection'];
  
  // Computed values
  hasActiveFilters: boolean;
  isAllSelected: boolean;
  hasSelection: boolean;
  selectedTemplates: EnhancedDMCATemplate[];
  
  // Actions from hook
  actions: ReturnType<typeof useTemplateLibrary>['actions'];
  
  // Enhanced actions
  enhancedActions: {
    // View preferences
    setViewPreferences: (preferences: Partial<TemplateViewPreferences>) => void;
    
    // Template actions
    performTemplateAction: (action: TemplateAction, template: DMCATemplate) => Promise<void>;
    performBulkAction: (action: BulkAction, templateIds: string[]) => Promise<void>;
    
    // Recently viewed
    markAsViewed: (templateId: string) => void;
    clearRecentlyViewed: () => void;
    
    // Filter presets
    saveFilterPreset: (preset: Omit<FilterPreset, 'id' | 'createdAt'>) => void;
    deleteFilterPreset: (presetId: string) => void;
    applyFilterPreset: (presetId: string) => void;
    
    // Analytics and events
    trackEvent: (event: TemplateLibraryEvent) => void;
    
    // Cache management
    invalidateCache: () => void;
    refreshData: () => Promise<void>;
  };
  
  // Configuration
  config: {
    enableVirtualScrolling: boolean;
    enableAnalytics: boolean;
    defaultViewPreferences: TemplateViewPreferences;
    availableActions: TemplateAction[];
    availableBulkActions: BulkAction[];
  };
}

const TemplateLibraryContext = createContext<TemplateLibraryContextValue | undefined>(undefined);

interface TemplateLibraryProviderProps {
  children: React.ReactNode;
  enableVirtualScrolling?: boolean;
  enableAnalytics?: boolean;
  customActions?: TemplateAction[];
  customBulkActions?: BulkAction[];
  onTemplateEvent?: (event: TemplateLibraryEvent) => void;
}

const defaultViewPreferences: TemplateViewPreferences = {
  layout: {
    type: 'grid',
    size: 'medium',
    gap: 16
  },
  showThumbnails: true,
  showPreview: false,
  showMetadata: true,
  showUsageStats: false,
  hideInactive: false,
  groupByCategory: false
};

const defaultActions: TemplateAction[] = [
  {
    id: 'view',
    label: 'View',
    icon: 'pi pi-eye',
    handler: (template) => {
      // Default view handler - can be overridden
      console.log('View template:', template.id);
    }
  },
  {
    id: 'edit',
    label: 'Edit',
    icon: 'pi pi-pencil',
    handler: (template) => {
      console.log('Edit template:', template.id);
    }
  },
  {
    id: 'duplicate',
    label: 'Duplicate',
    icon: 'pi pi-copy',
    handler: async (template) => {
      await templatesApi.duplicateTemplate(template.id, `${template.name} (Copy)`);
    }
  },
  {
    id: 'delete',
    label: 'Delete',
    icon: 'pi pi-trash',
    severity: 'danger',
    handler: async (template) => {
      await templatesApi.deleteTemplate(template.id);
    }
  }
];

const defaultBulkActions: BulkAction[] = [
  {
    id: 'activate',
    label: 'Activate Selected',
    icon: 'pi pi-check',
    handler: async (templateIds) => {
      await templatesApi.bulkActivate(templateIds);
    }
  },
  {
    id: 'deactivate',
    label: 'Deactivate Selected',
    icon: 'pi pi-times',
    handler: async (templateIds) => {
      await templatesApi.bulkDeactivate(templateIds);
    }
  },
  {
    id: 'delete',
    label: 'Delete Selected',
    icon: 'pi pi-trash',
    severity: 'danger',
    confirmMessage: 'Are you sure you want to delete the selected templates?',
    handler: async (templateIds) => {
      await templatesApi.bulkDelete(templateIds);
    }
  },
  {
    id: 'export',
    label: 'Export Selected',
    icon: 'pi pi-download',
    handler: async (templateIds) => {
      await templatesApi.exportTemplates(templateIds, 'json');
    }
  }
];

export const TemplateLibraryProvider: React.FC<TemplateLibraryProviderProps> = ({
  children,
  enableVirtualScrolling = false,
  enableAnalytics = true,
  customActions = [],
  customBulkActions = [],
  onTemplateEvent
}) => {
  // Use the template library hook
  const libraryState = useTemplateLibrary({
    autoFetch: true
  });

  // Additional state
  const [viewPreferences, setViewPreferences] = React.useState<TemplateViewPreferences>(
    () => {
      const saved = localStorage.getItem('template-view-preferences');
      return saved ? { ...defaultViewPreferences, ...JSON.parse(saved) } : defaultViewPreferences;
    }
  );

  const [filterPresets, setFilterPresets] = React.useState<FilterPreset[]>(
    () => {
      const saved = localStorage.getItem('template-filter-presets');
      return saved ? JSON.parse(saved) : [];
    }
  );

  const [recentlyViewed, setRecentlyViewed] = React.useState<string[]>(
    () => {
      const saved = localStorage.getItem('template-recently-viewed');
      return saved ? JSON.parse(saved) : [];
    }
  );

  // Save preferences to localStorage
  React.useEffect(() => {
    localStorage.setItem('template-view-preferences', JSON.stringify(viewPreferences));
  }, [viewPreferences]);

  React.useEffect(() => {
    localStorage.setItem('template-filter-presets', JSON.stringify(filterPresets));
  }, [filterPresets]);

  React.useEffect(() => {
    localStorage.setItem('template-recently-viewed', JSON.stringify(recentlyViewed));
  }, [recentlyViewed]);

  // Enhance templates with additional metadata
  const enhancedTemplates = useMemo(() => {
    return enhanceTemplates(libraryState.templates, {
      favorites: libraryState.selection.favorites,
      recentlyViewed,
      usageStats: {} // Could be populated from analytics
    });
  }, [libraryState.templates, libraryState.selection.favorites, recentlyViewed]);

  // Get selected templates
  const selectedTemplates = useMemo(() => {
    return enhancedTemplates.filter(t => libraryState.selection.selectedTemplates.includes(t.id));
  }, [enhancedTemplates, libraryState.selection.selectedTemplates]);

  // Enhanced actions
  const enhancedActions = useMemo(() => ({
    setViewPreferences: (preferences: Partial<TemplateViewPreferences>) => {
      setViewPreferences(prev => ({ ...prev, ...preferences }));
    },

    performTemplateAction: async (action: TemplateAction, template: DMCATemplate) => {
      try {
        await action.handler(template);
        
        // Refresh data if needed
        if (['delete', 'activate', 'deactivate'].includes(action.id)) {
          libraryState.fetchTemplates();
        }
        
        // Track event
        if (enableAnalytics) {
          const event: TemplateLibraryEvent = {
            type: 'bulk_action',
            payload: { actionId: action.id, templateId: template.id },
            timestamp: new Date().toISOString()
          };
          onTemplateEvent?.(event);
        }
      } catch (error) {
        console.error(`Failed to perform action ${action.id}:`, error);
        throw error;
      }
    },

    performBulkAction: async (action: BulkAction, templateIds: string[]) => {
      try {
        await action.handler(templateIds, selectedTemplates);
        
        // Clear selection after successful bulk action
        libraryState.actions.setSelectedTemplates([]);
        
        // Refresh data
        libraryState.fetchTemplates();
        
        // Track event
        if (enableAnalytics) {
          const event: TemplateLibraryEvent = {
            type: 'bulk_action',
            payload: { actionId: action.id, templateIds, count: templateIds.length },
            timestamp: new Date().toISOString()
          };
          onTemplateEvent?.(event);
        }
      } catch (error) {
        console.error(`Failed to perform bulk action ${action.id}:`, error);
        throw error;
      }
    },

    markAsViewed: (templateId: string) => {
      setRecentlyViewed(prev => {
        const filtered = prev.filter(id => id !== templateId);
        return [templateId, ...filtered].slice(0, 50); // Keep last 50
      });
    },

    clearRecentlyViewed: () => {
      setRecentlyViewed([]);
    },

    saveFilterPreset: (preset: Omit<FilterPreset, 'id' | 'createdAt'>) => {
      const newPreset: FilterPreset = {
        ...preset,
        id: `preset-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        createdAt: new Date().toISOString(),
        usage_count: 0
      };
      setFilterPresets(prev => [...prev, newPreset]);
    },

    deleteFilterPreset: (presetId: string) => {
      setFilterPresets(prev => prev.filter(p => p.id !== presetId));
    },

    applyFilterPreset: (presetId: string) => {
      const preset = filterPresets.find(p => p.id === presetId);
      if (preset) {
        libraryState.actions.setFilters(preset.filters);
        
        // Update usage count
        setFilterPresets(prev => prev.map(p => 
          p.id === presetId 
            ? { ...p, usage_count: (p.usage_count || 0) + 1 }
            : p
        ));
      }
    },

    trackEvent: (event: TemplateLibraryEvent) => {
      if (enableAnalytics) {
        onTemplateEvent?.(event);
      }
    },

    invalidateCache: () => {
      // Clear any cached data
      localStorage.removeItem('template-search-history');
    },

    refreshData: async () => {
      await Promise.all([
        libraryState.fetchTemplates(),
        libraryState.fetchCategories()
      ]);
    }
  }), [
    libraryState,
    selectedTemplates,
    filterPresets,
    enableAnalytics,
    onTemplateEvent
  ]);

  // Configuration
  const config = useMemo(() => ({
    enableVirtualScrolling,
    enableAnalytics,
    defaultViewPreferences,
    availableActions: [...defaultActions, ...customActions],
    availableBulkActions: [...defaultBulkActions, ...customBulkActions]
  }), [enableVirtualScrolling, enableAnalytics, customActions, customBulkActions]);

  const contextValue: TemplateLibraryContextValue = {
    // State from hook
    templates: enhancedTemplates,
    categories: libraryState.categories,
    loading: libraryState.loading,
    error: libraryState.error,
    totalRecords: libraryState.totalRecords,
    filters: libraryState.filters,
    pagination: libraryState.pagination,
    sorting: libraryState.sorting,
    
    // Enhanced state
    viewPreferences,
    filterPresets,
    recentlyViewed,
    
    // Additional properties needed by components
    availableTags: libraryState.availableTags,
    searchSuggestions: libraryState.searchSuggestions,
    selection: libraryState.selection,
    
    // Computed values
    hasActiveFilters: libraryState.hasActiveFilters,
    isAllSelected: libraryState.isAllSelected,
    hasSelection: libraryState.hasSelection,
    selectedTemplates,
    
    // Actions
    actions: libraryState.actions,
    enhancedActions,
    
    // Configuration
    config
  };

  return (
    <TemplateLibraryContext.Provider value={contextValue}>
      {children}
    </TemplateLibraryContext.Provider>
  );
};

export const useTemplateLibraryContext = () => {
  const context = useContext(TemplateLibraryContext);
  if (context === undefined) {
    throw new Error('useTemplateLibraryContext must be used within a TemplateLibraryProvider');
  }
  return context;
};

export { TemplateLibraryContext };