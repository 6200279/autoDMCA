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
  TemplateApprovalStatus,
  TemplatePreviewData,
  TemplateValidationResult,
  PlatformTemplateConfig,
  TemplateLibraryEntry
} from '../types/dmca';

import { dmcaTemplatesApi } from '../services/api';
import { 
  DMCATemplateApiResponse,
  TemplateValidationResponse,
  TemplatePreviewResponse,
  TemplateDashboardStatsResponse,
  PaginatedResponse,
  TemplateRealtimeUpdate
} from '../types/api';
import { useTemplateRealtime } from '../hooks/useTemplateRealtime';

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
  const [validationResult, setValidationResult] = useState<TemplateValidationResponse | null>(null);
  const [templatePreview, setTemplatePreview] = useState<string>('');
  const [filters, setFilters] = useState<DataTableFilterMeta>({});
  const [globalFilterValue, setGlobalFilterValue] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [operationLoading, setOperationLoading] = useState<Record<string, boolean>>({});
  const [dashboardStats, setDashboardStats] = useState<TemplateDashboardStatsResponse | null>(null);
  const [realtimeEnabled, setRealtimeEnabled] = useState<boolean>(true);
  
  // Real-time updates
  const { isConnected, lastUpdate, connectionError, reconnect } = useTemplateRealtime({
    categories: templateCategories,
    updateTypes: ['validation', 'compliance', 'usage', 'approval'],
    enabled: realtimeEnabled,
    onUpdate: handleRealtimeUpdate
  });

  function handleRealtimeUpdate(update: TemplateRealtimeUpdate) {
    console.log('Received real-time update:', update);
    
    // Update templates based on real-time data
    if (update.update_type === 'validation' || update.update_type === 'compliance') {
      setTemplates(prev => prev.map(template => {
        if (template.id === update.template_id) {
          return {
            ...template,
            complianceStatus: update.data.status as TemplateComplianceStatus || template.complianceStatus,
            updatedAt: new Date()
          };
        }
        return template;
      }));
      
      // Show notification for critical updates
      if (update.data.severity === 'critical') {
        toastRef.current?.show({
          severity: 'warn',
          summary: 'Template Update',
          detail: `${update.data.template_name}: ${update.data.message}`,
          life: 5000
        });
      }
    }
    
    if (update.update_type === 'usage') {
      // Reload dashboard stats for usage updates
      loadDashboardStats();
    }
    
    if (update.update_type === 'approval') {
      setTemplates(prev => prev.map(template => {
        if (template.id === update.template_id) {
          return {
            ...template,
            approvalStatus: update.data.status as TemplateApprovalStatus,
            updatedAt: new Date()
          };
        }
        return template;
      }));
      
      toastRef.current?.show({
        severity: update.data.status === 'approved' ? 'success' : 'info',
        summary: 'Template Approval Update',
        detail: `${update.data.template_name} has been ${update.data.status}`,
        life: 4000
      });
    }
  }

  // Variable validation handler
  const handleVariableValidation = async (template: IDMCATemplate) => {
    try {
      setOperationLoading(prev => ({ ...prev, [`variables-${template.id}`]: true }));
      
      // Extract variables from template content
      const variables: Record<string, any> = {};
      const variableMatches = template.content.match(/\{\{([^}]+)\}\}/g) || [];
      variableMatches.forEach(match => {
        const varName = match.slice(2, -2).trim();
        variables[varName] = samplePreviewData[varName as keyof typeof samplePreviewData] || '';
      });
      
      const response = await dmcaTemplatesApi.validateVariables(template.id, variables);
      
      toastRef.current?.show({
        severity: 'success',
        summary: 'Variable Validation',
        detail: `All ${variableMatches.length} variables validated successfully`
      });
    } catch (error: any) {
      console.error('Failed to validate variables:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Variable Validation Error',
        detail: error.response?.data?.detail || 'Failed to validate template variables'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [`variables-${template.id}`]: false }));
    }
  };

  // Jurisdiction validation handler
  const handleJurisdictionValidation = async (template: IDMCATemplate) => {
    if (!template.jurisdiction) return;
    
    try {
      setOperationLoading(prev => ({ ...prev, [`jurisdiction-${template.id}`]: true }));
      
      const response = await dmcaTemplatesApi.validateJurisdictionCompliance(
        template.id, 
        template.jurisdiction
      );
      
      const jurisdictionValidation = response.data;
      
      if (jurisdictionValidation.compliant) {
        toastRef.current?.show({
          severity: 'success',
          summary: 'Jurisdiction Compliance',
          detail: `Template complies with ${template.jurisdiction} legal requirements`
        });
      } else {
        toastRef.current?.show({
          severity: 'warn',
          summary: 'Jurisdiction Issues Found',
          detail: `Template needs updates for ${template.jurisdiction} compliance`
        });
        
        // You could show detailed issues in a dialog
        setValidationResult({
          is_valid: false,
          compliance_score: 60,
          errors: jurisdictionValidation.specific_requirements
            .filter(req => !req.met)
            .map(req => ({
              code: 'JURISDICTION_REQ',
              message: req.description,
              field: req.requirement,
              severity: 'high' as const,
              suggestion: req.reference
            })),
          warnings: [],
          required_elements: [],
          recommendations: jurisdictionValidation.additional_clauses || [],
          jurisdiction_compliance: jurisdictionValidation
        });
        setComplianceDialogVisible(true);
      }
    } catch (error: any) {
      console.error('Failed to validate jurisdiction:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Jurisdiction Validation Error',
        detail: error.response?.data?.detail || 'Failed to validate jurisdiction compliance'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [`jurisdiction-${template.id}`]: false }));
    }
  };

  // Template generation handler
  const handleGenerateTemplate = async () => {
    try {
      setOperationLoading(prev => ({ ...prev, generate: true }));
      
      // Show generation options dialog first
      const generationType = await showGenerationDialog();
      if (!generationType) return;
      
      const response = await dmcaTemplatesApi.generateTemplate({
        type: generationType.type,
        platform: generationType.platform,
        jurisdiction: generationType.jurisdiction,
        baseTemplate: generationType.baseTemplate,
        customFields: generationType.customFields
      });
      
      const generatedTemplate = response.data as DMCATemplateApiResponse;
      const transformedTemplate: IDMCATemplate = {
        ...generatedTemplate,
        createdAt: generatedTemplate.createdAt ? new Date(generatedTemplate.createdAt) : new Date(),
        updatedAt: generatedTemplate.updatedAt ? new Date(generatedTemplate.updatedAt) : undefined
      };
      
      // Add to templates list
      setTemplates(prev => [...prev, transformedTemplate]);
      
      // Open for editing
      setSelectedTemplate(transformedTemplate);
      setEditMode('edit');
      setDialogVisible(true);
      
      toastRef.current?.show({
        severity: 'success',
        summary: 'Template Generated',
        detail: `New ${generationType.type} template generated successfully`
      });
      
      loadDashboardStats();
    } catch (error: any) {
      console.error('Failed to generate template:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Generation Error',
        detail: error.response?.data?.detail || 'Failed to generate template'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, generate: false }));
    }
  };

  // Show generation options dialog (mock implementation)
  const showGenerationDialog = (): Promise<any> => {
    return new Promise((resolve) => {
      // For now, return a default configuration
      // In a real implementation, this would show a dialog with options
      resolve({
        type: 'standard' as const,
        platform: undefined,
        jurisdiction: 'US',
        baseTemplate: undefined,
        customFields: {}
      });
    });
  };

  // View template analytics
  const handleViewAnalytics = async (template: IDMCATemplate) => {
    try {
      setOperationLoading(prev => ({ ...prev, [`analytics-${template.id}`]: true }));
      
      const response = await dmcaTemplatesApi.getTemplateUsage(template.id, {
        date_range: {
          start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          end: new Date().toISOString()
        },
        granularity: 'daily'
      });
      
      const analytics = response.data;
      
      // Update local template with fresh usage stats
      setTemplates(prev => prev.map(t => t.id === template.id ? {
        ...t,
        usageStats: {
          totalUsage: analytics.usage_metrics.total_usage,
          successRate: analytics.usage_metrics.success_rate,
          platformBreakdown: analytics.platform_breakdown.reduce((acc, p) => {
            acc[p.platform] = p.usage_count;
            return acc;
          }, {} as Record<string, number>),
          lastUsed: analytics.trend_data.length > 0 ? 
            new Date(analytics.trend_data[analytics.trend_data.length - 1].date) : 
            undefined,
          averageResponseTime: analytics.usage_metrics.avg_response_time_hours
        }
      } : t));
      
      toastRef.current?.show({
        severity: 'info',
        summary: 'Template Analytics',
        detail: `${analytics.usage_metrics.total_usage} total uses, ${Math.round(analytics.usage_metrics.success_rate)}% success rate`
      });
      
      // Log detailed analytics for debugging
      console.log('Template analytics:', analytics);
    } catch (error: any) {
      console.error('Failed to load analytics:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Analytics Error',
        detail: error.response?.data?.detail || 'Failed to load template analytics'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [`analytics-${template.id}`]: false }));
    }
  };

  // Track template usage
  const trackTemplateUsage = async (templateId: string, context: string, success?: boolean, responseTime?: number) => {
    try {
      await dmcaTemplatesApi.trackUsage(templateId, {
        context,
        success,
        response_time: responseTime,
        metadata: {
          user_agent: navigator.userAgent,
          timestamp: new Date().toISOString(),
          session_id: Date.now().toString()
        }
      });
    } catch (error) {
      console.error('Failed to track usage:', error);
      // Don't show error to user as this is background tracking
    }
  };
  
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

  // Load templates and dashboard stats on component mount
  useEffect(() => {
    loadTemplates();
    loadDashboardStats();
  }, []);

  // Reload templates when active tab changes
  useEffect(() => {
    if (templateCategories[activeTabIndex]) {
      loadTemplates(templateCategories[activeTabIndex]);
    }
  }, [activeTabIndex]);

  const loadTemplates = async (category?: string) => {
    try {
      setLoading(true);
      const params = {
        category,
        page: 1,
        per_page: 100,
        sort: 'updated_at',
        order: 'desc' as const
      };
      
      const response = await dmcaTemplatesApi.getTemplates(params);
      const templatesData = response.data as PaginatedResponse<DMCATemplateApiResponse>;
      
      // Transform API response to match component expectations
      const transformedTemplates: IDMCATemplate[] = templatesData.items.map(template => ({
        ...template,
        createdAt: template.createdAt ? new Date(template.createdAt) : new Date(),
        updatedAt: template.updatedAt ? new Date(template.updatedAt) : undefined
      }));
      
      setTemplates(transformedTemplates);
    } catch (error) {
      console.error('Failed to load templates:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load templates'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardStats = async () => {
    try {
      const response = await dmcaTemplatesApi.getDashboardStats();
      setDashboardStats(response.data);
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
    }
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
      setOperationLoading(prev => ({ ...prev, submit: true }));
      
      // First validate the template content
      const validationResponse = await dmcaTemplatesApi.validateTemplateContent(
        selectedTemplate.content,
        selectedTemplate.category,
        selectedTemplate.jurisdiction
      );
      
      const validation = validationResponse.data as TemplateValidationResponse;
      
      if (!validation.is_valid) {
        setValidationResult(validation);
        setComplianceDialogVisible(true);
        return;
      }

      // Prepare template data for API
      const templateData = {
        title: selectedTemplate.title,
        content: selectedTemplate.content,
        category: selectedTemplate.category,
        platforms: selectedTemplate.platforms || [],
        jurisdiction: selectedTemplate.jurisdiction,
        variables: selectedTemplate.variables || [],
        legalReferences: selectedTemplate.legalReferences || []
      };

      let savedTemplate: DMCATemplateApiResponse;
      
      if (editMode === 'create') {
        const response = await dmcaTemplatesApi.createTemplate(templateData);
        savedTemplate = response.data;
      } else {
        const response = await dmcaTemplatesApi.updateTemplate(selectedTemplate.id, templateData);
        savedTemplate = response.data;
      }
      
      // Update local state
      const transformedTemplate: IDMCATemplate = {
        ...savedTemplate,
        createdAt: savedTemplate.createdAt ? new Date(savedTemplate.createdAt) : new Date(),
        updatedAt: savedTemplate.updatedAt ? new Date(savedTemplate.updatedAt) : undefined
      };
      
      setTemplates(prev => {
        if (editMode === 'create') {
          return [...prev, transformedTemplate];
        } else {
          return prev.map(t => t.id === savedTemplate.id ? transformedTemplate : t);
        }
      });
      
      setDialogVisible(false);
      setSelectedTemplate(null);
      
      toastRef.current?.show({
        severity: 'success',
        summary: 'Template Saved',
        detail: `DMCA Template ${editMode === 'create' ? 'created' : 'updated'} successfully`
      });
      
      // Reload dashboard stats
      loadDashboardStats();
      
    } catch (error: any) {
      console.error('Failed to save template:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: error.response?.data?.detail || 'Failed to save template'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, submit: false }));
    }
  };

  // Template Preview Handler
  const handlePreviewTemplate = async (template: IDMCATemplate) => {
    try {
      setOperationLoading(prev => ({ ...prev, [`preview-${template.id}`]: true }));
      
      const response = await dmcaTemplatesApi.generatePreview(template.id, samplePreviewData);
      const previewData = response.data as TemplatePreviewResponse;
      
      setTemplatePreview(previewData.preview_html || previewData.preview_text);
      setPreviewDialogVisible(true);
    } catch (error: any) {
      console.error('Failed to generate preview:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Preview Error',
        detail: error.response?.data?.detail || 'Failed to generate template preview'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [`preview-${template.id}`]: false }));
    }
  };

  // Template Compliance Check
  const handleComplianceCheck = async (template: IDMCATemplate) => {
    try {
      setOperationLoading(prev => ({ ...prev, [`compliance-${template.id}`]: true }));
      
      const response = await dmcaTemplatesApi.validateTemplate(template.id);
      const validation = response.data as TemplateValidationResponse;
      
      setValidationResult(validation);
      setComplianceDialogVisible(true);
    } catch (error: any) {
      console.error('Failed to check compliance:', error);
      toastRef.current?.show({
        severity: 'error',
        summary: 'Compliance Check Error',
        detail: error.response?.data?.detail || 'Failed to check template compliance'
      });
    } finally {
      setOperationLoading(prev => ({ ...prev, [`compliance-${template.id}`]: false }));
    }
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
    if (!usage) {
      return (
        <div className="flex align-items-center gap-2">
          <span className="text-gray-500">No data</span>
          <Button 
            icon="pi pi-chart-line"
            className="p-button-text p-button-sm"
            tooltip="View Analytics"
            onClick={() => handleViewAnalytics(template)}
            loading={operationLoading[`analytics-${template.id}`]}
          />
        </div>
      );
    }

    return (
      <div className="flex align-items-center gap-2">
        <Badge value={usage.totalUsage} />
        <span className="text-sm text-gray-600">
          {Math.round(usage.successRate)}% success
        </span>
        <Button 
          icon="pi pi-chart-line"
          className="p-button-text p-button-sm"
          tooltip="View Analytics"
          onClick={() => handleViewAnalytics(template)}
          loading={operationLoading[`analytics-${template.id}`]}
        />
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
        loading={operationLoading[`preview-${template.id}`]}
        onClick={async () => {
          const startTime = Date.now();
          try {
            await handlePreviewTemplate(template);
            const responseTime = Date.now() - startTime;
            trackTemplateUsage(template.id, 'preview', true, responseTime);
          } catch (error) {
            const responseTime = Date.now() - startTime;
            trackTemplateUsage(template.id, 'preview', false, responseTime);
          }
        }}
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
        loading={operationLoading[`compliance-${template.id}`]}
        onClick={async () => {
          const startTime = Date.now();
          try {
            await handleComplianceCheck(template);
            const responseTime = Date.now() - startTime;
            trackTemplateUsage(template.id, 'compliance_check', true, responseTime);
          } catch (error) {
            const responseTime = Date.now() - startTime;
            trackTemplateUsage(template.id, 'compliance_check', false, responseTime);
          }
        }}
      />
      <Button 
        icon="pi pi-copy" 
        className="p-button-rounded p-button-text p-button-sm"
        tooltip="Duplicate Template"
        loading={operationLoading[`duplicate-${template.id}`]}
        onClick={async () => {
          try {
            setOperationLoading(prev => ({ ...prev, [`duplicate-${template.id}`]: true }));
            
            const response = await dmcaTemplatesApi.duplicateTemplate(template.id, {
              title: `${template.title} (Copy)`
            });
            
            const duplicated = response.data as DMCATemplateApiResponse;
            const transformedTemplate: IDMCATemplate = {
              ...duplicated,
              createdAt: duplicated.createdAt ? new Date(duplicated.createdAt) : new Date(),
              updatedAt: duplicated.updatedAt ? new Date(duplicated.updatedAt) : undefined
            };
            
            setTemplates(prev => [...prev, transformedTemplate]);
            
            toastRef.current?.show({
              severity: 'success',
              summary: 'Template Duplicated',
              detail: `"${template.title}" duplicated successfully`
            });
            
            loadDashboardStats();
          } catch (error: any) {
            console.error('Failed to duplicate template:', error);
            toastRef.current?.show({
              severity: 'error',
              summary: 'Duplication Error',
              detail: error.response?.data?.detail || 'Failed to duplicate template'
            });
          } finally {
            setOperationLoading(prev => ({ ...prev, [`duplicate-${template.id}`]: false }));
          }
        }}
      />
      <Button 
        icon="pi pi-trash" 
        className="p-button-rounded p-button-text p-button-danger p-button-sm"
        tooltip="Delete Template"
        loading={operationLoading[`delete-${template.id}`]}
        onClick={() => confirmDialog({
          message: `Are you sure you want to delete "${template.title}"?`,
          header: 'Delete Confirmation',
          icon: 'pi pi-info-circle',
          acceptClassName: 'p-button-danger',
          accept: async () => {
            try {
              setOperationLoading(prev => ({ ...prev, [`delete-${template.id}`]: true }));
              
              await dmcaTemplatesApi.deleteTemplate(template.id);
              
              setTemplates(prev => prev.filter(t => t.id !== template.id));
              
              toastRef.current?.show({
                severity: 'success',
                summary: 'Template Deleted',
                detail: `"${template.title}" deleted successfully`
              });
              
              loadDashboardStats();
            } catch (error: any) {
              console.error('Failed to delete template:', error);
              toastRef.current?.show({
                severity: 'error',
                summary: 'Delete Error',
                detail: error.response?.data?.detail || 'Failed to delete template'
              });
            } finally {
              setOperationLoading(prev => ({ ...prev, [`delete-${template.id}`]: false }));
            }
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
        onClick={async () => {
          try {
            setOperationLoading(prev => ({ ...prev, library: true }));
            
            const response = await dmcaTemplatesApi.getTemplateLibrary();
            
            // For now, just show a success message
            // In the future, this would open a template library dialog
            toastRef.current?.show({
              severity: 'info',
              summary: 'Template Library',
              detail: `Found ${response.data.total_count} templates in library`
            });
          } catch (error: any) {
            toastRef.current?.show({
              severity: 'error',
              summary: 'Library Error',
              detail: error.response?.data?.detail || 'Failed to load template library'
            });
          } finally {
            setOperationLoading(prev => ({ ...prev, library: false }));
          }
        }}
        loading={operationLoading.library}
      />
      <Button 
        label="Generate Template" 
        icon="pi pi-magic" 
        className="p-button-success p-button-outlined"
        onClick={() => handleGenerateTemplate()}
        loading={operationLoading.generate}
      />
      {selectedTemplates.length > 0 && (
        <Button 
          label={`Bulk Actions (${selectedTemplates.length})`}
          icon="pi pi-cog" 
          className="p-button-secondary"
          onClick={(e) => menuRef.current?.toggle(e)}
          loading={operationLoading.bulkExport || operationLoading.bulkDelete || operationLoading.bulkStatus || operationLoading.bulkDuplicate}
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
        
        {/* Real-time connection status */}
        <div className="flex align-items-center gap-2 mb-4">
          <div className={`w-2 h-2 border-round ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm text-gray-600">
            Real-time updates: {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          {connectionError && (
            <>
              <i className="pi pi-exclamation-triangle text-orange-500" />
              <span className="text-sm text-orange-600">{connectionError}</span>
              <Button 
                icon="pi pi-refresh"
                className="p-button-text p-button-sm"
                onClick={reconnect}
                tooltip="Retry connection"
              />
            </>
          )}
        </div>
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
                  value={
                    dashboardStats?.category_distribution.find(c => c.category === category)?.count ||
                    templates.filter(t => t.category === category).length
                  } 
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
              loading={loading}
              loadingIcon="pi pi-spinner"
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
                loading={operationLoading.submit}
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
                        <>
                          <Button 
                            label="Check Compliance"
                            icon="pi pi-shield"
                            className="p-button-sm p-button-outlined w-full mb-2"
                            onClick={() => handleComplianceCheck(selectedTemplate)}
                            loading={operationLoading[`compliance-${selectedTemplate.id}`]}
                          />
                          <Button 
                            label="Validate Variables"
                            icon="pi pi-check-circle"
                            className="p-button-sm p-button-outlined p-button-secondary w-full mb-2"
                            onClick={() => handleVariableValidation(selectedTemplate)}
                            loading={operationLoading[`variables-${selectedTemplate.id}`]}
                          />
                          {selectedTemplate.jurisdiction && (
                            <Button 
                              label="Check Jurisdiction"
                              icon="pi pi-globe"
                              className="p-button-sm p-button-outlined p-button-info w-full"
                              onClick={() => handleJurisdictionValidation(selectedTemplate)}
                              loading={operationLoading[`jurisdiction-${selectedTemplate.id}`]}
                            />
                          )}
                        </>
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
                  value={validationResult.compliance_score} 
                  className="w-full"
                  color={validationResult.compliance_score >= 80 ? 'green' : 
                         validationResult.compliance_score >= 60 ? 'orange' : 'red'}
                />
                <span className="font-bold">{validationResult.compliance_score}%</span>
              </div>
            </div>

            <Divider />

            <div className="grid">
              <div className="col-12 md:col-6">
                <Panel header="Required Elements" className="h-full">
                  {validationResult.required_elements.map((element, index) => (
                    <div key={index} className="flex align-items-center gap-2 mb-2">
                      <i className={`pi ${element.present ? 'pi-check text-green-500' : 'pi-times text-red-500'}`} />
                      <div className="flex-1">
                        <div className="font-medium text-sm">{element.description}</div>
                        <div className="text-xs text-gray-500">{element.legal_reference}</div>
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