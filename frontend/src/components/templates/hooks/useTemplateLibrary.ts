import { useState, useEffect, useCallback, useRef } from 'react';
import { templatesApi } from '../../../services/api';
import { 
  DMCATemplate, 
  TemplateCategory, 
  TemplateListParams,
  PaginatedTemplatesResponse
} from '../../../types/templates';
import { useDebounce } from './useDebounce';

export interface FilterState {
  search: string;
  category: string;
  language: string;
  jurisdiction: string;
  status: 'all' | 'active' | 'inactive' | 'favorites';
  tags: string[];
}

export interface TemplateLibraryState {
  templates: DMCATemplate[];
  categories: TemplateCategory[];
  loading: boolean;
  error: string | null;
  totalRecords: number;
  filters: FilterState;
  pagination: {
    first: number;
    rows: number;
  };
  sorting: {
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  };
  selection: {
    selectedTemplates: string[];
    favorites: string[];
  };
  searchSuggestions: string[];
  availableTags: string[];
}

interface UseTemplateLibraryOptions {
  initialFilters?: Partial<FilterState>;
  initialPagination?: { first?: number; rows?: number };
  initialSorting?: { sortBy?: string; sortOrder?: 'asc' | 'desc' };
  autoFetch?: boolean;
}

export const useTemplateLibrary = (options: UseTemplateLibraryOptions = {}) => {
  const {
    initialFilters = {},
    initialPagination = {},
    initialSorting = {},
    autoFetch = true
  } = options;

  // State
  const [state, setState] = useState<TemplateLibraryState>({
    templates: [],
    categories: [],
    loading: false,
    error: null,
    totalRecords: 0,
    filters: {
      search: '',
      category: '',
      language: '',
      jurisdiction: '',
      status: 'all',
      tags: [],
      ...initialFilters
    },
    pagination: {
      first: 0,
      rows: 20,
      ...initialPagination
    },
    sorting: {
      sortBy: 'updated_at',
      sortOrder: 'desc',
      ...initialSorting
    },
    selection: {
      selectedTemplates: [],
      favorites: []
    },
    searchSuggestions: [],
    availableTags: []
  });

  // Debounced search term
  const debouncedSearchTerm = useDebounce(state.filters.search, 300);
  
  // Refs for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Load favorites from localStorage
  useEffect(() => {
    const savedFavorites = localStorage.getItem('template-favorites');
    if (savedFavorites) {
      setState(prev => ({
        ...prev,
        selection: { ...prev.selection, favorites: JSON.parse(savedFavorites) }
      }));
    }
  }, []);

  // Save favorites to localStorage
  useEffect(() => {
    localStorage.setItem('template-favorites', JSON.stringify(state.selection.favorites));
  }, [state.selection.favorites]);

  // Update state helper
  const updateState = useCallback((updater: (prev: TemplateLibraryState) => TemplateLibraryState) => {
    setState(updater);
  }, []);

  // Fetch templates with current filters and pagination
  const fetchTemplates = useCallback(async (cancelPrevious = true) => {
    if (cancelPrevious && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    updateState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const params: TemplateListParams = {
        page: Math.floor(state.pagination.first / state.pagination.rows) + 1,
        limit: state.pagination.rows,
        search: debouncedSearchTerm || undefined,
        category: state.filters.category || undefined,
        language: state.filters.language || undefined,
        jurisdiction: state.filters.jurisdiction || undefined,
        is_active: state.filters.status === 'active' ? true : 
                   state.filters.status === 'inactive' ? false : undefined,
        sort_by: state.sorting.sortBy as any,
        sort_order: state.sorting.sortOrder,
        tags: state.filters.tags.length > 0 ? state.filters.tags : undefined,
      };

      const response = await templatesApi.getTemplates(params);
      const data: PaginatedTemplatesResponse = response.data;
      
      if (!isMountedRef.current) return;

      let filteredTemplates = data.templates;
      
      // Apply favorite filter client-side
      if (state.filters.status === 'favorites') {
        filteredTemplates = data.templates.filter(t => state.selection.favorites.includes(t.id));
      }
      
      updateState(prev => ({
        ...prev,
        templates: filteredTemplates,
        totalRecords: state.filters.status === 'favorites' ? filteredTemplates.length : data.total,
        loading: false
      }));

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return; // Request was cancelled
      }
      
      if (!isMountedRef.current) return;
      
      updateState(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to load templates'
      }));
    }
  }, [state.pagination, state.filters, state.sorting, state.selection.favorites, debouncedSearchTerm, updateState]);

  // Fetch categories and extract available tags
  const fetchCategories = useCallback(async () => {
    try {
      const [categoriesResponse, allTemplatesResponse] = await Promise.all([
        templatesApi.getCategories(),
        templatesApi.getTemplates({ limit: 1000 }) // Get all templates for tag extraction
      ]);
      
      if (!isMountedRef.current) return;

      const categories = categoriesResponse.data;
      const allTags = new Set<string>();
      
      allTemplatesResponse.data.templates.forEach(template => {
        template.tags?.forEach(tag => allTags.add(tag));
      });
      
      updateState(prev => ({
        ...prev,
        categories,
        availableTags: Array.from(allTags).sort()
      }));
      
    } catch (error) {
      console.error('Error fetching categories:', error);
      // Fallback to default categories if API fails
      const defaultCategories = [
        'General DMCA', 'Social Media', 'Search Engines', 'Hosting Providers',
        'E-commerce', 'Video Platforms', 'Image Hosting', 'File Sharing'
      ].map((cat, index) => ({
        id: cat.toLowerCase().replace(/\s+/g, '-'),
        name: cat,
        description: `${cat} templates`,
        template_count: 0
      }));
      
      updateState(prev => ({
        ...prev,
        categories: defaultCategories
      }));
    }
  }, [updateState]);

  // Generate search suggestions
  const generateSearchSuggestions = useCallback((query: string): string[] => {
    if (!query) return [];
    
    const suggestions = new Set<string>();
    const queryLower = query.toLowerCase();
    
    // Add matching template names
    state.templates.forEach(template => {
      if (template.name.toLowerCase().includes(queryLower)) {
        suggestions.add(template.name);
      }
    });
    
    // Add matching categories
    state.categories.forEach(category => {
      if (category.name.toLowerCase().includes(queryLower)) {
        suggestions.add(category.name);
      }
    });
    
    // Add matching tags
    state.availableTags.forEach(tag => {
      if (tag.toLowerCase().includes(queryLower)) {
        suggestions.add(tag);
      }
    });
    
    return Array.from(suggestions).slice(0, 5);
  }, [state.templates, state.categories, state.availableTags]);

  // Update search suggestions when search changes
  useEffect(() => {
    if (state.filters.search) {
      const suggestions = generateSearchSuggestions(state.filters.search);
      updateState(prev => ({ ...prev, searchSuggestions: suggestions }));
    } else {
      updateState(prev => ({ ...prev, searchSuggestions: [] }));
    }
  }, [state.filters.search, generateSearchSuggestions, updateState]);

  // Actions
  const actions = {
    // Filter actions
    setFilters: useCallback((filters: Partial<FilterState>) => {
      updateState(prev => ({
        ...prev,
        filters: { ...prev.filters, ...filters },
        pagination: { ...prev.pagination, first: 0 } // Reset pagination
      }));
    }, [updateState]),

    clearFilters: useCallback(() => {
      updateState(prev => ({
        ...prev,
        filters: {
          search: '',
          category: '',
          language: '',
          jurisdiction: '',
          status: 'all',
          tags: []
        },
        pagination: { ...prev.pagination, first: 0 }
      }));
    }, [updateState]),

    // Pagination actions
    setPagination: useCallback((pagination: Partial<{ first: number; rows: number }>) => {
      updateState(prev => ({
        ...prev,
        pagination: { ...prev.pagination, ...pagination }
      }));
    }, [updateState]),

    // Sorting actions
    setSorting: useCallback((sorting: Partial<{ sortBy: string; sortOrder: 'asc' | 'desc' }>) => {
      updateState(prev => ({
        ...prev,
        sorting: { ...prev.sorting, ...sorting },
        pagination: { ...prev.pagination, first: 0 } // Reset pagination
      }));
    }, [updateState]),

    // Selection actions
    setSelectedTemplates: useCallback((templateIds: string[]) => {
      updateState(prev => ({
        ...prev,
        selection: { ...prev.selection, selectedTemplates: templateIds }
      }));
    }, [updateState]),

    toggleTemplateSelection: useCallback((templateId: string, selected?: boolean) => {
      updateState(prev => {
        const currentSelection = prev.selection.selectedTemplates;
        const isCurrentlySelected = currentSelection.includes(templateId);
        const shouldSelect = selected !== undefined ? selected : !isCurrentlySelected;
        
        return {
          ...prev,
          selection: {
            ...prev.selection,
            selectedTemplates: shouldSelect
              ? [...currentSelection, templateId]
              : currentSelection.filter(id => id !== templateId)
          }
        };
      });
    }, [updateState]),

    selectAllTemplates: useCallback((selected: boolean) => {
      updateState(prev => ({
        ...prev,
        selection: {
          ...prev.selection,
          selectedTemplates: selected ? prev.templates.map(t => t.id) : []
        }
      }));
    }, [updateState]),

    toggleFavorite: useCallback((templateId: string) => {
      updateState(prev => {
        const favorites = prev.selection.favorites;
        return {
          ...prev,
          selection: {
            ...prev.selection,
            favorites: favorites.includes(templateId)
              ? favorites.filter(id => id !== templateId)
              : [...favorites, templateId]
          }
        };
      });
    }, [updateState]),

    // Refresh actions
    refresh: useCallback(() => {
      return Promise.all([fetchTemplates(), fetchCategories()]);
    }, [fetchTemplates, fetchCategories]),

    // Error handling
    clearError: useCallback(() => {
      updateState(prev => ({ ...prev, error: null }));
    }, [updateState])
  };

  // Auto-fetch on mount and dependency changes
  useEffect(() => {
    if (autoFetch) {
      fetchCategories();
    }
  }, [fetchCategories, autoFetch]);

  useEffect(() => {
    if (autoFetch) {
      fetchTemplates();
    }
  }, [
    fetchTemplates, 
    autoFetch,
    debouncedSearchTerm,
    state.filters.category,
    state.filters.language,
    state.filters.jurisdiction,
    state.filters.status,
    state.filters.tags,
    state.pagination.first,
    state.pagination.rows,
    state.sorting.sortBy,
    state.sorting.sortOrder
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    // State
    ...state,
    
    // Computed values
    hasActiveFilters: state.filters.search || 
                     state.filters.category || 
                     state.filters.language || 
                     state.filters.jurisdiction || 
                     state.filters.status !== 'all' || 
                     state.filters.tags.length > 0,
    
    isAllSelected: state.selection.selectedTemplates.length === state.templates.length && state.templates.length > 0,
    hasSelection: state.selection.selectedTemplates.length > 0,
    
    // Actions
    actions,
    
    // Manual fetch functions
    fetchTemplates,
    fetchCategories
  };
};

export default useTemplateLibrary;