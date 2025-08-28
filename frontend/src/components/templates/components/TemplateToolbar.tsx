import React, { useMemo, useCallback } from 'react';
import { Toolbar } from 'primereact/toolbar';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { Badge } from 'primereact/badge';
import { SplitButton } from 'primereact/splitbutton';
import { ToggleButton } from 'primereact/togglebutton';
// Note: Using custom breadcrumb instead of PrimeReact Breadcrumb due to import issues
import { useTemplateLibraryContext } from '../context/TemplateLibraryContext';
import { TemplateToolbarProps, TemplateGridLayout } from '../types/enhanced';
import { EnhancedButton } from '../../common/EnhancedButton';

interface ExtendedTemplateToolbarProps extends Omit<TemplateToolbarProps, 'viewPreferences' | 'onViewPreferencesChange'> {
  showBreadcrumb?: boolean;
  showViewControls?: boolean;
  showSortControls?: boolean;
  showCreateButton?: boolean;
  onCreateTemplate?: () => void;
  className?: string;
}

const TemplateToolbar: React.FC<ExtendedTemplateToolbarProps> = ({
  showBreadcrumb = true,
  showViewControls = true,
  showSortControls = true,
  showCreateButton = true,
  primaryAction,
  onCreateTemplate,
  className = ''
}) => {
  const {
    totalRecords,
    selection,
    viewPreferences,
    enhancedActions,
    config,
    filters,
    sorting,
    actions,
    hasActiveFilters,
    hasSelection
  } = useTemplateLibraryContext();

  // Sort options
  const sortOptions = [
    { label: 'Recently Updated', value: 'updated_at_desc', icon: 'pi pi-sort-alt' },
    { label: 'Oldest Updated', value: 'updated_at_asc', icon: 'pi pi-sort-alt' },
    { label: 'Name A-Z', value: 'name_asc', icon: 'pi pi-sort-alpha-down' },
    { label: 'Name Z-A', value: 'name_desc', icon: 'pi pi-sort-alpha-up' },
    { label: 'Most Used', value: 'usage_count_desc', icon: 'pi pi-chart-line' },
    { label: 'Least Used', value: 'usage_count_asc', icon: 'pi pi-chart-line' },
    { label: 'Recently Created', value: 'created_at_desc', icon: 'pi pi-calendar-plus' },
    { label: 'Category', value: 'category_asc', icon: 'pi pi-tag' }
  ];

  // Layout size options
  const sizeOptions = [
    { label: 'Compact', value: 'small', icon: 'pi pi-th-large' },
    { label: 'Comfortable', value: 'medium', icon: 'pi pi-stop' },
    { label: 'Spacious', value: 'large', icon: 'pi pi-circle' }
  ];

  // Custom breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', icon: 'pi pi-home', url: '/' },
    { label: 'Templates', icon: 'pi pi-file-text' }
  ];

  const breadcrumbHome = { 
    icon: 'pi pi-home', 
    url: '/',
    'aria-label': 'Navigate to Dashboard'
  };

  // Bulk action menu items
  const bulkActionItems = useMemo(() => 
    config.availableBulkActions.map(action => ({
      label: action.label,
      icon: action.icon,
      command: () => {
        if (action.confirmMessage) {
          // Could show confirmation dialog here
          console.log('Confirm:', action.confirmMessage);
        }
        enhancedActions.performBulkAction(action, selection.selectedTemplates);
      },
      disabled: action.disabled?.(selection.selectedTemplates, []) || false,
      className: action.severity === 'danger' ? 'text-red-500' : ''
    }))
  , [config.availableBulkActions, enhancedActions, selection.selectedTemplates]);

  // Handle layout change
  const handleLayoutChange = useCallback((newLayout: Partial<TemplateGridLayout>) => {
    enhancedActions.setViewPreferences({
      layout: { ...viewPreferences.layout, ...newLayout }
    });
  }, [enhancedActions, viewPreferences.layout]);

  // Handle sort change
  const handleSortChange = useCallback((sortValue: string) => {
    const [field, order] = sortValue.split('_');
    actions.setSorting({
      sortBy: field,
      sortOrder: order as 'asc' | 'desc'
    });
  }, [actions]);

  // Current sort value
  const currentSortValue = `${sorting.sortBy}_${sorting.sortOrder}`;

  // View type toggle
  const handleViewTypeChange = useCallback((type: 'grid' | 'list') => {
    handleLayoutChange({ type });
  }, [handleLayoutChange]);

  // Toolbar start section
  const toolbarStart = () => (
    <div className="toolbar-start">
      {/* Custom Breadcrumb */}
      {showBreadcrumb && (
        <div className="breadcrumb-section">
          <nav className="template-breadcrumb flex align-items-center">
            <Button
              icon="pi pi-home"
              className="p-button-text p-button-sm"
              tooltip="Dashboard"
              onClick={() => window.location.href = '/'}
            />
            <i className="pi pi-angle-right mx-2 text-500"></i>
            <span className="flex align-items-center">
              <i className="pi pi-file-text mr-2"></i>
              Templates
            </span>
          </nav>
        </div>
      )}

      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">
          <i className="pi pi-file-text page-title-icon" />
          Template Library
        </h1>
        <div className="page-stats">
          <Badge 
            value={hasActiveFilters ? `${totalRecords} filtered` : totalRecords} 
            className="templates-count" 
            severity={hasActiveFilters ? 'info' : undefined}
          />
          <span className="templates-label">templates available</span>
        </div>
      </div>

      {/* Selection info */}
      {hasSelection && (
        <div className="selection-info">
          <Badge value={selection.selectedTemplates.length} severity="info" className="selection-count" />
          <span className="selection-text">
            {selection.selectedTemplates.length === 1 ? 'template' : 'templates'} selected
          </span>
        </div>
      )}
    </div>
  );

  // Toolbar center section
  const toolbarCenter = () => (
    <div className="toolbar-center">
      {showViewControls && (
        <div className="view-controls-group">
          {/* View type toggle */}
          <div className="view-mode-toggle">
            <Button
              icon="pi pi-th-large"
              className={`view-toggle-btn ${viewPreferences.layout.type === 'grid' ? 'p-button-raised' : 'p-button-outlined'}`}
              onClick={() => handleViewTypeChange('grid')}
              tooltip="Grid view"
              size="small"
              aria-pressed={viewPreferences.layout.type === 'grid'}
            />
            <Button
              icon="pi pi-list"
              className={`view-toggle-btn ${viewPreferences.layout.type === 'list' ? 'p-button-raised' : 'p-button-outlined'}`}
              onClick={() => handleViewTypeChange('list')}
              tooltip="List view"
              size="small"
              aria-pressed={viewPreferences.layout.type === 'list'}
            />
          </div>

          {/* Grid size control (only for grid view) */}
          {viewPreferences.layout.type === 'grid' && (
            <div className="grid-size-control">
              <Dropdown
                value={viewPreferences.layout.size}
                onChange={(e) => handleLayoutChange({ size: e.value })}
                options={sizeOptions}
                optionLabel="label"
                className="size-dropdown"
                tooltip="Card size"
              />
            </div>
          )}

          {/* View options toggles */}
          <div className="view-options">
            <ToggleButton
              checked={viewPreferences.showThumbnails}
              onChange={(e) => enhancedActions.setViewPreferences({ showThumbnails: e.value })}
              onIcon="pi pi-image"
              offIcon="pi pi-image"
              className="option-toggle"
              tooltip={`${viewPreferences.showThumbnails ? 'Hide' : 'Show'} thumbnails`}
              size="small"
            />
            <ToggleButton
              checked={viewPreferences.showMetadata}
              onChange={(e) => enhancedActions.setViewPreferences({ showMetadata: e.value })}
              onIcon="pi pi-info-circle"
              offIcon="pi pi-info-circle"
              className="option-toggle"
              tooltip={`${viewPreferences.showMetadata ? 'Hide' : 'Show'} metadata`}
              size="small"
            />
            {config.enableVirtualScrolling && (
              <ToggleButton
                checked={viewPreferences.groupByCategory}
                onChange={(e) => enhancedActions.setViewPreferences({ groupByCategory: e.value })}
                onIcon="pi pi-objects-column"
                offIcon="pi pi-objects-column"
                className="option-toggle"
                tooltip={`${viewPreferences.groupByCategory ? 'Ungroup' : 'Group'} by category`}
                size="small"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );

  // Toolbar end section
  const toolbarEnd = () => (
    <div className="toolbar-end">
      {/* Sort controls */}
      {showSortControls && (
        <div className="sort-control-group">
          <label className="sort-label">Sort by:</label>
          <Dropdown
            value={currentSortValue}
            onChange={(e) => handleSortChange(e.value)}
            options={sortOptions}
            optionLabel="label"
            className="sort-dropdown"
            placeholder="Sort options"
            tooltip="Choose sort order"
          />
        </div>
      )}

      {/* Bulk actions */}
      {hasSelection && bulkActionItems.length > 0 && (
        <div className="bulk-actions-group">
          <SplitButton
            label={`Actions (${selection.selectedTemplates.length})`}
            icon="pi pi-cog"
            model={bulkActionItems}
            className="bulk-actions-btn"
            size="small"
            severity="secondary"
          />
        </div>
      )}

      {/* Filter reset */}
      {hasActiveFilters && (
        <Button
          label="Clear Filters"
          icon="pi pi-filter-slash"
          className="p-button-outlined clear-filters-btn"
          onClick={actions.clearFilters}
          size="small"
          tooltip="Remove all active filters"
        />
      )}

      {/* Primary action */}
      {(primaryAction || showCreateButton) && (
        <div className="primary-action">
          <EnhancedButton
            label={primaryAction?.label || "Create Template"}
            icon={primaryAction?.icon || "pi pi-plus"}
            onClick={primaryAction?.onClick || onCreateTemplate}
            className="create-template-btn"
            size="small"
          />
        </div>
      )}
    </div>
  );

  return (
    <div className={`template-toolbar-container ${className}`}>
      <Toolbar
        className="template-toolbar enhanced"
        start={toolbarStart}
        center={toolbarCenter}
        end={toolbarEnd}
      />
    </div>
  );
};

export default React.memo(TemplateToolbar);