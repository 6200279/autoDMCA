import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Toolbar } from 'primereact/toolbar';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { InputSwitch } from 'primereact/inputswitch';
import { InputText } from 'primereact/inputtext';
// import { Dropdown } from 'primereact/dropdown';
// import { MultiSelect } from 'primereact/multiselect';
import { Chart } from 'primereact/chart';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
import { Toast } from 'primereact/toast';
import { ProgressBar } from 'primereact/progressbar';
import { Skeleton } from 'primereact/skeleton';
// import { Calendar } from 'primereact/calendar';
import { InputTextarea } from 'primereact/inputtextarea';
import { Divider } from 'primereact/divider';
// import { Panel } from 'primereact/panel';
import { Accordion, AccordionTab } from 'primereact/accordion';
import { Timeline } from 'primereact/timeline';
import { format, parseISO } from 'date-fns';

import { adminApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  AdminDashboardStats,
  AdminUser,
  SystemConfig,
  PlatformConfig,
  AdminActivity,
  AdminNotification,
  SystemHealthCheck,
  UserRole,
  // SubscriptionPlan,
  SubscriptionStatus,
  BulkUserOperation,
  SystemMetric,
  AuditLog
} from '../types/api';

const AdminPanel: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);

  // Main state
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [dashboardStats, setDashboardStats] = useState<AdminDashboardStats | null>(null);

  // User Management
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<AdminUser[]>([]);
  const [userFilters, setUserFilters] = useState({});
  const [userDialog, setUserDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [bulkActionDialog, setBulkActionDialog] = useState(false);

  // System Configuration
  const [systemConfigs, setSystemConfigs] = useState<SystemConfig[]>([]);
  const [platformConfigs, setPlatformConfigs] = useState<PlatformConfig[]>([]);
  const [configDialog, setConfigDialog] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<SystemConfig | null>(null);

  // System Health & Monitoring
  const [systemHealth, setSystemHealth] = useState<SystemHealthCheck[]>([]);
  const [adminActivities, setAdminActivities] = useState<AdminActivity[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);

  // Maintenance & Feature Flags
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({});

  // Analytics
  const [chartData, setChartData] = useState<any>({});
  const [chartOptions] = useState({
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  });

  useEffect(() => {
    if (user?.is_superuser) {
      loadAdminData();
    }
  }, [user]);

  const loadAdminData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        loadDashboardStats(),
        loadUsers(),
        loadSystemConfigs(),
        loadSystemHealth(),
        loadNotifications(),
      ]);
    } catch (error) {
      showError('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardStats = async () => {
    try {
      const response = await adminApi.getDashboardStats();
      setDashboardStats(response.data);
      
      // Prepare chart data
      const userGrowthData = {
        labels: response.data.platform_statistics ? Object.keys(response.data.platform_statistics) : [],
        datasets: [
          {
            label: 'Success Rate',
            data: response.data.platform_statistics ? Object.values(response.data.platform_statistics).map((p: any) => p.success_rate) : [],
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1,
          },
        ],
      };
      setChartData({ userGrowth: userGrowthData });
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await adminApi.getUsers();
      setUsers(response.data.items || response.data);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadSystemConfigs = async () => {
    try {
      const [configResponse, platformResponse] = await Promise.all([
        adminApi.getSystemConfigs(),
        adminApi.getPlatformConfigs(),
      ]);
      setSystemConfigs(configResponse.data);
      setPlatformConfigs(platformResponse.data);
    } catch (error) {
      console.error('Failed to load system configs:', error);
    }
  };

  const loadSystemHealth = async () => {
    try {
      const response = await adminApi.getSystemHealth();
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Failed to load system health:', error);
    }
  };

  const loadNotifications = async () => {
    try {
      const response = await adminApi.getAdminNotifications();
      setNotifications(response.data.items || response.data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const loadAdminActivities = async () => {
    try {
      const response = await adminApi.getAdminActivities();
      setAdminActivities(response.data.items || response.data);
    } catch (error) {
      console.error('Failed to load admin activities:', error);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const response = await adminApi.getAuditLogs();
      setAuditLogs(response.data.items || response.data);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    }
  };

  const showSuccess = (message: string) => {
    toast.current?.show({ severity: 'success', summary: 'Success', detail: message });
  };

  const showError = (message: string) => {
    toast.current?.show({ severity: 'error', summary: 'Error', detail: message });
  };

  const showWarning = (message: string) => {
    toast.current?.show({ severity: 'warn', summary: 'Warning', detail: message });
  };

  // User Management Functions
  const openUserDialog = (user: AdminUser) => {
    setSelectedUser({ ...user });
    setUserDialog(true);
  };

  const suspendUser = (user: AdminUser) => {
    confirmDialog({
      message: `Are you sure you want to suspend user ${user.full_name}?`,
      header: 'Confirm Suspension',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          await adminApi.suspendUser(user.id, { reason: 'Administrative action' });
          await loadUsers();
          showSuccess('User suspended successfully');
        } catch (error) {
          showError('Failed to suspend user');
        }
      },
    });
  };

  const activateUser = async (user: AdminUser) => {
    try {
      await adminApi.activateUser(user.id);
      await loadUsers();
      showSuccess('User activated successfully');
    } catch (error) {
      showError('Failed to activate user');
    }
  };

  const deleteUser = (user: AdminUser) => {
    confirmDialog({
      message: `Are you sure you want to permanently delete user ${user.full_name}? This action cannot be undone.`,
      header: 'Confirm Deletion',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          await adminApi.deleteUser(user.id);
          await loadUsers();
          showSuccess('User deleted successfully');
        } catch (error) {
          showError('Failed to delete user');
        }
      },
    });
  };

  const executeBulkAction = async (operation: BulkUserOperation) => {
    try {
      await adminApi.bulkUserOperation(operation);
      await loadUsers();
      setSelectedUsers([]);
      setBulkActionDialog(false);
      showSuccess(`Bulk ${operation.operation} completed successfully`);
    } catch (error) {
      showError(`Failed to execute bulk ${operation.operation}`);
    }
  };

  // System Configuration Functions
  const updateSystemConfig = async (config: SystemConfig) => {
    try {
      await adminApi.updateSystemConfig(config.key, { value: config.value });
      await loadSystemConfigs();
      setConfigDialog(false);
      showSuccess('Configuration updated successfully');
    } catch (error) {
      showError('Failed to update configuration');
    }
  };

  const testPlatformConnection = async (platform: PlatformConfig) => {
    try {
      await adminApi.testPlatformConnection(platform.id);
      showSuccess(`Connection to ${platform.platform_name} tested successfully`);
    } catch (error) {
      showError(`Failed to test connection to ${platform.platform_name}`);
    }
  };

  const toggleMaintenanceMode = async () => {
    try {
      if (maintenanceMode) {
        await adminApi.disableMaintenanceMode();
        showSuccess('Maintenance mode disabled');
      } else {
        await adminApi.enableMaintenanceMode({ reason: 'Scheduled maintenance' });
        showSuccess('Maintenance mode enabled');
      }
      setMaintenanceMode(!maintenanceMode);
    } catch (error) {
      showError('Failed to toggle maintenance mode');
    }
  };

  // Render Functions
  const renderUserStatus = (rowData: AdminUser) => {
    if (rowData.is_suspended) {
      return <Tag value="Suspended" severity="danger" />;
    }
    return rowData.is_active ? 
      <Tag value="Active" severity="success" /> : 
      <Tag value="Inactive" severity="warning" />;
  };

  const renderUserRole = (rowData: AdminUser) => {
    const severity = rowData.role === UserRole.SUPER_ADMIN ? 'danger' : 
                    rowData.role === UserRole.ADMIN ? 'warning' : 'info';
    return <Tag value={rowData.role} severity={severity} />;
  };

  const renderSubscription = (rowData: AdminUser) => {
    if (!rowData.subscription) return <Tag value="No Subscription" severity="secondary" />;
    
    const severity = rowData.subscription.status === SubscriptionStatus.ACTIVE ? 'success' : 'warning';
    return (
      <div>
        <Tag value={rowData.subscription.plan} severity={severity} />
        <div className="text-sm text-gray-500">{rowData.subscription.status}</div>
      </div>
    );
  };

  const renderUserActions = (rowData: AdminUser) => {
    return (
      <div className="flex gap-2">
        <Button
          icon="pi pi-eye"
          rounded
          text
          severity="info"
          onClick={() => openUserDialog(rowData)}
          tooltip="View Details"
        />
        {rowData.is_suspended ? (
          <Button
            icon="pi pi-check"
            rounded
            text
            severity="success"
            onClick={() => activateUser(rowData)}
            tooltip="Activate User"
          />
        ) : (
          <Button
            icon="pi pi-ban"
            rounded
            text
            severity="warning"
            onClick={() => suspendUser(rowData)}
            tooltip="Suspend User"
          />
        )}
        <Button
          icon="pi pi-trash"
          rounded
          text
          severity="danger"
          onClick={() => deleteUser(rowData)}
          tooltip="Delete User"
        />
      </div>
    );
  };

  const renderHealthStatus = (health: SystemHealthCheck) => {
    const severity = health.status === 'healthy' ? 'success' : 
                    health.status === 'degraded' ? 'warning' : 'danger';
    return <Tag value={health.status} severity={severity} />;
  };

  const renderMetricStatus = (metric: SystemMetric) => {
    const severity = metric.status === 'healthy' ? 'success' : 
                    metric.status === 'warning' ? 'warning' : 'danger';
    return (
      <div className="flex align-items-center gap-2">
        <Tag value={metric.status} severity={severity} />
        <span className="text-sm text-gray-500">
          {metric.value} {metric.unit}
        </span>
      </div>
    );
  };

  const renderNotificationIcon = (notification: AdminNotification) => {
    const iconMap = {
      info: 'pi pi-info-circle',
      warning: 'pi pi-exclamation-triangle',
      error: 'pi pi-times-circle',
      success: 'pi pi-check-circle',
    };
    return <i className={`${iconMap[notification.type]} text-lg`} />;
  };

  if (!user?.is_superuser) {
    return (
      <div className="flex justify-content-center align-items-center h-screen">
        <Message severity="error" text="Access Denied: Admin privileges required" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4">
        <Skeleton width="100%" height="4rem" className="mb-3" />
        <div className="grid">
          <div className="col-12 md:col-3">
            <Skeleton width="100%" height="8rem" />
          </div>
          <div className="col-12 md:col-3">
            <Skeleton width="100%" height="8rem" />
          </div>
          <div className="col-12 md:col-3">
            <Skeleton width="100%" height="8rem" />
          </div>
          <div className="col-12 md:col-3">
            <Skeleton width="100%" height="8rem" />
          </div>
        </div>
        <Skeleton width="100%" height="20rem" className="mt-4" />
      </div>
    );
  }

  return (
    <div className="p-4">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <div className="flex justify-content-between align-items-center mb-4">
        <h1 className="text-3xl font-bold text-900">Admin Panel</h1>
        <div className="flex gap-2 align-items-center">
          <span className="text-sm text-600">Maintenance Mode</span>
          <InputSwitch
            checked={maintenanceMode}
            onChange={toggleMaintenanceMode}
          />
          <Badge value={notifications.length} severity="danger" />
        </div>
      </div>

      <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
        {/* Dashboard Tab */}
        <TabPanel header="Dashboard" leftIcon="pi pi-chart-line">
          <div className="grid">
            {/* Key Metrics Cards */}
            <div className="col-12 md:col-3">
              <Card className="bg-blue-50">
                <div className="flex justify-content-between align-items-center">
                  <div>
                    <div className="text-blue-600 font-medium">Total Users</div>
                    <div className="text-2xl font-bold text-blue-900">
                      {dashboardStats?.total_users?.toLocaleString() || '0'}
                    </div>
                  </div>
                  <i className="pi pi-users text-3xl text-blue-500" />
                </div>
              </Card>
            </div>
            
            <div className="col-12 md:col-3">
              <Card className="bg-green-50">
                <div className="flex justify-content-between align-items-center">
                  <div>
                    <div className="text-green-600 font-medium">Monthly Revenue</div>
                    <div className="text-2xl font-bold text-green-900">
                      ${dashboardStats?.monthly_revenue?.toLocaleString() || '0'}
                    </div>
                  </div>
                  <i className="pi pi-dollar text-3xl text-green-500" />
                </div>
              </Card>
            </div>
            
            <div className="col-12 md:col-3">
              <Card className="bg-orange-50">
                <div className="flex justify-content-between align-items-center">
                  <div>
                    <div className="text-orange-600 font-medium">Active Subscriptions</div>
                    <div className="text-2xl font-bold text-orange-900">
                      {dashboardStats?.active_subscriptions?.toLocaleString() || '0'}
                    </div>
                  </div>
                  <i className="pi pi-credit-card text-3xl text-orange-500" />
                </div>
              </Card>
            </div>
            
            <div className="col-12 md:col-3">
              <Card className="bg-purple-50">
                <div className="flex justify-content-between align-items-center">
                  <div>
                    <div className="text-purple-600 font-medium">Success Rate</div>
                    <div className="text-2xl font-bold text-purple-900">
                      {dashboardStats?.success_rate?.toFixed(1) || '0'}%
                    </div>
                  </div>
                  <i className="pi pi-check-circle text-3xl text-purple-500" />
                </div>
              </Card>
            </div>

            {/* System Health */}
            <div className="col-12 md:col-8">
              <Card title="Platform Performance" className="h-full">
                {chartData.userGrowth && (
                  <Chart type="bar" data={chartData.userGrowth} options={chartOptions} />
                )}
              </Card>
            </div>

            <div className="col-12 md:col-4">
              <Card title="System Health" className="h-full">
                <div className="flex flex-column gap-3">
                  {systemHealth.slice(0, 5).map((health, index) => (
                    <div key={index} className="flex justify-content-between align-items-center">
                      <span className="font-medium">{health.service}</span>
                      {renderHealthStatus(health)}
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Recent Activities */}
            <div className="col-12">
              <Card title="Recent Admin Activities">
                <Timeline
                  value={adminActivities.slice(0, 10)}
                  align="alternate"
                  content={(item: AdminActivity) => (
                    <div className="p-2">
                      <div className="font-medium">{item.admin_name}</div>
                      <div className="text-sm text-600">{item.description}</div>
                      <div className="text-xs text-400">
                        {format(parseISO(item.created_at), 'MMM dd, yyyy HH:mm')}
                      </div>
                    </div>
                  )}
                />
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* User Management Tab */}
        <TabPanel header="User Management" leftIcon="pi pi-users">
          <div className="mb-4">
            <Toolbar
              start={
                <div className="flex gap-2">
                  <Button
                    label="Bulk Actions"
                    icon="pi pi-cog"
                    severity="secondary"
                    disabled={selectedUsers.length === 0}
                    onClick={() => setBulkActionDialog(true)}
                  />
                  <Button
                    label="Export Users"
                    icon="pi pi-download"
                    severity="secondary"
                    onClick={() => adminApi.exportUsers()}
                  />
                </div>
              }
              end={
                <div className="flex gap-2">
                  <InputText
                    placeholder="Search users..."
                    onInput={(e) => setUserFilters({ ...userFilters, global: { value: (e.target as HTMLInputElement).value, matchMode: 'contains' } })}
                  />
                  <Button
                    icon="pi pi-refresh"
                    onClick={loadUsers}
                    tooltip="Refresh"
                  />
                </div>
              }
            />
          </div>

          <DataTable
            value={users}
            selection={selectedUsers}
            onSelectionChange={(e) => setSelectedUsers(e.value)}
            dataKey="id"
            paginator
            rows={25}
            filters={userFilters}
            globalFilterFields={['full_name', 'email', 'company']}
            responsiveLayout="scroll"
            className="p-datatable-striped"
          >
            <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
            <Column field="full_name" header="Name" sortable />
            <Column field="email" header="Email" sortable />
            <Column field="company" header="Company" sortable />
            <Column
              field="role"
              header="Role"
              body={renderUserRole}
              sortable
            />
            <Column
              field="subscription"
              header="Subscription"
              body={renderSubscription}
            />
            <Column
              field="is_active"
              header="Status"
              body={renderUserStatus}
              sortable
            />
            <Column
              field="created_at"
              header="Created"
              body={(rowData) => format(parseISO(rowData.created_at), 'MMM dd, yyyy')}
              sortable
            />
            <Column
              field="last_login"
              header="Last Login"
              body={(rowData) => rowData.last_login ? format(parseISO(rowData.last_login), 'MMM dd, yyyy') : 'Never'}
              sortable
            />
            <Column
              header="Actions"
              body={renderUserActions}
              headerStyle={{ width: '10rem' }}
            />
          </DataTable>
        </TabPanel>

        {/* System Configuration Tab */}
        <TabPanel header="System Config" leftIcon="pi pi-cog">
          <div className="grid">
            <div className="col-12 md:col-6">
              <Card title="System Settings">
                <div className="flex flex-column gap-4">
                  {systemConfigs.filter(c => c.category === 'system').map((config) => (
                    <div key={config.id} className="flex justify-content-between align-items-center">
                      <div>
                        <div className="font-medium">{config.key}</div>
                        <div className="text-sm text-600">{config.description}</div>
                      </div>
                      <div className="flex align-items-center gap-2">
                        {config.data_type === 'boolean' ? (
                          <InputSwitch
                            checked={config.value === 'true'}
                            onChange={(e) => updateSystemConfig({ ...config, value: e.value ? 'true' : 'false' })}
                          />
                        ) : (
                          <Button
                            icon="pi pi-pencil"
                            text
                            onClick={() => {
                              setSelectedConfig(config);
                              setConfigDialog(true);
                            }}
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="col-12 md:col-6">
              <Card title="Platform Integrations">
                <div className="flex flex-column gap-4">
                  {platformConfigs.map((platform) => (
                    <div key={platform.id} className="border-1 border-300 border-round p-3">
                      <div className="flex justify-content-between align-items-start mb-2">
                        <h4 className="m-0">{platform.platform_name}</h4>
                        <InputSwitch
                          checked={platform.is_active}
                          onChange={(e) => adminApi.updatePlatformConfig(platform.id, { is_active: e.value })}
                        />
                      </div>
                      <div className="grid">
                        <div className="col-6">
                          <div className="text-sm text-600">Success Rate</div>
                          <div className="font-medium">{platform.success_rate}%</div>
                        </div>
                        <div className="col-6">
                          <div className="text-sm text-600">Response Time</div>
                          <div className="font-medium">{platform.avg_response_time}ms</div>
                        </div>
                      </div>
                      <Button
                        label="Test Connection"
                        icon="pi pi-check"
                        size="small"
                        className="mt-2"
                        onClick={() => testPlatformConnection(platform)}
                      />
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Analytics & Reports Tab */}
        <TabPanel header="Analytics" leftIcon="pi pi-chart-bar">
          <div className="grid">
            <div className="col-12 md:col-8">
              <Card title="System Metrics">
                <div className="grid">
                  {dashboardStats?.system_metrics?.map((metric, index) => (
                    <div key={index} className="col-12 md:col-6 lg:col-4">
                      <div className="border-1 border-300 border-round p-3">
                        <div className="flex justify-content-between align-items-center mb-2">
                          <h5 className="m-0">{metric.name}</h5>
                          {renderMetricStatus(metric)}
                        </div>
                        <ProgressBar
                          value={Math.min(metric.value / 100 * 100, 100)}
                          className="mb-2"
                        />
                        <div className="text-sm text-600">{metric.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="col-12 md:col-4">
              <Card title="Quick Actions">
                <div className="flex flex-column gap-3">
                  <Button
                    label="Generate Revenue Report"
                    icon="pi pi-file"
                    className="w-full"
                    onClick={() => adminApi.getRevenueSummary()}
                  />
                  <Button
                    label="Export Usage Data"
                    icon="pi pi-download"
                    className="w-full"
                    onClick={() => adminApi.exportSystemData('usage')}
                  />
                  <Button
                    label="Security Report"
                    icon="pi pi-shield"
                    className="w-full"
                    onClick={() => adminApi.getSecurityReport()}
                  />
                  <Button
                    label="Create Backup"
                    icon="pi pi-save"
                    className="w-full"
                    severity="secondary"
                    onClick={() => adminApi.createBackup()}
                  />
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Activity Logs Tab */}
        <TabPanel header="Activity Logs" leftIcon="pi pi-history">
          <div className="grid">
            <div className="col-12 md:col-6">
              <Card title="Admin Activities">
                <Button
                  label="Load Activities"
                  icon="pi pi-refresh"
                  onClick={loadAdminActivities}
                  className="mb-3"
                />
                <DataTable
                  value={adminActivities}
                  paginator
                  rows={10}
                  responsiveLayout="scroll"
                >
                  <Column
                    field="admin_name"
                    header="Admin"
                    style={{ width: '25%' }}
                  />
                  <Column
                    field="description"
                    header="Action"
                    style={{ width: '50%' }}
                  />
                  <Column
                    field="created_at"
                    header="Time"
                    body={(rowData) => format(parseISO(rowData.created_at), 'MMM dd, HH:mm')}
                    style={{ width: '25%' }}
                  />
                </DataTable>
              </Card>
            </div>

            <div className="col-12 md:col-6">
              <Card title="Audit Logs">
                <Button
                  label="Load Audit Logs"
                  icon="pi pi-refresh"
                  onClick={loadAuditLogs}
                  className="mb-3"
                />
                <DataTable
                  value={auditLogs}
                  paginator
                  rows={10}
                  responsiveLayout="scroll"
                >
                  <Column
                    field="action"
                    header="Action"
                    style={{ width: '30%' }}
                  />
                  <Column
                    field="resource_type"
                    header="Resource"
                    style={{ width: '25%' }}
                  />
                  <Column
                    field="user_id"
                    header="User ID"
                    style={{ width: '20%' }}
                  />
                  <Column
                    field="created_at"
                    header="Time"
                    body={(rowData) => format(parseISO(rowData.created_at), 'MMM dd, HH:mm')}
                    style={{ width: '25%' }}
                  />
                </DataTable>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Notifications Tab */}
        <TabPanel header="Notifications" leftIcon="pi pi-bell">
          <Card title="Admin Notifications">
            <div className="flex flex-column gap-3">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`border-1 border-round p-3 ${notification.is_read ? 'border-300 bg-gray-50' : 'border-primary bg-primary-50'}`}
                >
                  <div className="flex align-items-start gap-3">
                    {renderNotificationIcon(notification)}
                    <div className="flex-1">
                      <h5 className="m-0 mb-2">{notification.title}</h5>
                      <p className="m-0 text-700">{notification.message}</p>
                      <div className="text-sm text-500 mt-2">
                        {format(parseISO(notification.created_at), 'MMM dd, yyyy HH:mm')}
                      </div>
                    </div>
                    {!notification.is_read && (
                      <Button
                        icon="pi pi-check"
                        text
                        rounded
                        onClick={() => adminApi.markNotificationRead(notification.id)}
                        tooltip="Mark as read"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabPanel>
      </TabView>

      {/* User Details Dialog */}
      <Dialog
        header="User Details"
        visible={userDialog}
        style={{ width: '50vw' }}
        onHide={() => setUserDialog(false)}
      >
        {selectedUser && (
          <div className="grid">
            <div className="col-12 md:col-6">
              <div className="field">
                <label className="font-medium">Full Name</label>
                <div className="text-700">{selectedUser.full_name}</div>
              </div>
              <div className="field">
                <label className="font-medium">Email</label>
                <div className="text-700">{selectedUser.email}</div>
              </div>
              <div className="field">
                <label className="font-medium">Company</label>
                <div className="text-700">{selectedUser.company || 'N/A'}</div>
              </div>
            </div>
            <div className="col-12 md:col-6">
              <div className="field">
                <label className="font-medium">Role</label>
                <div>{renderUserRole(selectedUser)}</div>
              </div>
              <div className="field">
                <label className="font-medium">Status</label>
                <div>{renderUserStatus(selectedUser)}</div>
              </div>
              <div className="field">
                <label className="font-medium">Subscription</label>
                <div>{renderSubscription(selectedUser)}</div>
              </div>
            </div>
            <div className="col-12">
              <Divider />
              <div className="grid">
                <div className="col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">{selectedUser.total_infringements}</div>
                    <div className="text-sm text-600">Infringements</div>
                  </div>
                </div>
                <div className="col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">{selectedUser.total_takedowns}</div>
                    <div className="text-sm text-600">Takedowns</div>
                  </div>
                </div>
                <div className="col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-500">{selectedUser.total_logins}</div>
                    <div className="text-sm text-600">Total Logins</div>
                  </div>
                </div>
                <div className="col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-500">{selectedUser.failed_login_attempts}</div>
                    <div className="text-sm text-600">Failed Logins</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </Dialog>

      {/* Bulk Actions Dialog */}
      <Dialog
        header="Bulk User Actions"
        visible={bulkActionDialog}
        style={{ width: '30vw' }}
        onHide={() => setBulkActionDialog(false)}
      >
        <div className="flex flex-column gap-4">
          <div>
            <label className="font-medium">Selected Users: {selectedUsers.length}</label>
          </div>
          <div className="flex flex-column gap-2">
            <Button
              label="Suspend Users"
              icon="pi pi-ban"
              severity="warning"
              className="w-full"
              onClick={() => executeBulkAction({
                operation: 'suspend',
                user_ids: selectedUsers.map(u => u.id),
                reason: 'Bulk administrative action'
              })}
            />
            <Button
              label="Activate Users"
              icon="pi pi-check"
              severity="success"
              className="w-full"
              onClick={() => executeBulkAction({
                operation: 'activate',
                user_ids: selectedUsers.map(u => u.id)
              })}
            />
            <Button
              label="Export Users"
              icon="pi pi-download"
              severity="info"
              className="w-full"
              onClick={() => executeBulkAction({
                operation: 'export',
                user_ids: selectedUsers.map(u => u.id)
              })}
            />
          </div>
        </div>
      </Dialog>

      {/* Config Edit Dialog */}
      <Dialog
        header="Edit Configuration"
        visible={configDialog}
        style={{ width: '30vw' }}
        onHide={() => setConfigDialog(false)}
      >
        {selectedConfig && (
          <div className="flex flex-column gap-4">
            <div className="field">
              <label className="font-medium">Key</label>
              <InputText value={selectedConfig.key} disabled className="w-full" />
            </div>
            <div className="field">
              <label className="font-medium">Value</label>
              {selectedConfig.data_type === 'json' ? (
                <InputTextarea
                  value={selectedConfig.value}
                  onChange={(e) => setSelectedConfig({ ...selectedConfig, value: e.target.value })}
                  className="w-full"
                  rows={5}
                />
              ) : (
                <InputText
                  value={selectedConfig.value}
                  onChange={(e) => setSelectedConfig({ ...selectedConfig, value: e.target.value })}
                  className="w-full"
                />
              )}
            </div>
            <div className="field">
              <label className="font-medium">Description</label>
              <div className="text-600">{selectedConfig.description}</div>
            </div>
            <div className="flex gap-2 justify-content-end">
              <Button
                label="Cancel"
                severity="secondary"
                onClick={() => setConfigDialog(false)}
              />
              <Button
                label="Save"
                onClick={() => updateSystemConfig(selectedConfig)}
              />
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default AdminPanel;