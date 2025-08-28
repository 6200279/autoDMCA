import React, { useState, useMemo, useCallback, useRef, Suspense, useEffect } from 'react';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Sidebar } from 'primereact/sidebar';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Button } from 'primereact/button';
import { Paginator } from 'primereact/paginator';
import ErrorBoundary from '../common/ErrorBoundary';
import { TemplateLibraryProvider, useTemplateLibraryContext } from './context/TemplateLibraryContext';
import { TemplateAction, BulkAction } from './types/enhanced';
import { useAccessibility } from '../../hooks/useAccessibility';

// Lazy load components for better performance
const EnhancedTemplateSearch = React.lazy(() => import('./components/EnhancedTemplateSearch'));
const TemplateFilters = React.lazy(() => import('./components/TemplateFilters'));
const EnhancedTemplateGrid = React.lazy(() => import('./components/EnhancedTemplateGrid'));
const TemplateToolbar = React.lazy(() => import('./components/TemplateToolbar'));

import './EnhancedTemplateLibraryDashboard.css';
import './accessibility.css';

interface EnhancedTemplateLibraryDashboardProps {
  onTemplateEdit?: (template: any) => void;
  onTemplateCreate?: () => void;
  onTemplateView?: (template: any) => void;
  customActions?: TemplateAction[];
  customBulkActions?: BulkAction[];
  enableVirtualScrolling?: boolean;
  enableAnalytics?: boolean;
  className?: string;
}

