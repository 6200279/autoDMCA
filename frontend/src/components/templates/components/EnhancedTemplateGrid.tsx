import React, { useState, useMemo, useCallback, useRef, useEffect, useId } from 'react';
import { Skeleton } from 'primereact/skeleton';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { EmptyState } from '../../common/EmptyStates';
import { useTemplateLibraryContext } from '../context/TemplateLibraryContext';
import { useVirtualGrid } from '../hooks/useVirtualGrid';
import { TemplateGridProps, TemplateGridLayout } from '../types/enhanced';
import EnhancedTemplateCard from './EnhancedTemplateCard';
import { useAccessibility } from '../../../hooks/useAccessibility';

interface EnhancedTemplateGridProps extends Omit<TemplateGridProps, 'templates'> {
  enableKeyboardNavigation?: boolean;
  enableDragAndDrop?: boolean;
  showSelectionControls?: boolean;
  groupByCategory?: boolean;
  masonry?: boolean;
  className?: string;
}

const EnhancedTemplateGrid: React.FC<EnhancedTemplateGridProps> = ({
  layout,
  loading = false,
  virtualScrolling = false,
  containerHeight = 600,
  enableKeyboardNavigation = true,
  enableDragAndDrop = false,
  showSelectionControls = true,
  groupByCategory = false,
  masonry = false,
  emptyStateProps,
  onTemplateClick,
  onSelectionChange,
  className = ''
}) => {
  const {
    templates,
    loading: contextLoading,
    actions,
    selection,
    isAllSelected,
    hasSelection,
    selectedTemplates,
    config,
    viewPreferences,
    enhancedActions
  } = useTemplateLibraryContext();

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const gridId = useId();
  const accessibility = useAccessibility({ announcements: true });

  // Use loading state from context if not explicitly provided
  const isLoading = loading || contextLoading;

  // Calculate grid dimensions
  const gridDimensions = useMemo(() => {
    let itemMinWidth = 280;
    let itemHeight = 320;
    let gap = 16;

    switch (layout.size) {
      case 'small':
        itemMinWidth = 240;
        itemHeight = 280;
        gap = 12;
        break;
      case 'medium':
        itemMinWidth = 320;
        itemHeight = 360;
        gap = 16;
        break;
      case 'large':
        itemMinWidth = 380;
        itemHeight = 420;
        gap = 20;
        break;
    }

    return { itemMinWidth, itemHeight, gap };
  }, [layout.size]);

  // Virtual grid hook for performance
  const virtualGrid = useVirtualGrid({
    itemCount: templates.length,
    containerHeight: containerSize.height || containerHeight,
    containerWidth: containerSize.width,
    itemMinWidth: gridDimensions.itemMinWidth,
    itemHeight: gridDimensions.itemHeight,
    gap: gridDimensions.gap,
    overscan: 5
  });

  // Resize observer for container
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerSize({ width, height });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Group templates by category if enabled
  const groupedTemplates = useMemo(() => {
    if (!groupByCategory) {
      return { ungrouped: templates };
    }

    return templates.reduce((groups, template) => {
      const category = template.category || 'Uncategorized';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(template);
      return groups;
    }, {} as Record<string, typeof templates>);
  }, [templates, groupByCategory]);

  // Handle template click with analytics
  const handleTemplateClick = useCallback((template: typeof templates[0], index: number) => {
    // Mark as recently viewed
    enhancedActions.markAsViewed(template.id);
    
    // Announce template selection
    accessibility.announce(`Selected template: ${template.name}`);
    
    // Track interaction
    if (config.enableAnalytics) {
      enhancedActions.trackEvent({
        type: 'view_change',
        payload: { templateId: template.id, action: 'click' },
        timestamp: new Date().toISOString()
      });
    }
    
    setFocusedIndex(index);
    onTemplateClick?.(template);
  }, [enhancedActions, config.enableAnalytics, onTemplateClick, accessibility]);

  // Handle selection change
  const handleSelectionChange = useCallback((templateId: string, selected: boolean) => {
    const template = templates.find(t => t.id === templateId);
    actions.toggleTemplateSelection(templateId, selected);
    
    // Announce selection change
    if (template) {
      accessibility.announce(
        `Template ${template.name} ${selected ? 'selected' : 'deselected'}. ${selection.selectedTemplates.length} templates selected.`,
        'assertive'
      );
    }
    
    onSelectionChange?.(selection.selectedTemplates);
  }, [actions, onSelectionChange, templates, accessibility]);

  // Handle select all
  const handleSelectAll = useCallback((selected: boolean) => {
    actions.selectAllTemplates(selected);
    
    // Announce bulk selection change
    accessibility.announce(
      `${selected ? 'Selected all' : 'Deselected all'} ${templates.length} templates`,
      'assertive'
    );
    
    onSelectionChange?.(selected ? templates.map(t => t.id) : []);
  }, [actions, templates, onSelectionChange, accessibility]);

  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNavigation || !containerRef.current) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!templates.length || focusedIndex < 0) return;

      const columns = virtualGrid.columnsCount || 1;
      let newIndex = focusedIndex;

      switch (e.key) {
        case 'ArrowLeft':
          newIndex = Math.max(0, focusedIndex - 1);
          break;
        case 'ArrowRight':
          newIndex = Math.min(templates.length - 1, focusedIndex + 1);
          break;
        case 'ArrowUp':
          newIndex = Math.max(0, focusedIndex - columns);
          break;
        case 'ArrowDown':
          newIndex = Math.min(templates.length - 1, focusedIndex + columns);
          break;
        case 'Home':
          newIndex = 0;
          break;
        case 'End':
          newIndex = templates.length - 1;
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          handleTemplateClick(templates[focusedIndex], focusedIndex);
          return;
        default:
          return;
      }

      if (newIndex !== focusedIndex) {
        e.preventDefault();
        setFocusedIndex(newIndex);
      }
    };

    const container = containerRef.current;
    container.addEventListener('keydown', handleKeyDown);
    container.setAttribute('tabindex', '0');

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [enableKeyboardNavigation, focusedIndex, templates, virtualGrid.columnsCount, handleTemplateClick]);

  // Render loading skeleton
  const renderLoadingSkeleton = () => {
    const skeletonCount = Math.min(20, Math.max(8, Math.floor(containerSize.width / gridDimensions.itemMinWidth) * 3));
    
    return (
      <div 
        className="templates-loading-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fill, minmax(${gridDimensions.itemMinWidth}px, 1fr))`,
          gap: `${gridDimensions.gap}px`,
          padding: `${gridDimensions.gap}px`
        }}
      >
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <div key={index} className="template-skeleton">
            <Skeleton height={`${gridDimensions.itemHeight}px`} borderRadius="8px" />
          </div>
        ))}
      </div>
    );
  };

  // Render empty state
  const renderEmptyState = () => (
    <EmptyState
      variant="search"
      title={emptyStateProps?.title || "No templates found"}
      description={emptyStateProps?.description || "Try adjusting your filters or search terms."}
      primaryAction={emptyStateProps?.action}
    />
  );

  // Render virtual grid
  const renderVirtualGrid = () => {
    if (!virtualGrid.visibleItems.length) return null;

    return (
      <div
        style={virtualGrid.gridStyle}
        className="virtual-template-grid"
        onScroll={virtualGrid.handleScroll}
      >
        <div style={virtualGrid.containerStyle}>
          {virtualGrid.visibleItems.map(({ index, x, y, width, height }) => {
            const template = templates[index];
            if (!template) return null;

            return (
              <div
                key={template.id}
                style={{
                  position: 'absolute',
                  left: x,
                  top: y,
                  width: width,
                  height: height
                }}
              >
                <EnhancedTemplateCard
                  template={template}
                  selected={selection.selectedTemplates.includes(template.id)}
                  showCheckbox={hasSelection || showSelectionControls}
                  onSelectionChange={handleSelectionChange}
                  onClick={() => handleTemplateClick(template, index)}
                  focused={focusedIndex === index}
                  layout={layout}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Render regular grid
  const renderRegularGrid = () => {
    const gridStyle: React.CSSProperties = {
      display: 'grid',
      gap: `${gridDimensions.gap}px`,
      padding: `${gridDimensions.gap}px`
    };

    if (layout.type === 'masonry' || masonry) {
      // Masonry layout using CSS Grid
      gridStyle.gridTemplateColumns = `repeat(auto-fill, minmax(${gridDimensions.itemMinWidth}px, 1fr))`;
      gridStyle.gridAutoRows = 'max-content';
    } else {
      // Regular grid
      gridStyle.gridTemplateColumns = `repeat(auto-fill, minmax(${gridDimensions.itemMinWidth}px, 1fr))`;
    }

    if (groupByCategory) {
      return (
        <div className="grouped-templates-grid">
          {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
            <div key={category} className="template-category-group">
              <h3 className="category-group-header">
                <i className="pi pi-tag" />
                {category}
                <span className="category-count">({categoryTemplates.length})</span>
              </h3>
              <div style={gridStyle} className="category-templates-grid">
                {categoryTemplates.map((template, index) => (
                  <EnhancedTemplateCard
                    key={template.id}
                    template={template}
                    selected={selection.selectedTemplates.includes(template.id)}
                    showCheckbox={hasSelection || showSelectionControls}
                    onSelectionChange={handleSelectionChange}
                    onClick={() => handleTemplateClick(template, index)}
                    focused={focusedIndex === index}
                    layout={layout}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div style={gridStyle} className="templates-regular-grid">
        {templates.map((template, index) => (
          <EnhancedTemplateCard
            key={template.id}
            template={template}
            selected={selection.selectedTemplates.includes(template.id)}
            showCheckbox={hasSelection || showSelectionControls}
            onSelectionChange={handleSelectionChange}
            onClick={() => handleTemplateClick(template, index)}
            focused={focusedIndex === index}
            layout={layout}
          />
        ))}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div ref={containerRef} className={`template-grid-container loading ${className}`}>
        {renderLoadingSkeleton()}
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div ref={containerRef} className={`template-grid-container empty ${className}`}>
        {renderEmptyState()}
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`template-grid-container ${className}`}>
      {/* Selection Controls */}
      {showSelectionControls && hasSelection && (
        <div className="grid-selection-controls" role="toolbar" aria-label="Template selection controls">
          <div className="selection-info">
            <Checkbox
              checked={isAllSelected}
              indeterminate={hasSelection && !isAllSelected}
              onChange={(e) => handleSelectAll(e.checked || false)}
              className="select-all-checkbox"
              aria-label={`Select all ${templates.length} templates`}
              aria-describedby="selection-description"
            />
            <span className="selection-text" id="selection-description">
              {isAllSelected ? 'All' : selectedTemplates.length} of {templates.length} selected
            </span>
            <Button
              label="Clear Selection"
              icon="pi pi-times"
              className="p-button-text p-button-sm clear-selection-btn"
              onClick={() => handleSelectAll(false)}
              aria-describedby="selection-description"
            />
          </div>
        </div>
      )}

      {/* Grid Content */}
      <div 
        className="grid-content"
        role="grid"
        aria-label={`Template library with ${templates.length} templates`}
        aria-rowcount={Math.ceil(templates.length / (virtualGrid.columnsCount || 1))}
        aria-colcount={virtualGrid.columnsCount || 1}
        aria-multiselectable={showSelectionControls}
        aria-activedescendant={focusedIndex >= 0 ? `template-${templates[focusedIndex]?.id}` : undefined}
        tabIndex={0}
        onFocus={() => {
          if (focusedIndex < 0 && templates.length > 0) {
            setFocusedIndex(0);
          }
        }}
      >
        {virtualScrolling && config.enableVirtualScrolling ? 
          renderVirtualGrid() : 
          renderRegularGrid()
        }
      </div>
    </div>
  );
};

export default React.memo(EnhancedTemplateGrid);