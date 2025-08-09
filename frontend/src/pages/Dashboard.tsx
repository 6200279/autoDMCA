import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card } from 'primereact/card';
import { Panel } from 'primereact/panel';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Button } from 'primereact/button';
import { ProgressBar } from 'primereact/progressbar';
import { Skeleton } from 'primereact/skeleton';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import { Chart } from 'primereact/chart';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { Tooltip } from 'primereact/tooltip';
import { Toast } from 'primereact/toast';
import { Message } from 'primereact/message';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip as ChartTooltip, 
  Legend,
  ArcElement,
  BarElement
} from 'chart.js';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../services/api';
import { 
  DashboardStats, 
  UsageMetrics, 
  RecentActivity, 
  PlatformData, 
  AnalyticsData,
  DashboardPreferences,
  QuickActionsData,
  ApiResponse 
} from '../types/api';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend
);

// Loading states for different sections
interface LoadingStates {
  stats: boolean;
  usage: boolean;
  activity: boolean;
  analytics: boolean;
  platformData: boolean;
  preferences: boolean;
}

// Error states
interface ErrorStates {
  stats: string | null;
  usage: string | null;
  activity: string | null;
  analytics: string | null;
  platformData: string | null;
  preferences: string | null;
}

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const [dateRange, setDateRange] = useState<Date[]>([
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    new Date()
  ]);
  
  // Loading states
  const [loading, setLoading] = useState<LoadingStates>({
    stats: true,
    usage: true,
    activity: true,
    analytics: true,
    platformData: true,
    preferences: true
  });
  
  // Error states
  const [errors, setErrors] = useState<ErrorStates>({
    stats: null,
    usage: null,
    activity: null,
    analytics: null,
    platformData: null,
    preferences: null
  });
  
  // Last updated timestamps
  const [lastUpdated, setLastUpdated] = useState<Record<string, string>>({});
  
  // Data states
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [platformData, setPlatformData] = useState<PlatformData[]>([]);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [preferences, setPreferences] = useState<DashboardPreferences | null>(null);
  const [quickActionsData, setQuickActionsData] = useState<QuickActionsData | null>(null);

  // Utility functions for error handling
  const showError = useCallback((section: string, error: any) => {
    const message = error?.response?.data?.detail || error?.message || 'An unexpected error occurred';
    setErrors(prev => ({ ...prev, [section]: message }));
    
    toast.current?.show({
      severity: 'error',
      summary: `${section.charAt(0).toUpperCase() + section.slice(1)} Error`,
      detail: message,
      life: 5000
    });
  }, []);
  
  const clearError = useCallback((section: string) => {
    setErrors(prev => ({ ...prev, [section]: null }));
  }, []);
  
  const updateLastUpdated = useCallback((section: string) => {
    setLastUpdated(prev => ({ ...prev, [section]: new Date().toISOString() }));
  }, []);

  // API functions
  const fetchDashboardStats = useCallback(async () => {
    setLoading(prev => ({ ...prev, stats: true }));
    clearError('stats');
    
    try {
      const dateParams = dateRange.length === 2 ? {
        start: dateRange[0].toISOString(),
        end: dateRange[1].toISOString()
      } : undefined;
      
      const response = await dashboardApi.getStats(dateParams);
      setStats(response.data);
      updateLastUpdated('stats');
    } catch (error) {
      showError('stats', error);
    } finally {
      setLoading(prev => ({ ...prev, stats: false }));
    }
  }, [dateRange, showError, clearError, updateLastUpdated]);
  
  const fetchUsageMetrics = useCallback(async () => {
    setLoading(prev => ({ ...prev, usage: true }));
    clearError('usage');
    
    try {
      const response = await dashboardApi.getUsageMetrics();
      setUsageMetrics(response.data);
      updateLastUpdated('usage');
    } catch (error) {
      showError('usage', error);
    } finally {
      setLoading(prev => ({ ...prev, usage: false }));
    }
  }, [showError, clearError, updateLastUpdated]);
  
  const fetchRecentActivity = useCallback(async () => {
    setLoading(prev => ({ ...prev, activity: true }));
    clearError('activity');
    
    try {
      const response = await dashboardApi.getRecentActivity({ limit: 10 });
      setRecentActivity(response.data);
      updateLastUpdated('activity');
    } catch (error) {
      showError('activity', error);
    } finally {
      setLoading(prev => ({ ...prev, activity: false }));
    }
  }, [showError, clearError, updateLastUpdated]);
  
  const fetchAnalyticsData = useCallback(async () => {
    setLoading(prev => ({ ...prev, analytics: true }));
    clearError('analytics');
    
    try {
      const dateParams = dateRange.length === 2 ? {
        dateRange: {
          start: dateRange[0].toISOString(),
          end: dateRange[1].toISOString()
        },
        granularity: 'month' as const
      } : undefined;
      
      const response = await dashboardApi.getAnalytics(dateParams);
      setAnalyticsData(response.data);
      updateLastUpdated('analytics');
    } catch (error) {
      showError('analytics', error);
    } finally {
      setLoading(prev => ({ ...prev, analytics: false }));
    }
  }, [dateRange, showError, clearError, updateLastUpdated]);
  
  const fetchPlatformData = useCallback(async () => {
    setLoading(prev => ({ ...prev, platformData: true }));
    clearError('platformData');
    
    try {
      const dateParams = dateRange.length === 2 ? {
        start: dateRange[0].toISOString(),
        end: dateRange[1].toISOString()
      } : undefined;
      
      const response = await dashboardApi.getPlatformDistribution(dateParams);
      setPlatformData(response.data);
      updateLastUpdated('platformData');
    } catch (error) {
      showError('platformData', error);
    } finally {
      setLoading(prev => ({ ...prev, platformData: false }));
    }
  }, [dateRange, showError, clearError, updateLastUpdated]);
  
  const fetchPreferences = useCallback(async () => {
    setLoading(prev => ({ ...prev, preferences: true }));
    clearError('preferences');
    
    try {
      const response = await dashboardApi.getDashboardPreferences();
      setPreferences(response.data);
      updateLastUpdated('preferences');
    } catch (error) {
      showError('preferences', error);
    } finally {
      setLoading(prev => ({ ...prev, preferences: false }));
    }
  }, [showError, clearError, updateLastUpdated]);
  
  const fetchQuickActionsData = useCallback(async () => {
    try {
      const response = await dashboardApi.getQuickActionsData();
      setQuickActionsData(response.data);
    } catch (error) {
      // Quick actions data is non-critical, so we don't show errors
      console.warn('Failed to load quick actions data:', error);
    }
  }, []);
  
  // Refresh all data
  const refreshAllData = useCallback(async () => {
    await Promise.allSettled([
      fetchDashboardStats(),
      fetchUsageMetrics(),
      fetchRecentActivity(),
      fetchAnalyticsData(),
      fetchPlatformData(),
      fetchQuickActionsData()
    ]);
  }, [fetchDashboardStats, fetchUsageMetrics, fetchRecentActivity, fetchAnalyticsData, fetchPlatformData, fetchQuickActionsData]);
  
  // Initial data load
  useEffect(() => {
    fetchPreferences();
    refreshAllData();
  }, [fetchPreferences, refreshAllData]);
  
  // Refresh data when date range changes
  useEffect(() => {
    if (dateRange.length === 2) {
      fetchDashboardStats();
      fetchAnalyticsData();
      fetchPlatformData();
    }
  }, [dateRange, fetchDashboardStats, fetchAnalyticsData, fetchPlatformData]);
  
  // Set up auto-refresh interval based on preferences
  useEffect(() => {
    if (preferences?.realTimeUpdates && preferences?.refreshInterval) {
      refreshIntervalRef.current = setInterval(() => {
        refreshAllData();
      }, preferences.refreshInterval * 1000);
      
      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [preferences, refreshAllData]);

  // Chart data - using real analytics data with fallbacks
  const monthlyTrendsData = analyticsData?.monthlyTrends || {
    labels: [],
    datasets: []
  };

  const platformDistributionData = analyticsData?.platformDistribution || {
    labels: [],
    datasets: []
  };

  const successRateData = analyticsData?.successRateByPlatform || {
    labels: [],
    datasets: []
  };
  
  // Export dashboard data
  const handleExportData = useCallback(async (format: 'csv' | 'xlsx' | 'pdf') => {
    try {
      const params = {
        format,
        dateRange: dateRange.length === 2 ? {
          start: dateRange[0].toISOString(),
          end: dateRange[1].toISOString()
        } : undefined,
        sections: ['stats', 'usage', 'activity', 'analytics', 'platformData']
      };
      
      const response = await dashboardApi.exportDashboardData(params);
      
      // Handle file download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `dashboard-report.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Export Successful',
        detail: `Dashboard data exported as ${format.toUpperCase()}`,
        life: 3000
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Export Failed',
        detail: 'Unable to export dashboard data. Please try again.',
        life: 5000
      });
    }
  }, [dateRange]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      }
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
      }
    }
  };

  // Helper functions
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'success': return 'success';
      case 'pending': return 'warning';
      case 'in-progress': return 'info';
      case 'failed': return 'danger';
      default: return null;
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'infringement': return 'pi pi-exclamation-triangle';
      case 'takedown': return 'pi pi-file';
      case 'scan': return 'pi pi-search';
      case 'profile': return 'pi pi-user';
      default: return 'pi pi-info-circle';
    }
  };

  const formatTimestamp = (timestamp: string | Date) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
      return `${diffInMinutes}m ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      return date.toLocaleDateString();
    }
  };
  
  // Check if data is loading
  const isDataLoading = Object.values(loading).some(Boolean);
  const hasErrors = Object.values(errors).some(Boolean);

  // Column templates for DataTable
  const activityTypeTemplate = (rowData: RecentActivity) => (
    <div className="flex align-items-center gap-2">
      <i className={`${getActivityIcon(rowData.type)} text-lg`} />
      <span className="font-medium">{rowData.title}</span>
    </div>
  );

  const statusTemplate = (rowData: RecentActivity) => (
    <Tag 
      value={rowData.status} 
      severity={getStatusSeverity(rowData.status)}
      className="text-sm"
    />
  );

  const platformTemplate = (rowData: RecentActivity) => (
    <Badge value={rowData.platform} size="normal" />
  );

  const timestampTemplate = (rowData: RecentActivity) => {
    const lastUpdatedTime = lastUpdated.activity ? formatTimestamp(lastUpdated.activity) : null;
    
    return (
      <div className="flex flex-column gap-1">
        <span className="text-color-secondary text-sm">{formatTimestamp(rowData.timestamp)}</span>
        {lastUpdatedTime && (
          <span className="text-xs text-500">Updated {lastUpdatedTime}</span>
        )}
      </div>
    );
  };

  const actionsTemplate = (rowData: RecentActivity) => (
    <div className="flex gap-1">
      <Button 
        icon="pi pi-eye" 
        size="small" 
        text 
        tooltip="View Details" 
        onClick={() => navigate(`/protection/activity/${rowData.id}`)}
      />
      {rowData.url && (
        <Button 
          icon="pi pi-external-link" 
          size="small" 
          text 
          tooltip="Open URL" 
          onClick={() => window.open(rowData.url, '_blank')}
        />
      )}
    </div>
  );

  // Render error message component
  const renderErrorMessage = (section: string, onRetry: () => void) => {
    const error = errors[section as keyof ErrorStates];
    if (!error) return null;
    
    return (
      <Message
        severity="error"
        text={error}
        className="mb-3"
        content={
          <div className="flex justify-content-between align-items-center w-full">
            <span>{error}</span>
            <Button
              label="Retry"
              icon="pi pi-refresh"
              size="small"
              text
              onClick={onRetry}
            />
          </div>
        }
      />
    );
  };
  
  // Render loading skeleton for specific sections
  const renderSectionSkeleton = (height: string = '80px') => (
    <Skeleton width="100%" height={height} className="border-round" />
  );

  return (
    <>
      <Toast ref={toast} />
      <div className="grid">
      {/* Header */}
      <div className="col-12">
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">Welcome back, {user?.full_name || 'User'}!</h2>
            <p className="text-600 m-0 mt-1">Here's what's happening with your content protection</p>
          </div>
          <div className="flex gap-2 align-items-center">
            <Calendar 
              value={dateRange} 
              onChange={(e) => setDateRange(e.value as Date[])} 
              selectionMode="range" 
              readOnlyInput 
              showIcon
              placeholder="Select date range"
              className="w-full md:w-auto"
            />
            <div className="flex gap-2">
              <Button 
                label="Refresh" 
                icon="pi pi-refresh" 
                size="small"
                outlined
                loading={isDataLoading}
                onClick={refreshAllData}
                tooltip="Refresh all data"
              />
              <Button 
                label="Export" 
                icon="pi pi-download" 
                outlined 
                size="small"
                onClick={(e) => {
                  e.preventDefault();
                  handleExportData('xlsx');
                }}
                tooltip="Export dashboard data"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Overview Statistics */}
      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? renderSectionSkeleton() : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="text-500 font-medium text-sm">Total Profiles</div>
                <div className="text-900 font-bold text-xl mt-1">{stats?.totalProfiles || 0}</div>
                <div className="flex align-items-center gap-1 mt-2">
                  <i className={`pi ${(stats?.profilesChange || 0) >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                  <span className={`text-sm font-medium ${(stats?.profilesChange || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {Math.abs(stats?.profilesChange || 0)}%
                  </span>
                  <span className="text-500 text-sm">this month</span>
                </div>
              </div>
              <div className="bg-blue-100 text-blue-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
                <i className="pi pi-user text-xl" />
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? renderSectionSkeleton() : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="text-500 font-medium text-sm">Active Scans</div>
                <div className="text-900 font-bold text-xl mt-1">{stats?.activeScans || 0}</div>
                <div className="flex align-items-center gap-1 mt-2">
                  <i className={`pi ${(stats?.scansChange || 0) >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                  <span className={`text-sm font-medium ${(stats?.scansChange || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {Math.abs(stats?.scansChange || 0)}%
                  </span>
                  <span className="text-500 text-sm">this month</span>
                </div>
              </div>
              <div className="bg-purple-100 text-purple-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
                <i className="pi pi-search text-xl" />
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? renderSectionSkeleton() : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="text-500 font-medium text-sm">Infringements Found</div>
                <div className="text-900 font-bold text-xl mt-1">{stats?.infringementsFound || 0}</div>
                <div className="flex align-items-center gap-1 mt-2">
                  <i className={`pi ${(stats?.infringementsChange || 0) >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                  <span className={`text-sm font-medium ${(stats?.infringementsChange || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {Math.abs(stats?.infringementsChange || 0)}%
                  </span>
                  <span className="text-500 text-sm">this month</span>
                </div>
              </div>
              <div className="bg-orange-100 text-orange-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
                <i className="pi pi-exclamation-triangle text-xl" />
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? renderSectionSkeleton() : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="text-500 font-medium text-sm">Takedowns Sent</div>
                <div className="text-900 font-bold text-xl mt-1">{stats?.takedownsSent || 0}</div>
                <div className="flex align-items-center gap-1 mt-2">
                  <i className={`pi ${(stats?.takedownsChange || 0) >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                  <span className={`text-sm font-medium ${(stats?.takedownsChange || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {Math.abs(stats?.takedownsChange || 0)}%
                  </span>
                  <span className="text-500 text-sm">this month</span>
                </div>
              </div>
              <div className="bg-green-100 text-green-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
                <i className="pi pi-file text-xl" />
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Usage Metrics */}
      <div className="col-12 md:col-8">
        <Card title="Usage Metrics" className="h-full">
          {renderErrorMessage('usage', fetchUsageMetrics)}
          {loading.usage ? renderSectionSkeleton('200px') : (
            <>
              <div className="grid">
                <div className="col-12 md:col-6">
                  <div className="mb-3">
                    <div className="flex justify-content-between align-items-center mb-2">
                      <span className="text-900 font-medium">Monthly Scans</span>
                      <span className="text-600">
                        {usageMetrics?.scansUsed || 0} / {usageMetrics?.scansLimit || 0}
                      </span>
                    </div>
                    <ProgressBar 
                      value={usageMetrics ? (usageMetrics.scansUsed / usageMetrics.scansLimit) * 100 : 0} 
                      showValue={false}
                      style={{ height: '8px' }}
                    />
                  </div>
                </div>
                <div className="col-12 md:col-6">
                  <div className="mb-3">
                    <div className="flex justify-content-between align-items-center mb-2">
                      <span className="text-900 font-medium">Success Rate</span>
                      <span className="text-600">{usageMetrics?.successRate || 0}%</span>
                    </div>
                    <ProgressBar 
                      value={usageMetrics?.successRate || 0} 
                      showValue={false}
                      style={{ height: '8px' }}
                      color="#10B981"
                    />
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 mt-4">
                <div className="flex align-items-center gap-2 p-3 bg-blue-50 border-round">
                  <i className="pi pi-calendar text-blue-600" />
                  <div>
                    <div className="text-blue-900 font-medium text-sm">This Month</div>
                    <div className="text-blue-600 text-lg font-bold">{usageMetrics?.scansUsed || 0}</div>
                  </div>
                </div>
                <div className="flex align-items-center gap-2 p-3 bg-green-50 border-round">
                  <i className="pi pi-check-circle text-green-600" />
                  <div>
                    <div className="text-green-900 font-medium text-sm">Success Rate</div>
                    <div className="text-green-600 text-lg font-bold">{usageMetrics?.monthlySuccessRate || 0}%</div>
                  </div>
                </div>
                {usageMetrics?.resetDate && (
                  <div className="flex align-items-center gap-2 p-3 bg-gray-50 border-round">
                    <i className="pi pi-refresh text-gray-600" />
                    <div>
                      <div className="text-gray-900 font-medium text-sm">Resets</div>
                      <div className="text-gray-600 text-sm">
                        {new Date(usageMetrics.resetDate).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="col-12 md:col-4">
        <Card title="Quick Actions" className="h-full">
          <div className="flex flex-column gap-3">
            <Button 
              label="Submit New URL" 
              icon="pi pi-plus" 
              className="p-button-primary w-full justify-content-start"
              onClick={() => navigate('/protection/submissions')}
            />
            <Button 
              label="Create Profile" 
              icon="pi pi-user-plus" 
              outlined 
              className="w-full justify-content-start"
              onClick={() => navigate('/protection/profiles')}
            />
            <Button 
              label="View Reports" 
              icon="pi pi-chart-bar" 
              outlined 
              className="w-full justify-content-start"
              onClick={() => navigate('/reports')}
            />
            <Divider />
            <div className="text-center">
              <div className="text-500 text-sm mb-2">Need help?</div>
              <Button 
                label="Contact Support" 
                icon="pi pi-question-circle" 
                link 
                size="small"
                onClick={() => navigate('/support')}
              />
            </div>
          </div>
        </Card>
      </div>

      {/* Monthly Trends Chart */}
      <div className="col-12 lg:col-8">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-center mb-3">
            <span className="text-900 font-bold text-lg">Monthly Trends</span>
            {lastUpdated.analytics && (
              <span className="text-sm text-500">
                Updated {formatTimestamp(lastUpdated.analytics)}
              </span>
            )}
          </div>
          {renderErrorMessage('analytics', fetchAnalyticsData)}
          {loading.analytics ? renderSectionSkeleton('300px') : (
            <div style={{ height: '300px' }}>
              {monthlyTrendsData.labels.length > 0 ? (
                <Chart 
                  type="line" 
                  data={monthlyTrendsData} 
                  options={chartOptions} 
                  height="300px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <i className="pi pi-chart-line text-6xl text-300 mb-3" />
                    <p className="text-500">No trend data available for the selected period</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Platform Distribution */}
      <div className="col-12 lg:col-4">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-center mb-3">
            <span className="text-900 font-bold text-lg">Platform Distribution</span>
            {lastUpdated.platformData && (
              <span className="text-sm text-500">
                Updated {formatTimestamp(lastUpdated.platformData)}
              </span>
            )}
          </div>
          {renderErrorMessage('platformData', fetchPlatformData)}
          {loading.platformData ? renderSectionSkeleton('300px') : (
            <div style={{ height: '300px' }}>
              {platformDistributionData.labels.length > 0 ? (
                <Chart 
                  type="doughnut" 
                  data={platformDistributionData} 
                  options={doughnutOptions}
                  height="300px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <i className="pi pi-chart-pie text-6xl text-300 mb-3" />
                    <p className="text-500">No platform data available</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Success Rate by Platform */}
      <div className="col-12 lg:col-6">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-center mb-3">
            <span className="text-900 font-bold text-lg">Success Rate by Platform</span>
            {lastUpdated.analytics && (
              <span className="text-sm text-500">
                Updated {formatTimestamp(lastUpdated.analytics)}
              </span>
            )}
          </div>
          {renderErrorMessage('analytics', fetchAnalyticsData)}
          {loading.analytics ? renderSectionSkeleton('250px') : (
            <div style={{ height: '250px' }}>
              {successRateData.labels.length > 0 ? (
                <Chart 
                  type="bar" 
                  data={successRateData} 
                  options={chartOptions}
                  height="250px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <i className="pi pi-chart-bar text-6xl text-300 mb-3" />
                    <p className="text-500">No success rate data available</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Platform Performance Table */}
      <div className="col-12 lg:col-6">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-center mb-3">
            <span className="text-900 font-bold text-lg">Platform Performance</span>
            {lastUpdated.platformData && (
              <span className="text-sm text-500">
                Updated {formatTimestamp(lastUpdated.platformData)}
              </span>
            )}
          </div>
          {renderErrorMessage('platformData', fetchPlatformData)}
          {loading.platformData ? renderSectionSkeleton('250px') : (
            <DataTable 
              value={platformData} 
              size="small"
              showGridlines
              emptyMessage="No platform data available"
            >
              <Column field="platform" header="Platform" />
              <Column 
                field="infringements" 
                header="Infringements" 
                body={(rowData) => (
                  <Badge value={rowData.infringements} severity="warning" />
                )}
              />
              <Column 
                field="takedowns" 
                header="Takedowns" 
                body={(rowData) => (
                  <Badge value={rowData.takedowns} severity="success" />
                )}
              />
              <Column 
                field="successRate" 
                header="Success Rate" 
                body={(rowData) => (
                  <div className="flex align-items-center gap-2">
                    <ProgressBar 
                      value={rowData.successRate} 
                      showValue={false} 
                      style={{ width: '60px', height: '6px' }}
                    />
                    <span className="text-sm">{rowData.successRate}%</span>
                    {rowData.trend && (
                      <i className={`pi ${
                        rowData.trend === 'up' ? 'pi-arrow-up text-green-500' :
                        rowData.trend === 'down' ? 'pi-arrow-down text-red-500' :
                        'pi-minus text-gray-500'
                      } text-sm`} />
                    )}
                  </div>
                )}
              />
            </DataTable>
          )}
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="col-12">
        <Panel 
          toggleable 
          className="mt-4"
          headerTemplate={(options) => (
            <div className="flex justify-content-between align-items-center w-full">
              <div className="flex align-items-center gap-3">
                <span className="font-bold text-lg">Recent Activity</span>
                {lastUpdated.activity && (
                  <span className="text-sm text-500">
                    Updated {formatTimestamp(lastUpdated.activity)}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button 
                  icon="pi pi-refresh" 
                  size="small"
                  text
                  loading={loading.activity}
                  onClick={fetchRecentActivity}
                  tooltip="Refresh activity"
                />
                <Button 
                  label="View All" 
                  link 
                  size="small"
                  onClick={() => navigate('/protection/activity')}
                />
                {options.togglerElement}
              </div>
            </div>
          )}
        >
          {renderErrorMessage('activity', fetchRecentActivity)}
          {loading.activity ? renderSectionSkeleton('300px') : (
            <DataTable 
              value={recentActivity} 
              paginator 
              rows={10}
              size="small"
              showGridlines
              emptyMessage="No recent activity found"
              loading={loading.activity}
            >
              <Column 
                field="type" 
                header="Activity" 
                body={activityTypeTemplate}
                style={{ width: '25%' }}
              />
              <Column 
                field="description" 
                header="Description" 
                style={{ width: '30%' }}
              />
              <Column 
                field="platform" 
                header="Platform" 
                body={platformTemplate}
                style={{ width: '15%' }}
              />
              <Column 
                field="status" 
                header="Status" 
                body={statusTemplate}
                style={{ width: '15%' }}
              />
              <Column 
                field="timestamp" 
                header="Time" 
                body={timestampTemplate}
                style={{ width: '10%' }}
              />
              <Column 
                body={actionsTemplate}
                style={{ width: '5%' }}
              />
            </DataTable>
          )}
        </Panel>
      </div>
    </div>
    </>
  );
};

export default Dashboard;