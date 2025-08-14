import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Button } from 'primereact/button';
import { Dropdown, DropdownChangeEvent } from 'primereact/dropdown';
import { FileUpload, FileUploadUploadEvent } from 'primereact/fileupload';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { ProgressBar } from 'primereact/progressbar';
import { Message } from 'primereact/message';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { Toast } from 'primereact/toast';
import { confirmDialog } from 'primereact/confirmdialog';
import { Chip } from 'primereact/chip';
import { InputSwitch } from 'primereact/inputswitch';
import { Skeleton } from 'primereact/skeleton';
import { Panel } from 'primereact/panel';
import { MultiSelect, MultiSelectChangeEvent } from 'primereact/multiselect';
import { Slider } from 'primereact/slider';
import { ColorPicker, ColorPickerChangeEvent } from 'primereact/colorpicker';
import { SelectButton, SelectButtonChangeEvent } from 'primereact/selectbutton';
import { Knob } from 'primereact/knob';
import { Image } from 'primereact/image';
import { Toolbar } from 'primereact/toolbar';
import { SplitButton } from 'primereact/splitbutton';
import { MenuItem } from 'primereact/menuitem';
import { InputNumber, InputNumberChangeEvent } from 'primereact/inputnumber';
import { Accordion, AccordionTab } from 'primereact/accordion';
import { Timeline } from 'primereact/timeline';
import { Chart } from 'primereact/chart';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocketContext';
import { contentWatermarkingApi } from '../services/api';
import {
  WatermarkContent,
  WatermarkTemplate,
  WatermarkSettings,
  WatermarkType,
  WatermarkPosition,
  TemplateCategory,
  ContentStatus,
  BatchWatermarkJob,
  BatchJobStatus,
  WatermarkDetectionResult,
  DetectionConfidence,
  WatermarkingDashboard,
  WatermarkAnalytics,
  ContentCollection,
  CreateWatermarkTemplate,
  WatermarkPreview,
  TemplateLibrary,
  WatermarkingSettings,
  SystemHealth,
  ImportStatus,
  ExportRequest,
  WatermarkingWebSocketMessage,
  WatermarkingSubscription
} from '../types/api';

interface ContentWatermarkingState {
  loading: boolean;
  activeTab: number;
  
  // Content Management
  content: WatermarkContent[];
  selectedContent: WatermarkContent[];
  contentLoading: boolean;
  contentPagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
  contentFilters: {
    status?: ContentStatus;
    type?: string;
    search?: string;
  };
  
  // Templates
  templates: WatermarkTemplate[];
  selectedTemplate: WatermarkTemplate | null;
  templateLoading: boolean;
  templateLibrary: TemplateLibrary | null;
  templatePreview: WatermarkPreview | null;
  
  // Batch Operations
  batchJobs: BatchWatermarkJob[];
  activeBatchJob: BatchWatermarkJob | null;
  batchLoading: boolean;
  
  // Detection
  detectionResults: WatermarkDetectionResult[];
  detectionLoading: boolean;
  
  // Collections
  collections: ContentCollection[];
  selectedCollection: ContentCollection | null;
  
  // Analytics
  dashboard: WatermarkingDashboard | null;
  analytics: WatermarkAnalytics | null;
  
  // Settings
  settings: WatermarkingSettings | null;
  systemHealth: SystemHealth | null;
  
  // Import/Export
  importStatus: ImportStatus | null;
  exportInProgress: boolean;
  
  // WebSocket
  wsSubscription: WatermarkingSubscription | null;
  realTimeUpdates: WatermarkingWebSocketMessage[];
}

interface TemplateForm {
  name: string;
  type: WatermarkType;
  category: TemplateCategory;
  description: string;
  is_public: boolean;
  tags: string[];
  settings: WatermarkSettings;
  preview_file?: File;
}

interface BatchForm {
  name: string;
  content_ids: string[];
  template_id: string;
  output_format: 'original' | 'jpg' | 'png' | 'pdf';
  quality: 'low' | 'medium' | 'high';
  preserve_originals: boolean;
  notification_email: string;
}

