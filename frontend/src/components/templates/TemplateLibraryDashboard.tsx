import React, { useState, useEffect, useCallback, useRef } from 'react';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Button } from 'primereact/button';
import { Panel } from 'primereact/panel';
import { Checkbox } from 'primereact/checkbox';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Paginator } from 'primereact/paginator';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Dialog } from 'primereact/dialog';
import { AutoComplete } from 'primereact/autocomplete';
import { Skeleton } from 'primereact/skeleton';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Sidebar } from 'primereact/sidebar';
import { Toolbar } from 'primereact/toolbar';
import { ToggleButton } from 'primereact/togglebutton';
import { EnhancedCard } from '../common/EnhancedCard';
import { EnhancedButton } from '../common/EnhancedButton';
import { EmptyState } from '../common/EmptyStates';
import TemplateCard from './TemplateCard';
import { templatesApi } from '../../services/api';
import { 
  DMCATemplate, 
  TemplateCategory, 
  TemplateListParams,
  PaginatedTemplatesResponse,
  DEFAULT_CATEGORIES,
  SUPPORTED_LANGUAGES,
  JURISDICTIONS
} from '../../types/templates';
import './TemplateLibraryDashboard.css';

interface TemplateLibraryDashboardProps {
  onTemplateEdit?: (template: DMCATemplate) => void;
  onTemplateCreate?: () => void;
  onTemplateView?: (template: DMCATemplate) => void;
}

interface SearchHistory {
  query: string;
  timestamp: number;
  resultsCount: number;
}

interface FilterState {
  search: string;
  category: string;
  language: string;
  jurisdiction: string;
  status: 'all' | 'active' | 'inactive' | 'favorites';
  tags: string[];
}

