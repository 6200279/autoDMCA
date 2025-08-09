import React, { useState, useRef, useEffect } from 'react';
import { 
  TabView, 
  TabPanel 
} from 'primereact/tabview';
import { 
  DataTable, 
  DataTableSelectionChangeEvent,
  DataTableFilterMeta
} from 'primereact/datatable';
import { 
  Column, 
  ColumnFilterElementTemplateOptions 
} from 'primereact/column';
import { 
  Dialog 
} from 'primereact/dialog';
import { 
  Button 
} from 'primereact/button';
import { 
  Toolbar 
} from 'primereact/toolbar';
import { 
  InputText 
} from 'primereact/inputtext';
import { 
  Card 
} from 'primereact/card';
import { 
  Editor 
} from 'primereact/editor';
import { 
  Timeline 
} from 'primereact/timeline';
import { 
  Tree, 
  TreeNode 
} from 'primereact/tree';
import { 
  Toast 
} from 'primereact/toast';
import { 
  Dropdown 
} from 'primereact/dropdown';
import { 
  Tag 
} from 'primereact/tag';
import { 
  ConfirmDialog, 
  confirmDialog 
} from 'primereact/confirmdialog';
import { 
  Splitter, 
  SplitterPanel 
} from 'primereact/splitter';
import { 
  Checkbox 
} from 'primereact/checkbox';
import { 
  MultiSelect 
} from 'primereact/multiselect';
import { 
  ProgressBar 
} from 'primereact/progressbar';
import { 
  InputTextarea 
} from 'primereact/inputtextarea';
import { 
  Panel 
} from 'primereact/panel';
import { 
  Divider 
} from 'primereact/divider';
import { 
  Badge 
} from 'primereact/badge';
import { 
  Chip 
} from 'primereact/chip';
import { 
  Menu 
} from 'primereact/menu';
import { 
  OverlayPanel 
} from 'primereact/overlaypanel';
import { 
  FilterMatchMode 
} from 'primereact/api';

import { 
  IDMCATemplate, 
  TemplateCategoryType, 
  TemplateComplianceStatus,
  TemplatePreviewData,
  TemplateValidationResult,
  PlatformTemplateConfig,
  TemplateLibraryEntry
} from '../types/dmca';

import { 
  validateDMCATemplate, 
  generateTemplatePreview,
  validateTemplateVariables,
  validateJurisdictionCompliance,
  analyzeTemplateEffectiveness
} from '../services/dmcaTemplateValidator';

// Import component-specific styles
import './DMCATemplates.css';