// Internal dashboard component that uses the context
const EnhancedDashboardContent: React.FC<{
  onTemplateEdit?: (template: any) => void;
  onTemplateView?: (template: any) => void;
  onTemplateCreate?: () => void;
}> = ({
  onTemplateEdit,
  onTemplateView,
  onTemplateCreate
}) => {
  const {
    templates,
    loading,
    error,
    totalRecords,
    filters,
    pagination,
    viewPreferences,
    hasActiveFilters,
    hasSelection,
    selectedTemplates,
    actions,
    enhancedActions,
    config
  } = useTemplateLibraryContext();

  const [showFilters, setShowFilters] = useState(true);
  const [mobileFiltersVisible, setMobileFiltersVisible] = useState(false);
  const [confirmDialogVisible, setConfirmDialogVisible] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState<{
    action: BulkAction;
    templateIds: string[];
  } | null>(null);

  const toast = useRef<Toast>(null);
  
  // Accessibility hooks
  const accessibility = useAccessibility({
    announcements: true,
    keyboardShortcuts: true,
    focusManagement: true,
    highContrast: true
  });

  // Register keyboard shortcuts
  useEffect(() => {
    const shortcuts = [
      accessibility.keyboard.registerShortcut('ctrl+/', () => {
        const searchInput = document.querySelector('[aria-label="Search templates"]') as HTMLElement;
        accessibility.manageFocus.moveTo(searchInput);
      }, 'Focus search'),
      
      accessibility.keyboard.registerShortcut('ctrl+f', () => {
        const filtersSection = document.getElementById('filters-section');
        accessibility.manageFocus.moveTo(filtersSection);
      }, 'Focus filters'),
      
      accessibility.keyboard.registerShortcut('ctrl+n', () => {
        onTemplateCreate?.();
      }, 'Create new template'),
      
      accessibility.keyboard.registerShortcut('ctrl+r', () => {
        enhancedActions.refreshData();
        accessibility.announce('Templates refreshed');
      }, 'Refresh templates'),
      
      accessibility.keyboard.registerShortcut('escape', () => {
        if (mobileFiltersVisible) {
          setMobileFiltersVisible(false);
          accessibility.manageFocus.restore();
        }
      }, 'Close dialogs')
    ];

    return () => {
      shortcuts.forEach(cleanup => cleanup());
    };
  }, [accessibility, onTemplateCreate, enhancedActions, mobileFiltersVisible]);

  // Handle template actions
  const handleTemplateClick = useCallback((template: any) => {
    enhancedActions.markAsViewed(template.id);
    onTemplateView?.(template);
  }, [enhancedActions, onTemplateView]);

  const handleTemplateEdit = useCallback((template: any) => {
    enhancedActions.markAsViewed(template.id);
    onTemplateEdit?.(template);
  }, [enhancedActions, onTemplateEdit]);

  // Handle bulk actions with confirmation
  const handleBulkAction = useCallback(async (actionId: string, templateIds: string[]) => {
    const action = config.availableBulkActions.find(a => a.id === actionId);
    if (!action) return;

    if (action.confirmMessage) {
      setPendingBulkAction({ action, templateIds });
      setConfirmDialogVisible(true);
    } else {
      try {
        await enhancedActions.performBulkAction(action, templateIds);
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: `${action.label} completed successfully`
        });
        accessibility.announce(`${action.label} completed successfully`, 'assertive');
      } catch (error) {
        toast.current?.show({
          severity: 'error',
          summary: 'Error',
          detail: `Failed to ${action.label.toLowerCase()}`
        });
      }
    }
  }, [config.availableBulkActions, enhancedActions]);

  // Confirm bulk action
  const confirmBulkAction = useCallback(async () => {
    if (!pendingBulkAction) return;

    try {
      await enhancedActions.performBulkAction(pendingBulkAction.action, pendingBulkAction.templateIds);
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `${pendingBulkAction.action.label} completed successfully`
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: `Failed to ${pendingBulkAction.action.label.toLowerCase()}`
      });
    } finally {
      setConfirmDialogVisible(false);
      setPendingBulkAction(null);
    }
  }, [pendingBulkAction, enhancedActions]);

  // Handle pagination
  const handlePageChange = useCallback((event: any) => {
    actions.setPagination({
      first: event.first,
      rows: event.rows
    });
  }, [actions]);

  // Error handling
  const handleError = useCallback((error: Error) => {
    console.error('Template library error:', error);
    toast.current?.show({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'An unexpected error occurred'
    });
  }, []);

  // Layout calculations
  const containerHeight = useMemo(() => {
    // Calculate available height for the grid
    const headerHeight = 120;
    const toolbarHeight = 80;
    const paginationHeight = 60;
    return window.innerHeight - headerHeight - toolbarHeight - paginationHeight;
  }, []);

  // Render loading spinner
  const LoadingSpinner = () => (
    <div className="loading-container">
      <ProgressSpinner size="50px" />
      <p>Loading templates...</p>
    </div>
  );

  // Render error state
  const ErrorState = () => (
    <div className="error-container">
      <i className="pi pi-exclamation-triangle error-icon" />
      <h3>Error Loading Templates</h3>
      <p>{error}</p>
      <Button
        label="Retry"
        icon="pi pi-refresh"
        onClick={() => enhancedActions.refreshData()}
        className="retry-btn"
      />
    </div>
  );

  if (error) {
    return <ErrorState />;
  }

  return (
    <div className="enhanced-template-library-dashboard">
      <Toast ref={toast} />
      
      {/* Confirm Dialog */}
      <ConfirmDialog
        visible={confirmDialogVisible}
        onHide={() => setConfirmDialogVisible(false)}
        message={pendingBulkAction?.action.confirmMessage}
        header="Confirm Action"
        icon="pi pi-exclamation-triangle"
        accept={confirmBulkAction}
        reject={() => {
          setConfirmDialogVisible(false);
          setPendingBulkAction(null);
        }}
      />

      {/* Enhanced Skip Navigation Links */}
      <div className="skip-links" role="navigation" aria-label="Skip navigation">
        <a 
          href="#toolbar-section" 
          className="skip-link"
          onFocus={() => accessibility.announce('Skip to toolbar section')}
        >
          Skip to toolbar
        </a>
        <a 
          href="#search-section" 
          className="skip-link"
          onFocus={() => accessibility.announce('Skip to search section')}
        >
          Skip to search
        </a>
        <a 
          href="#filters-section" 
          className="skip-link"
          onFocus={() => accessibility.announce('Skip to filters section')}
        >
          Skip to filters
        </a>
        <a 
          href="#templates-section" 
          className="skip-link"
          onFocus={() => accessibility.announce('Skip to templates grid')}
        >
          Skip to templates
        </a>
        <button
          className="skip-link keyboard-shortcuts-trigger"
          onClick={() => {
            const shortcuts = accessibility.keyboard.getShortcuts();
            const shortcutsList = shortcuts.map(s => `${s.key}: ${s.description}`).join(', ');
            accessibility.announce(`Available keyboard shortcuts: ${shortcutsList}`, 'assertive');
          }}
        >
          Show keyboard shortcuts
        </button>
      </div>

      {/* Main Layout */}
      <main className="dashboard-layout enhanced" role="main" aria-label="Template Library Dashboard">
        {/* Toolbar */}
        <section id="toolbar-section" role="banner" aria-label="Template Library Toolbar">
          <Suspense fallback={<LoadingSpinner />}>
            <TemplateToolbar
              totalCount={totalRecords}
              selectedCount={selectedTemplates.length}
              onCreateTemplate={onTemplateCreate}
              onBulkAction={handleBulkAction}
              showBreadcrumb={true}
              showViewControls={true}
              showSortControls={true}
              showCreateButton={true}
            />
          </Suspense>
        </section>

        {/* Content Area */}
        <div className="dashboard-content enhanced" role="region" aria-label="Template Library Content">
          {showFilters ? (
            <Splitter className="enhanced-splitter" layout="horizontal">
              {/* Filters Panel */}
              <SplitterPanel 
                size={25} 
                minSize={20} 
                maxSize={40} 
                className="filters-panel-container"
              >
                <aside className="filters-panel enhanced" role="complementary" aria-label="Template Filters and Search">
                  <section id="search-section" role="search" aria-label="Template Search">
                    <Suspense fallback={<LoadingSpinner />}>
                      <EnhancedTemplateSearch
                        value={filters.search}
                        showAdvancedSearch={true}
                        showSearchHistory={true}
                        showQuickFilters={true}
                      />
                    </Suspense>
                  </section>
                  
                  <section id="filters-section" role="region" aria-label="Template Filters">
                    <Suspense fallback={<LoadingSpinner />}>
                      <TemplateFilters
                        showAsPanel={true}
                        showPresets={true}
                        showAdvancedFilters={true}
                        collapsible={false}
                      />
                    </Suspense>
                  </section>
                </aside>
              </SplitterPanel>

              {/* Templates Panel */}
              <SplitterPanel size={75} className="templates-panel-container">
                <section className="templates-panel enhanced" id="templates-section" role="region" aria-label="Template Grid">
                  <ErrorBoundary onError={handleError}>
                    <Suspense fallback={<LoadingSpinner />}>
                      <EnhancedTemplateGrid
                        layout={viewPreferences.layout}
                        loading={loading}
                        virtualScrolling={config.enableVirtualScrolling}
                        containerHeight={containerHeight}
                        enableKeyboardNavigation={true}
                        enableDragAndDrop={false}
                        showSelectionControls={true}
                        groupByCategory={viewPreferences.groupByCategory}
                        masonry={viewPreferences.layout.type === 'masonry'}
                        onTemplateClick={handleTemplateClick}
                        onSelectionChange={(selectedIds) => {
                          // Selection is managed by context
                        }}
                        emptyStateProps={{
                          title: hasActiveFilters ? "No templates match your filters" : "No templates found",
                          description: hasActiveFilters 
                            ? "Try adjusting your search terms or filters." 
                            : "Get started by creating your first DMCA template.",
                          action: {
                            label: "Create Template",
                            onClick: onTemplateCreate || (() => {})
                          }
                        }}
                      />
                    </Suspense>
                  </ErrorBoundary>

                  {/* Pagination */}
                  {totalRecords > pagination.rows && (
                    <div className="template-pagination enhanced">
                      <div className="pagination-info">
                        <span className="pagination-summary">
                          Showing {pagination.first + 1} to {Math.min(pagination.first + pagination.rows, totalRecords)} of {totalRecords} templates
                        </span>
                      </div>
                      <Paginator
                        first={pagination.first}
                        rows={pagination.rows}
                        totalRecords={totalRecords}
                        rowsPerPageOptions={[12, 20, 36, 48, 60]}
                        onPageChange={handlePageChange}
                        template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
                        className="enhanced-paginator"
                        leftContent={
                          <Button
                            icon="pi pi-refresh"
                            className="p-button-text refresh-btn"
                            onClick={() => enhancedActions.refreshData()}
                            tooltip="Refresh templates"
                          />
                        }
                      />
                    </div>
                  )}
                </section>
              </SplitterPanel>
            </Splitter>
          ) : (
            /* Full Width Layout */
            <div className="templates-full-panel enhanced">
              <div id="search-section" className="search-bar-inline">
                <Suspense fallback={<LoadingSpinner />}>
                  <EnhancedTemplateSearch
                    value={filters.search}
                    showAdvancedSearch={true}
                    showSearchHistory={true}
                    showQuickFilters={true}
                  />
                </Suspense>
              </div>

              <div id="templates-section" className="templates-content-full">
                <ErrorBoundary onError={handleError}>
                  <Suspense fallback={<LoadingSpinner />}>
                    <EnhancedTemplateGrid
                      layout={viewPreferences.layout}
                      loading={loading}
                      virtualScrolling={config.enableVirtualScrolling}
                      containerHeight={containerHeight}
                      enableKeyboardNavigation={true}
                      showSelectionControls={true}
                      groupByCategory={viewPreferences.groupByCategory}
                      onTemplateClick={handleTemplateClick}
                      emptyStateProps={{
                        title: hasActiveFilters ? "No templates match your filters" : "No templates found",
                        description: hasActiveFilters 
                          ? "Try adjusting your search terms or filters." 
                          : "Get started by creating your first DMCA template.",
                        action: {
                          label: "Create Template",
                          onClick: onTemplateCreate || (() => {})
                        }
                      }}
                    />
                  </Suspense>
                </ErrorBoundary>

                {/* Pagination */}
                {totalRecords > pagination.rows && (
                  <div className="template-pagination enhanced">
                    <Paginator
                      first={pagination.first}
                      rows={pagination.rows}
                      totalRecords={totalRecords}
                      rowsPerPageOptions={[12, 20, 36, 48, 60]}
                      onPageChange={handlePageChange}
                      template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
                      className="enhanced-paginator"
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Mobile Filters Toggle */}
        <Button
          icon="pi pi-filter"
          className="mobile-filters-toggle p-button-raised"
          onClick={() => {
            accessibility.manageFocus.saveFocus();
            setMobileFiltersVisible(true);
            accessibility.announce('Filters panel opened', 'assertive');
          }}
          tooltip="Show filters"
          aria-label="Open filters panel"
          style={{ 
            position: 'fixed', 
            bottom: '20px', 
            right: '20px', 
            zIndex: 1000,
            display: window.innerWidth <= 768 ? 'block' : 'none'
          }}
        />

        {/* Mobile Filters Sidebar */}
        <Sidebar
          visible={mobileFiltersVisible}
          onHide={() => {
            setMobileFiltersVisible(false);
            accessibility.manageFocus.restore();
            accessibility.announce('Filters panel closed');
          }}
          className="mobile-filters-sidebar"
          position="left"
          style={{ width: '90vw', maxWidth: '400px' }}
          role="dialog"
          aria-label="Mobile Filters"
          aria-modal="true"
        >
          <div className="mobile-filters-content" role="region" aria-label="Filter Controls">
            <Suspense fallback={<LoadingSpinner />}>
              <EnhancedTemplateSearch
                value={filters.search}
                showAdvancedSearch={true}
                showSearchHistory={true}
                showQuickFilters={true}
              />
              <TemplateFilters
                showPresets={true}
                showAdvancedFilters={true}
                collapsible={false}
              />
            </Suspense>
          </div>
        </Sidebar>
      </main>
    </div>
  );
};

// Main component with context provider
const EnhancedTemplateLibraryDashboard: React.FC<EnhancedTemplateLibraryDashboardProps> = ({
  onTemplateEdit,
  onTemplateCreate,
  onTemplateView,
  customActions = [],
  customBulkActions = [],
  enableVirtualScrolling = true,
  enableAnalytics = true,
  className = ''
}) => {
  const handleTemplateEvent = useCallback((event: any) => {
    // Handle template library events (analytics, logging, etc.)
    if (enableAnalytics) {
      console.log('Template library event:', event);
      // Could send to analytics service
    }
  }, [enableAnalytics]);

  return (
    <div className={`enhanced-template-library-wrapper ${className}`}>
      <TemplateLibraryProvider
        enableVirtualScrolling={enableVirtualScrolling}
        enableAnalytics={enableAnalytics}
        customActions={customActions}
        customBulkActions={customBulkActions}
        onTemplateEvent={handleTemplateEvent}
      >
        <EnhancedDashboardContent
          onTemplateEdit={onTemplateEdit}
          onTemplateView={onTemplateView}
          onTemplateCreate={onTemplateCreate}
        />
      </TemplateLibraryProvider>
    </div>
  );
};

export default React.memo(EnhancedTemplateLibraryDashboard);