const ContentWatermarking: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { subscribe, unsubscribe, isConnected } = useWebSocket();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);
  const detectionFileUploadRef = useRef<FileUpload>(null);
  const subscriptionIdRef = useRef<string>('watermarking-page');

  // State
  const [state, setState] = useState<ContentWatermarkingState>({
    loading: true,
    activeTab: 0,
    content: [],
    selectedContent: [],
    contentLoading: false,
    contentPagination: { page: 1, per_page: 10, total: 0, pages: 0 },
    contentFilters: {},
    templates: [],
    selectedTemplate: null,
    templateLoading: false,
    templateLibrary: null,
    templatePreview: null,
    batchJobs: [],
    activeBatchJob: null,
    batchLoading: false,
    detectionResults: [],
    detectionLoading: false,
    collections: [],
    selectedCollection: null,
    dashboard: null,
    analytics: null,
    settings: null,
    systemHealth: null,
    importStatus: null,
    exportInProgress: false,
    wsSubscription: null,
    realTimeUpdates: []
  });

  const [templateForm, setTemplateForm] = useState<TemplateForm>({
    name: '',
    type: WatermarkType.TEXT,
    category: TemplateCategory.PERSONAL,
    description: '',
    is_public: false,
    tags: [],
    settings: {
      text: {
        content: '',
        font_family: 'Arial',
        font_size: 24,
        color: '#000000',
        opacity: 0.7,
        rotation: 0,
        bold: false,
        italic: false,
        outline: false,
        shadow: false
      },
      position: {
        type: WatermarkPosition.BOTTOM_RIGHT,
        margin_x: 20,
        margin_y: 20
      },
      quality: {
        compression: 85,
        preserve_metadata: true
      }
    }
  });

  const [batchForm, setBatchForm] = useState<BatchForm>({
    name: '',
    content_ids: [],
    template_id: '',
    output_format: 'original',
    quality: 'medium',
    preserve_originals: true,
    notification_email: user?.email || ''
  });

  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Load initial data
  useEffect(() => {
    loadDashboard();
    loadContent();
    loadTemplates();
    loadCollections();
    loadSettings();
    loadSystemHealth();
    setupWebSocketSubscription();
    setState(prev => ({ ...prev, loading: false }));
  }, []);

  // Load dashboard data
  const loadDashboard = useCallback(async () => {
    try {
      const response = await contentWatermarkingApi.getDashboard();
      setState(prev => ({ ...prev, dashboard: response.data }));
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load dashboard data'
      });
    }
  }, []);

  // Load content
  const loadContent = useCallback(async (filters = state.contentFilters, pagination = state.contentPagination) => {
    try {
      setState(prev => ({ ...prev, contentLoading: true }));
      const response = await contentWatermarkingApi.getContent({
        ...filters,
        page: pagination.page,
        per_page: pagination.per_page
      });
      
      setState(prev => ({
        ...prev,
        content: response.data.items,
        contentPagination: {
          page: response.data.page,
          per_page: response.data.per_page,
          total: response.data.total,
          pages: response.data.pages
        },
        contentLoading: false
      }));
    } catch (error) {
      console.error('Failed to load content:', error);
      setState(prev => ({ ...prev, contentLoading: false }));
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load content'
      });
    }
  }, [state.contentFilters, state.contentPagination]);

  // Load templates
  const loadTemplates = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, templateLoading: true }));
      const [templatesResponse, libraryResponse] = await Promise.all([
        contentWatermarkingApi.getTemplates(),
        contentWatermarkingApi.getLibraryTemplates()
      ]);
      
      setState(prev => ({
        ...prev,
        templates: templatesResponse.data.items,
        templateLibrary: libraryResponse.data,
        templateLoading: false
      }));
    } catch (error) {
      console.error('Failed to load templates:', error);
      setState(prev => ({ ...prev, templateLoading: false }));
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load templates'
      });
    }
  }, []);

  // Load collections
  const loadCollections = useCallback(async () => {
    try {
      const response = await contentWatermarkingApi.getCollections();
      setState(prev => ({ ...prev, collections: response.data }));
    } catch (error) {
      console.error('Failed to load collections:', error);
    }
  }, []);

  // Load settings
  const loadSettings = useCallback(async () => {
    try {
      const response = await contentWatermarkingApi.getSettings();
      setState(prev => ({ ...prev, settings: response.data }));
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }, []);

  // Load system health
  const loadSystemHealth = useCallback(async () => {
    try {
      const response = await contentWatermarkingApi.getSystemHealth();
      setState(prev => ({ ...prev, systemHealth: response.data }));
    } catch (error) {
      console.error('Failed to load system health:', error);
    }
  }, []);

  // Setup WebSocket subscription for real-time updates
  const setupWebSocketSubscription = useCallback(async () => {
    try {
      const response = await contentWatermarkingApi.subscribeToUpdates({
        types: ['content_processing', 'batch_progress', 'detection_result', 'template_update'],
        content_ids: state.content.map(c => c.id),
        batch_ids: state.batchJobs.map(j => j.id)
      });
      
      setState(prev => ({ 
        ...prev, 
        wsSubscription: { 
          id: response.data.subscription_id,
          types: ['content_processing', 'batch_progress', 'detection_result', 'template_update'],
          active: true
        }
      }));
    } catch (error) {
      console.error('Failed to setup WebSocket subscription:', error);
    }
  }, [state.content, state.batchJobs]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: WatermarkingWebSocketMessage) => {
    setState(prev => ({
      ...prev,
      realTimeUpdates: [message, ...prev.realTimeUpdates.slice(0, 49)] // Keep last 50 updates
    }));

    switch (message.type) {
      case 'content_processing_complete':
        loadContent();
        loadDashboard();
        toast.current?.show({
          severity: 'success',
          summary: 'Processing Complete',
          detail: `Content "${message.payload.content?.name}" has been processed successfully`
        });
        break;
      
      case 'batch_progress_update':
        if (message.payload.batch_job) {
          setState(prev => ({
            ...prev,
            batchJobs: prev.batchJobs.map(job => 
              job.id === message.payload.batch_job.id ? message.payload.batch_job : job
            )
          }));
        }
        break;
      
      case 'watermark_detection_complete':
        setState(prev => ({
          ...prev,
          detectionResults: [message.payload.result, ...prev.detectionResults.slice(0, 19)]
        }));
        toast.current?.show({
          severity: 'info',
          summary: 'Detection Complete',
          detail: `Detected ${message.payload.result.detected_watermarks.length} watermark(s)`
        });
        break;
      
      case 'template_update':
        loadTemplates();
        break;
    }
  }, [loadContent, loadDashboard, loadTemplates]);

  // File upload handler
  const handleFileUpload = useCallback(async (event: FileUploadUploadEvent) => {
    const files = Array.isArray(event.files) ? event.files : [event.files];
    
    try {
      // Initialize progress tracking
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        files.forEach(file => {
          newProgress[file.name] = 0;
        });
        return newProgress;
      });

      // Simulate progress for demo purposes
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          files.forEach(file => {
            if (newProgress[file.name] < 90) {
              newProgress[file.name] = Math.min(90, newProgress[file.name] + Math.random() * 20);
            }
          });
          return newProgress;
        });
      }, 500);

      const response = await contentWatermarkingApi.uploadContent(files, {
        auto_organize: true,
        extract_metadata: true
      });

      clearInterval(progressInterval);
      
      // Complete progress
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        files.forEach(file => {
          newProgress[file.name] = 100;
        });
        return newProgress;
      });

      // Clear progress after a short delay
      setTimeout(() => setUploadProgress({}), 2000);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Upload Complete',
        detail: `Successfully uploaded ${files.length} file(s)`
      });

      loadContent();
      loadDashboard();
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadProgress({});
      toast.current?.show({
        severity: 'error',
        summary: 'Upload Failed',
        detail: 'Failed to upload files. Please try again.'
      });
    }
  }, [loadContent, loadDashboard]);

  // Apply watermark
  const applyWatermark = useCallback(async (contentId: string, templateId: string) => {
    try {
      await contentWatermarkingApi.applyWatermark(contentId, templateId);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Watermark applied successfully'
      });

      loadContent();
      loadDashboard();
    } catch (error) {
      console.error('Failed to apply watermark:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to apply watermark'
      });
    }
  }, [loadContent, loadDashboard]);

  // Create template
  const createTemplate = useCallback(async () => {
    try {
      const templateData: CreateWatermarkTemplate = {
        name: templateForm.name,
        type: templateForm.type,
        category: templateForm.category,
        description: templateForm.description,
        settings: templateForm.settings,
        is_public: templateForm.is_public,
        tags: templateForm.tags,
        preview_file: templateForm.preview_file
      };

      await contentWatermarkingApi.createTemplate(templateData);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Template created successfully'
      });

      setShowTemplateDialog(false);
      loadTemplates();
      resetTemplateForm();
    } catch (error) {
      console.error('Failed to create template:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to create template'
      });
    }
  }, [templateForm, loadTemplates]);

  // Reset template form
  const resetTemplateForm = () => {
    setTemplateForm({
      name: '',
      type: WatermarkType.TEXT,
      category: TemplateCategory.PERSONAL,
      description: '',
      is_public: false,
      tags: [],
      settings: {
        text: {
          content: '',
          font_family: 'Arial',
          font_size: 24,
          color: '#000000',
          opacity: 0.7,
          rotation: 0,
          bold: false,
          italic: false,
          outline: false,
          shadow: false
        },
        position: {
          type: WatermarkPosition.BOTTOM_RIGHT,
          margin_x: 20,
          margin_y: 20
        },
        quality: {
          compression: 85,
          preserve_metadata: true
        }
      }
    });
  };

  // Status templates
  const statusBodyTemplate = (rowData: WatermarkContent) => {
    const getSeverity = (status: ContentStatus) => {
      switch (status) {
        case ContentStatus.UPLOADED: return 'info';
        case ContentStatus.PROCESSING: return 'warning';
        case ContentStatus.WATERMARKED: return 'success';
        case ContentStatus.FAILED: return 'danger';
        case ContentStatus.ARCHIVED: return 'secondary';
        default: return 'info';
      }
    };

    return <Tag value={rowData.status} severity={getSeverity(rowData.status)} />;
  };

  const sizeBodyTemplate = (rowData: WatermarkContent) => {
    return `${(rowData.file_size / 1024 / 1024).toFixed(2)} MB`;
  };

  const thumbnailBodyTemplate = (rowData: WatermarkContent) => {
    return rowData.thumbnail_url ? (
      <Image src={rowData.thumbnail_url} alt={rowData.name} width="50" preview />
    ) : (
      <i className="pi pi-file text-2xl" />
    );
  };

  const actionsBodyTemplate = (rowData: WatermarkContent) => {
    const menuItems: MenuItem[] = [
      {
        label: 'Apply Watermark',
        icon: 'pi pi-plus',
        command: () => {
          if (state.selectedTemplate) {
            applyWatermark(rowData.id, state.selectedTemplate.id);
          } else {
            toast.current?.show({
              severity: 'warn',
              summary: 'Warning',
              detail: 'Please select a template first'
            });
          }
        }
      },
      {
        label: 'Download',
        icon: 'pi pi-download',
        command: async () => {
          try {
            const response = await contentWatermarkingApi.downloadContent(rowData.id, true);
            // Handle file download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = rowData.original_filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
          } catch (error) {
            toast.current?.show({
              severity: 'error',
              summary: 'Error',
              detail: 'Failed to download file'
            });
          }
        }
      },
      {
        label: 'Delete',
        icon: 'pi pi-trash',
        command: () => {
          confirmDialog({
            message: 'Are you sure you want to delete this content?',
            header: 'Delete Confirmation',
            icon: 'pi pi-exclamation-triangle',
            accept: async () => {
              try {
                await contentWatermarkingApi.deleteContent(rowData.id);
                toast.current?.show({
                  severity: 'success',
                  summary: 'Success',
                  detail: 'Content deleted successfully'
                });
                loadContent();
                loadDashboard();
              } catch (error) {
                toast.current?.show({
                  severity: 'error',
                  summary: 'Error',
                  detail: 'Failed to delete content'
                });
              }
            }
          });
        }
      }
    ];

    return <SplitButton label="Actions" icon="pi pi-cog" model={menuItems} />;
  };

  // Dashboard overview cards
  const renderDashboardOverview = () => {
    if (!state.dashboard) return <Skeleton height="200px" />;

    const { overview } = state.dashboard;

    return (
      <div className="grid">
        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="flex align-items-center">
              <div className="flex-1">
                <div className="text-2xl font-bold text-primary">{overview.total_content}</div>
                <div className="text-sm text-500">Total Content</div>
              </div>
              <i className="pi pi-file text-3xl text-primary" />
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="flex align-items-center">
              <div className="flex-1">
                <div className="text-2xl font-bold text-green-500">{overview.watermarked_content}</div>
                <div className="text-sm text-500">Watermarked</div>
              </div>
              <i className="pi pi-shield text-3xl text-green-500" />
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="flex align-items-center">
              <div className="flex-1">
                <div className="text-2xl font-bold text-orange-500">{overview.active_jobs}</div>
                <div className="text-sm text-500">Active Jobs</div>
              </div>
              <i className="pi pi-cog text-3xl text-orange-500" />
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="flex align-items-center">
              <div className="flex-1">
                <div className="text-2xl font-bold text-blue-500">{(overview.storage_used / 1024 / 1024 / 1024).toFixed(1)} GB</div>
                <div className="text-sm text-500">Storage Used</div>
              </div>
              <i className="pi pi-database text-3xl text-blue-500" />
            </div>
          </Card>
        </div>
      </div>
    );
  };

  if (state.loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Card>
            <Skeleton height="4rem" className="mb-2" />
            <Skeleton height="20rem" />
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="grid">
      <Toast ref={toast} />
      
      <div className="col-12">
        <div className="flex justify-content-between align-items-center mb-4">
          <div>
            <div className="flex align-items-center gap-3">
              <h2 className="text-3xl font-bold text-900 mb-2">Content Watermarking</h2>
              {isConnected ? (
                <Tag icon="pi pi-check-circle" value="Connected" severity="success" className="font-normal" />
              ) : (
                <Tag icon="pi pi-times-circle" value="Disconnected" severity="danger" className="font-normal" />
              )}
            </div>
            <p className="text-600 m-0">Protect your content with digital watermarks and detect unauthorized usage</p>
          </div>
          <div className="flex gap-2">
            <Button
              label="Import Content"
              icon="pi pi-upload"
              className="p-button-outlined"
              onClick={() => fileUploadRef.current?.choose()}
            />
            <Button
              label="Batch Operations"
              icon="pi pi-list"
              className="p-button-outlined"
              onClick={() => setShowBatchDialog(true)}
              disabled={state.content.length === 0 || state.templates.length === 0}
            />
            <Button
              label="New Template"
              icon="pi pi-plus"
              onClick={() => setShowTemplateDialog(true)}
            />
          </div>
        </div>
      </div>

      <div className="col-12">
        <Card>
          <TabView activeIndex={state.activeTab} onTabChange={(e) => setState(prev => ({ ...prev, activeTab: e.index }))}>
            {/* Dashboard Tab */}
            <TabPanel header="Dashboard" leftIcon="pi pi-chart-line">
              <div className="grid">
                <div className="col-12">
                  {renderDashboardOverview()}
                </div>
                
                <div className="col-12 md:col-8">
                  <Card title="Recent Activity">
                    {state.dashboard?.recent_activity ? (
                      <Timeline 
                        value={state.dashboard.recent_activity.map(activity => ({
                          status: activity.status,
                          date: new Date(activity.timestamp).toLocaleString(),
                          icon: activity.status === 'success' ? 'pi pi-check' : 
                                activity.status === 'failed' ? 'pi pi-times' : 'pi pi-exclamation-triangle',
                          color: activity.status === 'success' ? '#10B981' : 
                                 activity.status === 'failed' ? '#EF4444' : '#F59E0B',
                          description: activity.description
                        }))} 
                        content={(item) => (
                          <div>
                            <div className="font-semibold">{item.description}</div>
                            <div className="text-sm text-500">{item.date}</div>
                          </div>
                        )}
                      />
                    ) : (
                      <Skeleton height="300px" />
                    )}
                  </Card>
                </div>
                
                <div className="col-12 md:col-4">
                  <Card title="Processing Queue">
                    {state.dashboard?.processing_queue ? (
                      <div>
                        <div className="flex justify-content-between align-items-center mb-3">
                          <span>Pending Jobs</span>
                          <Badge value={state.dashboard.processing_queue.pending_jobs} severity="info" />
                        </div>
                        <div className="flex justify-content-between align-items-center mb-3">
                          <span>Estimated Time</span>
                          <span className="text-600">{state.dashboard.processing_queue.estimated_time}</span>
                        </div>
                        {state.dashboard.processing_queue.current_job && (
                          <div>
                            <div className="text-sm text-600 mb-2">Current Job: {state.dashboard.processing_queue.current_job.name}</div>
                            <ProgressBar value={state.dashboard.processing_queue.current_job.progress} />
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center text-500">No active jobs</div>
                    )}
                  </Card>
                  
                  {state.systemHealth && (
                    <Card title="System Health" className="mt-3">
                      <div className="flex align-items-center gap-2 mb-3">
                        <i className={`pi ${
                          state.systemHealth.status === 'healthy' ? 'pi-check-circle text-green-500' :
                          state.systemHealth.status === 'degraded' ? 'pi-exclamation-triangle text-orange-500' :
                          'pi-times-circle text-red-500'
                        }`} />
                        <span className={`font-semibold ${
                          state.systemHealth.status === 'healthy' ? 'text-green-500' :
                          state.systemHealth.status === 'degraded' ? 'text-orange-500' :
                          'text-red-500'
                        }`}>
                          {state.systemHealth.status.charAt(0).toUpperCase() + state.systemHealth.status.slice(1)}
                        </span>
                      </div>
                      <div className="grid">
                        <div className="col-6">
                          <div className="text-sm text-600">Uptime</div>
                          <div className="font-semibold">{state.systemHealth.performance.uptime}%</div>
                        </div>
                        <div className="col-6">
                          <div className="text-sm text-600">Queue Size</div>
                          <div className="font-semibold">{state.systemHealth.performance.queue_size}</div>
                        </div>
                      </div>
                    </Card>
                  )}
                </div>
              </div>
            </TabPanel>

            {/* Content Management Tab */}
            <TabPanel header="Content Library" leftIcon="pi pi-images">
              <div className="mb-4">
                <Toolbar
                  left={
                    <div className="flex gap-2">
                      <FileUpload
                        ref={fileUploadRef}
                        mode="advanced"
                        multiple
                        accept="image/*,video/*,.pdf"
                        maxFileSize={100000000}
                        customUpload
                        uploadHandler={handleFileUpload}
                        auto
                        chooseLabel="Upload Files"
                        uploadLabel="Processing..."
                        cancelLabel="Cancel"
                        className="p-fileupload-basic"
                        progressBarTemplate={() => {
                          const progressEntries = Object.entries(uploadProgress);
                          if (progressEntries.length === 0) return null;
                          
                          return (
                            <div className="mt-2">
                              {progressEntries.map(([filename, progress]) => (
                                <div key={filename} className="mb-2">
                                  <div className="flex justify-content-between align-items-center mb-1">
                                    <small className="text-600">{filename}</small>
                                    <small className="text-600">{Math.round(progress)}%</small>
                                  </div>
                                  <ProgressBar value={progress} className="mb-1" style={{ height: '4px' }} />
                                </div>
                              ))}
                            </div>
                          );
                        }}
                      />
                    </div>
                  }
                  right={
                    <div className="flex gap-2">
                      <InputText
                        placeholder="Search content..."
                        value={state.contentFilters.search || ''}
                        onChange={(e) => setState(prev => ({
                          ...prev,
                          contentFilters: { ...prev.contentFilters, search: e.target.value }
                        }))}
                        className="w-20rem"
                      />
                      <Dropdown
                        placeholder="Filter by status"
                        value={state.contentFilters.status}
                        onChange={(e: DropdownChangeEvent) => setState(prev => ({
                          ...prev,
                          contentFilters: { ...prev.contentFilters, status: e.value }
                        }))}
                        options={Object.values(ContentStatus).map(status => ({ label: status, value: status }))}
                        showClear
                        className="w-12rem"
                      />
                    </div>
                  }
                />
              </div>

              <DataTable
                value={state.content}
                selection={state.selectedContent}
                onSelectionChange={(e) => setState(prev => ({ ...prev, selectedContent: e.value }))}
                dataKey="id"
                loading={state.contentLoading}
                paginator
                rows={state.contentPagination.per_page}
                totalRecords={state.contentPagination.total}
                lazy
                onPage={(e) => {
                  const newPagination = {
                    ...state.contentPagination,
                    page: (e.page || 0) + 1
                  };
                  loadContent(state.contentFilters, newPagination);
                }}
                className="p-datatable-gridlines"
                emptyMessage="No content found"
              >
                <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
                <Column field="thumbnail_url" header="Preview" body={thumbnailBodyTemplate} style={{ width: '80px' }} />
                <Column field="name" header="Name" sortable />
                <Column field="content_type" header="Type" sortable />
                <Column field="file_size" header="Size" body={sizeBodyTemplate} />
                <Column field="status" header="Status" body={statusBodyTemplate} sortable />
                <Column field="watermarked_versions" header="Versions" body={(rowData) => rowData.watermarked_versions.length} />
                <Column field="uploaded_at" header="Uploaded" body={(rowData) => new Date(rowData.uploaded_at).toLocaleDateString()} sortable />
                <Column body={actionsBodyTemplate} style={{ width: '120px' }} />
              </DataTable>
            </TabPanel>

            {/* Templates Tab */}
            <TabPanel header="Templates" leftIcon="pi pi-palette">
              <div className="mb-4">
                <Toolbar
                  left={
                    <div className="flex gap-2 align-items-center">
                      <Button
                        label="New Template"
                        icon="pi pi-plus"
                        onClick={() => setShowTemplateDialog(true)}
                      />
                      <Button
                        label="Import Template"
                        icon="pi pi-upload"
                        className="p-button-outlined"
                        onClick={() => {
                          toast.current?.show({
                            severity: 'info',
                            summary: 'Import Template',
                            detail: 'Template import functionality coming soon...'
                          });
                        }}
                      />
                    </div>
                  }
                  right={
                    <div className="flex gap-2">
                      <InputText
                        placeholder="Search templates..."
                        className="w-20rem"
                      />
                      <Dropdown
                        placeholder="Filter by category"
                        options={[
                          { label: 'Personal', value: 'personal' },
                          { label: 'Business', value: 'business' },
                          { label: 'Brand', value: 'brand' },
                          { label: 'Copyright', value: 'copyright' }
                        ]}
                        className="w-12rem"
                        showClear
                      />
                    </div>
                  }
                />
              </div>

              <div className="grid">
                {state.templates.map(template => (
                  <div key={template.id} className="col-12 md:col-6 lg:col-4">
                    <Card className="h-full">
                      <div className="flex justify-content-between align-items-start mb-3">
                        <div>
                          <h4 className="m-0 mb-1">{template.name}</h4>
                          <small className="text-500">{template.category}</small>
                        </div>
                        <Tag value={template.type} severity="info" />
                      </div>
                      
                      {template.preview_url && (
                        <div className="mb-3">
                          <Image 
                            src={template.preview_url} 
                            alt={template.name}
                            width="100%" 
                            height="120px"
                            style={{ objectFit: 'cover' }}
                            preview
                          />
                        </div>
                      )}
                      
                      <p className="text-600 text-sm mb-3">{template.description}</p>
                      
                      <div className="flex justify-content-between align-items-center">
                        <div className="flex gap-1">
                          {template.tags?.map(tag => (
                            <Chip key={tag} label={tag} className="p-chip-sm" />
                          )) || null}
                        </div>
                        
                        <div className="flex gap-1">
                          <Button
                            icon="pi pi-eye"
                            className="p-button-text p-button-sm"
                            onClick={() => {
                              setState(prev => ({ ...prev, selectedTemplate: template }));
                              setShowPreview(true);
                            }}
                            tooltip="Preview"
                          />
                          <Button
                            icon="pi pi-copy"
                            className="p-button-text p-button-sm"
                            onClick={async () => {
                              try {
                                await contentWatermarkingApi.duplicateTemplate(template.id);
                                toast.current?.show({
                                  severity: 'success',
                                  summary: 'Success',
                                  detail: 'Template duplicated successfully'
                                });
                                loadTemplates();
                              } catch (error) {
                                toast.current?.show({
                                  severity: 'error',
                                  summary: 'Error',
                                  detail: 'Failed to duplicate template'
                                });
                              }
                            }}
                            tooltip="Duplicate"
                          />
                          <Button
                            icon="pi pi-trash"
                            className="p-button-text p-button-sm p-button-danger"
                            onClick={() => {
                              confirmDialog({
                                message: 'Are you sure you want to delete this template?',
                                header: 'Delete Template',
                                icon: 'pi pi-exclamation-triangle',
                                accept: async () => {
                                  try {
                                    await contentWatermarkingApi.deleteTemplate(template.id);
                                    toast.current?.show({
                                      severity: 'success',
                                      summary: 'Success',
                                      detail: 'Template deleted successfully'
                                    });
                                    loadTemplates();
                                  } catch (error) {
                                    toast.current?.show({
                                      severity: 'error',
                                      summary: 'Error',
                                      detail: 'Failed to delete template'
                                    });
                                  }
                                }
                              });
                            }}
                            tooltip="Delete"
                          />
                        </div>
                      </div>
                    </Card>
                  </div>
                ))}
                
                {state.templates.length === 0 && (
                  <div className="col-12 text-center py-8">
                    <i className="pi pi-palette text-6xl text-400 mb-4" />
                    <h3 className="text-900 mb-3">No Templates Found</h3>
                    <p className="text-600 mb-4">Create your first watermark template to get started.</p>
                    <Button
                      label="Create Template"
                      icon="pi pi-plus"
                      onClick={() => setShowTemplateDialog(true)}
                    />
                  </div>
                )}
              </div>
            </TabPanel>

            {/* Detection Tab */}
            <TabPanel header="Detection" leftIcon="pi pi-search">
              <div className="mb-4">
                <Toolbar
                  left={
                    <div className="flex gap-2">
                      <Button
                        label="Upload for Detection"
                        icon="pi pi-upload"
                        onClick={() => detectionFileUploadRef.current?.choose()}
                      />
                      <Button
                        label="Bulk Detection"
                        icon="pi pi-list"
                        className="p-button-outlined"
                        onClick={() => {
                          toast.current?.show({
                            severity: 'info',
                            summary: 'Bulk Detection',
                            detail: 'Bulk detection feature coming soon...'
                          });
                        }}
                      />
                    </div>
                  }
                  right={
                    <div className="flex gap-2">
                      <Dropdown
                        placeholder="Sensitivity"
                        value="medium"
                        options={[
                          { label: 'Low', value: 'low' },
                          { label: 'Medium', value: 'medium' },
                          { label: 'High', value: 'high' }
                        ]}
                        className="w-10rem"
                      />
                    </div>
                  }
                />
              </div>

              <div className="grid">
                <div className="col-12 md:col-8">
                  <Card title="Detection Results">
                    <DataTable
                      value={state.detectionResults}
                      loading={state.detectionLoading}
                      emptyMessage="No detection results found"
                      paginator
                      rows={10}
                      className="p-datatable-gridlines"
                    >
                      <Column field="id" header="ID" style={{ width: '80px' }} />
                      <Column field="filename" header="File" />
                      <Column 
                        field="detected_watermarks" 
                        header="Detected" 
                        body={(rowData) => (
                          <Badge 
                            value={rowData.detected_watermarks.length} 
                            severity={rowData.detected_watermarks.length > 0 ? 'success' : 'secondary'}
                          />
                        )} 
                      />
                      <Column 
                        field="confidence_score" 
                        header="Confidence" 
                        body={(rowData) => (
                          <ProgressBar value={rowData.confidence_score * 100} style={{ height: '6px' }} />
                        )} 
                      />
                      <Column 
                        field="processed_at" 
                        header="Processed" 
                        body={(rowData) => new Date(rowData.processed_at).toLocaleDateString()} 
                      />
                      <Column 
                        body={(rowData) => (
                          <Button
                            icon="pi pi-eye"
                            className="p-button-text p-button-sm"
                            onClick={() => {
                              // Show detailed detection results
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Detection Details',
                                detail: `Found ${rowData.detected_watermarks.length} watermark(s) with ${Math.round(rowData.confidence_score * 100)}% confidence`
                              });
                            }}
                          />
                        )}
                        style={{ width: '50px' }}
                      />
                    </DataTable>
                  </Card>
                </div>
                
                <div className="col-12 md:col-4">
                  <Card title="Detection Statistics">
                    <div className="grid">
                      <div className="col-6">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-500">
                            {state.detectionResults.length}
                          </div>
                          <div className="text-sm text-500">Total Scanned</div>
                        </div>
                      </div>
                      <div className="col-6">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-500">
                            {state.detectionResults.filter(r => r.detected_watermarks.length > 0).length}
                          </div>
                          <div className="text-sm text-500">Detected</div>
                        </div>
                      </div>
                      <div className="col-12">
                        <div className="text-center mt-3">
                          <div className="text-lg font-semibold">
                            {state.detectionResults.length > 0 
                              ? Math.round((state.detectionResults.filter(r => r.detected_watermarks.length > 0).length / state.detectionResults.length) * 100)
                              : 0}%
                          </div>
                          <div className="text-sm text-500">Detection Rate</div>
                        </div>
                      </div>
                    </div>
                  </Card>
                  
                  <Card title="Recent Detections" className="mt-3">
                    <Timeline 
                      value={state.detectionResults.slice(0, 5).map(result => ({
                        status: result.detected_watermarks.length > 0 ? 'Detected' : 'None Found',
                        date: new Date(result.processed_at).toLocaleString(),
                        icon: result.detected_watermarks.length > 0 ? 'pi pi-check' : 'pi pi-times',
                        color: result.detected_watermarks.length > 0 ? '#10B981' : '#6B7280',
                        file: result.filename
                      }))} 
                      content={(item) => (
                        <div>
                          <div className="font-semibold">{item.file}</div>
                          <div className="text-sm text-500">{item.status} - {item.date}</div>
                        </div>
                      )}
                      className="custom-timeline"
                    />
                  </Card>
                </div>
              </div>

              <FileUpload
                ref={detectionFileUploadRef}
                style={{ display: 'none' }}
                mode="advanced"
                multiple
                accept="image/*,video/*,.pdf"
                maxFileSize={50000000}
                customUpload
                uploadHandler={async (e) => {
                  const files = Array.isArray(e.files) ? e.files : [e.files];
                  
                  try {
                    setState(prev => ({ ...prev, detectionLoading: true }));
                    
                    const response = await contentWatermarkingApi.bulkDetection(files, {
                      sensitivity: 'medium',
                      expected_templates: state.templates.map(t => t.id)
                    });
                    
                    setState(prev => ({ ...prev, detectionLoading: false }));
                    
                    toast.current?.show({
                      severity: 'success',
                      summary: 'Detection Complete',
                      detail: `Analyzed ${files.length} file(s) for watermarks`
                    });
                  } catch (error) {
                    setState(prev => ({ ...prev, detectionLoading: false }));
                    toast.current?.show({
                      severity: 'error',
                      summary: 'Detection Failed',
                      detail: 'Failed to analyze files for watermarks'
                    });
                  }
                }}
              />
            </TabPanel>

            {/* Analytics Tab */}
            <TabPanel header="Analytics" leftIcon="pi pi-chart-bar">
              <div className="mb-4">
                <Toolbar
                  left={
                    <div className="flex gap-2">
                      <Button
                        label="Generate Report"
                        icon="pi pi-file-pdf"
                        onClick={() => {
                          toast.current?.show({
                            severity: 'info',
                            summary: 'Report Generation',
                            detail: 'Generating comprehensive analytics report...'
                          });
                        }}
                      />
                      <Button
                        label="Export Data"
                        icon="pi pi-download"
                        className="p-button-outlined"
                        onClick={() => {
                          toast.current?.show({
                            severity: 'info',
                            summary: 'Export Data',
                            detail: 'Exporting analytics data...'
                          });
                        }}
                      />
                    </div>
                  }
                  right={
                    <div className="flex gap-2 align-items-center">
                      <label className="font-semibold">Date Range:</label>
                      <Dropdown
                        value="last_30_days"
                        options={[
                          { label: 'Last 7 Days', value: 'last_7_days' },
                          { label: 'Last 30 Days', value: 'last_30_days' },
                          { label: 'Last 90 Days', value: 'last_90_days' },
                          { label: 'This Year', value: 'this_year' }
                        ]}
                        className="w-12rem"
                      />
                    </div>
                  }
                />
              </div>

              <div className="grid">
                <div className="col-12 md:col-6 lg:col-3">
                  <Card className="h-full">
                    <div className="flex align-items-center">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-blue-500">
                          {state.analytics?.usage_stats?.watermarks_applied || 0}
                        </div>
                        <div className="text-sm text-500">Watermarks Applied</div>
                        <div className="text-xs text-green-500 mt-1">+12% this month</div>
                      </div>
                      <i className="pi pi-shield text-3xl text-blue-500" />
                    </div>
                  </Card>
                </div>
                
                <div className="col-12 md:col-6 lg:col-3">
                  <Card className="h-full">
                    <div className="flex align-items-center">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-green-500">
                          {state.analytics?.usage_stats?.watermarks_detected || 0}
                        </div>
                        <div className="text-sm text-500">Watermarks Detected</div>
                        <div className="text-xs text-green-500 mt-1">+8% this month</div>
                      </div>
                      <i className="pi pi-search text-3xl text-green-500" />
                    </div>
                  </Card>
                </div>
                
                <div className="col-12 md:col-6 lg:col-3">
                  <Card className="h-full">
                    <div className="flex align-items-center">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-orange-500">
                          {state.analytics?.usage_stats?.processing_time_avg || '0s'}
                        </div>
                        <div className="text-sm text-500">Avg Processing Time</div>
                        <div className="text-xs text-green-500 mt-1">-15% this month</div>
                      </div>
                      <i className="pi pi-clock text-3xl text-orange-500" />
                    </div>
                  </Card>
                </div>
                
                <div className="col-12 md:col-6 lg:col-3">
                  <Card className="h-full">
                    <div className="flex align-items-center">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-purple-500">
                          {state.analytics?.usage_stats?.success_rate ? Math.round(state.analytics.usage_stats.success_rate * 100) : 0}%
                        </div>
                        <div className="text-sm text-500">Success Rate</div>
                        <div className="text-xs text-green-500 mt-1">+3% this month</div>
                      </div>
                      <i className="pi pi-check-circle text-3xl text-purple-500" />
                    </div>
                  </Card>
                </div>
                
                <div className="col-12 md:col-8">
                  <Card title="Processing Trends">
                    <Chart 
                      type="line" 
                      data={{
                        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                        datasets: [{
                          label: 'Watermarks Applied',
                          data: [12, 19, 8, 15, 22, 18],
                          borderColor: '#3B82F6',
                          backgroundColor: 'rgba(59, 130, 246, 0.1)',
                          tension: 0.4
                        }, {
                          label: 'Detections',
                          data: [5, 8, 12, 6, 9, 15],
                          borderColor: '#10B981',
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          tension: 0.4
                        }]
                      }}
                      options={{
                        plugins: {
                          legend: {
                            display: true,
                            position: 'top'
                          }
                        },
                        scales: {
                          y: {
                            beginAtZero: true
                          }
                        }
                      }}
                      height="300px"
                    />
                  </Card>
                </div>
                
                <div className="col-12 md:col-4">
                  <Card title="Content Types">
                    <Chart 
                      type="doughnut"
                      data={{
                        labels: ['Images', 'Videos', 'Documents'],
                        datasets: [{
                          data: [45, 35, 20],
                          backgroundColor: ['#3B82F6', '#10B981', '#F59E0B']
                        }]
                      }}
                      options={{
                        plugins: {
                          legend: {
                            display: true,
                            position: 'bottom'
                          }
                        }
                      }}
                      height="250px"
                    />
                  </Card>
                  
                  <Card title="Template Usage" className="mt-3">
                    <div className="space-y-3">
                      {state.templates.slice(0, 5).map((template, index) => (
                        <div key={template.id} className="flex justify-content-between align-items-center">
                          <span className="text-sm">{template.name}</span>
                          <div className="flex align-items-center gap-2">
                            <ProgressBar 
                              value={(5 - index) * 20} 
                              style={{ width: '60px', height: '6px' }}
                            />
                            <span className="text-xs text-500">{(5 - index) * 20}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </div>
            </TabPanel>
          </TabView>
        </Card>
      </div>

      {/* Template Creation Dialog */}
      {showTemplateDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex align-items-center justify-content-center z-50">
          <Card className="w-11 max-w-4xl max-h-screen overflow-auto">
            <div className="flex justify-content-between align-items-center mb-4">
              <h3 className="m-0">Create Watermark Template</h3>
              <Button
                icon="pi pi-times"
                className="p-button-text p-button-rounded"
                onClick={() => {
                  setShowTemplateDialog(false);
                  resetTemplateForm();
                }}
              />
            </div>
            
            <div className="grid">
              <div className="col-12 md:col-6">
                <div className="field">
                  <label htmlFor="template-name" className="block">Name *</label>
                  <InputText
                    id="template-name"
                    value={templateForm.name}
                    onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full"
                    placeholder="Enter template name"
                  />
                </div>
              </div>
              
              <div className="col-12 md:col-6">
                <div className="field">
                  <label htmlFor="template-type" className="block">Type *</label>
                  <Dropdown
                    id="template-type"
                    value={templateForm.type}
                    onChange={(e: DropdownChangeEvent) => setTemplateForm(prev => ({ ...prev, type: e.value }))}
                    options={Object.values(WatermarkType).map(type => ({ label: type, value: type }))}
                    className="w-full"
                    placeholder="Select type"
                  />
                </div>
              </div>

              <div className="col-12">
                <div className="field">
                  <label htmlFor="template-description" className="block">Description</label>
                  <InputTextarea
                    id="template-description"
                    value={templateForm.description}
                    onChange={(e) => setTemplateForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full"
                    placeholder="Enter template description"
                  />
                </div>
              </div>

              {templateForm.type === WatermarkType.TEXT && (
                <div className="col-12">
                  <Panel header="Text Settings" className="mb-4">
                    <div className="grid">
                      <div className="col-12 md:col-6">
                        <div className="field">
                          <label htmlFor="text-content" className="block">Text Content *</label>
                          <InputText
                            id="text-content"
                            value={templateForm.settings.text?.content || ''}
                            onChange={(e) => setTemplateForm(prev => ({
                              ...prev,
                              settings: {
                                ...prev.settings,
                                text: { ...prev.settings.text!, content: e.target.value }
                              }
                            }))}
                            className="w-full"
                            placeholder="Enter watermark text"
                          />
                        </div>
                      </div>

                      <div className="col-12 md:col-6">
                        <div className="field">
                          <label htmlFor="text-opacity" className="block">Opacity: {Math.round((templateForm.settings.text?.opacity || 0.7) * 100)}%</label>
                          <Slider
                            id="text-opacity"
                            value={(templateForm.settings.text?.opacity || 0.7) * 100}
                            onChange={(e) => setTemplateForm(prev => ({
                              ...prev,
                              settings: {
                                ...prev.settings,
                                text: { ...prev.settings.text!, opacity: (e.value as number) / 100 }
                              }
                            }))}
                            min={0}
                            max={100}
                            className="w-full"
                          />
                        </div>
                      </div>
                    </div>
                  </Panel>
                </div>
              )}
            </div>
            
            <div className="flex justify-content-end gap-2 mt-4">
              <Button
                label="Cancel"
                className="p-button-outlined"
                onClick={() => {
                  setShowTemplateDialog(false);
                  resetTemplateForm();
                }}
              />
              <Button
                label="Create Template"
                onClick={createTemplate}
                disabled={!templateForm.name || (templateForm.type === WatermarkType.TEXT && !templateForm.settings.text?.content)}
              />
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ContentWatermarking;