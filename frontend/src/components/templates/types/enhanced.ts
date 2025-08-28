import { DMCATemplate, TemplateCategory } from '../../../types/templates';

// Enhanced template interfaces with additional metadata
export interface EnhancedDMCATemplate extends DMCATemplate {
  isRecentlyViewed?: boolean;
  viewedAt?: string;
  isFavorite?: boolean;
  usageScore?: number;
  similarTemplates?: string[];
  thumbnailUrl?: string;
  previewContent?: string;
  validationStatus?: 'valid' | 'warning' | 'error';
  validationMessages?: string[];
}

export interface TemplateSearchFilter {
  field: keyof DMCATemplate | 'global';
  operator: 'contains' | 'equals' | 'starts_with' | 'ends_with' | 'regex';
  value: string;
  negated?: boolean;
}

export interface AdvancedSearchQuery {
  filters: TemplateSearchFilter[];
  operator: 'AND' | 'OR';
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface TemplateGridLayout {
  type: 'grid' | 'masonry' | 'list' | 'compact';
  size: 'small' | 'medium' | 'large';
  columnsCount?: number;
  itemHeight?: number;
  gap?: number;
}

export interface TemplateViewPreferences {
  layout: TemplateGridLayout;
  showThumbnails: boolean;
  showPreview: boolean;
  showMetadata: boolean;
  showUsageStats: boolean;
  hideInactive: boolean;
  groupByCategory: boolean;
}

export interface TemplateSelectionMode {
  enabled: boolean;
  allowMultiple: boolean;
  allowSelectAll: boolean;
  onSelectionChange?: (selectedIds: string[], templates: DMCATemplate[]) => void;
}

export interface TemplateAction {
  id: string;
  label: string;
  icon: string;
  handler: (template: DMCATemplate) => void | Promise<void>;
  disabled?: (template: DMCATemplate) => boolean;
  visible?: (template: DMCATemplate) => boolean;
  severity?: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'danger';
  tooltip?: string;
}

export interface BulkAction {
  id: string;
  label: string;
  icon: string;
  handler: (templateIds: string[], templates: DMCATemplate[]) => void | Promise<void>;
  confirmMessage?: string;
  severity?: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'danger';
  disabled?: (templateIds: string[], templates: DMCATemplate[]) => boolean;
}

export interface TemplateAnalytics {
  totalViews: number;
  uniqueUsers: number;
  avgRating: number;
  usageGrowth: number;
  popularTags: string[];
  categoryDistribution: Record<string, number>;
  languageDistribution: Record<string, number>;
  recentActivity: {
    date: string;
    action: string;
    count: number;
  }[];
}

export interface SearchSuggestion {
  type: 'template' | 'category' | 'tag' | 'recent' | 'popular';
  value: string;
  label: string;
  icon?: string;
  count?: number;
  description?: string;
}

export interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  filters: Record<string, any>;
  isDefault?: boolean;
  isSystem?: boolean;
  createdAt?: string;
  usage_count?: number;
}

export interface TemplateComparison {
  templates: DMCATemplate[];
  fields: (keyof DMCATemplate)[];
  differences: {
    field: keyof DMCATemplate;
    values: { templateId: string; value: any }[];
  }[];
}

export interface TemplateExportOptions {
  format: 'json' | 'csv' | 'xlsx' | 'pdf' | 'html' | 'xml';
  templateIds: string[];
  includeMetadata: boolean;
  includeVariables: boolean;
  includeContent: boolean;
  includeAnalytics?: boolean;
}

export interface TemplateImportResult {
  success: boolean;
  imported: number;
  skipped: number;
  errors: {
    row?: number;
    templateId?: string;
    field?: string;
    message: string;
  }[];
  duplicates: {
    templateId: string;
    name: string;
    action: 'skipped' | 'updated' | 'renamed';
  }[];
}

// UI Component Props Interfaces
export interface TemplateCardProps {
  template: EnhancedDMCATemplate;
  layout: TemplateGridLayout;
  selected?: boolean;
  selectionMode?: TemplateSelectionMode;
  actions?: TemplateAction[];
  showThumbnail?: boolean;
  showPreview?: boolean;
  showMetadata?: boolean;
  showUsageStats?: boolean;
  onSelectionChange?: (templateId: string, selected: boolean) => void;
  onClick?: (template: DMCATemplate) => void;
  onDoubleClick?: (template: DMCATemplate) => void;
  className?: string;
  style?: React.CSSProperties;
}

export interface TemplateGridProps {
  templates: EnhancedDMCATemplate[];
  layout: TemplateGridLayout;
  loading?: boolean;
  virtualScrolling?: boolean;
  containerHeight?: number;
  selectionMode?: TemplateSelectionMode;
  actions?: TemplateAction[];
  emptyStateProps?: {
    title?: string;
    description?: string;
    action?: { label: string; onClick: () => void };
  };
  onTemplateClick?: (template: DMCATemplate) => void;
  onSelectionChange?: (selectedIds: string[]) => void;
  className?: string;
}

export interface TemplateFiltersProps {
  categories: TemplateCategory[];
  availableTags: string[];
  filters: Record<string, any>;
  presets?: FilterPreset[];
  showAdvancedSearch?: boolean;
  onFiltersChange: (filters: Record<string, any>) => void;
  onPresetSave?: (preset: Omit<FilterPreset, 'id' | 'createdAt'>) => void;
  onPresetDelete?: (presetId: string) => void;
  onClearAll: () => void;
  className?: string;
}

export interface TemplateSearchProps {
  value: string;
  suggestions?: SearchSuggestion[];
  showHistory?: boolean;
  showSuggestions?: boolean;
  placeholder?: string;
  onValueChange: (value: string) => void;
  onSearch?: (query: string) => void;
  onSuggestionSelect?: (suggestion: SearchSuggestion) => void;
  className?: string;
}

export interface TemplateToolbarProps {
  totalCount: number;
  selectedCount: number;
  viewPreferences: TemplateViewPreferences;
  bulkActions?: BulkAction[];
  primaryAction?: {
    label: string;
    icon: string;
    onClick: () => void;
  };
  onViewPreferencesChange: (preferences: Partial<TemplateViewPreferences>) => void;
  onBulkAction?: (actionId: string, selectedIds: string[]) => void;
  className?: string;
}

// Hook return types
export interface UseTemplateSearchReturn {
  searchQuery: string;
  suggestions: SearchSuggestion[];
  history: string[];
  isSearching: boolean;
  setSearchQuery: (query: string) => void;
  performSearch: (query?: string) => void;
  clearSearch: () => void;
  clearHistory: () => void;
}

export interface UseTemplateSelectionReturn {
  selectedIds: string[];
  selectedTemplates: DMCATemplate[];
  isAllSelected: boolean;
  hasSelection: boolean;
  toggleSelection: (templateId: string) => void;
  toggleAll: () => void;
  clearSelection: () => void;
  selectTemplates: (templateIds: string[]) => void;
}

export interface UseTemplateActionsReturn {
  performAction: (actionId: string, template: DMCATemplate) => Promise<void>;
  performBulkAction: (actionId: string, templateIds: string[]) => Promise<void>;
  canPerformAction: (actionId: string, template: DMCATemplate) => boolean;
  isActionVisible: (actionId: string, template: DMCATemplate) => boolean;
}

// Event interfaces
export interface TemplateEvent {
  type: 'created' | 'updated' | 'deleted' | 'viewed' | 'favorited' | 'used';
  templateId: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface TemplateLibraryEvent {
  type: 'search' | 'filter' | 'sort' | 'view_change' | 'bulk_action';
  payload: Record<string, any>;
  timestamp: string;
}