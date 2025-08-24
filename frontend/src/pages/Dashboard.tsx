import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Panel } from 'primereact/panel';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { ProgressBar } from 'primereact/progressbar';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import { Chart } from 'primereact/chart';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { Button } from 'primereact/button';
import { Tooltip } from 'primereact/tooltip';
import { Toast } from 'primereact/toast';
import { Message } from 'primereact/message';
import { EnhancedCard } from '../components/common/EnhancedCard';
import { EnhancedButton } from '../components/common/EnhancedButton';
import { EnhancedLoading } from '../components/common/EnhancedLoading';
import { SecurityShield, SecurityBadge, TrustIndicatorBar, DataProtectionNotice } from '../components/common/TrustIndicators';
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
import { useDashboardRealtime, useNotificationsRealtime } from '../contexts/WebSocketContext';

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
  
  // WebSocket real-time updates
  const { dashboardStats: realtimeStats } = useDashboardRealtime();
  const { notifications } = useNotificationsRealtime();
  
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
  
  // Data states with defensive initialization
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [platformData, setPlatformData] = useState<PlatformData[]>([]);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [preferences, setPreferences] = useState<DashboardPreferences | null>(null);
  const [quickActionsData, setQuickActionsData] = useState<QuickActionsData | null>(null);
  
  // Safe data accessors with fallbacks
  const safeRecentActivity = React.useMemo(() => {
    return Array.isArray(recentActivity) ? recentActivity : [];
  }, [recentActivity]);
  
  const safePlatformData = React.useMemo(() => {
    return Array.isArray(platformData) ? platformData : [];
  }, [platformData]);

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
      // Fix: Extract activities array from response.data with validation
      const activities = response.data?.activities;
      setRecentActivity(Array.isArray(activities) ? activities : []);
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
      // Fix: Extract platforms array from response.data with validation
      const platforms = response.data?.platforms;
      setPlatformData(Array.isArray(platforms) ? platforms : []);
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
  
  // Handle real-time dashboard stats updates
  useEffect(() => {
    if (realtimeStats) {
      setStats(prevStats => ({
        ...prevStats,
        ...realtimeStats
      }));
    }
  }, [realtimeStats]);
  
  // Handle real-time notifications
  useEffect(() => {
    notifications.forEach(notification => {
      if (notification.category === 'dashboard' || notification.category === 'system') {
        toast.current?.show({
          severity: notification.type === 'success' ? 'success' : 
                   notification.type === 'error' ? 'error' : 
                   notification.type === 'warning' ? 'warn' : 'info',
          summary: notification.title,
          detail: notification.message,
          life: 5000
        });
      }
    });
  }, [notifications]);

  // Chart data - using real analytics data with robust fallbacks
  const monthlyTrendsData = React.useMemo(() => {
    if (!analyticsData?.monthlyTrends) {
      return { labels: [], datasets: [] };
    }
    
    const trends = analyticsData.monthlyTrends;
    if (!Array.isArray(trends.labels) || !Array.isArray(trends.datasets)) {
      return { labels: [], datasets: [] };
    }
    
    return {
      labels: trends.labels || [],
      datasets: trends.datasets || []
    };
  }, [analyticsData]);

  const platformDistributionData = React.useMemo(() => {
    if (!analyticsData?.platformDistribution) {
      return { labels: [], datasets: [] };
    }
    
    const distribution = analyticsData.platformDistribution;
    if (!Array.isArray(distribution.labels) || !Array.isArray(distribution.datasets)) {
      return { labels: [], datasets: [] };
    }
    
    return {
      labels: distribution.labels || [],
      datasets: distribution.datasets || []
    };
  }, [analyticsData]);

  const successRateData = React.useMemo(() => {
    if (!analyticsData?.successRateByPlatform) {
      return { labels: [], datasets: [] };
    }
    
    const successRate = analyticsData.successRateByPlatform;
    if (!Array.isArray(successRate.labels) || !Array.isArray(successRate.datasets)) {
      return { labels: [], datasets: [] };
    }
    
    return {
      labels: successRate.labels || [],
      datasets: successRate.datasets || []
    };
  }, [analyticsData]);
  
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
  
  // Render enhanced loading for specific sections
  const renderSectionSkeleton = (height: string = '80px') => (
    <EnhancedLoading type="skeleton" variant="card" size="md" />
  );

  return (
    <>
      <Toast ref={toast} />
      <div className="grid">
      {/* Enhanced Header with Security Branding */}
      <div className="col-12">
        <EnhancedCard variant="filled" padding="lg" className="mb-4" style={{
          background: 'linear-gradient(135deg, var(--autodmca-primary-600), var(--autodmca-primary-700))',
          color: 'white',
          border: 'none'
        }}>
          <div className="flex flex-column lg:flex-row lg:justify-content-between lg:align-items-center gap-4">
            <div className="flex align-items-center gap-3">
              <SecurityShield level="premium" size="lg" animated={true} />
              <div>
                <h1 className="m-0 text-white text-3xl font-bold">
                  Welcome back, {user?.full_name || 'User'}!
                </h1>
                <p className="m-0 mt-2 text-white opacity-90 text-lg">
                  Your content protection dashboard - Secure, Professional, Reliable
                </p>
                <TrustIndicatorBar 
                  indicators={['ssl', 'verified', 'professional', 'gdpr']} 
                  size="sm" 
                  layout="horizontal"
                  className="mt-3"
                />
              </div>
            </div>
            <div className="flex gap-3 align-items-center">
              <Calendar 
                value={dateRange} 
                onChange={(e) => setDateRange(e.value as Date[])} 
                selectionMode="range" 
                readOnlyInput 
                showIcon
                placeholder="Select date range"
                aria-label="Select date range for dashboard metrics"
                className="w-full lg:w-auto"
                style={{ minWidth: '250px' }}
              />
              <div className="flex gap-2">
                <EnhancedButton 
                  variant="secondary" 
                  size="md"
                  icon="pi pi-refresh"
                  loading={isDataLoading}
                  loadingText="Refreshing..."
                  onClick={refreshAllData}
                  elevation="2"
                >
                  Refresh
                </EnhancedButton>
                <EnhancedButton 
                  variant="outline" 
                  size="md"
                  icon="pi pi-download"
                  onClick={(e) => {
                    e.preventDefault();
                    handleExportData('xlsx');
                  }}
                  elevation="2"
                >
                  Export
                </EnhancedButton>
              </div>
            </div>
          </div>
        </EnhancedCard>
      </div>

      {/* Enhanced Statistics Cards */}
      <div className="col-12 md:col-6 lg:col-3">
        <EnhancedCard variant="elevated" padding="lg" interactive elevation="2" className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? (
            <EnhancedLoading type="skeleton" variant="card" size="md" />
          ) : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="flex align-items-center gap-2 mb-2">
                  <SecurityBadge type="verified" size="sm" showText={false} />
                  <span className="text-600 font-semibold text-sm uppercase tracking-wide">
                    Protected Profiles
                  </span>
                </div>
                <div className="text-900 font-bold text-3xl mb-2">
                  {stats?.totalProfiles || 0}
                </div>
                <div className="flex align-items-center gap-2">
                  <div className="flex align-items-center gap-1">
                    <i className={`pi ${(stats?.profilesChange || 0) >= 0 ? 'pi-arrow-up' : 'pi-arrow-down'} text-sm`}
                       style={{ color: (stats?.profilesChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }} />
                    <span className={`text-sm font-bold`}
                          style={{ color: (stats?.profilesChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }}>
                      {Math.abs(stats?.profilesChange || 0)}%
                    </span>
                  </div>
                  <span className="text-600 text-sm">this month</span>
                </div>
              </div>
              <div className="w-4rem h-4rem border-circle flex align-items-center justify-content-center"
                   style={{ 
                     background: 'linear-gradient(135deg, var(--autodmca-primary-100), var(--autodmca-primary-200))',
                     color: 'var(--autodmca-primary-700)' 
                   }}>
                <i className="pi pi-shield text-2xl" />
              </div>
            </div>
          )}
        </EnhancedCard>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <EnhancedCard variant="elevated" padding="lg" interactive elevation="2" className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? (
            <EnhancedLoading type="skeleton" variant="card" size="md" />
          ) : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="flex align-items-center gap-2 mb-2">
                  <SecurityBadge type="ssl" size="sm" showText={false} />
                  <span className="text-600 font-semibold text-sm uppercase tracking-wide">
                    Active Scans
                  </span>
                </div>
                <div className="text-900 font-bold text-3xl mb-2">
                  {stats?.activeScans || 0}
                </div>
                <div className="flex align-items-center gap-2">
                  <div className="flex align-items-center gap-1">
                    <i className={`pi ${(stats?.scansChange || 0) >= 0 ? 'pi-arrow-up' : 'pi-arrow-down'} text-sm`}
                       style={{ color: (stats?.scansChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }} />
                    <span className={`text-sm font-bold`}
                          style={{ color: (stats?.scansChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }}>
                      {Math.abs(stats?.scansChange || 0)}%
                    </span>
                  </div>
                  <span className="text-600 text-sm">this month</span>
                </div>
              </div>
              <div className="w-4rem h-4rem border-circle flex align-items-center justify-content-center"
                   style={{ 
                     background: 'linear-gradient(135deg, var(--autodmca-info-100), var(--autodmca-info-200))',
                     color: 'var(--autodmca-info-700)' 
                   }}>
                <i className="pi pi-search text-2xl" />
              </div>
            </div>
          )}
        </EnhancedCard>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <EnhancedCard variant="elevated" padding="lg" interactive elevation="2" className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? (
            <EnhancedLoading type="skeleton" variant="card" size="md" />
          ) : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="flex align-items-center gap-2 mb-2">
                  <SecurityBadge type="dmca" size="sm" showText={false} />
                  <span className="text-600 font-semibold text-sm uppercase tracking-wide">
                    Threats Detected
                  </span>
                </div>
                <div className="text-900 font-bold text-3xl mb-2">
                  {stats?.infringementsFound || 0}
                </div>
                <div className="flex align-items-center gap-2">
                  <div className="flex align-items-center gap-1">
                    <i className={`pi ${(stats?.infringementsChange || 0) >= 0 ? 'pi-arrow-up' : 'pi-arrow-down'} text-sm`}
                       style={{ color: (stats?.infringementsChange || 0) >= 0 ? 'var(--autodmca-danger-600)' : 'var(--autodmca-success-600)' }} />
                    <span className={`text-sm font-bold`}
                          style={{ color: (stats?.infringementsChange || 0) >= 0 ? 'var(--autodmca-danger-600)' : 'var(--autodmca-success-600)' }}>
                      {Math.abs(stats?.infringementsChange || 0)}%
                    </span>
                  </div>
                  <span className="text-600 text-sm">this month</span>
                </div>
              </div>
              <div className="w-4rem h-4rem border-circle flex align-items-center justify-content-center"
                   style={{ 
                     background: 'linear-gradient(135deg, var(--autodmca-warning-100), var(--autodmca-warning-200))',
                     color: 'var(--autodmca-warning-700)' 
                   }}>
                <i className="pi pi-exclamation-triangle text-2xl" />
              </div>
            </div>
          )}
        </EnhancedCard>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <EnhancedCard variant="elevated" padding="lg" interactive elevation="2" className="h-full">
          {renderErrorMessage('stats', fetchDashboardStats)}
          {loading.stats ? (
            <EnhancedLoading type="skeleton" variant="card" size="md" />
          ) : (
            <div className="flex justify-content-between align-items-start">
              <div>
                <div className="flex align-items-center gap-2 mb-2">
                  <SecurityBadge type="professional" size="sm" showText={false} />
                  <span className="text-600 font-semibold text-sm uppercase tracking-wide">
                    Actions Taken
                  </span>
                </div>
                <div className="text-900 font-bold text-3xl mb-2">
                  {stats?.takedownsSent || 0}
                </div>
                <div className="flex align-items-center gap-2">
                  <div className="flex align-items-center gap-1">
                    <i className={`pi ${(stats?.takedownsChange || 0) >= 0 ? 'pi-arrow-up' : 'pi-arrow-down'} text-sm`}
                       style={{ color: (stats?.takedownsChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }} />
                    <span className={`text-sm font-bold`}
                          style={{ color: (stats?.takedownsChange || 0) >= 0 ? 'var(--autodmca-success-600)' : 'var(--autodmca-danger-600)' }}>
                      {Math.abs(stats?.takedownsChange || 0)}%
                    </span>
                  </div>
                  <span className="text-600 text-sm">this month</span>
                </div>
              </div>
              <div className="w-4rem h-4rem border-circle flex align-items-center justify-content-center"
                   style={{ 
                     background: 'linear-gradient(135deg, var(--autodmca-success-100), var(--autodmca-success-200))',
                     color: 'var(--autodmca-success-700)' 
                   }}>
                <i className="pi pi-check-circle text-2xl" />
              </div>
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Usage Metrics */}
      <div className="col-12 md:col-8">
        <EnhancedCard 
          title="Usage Analytics" 
          variant="elevated" 
          padding="lg" 
          elevation="2"
          className="h-full"
          headerActions={
            <SecurityBadge type="professional" size="sm" />
          }
        >
          {renderErrorMessage('usage', fetchUsageMetrics)}
          {loading.usage ? (
            <EnhancedLoading type="skeleton" variant="dashboard" size="md" />
          ) : (
            <>
              <div className="grid">
                <div className="col-12 md:col-6">
                  <div className="mb-4">
                    <div className="flex justify-content-between align-items-center mb-3">
                      <div className="flex align-items-center gap-2">
                        <SecurityBadge type="ssl" size="sm" showText={false} />
                        <span className="text-900 font-semibold">Monthly Scans</span>
                      </div>
                      <span className="text-600 font-bold text-lg">
                        {usageMetrics?.scansUsed || 0} / {usageMetrics?.scansLimit || 0}
                      </span>
                    </div>
                    <ProgressBar 
                      value={usageMetrics ? (usageMetrics.scansUsed / usageMetrics.scansLimit) * 100 : 0} 
                      showValue={false}
                      style={{ 
                        height: '12px', 
                        background: 'var(--autodmca-surface-200)',
                        borderRadius: 'var(--border-radius-lg)'
                      }}
                      color="var(--autodmca-primary-500)"
                    />
                    <div className="flex justify-content-between mt-2">
                      <span className="text-xs text-600">Used</span>
                      <span className="text-xs text-600">Limit</span>
                    </div>
                  </div>
                </div>
                <div className="col-12 md:col-6">
                  <div className="mb-4">
                    <div className="flex justify-content-between align-items-center mb-3">
                      <div className="flex align-items-center gap-2">
                        <SecurityBadge type="verified" size="sm" showText={false} />
                        <span className="text-900 font-semibold">Success Rate</span>
                      </div>
                      <span className="text-600 font-bold text-lg">{usageMetrics?.successRate || 0}%</span>
                    </div>
                    <ProgressBar 
                      value={usageMetrics?.successRate || 0} 
                      showValue={false}
                      style={{ 
                        height: '12px',
                        background: 'var(--autodmca-surface-200)',
                        borderRadius: 'var(--border-radius-lg)'
                      }}
                      color="var(--autodmca-success-500)"
                    />
                    <div className="flex justify-content-between mt-2">
                      <span className="text-xs text-600">0%</span>
                      <span className="text-xs text-600">100%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-4 mt-4">
                <div className="flex align-items-center gap-3 p-3 border-round-lg" 
                     style={{ background: 'linear-gradient(135deg, var(--autodmca-primary-50), var(--autodmca-primary-100))' }}>
                  <div className="w-3rem h-3rem border-circle flex align-items-center justify-content-center"
                       style={{ background: 'var(--autodmca-primary-500)', color: 'white' }}>
                    <i className="pi pi-calendar text-lg" />
                  </div>
                  <div>
                    <div className="text-primary-900 font-semibold text-sm">This Month</div>
                    <div className="text-primary-700 text-xl font-bold">{usageMetrics?.scansUsed || 0}</div>
                  </div>
                </div>
                <div className="flex align-items-center gap-3 p-3 border-round-lg"
                     style={{ background: 'linear-gradient(135deg, var(--autodmca-success-50), var(--autodmca-success-100))' }}>
                  <div className="w-3rem h-3rem border-circle flex align-items-center justify-content-center"
                       style={{ background: 'var(--autodmca-success-500)', color: 'white' }}>
                    <i className="pi pi-check-circle text-lg" />
                  </div>
                  <div>
                    <div className="text-green-900 font-semibold text-sm">Success Rate</div>
                    <div className="text-green-700 text-xl font-bold">{usageMetrics?.monthlySuccessRate || 0}%</div>
                  </div>
                </div>
                {usageMetrics?.resetDate && (
                  <div className="flex align-items-center gap-3 p-3 border-round-lg"
                       style={{ background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))' }}>
                    <div className="w-3rem h-3rem border-circle flex align-items-center justify-content-center"
                         style={{ background: 'var(--autodmca-surface-400)', color: 'white' }}>
                      <i className="pi pi-refresh text-lg" />
                    </div>
                    <div>
                      <div className="text-600 font-semibold text-sm">Resets</div>
                      <div className="text-700 text-sm font-medium">
                        {new Date(usageMetrics.resetDate).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Quick Actions */}
      <div className="col-12 md:col-4">
        <EnhancedCard 
          title="Security Actions" 
          variant="elevated" 
          padding="lg" 
          elevation="2"
          className="h-full"
          headerActions={
            <SecurityShield level="premium" size="sm" animated={false} />
          }
        >
          <div className="flex flex-column gap-3">
            <EnhancedButton 
              variant="primary" 
              size="lg"
              icon="pi pi-plus"
              fullWidth
              elevation="1"
              onClick={() => navigate('/protection/submissions')}
            >
              Submit New Content
            </EnhancedButton>
            <EnhancedButton 
              variant="outline" 
              size="lg"
              icon="pi pi-shield"
              fullWidth
              onClick={() => navigate('/protection/profiles')}
            >
              Create Profile
            </EnhancedButton>
            <EnhancedButton 
              variant="outline" 
              size="lg"
              icon="pi pi-chart-line"
              fullWidth
              onClick={() => navigate('/reports')}
            >
              View Analytics
            </EnhancedButton>
            
            <Divider />
            
            <div className="text-center p-3 border-round-lg"
                 style={{ background: 'var(--autodmca-surface-50)' }}>
              <SecurityBadge type="encrypted" size="md" className="mb-2" />
              <div className="text-700 font-semibold text-sm mb-2">Professional Support</div>
              <EnhancedButton 
                variant="ghost" 
                size="sm"
                icon="pi pi-headphones"
                onClick={() => navigate('/support')}
              >
                Contact Support
              </EnhancedButton>
            </div>
          </div>
        </EnhancedCard>
      </div>

      {/* Enhanced Monthly Trends Chart */}
      <div className="col-12 lg:col-8">
        <EnhancedCard 
          variant="elevated" 
          padding="lg" 
          elevation="2" 
          className="h-full"
          headerActions={
            <div className="flex align-items-center gap-2">
              <SecurityBadge type="professional" size="sm" showText={false} />
              {lastUpdated.analytics && (
                <span className="text-sm text-600">
                  Updated {formatTimestamp(lastUpdated.analytics)}
                </span>
              )}
            </div>
          }
        >
          <div className="flex align-items-center gap-2 mb-4">
            <SecurityShield level="premium" size="sm" animated={false} />
            <h3 className="text-900 font-bold text-xl m-0">Security Trends</h3>
          </div>
          {renderErrorMessage('analytics', fetchAnalyticsData)}
          {loading.analytics ? (
            <EnhancedLoading type="skeleton" variant="dashboard" size="lg" />
          ) : (
            <div className="border-round-lg p-3"
                 style={{ 
                   height: '350px',
                   background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))',
                   border: '1px solid var(--autodmca-surface-200)'
                 }}>
              {monthlyTrendsData.labels.length > 0 ? (
                <Chart 
                  type="line" 
                  data={monthlyTrendsData} 
                  options={{
                    ...chartOptions,
                    plugins: {
                      ...chartOptions.plugins,
                      legend: {
                        position: 'top' as const,
                        labels: {
                          usePointStyle: true,
                          font: {
                            family: 'Inter',
                            size: 12,
                            weight: '500'
                          }
                        }
                      }
                    }
                  }}
                  height="350px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <SecurityShield level="basic" size="lg" animated={false} className="mb-3" />
                    <p className="text-600 font-medium">No trend data available for the selected period</p>
                    <p className="text-500 text-sm">Data will appear as your protection activities increase</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Platform Distribution */}
      <div className="col-12 lg:col-4">
        <EnhancedCard 
          variant="elevated" 
          padding="lg" 
          elevation="2" 
          className="h-full"
          headerActions={
            <div className="flex align-items-center gap-2">
              <SecurityBadge type="ssl" size="sm" showText={false} />
              {lastUpdated.platformData && (
                <span className="text-sm text-600">
                  Updated {formatTimestamp(lastUpdated.platformData)}
                </span>
              )}
            </div>
          }
        >
          <div className="flex align-items-center gap-2 mb-4">
            <SecurityBadge type="verified" size="sm" />
            <h3 className="text-900 font-bold text-xl m-0">Platform Coverage</h3>
          </div>
          {renderErrorMessage('platformData', fetchPlatformData)}
          {loading.platformData ? (
            <EnhancedLoading type="skeleton" variant="dashboard" size="lg" />
          ) : (
            <div className="border-round-lg p-3"
                 style={{ 
                   height: '350px',
                   background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))',
                   border: '1px solid var(--autodmca-surface-200)'
                 }}>
              {platformDistributionData.labels.length > 0 ? (
                <Chart 
                  type="doughnut" 
                  data={platformDistributionData} 
                  options={{
                    ...doughnutOptions,
                    plugins: {
                      ...doughnutOptions.plugins,
                      legend: {
                        position: 'right' as const,
                        labels: {
                          usePointStyle: true,
                          font: {
                            family: 'Inter',
                            size: 11,
                            weight: '500'
                          }
                        }
                      }
                    }
                  }}
                  height="350px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <SecurityShield level="enterprise" size="lg" animated={false} className="mb-3" />
                    <p className="text-600 font-medium">No platform data available</p>
                    <p className="text-500 text-sm">Start monitoring to see platform distribution</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Success Rate by Platform */}
      <div className="col-12 lg:col-6">
        <EnhancedCard 
          variant="elevated" 
          padding="lg" 
          elevation="2" 
          className="h-full"
          headerActions={
            <div className="flex align-items-center gap-2">
              <SecurityBadge type="verified" size="sm" showText={false} />
              {lastUpdated.analytics && (
                <span className="text-sm text-600">
                  Updated {formatTimestamp(lastUpdated.analytics)}
                </span>
              )}
            </div>
          }
        >
          <div className="flex align-items-center gap-2 mb-4">
            <SecurityBadge type="professional" size="sm" />
            <h3 className="text-900 font-bold text-xl m-0">Success Metrics</h3>
          </div>
          {renderErrorMessage('analytics', fetchAnalyticsData)}
          {loading.analytics ? (
            <EnhancedLoading type="skeleton" variant="dashboard" size="md" />
          ) : (
            <div className="border-round-lg p-3"
                 style={{ 
                   height: '300px',
                   background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))',
                   border: '1px solid var(--autodmca-surface-200)'
                 }}>
              {successRateData.labels.length > 0 ? (
                <Chart 
                  type="bar" 
                  data={successRateData} 
                  options={{
                    ...chartOptions,
                    plugins: {
                      ...chartOptions.plugins,
                      legend: {
                        position: 'top' as const,
                        labels: {
                          font: {
                            family: 'Inter',
                            size: 12,
                            weight: '500'
                          }
                        }
                      }
                    }
                  }}
                  height="300px"
                />
              ) : (
                <div className="flex align-items-center justify-content-center h-full">
                  <div className="text-center">
                    <SecurityShield level="premium" size="lg" animated={false} className="mb-3" />
                    <p className="text-600 font-medium">No success rate data available</p>
                    <p className="text-500 text-sm">Data will populate as takedowns are processed</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Platform Performance Table */}
      <div className="col-12 lg:col-6">
        <EnhancedCard 
          variant="elevated" 
          padding="lg" 
          elevation="2" 
          className="h-full"
          headerActions={
            <div className="flex align-items-center gap-2">
              <SecurityBadge type="dmca" size="sm" showText={false} />
              {lastUpdated.platformData && (
                <span className="text-sm text-600">
                  Updated {formatTimestamp(lastUpdated.platformData)}
                </span>
              )}
            </div>
          }
        >
          <div className="flex align-items-center gap-2 mb-4">
            <SecurityBadge type="ssl" size="sm" />
            <h3 className="text-900 font-bold text-xl m-0">Platform Status</h3>
          </div>
          {renderErrorMessage('platformData', fetchPlatformData)}
          {loading.platformData ? (
            <EnhancedLoading type="skeleton" variant="table" size="md" lines={5} />
          ) : (
            <div className="border-round-lg overflow-hidden"
                 style={{ 
                   background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))',
                   border: '1px solid var(--autodmca-surface-200)'
                 }}>
              <DataTable 
                value={safePlatformData} 
                size="small"
                showGridlines
                emptyMessage={
                  <div className="text-center p-4">
                    <SecurityShield level="enterprise" size="lg" animated={false} className="mb-3" />
                    <p className="text-600 font-medium">No platform data available</p>
                    <p className="text-500 text-sm">Begin monitoring to see platform performance</p>
                  </div>
                }
                className="border-none"
                style={{ background: 'transparent' }}
              >
                <Column 
                  field="platform" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="ssl" size="sm" showText={false} />
                      <span>Platform</span>
                    </div>
                  } 
                />
                <Column 
                  field="infringements" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="dmca" size="sm" showText={false} />
                      <span>Threats</span>
                    </div>
                  }
                  body={(rowData) => (
                    <Badge 
                      value={rowData.infringements} 
                      severity="warning"
                      style={{ background: 'var(--autodmca-warning-500)' }}
                    />
                  )}
                />
                <Column 
                  field="takedowns" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="professional" size="sm" showText={false} />
                      <span>Actions</span>
                    </div>
                  }
                  body={(rowData) => (
                    <Badge 
                      value={rowData.takedowns} 
                      severity="success"
                      style={{ background: 'var(--autodmca-success-500)' }}
                    />
                  )}
                />
                <Column 
                  field="successRate" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="verified" size="sm" showText={false} />
                      <span>Success Rate</span>
                    </div>
                  }
                  body={(rowData) => (
                    <div className="flex align-items-center gap-2">
                      <ProgressBar 
                        value={rowData.successRate} 
                        showValue={false} 
                        style={{ 
                          width: '60px', 
                          height: '8px',
                          background: 'var(--autodmca-surface-200)'
                        }}
                        color="var(--autodmca-success-500)"
                      />
                      <span className="text-sm font-medium">{rowData.successRate}%</span>
                      {rowData.trend && (
                        <i className={`pi ${
                          rowData.trend === 'up' ? 'pi-arrow-up' :
                          rowData.trend === 'down' ? 'pi-arrow-down' :
                          'pi-minus'
                        } text-sm`} 
                        style={{ 
                          color: rowData.trend === 'up' ? 'var(--autodmca-success-600)' :
                                 rowData.trend === 'down' ? 'var(--autodmca-danger-600)' :
                                 'var(--autodmca-surface-500)'
                        }} />
                      )}
                    </div>
                  )}
                />
              </DataTable>
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Enhanced Recent Activity */}
      <div className="col-12">
        <EnhancedCard 
          variant="elevated" 
          padding="lg" 
          elevation="2"
          className="mt-4"
          headerActions={
            <div className="flex gap-2 align-items-center">
              <SecurityBadge type="ssl" size="sm" showText={false} />
              <EnhancedButton 
                variant="ghost" 
                size="sm"
                icon="pi pi-refresh"
                loading={loading.activity}
                onClick={fetchRecentActivity}
              />
              <EnhancedButton 
                variant="outline" 
                size="sm"
                onClick={() => navigate('/protection/activity')}
              >
                View All
              </EnhancedButton>
            </div>
          }
        >
          <div className="flex align-items-center gap-3 mb-4">
            <SecurityShield level="premium" size="sm" animated={false} />
            <h3 className="text-900 font-bold text-xl m-0">Security Activity Feed</h3>
            {lastUpdated.activity && (
              <span className="text-sm text-600">
                Updated {formatTimestamp(lastUpdated.activity)}
              </span>
            )}
          </div>
          
          {renderErrorMessage('activity', fetchRecentActivity)}
          {loading.activity ? (
            <EnhancedLoading type="skeleton" variant="table" size="lg" lines={8} />
          ) : (
            <div className="border-round-lg overflow-hidden"
                 style={{ 
                   background: 'linear-gradient(135deg, var(--autodmca-surface-50), var(--autodmca-surface-100))',
                   border: '1px solid var(--autodmca-surface-200)'
                 }}>
              <DataTable 
                value={safeRecentActivity} 
                paginator 
                rows={10}
                size="small"
                showGridlines
                emptyMessage={
                  <div className="text-center p-5">
                    <SecurityShield level="basic" size="xl" animated={false} className="mb-4" />
                    <h4 className="text-900 font-bold mb-2">No Recent Activity</h4>
                    <p className="text-600 mb-3">Your security monitoring will appear here once activated</p>
                    <EnhancedButton 
                      variant="primary" 
                      size="md"
                      icon="pi pi-plus"
                      onClick={() => navigate('/protection/submissions')}
                    >
                      Start Monitoring
                    </EnhancedButton>
                  </div>
                }
                loading={loading.activity}
                className="border-none"
                style={{ background: 'transparent' }}
              >
                <Column 
                  field="type" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="dmca" size="sm" showText={false} />
                      <span>Activity Type</span>
                    </div>
                  }
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
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="ssl" size="sm" showText={false} />
                      <span>Platform</span>
                    </div>
                  }
                  body={platformTemplate}
                  style={{ width: '15%' }}
                />
                <Column 
                  field="status" 
                  header={
                    <div className="flex align-items-center gap-2">
                      <SecurityBadge type="verified" size="sm" showText={false} />
                      <span>Status</span>
                    </div>
                  }
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
            </div>
          )}
        </EnhancedCard>
      </div>

      {/* Professional Footer */}
      <div className="col-12 mt-5">
        <EnhancedCard 
          variant="filled" 
          padding="lg"
          style={{
            background: 'linear-gradient(135deg, var(--autodmca-surface-100), var(--autodmca-surface-200))',
            border: '1px solid var(--autodmca-surface-300)'
          }}
        >
          <div className="flex flex-column lg:flex-row justify-content-between align-items-center gap-4">
            <div className="flex align-items-center gap-3">
              <SecurityShield level="enterprise" size="md" animated={false} />
              <div>
                <h4 className="text-900 font-bold m-0">Enterprise-Grade Content Protection</h4>
                <p className="text-600 m-0 mt-1">
                  Powered by advanced AI and professional DMCA enforcement
                </p>
              </div>
            </div>
            
            <div className="flex flex-column lg:flex-row align-items-center gap-4">
              <TrustIndicatorBar 
                indicators={['ssl', 'encrypted', 'verified', 'professional', 'gdpr', 'dmca']} 
                size="md" 
                layout="horizontal"
              />
              <div className="flex gap-2">
                <EnhancedButton 
                  variant="outline" 
                  size="sm"
                  icon="pi pi-shield"
                  onClick={() => navigate('/security')}
                >
                  Security Center
                </EnhancedButton>
                <EnhancedButton 
                  variant="outline" 
                  size="sm"
                  icon="pi pi-book"
                  onClick={() => navigate('/docs')}
                >
                  Documentation
                </EnhancedButton>
              </div>
            </div>
          </div>
          
          <Divider className="my-4" />
          
          <div className="flex flex-column lg:flex-row justify-content-between align-items-center gap-3">
            <DataProtectionNotice compact />
            <div className="text-center">
              <p className="text-600 text-sm m-0">
                © 2024 AutoDMCA Professional. All rights reserved. | 
                <a href="/privacy" className="text-primary-600 ml-1 no-underline">Privacy Policy</a> | 
                <a href="/terms" className="text-primary-600 ml-1 no-underline">Terms of Service</a>
              </p>
            </div>
          </div>
        </EnhancedCard>
      </div>
    </div>
    </>
  );
};

export default Dashboard;