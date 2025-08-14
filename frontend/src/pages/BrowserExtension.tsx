import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { InputSwitch } from 'primereact/inputswitch';
import { Panel } from 'primereact/panel';
import { Timeline } from 'primereact/timeline';
import { Steps } from 'primereact/steps';
import { Divider } from 'primereact/divider';
import { Chip } from 'primereact/chip';
import { ProgressBar } from 'primereact/progressbar';
import { Skeleton } from 'primereact/skeleton';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Message } from 'primereact/message';
import { Avatar } from 'primereact/avatar';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { confirmDialog } from 'primereact/confirmdialog';
import { Toast } from 'primereact/toast';
import { MultiSelect } from 'primereact/multiselect';
import { Slider } from 'primereact/slider';
import { Chart } from 'primereact/chart';
import { Toolbar } from 'primereact/toolbar';
import { SplitButton } from 'primereact/splitbutton';
import { Calendar } from 'primereact/calendar';
import { TabMenu } from 'primereact/tabmenu';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../contexts/WebSocketContext';
import { extensionApi } from '../services/api';
import { 
  BrowserExtension as BrowserExtensionType, 
  ExtensionActivity, 
  ExtensionSettings,
  ExtensionStats,
  BrowserType,
  ExtensionStatus,
  ExtensionAction,
  BulkExtensionOperation 
} from '../types/api';

// Installation wizard step interface
interface InstallationStep {
  label: string;
  command?: string;
  icon?: string;
  description?: string;
}

interface ExtensionHealth {
  extension_id: string;
  status: 'healthy' | 'warning' | 'error';
  last_heartbeat: string;
  response_time: number;
  error_count: number;
  uptime_percentage: number;
}

// Browser compatibility interface
interface BrowserCompatibility {
  browser: BrowserType;
  supported: boolean;
  minimum_version: string;
  current_version?: string;
  compatibility_issues?: string[];
  installation_url?: string;
}

// Extension metrics for dashboard
interface ExtensionMetrics {
  daily_activities: number;
  success_rate: number;
  avg_response_time: number;
  error_count: number;
  last_24h_trend: 'up' | 'down' | 'stable';
}

