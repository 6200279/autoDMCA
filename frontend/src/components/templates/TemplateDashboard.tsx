import React, { useState, useEffect, useCallback, useRef } from 'react';
import { DataView } from 'primereact/dataview';
import { Panel } from 'primereact/panel';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Menu } from 'primereact/menu';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Dialog } from 'primereact/dialog';
import { Paginator } from 'primereact/paginator';
import { Skeleton } from 'primereact/skeleton';
import { EnhancedCard } from '../common/EnhancedCard';
import { EnhancedButton } from '../common/EnhancedButton';
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
import './TemplateDashboard.css';

interface TemplateDashboardProps {
  onTemplateEdit?: (template: DMCATemplate) => void;
  onTemplateCreate?: () => void;
  onTemplateView?: (template: DMCATemplate) => void;
}

const TemplateDashboard: React.FC<TemplateDashboardProps> = ({
  onTemplateEdit,
  onTemplateCreate,
  onTemplateView
}) => {
  const [templates, setTemplates] = useState<DMCATemplate[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [first, setFirst] = useState(0);
  const [rows, setRows] = useState(12);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [layout, setLayout] = useState<'grid' | 'list'>('grid');
  
  // State management
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [actionType, setActionType] = useState<'delete' | 'activate' | 'deactivate'>('delete');
  
  const toast = useRef<Toast>(null);
  const menuRef = useRef<Menu>(null);

  // Fetch templates with current filters
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const params: TemplateListParams = {
        page: Math.floor(first / rows) + 1,
        limit: rows,
        search: searchTerm || undefined,
        category: selectedCategory || undefined,
        language: selectedLanguage || undefined,
        jurisdiction: selectedJurisdiction || undefined,
        is_active: activeFilter === 'active' ? true : activeFilter === 'inactive' ? false : undefined,
        sort_by: sortBy as any,
        sort_order: sortOrder,
      };

      const response = await templatesApi.getTemplates(params);
      const data: PaginatedTemplatesResponse = response.data;
      
      setTemplates(data.templates);
      setTotalRecords(data.total);
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
  }, [first, rows, searchTerm, selectedCategory, selectedLanguage, selectedJurisdiction, activeFilter, sortBy, sortOrder]);

  // Fetch categories
  const fetchCategories = useCallback(async () => {
    try {
      const response = await templatesApi.getCategories();
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
      // Fallback to default categories
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

  // Handle search with debounce
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setFirst(0); // Reset pagination when search changes
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [searchTerm]);

  const handlePageChange = (event: any) => {
    setFirst(event.first);
    setRows(event.rows);
  };

  const handleDuplicate = async (template: DMCATemplate) => {
    try {
      const newName = `${template.name} (Copy)`;
      await templatesApi.duplicateTemplate(template.id, newName);
      fetchTemplates();
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Template duplicated successfully'
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to duplicate template'
      });
    }
  };

  const handleDelete = async (template: DMCATemplate) => {
    try {
      await templatesApi.deleteTemplate(template.id);
      fetchTemplates();
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Template deleted successfully'
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to delete template'
      });
    }
  };

  const handleBulkAction = async () => {
    try {
      if (actionType === 'delete') {
        await templatesApi.bulkDelete(selectedTemplates);
      } else if (actionType === 'activate') {
        await templatesApi.bulkActivate(selectedTemplates);
      } else if (actionType === 'deactivate') {
        await templatesApi.bulkDeactivate(selectedTemplates);
      }
      
      fetchTemplates();
      setSelectedTemplates([]);
      setShowBulkActions(false);
      setConfirmVisible(false);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `Templates ${actionType}d successfully`
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: `Failed to ${actionType} templates`
      });
    }
  };

  const getStatusSeverity = (isActive: boolean): "success" | "secondary" | "info" | "warning" | "danger" | "contrast" => {
    return isActive ? 'success' : 'secondary';
  };

  const getCategoryColor = (category: string): string => {
    const colors = [
      'bg-blue-100 text-blue-800',
      'bg-green-100 text-green-800',
      'bg-yellow-100 text-yellow-800',
      'bg-purple-100 text-purple-800',
      'bg-pink-100 text-pink-800',
      'bg-indigo-100 text-indigo-800'
    ];
    const index = category.length % colors.length;
    return colors[index];
  };

  const renderTemplateCard = (template: DMCATemplate) => (
    <EnhancedCard 
      key={template.id}
      className="template-card h-full"
      variant="elevated"
      elevation="2"
      interactive
    >
      <div className="template-card-content h-full flex flex-column">
        <div className="template-header flex justify-content-between align-items-start mb-3">
          <div className="flex-1">
            <h3 className="template-title text-xl font-semibold mb-2 line-height-2">
              {template.name}
            </h3>
            <p className="template-description text-color-secondary text-sm mb-2 line-height-3">
              {template.description}
            </p>
          </div>
          <div className="template-actions">
            <Button
              icon="pi pi-ellipsis-v"
              className="p-button-text p-button-rounded"
              onClick={(e) => {
                const items = [
                  {
                    label: 'View',
                    icon: 'pi pi-eye',
                    command: () => onTemplateView?.(template)
                  },
                  {
                    label: 'Edit',
                    icon: 'pi pi-pencil',
                    command: () => onTemplateEdit?.(template)
                  },
                  {
                    label: 'Duplicate',
                    icon: 'pi pi-copy',
                    command: () => handleDuplicate(template)
                  },
                  { separator: true },
                  {
                    label: 'Delete',
                    icon: 'pi pi-trash',
                    command: () => handleDelete(template),
                    className: 'text-red-500'
                  }
                ];
                menuRef.current?.toggle(e);
              }}
            />
            <Menu ref={menuRef} model={[]} popup />
          </div>
        </div>

        <div className="template-meta flex-1">
          <div className="template-tags mb-3">
            <Chip
              label={template.category}
              className={`mr-2 mb-1 text-xs ${getCategoryColor(template.category)}`}
            />
            <Tag
              value={template.is_active ? 'Active' : 'Inactive'}
              severity={getStatusSeverity(template.is_active)}
              className="mr-2 mb-1"
            />
            {template.is_system && (
              <Tag value="System" severity="info" className="mr-2 mb-1" />
            )}
          </div>

          {template.tags && template.tags.length > 0 && (
            <div className="template-custom-tags mb-3">
              {template.tags.slice(0, 3).map((tag, index) => (
                <Chip
                  key={index}
                  label={tag}
                  className="mr-1 mb-1 text-xs bg-gray-100 text-gray-700"
                />
              ))}
              {template.tags.length > 3 && (
                <span className="text-xs text-color-secondary ml-1">
                  +{template.tags.length - 3} more
                </span>
              )}
            </div>
          )}

          <div className="template-info text-xs text-color-secondary">
            <div className="mb-1">
              <i className="pi pi-globe mr-2"></i>
              {template.language && SUPPORTED_LANGUAGES.find(l => l.value === template.language)?.label || 'English'}
              {template.jurisdiction && (
                <>
                  {' • '}
                  {JURISDICTIONS.find(j => j.value === template.jurisdiction)?.label || template.jurisdiction}
                </>
              )}
            </div>
            <div className="mb-1">
              <i className="pi pi-users mr-2"></i>
              Used {template.usage_count || 0} times
            </div>
            <div>
              <i className="pi pi-clock mr-2"></i>
              Updated {new Date(template.updated_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        <div className="template-footer mt-3 pt-3 border-top-1 surface-border">
          <div className="flex justify-content-between align-items-center">
            <EnhancedButton
              label="View"
              icon="pi pi-eye"
              size="small"
              variant="outlined"
              onClick={() => onTemplateView?.(template)}
            />
            <EnhancedButton
              label="Edit"
              icon="pi pi-pencil"
              size="small"
              onClick={() => onTemplateEdit?.(template)}
            />
          </div>
        </div>
      </div>
    </EnhancedCard>
  );

  const renderTemplateList = (template: DMCATemplate) => (
    <EnhancedCard key={template.id} className="template-list-item mb-3" variant="outlined">
      <div className="flex align-items-center">
        <div className="flex-1">
          <div className="flex align-items-center mb-2">
            <h4 className="template-title text-lg font-medium mr-3 mb-0">
              {template.name}
            </h4>
            <Tag
              value={template.is_active ? 'Active' : 'Inactive'}
              severity={getStatusSeverity(template.is_active)}
              className="mr-2"
            />
            {template.is_system && (
              <Tag value="System" severity="info" className="mr-2" />
            )}
          </div>
          <p className="template-description text-color-secondary mb-2">
            {template.description}
          </p>
          <div className="flex align-items-center text-sm text-color-secondary">
            <Chip
              label={template.category}
              className={`mr-2 text-xs ${getCategoryColor(template.category)}`}
            />
            <span className="mr-3">
              <i className="pi pi-users mr-1"></i>
              {template.usage_count || 0} uses
            </span>
            <span>
              <i className="pi pi-clock mr-1"></i>
              {new Date(template.updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div className="template-actions flex align-items-center ml-3">
          <EnhancedButton
            label="View"
            icon="pi pi-eye"
            size="small"
            variant="outlined"
            className="mr-2"
            onClick={() => onTemplateView?.(template)}
          />
          <EnhancedButton
            label="Edit"
            icon="pi pi-pencil"
            size="small"
            onClick={() => onTemplateEdit?.(template)}
          />
        </div>
      </div>
    </EnhancedCard>
  );

  const renderHeader = () => (
    <div className="template-dashboard-header">
      <div className="flex flex-column lg:flex-row lg:align-items-center lg:justify-content-between mb-4">
        <div className="mb-3 lg:mb-0">
          <h1 className="text-3xl font-bold mb-2">DMCA Templates</h1>
          <p className="text-color-secondary">
            Manage your DMCA takedown notice templates
          </p>
        </div>
        <div className="flex flex-column sm:flex-row align-items-stretch sm:align-items-center gap-2">
          <EnhancedButton
            label="Import Templates"
            icon="pi pi-upload"
            variant="outlined"
            onClick={() => {/* TODO: Implement import */}}
          />
          <EnhancedButton
            label="Create Template"
            icon="pi pi-plus"
            onClick={onTemplateCreate}
          />
        </div>
      </div>

      <div className="template-filters mb-4">
        <div className="flex flex-column lg:flex-row gap-3">
          <div className="flex-1">
            <span className="p-input-icon-left w-full">
              <i className="pi pi-search" />
              <InputText
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search templates..."
                className="w-full"
              />
            </span>
          </div>
          
          <div className="flex flex-column sm:flex-row gap-2">
            <Dropdown
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.value)}
              options={[
                { label: 'All Categories', value: '' },
                ...categories.map(cat => ({ label: cat.name, value: cat.name }))
              ]}
              placeholder="Category"
              className="w-full sm:w-12rem"
              showClear
            />
            
            <Dropdown
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.value)}
              options={[
                { label: 'All Languages', value: '' },
                ...SUPPORTED_LANGUAGES.map(lang => ({ label: lang.label, value: lang.value }))
              ]}
              placeholder="Language"
              className="w-full sm:w-12rem"
              showClear
            />
            
            <Dropdown
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.value)}
              options={[
                { label: 'All Templates', value: 'all' },
                { label: 'Active Only', value: 'active' },
                { label: 'Inactive Only', value: 'inactive' }
              ]}
              className="w-full sm:w-12rem"
            />
          </div>
        </div>

        <div className="flex justify-content-between align-items-center mt-3">
          <div className="flex align-items-center gap-2">
            <Button
              icon={layout === 'grid' ? 'pi pi-th-large' : 'pi pi-list'}
              className="p-button-outlined"
              onClick={() => setLayout(layout === 'grid' ? 'list' : 'grid')}
              tooltip={`Switch to ${layout === 'grid' ? 'list' : 'grid'} view`}
            />
            
            <Dropdown
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.value.split('_');
                setSortBy(field);
                setSortOrder(order);
              }}
              options={[
                { label: 'Name A-Z', value: 'name_asc' },
                { label: 'Name Z-A', value: 'name_desc' },
                { label: 'Recently Updated', value: 'updated_at_desc' },
                { label: 'Oldest Updated', value: 'updated_at_asc' },
                { label: 'Most Used', value: 'usage_count_desc' },
                { label: 'Least Used', value: 'usage_count_asc' }
              ]}
              className="w-full sm:w-12rem"
            />
          </div>
          
          {selectedTemplates.length > 0 && (
            <div className="flex align-items-center gap-2">
              <Badge value={selectedTemplates.length} className="mr-2" />
              <Button
                label="Delete Selected"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                onClick={() => {
                  setActionType('delete');
                  setConfirmVisible(true);
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (loading) {
      return (
        <div className={`grid ${layout === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4' : 'grid-cols-1'} gap-4`}>
          {Array.from({ length: rows }).map((_, index) => (
            <div key={index} className="template-skeleton">
              <Skeleton height="300px" />
            </div>
          ))}
        </div>
      );
    }

    if (templates.length === 0) {
      return (
        <div className="template-empty-state text-center py-8">
          <div className="mb-4">
            <i className="pi pi-file text-6xl text-color-secondary"></i>
          </div>
          <h3 className="text-xl font-medium mb-2">No templates found</h3>
          <p className="text-color-secondary mb-4">
            {searchTerm || selectedCategory || selectedLanguage 
              ? 'Try adjusting your filters to see more results.'
              : 'Get started by creating your first DMCA template.'}
          </p>
          <EnhancedButton
            label="Create Template"
            icon="pi pi-plus"
            onClick={onTemplateCreate}
          />
        </div>
      );
    }

    return (
      <>
        <div className={`templates-grid ${layout === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4' : ''}`}>
          {templates.map(template => 
            layout === 'grid' ? renderTemplateCard(template) : renderTemplateList(template)
          )}
        </div>
        
        <div className="template-pagination mt-6">
          <Paginator
            first={first}
            rows={rows}
            totalRecords={totalRecords}
            rowsPerPageOptions={[12, 24, 48]}
            onPageChange={handlePageChange}
            template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
            currentPageReportTemplate="Showing {first} to {last} of {totalRecords} templates"
          />
        </div>
      </>
    );
  };

  return (
    <div className="template-dashboard">
      <Toast ref={toast} />
      <ConfirmDialog
        visible={confirmVisible}
        onHide={() => setConfirmVisible(false)}
        message={`Are you sure you want to ${actionType} the selected templates?`}
        header="Confirm Action"
        icon="pi pi-exclamation-triangle"
        accept={handleBulkAction}
        reject={() => setConfirmVisible(false)}
      />
      
      {renderHeader()}
      {renderContent()}
    </div>
  );
};

export default TemplateDashboard;