const TemplateLibraryDashboard: React.FC<TemplateLibraryDashboardProps> = ({
  onTemplateEdit,
  onTemplateCreate,
  onTemplateView
}) => {
  // State management
  const [templates, setTemplates] = useState<DMCATemplate[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [first, setFirst] = useState(0);
  const [rows, setRows] = useState(20);
  
  // View and layout state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [gridSize, setGridSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [showFilters, setShowFilters] = useState(true);
  const [sidebarVisible, setSidebarVisible] = useState(false);
  
  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    category: '',
    language: '',
    jurisdiction: '',
    status: 'all',
    tags: []
  });
  
  // Search and filtering
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([]);
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [quickFilters, setQuickFilters] = useState<string[]>([]);
  
  // Selection and bulk operations
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  
  // Sort options
  const [sortBy, setSortBy] = useState<string>('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // Dialog states
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [bulkAction, setBulkAction] = useState<'delete' | 'activate' | 'deactivate' | 'export'>('delete');
  const [exportDialogVisible, setExportDialogVisible] = useState(false);
  
  const toast = useRef<Toast>(null);
  const searchTimeout = useRef<NodeJS.Timeout>();

  // Load favorites from localStorage
  useEffect(() => {
    const savedFavorites = localStorage.getItem('template-favorites');
    if (savedFavorites) {
      setFavorites(JSON.parse(savedFavorites));
    }
    
    const savedSearchHistory = localStorage.getItem('template-search-history');
    if (savedSearchHistory) {
      setSearchHistory(JSON.parse(savedSearchHistory));
    }
  }, []);

  // Save favorites to localStorage
  useEffect(() => {
    localStorage.setItem('template-favorites', JSON.stringify(favorites));
  }, [favorites]);

  // Fetch templates with current filters
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const params: TemplateListParams = {
        page: Math.floor(first / rows) + 1,
        limit: rows,
        search: filters.search || undefined,
        category: filters.category || undefined,
        language: filters.language || undefined,
        jurisdiction: filters.jurisdiction || undefined,
        is_active: filters.status === 'active' ? true : filters.status === 'inactive' ? false : undefined,
        sort_by: sortBy as any,
        sort_order: sortOrder,
        tags: filters.tags.length > 0 ? filters.tags : undefined,
      };

      const response = await templatesApi.getTemplates(params);
      const data: PaginatedTemplatesResponse = response.data;
      
      let filteredTemplates = data.templates;
      
      // Apply favorite filter client-side
      if (filters.status === 'favorites') {
        filteredTemplates = data.templates.filter(t => favorites.includes(t.id));
        setTotalRecords(filteredTemplates.length);
      } else {
        setTotalRecords(data.total);
      }
      
      setTemplates(filteredTemplates);
      
      // Update search history
      if (filters.search && filteredTemplates.length > 0) {
        const newHistoryItem: SearchHistory = {
          query: filters.search,
          timestamp: Date.now(),
          resultsCount: filteredTemplates.length
        };
        
        setSearchHistory(prev => {
          const filtered = prev.filter(item => item.query !== filters.search);
          const updated = [newHistoryItem, ...filtered].slice(0, 10);
          localStorage.setItem('template-search-history', JSON.stringify(updated));
          return updated;
        });
      }
      
    } catch (error) {
      console.error('Error fetching templates:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load templates'
      });
    } finally {
      setLoading(false);
    }
  }, [first, rows, filters, sortBy, sortOrder, favorites]);

  // Fetch categories and extract available tags
  const fetchCategories = useCallback(async () => {
    try {
      const response = await templatesApi.getCategories();
      setCategories(response.data);
      
      // Extract all available tags from templates
      const allTemplatesResponse = await templatesApi.getTemplates({ limit: 1000 });
      const allTags = new Set<string>();
      allTemplatesResponse.data.templates.forEach(template => {
        template.tags?.forEach(tag => allTags.add(tag));
      });
      setAvailableTags(Array.from(allTags));
      
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories(DEFAULT_CATEGORIES.map((cat, index) => ({
        id: cat.toLowerCase().replace(/\s+/g, '-'),
        name: cat,
        description: `${cat} templates`,
        template_count: 0
      })));
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Debounced search
  useEffect(() => {
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }
    
    searchTimeout.current = setTimeout(() => {
      setFirst(0); // Reset pagination when search changes
    }, 300);
    
    return () => {
      if (searchTimeout.current) {
        clearTimeout(searchTimeout.current);
      }
    };
  }, [filters.search]);

  // Generate search suggestions
  const generateSearchSuggestions = (query: string) => {
    if (!query) return [];
    
    const suggestions = new Set<string>();
    
    // Add matching template names
    templates.forEach(template => {
      if (template.name.toLowerCase().includes(query.toLowerCase())) {
        suggestions.add(template.name);
      }
    });
    
    // Add matching categories
    categories.forEach(category => {
      if (category.name.toLowerCase().includes(query.toLowerCase())) {
        suggestions.add(category.name);
      }
    });
    
    // Add matching tags
    availableTags.forEach(tag => {
      if (tag.toLowerCase().includes(query.toLowerCase())) {
        suggestions.add(tag);
      }
    });
    
    // Add from search history
    searchHistory.forEach(item => {
      if (item.query.toLowerCase().includes(query.toLowerCase())) {
        suggestions.add(item.query);
      }
    });
    
    return Array.from(suggestions).slice(0, 5);
  };

  // Handlers
  const handleSearchChange = (value: string) => {
    setFilters(prev => ({ ...prev, search: value }));
    setSearchSuggestions(generateSearchSuggestions(value));
  };

  const handleFilterChange = (field: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setFirst(0);
  };

  const handlePageChange = (event: any) => {
    setFirst(event.first);
    setRows(event.rows);
  };

  const handleSelectionChange = (templateId: string, selected: boolean) => {
    setSelectedTemplates(prev => 
      selected 
        ? [...prev, templateId]
        : prev.filter(id => id !== templateId)
    );
  };

  const handleSelectAll = (selected: boolean) => {
    setSelectedTemplates(selected ? templates.map(t => t.id) : []);
  };

  const handleToggleFavorite = (template: DMCATemplate) => {
    setFavorites(prev => 
      prev.includes(template.id)
        ? prev.filter(id => id !== template.id)
        : [...prev, template.id]
    );
  };

  // Bulk operations
  const handleBulkAction = async () => {
    if (selectedTemplates.length === 0) return;
    
    try {
      switch (bulkAction) {
        case 'delete':
          await templatesApi.bulkDelete(selectedTemplates);
          break;
        case 'activate':
          await templatesApi.bulkActivate(selectedTemplates);
          break;
        case 'deactivate':
          await templatesApi.bulkDeactivate(selectedTemplates);
          break;
        case 'export':
          // Handle export logic
          break;
      }
      
      fetchTemplates();
      setSelectedTemplates([]);
      setConfirmVisible(false);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `Templates ${bulkAction}d successfully`
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: `Failed to ${bulkAction} templates`
      });
    }
  };

  const clearAllFilters = () => {
    setFilters({
      search: '',
      category: '',
      language: '',
      jurisdiction: '',
      status: 'all',
      tags: []
    });
    setFirst(0);
  };

  const getGridColumns = () => {
    switch (gridSize) {
      case 'small': return 'repeat(auto-fill, minmax(280px, 1fr))';
      case 'medium': return 'repeat(auto-fill, minmax(320px, 1fr))';
      case 'large': return 'repeat(auto-fill, minmax(380px, 1fr))';
      default: return 'repeat(auto-fill, minmax(320px, 1fr))';
    }
  };

  // Sort options
  const sortOptions = [
    { label: 'Recently Updated', value: 'updated_at_desc' },
    { label: 'Oldest Updated', value: 'updated_at_asc' },
    { label: 'Name A-Z', value: 'name_asc' },
    { label: 'Name Z-A', value: 'name_desc' },
    { label: 'Most Used', value: 'usage_count_desc' },
    { label: 'Least Used', value: 'usage_count_asc' },
    { label: 'Recently Created', value: 'created_at_desc' },
    { label: 'Category', value: 'category_asc' }
  ];

  const renderBreadcrumb = () => {
    return (
      <div className="template-breadcrumb-section">
        <nav className="template-breadcrumb" aria-label="Breadcrumb navigation">
          <div className="breadcrumb-list">
            <Button
              icon="pi pi-home"
              className="p-button-text breadcrumb-home"
              onClick={() => window.location.href = '/'}
              tooltip="Go to Dashboard"
              aria-label="Navigate to Dashboard"
            />
            <i className="pi pi-chevron-right breadcrumb-separator"></i>
            <span className="breadcrumb-current">
              <i className="pi pi-file-text"></i>
              Template Library
            </span>
          </div>
        </nav>
      </div>
    );
  };

  const renderSearchBar = () => (
    <div className="template-search-section" id="search-section">
      <div className="search-bar-container">
        <div className="search-header">
          <h2 className="search-title">Find Your Perfect Template</h2>
          <p className="search-subtitle">Search through {totalRecords} professional DMCA templates</p>
        </div>
        <div className="search-input-wrapper">
          <span className="p-input-icon-left p-input-icon-right search-input">
            <i className="pi pi-search search-icon" />
            <AutoComplete
              value={filters.search}
              suggestions={searchSuggestions}
              completeMethod={() => {}}
              onChange={(e) => handleSearchChange(e.value)}
              onSelect={(e) => handleSearchChange(e.value)}
              placeholder="Search by name, category, or keywords..."
              className="w-full"
              inputClassName="search-input-field"
              panelClassName="search-suggestions"
              aria-label="Search templates"
              role="searchbox"
            />
            {filters.search && (
              <i 
                className="pi pi-times search-clear" 
                onClick={() => handleSearchChange('')}
                role="button"
                tabIndex={0}
                aria-label="Clear search"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSearchChange('');
                  }
                }}
              />
            )}
          </span>
          
          {/* Quick Search Tags */}
          {!filters.search && (
            <div className="quick-search-tags">
              <span className="quick-search-label">Quick search:</span>
              <div className="quick-search-items">
                {['Copyright', 'Takedown', 'DMCA Notice', 'Content Removal'].map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    className="quick-search-chip"
                    onClick={() => handleSearchChange(tag)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Search History */}
        {searchHistory.length > 0 && !filters.search && (
          <div className="search-history">
            <span className="search-history-label">Recent searches:</span>
            <div className="search-history-items">
              {searchHistory.slice(0, 3).map((item, index) => (
                <Chip
                  key={index}
                  label={`${item.query} (${item.resultsCount})`}
                  className="search-history-chip cursor-pointer"
                  onClick={() => handleSearchChange(item.query)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderFilters = () => (
    <EnhancedCard className="filters-card" variant="outlined" id="filters-section">
      <div className="filters-header">
        <div className="filters-title-section">
          <h3 className="filters-title">
            <i className="pi pi-filter filters-icon"></i>
            Filter Templates
          </h3>
          <p className="filters-subtitle">Narrow down your search</p>
        </div>
        <Button
          label="Reset"
          icon="pi pi-refresh"
          className="p-button-text p-button-sm clear-filters-btn"
          onClick={clearAllFilters}
          disabled={Object.values(filters).every(v => !v || (Array.isArray(v) && v.length === 0))}
          tooltip="Clear all filters"
        />
      </div>
      
      <div className="filters-content">
        <div className="filters-grid">
          <div className="filter-group enhanced">
            <label className="filter-label">
              <i className="pi pi-tag"></i>
              Category
            </label>
            <Dropdown
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.value)}
              options={[
                { label: 'All Categories', value: '', icon: 'pi pi-list' },
                ...categories.map(cat => ({ 
                  label: `${cat.name}`, 
                  value: cat.name,
                  icon: 'pi pi-tag',
                  template: (option: any) => (
                    <div className="category-option">
                      <i className={option.icon}></i>
                      <span>{option.label}</span>
                      <Badge value={cat.template_count} className="ml-auto" />
                    </div>
                  )
                }))
              ]}
              placeholder="Choose category"
              className="w-full filter-dropdown"
              showClear
              filter
            />
          </div>

          <div className="filter-group enhanced">
            <label className="filter-label">
              <i className="pi pi-circle"></i>
              Status
            </label>
            <Dropdown
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.value)}
              options={[
                { label: 'All Templates', value: 'all', icon: 'pi pi-list' },
                { label: 'Active Templates', value: 'active', icon: 'pi pi-check-circle' },
                { label: 'Inactive Templates', value: 'inactive', icon: 'pi pi-times-circle' },
                { label: 'My Favorites', value: 'favorites', icon: 'pi pi-heart-fill' }
              ]}
              className="w-full filter-dropdown"
              optionLabel="label"
            />
          </div>

          <div className="filter-group enhanced">
            <label className="filter-label">
              <i className="pi pi-globe"></i>
              Language
            </label>
            <Dropdown
              value={filters.language}
              onChange={(e) => handleFilterChange('language', e.value)}
              options={[
                { label: 'All Languages', value: '', icon: 'pi pi-globe' },
                ...SUPPORTED_LANGUAGES.map(lang => ({ ...lang, icon: 'pi pi-flag' }))
              ]}
              placeholder="Select language"
              className="w-full filter-dropdown"
              showClear
              filter
            />
          </div>

          <div className="filter-group enhanced">
            <label className="filter-label">
              <i className="pi pi-map"></i>
              Jurisdiction
            </label>
            <Dropdown
              value={filters.jurisdiction}
              onChange={(e) => handleFilterChange('jurisdiction', e.value)}
              options={[
                { label: 'All Jurisdictions', value: '', icon: 'pi pi-map' },
                ...JURISDICTIONS.map(jur => ({ ...jur, icon: 'pi pi-map-marker' }))
              ]}
              placeholder="Select jurisdiction"
              className="w-full filter-dropdown"
              showClear
              filter
            />
          </div>
        </div>

        {/* Filter Statistics */}
        <div className="filter-stats">
          <div className="stat-item">
            <span className="stat-number">{totalRecords}</span>
            <span className="stat-label">Total Templates</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{favorites.length}</span>
            <span className="stat-label">Favorites</span>
          </div>
        </div>
      </div>

      {/* Active Filters */}
      {(filters.search || filters.category || filters.language || filters.jurisdiction || filters.status !== 'all' || filters.tags.length > 0) && (
        <div className="active-filters">
          <span className="active-filters-label">Active filters:</span>
          <div className="active-filters-chips">
            {filters.search && (
              <Chip
                label={`Search: "${filters.search}"`}
                icon="pi pi-search"
                removable
                onRemove={() => handleFilterChange('search', '')}
              />
            )}
            {filters.category && (
              <Chip
                label={`Category: ${filters.category}`}
                icon="pi pi-tag"
                removable
                onRemove={() => handleFilterChange('category', '')}
              />
            )}
            {filters.status !== 'all' && (
              <Chip
                label={`Status: ${filters.status}`}
                icon="pi pi-circle"
                removable
                onRemove={() => handleFilterChange('status', 'all')}
              />
            )}
            {filters.language && (
              <Chip
                label={`Language: ${SUPPORTED_LANGUAGES.find(l => l.value === filters.language)?.label}`}
                icon="pi pi-globe"
                removable
                onRemove={() => handleFilterChange('language', '')}
              />
            )}
            {filters.jurisdiction && (
              <Chip
                label={`Jurisdiction: ${JURISDICTIONS.find(j => j.value === filters.jurisdiction)?.label}`}
                icon="pi pi-map"
                removable
                onRemove={() => handleFilterChange('jurisdiction', '')}
              />
            )}
          </div>
        </div>
      )}
    </EnhancedCard>
  );

  const renderToolbar = () => (
    <div className="template-toolbar-container">
      {/* Breadcrumb */}
      {renderBreadcrumb()}
      
      <Toolbar
        className="template-toolbar"
        start={() => (
          <div className="toolbar-start">
            <div className="page-header">
              <div className="page-header-content">
                <h1 className="page-title">
                  <i className="pi pi-file-text page-title-icon"></i>
                  Template Library
                </h1>
                <div className="page-stats">
                  <Badge value={totalRecords} className="templates-count" />
                  <span className="templates-label">templates available</span>
                </div>
              </div>
            </div>
            
            {selectedTemplates.length > 0 && (
              <div className="bulk-selection-info">
                <div className="selection-indicator">
                  <Badge value={selectedTemplates.length} severity="info" className="selection-count" />
                  <span className="selection-text">selected</span>
                </div>
              </div>
            )}
          </div>
        )}
        center={() => (
          <div className="toolbar-center">
            {/* Enhanced View Controls */}
            <div className="view-controls-group">
              <div className="view-mode-toggle">
                <Button
                  icon="pi pi-th-large"
                  className={`view-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                  tooltip="Grid view"
                  size="small"
                />
                <Button
                  icon="pi pi-list"
                  className={`view-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                  onClick={() => setViewMode('list')}
                  tooltip="List view"
                  size="small"
                />
              </div>
              
              {viewMode === 'grid' && (
                <div className="grid-size-control">
                  <Dropdown
                    value={gridSize}
                    onChange={(e) => setGridSize(e.value)}
                    options={[
                      { label: 'Compact', value: 'small', icon: 'pi pi-th-large' },
                      { label: 'Comfortable', value: 'medium', icon: 'pi pi-stop' },
                      { label: 'Spacious', value: 'large', icon: 'pi pi-circle' }
                    ]}
                    optionLabel="label"
                    className="grid-size-dropdown"
                    placeholder="Card size"
                  />
                </div>
              )}
              
              <div className="filter-toggle">
                <Button
                  icon={showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'}
                  className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                  onClick={() => setShowFilters(!showFilters)}
                  tooltip={`${showFilters ? 'Hide' : 'Show'} filters`}
                  size="small"
                />
              </div>
            </div>
          </div>
        )}
        end={() => (
          <div className="toolbar-end">
            {/* Enhanced Sort Controls */}
            <div className="sort-control-group">
              <label className="sort-label">Sort by:</label>
              <Dropdown
                value={`${sortBy}_${sortOrder}`}
                onChange={(e) => {
                  const [field, order] = e.value.split('_');
                  setSortBy(field);
                  setSortOrder(order);
                }}
                options={sortOptions.map(opt => ({ ...opt, icon: 'pi pi-sort-alt' }))}
                className="sort-dropdown"
                placeholder="Sort options"
              />
            </div>
            
            {/* Bulk Action Buttons */}
            {selectedTemplates.length > 0 && (
              <div className="bulk-actions-group">
                <Button
                  label="Delete Selected"
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  className="bulk-action-btn"
                  onClick={() => {
                    setBulkAction('delete');
                    setConfirmVisible(true);
                  }}
                />
                <Button
                  label="Export"
                  icon="pi pi-download"
                  className="p-button-outlined bulk-action-btn"
                  size="small"
                  onClick={() => {
                    setBulkAction('export');
                    setExportDialogVisible(true);
                  }}
                />
              </div>
            )}
            
            {/* Primary Action */}
            <div className="primary-action">
              <EnhancedButton
                label="Create Template"
                icon="pi pi-plus"
                onClick={onTemplateCreate}
                className="create-template-btn"
              />
            </div>
          </div>
        )}
      />
    </div>
  );

  const renderTemplatesGrid = () => {
    if (loading) {
      return (
        <div 
          className="templates-loading-grid"
          style={{ 
            display: 'grid', 
            gridTemplateColumns: getGridColumns(),
            gap: '1.5rem'
          }}
        >
          {Array.from({ length: rows }).map((_, index) => (
            <Skeleton key={index} height="400px" />
          ))}
        </div>
      );
    }

    if (templates.length === 0) {
      return (
        <EmptyState
          variant="search"
          title="No templates found"
          description={
            Object.values(filters).some(v => v && (!Array.isArray(v) || v.length > 0))
              ? "Try adjusting your filters or search terms."
              : "Get started by creating your first DMCA template."
          }
          primaryAction={{
            label: "Create Template",
            onClick: () => onTemplateCreate?.()
          }}
        />
      );
    }

    if (viewMode === 'grid') {
      return (
        <div 
          className="templates-grid"
          style={{ 
            display: 'grid', 
            gridTemplateColumns: getGridColumns(),
            gap: '1.5rem'
          }}
          role="grid"
          aria-label={`Template library with ${templates.length} templates`}
        >
          {templates.map(template => (
            <TemplateCard
              key={template.id}
              template={template}
              selected={selectedTemplates.includes(template.id)}
              showCheckbox={selectedTemplates.length > 0 || templates.length > 1}
              onSelectionChange={handleSelectionChange}
              onEdit={onTemplateEdit}
              onView={onTemplateView}
              onDuplicate={(template) => {
                // Handle duplicate
                templatesApi.duplicateTemplate(template.id, `${template.name} (Copy)`);
                fetchTemplates();
              }}
              onDelete={(template) => {
                // Handle delete
                templatesApi.deleteTemplate(template.id);
                fetchTemplates();
              }}
              onToggleFavorite={handleToggleFavorite}
              isFavorite={favorites.includes(template.id)}
            />
          ))}
        </div>
      );
    }

    // List view implementation would go here
    return null;
  };

  return (
    <div className="template-library-dashboard">
      {/* Skip Navigation Links */}
      <div className="skip-links">
        <a href="#search-section" className="skip-link">Skip to search</a>
        <a href="#filters-section" className="skip-link">Skip to filters</a>
        <a href="#templates-section" className="skip-link">Skip to templates</a>
      </div>
      
      <Toast ref={toast} />
      
      {/* Confirm Dialog */}
      <ConfirmDialog
        visible={confirmVisible}
        onHide={() => setConfirmVisible(false)}
        message={`Are you sure you want to ${bulkAction} the selected ${selectedTemplates.length} template(s)?`}
        header="Confirm Action"
        icon="pi pi-exclamation-triangle"
        accept={handleBulkAction}
        reject={() => setConfirmVisible(false)}
      />

      {/* Enhanced Main Layout */}
      <div className="dashboard-layout enhanced">
        {renderToolbar()}
        
        <div className="dashboard-content enhanced">
          {showFilters ? (
            <Splitter className="enhanced-splitter" layout="horizontal">
              <SplitterPanel size={22} minSize={18} maxSize={35} className="filters-panel-container">
                <div className="filters-panel enhanced">
                  {renderSearchBar()}
                  {renderFilters()}
                </div>
              </SplitterPanel>
              <SplitterPanel size={78} className="templates-panel-container">
                <div className="templates-panel enhanced" id="templates-section">
                  {selectedTemplates.length > 0 && (
                    <div className="bulk-actions-bar enhanced">
                      <div className="bulk-selection-header">
                        <div className="bulk-selection-controls">
                          <Checkbox
                            checked={selectedTemplates.length === templates.length}
                            onChange={(e) => handleSelectAll(e.checked || false)}
                            className="select-all-checkbox"
                          />
                          <div className="selection-info">
                            <span className="selection-text">
                              {selectedTemplates.length === templates.length ? 'All' : selectedTemplates.length} of {templates.length} selected
                            </span>
                            <Button
                              label="Clear Selection"
                              icon="pi pi-times"
                              className="p-button-text p-button-sm"
                              onClick={() => setSelectedTemplates([])}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="templates-content-area">
                    {renderTemplatesGrid()}
                  </div>
                  
                  {/* Enhanced Pagination */}
                  {totalRecords > rows && (
                    <div className="template-pagination enhanced">
                      <div className="pagination-info">
                        <span className="pagination-summary">
                          Showing {first + 1} to {Math.min(first + rows, totalRecords)} of {totalRecords} templates
                        </span>
                      </div>
                      <Paginator
                        first={first}
                        rows={rows}
                        totalRecords={totalRecords}
                        rowsPerPageOptions={[12, 20, 36, 48]}
                        onPageChange={handlePageChange}
                        template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
                        className="enhanced-paginator"
                      />
                    </div>
                  )}
                </div>
              </SplitterPanel>
            </Splitter>
          ) : (
            <div className="templates-full-panel enhanced">
              <div className="search-bar-inline enhanced">
                {renderSearchBar()}
              </div>
              
              {selectedTemplates.length > 0 && (
                <div className="bulk-actions-bar enhanced">
                  <div className="bulk-selection-header">
                    <div className="bulk-selection-controls">
                      <Checkbox
                        checked={selectedTemplates.length === templates.length}
                        onChange={(e) => handleSelectAll(e.checked || false)}
                        className="select-all-checkbox"
                      />
                      <div className="selection-info">
                        <span className="selection-text">
                          {selectedTemplates.length === templates.length ? 'All' : selectedTemplates.length} of {templates.length} selected
                        </span>
                        <Button
                          label="Clear Selection"
                          icon="pi pi-times"
                          className="p-button-text p-button-sm"
                          onClick={() => setSelectedTemplates([])}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="templates-content-area">
                {renderTemplatesGrid()}
              </div>
              
              {/* Enhanced Pagination */}
              {totalRecords > rows && (
                <div className="template-pagination enhanced">
                  <div className="pagination-info">
                    <span className="pagination-summary">
                      Showing {first + 1} to {Math.min(first + rows, totalRecords)} of {totalRecords} templates
                    </span>
                  </div>
                  <Paginator
                    first={first}
                    rows={rows}
                    totalRecords={totalRecords}
                    rowsPerPageOptions={[12, 20, 36, 48]}
                    onPageChange={handlePageChange}
                    template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
                    className="enhanced-paginator"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mobile Filters Sidebar */}
      <Sidebar
        visible={sidebarVisible}
        onHide={() => setSidebarVisible(false)}
        className="filters-sidebar"
        position="left"
      >
        {renderSearchBar()}
        {renderFilters()}
      </Sidebar>
    </div>
  );
};

export default TemplateLibraryDashboard;