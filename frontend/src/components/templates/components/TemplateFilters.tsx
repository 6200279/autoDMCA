import React, { useState, useCallback, useMemo } from 'react';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Sidebar } from 'primereact/sidebar';
import { InputText } from 'primereact/inputtext';
import { EnhancedCard } from '../../common/EnhancedCard';
import { useTemplateLibraryContext } from '../context/TemplateLibraryContext';
import { TemplateFiltersProps, FilterPreset } from '../types/enhanced';
import { SUPPORTED_LANGUAGES, JURISDICTIONS } from '../../../types/templates';

interface ExtendedTemplateFiltersProps extends Omit<TemplateFiltersProps, 'onFiltersChange'> {
  showAsPanel?: boolean;
  collapsible?: boolean;
  showPresets?: boolean;
  showAdvancedFilters?: boolean;
}

const TemplateFilters: React.FC<ExtendedTemplateFiltersProps> = ({
  showAsPanel = false,
  collapsible = true,
  showPresets = true,
  showAdvancedFilters = false,
  className = ''
}) => {
  const {
    categories,
    availableTags,
    filters,
    actions,
    enhancedActions,
    filterPresets,
    totalRecords,
    selection,
    hasActiveFilters
  } = useTemplateLibraryContext();

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [presetDialogVisible, setPresetDialogVisible] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  // Status options with icons
  const statusOptions = [
    { label: 'All Templates', value: 'all', icon: 'pi pi-list' },
    { label: 'Active Only', value: 'active', icon: 'pi pi-check-circle' },
    { label: 'Inactive Only', value: 'inactive', icon: 'pi pi-times-circle' },
    { label: 'My Favorites', value: 'favorites', icon: 'pi pi-heart-fill' }
  ];

  // Language options with enhanced display
  const languageOptions = useMemo(() => [
    { label: 'All Languages', value: '', icon: 'pi pi-globe' },
    ...SUPPORTED_LANGUAGES.map(lang => ({
      label: lang.label,
      value: lang.value,
      icon: 'pi pi-flag'
    }))
  ], []);

  // Jurisdiction options
  const jurisdictionOptions = useMemo(() => [
    { label: 'All Jurisdictions', value: '', icon: 'pi pi-map' },
    ...JURISDICTIONS.map(jur => ({
      label: jur.label,
      value: jur.value,
      icon: 'pi pi-map-marker'
    }))
  ], []);

  // Category options with template counts
  const categoryOptions = useMemo(() => [
    { label: 'All Categories', value: '', icon: 'pi pi-list' },
    ...categories.map(cat => ({
      label: `${cat.name} (${cat.template_count})`,
      value: cat.name,
      icon: 'pi pi-tag',
      templateCount: cat.template_count
    }))
  ], [categories]);

  // Tag options for multi-select
  const tagOptions = useMemo(() => 
    availableTags.map(tag => ({
      label: tag,
      value: tag
    }))
  , [availableTags]);

  const handleFilterChange = useCallback((field: string, value: any) => {
    actions.setFilters({ [field]: value });
  }, [actions]);

  const handleTagsChange = useCallback((tags: string[]) => {
    actions.setFilters({ tags });
  }, [actions]);

  const clearAllFilters = useCallback(() => {
    actions.clearFilters();
    setSelectedPreset('');
  }, [actions]);

  const saveCurrentFiltersAsPreset = useCallback(() => {
    if (newPresetName.trim()) {
      enhancedActions.saveFilterPreset({
        name: newPresetName.trim(),
        description: `Filter preset created on ${new Date().toLocaleDateString()}`,
        filters: filters
      });
      setNewPresetName('');
      setPresetDialogVisible(false);
    }
  }, [newPresetName, filters, enhancedActions]);

  const applyPreset = useCallback((presetId: string) => {
    enhancedActions.applyFilterPreset(presetId);
    setSelectedPreset(presetId);
  }, [enhancedActions]);

  const deletePreset = useCallback((presetId: string) => {
    enhancedActions.deleteFilterPreset(presetId);
    if (selectedPreset === presetId) {
      setSelectedPreset('');
    }
  }, [enhancedActions, selectedPreset]);

  // Active filters display
  const activeFilterChips = useMemo(() => {
    const chips = [];
    
    if (filters.search) {
      chips.push({
        key: 'search',
        label: `Search: "${filters.search}"`,
        icon: 'pi pi-search',
        onRemove: () => handleFilterChange('search', '')
      });
    }
    
    if (filters.category) {
      chips.push({
        key: 'category',
        label: `Category: ${filters.category}`,
        icon: 'pi pi-tag',
        onRemove: () => handleFilterChange('category', '')
      });
    }
    
    if (filters.status !== 'all') {
      const statusLabel = statusOptions.find(opt => opt.value === filters.status)?.label;
      chips.push({
        key: 'status',
        label: `Status: ${statusLabel}`,
        icon: 'pi pi-circle',
        onRemove: () => handleFilterChange('status', 'all')
      });
    }
    
    if (filters.language) {
      const langLabel = SUPPORTED_LANGUAGES.find(lang => lang.value === filters.language)?.label;
      chips.push({
        key: 'language',
        label: `Language: ${langLabel}`,
        icon: 'pi pi-globe',
        onRemove: () => handleFilterChange('language', '')
      });
    }
    
    if (filters.jurisdiction) {
      const jurLabel = JURISDICTIONS.find(jur => jur.value === filters.jurisdiction)?.label;
      chips.push({
        key: 'jurisdiction',
        label: `Jurisdiction: ${jurLabel}`,
        icon: 'pi pi-map',
        onRemove: () => handleFilterChange('jurisdiction', '')
      });
    }
    
    if (filters.tags && filters.tags.length > 0) {
      filters.tags.forEach(tag => {
        chips.push({
          key: `tag-${tag}`,
          label: `Tag: ${tag}`,
          icon: 'pi pi-tag',
          onRemove: () => {
            const newTags = filters.tags.filter(t => t !== tag);
            handleTagsChange(newTags);
          }
        });
      });
    }
    
    return chips;
  }, [filters, handleFilterChange, handleTagsChange]);

  const filtersContent = (
    <div className={`template-filters ${className}`}>
      <div className="filters-header">
        <div className="filters-title-section">
          <h3 className="filters-title">
            <i className="pi pi-filter filters-icon" />
            Filter Templates
            <Badge value={totalRecords} className="ml-2" />
          </h3>
          {collapsible && (
            <Button
              icon={isCollapsed ? 'pi pi-chevron-down' : 'pi pi-chevron-up'}
              className="p-button-text p-button-sm"
              onClick={() => setIsCollapsed(!isCollapsed)}
              tooltip={isCollapsed ? 'Expand filters' : 'Collapse filters'}
            />
          )}
        </div>
        <div className="filters-actions">
          {showPresets && (
            <Button
              icon="pi pi-bookmark"
              className="p-button-text p-button-sm"
              onClick={() => setPresetDialogVisible(true)}
              tooltip="Save current filters as preset"
              disabled={!hasActiveFilters}
            />
          )}
          <Button
            label="Reset"
            icon="pi pi-refresh"
            className="p-button-text p-button-sm"
            onClick={clearAllFilters}
            disabled={!hasActiveFilters}
            tooltip="Clear all filters"
          />
        </div>
      </div>

      {!isCollapsed && (
        <div className="filters-content">
          {/* Filter Presets */}
          {showPresets && filterPresets.length > 0 && (
            <div className="filter-group preset-group">
              <label className="filter-label">
                <i className="pi pi-bookmark" />
                Saved Filters
              </label>
              <Dropdown
                value={selectedPreset}
                onChange={(e) => applyPreset(e.value)}
                options={filterPresets.map(preset => ({
                  label: preset.name,
                  value: preset.id,
                  description: preset.description
                }))}
                placeholder="Select a saved filter"
                className="w-full"
                showClear
                optionLabel="label"
                itemTemplate={(option) => (
                  <div className="preset-option">
                    <span className="preset-name">{option.label}</span>
                    {option.description && (
                      <small className="preset-description">{option.description}</small>
                    )}
                    <Button
                      icon="pi pi-trash"
                      className="p-button-text p-button-sm preset-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        deletePreset(option.value);
                      }}
                      tooltip="Delete preset"
                    />
                  </div>
                )}
              />
            </div>
          )}

          {/* Main Filters */}
          <div className="filters-grid">
            {/* Category Filter */}
            <div className="filter-group enhanced">
              <label className="filter-label">
                <i className="pi pi-tag" />
                Category
              </label>
              <Dropdown
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.value)}
                options={categoryOptions}
                placeholder="Choose category"
                className="w-full filter-dropdown"
                showClear
                filter
                optionLabel="label"
                itemTemplate={(option) => (
                  <div className="category-option">
                    <i className={option.icon} />
                    <span>{option.label}</span>
                  </div>
                )}
              />
            </div>

            {/* Status Filter */}
            <div className="filter-group enhanced">
              <label className="filter-label">
                <i className="pi pi-circle" />
                Status
              </label>
              <Dropdown
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.value)}
                options={statusOptions}
                className="w-full filter-dropdown"
                optionLabel="label"
                itemTemplate={(option) => (
                  <div className="status-option">
                    <i className={option.icon} />
                    <span>{option.label}</span>
                    {option.value === 'favorites' && (
                      <Badge value={selection.favorites.length} className="ml-auto" />
                    )}
                  </div>
                )}
              />
            </div>

            {/* Language Filter */}
            <div className="filter-group enhanced">
              <label className="filter-label">
                <i className="pi pi-globe" />
                Language
              </label>
              <Dropdown
                value={filters.language}
                onChange={(e) => handleFilterChange('language', e.value)}
                options={languageOptions}
                placeholder="Select language"
                className="w-full filter-dropdown"
                showClear
                filter
                optionLabel="label"
                itemTemplate={(option) => (
                  <div className="language-option">
                    <i className={option.icon} />
                    <span>{option.label}</span>
                  </div>
                )}
              />
            </div>

            {/* Jurisdiction Filter */}
            <div className="filter-group enhanced">
              <label className="filter-label">
                <i className="pi pi-map" />
                Jurisdiction
              </label>
              <Dropdown
                value={filters.jurisdiction}
                onChange={(e) => handleFilterChange('jurisdiction', e.value)}
                options={jurisdictionOptions}
                placeholder="Select jurisdiction"
                className="w-full filter-dropdown"
                showClear
                filter
                optionLabel="label"
                itemTemplate={(option) => (
                  <div className="jurisdiction-option">
                    <i className={option.icon} />
                    <span>{option.label}</span>
                  </div>
                )}
              />
            </div>

            {/* Tags Filter */}
            {availableTags.length > 0 && (
              <div className="filter-group enhanced tags-group">
                <label className="filter-label">
                  <i className="pi pi-tags" />
                  Tags
                </label>
                <MultiSelect
                  value={filters.tags}
                  onChange={(e) => handleTagsChange(e.value)}
                  options={tagOptions}
                  placeholder="Select tags"
                  className="w-full tags-multiselect"
                  display="chip"
                  filter
                  maxSelectedLabels={3}
                  selectedItemsLabel="{0} tags selected"
                  optionLabel="label"
                />
              </div>
            )}
          </div>

          {/* Advanced Filters */}
          {showAdvancedFilters && (
            <div className="advanced-filters-section">
              <h4 className="advanced-filters-title">Advanced Options</h4>
              <div className="advanced-filters-grid">
                <div className="filter-group checkbox-group">
                  <div className="checkbox-item">
                    <Checkbox
                      inputId="hide-inactive"
                      checked={filters.status === 'active'}
                      onChange={(e) => handleFilterChange('status', e.checked ? 'active' : 'all')}
                    />
                    <label htmlFor="hide-inactive" className="checkbox-label">
                      Hide inactive templates
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filter Statistics */}
          <div className="filter-stats">
            <div className="stat-item">
              <span className="stat-number">{totalRecords}</span>
              <span className="stat-label">Total Templates</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{selection.favorites.length}</span>
              <span className="stat-label">Favorites</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{categories.length}</span>
              <span className="stat-label">Categories</span>
            </div>
          </div>

          {/* Active Filters Display */}
          {activeFilterChips.length > 0 && (
            <div className="active-filters">
              <span className="active-filters-label">Active filters:</span>
              <div className="active-filters-chips">
                {activeFilterChips.map((chip) => (
                  <Chip
                    key={chip.key}
                    label={chip.label}
                    icon={chip.icon}
                    removable
                    onRemove={chip.onRemove}
                    className="active-filter-chip"
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Save Preset Dialog */}
      <Sidebar
        visible={presetDialogVisible}
        onHide={() => setPresetDialogVisible(false)}
        className="preset-dialog"
        position="right"
        style={{ width: '400px' }}
      >
        <div className="preset-dialog-content">
          <h3>Save Filter Preset</h3>
          <p>Save your current filter settings for quick access later.</p>
          
          <div className="preset-form">
            <div className="field">
              <label htmlFor="preset-name">Preset Name</label>
              <InputText
                id="preset-name"
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                placeholder="Enter preset name"
                className="w-full"
              />
            </div>
            
            <div className="current-filters-preview">
              <h4>Current Filters:</h4>
              {activeFilterChips.length > 0 ? (
                <div className="preview-chips">
                  {activeFilterChips.map((chip) => (
                    <Chip
                      key={chip.key}
                      label={chip.label}
                      icon={chip.icon}
                      className="preview-chip"
                    />
                  ))}
                </div>
              ) : (
                <p className="no-filters-message">No active filters to save.</p>
              )}
            </div>
            
            <div className="preset-actions">
              <Button
                label="Save Preset"
                icon="pi pi-check"
                onClick={saveCurrentFiltersAsPreset}
                disabled={!newPresetName.trim() || activeFilterChips.length === 0}
                className="w-full"
              />
              <Button
                label="Cancel"
                icon="pi pi-times"
                className="p-button-secondary w-full"
                onClick={() => {
                  setPresetDialogVisible(false);
                  setNewPresetName('');
                }}
              />
            </div>
          </div>
        </div>
      </Sidebar>
    </div>
  );

  if (showAsPanel) {
    return (
      <EnhancedCard className="filters-panel" variant="outlined">
        {filtersContent}
      </EnhancedCard>
    );
  }

  return filtersContent;
};

export default React.memo(TemplateFilters);