const DMCATemplates: React.FC = () => {
  // State Management
  const [activeTabIndex, setActiveTabIndex] = useState<number>(0);
  const [templates, setTemplates] = useState<IDMCATemplate[]>([]);
  const [selectedTemplates, setSelectedTemplates] = useState<IDMCATemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<IDMCATemplate | null>(null);
  const [dialogVisible, setDialogVisible] = useState<boolean>(false);
  const [previewDialogVisible, setPreviewDialogVisible] = useState<boolean>(false);
  const [complianceDialogVisible, setComplianceDialogVisible] = useState<boolean>(false);
  const [editMode, setEditMode] = useState<'create' | 'edit'>('create');
  const [validationResult, setValidationResult] = useState<TemplateValidationResult | null>(null);
  const [templatePreview, setTemplatePreview] = useState<string>('');
  const [filters, setFilters] = useState<DataTableFilterMeta>({});
  const [globalFilterValue, setGlobalFilterValue] = useState<string>('');
  
  // Refs
  const toastRef = useRef<Toast>(null);
  const editorRef = useRef<Editor>(null);
  const menuRef = useRef<Menu>(null);
  const overlayPanelRef = useRef<OverlayPanel>(null);

  // Template Categories with enhanced metadata
  const templateCategories: TemplateCategoryType[] = [
    'Standard DMCA Notices',
    'Platform-Specific',
    'International',
    'Counter-Notices',
    'Follow-up',
    'Search Engine'
  ];

  // Platform Options for Platform-Specific Templates
  const platformOptions = [
    { label: 'Instagram', value: 'Instagram' },
    { label: 'TikTok', value: 'TikTok' },
    { label: 'YouTube', value: 'YouTube' },
    { label: 'OnlyFans', value: 'OnlyFans' },
    { label: 'Twitter/X', value: 'Twitter' },
    { label: 'Facebook', value: 'Facebook' },
    { label: 'Google', value: 'Google' },
    { label: 'Bing', value: 'Bing' }
  ];

  // Jurisdiction Options for International Templates
  const jurisdictionOptions = [
    { label: 'United States', value: 'US' },
    { label: 'European Union', value: 'EU' },
    { label: 'United Kingdom', value: 'UK' },
    { label: 'Canada', value: 'CA' },
    { label: 'Australia', value: 'AU' },
    { label: 'Brazil', value: 'BR' },
    { label: 'Japan', value: 'JP' }
  ];

  // Sample Preview Data for Template Testing
  const samplePreviewData: TemplatePreviewData = {
    creatorName: 'Jane Creator',
    infringingUrl: 'https://example.com/infringing-content',
    platform: 'Instagram',
    workDescription: 'Original photography and creative content',
    contactEmail: 'jane@example.com',
    copyrightUrl: 'https://jane-creator.com/portfolio',
    dateOfInfringement: new Date().toLocaleDateString()
  };

  // Initialize filters
  useEffect(() => {
    setFilters({
      global: { value: null, matchMode: FilterMatchMode.CONTAINS },
      title: { value: null, matchMode: FilterMatchMode.STARTS_WITH },
      complianceStatus: { value: null, matchMode: FilterMatchMode.EQUALS }
    });
  }, []);

  // Load sample templates on component mount
  useEffect(() => {
    loadSampleTemplates();
  }, []);

  const loadSampleTemplates = () => {
    const sampleTemplates: IDMCATemplate[] = [
      {
        id: '1',
        title: 'Standard DMCA Takedown Notice',
        content: `Dear {{platform}} Team,

I am writing to report copyright infringement of my original work that has been posted on your platform without my authorization.

**Copyright Owner Information:**
Name: {{creator_name}}
Email: {{contact_email}}
Phone: [Your Phone Number]

**Identification of Copyrighted Work:**
I am the copyright owner of {{work_description}}, which can be found at: {{copyright_url}}

**Identification of Infringing Material:**
The infringing material is located at: {{infringing_url}}
This content was posted on {{date_of_infringement}} without my permission.

**Good Faith Statement:**
I have a good faith belief that use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.

**Accuracy Statement:**
I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or am authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.

**Electronic Signature:**
{{signature}}

Sincerely,
{{creator_name}}`,
        category: 'Standard DMCA Notices',
        complianceStatus: 'COMPLIANT',
        createdAt: new Date(),
        platforms: ['General']
      },
      {
        id: '2',
        title: 'Instagram DMCA Notice',
        content: `Instagram Copyright Team,

I am reporting unauthorized use of my copyrighted content on Instagram.

**Copyright Owner:** {{creator_name}}
**Contact:** {{contact_email}}

**Original Work:** {{work_description}}
Available at: {{copyright_url}}

**Infringing Instagram Post:** {{infringing_url}}

I have a good faith belief that the use of my copyrighted material is not authorized. Under penalty of perjury, I swear that this information is accurate and I am the copyright owner.

{{signature}}
{{creator_name}}`,
        category: 'Platform-Specific',
        complianceStatus: 'COMPLIANT',
        createdAt: new Date(),
        platforms: ['Instagram']
      }
    ];
    
    setTemplates(sampleTemplates);
  };

  // Global filter handler
  const onGlobalFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    let updatedFilters = { ...filters };
    
    if (updatedFilters.global) {
      updatedFilters.global.value = value;
    }
    
    setFilters(updatedFilters);
    setGlobalFilterValue(value);
  };

  // Create/Edit Template Handler
  const handleTemplateSubmit = async () => {
    if (!selectedTemplate) return;

    try {
      const validationResult = validateDMCATemplate(selectedTemplate);
      const variableErrors = validateTemplateVariables(selectedTemplate);
      const jurisdictionIssues = selectedTemplate.jurisdiction 
        ? validateJurisdictionCompliance(selectedTemplate, selectedTemplate.jurisdiction)
        : [];

      const allErrors = [
        ...validationResult.errors,
        ...variableErrors,
        ...jurisdictionIssues
      ];

      if (allErrors.length === 0) {
        const updatedTemplates = editMode === 'create'
          ? [...templates, { ...selectedTemplate, id: Date.now().toString(), createdAt: new Date() }]
          : templates.map(t => t.id === selectedTemplate.id ? 
              { ...selectedTemplate, updatedAt: new Date() } : t);
        
        setTemplates(updatedTemplates);
        setDialogVisible(false);
        
        toastRef.current?.show({
          severity: 'success', 
          summary: 'Template Saved', 
          detail: `DMCA Template ${editMode === 'create' ? 'created' : 'updated'} successfully`
        });
      } else {
        setValidationResult({
          ...validationResult,
          errors: allErrors,
          isValid: false
        });
        setComplianceDialogVisible(true);
      }
    } catch (error) {
      toastRef.current?.show({
        severity: 'error', 
        summary: 'Error', 
        detail: 'Failed to process template'
      });
    }
  };

  // Template Preview Handler
  const handlePreviewTemplate = (template: IDMCATemplate) => {
    const preview = generateTemplatePreview(template, samplePreviewData);
    setTemplatePreview(preview);
    setPreviewDialogVisible(true);
  };

  // Template Compliance Check
  const handleComplianceCheck = (template: IDMCATemplate) => {
    const result = validateDMCATemplate(template);
    const effectiveness = analyzeTemplateEffectiveness(template);
    
    setValidationResult({
      ...result,
      warnings: [...result.warnings, ...effectiveness.improvements]
    });
    setComplianceDialogVisible(true);
  };

  // Bulk Operations Menu Items
  const bulkMenuItems = [
    {
      label: 'Export Selected',
      icon: 'pi pi-download',
      command: () => handleBulkExport()
    },
    {
      label: 'Delete Selected',
      icon: 'pi pi-trash',
      command: () => handleBulkDelete()
    },
    {
      label: 'Mark as Compliant',
      icon: 'pi pi-check',
      command: () => handleBulkStatusUpdate('COMPLIANT')
    },
    {
      label: 'Duplicate Selected',
      icon: 'pi pi-copy',
      command: () => handleBulkDuplicate()
    }
  ];

  const handleBulkExport = () => {
    const dataStr = JSON.stringify(selectedTemplates, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `dmca-templates-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    toastRef.current?.show({
      severity: 'success',
      summary: 'Export Complete',
      detail: `${selectedTemplates.length} templates exported`
    });
  };

  const handleBulkDelete = () => {
    confirmDialog({
      message: `Are you sure you want to delete ${selectedTemplates.length} selected templates?`,
      header: 'Bulk Delete Confirmation',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: () => {
        const selectedIds = selectedTemplates.map(t => t.id);
        setTemplates(templates.filter(t => !selectedIds.includes(t.id)));
        setSelectedTemplates([]);
        
        toastRef.current?.show({
          severity: 'success',
          summary: 'Templates Deleted',
          detail: `${selectedTemplates.length} templates deleted`
        });
      }
    });
  };

  const handleBulkStatusUpdate = (status: TemplateComplianceStatus) => {
    const updatedTemplates = templates.map(template => 
      selectedTemplates.some(selected => selected.id === template.id)
        ? { ...template, complianceStatus: status, updatedAt: new Date() }
        : template
    );
    
    setTemplates(updatedTemplates);
    setSelectedTemplates([]);
    
    toastRef.current?.show({
      severity: 'success',
      summary: 'Status Updated',
      detail: `${selectedTemplates.length} templates marked as ${status.toLowerCase()}`
    });
  };

  const handleBulkDuplicate = () => {
    const duplicatedTemplates = selectedTemplates.map(template => ({
      ...template,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      title: `${template.title} (Copy)`,
      createdAt: new Date(),
      complianceStatus: 'PENDING' as TemplateComplianceStatus
    }));
    
    setTemplates([...templates, ...duplicatedTemplates]);
    setSelectedTemplates([]);
    
    toastRef.current?.show({
      severity: 'success',
      summary: 'Templates Duplicated',
      detail: `${selectedTemplates.length} templates duplicated`
    });
  };

  // Template Compliance Status Renderer
  const complianceStatusTemplate = (template: IDMCATemplate) => {
    const statusConfig = {
      'PENDING': { severity: 'warning' as const, label: 'Pending Review' },
      'COMPLIANT': { severity: 'success' as const, label: 'Compliant' },
      'NEEDS_REVISION': { severity: 'danger' as const, label: 'Needs Revision' }
    };

    const config = statusConfig[template.complianceStatus];
    return <Tag value={config.label} severity={config.severity} />;
  };

  // Template Usage Stats Renderer
  const usageStatsTemplate = (template: IDMCATemplate) => {
    const usage = template.usageStats;
    if (!usage) return <span className="text-gray-500">No data</span>;

    return (
      <div className="flex align-items-center gap-2">
        <Badge value={usage.totalUsage} />
        <span className="text-sm text-gray-600">
          {Math.round(usage.successRate)}% success
        </span>
      </div>
    );
  };

  // Template Actions Renderer
  const actionTemplate = (template: IDMCATemplate) => (
    <div className="flex gap-1">
      <Button 
        icon="pi pi-eye" 
        className="p-button-rounded p-button-text p-button-sm"
        tooltip="Preview Template"
        onClick={() => handlePreviewTemplate(template)}
      />
      <Button 
        icon="pi pi-pencil" 
        className="p-button-rounded p-button-text p-button-sm"
        tooltip="Edit Template"
        onClick={() => {
          setSelectedTemplate(template);
          setEditMode('edit');
          setDialogVisible(true);
        }}
      />
      <Button 
        icon="pi pi-shield" 
        className="p-button-rounded p-button-text p-button-sm"
        tooltip="Check Compliance"
        onClick={() => handleComplianceCheck(template)}
      />
      <Button 
        icon="pi pi-copy" 
        className="p-button-rounded p-button-text p-button-sm"
        tooltip="Duplicate Template"
        onClick={() => {
          const duplicated = {
            ...template,
            id: Date.now().toString(),
            title: `${template.title} (Copy)`,
            complianceStatus: 'PENDING' as TemplateComplianceStatus,
            createdAt: new Date()
          };
          setTemplates([...templates, duplicated]);
          toastRef.current?.show({
            severity: 'success',
            summary: 'Template Duplicated',
            detail: `"${template.title}" duplicated successfully`
          });
        }}
      />
      <Button 
        icon="pi pi-trash" 
        className="p-button-rounded p-button-text p-button-danger p-button-sm"
        tooltip="Delete Template"
        onClick={() => confirmDialog({
          message: `Are you sure you want to delete "${template.title}"?`,
          header: 'Delete Confirmation',
          icon: 'pi pi-info-circle',
          acceptClassName: 'p-button-danger',
          accept: () => {
            setTemplates(templates.filter(t => t.id !== template.id));
            toastRef.current?.show({
              severity: 'success',
              summary: 'Template Deleted',
              detail: `"${template.title}" deleted successfully`
            });
          }
        })}
      />
    </div>
  );

  // Platform chips renderer for Platform-Specific templates
  const platformsTemplate = (template: IDMCATemplate) => {
    if (!template.platforms || template.platforms.length === 0) {
      return <span className="text-gray-500">General</span>;
    }

    return (
      <div className="flex flex-wrap gap-1">
        {template.platforms.map((platform, index) => (
          <Chip key={index} label={platform} className="text-xs" />
        ))}
      </div>
    );
  };

  // Toolbar Content
  const toolbarStartContent = (
    <div className="flex gap-2">
      <Button 
        label="New Template" 
        icon="pi pi-plus" 
        onClick={() => {
          setEditMode('create');
          setSelectedTemplate({
            id: '',
            title: '',
            content: '',
            category: templateCategories[activeTabIndex],
            complianceStatus: 'PENDING',
            platforms: []
          });
          setDialogVisible(true);
        }} 
      />
      <Button 
        label="Template Library" 
        icon="pi pi-book" 
        className="p-button-outlined"
        onClick={() => {
          // Open template library dialog
          toastRef.current?.show({
            severity: 'info',
            summary: 'Coming Soon',
            detail: 'Template library feature will be available soon'
          });
        }}
      />
      {selectedTemplates.length > 0 && (
        <Button 
          label={`Bulk Actions (${selectedTemplates.length})`}
          icon="pi pi-cog" 
          className="p-button-secondary"
          onClick={(e) => menuRef.current?.toggle(e)}
        />
      )}
    </div>
  );

  const toolbarEndContent = (
    <div className="flex gap-2 align-items-center">
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText 
          value={globalFilterValue}
          onChange={onGlobalFilterChange}
          placeholder="Search templates..."
          className="w-20rem"
        />
      </span>
      <Button 
        icon="pi pi-download" 
        className="p-button-help p-button-outlined"
        tooltip="Export All Templates"
        onClick={() => {
          const dataStr = JSON.stringify(templates, null, 2);
          const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
          
          const exportFileDefaultName = `all-dmca-templates-${new Date().toISOString().split('T')[0]}.json`;
          
          const linkElement = document.createElement('a');
          linkElement.setAttribute('href', dataUri);
          linkElement.setAttribute('download', exportFileDefaultName);
          linkElement.click();
        }}
      />
    </div>
  );

  return (
    <div className="dmca-templates-management p-4">
      <Toast ref={toastRef} />
      <Menu model={bulkMenuItems} popup ref={menuRef} />
      
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">DMCA Template Management</h1>
        <p className="text-gray-600 mb-4">
          Manage and customize DMCA takedown notice templates for different platforms and jurisdictions.
          Ensure legal compliance with built-in validation and effectiveness analysis.
        </p>
      </div>

      <Toolbar 
        start={toolbarStartContent} 
        end={toolbarEndContent}
        className="mb-4"
      />

      <TabView 
        activeIndex={activeTabIndex} 
        onTabChange={(e) => setActiveTabIndex(e.index)}
      >
        {templateCategories.map((category, index) => (
          <TabPanel 
            key={index} 
            header={
              <span>
                {category} 
                <Badge 
                  value={templates.filter(t => t.category === category).length} 
                  className="ml-2" 
                />
              </span>
            }
          >
            <DataTable 
              value={templates.filter(t => t.category === category)}
              selection={selectedTemplates}
              onSelectionChange={(e) => setSelectedTemplates(e.value)}
              dataKey="id"
              paginator
              rows={10}
              filters={filters}
              globalFilterFields={['title', 'content', 'complianceStatus']}
              emptyMessage={`No ${category.toLowerCase()} templates found.`}
              selectionMode="multiple"
              className="p-datatable-sm"
            >
              <Column selectionMode="multiple" headerStyle={{width: '3rem'}} />
              <Column 
                field="title" 
                header="Template Title" 
                sortable
                filter
                filterPlaceholder="Search by title"
                style={{minWidth: '250px'}}
              />
              <Column 
                field="complianceStatus" 
                header="Compliance Status" 
                body={complianceStatusTemplate} 
                sortable
                filter
                filterElement={(options) => (
                  <Dropdown
                    value={options.value}
                    options={[
                      { label: 'All', value: null },
                      { label: 'Pending Review', value: 'PENDING' },
                      { label: 'Compliant', value: 'COMPLIANT' },
                      { label: 'Needs Revision', value: 'NEEDS_REVISION' }
                    ]}
                    onChange={(e) => options.filterApplyCallback(e.value)}
                    placeholder="Select Status"
                    className="p-column-filter"
                    showClear
                  />
                )}
                style={{minWidth: '150px'}}
              />
              {category === 'Platform-Specific' && (
                <Column 
                  field="platforms" 
                  header="Platforms"
                  body={platformsTemplate}
                  style={{minWidth: '180px'}}
                />
              )}
              <Column 
                field="usageStats" 
                header="Usage"
                body={usageStatsTemplate}
                sortable
                style={{minWidth: '120px'}}
              />
              <Column 
                field="updatedAt" 
                header="Last Modified" 
                sortable
                body={(template) => template.updatedAt ? 
                  template.updatedAt.toLocaleDateString() : 
                  template.createdAt?.toLocaleDateString() || 'Unknown'
                }
                style={{minWidth: '120px'}}
              />
              <Column 
                header="Actions" 
                body={actionTemplate}
                style={{minWidth: '200px'}}
              />
            </DataTable>
          </TabPanel>
        ))}
      </TabView>

      {/* Template Creation/Edit Dialog */}
      <Dialog 
        header={
          <div className="flex align-items-center gap-2">
            <i className={`pi ${editMode === 'create' ? 'pi-plus' : 'pi-pencil'}`} />
            <span>{editMode === 'create' ? 'Create DMCA Template' : 'Edit DMCA Template'}</span>
          </div>
        }
        visible={dialogVisible}
        style={{width: '90vw', maxWidth: '1200px'}}
        onHide={() => setDialogVisible(false)}
        footer={
          <div className="flex justify-content-between">
            <div>
              {selectedTemplate && (
                <Button 
                  label="Preview" 
                  icon="pi pi-eye" 
                  onClick={() => handlePreviewTemplate(selectedTemplate)}
                  className="p-button-outlined"
                />
              )}
            </div>
            <div className="flex gap-2">
              <Button 
                label="Cancel" 
                icon="pi pi-times" 
                onClick={() => setDialogVisible(false)} 
                className="p-button-text" 
              />
              <Button 
                label={editMode === 'create' ? 'Create' : 'Update'} 
                icon="pi pi-check" 
                onClick={handleTemplateSubmit} 
                className="p-button-primary"
                disabled={!selectedTemplate?.title || !selectedTemplate?.content}
              />
            </div>
          </div>
        }
      >
        {selectedTemplate && (
          <Splitter style={{height: '600px'}}>
            <SplitterPanel size={70} minSize={60}>
              <div className="template-edit-form p-4">
                <div className="grid">
                  <div className="col-12 md:col-8">
                    <label htmlFor="template-title" className="block text-sm font-medium mb-2">
                      Template Title *
                    </label>
                    <InputText 
                      id="template-title"
                      placeholder="Enter template title" 
                      value={selectedTemplate.title}
                      onChange={(e) => setSelectedTemplate({
                        ...selectedTemplate, 
                        title: e.target.value
                      })}
                      className="w-full"
                      required
                    />
                  </div>
                  <div className="col-12 md:col-4">
                    <label htmlFor="template-category" className="block text-sm font-medium mb-2">
                      Category *
                    </label>
                    <Dropdown 
                      id="template-category"
                      options={templateCategories.map(cat => ({ label: cat, value: cat }))}
                      value={selectedTemplate.category}
                      onChange={(e) => setSelectedTemplate({
                        ...selectedTemplate, 
                        category: e.value
                      })}
                      placeholder="Select Category"
                      className="w-full"
                      required
                    />
                  </div>

                  {selectedTemplate.category === 'Platform-Specific' && (
                    <div className="col-12 md:col-6">
                      <label htmlFor="template-platforms" className="block text-sm font-medium mb-2">
                        Target Platforms
                      </label>
                      <MultiSelect 
                        id="template-platforms"
                        options={platformOptions}
                        value={selectedTemplate.platforms || []}
                        onChange={(e) => setSelectedTemplate({
                          ...selectedTemplate, 
                          platforms: e.value
                        })}
                        placeholder="Select Platforms"
                        className="w-full"
                        maxSelectedLabels={3}
                      />
                    </div>
                  )}

                  {selectedTemplate.category === 'International' && (
                    <div className="col-12 md:col-6">
                      <label htmlFor="template-jurisdiction" className="block text-sm font-medium mb-2">
                        Jurisdiction
                      </label>
                      <Dropdown 
                        id="template-jurisdiction"
                        options={jurisdictionOptions}
                        value={selectedTemplate.jurisdiction}
                        onChange={(e) => setSelectedTemplate({
                          ...selectedTemplate, 
                          jurisdiction: e.value
                        })}
                        placeholder="Select Jurisdiction"
                        className="w-full"
                      />
                    </div>
                  )}

                  <div className="col-12">
                    <label htmlFor="template-content" className="block text-sm font-medium mb-2">
                      Template Content *
                    </label>
                    <Editor 
                      id="template-content"
                      ref={editorRef}
                      value={selectedTemplate.content}
                      onTextChange={(e) => setSelectedTemplate({
                        ...selectedTemplate, 
                        content: e.htmlValue || ''
                      })}
                      style={{height:'350px'}}
                      placeholder="Enter your DMCA template content with variables like {{creator_name}}, {{infringing_url}}, etc."
                    />
                    <small className="text-gray-600 mt-1 block">
                      Use double curly braces for variables: {'{{creator_name}}'}, {'{{infringing_url}}'}, {'{{platform}}'}, etc.
                    </small>
                  </div>
                </div>
              </div>
            </SplitterPanel>
            
            <SplitterPanel size={30} minSize={25}>
              <div className="p-4">
                <Panel header="Template Variables" className="mb-3">
                  <div className="text-sm">
                    <p className="mb-2 font-medium">Common Variables:</p>
                    <div className="grid gap-1">
                      {[
                        '{{creator_name}}',
                        '{{contact_email}}', 
                        '{{infringing_url}}',
                        '{{platform}}',
                        '{{work_description}}',
                        '{{copyright_url}}',
                        '{{date_of_infringement}}',
                        '{{signature}}'
                      ].map((variable, index) => (
                        <Chip 
                          key={index} 
                          label={variable} 
                          className="text-xs cursor-pointer"
                          onClick={() => {
                            if (editorRef.current && selectedTemplate) {
                              const newContent = selectedTemplate.content + ' ' + variable;
                              setSelectedTemplate({
                                ...selectedTemplate,
                                content: newContent
                              });
                            }
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </Panel>

                <Panel header="Legal Requirements" className="mb-3">
                  <div className="text-sm">
                    <p className="mb-2 font-medium">DMCA 512(c)(3) Elements:</p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      <li>Physical/electronic signature</li>
                      <li>Identification of copyrighted work</li>
                      <li>Identification of infringing material</li>
                      <li>Contact information</li>
                      <li>Good faith statement</li>
                      <li>Accuracy statement under penalty of perjury</li>
                    </ul>
                  </div>
                </Panel>

                {selectedTemplate && (
                  <Panel header="Quick Validation">
                    <div className="text-sm">
                      <p className="mb-2">Characters: {selectedTemplate.content.length}</p>
                      <p className="mb-2">
                        Variables: {(selectedTemplate.content.match(/\{\{[^}]+\}\}/g) || []).length}
                      </p>
                      {selectedTemplate.content.length > 0 && (
                        <Button 
                          label="Check Compliance"
                          icon="pi pi-shield"
                          className="p-button-sm p-button-outlined w-full"
                          onClick={() => handleComplianceCheck(selectedTemplate)}
                        />
                      )}
                    </div>
                  </Panel>
                )}
              </div>
            </SplitterPanel>
          </Splitter>
        )}
      </Dialog>

      {/* Template Preview Dialog */}
      <Dialog 
        header="Template Preview"
        visible={previewDialogVisible}
        style={{width: '70vw'}}
        onHide={() => setPreviewDialogVisible(false)}
      >
        <div className="template-preview">
          <Panel header="Preview with Sample Data">
            <div 
              className="p-4 border-1 surface-border border-round"
              style={{whiteSpace: 'pre-wrap', fontFamily: 'monospace'}}
              dangerouslySetInnerHTML={{__html: templatePreview}}
            />
          </Panel>
        </div>
      </Dialog>

      {/* Compliance Check Dialog */}
      <Dialog 
        header="Template Compliance Analysis"
        visible={complianceDialogVisible}
        style={{width: '60vw'}}
        onHide={() => setComplianceDialogVisible(false)}
      >
        {validationResult && (
          <div className="compliance-analysis">
            <div className="mb-4">
              <div className="flex align-items-center gap-3 mb-3">
                <span className="text-lg font-semibold">Compliance Score:</span>
                <ProgressBar 
                  value={validationResult.complianceScore} 
                  className="w-full"
                  color={validationResult.complianceScore >= 80 ? 'green' : 
                         validationResult.complianceScore >= 60 ? 'orange' : 'red'}
                />
                <span className="font-bold">{validationResult.complianceScore}%</span>
              </div>
            </div>

            <Divider />

            <div className="grid">
              <div className="col-12 md:col-6">
                <Panel header="Required Elements" className="h-full">
                  {validationResult.requiredElements.map((element, index) => (
                    <div key={index} className="flex align-items-center gap-2 mb-2">
                      <i className={`pi ${element.present ? 'pi-check text-green-500' : 'pi-times text-red-500'}`} />
                      <div className="flex-1">
                        <div className="font-medium text-sm">{element.description}</div>
                        <div className="text-xs text-gray-500">{element.legalRequirement}</div>
                      </div>
                    </div>
                  ))}
                </Panel>
              </div>

              <div className="col-12 md:col-6">
                <Panel header="Issues & Recommendations" className="h-full">
                  {validationResult.errors.length > 0 && (
                    <div className="mb-3">
                      <h4 className="text-red-600 font-semibold mb-2">Errors:</h4>
                      {validationResult.errors.map((error, index) => (
                        <div key={index} className="flex align-items-start gap-2 mb-2">
                          <i className="pi pi-exclamation-triangle text-red-500 mt-1" />
                          <span className="text-sm">{error}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {validationResult.warnings.length > 0 && (
                    <div>
                      <h4 className="text-orange-600 font-semibold mb-2">Warnings:</h4>
                      {validationResult.warnings.map((warning, index) => (
                        <div key={index} className="flex align-items-start gap-2 mb-2">
                          <i className="pi pi-info-circle text-orange-500 mt-1" />
                          <span className="text-sm">{warning}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>
              </div>
            </div>
          </div>
        )}
      </Dialog>

      <ConfirmDialog />
    </div>
  );
};

export default DMCATemplates;