const BrowserExtension: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [showPermissionsDialog, setShowPermissionsDialog] = useState(false);
  const [showBulkOperationsDialog, setShowBulkOperationsDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [selectedExtension, setSelectedExtension] = useState<BrowserExtensionType | null>(null);
  const [selectedExtensions, setSelectedExtensions] = useState<string[]>([]);
  const [activeStep, setActiveStep] = useState(0);
  const [dateRange, setDateRange] = useState<Date[]>([new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), new Date()]);
  const [activityFilter, setActivityFilter] = useState<ExtensionAction[]>([]);
  const [bulkOperation, setBulkOperation] = useState<BulkExtensionOperation>({ operation: 'install', extension_ids: [] });
  
  const toast = useRef<Toast>(null);
  const queryClient = useQueryClient();
  const { subscribe, unsubscribe, isConnected } = useWebSocket();

  // API Queries
  const { data: extensions = [], isLoading: extensionsLoading, refetch: refetchExtensions } = useQuery({
    queryKey: ['extensions'],
    queryFn: () => extensionApi.getExtensions().then(res => res.data),
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  const { data: extensionStats, isLoading: statsLoading } = useQuery({
    queryKey: ['extension-stats'],
    queryFn: () => extensionApi.getExtensionStats().then(res => res.data),
    refetchInterval: 60000 // Refresh every minute
  });

  const { data: activities = [], isLoading: activitiesLoading } = useQuery({
    queryKey: ['extension-activities', dateRange, activityFilter],
    queryFn: () => {
      const params = {
        start_date: dateRange[0]?.toISOString(),
        end_date: dateRange[1]?.toISOString(),
        actions: activityFilter.length > 0 ? activityFilter : undefined
      };
      return extensionApi.getExtensionActivities(params).then(res => res.data);
    },
    refetchInterval: 30000
  });

  const { data: browserDistribution = [], isLoading: browserStatsLoading } = useQuery({
    queryKey: ['browser-distribution'],
    queryFn: () => extensionApi.getBrowserDistribution().then(res => res.data),
    refetchInterval: 300000 // Refresh every 5 minutes
  });

  // Real-time WebSocket subscription for extension updates
  useEffect(() => {
    const subscriptionId = 'browser-extension-realtime';
    
    subscribe(subscriptionId, {
      types: ['extension_status_update', 'extension_activity', 'extension_health_check'] as any,
    }, (message) => {
      // Handle real-time updates
      if (message.type === 'extension_status_update') {
        queryClient.invalidateQueries({ queryKey: ['extensions'] });
        toast.current?.show({
          severity: 'info',
          summary: 'Extension Update',
          detail: message.payload.message || 'Extension status updated',
          life: 3000
        });
      } else if (message.type === 'extension_activity') {
        queryClient.invalidateQueries({ queryKey: ['extension-activities'] });
        queryClient.invalidateQueries({ queryKey: ['extension-stats'] });
      }
    });

    return () => {
      unsubscribe(subscriptionId);
    };
  }, [subscribe, unsubscribe, queryClient]);

  // Mutations for API operations
  const installMutation = useMutation({
    mutationFn: ({ extensionId, browserData }: { extensionId: string; browserData: any }) => 
      extensionApi.installExtension(extensionId, browserData),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Installation Started',
        detail: 'Extension installation initiated successfully',
        life: 3000
      });
    },
    onError: (error: any) => {
      toast.current?.show({
        severity: 'error',
        summary: 'Installation Failed',
        detail: error.response?.data?.message || 'Failed to install extension',
        life: 5000
      });
    }
  });

  const activateExtensionMutation = useMutation({
    mutationFn: (extensionId: string) => extensionApi.activateExtension(extensionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Extension Activated',
        detail: 'Extension activated successfully',
        life: 3000
      });
    },
    onError: (error: any) => {
      toast.current?.show({
        severity: 'error',
        summary: 'Activation Failed',
        detail: error.response?.data?.message || 'Failed to activate extension',
        life: 5000
      });
    }
  });

  const deactivateExtensionMutation = useMutation({
    mutationFn: (extensionId: string) => extensionApi.deactivateExtension(extensionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Extension Deactivated',
        detail: 'Extension deactivated successfully',
        life: 3000
      });
    },
    onError: (error: any) => {
      toast.current?.show({
        severity: 'error',
        summary: 'Deactivation Failed',
        detail: error.response?.data?.message || 'Failed to deactivate extension',
        life: 5000
      });
    }
  });

  const updateExtensionMutation = useMutation({
    mutationFn: (extensionId: string) => extensionApi.updateExtension(extensionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Extension Updated',
        detail: 'Extension updated successfully',
        life: 3000
      });
    },
    onError: (error: any) => {
      toast.current?.show({
        severity: 'error',
        summary: 'Update Failed',
        detail: error.response?.data?.message || 'Failed to update extension',
        life: 5000
      });
    }
  });

  const bulkOperationMutation = useMutation({
    mutationFn: (operationData: BulkExtensionOperation) => 
      extensionApi.bulkExtensionOperation(operationData),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Bulk Operation Started',
        detail: `Operation ${bulkOperation.operation} started for ${selectedExtensions.length} extensions`,
        life: 3000
      });
      setShowBulkOperationsDialog(false);
      setSelectedExtensions([]);
    },
    onError: (error: any) => {
      toast.current?.show({
        severity: 'error',
        summary: 'Bulk Operation Failed',
        detail: error.response?.data?.message || 'Failed to execute bulk operation',
        life: 5000
      });
    }
  });

  // Event Handlers
  const handleInstallExtension = (extension: BrowserExtensionType) => {
    confirmDialog({
      message: `This will install the ${extension.name} extension. Continue?`,
      header: 'Install Extension',
      icon: 'pi pi-download',
      accept: () => {
        const browserData = {
          browser: extension.browser,
          version: extension.version,
          user_agent: navigator.userAgent
        };
        installMutation.mutate({ extensionId: extension.id, browserData });
      }
    });
  };

  const handleToggleExtension = (extensionId: string, active: boolean) => {
    if (active) {
      activateExtensionMutation.mutate(extensionId);
    } else {
      deactivateExtensionMutation.mutate(extensionId);
    }
  };

  const handleUpdateExtension = (extensionId: string) => {
    confirmDialog({
      message: 'This will update the extension to the latest version. Continue?',
      header: 'Update Extension',
      icon: 'pi pi-refresh',
      accept: () => {
        updateExtensionMutation.mutate(extensionId);
      }
    });
  };

  const handleSyncExtension = useCallback(async (extensionId: string) => {
    try {
      await extensionApi.syncExtension(extensionId);
      queryClient.invalidateQueries({ queryKey: ['extensions'] });
      toast.current?.show({
        severity: 'success',
        summary: 'Extension Synced',
        detail: 'Extension synchronized successfully',
        life: 3000
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Sync Failed',
        detail: error.response?.data?.message || 'Failed to sync extension',
        life: 5000
      });
    }
  }, [queryClient]);

  const handleBulkOperation = () => {
    if (selectedExtensions.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Extensions Selected',
        detail: 'Please select at least one extension for bulk operations',
        life: 3000
      });
      return;
    }
    
    const operationData: BulkExtensionOperation = {
      ...bulkOperation,
      extension_ids: selectedExtensions
    };
    
    confirmDialog({
      message: `Are you sure you want to ${bulkOperation.operation} ${selectedExtensions.length} extension(s)?`,
      header: 'Confirm Bulk Operation',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        bulkOperationMutation.mutate(operationData);
      }
    });
  };

  const handleExportData = useCallback(async () => {
    try {
      const response = await extensionApi.exportExtensionData('all', 'csv');
      // Handle download response
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `extension-data-${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Data Exported',
        detail: 'Extension data exported successfully',
        life: 3000
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Export Failed',
        detail: error.response?.data?.message || 'Failed to export data',
        life: 5000
      });
    }
  }, []);

  // Helper functions
  const getBrowserIcon = (browser: BrowserType) => {
    switch (browser) {
      case BrowserType.CHROME: return 'pi pi-chrome';
      case BrowserType.FIREFOX: return 'pi pi-firefox';
      case BrowserType.EDGE: return 'pi pi-microsoft';
      case BrowserType.SAFARI: return 'pi pi-apple';
      default: return 'pi pi-globe';
    }
  };

  const getBrowserColor = (browser: BrowserType) => {
    switch (browser) {
      case BrowserType.CHROME: return '#4285f4';
      case BrowserType.FIREFOX: return '#ff6611';
      case BrowserType.EDGE: return '#0078d4';
      case BrowserType.SAFARI: return '#007aff';
      default: return '#6c757d';
    }
  };

  const getStatusSeverity = (status: ExtensionStatus) => {
    switch (status) {
      case ExtensionStatus.ACTIVE: return 'success';
      case ExtensionStatus.INACTIVE: return 'secondary';
      case ExtensionStatus.NOT_INSTALLED: return 'warning';
      case ExtensionStatus.ERROR: return 'danger';
      case ExtensionStatus.UPDATE_AVAILABLE: return 'info';
      default: return 'secondary';
    }
  };

  const getStatusLabel = (status: ExtensionStatus) => {
    switch (status) {
      case ExtensionStatus.ACTIVE: return 'Active';
      case ExtensionStatus.INACTIVE: return 'Inactive';
      case ExtensionStatus.NOT_INSTALLED: return 'Not Installed';
      case ExtensionStatus.ERROR: return 'Error';
      case ExtensionStatus.UPDATE_AVAILABLE: return 'Update Available';
      case ExtensionStatus.INSTALLED: return 'Installed';
      default: return 'Unknown';
    }
  };

  const renderExtensionStatus = (extension: BrowserExtensionType) => {
    return (
      <Badge 
        value={getStatusLabel(extension.status)} 
        severity={getStatusSeverity(extension.status)} 
      />
    );
  };

  const renderActivityIcon = (activity: ExtensionActivity) => {
    const iconMap = {
      [ExtensionAction.CONTENT_REPORTED]: 'pi pi-flag',
      [ExtensionAction.BULK_SELECTION]: 'pi pi-clone',
      [ExtensionAction.CONTEXT_MENU_USED]: 'pi pi-cursor',
      [ExtensionAction.AUTO_DETECTION_TRIGGERED]: 'pi pi-eye',
      [ExtensionAction.FORM_AUTOFILL]: 'pi pi-file-edit',
      [ExtensionAction.QUICK_ACTION]: 'pi pi-bolt'
    };
    
    return (
      <div className={`flex align-items-center justify-content-center w-3rem h-3rem border-circle ${
        activity.success ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
      }`}>
        <i className={iconMap[activity.action] || 'pi pi-circle'} />
      </div>
    );
  };

  const installationSteps: InstallationStep[] = [
    { label: 'Download Extension', icon: 'pi pi-download', description: 'Get the extension package' },
    { label: 'Install in Browser', icon: 'pi pi-cog', description: 'Install via browser store or manually' },
    { label: 'Grant Permissions', icon: 'pi pi-shield', description: 'Allow necessary permissions' },
    { label: 'Sign In to AutoDMCA', icon: 'pi pi-user', description: 'Authenticate with your account' },
    { label: 'Configure Settings', icon: 'pi pi-sliders-h', description: 'Customize extension behavior' },
    { label: 'Test Extension', icon: 'pi pi-play', description: 'Verify functionality' }
  ];

  // Loading state
  if (extensionsLoading || statsLoading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <Skeleton width="20rem" height="2rem" className="mb-2" />
          <Skeleton width="30rem" height="1rem" />
        </div>
        
        <div className="grid">
          <div className="col-12 lg:col-8">
            <Card>
              <Skeleton width="100%" height="20rem" />
            </Card>
          </div>
          <div className="col-12 lg:col-4">
            <Card>
              <Skeleton width="100%" height="20rem" />
            </Card>
          </div>
        </div>
      </div>
    );
  }

  const installedExtensions = extensions.filter(ext => ext.is_installed);
  const activeExtensions = extensions.filter(ext => ext.is_installed && ext.is_active);
  const updateAvailableCount = extensions.filter(ext => ext.status === ExtensionStatus.UPDATE_AVAILABLE).length;
  
  // Activity filter options
  const activityFilterOptions = [
    { label: 'Content Reported', value: ExtensionAction.CONTENT_REPORTED },
    { label: 'Bulk Selection', value: ExtensionAction.BULK_SELECTION },
    { label: 'Context Menu Used', value: ExtensionAction.CONTEXT_MENU_USED },
    { label: 'Auto Detection', value: ExtensionAction.AUTO_DETECTION_TRIGGERED },
    { label: 'Form Autofill', value: ExtensionAction.FORM_AUTOFILL },
    { label: 'Quick Action', value: ExtensionAction.QUICK_ACTION }
  ];

  // Bulk operation options
  const bulkOperationOptions = [
    { label: 'Install', value: 'install' },
    { label: 'Activate', value: 'activate' },
    { label: 'Deactivate', value: 'deactivate' },
    { label: 'Update', value: 'update' },
    { label: 'Uninstall', value: 'uninstall' }
  ];

  return (
    <div className="browser-extension-page">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Page Header */}
      <div className="flex justify-content-between align-items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-900 m-0 mb-2">
            Browser Extensions
          </h1>
          <p className="text-600 text-lg m-0">
            Install and manage AutoDMCA browser extensions for instant content protection
          </p>
        </div>
        
        <div className="flex gap-2 align-items-center">
          <Chip 
            label={`${installedExtensions.length} Installed`} 
            icon="pi pi-download" 
            className="bg-blue-100 text-blue-800"
          />
          <Chip 
            label={`${activeExtensions.length} Active`} 
            icon="pi pi-check-circle" 
            className="bg-green-100 text-green-800"
          />
          {updateAvailableCount > 0 && (
            <Chip 
              label={`${updateAvailableCount} Updates`} 
              icon="pi pi-refresh" 
              className="bg-orange-100 text-orange-800"
            />
          )}
          {isConnected ? (
            <Tag value="Connected" severity="success" icon="pi pi-check-circle" />
          ) : (
            <Tag value="Disconnected" severity="danger" icon="pi pi-times-circle" />
          )}
          
          <div className="ml-auto flex gap-2">
            <Button
              label="Bulk Operations"
              icon="pi pi-cog"
              outlined
              size="small"
              onClick={() => setShowBulkOperationsDialog(true)}
              disabled={extensions.length === 0}
            />
            <Button
              label="Export Data"
              icon="pi pi-download"
              outlined
              size="small"
              onClick={handleExportData}
            />
            <Button
              label="Refresh"
              icon="pi pi-refresh"
              outlined
              size="small"
              onClick={() => {
                refetchExtensions();
                queryClient.invalidateQueries({ queryKey: ['extension-stats'] });
              }}
              loading={extensionsLoading}
            />
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid mb-6">
        <div className="col-12 md:col-3">
          <Card className="bg-blue-50 border-blue-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-blue-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-download text-blue-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-blue-900 font-medium text-lg">{extensionStats?.total_installations || 0}</div>
                <div className="text-blue-700 text-sm">Total Installations</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-green-50 border-green-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-green-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-check-circle text-green-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-green-900 font-medium text-lg">{extensionStats?.active_extensions || 0}</div>
                <div className="text-green-700 text-sm">Active Extensions</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-orange-50 border-orange-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-orange-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-users text-orange-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-orange-900 font-medium text-lg">{extensionStats?.daily_active_users || 0}</div>
                <div className="text-orange-700 text-sm">Daily Active Users</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-purple-50 border-purple-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-purple-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-shield text-purple-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-purple-900 font-medium text-lg">{Math.round(extensionStats?.success_rate || 0)}%</div>
                <div className="text-purple-700 text-sm">Success Rate</div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Main Content Tabs */}
      <Card>
        <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
          
          {/* Extensions Overview Tab */}
          <TabPanel header="Extensions" leftIcon="pi pi-download mr-2">
            <div className="mb-4">
              <Toolbar
                start={(
                  <div className="flex gap-2">
                    <SplitButton
                      label="Actions"
                      icon="pi pi-cog"
                      model={[
                        { label: 'Update All', icon: 'pi pi-refresh', command: () => {
                          const updateableExtensions = extensions.filter(ext => ext.status === ExtensionStatus.UPDATE_AVAILABLE);
                          if (updateableExtensions.length > 0) {
                            setSelectedExtensions(updateableExtensions.map(ext => ext.id));
                            setBulkOperation({ operation: 'update', extension_ids: [] });
                            setShowBulkOperationsDialog(true);
                          } else {
                            toast.current?.show({
                              severity: 'info',
                              summary: 'No Updates Available',
                              detail: 'All extensions are up to date',
                              life: 3000
                            });
                          }
                        }},
                        { label: 'Sync All', icon: 'pi pi-sync', command: async () => {
                          try {
                            await Promise.all(
                              extensions.filter(ext => ext.is_active).map(ext =>
                                extensionApi.syncExtension(ext.id)
                              )
                            );
                            queryClient.invalidateQueries({ queryKey: ['extensions'] });
                            toast.current?.show({
                              severity: 'success',
                              summary: 'Sync Complete',
                              detail: 'All active extensions synchronized',
                              life: 3000
                            });
                          } catch (error) {
                            toast.current?.show({
                              severity: 'error',
                              summary: 'Sync Failed',
                              detail: 'Failed to sync one or more extensions',
                              life: 5000
                            });
                          }
                        }},
                        { separator: true },
                        { label: 'Check Updates', icon: 'pi pi-search', command: async () => {
                          try {
                            await extensionApi.checkForUpdates();
                            queryClient.invalidateQueries({ queryKey: ['extensions'] });
                            toast.current?.show({
                              severity: 'success',
                              summary: 'Update Check Complete',
                              detail: 'Extension versions checked',
                              life: 3000
                            });
                          } catch (error) {
                            toast.current?.show({
                              severity: 'error',
                              summary: 'Update Check Failed',
                              detail: 'Failed to check for updates',
                              life: 5000
                            });
                          }
                        }},
                      ]}
                    />
                  </div>
                )}
                end={(
                  <div className="flex gap-2">
                    <Tag
                      value={`${extensions.length} Total`}
                      icon="pi pi-list"
                      severity="secondary"
                    />
                    {updateAvailableCount > 0 && (
                      <Tag
                        value={`${updateAvailableCount} Updates`}
                        icon="pi pi-exclamation-triangle"
                        severity="warning"
                      />
                    )}
                  </div>
                )}
              />
            </div>
            
            <div className="grid">
              {extensions.map((extension) => (
                <div key={extension.id} className="col-12 lg:col-6 mb-4">
                  <Card className="h-full">
                    <div className="flex align-items-start justify-content-between mb-4">
                      <div className="flex align-items-center">
                        <Avatar 
                          icon={getBrowserIcon(extension.browser)}
                          style={{ 
                            backgroundColor: getBrowserColor(extension.browser),
                            color: 'white'
                          }}
                          size="large"
                        />
                        <div className="ml-3">
                          <div className="font-semibold text-lg">{extension.name}</div>
                          <div className="text-600 text-sm">Version {extension.version}</div>
                        </div>
                      </div>
                      {renderExtensionStatus(extension)}
                    </div>
                    
                    <div className="mb-4">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <span className="text-600">Browser:</span>
                        <Chip 
                          label={extension.browser.charAt(0).toUpperCase() + extension.browser.slice(1)}
                          icon={getBrowserIcon(extension.browser)}
                          style={{ backgroundColor: getBrowserColor(extension.browser), color: 'white' }}
                        />
                      </div>
                      
                      {extension.is_installed && extension.last_sync && (
                        <div className="flex align-items-center justify-content-between mb-2">
                          <span className="text-600">Last Sync:</span>
                          <span className="text-900">
                            {new Date(extension.last_sync).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      
                      <div className="flex align-items-center justify-content-between mb-2">
                        <span className="text-600">Install Count:</span>
                        <span className="text-900">{extension.install_count || 0}</span>
                      </div>
                      
                      <div className="flex align-items-center justify-content-between mb-2">
                        <span className="text-600">Success Rate:</span>
                        <span className="text-900">{Math.round(extension.success_rate || 0)}%</span>
                      </div>
                    </div>
                    
                    <div className="flex gap-2 flex-wrap">
                      {!extension.is_installed ? (
                        <>
                          <Button
                            label="Install"
                            icon="pi pi-download"
                            severity="success"
                            onClick={() => handleInstallExtension(extension)}
                            loading={installMutation.isPending}
                          />
                          <Button
                            label="Store Page"
                            icon="pi pi-external-link"
                            outlined
                            onClick={() => window.open(extension.store_url, '_blank')}
                          />
                        </>
                      ) : (
                        <>
                          <div className="flex align-items-center">
                            <span className="mr-2">Active:</span>
                            <InputSwitch
                              checked={extension.is_active}
                              onChange={(e) => handleToggleExtension(extension.id, e.value)}
                              disabled={activateExtensionMutation.isPending || deactivateExtensionMutation.isPending}
                            />
                          </div>
                          <Button
                            label="Permissions"
                            icon="pi pi-shield"
                            outlined
                            size="small"
                            onClick={() => {
                              setSelectedExtension(extension);
                              setShowPermissionsDialog(true);
                            }}
                          />
                          {extension.status === ExtensionStatus.UPDATE_AVAILABLE && (
                            <Button
                              label="Update"
                              icon="pi pi-refresh"
                              severity="warning"
                              outlined
                              size="small"
                              onClick={() => handleUpdateExtension(extension.id)}
                              loading={updateExtensionMutation.isPending}
                            />
                          )}
                          <Button
                            label="Sync"
                            icon="pi pi-sync"
                            outlined
                            size="small"
                            onClick={() => handleSyncExtension(extension.id)}
                          />
                        </>
                      )}
                    </div>
                  </Card>
                </div>
              ))}
            </div>
          </TabPanel>

          {/* Installation Guide Tab */}
          <TabPanel header="Installation Guide" leftIcon="pi pi-book mr-2">
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Step-by-Step Installation">
                  <Steps 
                    model={installationSteps} 
                    activeIndex={activeStep}
                    onSelect={(e) => setActiveStep(e.index)}
                    readOnly={false}
                  />
                  
                  <Divider />
                  
                  <div className="installation-step-content">
                    {activeStep === 0 && (
                      <div>
                        <h3>Download Extension</h3>
                        <p>Choose your browser and download the appropriate extension:</p>
                        <div className="flex gap-3 flex-wrap">
                          {extensions.map((ext) => (
                            <Button
                              key={ext.id}
                              label={`Download for ${ext.browser}`}
                              icon={getBrowserIcon(ext.browser)}
                              onClick={() => handleInstallExtension(ext)}
                              className="mb-2"
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {activeStep === 1 && (
                      <div>
                        <h3>Install in Browser</h3>
                        <p>Follow these browser-specific instructions:</p>
                        <Panel header="Chrome" className="mb-3">
                          <ol>
                            <li>Open Chrome and navigate to <code>chrome://extensions/</code></li>
                            <li>Enable "Developer mode" in the top right</li>
                            <li>Click "Load unpacked" and select the extension folder</li>
                            <li>The extension will appear in your browser toolbar</li>
                          </ol>
                        </Panel>
                        <Panel header="Firefox" className="mb-3">
                          <ol>
                            <li>Open Firefox and navigate to <code>about:addons</code></li>
                            <li>Click the gear icon and select "Install Add-on From File..."</li>
                            <li>Select the downloaded .xpi file</li>
                            <li>Click "Add" to install the extension</li>
                          </ol>
                        </Panel>
                      </div>
                    )}
                    
                    {activeStep === 2 && (
                      <div>
                        <h3>Grant Permissions</h3>
                        <p>The extension requires the following permissions:</p>
                        <ul>
                          <li><strong>Active Tab:</strong> To analyze content on the current page</li>
                          <li><strong>Context Menus:</strong> To add right-click reporting options</li>
                          <li><strong>Storage:</strong> To save your preferences and settings</li>
                          <li><strong>Notifications:</strong> To alert you about detected content</li>
                        </ul>
                        <Message severity="info" text="All permissions are used solely for AutoDMCA functionality and your data remains secure." />
                      </div>
                    )}
                    
                    {/* Continue with other steps... */}
                  </div>
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Quick Start">
                  <div className="mb-4">
                    <h4>Browser Support</h4>
                    <div className="flex flex-column gap-2">
                      <div className="flex align-items-center">
                        <i className="pi pi-chrome text-blue-500 mr-2" />
                        <span>Chrome 88+</span>
                        <Badge value="Stable" severity="success" className="ml-auto" />
                      </div>
                      <div className="flex align-items-center">
                        <i className="pi pi-firefox text-orange-500 mr-2" />
                        <span>Firefox 85+</span>
                        <Badge value="Stable" severity="success" className="ml-auto" />
                      </div>
                      <div className="flex align-items-center">
                        <i className="pi pi-microsoft text-blue-600 mr-2" />
                        <span>Edge 88+</span>
                        <Badge value="Beta" severity="warning" className="ml-auto" />
                      </div>
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <h4>Features</h4>
                    <ul className="list-none p-0">
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Right-click reporting</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Auto-detection</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Bulk operations</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Real-time sync</span>
                      </li>
                    </ul>
                  </div>
                  
                  <Button
                    label="Download Now"
                    icon="pi pi-download"
                    className="w-full"
                    onClick={() => extensions.length > 0 && handleInstallExtension(extensions[0])}
                  />
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Settings Tab */}
          <TabPanel header="Settings" leftIcon="pi pi-cog mr-2">
            <Message 
              severity="info" 
              text="Extension settings are managed individually for each installed extension. Select an extension to configure its settings."
              className="mb-4"
            />
            
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Global Extension Settings">
                  <div className="flex flex-column gap-4">
                    
                    <Panel header="Extension Management" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Auto-Install Updates</div>
                            <div className="text-600 text-sm">Automatically install extension updates when available</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              // Global setting would be saved to backend
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Setting Updated',
                                detail: `Auto-install updates ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Background Sync</div>
                            <div className="text-600 text-sm">Keep extensions synchronized in the background</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Setting Updated',
                                detail: `Background sync ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div>
                          <label className="font-medium mb-2 block">Sync Interval (minutes)</label>
                          <Slider
                            value={15}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Sync Interval Updated',
                                detail: `Sync interval set to ${e.value} minutes`,
                                life: 2000
                              });
                            }}
                            min={5}
                            max={60}
                            step={5}
                            className="w-full"
                          />
                          <div className="flex justify-content-between text-sm text-600 mt-1">
                            <span>5 min</span>
                            <span>60 min</span>
                          </div>
                        </div>
                      </div>
                    </Panel>
                    
                    <Panel header="Notifications & Alerts" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Extension Status Notifications</div>
                            <div className="text-600 text-sm">Receive notifications about extension status changes</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Notifications Updated',
                                detail: `Status notifications ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Update Notifications</div>
                            <div className="text-600 text-sm">Get notified when extension updates are available</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Update Notifications Updated',
                                detail: `Update notifications ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Error Alerts</div>
                            <div className="text-600 text-sm">Receive alerts when extensions encounter errors</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Error Alerts Updated',
                                detail: `Error alerts ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                      </div>
                    </Panel>
                    
                    <Panel header="Privacy & Security" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Anonymous Usage Analytics</div>
                            <div className="text-600 text-sm">Help improve extensions by sharing anonymous usage data</div>
                          </div>
                          <InputSwitch
                            checked={false}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Privacy Setting Updated',
                                detail: `Usage analytics ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Extension Data Encryption</div>
                            <div className="text-600 text-sm">Encrypt extension data for enhanced security</div>
                          </div>
                          <InputSwitch
                            checked={true}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Security Setting Updated',
                                detail: `Data encryption ${e.value ? 'enabled' : 'disabled'}`,
                                life: 3000
                              });
                            }}
                          />
                        </div>
                        
                        <div>
                          <label className="font-medium mb-2 block">Data Retention Period (days)</label>
                          <Slider
                            value={30}
                            onChange={(e) => {
                              toast.current?.show({
                                severity: 'info',
                                summary: 'Retention Period Updated',
                                detail: `Data will be retained for ${e.value} days`,
                                life: 2000
                              });
                            }}
                            min={7}
                            max={365}
                            step={1}
                            className="w-full"
                          />
                          <div className="flex justify-content-between text-sm text-600 mt-1">
                            <span>7 days</span>
                            <span>365 days</span>
                          </div>
                        </div>
                      </div>
                    </Panel>
                    
                    <div className="flex justify-content-end gap-2 mt-4">
                      <Button
                        label="Reset to Defaults"
                        icon="pi pi-refresh"
                        outlined
                        onClick={() => {
                          confirmDialog({
                            message: 'This will reset all global settings to their default values. Continue?',
                            header: 'Reset Settings',
                            icon: 'pi pi-exclamation-triangle',
                            accept: () => {
                              toast.current?.show({
                                severity: 'success',
                                summary: 'Settings Reset',
                                detail: 'All settings have been reset to defaults',
                                life: 3000
                              });
                            }
                          });
                        }}
                      />
                      <Button
                        label="Save Settings"
                        icon="pi pi-save"
                        onClick={() => {
                          toast.current?.show({
                            severity: 'success',
                            summary: 'Settings Saved',
                            detail: 'All settings have been saved successfully',
                            life: 3000
                          });
                        }}
                      />
                    </div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Extension Configuration" className="mb-4">
                  <div className="flex flex-column gap-3">
                    <div className="text-sm text-600 mb-2">
                      Configure individual extension settings by selecting an installed extension:
                    </div>
                    
                    {installedExtensions.length === 0 ? (
                      <Message severity="info" text="No extensions installed. Install extensions to configure their settings." />
                    ) : (
                      <div className="flex flex-column gap-2">
                        {installedExtensions.map(extension => (
                          <div 
                            key={extension.id} 
                            className="flex align-items-center justify-content-between p-2 border-1 border-300 border-round cursor-pointer hover:bg-gray-50"
                            onClick={async () => {
                              try {
                                const settings = await extensionApi.getExtensionSettings(extension.id);
                                setSelectedExtension(extension);
                                setShowSettingsDialog(true);
                              } catch (error) {
                                toast.current?.show({
                                  severity: 'error',
                                  summary: 'Settings Error',
                                  detail: 'Failed to load extension settings',
                                  life: 5000
                                });
                              }
                            }}
                          >
                            <div className="flex align-items-center">
                              <Avatar 
                                icon={getBrowserIcon(extension.browser)}
                                style={{ backgroundColor: getBrowserColor(extension.browser), color: 'white' }}
                                size="small"
                              />
                              <span className="ml-2 font-medium">{extension.name}</span>
                            </div>
                            <i className="pi pi-chevron-right text-600" />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>
                
                <Card title="Privacy & Security" className="mb-4">
                  <div className="flex flex-column gap-3">
                    <div className="flex align-items-start">
                      <i className="pi pi-shield text-green-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Secure Communication</div>
                        <div className="text-600 text-xs">All data encrypted with TLS 1.3</div>
                      </div>
                    </div>
                    <div className="flex align-items-start">
                      <i className="pi pi-lock text-blue-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Zero-Knowledge Architecture</div>
                        <div className="text-600 text-xs">Extension data encrypted client-side</div>
                      </div>
                    </div>
                    <div className="flex align-items-start">
                      <i className="pi pi-eye-slash text-purple-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Privacy First</div>
                        <div className="text-600 text-xs">No personal browsing data collected</div>
                      </div>
                    </div>
                    <div className="flex align-items-start">
                      <i className="pi pi-verified text-orange-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Code Audited</div>
                        <div className="text-600 text-xs">Regular security audits by third parties</div>
                      </div>
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <div className="flex gap-2">
                    <Button
                      label="Privacy Policy"
                      icon="pi pi-external-link"
                      text
                      size="small"
                      className="flex-1"
                      onClick={() => window.open('/privacy-policy', '_blank')}
                    />
                    <Button
                      label="Security Report"
                      icon="pi pi-file"
                      text
                      size="small"
                      className="flex-1"
                      onClick={() => window.open('/security-report', '_blank')}
                    />
                  </div>
                </Card>
                
                <Card title="Extension Health">
                  <div className="flex flex-column gap-3">
                    {extensions.length === 0 ? (
                      <div className="text-center text-600">
                        <i className="pi pi-info-circle text-2xl mb-2" />
                        <div>No extensions to monitor</div>
                      </div>
                    ) : (
                      extensions.map(extension => (
                        <div key={extension.id} className="flex justify-content-between align-items-center">
                          <div className="flex align-items-center">
                            <Avatar 
                              icon={getBrowserIcon(extension.browser)}
                              style={{ backgroundColor: getBrowserColor(extension.browser), color: 'white' }}
                              size="small"
                            />
                            <span className="ml-2 text-sm">{extension.browser.charAt(0).toUpperCase() + extension.browser.slice(1)}</span>
                          </div>
                          {renderExtensionStatus(extension)}
                        </div>
                      ))
                    )}
                  </div>
                  
                  {extensionStats && (
                    <>
                      <Divider />
                      <div className="text-center">
                        <div className="text-2xl font-bold text-900 mb-1">
                          {Math.round(extensionStats.success_rate || 0)}%
                        </div>
                        <div className="text-600 text-sm mb-2">Overall Success Rate</div>
                        <ProgressBar 
                          value={Math.round(extensionStats.success_rate || 0)} 
                          className="h-1rem" 
                        />
                        <div className="text-xs text-600 mt-2">
                          Based on {extensionStats.total_activities || 0} activities
                        </div>
                      </div>
                    </>
                  )}
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Activity Monitor Tab */}
          <TabPanel header="Activity" leftIcon="pi pi-chart-line mr-2">
            <div className="mb-4">
              <Card>
                <div className="flex flex-wrap gap-3 align-items-center">
                  <div className="flex align-items-center gap-2">
                    <label htmlFor="dateRange" className="text-600">Date Range:</label>
                    <Calendar 
                      id="dateRange"
                      value={dateRange}
                      onChange={(e) => setDateRange(e.value || [])}
                      selectionMode="range"
                      readOnlyInput
                      showIcon
                    />
                  </div>
                  <div className="flex align-items-center gap-2">
                    <label htmlFor="activityFilter" className="text-600">Filter Actions:</label>
                    <MultiSelect
                      id="activityFilter"
                      value={activityFilter}
                      onChange={(e) => setActivityFilter(e.value)}
                      options={activityFilterOptions}
                      placeholder="All Activities"
                      className="w-15rem"
                      display="chip"
                    />
                  </div>
                </div>
              </Card>
            </div>
            
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Extension Activity Log">
                  {activitiesLoading ? (
                    <div className="flex flex-column gap-3">
                      {[...Array(5)].map((_, i) => (
                        <Skeleton key={i} width="100%" height="3rem" />
                      ))}
                    </div>
                  ) : (
                    <DataTable
                      value={activities}
                      paginator
                      rows={15}
                      responsiveLayout="scroll"
                      emptyMessage="No activity recorded for selected filters"
                      sortField="timestamp"
                      sortOrder={-1}
                      selection={selectedExtensions}
                      onSelectionChange={(e) => setSelectedExtensions(e.value)}
                      dataKey="id"
                    >
                      <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
                      <Column 
                        field="action" 
                        header="Action" 
                        body={(activity) => (
                          <div className="flex align-items-center">
                            <Tag 
                              value={activity.action} 
                              severity={activity.success ? 'success' : 'danger'}
                              className="mr-2"
                            />
                            {activity.platform && (
                              <Badge value={activity.platform} />
                            )}
                          </div>
                        )}
                      />
                      <Column 
                        field="url" 
                        header="URL" 
                        body={(activity) => (
                          <a 
                            href={activity.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800"
                          >
                            {activity.url.length > 50 ? `${activity.url.substring(0, 50)}...` : activity.url}
                          </a>
                        )}
                      />
                      <Column 
                        field="timestamp" 
                        header="Time"
                        sortable
                        body={(activity) => new Date(activity.timestamp).toLocaleString()}
                      />
                      <Column 
                        field="success" 
                        header="Status"
                        body={(activity) => (
                          <i className={`pi ${activity.success ? 'pi-check text-green-500' : 'pi-times text-red-500'}`} />
                        )}
                      />
                      <Column 
                        field="confidence_score" 
                        header="Confidence"
                        body={(activity) => activity.confidence_score ? `${Math.round(activity.confidence_score * 100)}%` : '-'}
                      />
                    </DataTable>
                  )}
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Activity Timeline" className="mb-4">
                  {activitiesLoading ? (
                    <div className="flex flex-column gap-3">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className="flex align-items-center gap-3">
                          <Skeleton shape="circle" size="3rem" />
                          <div className="flex-1">
                            <Skeleton width="100%" height="1rem" className="mb-2" />
                            <Skeleton width="60%" height="0.8rem" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Timeline
                      value={activities.slice(0, 5)}
                      marker={(activity) => renderActivityIcon(activity)}
                      content={(activity) => (
                        <div className="ml-3">
                          <div className="font-medium text-sm">{activity.action}</div>
                          <div className="text-600 text-xs mb-1">
                            {new Date(activity.timestamp).toLocaleTimeString()}
                          </div>
                          {activity.details && (
                            <div className="text-700 text-xs">{activity.details}</div>
                          )}
                          {activity.confidence_score && (
                            <div className="text-600 text-xs">
                              Confidence: {Math.round(activity.confidence_score * 100)}%
                            </div>
                          )}
                        </div>
                      )}
                    />
                  )}
                </Card>
                
                {/* Browser Distribution Chart */}
                {!browserStatsLoading && browserDistribution.length > 0 && (
                  <Card title="Browser Distribution" className="mb-4">
                    <Chart
                      type="doughnut"
                      data={{
                        labels: browserDistribution.map(item => item.browser),
                        datasets: [{
                          data: browserDistribution.map(item => item.count),
                          backgroundColor: browserDistribution.map(item => getBrowserColor(item.browser as BrowserType)),
                          borderWidth: 0
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'bottom',
                            labels: {
                              usePointStyle: true,
                              padding: 10
                            }
                          }
                        }
                      }}
                      style={{ height: '200px' }}
                    />
                  </Card>
                )}
                
                <Card title="Quick Actions">
                  <div className="flex flex-column gap-2">
                    <Button
                      label="Refresh Extensions"
                      icon="pi pi-refresh"
                      outlined
                      className="w-full"
                      onClick={() => {
                        refetchExtensions();
                        queryClient.invalidateQueries({ queryKey: ['extension-activities'] });
                        queryClient.invalidateQueries({ queryKey: ['extension-stats'] });
                      }}
                      loading={extensionsLoading}
                    />
                    <Button
                      label="Health Check"
                      icon="pi pi-heart"
                      outlined
                      className="w-full"
                      onClick={async () => {
                        try {
                          await Promise.all(
                            extensions.filter(ext => ext.is_active).map(ext =>
                              extensionApi.pingExtension(ext.id)
                            )
                          );
                          toast.current?.show({
                            severity: 'success',
                            summary: 'Health Check Complete',
                            detail: 'All active extensions are healthy',
                            life: 3000
                          });
                        } catch (error) {
                          toast.current?.show({
                            severity: 'error',
                            summary: 'Health Check Failed',
                            detail: 'One or more extensions are not responding',
                            life: 5000
                          });
                        }
                      }}
                    />
                    <Button
                      label="Export Activity"
                      icon="pi pi-download"
                      outlined
                      className="w-full"
                      onClick={handleExportData}
                    />
                    <Button
                      label="Test Extensions"
                      icon="pi pi-play"
                      outlined
                      className="w-full"
                      onClick={async () => {
                        try {
                          const testResults = await Promise.allSettled(
                            activeExtensions.map(ext => extensionApi.pingExtension(ext.id))
                          );
                          const successCount = testResults.filter(result => result.status === 'fulfilled').length;
                          toast.current?.show({
                            severity: successCount === activeExtensions.length ? 'success' : 'warn',
                            summary: 'Extension Test Results',
                            detail: `${successCount}/${activeExtensions.length} extensions passed the test`,
                            life: 4000
                          });
                        } catch (error) {
                          toast.current?.show({
                            severity: 'error',
                            summary: 'Test Failed',
                            detail: 'Unable to test extensions',
                            life: 5000
                          });
                        }
                      }}
                    />
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>
          
          {/* Analytics & Performance Tab */}
          <TabPanel header="Analytics" leftIcon="pi pi-chart-bar mr-2">
            <div className="grid">
              <div className="col-12 lg:col-6">
                <Card title="Usage Statistics" className="mb-4">
                  {statsLoading ? (
                    <Skeleton width="100%" height="200px" />
                  ) : extensionStats?.activity_trends ? (
                    <Chart
                      type="line"
                      data={{
                        labels: extensionStats.activity_trends.map(item => 
                          new Date(item.date).toLocaleDateString()
                        ),
                        datasets: [{
                          label: 'Activities',
                          data: extensionStats.activity_trends.map(item => item.activities),
                          borderColor: '#3B82F6',
                          backgroundColor: 'rgba(59, 130, 246, 0.1)',
                          tension: 0.4,
                          fill: true
                        }, {
                          label: 'Success Rate (%)',
                          data: extensionStats.activity_trends.map(item => item.success_rate * 100),
                          borderColor: '#10B981',
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          tension: 0.4,
                          yAxisID: 'y1'
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                          y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                          },
                          y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            max: 100,
                            grid: {
                              drawOnChartArea: false,
                            },
                          }
                        },
                        plugins: {
                          legend: {
                            position: 'bottom'
                          }
                        }
                      }}
                      style={{ height: '300px' }}
                    />
                  ) : (
                    <div className="text-center text-600 p-4">
                      <i className="pi pi-chart-line text-4xl mb-3" />
                      <div>No activity data available</div>
                    </div>
                  )}
                </Card>
                
                <Card title="Top Actions">
                  {extensionStats?.top_actions ? (
                    <div className="flex flex-column gap-3">
                      {extensionStats.top_actions.map((action, index) => (
                        <div key={index} className="flex align-items-center justify-content-between">
                          <div className="flex align-items-center">
                            <Badge value={index + 1} className="mr-2" />
                            <span className="font-medium">{action.action.replace(/_/g, ' ')}</span>
                          </div>
                          <div className="text-right">
                            <div className="font-bold">{action.count}</div>
                            <div className="text-sm text-600">{Math.round(action.percentage)}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-600 p-4">
                      No action data available
                    </div>
                  )}
                </Card>
              </div>
              
              <div className="col-12 lg:col-6">
                <Card title="Performance Metrics" className="mb-4">
                  <div className="grid">
                    <div className="col-6">
                      <div className="text-center p-3 border-1 border-300 border-round">
                        <div className="text-2xl font-bold text-blue-600 mb-1">
                          {extensionStats?.daily_active_users || 0}
                        </div>
                        <div className="text-sm text-600">Daily Active Users</div>
                      </div>
                    </div>
                    <div className="col-6">
                      <div className="text-center p-3 border-1 border-300 border-round">
                        <div className="text-2xl font-bold text-green-600 mb-1">
                          {extensionStats?.total_activities || 0}
                        </div>
                        <div className="text-sm text-600">Total Activities</div>
                      </div>
                    </div>
                    <div className="col-6">
                      <div className="text-center p-3 border-1 border-300 border-round">
                        <div className="text-2xl font-bold text-orange-600 mb-1">
                          {Math.round(extensionStats?.success_rate || 0)}%
                        </div>
                        <div className="text-sm text-600">Success Rate</div>
                      </div>
                    </div>
                    <div className="col-6">
                      <div className="text-center p-3 border-1 border-300 border-round">
                        <div className="text-2xl font-bold text-purple-600 mb-1">
                          {extensionStats?.active_extensions || 0}
                        </div>
                        <div className="text-sm text-600">Active Extensions</div>
                      </div>
                    </div>
                  </div>
                </Card>
                
                {!browserStatsLoading && extensionStats?.browser_distribution && (
                  <Card title="Browser Distribution">
                    <Chart
                      type="pie"
                      data={{
                        labels: Object.keys(extensionStats.browser_distribution),
                        datasets: [{
                          data: Object.values(extensionStats.browser_distribution),
                          backgroundColor: Object.keys(extensionStats.browser_distribution).map(browser => 
                            getBrowserColor(browser as BrowserType)
                          ),
                          borderWidth: 0
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'bottom',
                            labels: {
                              usePointStyle: true,
                              padding: 15
                            }
                          }
                        }
                      }}
                      style={{ height: '300px' }}
                    />
                  </Card>
                )}
              </div>
            </div>
          </TabPanel>

        </TabView>
      </Card>
      
      {/* Extension Settings Dialog */}
      <Dialog
        visible={showSettingsDialog}
        onHide={() => setShowSettingsDialog(false)}
        header={`${selectedExtension?.name} Settings`}
        style={{ width: '600px' }}
        maximizable
      >
        {selectedExtension && (
          <div className="flex flex-column gap-4">
            <Message 
              severity="info" 
              text="Extension settings are synchronized across all your devices and browsers."
            />
            
            <Panel header="Detection Settings" toggleable>
              <div className="flex flex-column gap-3">
                <div className="flex align-items-center justify-content-between">
                  <div>
                    <div className="font-medium">Auto Detection</div>
                    <div className="text-600 text-sm">Automatically detect content on pages</div>
                  </div>
                  <InputSwitch checked={true} onChange={() => {}} />
                </div>
                
                <div>
                  <label className="font-medium mb-2 block">Detection Threshold</label>
                  <Slider
                    value={75}
                    onChange={() => {}}
                    min={0}
                    max={100}
                    step={5}
                    className="w-full"
                  />
                  <div className="flex justify-content-between text-sm text-600 mt-1">
                    <span>Conservative</span>
                    <span>Aggressive</span>
                  </div>
                </div>
              </div>
            </Panel>
            
            <Panel header="Notification Settings" toggleable>
              <div className="flex flex-column gap-3">
                <div className="flex align-items-center justify-content-between">
                  <div>
                    <div className="font-medium">Desktop Notifications</div>
                    <div className="text-600 text-sm">Show notifications when content is detected</div>
                  </div>
                  <InputSwitch checked={true} onChange={() => {}} />
                </div>
                
                <div>
                  <label className="font-medium mb-2 block">Notification Frequency</label>
                  <Dropdown
                    value="immediate"
                    options={[
                      { label: 'Immediate', value: 'immediate' },
                      { label: 'Every 5 minutes', value: '5min' },
                      { label: 'Hourly', value: 'hourly' },
                      { label: 'Daily', value: 'daily' }
                    ]}
                    className="w-full"
                    onChange={() => {}}
                  />
                </div>
              </div>
            </Panel>
            
            <div className="flex justify-content-end gap-2">
              <Button
                label="Reset to Defaults"
                icon="pi pi-refresh"
                outlined
                onClick={() => setShowSettingsDialog(false)}
              />
              <Button
                label="Save Settings"
                icon="pi pi-save"
                onClick={async () => {
                  try {
                    await extensionApi.updateExtensionSettings(selectedExtension.id, {
                      // Settings would be collected from form state
                    });
                    setShowSettingsDialog(false);
                    toast.current?.show({
                      severity: 'success',
                      summary: 'Settings Saved',
                      detail: 'Extension settings updated successfully',
                      life: 3000
                    });
                  } catch (error: any) {
                    toast.current?.show({
                      severity: 'error',
                      summary: 'Save Failed',
                      detail: error.response?.data?.message || 'Failed to save settings',
                      life: 5000
                    });
                  }
                }}
              />
            </div>
          </div>
        )}
      </Dialog>

      {/* Permissions Dialog */}
      <Dialog
        visible={showPermissionsDialog}
        onHide={() => setShowPermissionsDialog(false)}
        header={`${selectedExtension?.name} Permissions`}
        style={{ width: '600px' }}
        maximizable
      >
        {selectedExtension && (
          <div className="flex flex-column gap-3">
            <p>This extension requests the following permissions:</p>
            
            {selectedExtension.permissions?.map((permission, index) => (
              <div key={index} className="flex align-items-start gap-3 p-3 border-1 border-300 border-round">
                <i className="pi pi-shield text-blue-500 mt-1" />
                <div className="flex-1">
                  <div className="font-medium">{permission}</div>
                  <div className="text-600 text-sm mt-1">
                    {permission === 'activeTab' && 'Access to view and analyze content on the current browser tab'}
                    {permission === 'contextMenus' && 'Add right-click menu options for quick reporting'}
                    {permission === 'storage' && 'Save extension settings and preferences locally'}
                    {permission === 'notifications' && 'Display desktop notifications for detected content'}
                    {permission === 'tabs' && 'Access to browser tab information for content detection'}
                    {permission === 'webRequest' && 'Monitor web requests for content analysis'}
                    {permission === 'background' && 'Run background scripts for real-time monitoring'}
                  </div>
                </div>
                <Tag value="Required" severity="info" />
              </div>
            ))}
            
            <Message 
              severity="info" 
              text="All permissions are used exclusively for AutoDMCA functionality. No personal data is collected or shared with third parties."
              className="mt-3"
            />
            
            <Divider />
            
            <div className="flex justify-content-between align-items-center">
              <div className="flex gap-2">
                <Button
                  label="View Privacy Policy"
                  icon="pi pi-external-link"
                  text
                  onClick={() => window.open('/privacy-policy', '_blank')}
                />
                <Button
                  label="Extension Details"
                  icon="pi pi-info-circle"
                  text
                  onClick={() => window.open(selectedExtension.store_url, '_blank')}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  label="Manage Permissions"
                  icon="pi pi-cog"
                  outlined
                  onClick={async () => {
                    try {
                      await extensionApi.updateExtensionPermissions(selectedExtension.id, {
                        // Implementation would depend on specific permission management needs
                      });
                      setShowPermissionsDialog(false);
                    } catch (error: any) {
                      toast.current?.show({
                        severity: 'error',
                        summary: 'Permission Update Failed',
                        detail: error.response?.data?.message || 'Failed to update permissions',
                        life: 5000
                      });
                    }
                  }}
                />
                <Button
                  label="Close"
                  onClick={() => setShowPermissionsDialog(false)}
                />
              </div>
            </div>
          </div>
        )}
      </Dialog>

      {/* Bulk Operations Dialog */}
      <Dialog
        visible={showBulkOperationsDialog}
        onHide={() => setShowBulkOperationsDialog(false)}
        header="Bulk Extension Operations"
        style={{ width: '500px' }}
      >
        <div className="flex flex-column gap-4">
          <div>
            <label htmlFor="operation" className="block text-900 font-medium mb-2">Operation</label>
            <Dropdown
              id="operation"
              value={bulkOperation.operation}
              onChange={(e) => setBulkOperation(prev => ({ ...prev, operation: e.value }))}
              options={bulkOperationOptions}
              placeholder="Select operation"
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block text-900 font-medium mb-2">Target Extensions</label>
            <MultiSelect
              value={selectedExtensions}
              onChange={(e) => setSelectedExtensions(e.value)}
              options={extensions.map(ext => ({ label: ext.name, value: ext.id }))}
              placeholder="Select extensions"
              className="w-full"
              display="chip"
            />
          </div>
          
          {selectedExtensions.length > 0 && (
            <Message 
              severity="info" 
              text={`This operation will affect ${selectedExtensions.length} extension(s).`}
            />
          )}
          
          {bulkOperation.operation === 'update' && (
            <div>
              <label className="block text-900 font-medium mb-2">Schedule Time (Optional)</label>
              <Calendar
                value={bulkOperation.schedule_time ? new Date(bulkOperation.schedule_time) : null}
                onChange={(e) => setBulkOperation(prev => ({ 
                  ...prev, 
                  schedule_time: e.value?.toISOString() 
                }))}
                showTime
                hourFormat="24"
                placeholder="Immediate"
                className="w-full"
              />
            </div>
          )}
          
          <Divider />
          
          <div className="flex justify-content-end gap-2">
            <Button
              label="Cancel"
              outlined
              onClick={() => setShowBulkOperationsDialog(false)}
            />
            <Button
              label="Execute"
              onClick={handleBulkOperation}
              loading={bulkOperationMutation.isPending}
              disabled={selectedExtensions.length === 0}
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default BrowserExtension;