import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Chart } from 'primereact/chart';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Button } from 'primereact/button';
import { ProgressBar } from 'primereact/progressbar';
import { Panel } from 'primereact/panel';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Slider } from 'primereact/slider';
import { InputSwitch } from 'primereact/inputswitch';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Skeleton } from 'primereact/skeleton';
import { Toolbar } from 'primereact/toolbar';
import { SplitButton } from 'primereact/splitbutton';
import { Message } from 'primereact/message';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement,
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  Filler
} from 'chart.js';
import { useAuth } from '../contexts/AuthContext';
import { reportsApi } from '../services/api';
import { 
  ReportFilters, 
  OverviewMetrics, 
  PlatformMetrics, 
  ContentTypeMetrics, 
  GeographicDataPoint,
  PlatformCompliance,
  ROIMetrics,
  ResponseTimeData,
  ReportTemplate as ApiReportTemplate,
  TimeSeriesDataPoint,
  RealTimeMetrics,
  TrendAnalysis,
  PerformanceMetrics,
  DataQualityReport
} from '../types/api';
import './Reports.css';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Local component interfaces
interface LocalReportFilters {
  dateRange: Date[];
  platforms: string[];
  contentTypes: string[];
  reportType: string;
  timeGranularity: string;
}

interface LocalAnalyticsData {
  overview?: OverviewMetrics;
  platformBreakdown: PlatformMetrics[];
  contentAnalytics: ContentTypeMetrics[];
  geographicData: GeographicDataPoint[];
  complianceMetrics: PlatformCompliance[];
  roiAnalysis?: ROIMetrics;
  responseTimeAnalysis: ResponseTimeData[];
  trendAnalysis?: TrendAnalysis[];
  performanceMetrics?: PerformanceMetrics;
  dataQuality?: DataQualityReport;
}

interface LoadingState {
  overview: boolean;
  platforms: boolean;
  content: boolean;
  compliance: boolean;
  roi: boolean;
  trends: boolean;
  charts: boolean;
}

interface ErrorState {
  overview?: string;
  platforms?: string;
  content?: string;
  compliance?: string;
  roi?: string;
  trends?: string;
  charts?: string;
  general?: string;
}

interface ReportGenerationProgress {
  id: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  progress: number;
  message: string;
}

const Reports: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [realTimeMode, setRealTimeMode] = useState(false);
  const [realTimeSubscriptionId, setRealTimeSubscriptionId] = useState<string | null>(null);
  
  // Loading and Error States
  const [loading, setLoading] = useState<LoadingState>({
    overview: true,
    platforms: true,
    content: true,
    compliance: true,
    roi: true,
    trends: true,
    charts: true
  });
  const [errors, setErrors] = useState<ErrorState>({});
  const [reportProgress, setReportProgress] = useState<ReportGenerationProgress | null>(null);
  
  // Filters and Settings
  const [filters, setFilters] = useState<LocalReportFilters>({
    dateRange: [
      new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
      new Date()
    ],
    platforms: ['Instagram', 'TikTok', 'OnlyFans', 'Twitter', 'YouTube'],
    contentTypes: ['Images', 'Videos', 'Audio', 'Text'],
    reportType: 'comprehensive',
    timeGranularity: 'daily'
  });

  // Analytics data from API
  const [analyticsData, setAnalyticsData] = useState<LocalAnalyticsData>({
    platformBreakdown: [],
    contentAnalytics: [],
    geographicData: [],
    complianceMetrics: [],
    responseTimeAnalysis: []
  });
  
  const [reportTemplates, setReportTemplates] = useState<ApiReportTemplate[]>([]);
  const [realTimeData, setRealTimeData] = useState<RealTimeMetrics | null>(null);
  const [lastDataUpdate, setLastDataUpdate] = useState<string>('');

  // Platform and filter options
  const platformOptions = [
    { label: 'Instagram', value: 'Instagram' },
    { label: 'TikTok', value: 'TikTok' },
    { label: 'OnlyFans', value: 'OnlyFans' },
    { label: 'Twitter', value: 'Twitter' },
    { label: 'YouTube', value: 'YouTube' },
    { label: 'Reddit', value: 'Reddit' },
    { label: 'Facebook', value: 'Facebook' }
  ];

  const contentTypeOptions = [
    { label: 'Images', value: 'Images' },
    { label: 'Videos', value: 'Videos' },
    { label: 'Audio', value: 'Audio' },
    { label: 'Text', value: 'Text' }
  ];

  const reportTypeOptions = [
    { label: 'Comprehensive Report', value: 'comprehensive' },
    { label: 'Executive Summary', value: 'executive' },
    { label: 'Platform Analysis', value: 'platform' },
    { label: 'ROI Analysis', value: 'roi' },
    { label: 'Compliance Report', value: 'compliance' }
  ];

  const timeGranularityOptions = [
    { label: 'Hourly', value: 'hourly' },
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' }
  ];

  const exportOptions = [
    { label: 'Export as PDF', icon: 'pi pi-file-pdf', command: () => handleExport('pdf') },
    { label: 'Export as CSV', icon: 'pi pi-file-excel', command: () => handleExport('csv') },
    { label: 'Export as Excel', icon: 'pi pi-file', command: () => handleExport('excel') }
  ];

  // Data loading functions
  const convertFiltersToApiFormat = useCallback((localFilters: LocalReportFilters) => {
    const [startDate, endDate] = localFilters.dateRange;
    return {
      dateRange: {
        start: startDate.toISOString().split('T')[0],
        end: endDate.toISOString().split('T')[0]
      },
      platforms: localFilters.platforms,
      contentTypes: localFilters.contentTypes,
      timeGranularity: localFilters.timeGranularity as 'hourly' | 'daily' | 'weekly' | 'monthly'
    };
  }, []);

  // Load overview metrics
  const loadOverviewData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, overview: true }));
      setErrors(prev => ({ ...prev, overview: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getOverviewMetrics(apiFilters);
      
      setAnalyticsData(prev => ({
        ...prev,
        overview: response.data
      }));
      
      setLastDataUpdate(new Date().toISOString());
    } catch (error: any) {
      setErrors(prev => ({ ...prev, overview: error.message || 'Failed to load overview data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Data Load Error',
        detail: 'Failed to load overview metrics',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, overview: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load platform analytics
  const loadPlatformData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, platforms: true }));
      setErrors(prev => ({ ...prev, platforms: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getPlatformAnalytics({
        ...apiFilters,
        includeCompliance: true
      });
      
      setAnalyticsData(prev => ({
        ...prev,
        platformBreakdown: response.data.platforms || [],
        complianceMetrics: response.data.compliance || []
      }));
    } catch (error: any) {
      setErrors(prev => ({ ...prev, platforms: error.message || 'Failed to load platform data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Data Load Error',
        detail: 'Failed to load platform analytics',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, platforms: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load content analytics
  const loadContentData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, content: true }));
      setErrors(prev => ({ ...prev, content: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getContentAnalytics({
        ...apiFilters,
        includeGeo: true
      });
      
      setAnalyticsData(prev => ({
        ...prev,
        contentAnalytics: response.data.contentTypes || [],
        geographicData: response.data.geographic || []
      }));
    } catch (error: any) {
      setErrors(prev => ({ ...prev, content: error.message || 'Failed to load content data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Data Load Error',
        detail: 'Failed to load content analytics',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, content: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load ROI analysis
  const loadROIData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, roi: true }));
      setErrors(prev => ({ ...prev, roi: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getROIAnalysis({
        ...apiFilters,
        includeProjections: true
      });
      
      setAnalyticsData(prev => ({
        ...prev,
        roiAnalysis: response.data
      }));
    } catch (error: any) {
      setErrors(prev => ({ ...prev, roi: error.message || 'Failed to load ROI data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Data Load Error',
        detail: 'Failed to load ROI analysis',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, roi: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load compliance metrics
  const loadComplianceData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, compliance: true }));
      setErrors(prev => ({ ...prev, compliance: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getComplianceMetrics({
        ...apiFilters,
        includeResponseTimes: true
      });
      
      setAnalyticsData(prev => ({
        ...prev,
        complianceMetrics: response.data.compliance || [],
        responseTimeAnalysis: response.data.responseTimes || []
      }));
    } catch (error: any) {
      setErrors(prev => ({ ...prev, compliance: error.message || 'Failed to load compliance data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Data Load Error',
        detail: 'Failed to load compliance metrics',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, compliance: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load trend analysis
  const loadTrendData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, trends: true }));
      setErrors(prev => ({ ...prev, trends: undefined }));
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.getTrendAnalysis({
        ...apiFilters,
        trendType: 'growth'
      });
      
      setAnalyticsData(prev => ({
        ...prev,
        trendAnalysis: response.data
      }));
    } catch (error: any) {
      setErrors(prev => ({ ...prev, trends: error.message || 'Failed to load trend data' }));
    } finally {
      setLoading(prev => ({ ...prev, trends: false }));
    }
  }, [filters, convertFiltersToApiFormat]);

  // Load report templates
  const loadReportTemplates = useCallback(async () => {
    try {
      const response = await reportsApi.getReportTemplates();
      setReportTemplates(response.data);
    } catch (error: any) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Templates Load Error',
        detail: 'Failed to load report templates',
        life: 3000
      });
    }
  }, []);

  // Load all data
  const loadAllData = useCallback(async () => {
    await Promise.all([
      loadOverviewData(),
      loadPlatformData(),
      loadContentData(),
      loadROIData(),
      loadComplianceData(),
      loadTrendData()
    ]);
    
    // Set charts loading to false after all data is loaded
    setLoading(prev => ({ ...prev, charts: false }));
  }, [loadOverviewData, loadPlatformData, loadContentData, loadROIData, loadComplianceData, loadTrendData]);

  // Initial data load
  useEffect(() => {
    loadAllData();
    loadReportTemplates();
  }, [loadAllData, loadReportTemplates]);

  // Reload data when filters change
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      loadAllData();
    }, 500); // Debounce filter changes
    
    return () => clearTimeout(debounceTimer);
  }, [filters, loadAllData]);

  // Real-time data functionality
  const loadRealTimeData = useCallback(async () => {
    try {
      const response = await reportsApi.getRealTimeMetrics();
      setRealTimeData(response.data);
      setLastDataUpdate(new Date().toISOString());
    } catch (error: any) {
      console.error('Failed to load real-time data:', error);
    }
  }, []);

  // Subscribe to real-time updates
  const subscribeToRealTime = useCallback(async () => {
    try {
      const response = await reportsApi.subscribeToRealTimeUpdates({
        metrics: ['infringements', 'takedowns', 'success_rate'],
        platforms: filters.platforms,
        updateFrequency: 'medium'
      });
      setRealTimeSubscriptionId(response.data.subscriptionId);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Real-time Updates',
        detail: 'Successfully enabled real-time data updates',
        life: 3000
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Real-time Error',
        detail: 'Failed to enable real-time updates',
        life: 3000
      });
    }
  }, [filters.platforms]);

  // Unsubscribe from real-time updates
  const unsubscribeFromRealTime = useCallback(async () => {
    if (!realTimeSubscriptionId) return;
    
    try {
      await reportsApi.unsubscribeFromRealTimeUpdates(realTimeSubscriptionId);
      setRealTimeSubscriptionId(null);
      setRealTimeData(null);
      
      toast.current?.show({
        severity: 'info',
        summary: 'Real-time Updates',
        detail: 'Real-time data updates disabled',
        life: 3000
      });
    } catch (error: any) {
      console.error('Failed to unsubscribe from real-time updates:', error);
    }
  }, [realTimeSubscriptionId]);

  // Auto-refresh for real-time mode
  useEffect(() => {
    if (!realTimeMode) {
      unsubscribeFromRealTime();
      return;
    }
    
    subscribeToRealTime();
    loadRealTimeData();
    
    const interval = setInterval(() => {
      loadRealTimeData();
    }, 30000); // Refresh every 30 seconds

    return () => {
      clearInterval(interval);
      unsubscribeFromRealTime();
    };
  }, [realTimeMode, subscribeToRealTime, unsubscribeFromRealTime, loadRealTimeData]);

  // Chart data generators
  const trendsChartData = useMemo(() => ({
    labels: analyticsData.timeSeriesData.map(d => new Date(d.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Infringements Detected',
        data: analyticsData.timeSeriesData.map(d => d.infringements),
        borderColor: '#FF6B6B',
        backgroundColor: 'rgba(255, 107, 107, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Successful Takedowns',
        data: analyticsData.timeSeriesData.map(d => d.takedowns),
        borderColor: '#4ECDC4',
        backgroundColor: 'rgba(78, 205, 196, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Success Rate (%)',
        data: analyticsData.timeSeriesData.map(d => d.successRate),
        borderColor: '#45B7D1',
        backgroundColor: 'rgba(69, 183, 209, 0.1)',
        tension: 0.4,
        fill: false,
        yAxisID: 'y1'
      }
    ]
  }), [analyticsData.timeSeriesData]);

  const platformDistributionData = useMemo(() => ({
    labels: analyticsData.platformBreakdown.map(p => p.platform),
    datasets: [{
      data: analyticsData.platformBreakdown.map(p => p.infringements),
      backgroundColor: [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8'
      ],
      hoverBackgroundColor: [
        '#FF5252', '#26C6DA', '#42A5F5', '#66BB6A', '#FFCA28', '#BA68C8', '#4DB6AC'
      ]
    }]
  }), [analyticsData.platformBreakdown]);

  const successRateComparisonData = useMemo(() => ({
    labels: analyticsData.platformBreakdown.map(p => p.platform),
    datasets: [{
      label: 'Success Rate (%)',
      data: analyticsData.platformBreakdown.map(p => p.successRate),
      backgroundColor: 'rgba(78, 205, 196, 0.8)',
      borderColor: '#4ECDC4',
      borderWidth: 1
    }]
  }), [analyticsData.platformBreakdown]);

  const roiComparisonData = useMemo(() => ({
    labels: analyticsData.platformBreakdown.map(p => p.platform),
    datasets: [{
      label: 'ROI (%)',
      data: analyticsData.platformBreakdown.map(p => p.roi),
      backgroundColor: 'rgba(255, 202, 40, 0.8)',
      borderColor: '#FFCA28',
      borderWidth: 1
    }]
  }), [analyticsData.platformBreakdown]);

  const responseTimeChartData = useMemo(() => ({
    labels: analyticsData.responseTimeAnalysis.map(r => r.platform),
    datasets: [{
      label: 'Average Response Time (Hours)',
      data: analyticsData.responseTimeAnalysis.map(r => r.avgHours),
      backgroundColor: analyticsData.responseTimeAnalysis.map(r => 
        r.category === 'fast' ? 'rgba(76, 175, 80, 0.8)' :
        r.category === 'medium' ? 'rgba(255, 193, 7, 0.8)' :
        'rgba(244, 67, 54, 0.8)'
      ),
      borderColor: analyticsData.responseTimeAnalysis.map(r => 
        r.category === 'fast' ? '#4CAF50' :
        r.category === 'medium' ? '#FFC107' :
        '#F44336'
      ),
      borderWidth: 1
    }]
  }), [analyticsData.responseTimeAnalysis]);

  const contentTypeData = useMemo(() => ({
    labels: analyticsData.contentAnalytics.map(c => c.type),
    datasets: [{
      data: analyticsData.contentAnalytics.map(c => c.percentage),
      backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'],
      hoverBackgroundColor: ['#FF5252', '#26C6DA', '#42A5F5', '#66BB6A']
    }]
  }), [analyticsData.contentAnalytics]);

  const geoDistributionData = useMemo(() => ({
    labels: analyticsData.geographicData.map(g => g.country),
    datasets: [{
      label: 'Infringements',
      data: analyticsData.geographicData.map(g => g.infringements),
      backgroundColor: 'rgba(69, 183, 209, 0.8)',
      borderColor: '#45B7D1',
      borderWidth: 1
    }]
  }), [analyticsData.geographicData]);

  // Chart options
  const multiAxisOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      title: {
        display: true,
        text: 'Trends Over Time'
      },
      legend: {
        position: 'top' as const,
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date'
        }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Count'
        }
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Percentage (%)'
        },
        grid: {
          drawOnChartArea: false,
        },
      }
    }
  };

  const standardChartOptions = {
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

  // Event handlers
  const handleFilterChange = (key: keyof LocalReportFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
    
    // Show loading state immediately for better UX
    setLoading({
      overview: true,
      platforms: true,
      content: true,
      compliance: true,
      roi: true,
      trends: true,
      charts: true
    });
  };

  const handleExport = async (format: 'pdf' | 'csv' | 'excel') => {
    try {
      setReportProgress({
        id: `export-${Date.now()}`,
        status: 'generating',
        progress: 0,
        message: 'Preparing export...'
      });
      
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.exportReport({
        format,
        reportType: filters.reportType as any,
        dateRange: apiFilters.dateRange,
        platforms: apiFilters.platforms,
        sections: ['overview', 'platforms', 'content', 'compliance']
      });
      
      setReportProgress({
        id: response.data.reportId,
        status: 'completed',
        progress: 100,
        message: 'Export completed successfully'
      });
      
      // Download the file
      if (response.data.downloadUrl) {
        window.open(response.data.downloadUrl, '_blank');
      }
      
      toast.current?.show({
        severity: 'success',
        summary: 'Export Successful',
        detail: `Report exported as ${format.toUpperCase()}`,
        life: 5000
      });
      
      setShowExportDialog(false);
    } catch (error: any) {
      setReportProgress({
        id: 'export-failed',
        status: 'failed',
        progress: 0,
        message: error.message || 'Export failed'
      });
      
      toast.current?.show({
        severity: 'error',
        summary: 'Export Failed',
        detail: error.message || 'Failed to export report',
        life: 5000
      });
    }
  };

  const handleTemplateApply = (template: ApiReportTemplate) => {
    // Convert API template filters to local format
    const newFilters: LocalReportFilters = {
      ...filters,
      reportType: template.filters.reportType || filters.reportType,
      timeGranularity: template.filters.timeGranularity || filters.timeGranularity,
      platforms: template.filters.platforms || filters.platforms,
      contentTypes: template.filters.contentTypes || filters.contentTypes
    };
    
    if (template.filters.dateRange) {
      newFilters.dateRange = [
        new Date(template.filters.dateRange.start),
        new Date(template.filters.dateRange.end)
      ];
    }
    
    setFilters(newFilters);
    setShowTemplateDialog(false);
    
    toast.current?.show({
      severity: 'success',
      summary: 'Template Applied',
      detail: `Applied template: ${template.name}`,
      life: 3000
    });
  };

  const handleScheduleReport = async () => {
    try {
      const apiFilters = convertFiltersToApiFormat(filters);
      const response = await reportsApi.scheduleReport({
        reportType: filters.reportType as any,
        schedule: {
          frequency: 'weekly',
          dayOfWeek: 1, // Monday
          time: '09:00'
        },
        recipients: [user?.email].filter(Boolean),
        dateRange: 'last_week',
        platforms: apiFilters.platforms,
        sections: ['overview', 'platforms', 'compliance'],
        format: 'pdf',
        active: true
      });
      
      toast.current?.show({
        severity: 'success',
        summary: 'Report Scheduled',
        detail: 'Weekly report has been scheduled successfully',
        life: 5000
      });
    } catch (error: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Scheduling Failed',
        detail: error.message || 'Failed to schedule report',
        life: 5000
      });
    }
  };

  // Template functions with error handling
  const renderKPICard = (title: string, value: string | number, subtitle?: string, icon?: string, color?: string, isLoading?: boolean, error?: string) => (
    <Card className="h-full kpi-card">
      <div className="flex justify-content-between align-items-start">
        <div className="flex-1">
          <div className="text-500 font-medium text-sm">{title}</div>
          {isLoading ? (
            <Skeleton width="4rem" height="1.5rem" className="mt-1" />
          ) : error ? (
            <div className="text-red-500 text-sm mt-1">{error}</div>
          ) : (
            <div className="text-900 font-bold text-xl mt-1">{value}</div>
          )}
          {subtitle && !isLoading && !error && (
            <div className="text-600 text-sm mt-1">{subtitle}</div>
          )}
        </div>
        {icon && (
          <div className={`kpi-icon ${color || 'bg-blue-100 text-blue-800'}`}>
            <i className={`${icon} text-xl`} />
          </div>
        )}
      </div>
    </Card>
  );

  const renderPlatformTable = () => {
    if (loading.platforms) {
      return (
        <div className="grid">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="col-12">
              <Skeleton width="100%" height="3rem" className="mb-2" />
            </div>
          ))}
        </div>
      );
    }
    
    if (errors.platforms) {
      return (
        <Message 
          severity="error" 
          text={errors.platforms} 
          className="w-full"
        />
      );
    }
    
    return (
      <DataTable 
        value={analyticsData.platformBreakdown}
        size="small"
        showGridlines
        sortMode="multiple"
        paginator
        rows={10}
        emptyMessage="No platform data available"
      >
        <Column field="platform" header="Platform" sortable />
        <Column 
          field="infringements" 
          header="Infringements" 
          sortable
          body={(rowData) => (
            <Badge value={rowData.infringements} severity="warning" />
          )}
        />
        <Column 
          field="takedowns" 
          header="Takedowns" 
          sortable
          body={(rowData) => (
            <Badge value={rowData.takedowns} severity="success" />
          )}
        />
        <Column 
          field="successRate" 
          header="Success Rate" 
          sortable
          body={(rowData) => (
            <div className="flex align-items-center gap-2">
              <ProgressBar 
                value={rowData.successRate} 
                showValue={false} 
                style={{ width: '60px', height: '6px' }}
              />
              <span className="text-sm font-medium">{rowData.successRate.toFixed(1)}%</span>
            </div>
          )}
        />
        <Column 
          field="avgResponseTime" 
          header="Avg Response Time" 
          sortable
          body={(rowData) => (
            <span>{rowData.avgResponseTime.toFixed(1)}h</span>
          )}
        />
        <Column 
          field="roi" 
          header="ROI" 
          sortable
          body={(rowData) => (
            <Tag 
              value={`${rowData.roi.toFixed(1)}%`} 
              severity={rowData.roi > 300 ? 'success' : rowData.roi > 200 ? 'warning' : 'danger'}
            />
          )}
        />
        <Column 
          field="complianceRating" 
          header="Compliance" 
          sortable
          body={(rowData) => (
            <div className="flex align-items-center gap-2">
              <ProgressBar 
                value={rowData.complianceRating * 10} 
                showValue={false} 
                style={{ width: '60px', height: '6px' }}
                color={rowData.complianceRating >= 8 ? '#10B981' : rowData.complianceRating >= 6 ? '#F59E0B' : '#EF4444'}
              />
              <span className="text-sm font-medium">{rowData.complianceRating.toFixed(1)}/10</span>
            </div>
          )}
        />
      </DataTable>
    );
  };

  // Show global loading state only if all sections are loading
  const isGlobalLoading = Object.values(loading).every(Boolean);
  
  if (isGlobalLoading) {
    return (
      <div className="analytics-reports-page">
        <div className="grid">
          <div className="col-12">
            <Skeleton width="100%" height="4rem" className="mb-4" />
          </div>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="col-12 md:col-6 lg:col-3">
              <Skeleton width="100%" height="8rem" />
            </div>
          ))}
          <div className="col-12">
            <Skeleton width="100%" height="30rem" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-reports-page">
      <Toast ref={toast} />
      
      {/* Header with filters and actions */}
      <div className="grid">
        <div className="col-12">
          <div className="flex flex-column lg:flex-row lg:justify-content-between lg:align-items-start gap-4 mb-4">
            <div>
              <h2 className="m-0 text-900">Analytics & Reports</h2>
              <p className="text-600 m-0 mt-1">Comprehensive insights into your content protection performance</p>
            </div>
            
            <div className="flex flex-wrap gap-2 align-items-center">
              <div className="flex align-items-center gap-2">
                <span className="text-sm">Real-time</span>
                <InputSwitch 
                  checked={realTimeMode} 
                  onChange={(e) => setRealTimeMode(e.value)} 
                  tooltip={realTimeMode ? 'Disable real-time updates' : 'Enable real-time updates'}
                />
                {realTimeData && (
                  <Tag 
                    value="Live" 
                    severity="success" 
                    className="animate-pulse" 
                  />
                )}
              </div>
              
              <Button 
                label="Templates" 
                icon="pi pi-bookmark" 
                outlined 
                size="small"
                onClick={() => setShowTemplateDialog(true)}
              />
              
              <SplitButton 
                label="Export Report" 
                icon="pi pi-download" 
                model={exportOptions}
                size="small"
              />
              
              <Button 
                label="Schedule Report" 
                icon="pi pi-calendar" 
                size="small"
                onClick={handleScheduleReport}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      <Panel header="Report Filters" toggleable className="mb-4">
        <div className="grid">
          <div className="col-12 md:col-6 lg:col-3">
            <label className="block text-sm font-medium mb-2">Date Range</label>
            <Calendar
              value={filters.dateRange}
              onChange={(e) => handleFilterChange('dateRange', e.value)}
              selectionMode="range"
              readOnlyInput
              showIcon
              dateFormat="mm/dd/yy"
              className="w-full"
            />
          </div>
          
          <div className="col-12 md:col-6 lg:col-3">
            <label className="block text-sm font-medium mb-2">Platforms</label>
            <MultiSelect
              value={filters.platforms}
              options={platformOptions}
              onChange={(e) => handleFilterChange('platforms', e.value)}
              placeholder="Select platforms"
              maxSelectedLabels={2}
              className="w-full"
            />
          </div>
          
          <div className="col-12 md:col-6 lg:col-3">
            <label className="block text-sm font-medium mb-2">Report Type</label>
            <Dropdown
              value={filters.reportType}
              options={reportTypeOptions}
              onChange={(e) => handleFilterChange('reportType', e.value)}
              className="w-full"
            />
          </div>
          
          <div className="col-12 md:col-6 lg:col-3">
            <label className="block text-sm font-medium mb-2">Time Granularity</label>
            <Dropdown
              value={filters.timeGranularity}
              options={timeGranularityOptions}
              onChange={(e) => handleFilterChange('timeGranularity', e.value)}
              className="w-full"
            />
          </div>
        </div>
      </Panel>

      {/* Main Analytics Tabs */}
      <TabView activeIndex={activeTabIndex} onTabChange={(e) => setActiveTabIndex(e.index)}>
        
        {/* Overview Tab */}
        <TabPanel header="Overview" leftIcon="pi pi-chart-line">
          <div className="grid">
            {/* KPI Cards */}
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Total Infringements',
                analyticsData.overview?.totalInfringements?.toLocaleString() || '0',
                'Detected this period',
                'pi pi-exclamation-triangle',
                'bg-orange-100 text-orange-800',
                loading.overview,
                errors.overview
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Successful Takedowns',
                analyticsData.overview?.totalTakedowns?.toLocaleString() || '0',
                'Content removed',
                'pi pi-check-circle',
                'bg-green-100 text-green-800',
                loading.overview,
                errors.overview
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Success Rate',
                analyticsData.overview?.successRate ? `${analyticsData.overview.successRate.toFixed(1)}%` : '0%',
                'Overall effectiveness',
                'pi pi-chart-pie',
                'bg-blue-100 text-blue-800',
                loading.overview,
                errors.overview
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Avg Response Time',
                analyticsData.overview?.avgResponseTime ? `${analyticsData.overview.avgResponseTime.toFixed(1)}h` : '0h',
                'Platform response',
                'pi pi-clock',
                'bg-purple-100 text-purple-800',
                loading.overview,
                errors.overview
              )}
            </div>

            {/* ROI Overview */}
            <div className="col-12 lg:col-8">
              <Card title="Return on Investment Analysis" className="h-full">
                {loading.roi ? (
                  <div className="grid">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="col-12 md:col-6">
                        <Skeleton width="100%" height="4rem" className="mb-2" />
                      </div>
                    ))}
                  </div>
                ) : errors.roi ? (
                  <Message severity="error" text={errors.roi} className="w-full" />
                ) : analyticsData.roiAnalysis ? (
                  <>
                    <div className="grid">
                      <div className="col-12 md:col-6">
                        <div className="text-center p-3 border-round bg-blue-50">
                          <div className="text-blue-900 text-lg font-bold">${analyticsData.roiAnalysis.totalInvestment.toLocaleString()}</div>
                          <div className="text-blue-600 text-sm font-medium">Total Investment</div>
                        </div>
                      </div>
                      <div className="col-12 md:col-6">
                        <div className="text-center p-3 border-round bg-green-50">
                          <div className="text-green-900 text-lg font-bold">${analyticsData.roiAnalysis.contentValueProtected.toLocaleString()}</div>
                          <div className="text-green-600 text-sm font-medium">Content Value Protected</div>
                        </div>
                      </div>
                      <div className="col-12 md:col-6">
                        <div className="text-center p-3 border-round bg-orange-50">
                          <div className="text-orange-900 text-lg font-bold">${analyticsData.roiAnalysis.estimatedLossPrevented.toLocaleString()}</div>
                          <div className="text-orange-600 text-sm font-medium">Loss Prevented</div>
                        </div>
                      </div>
                      <div className="col-12 md:col-6">
                        <div className="text-center p-3 border-round bg-purple-50">
                          <div className="text-purple-900 text-lg font-bold">{analyticsData.roiAnalysis.roi.toFixed(1)}%</div>
                          <div className="text-purple-600 text-sm font-medium">ROI</div>
                        </div>
                      </div>
                    </div>
                    <Divider />
                    <div className="flex justify-content-between align-items-center">
                      <span className="font-medium">Cost per Takedown:</span>
                      <Tag value={`$${analyticsData.roiAnalysis.costPerTakedown.toFixed(2)}`} severity="info" />
                    </div>
                  </>
                ) : (
                  <Message severity="info" text="No ROI data available for the selected period" className="w-full" />
                )}
              </Card>
            </div>

            {/* Quick Stats */}
            <div className="col-12 lg:col-4">
              <Card title="Quick Stats" className="h-full">
                <div className="flex flex-column gap-3">
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Platform Coverage</span>
                    <Badge value={`${filters.platforms.length} platforms`} />
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Content Types</span>
                    <Badge value={`${analyticsData.contentAnalytics.length || 0} types`} />
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Geographic Reach</span>
                    <Badge value={`${analyticsData.geographicData.length || 0} countries`} />
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Data Freshness</span>
                    <Tag 
                      value={realTimeMode && realTimeData ? "Live data" : lastDataUpdate ? `Updated ${new Date(lastDataUpdate).toLocaleTimeString()}` : "No data"} 
                      severity={realTimeMode && realTimeData ? "success" : "info"} 
                    />
                  </div>
                  {reportProgress && (
                    <div className="flex flex-column gap-2">
                      <div className="flex justify-content-between align-items-center">
                        <span className="text-sm">Report Generation</span>
                        <Tag 
                          value={reportProgress.status} 
                          severity={reportProgress.status === 'completed' ? 'success' : reportProgress.status === 'failed' ? 'danger' : 'info'}
                        />
                      </div>
                      {reportProgress.status === 'generating' && (
                        <ProgressBar value={reportProgress.progress} showValue />
                      )}
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Trends Chart */}
            <div className="col-12">
              <Card title="Performance Trends" className="h-full">
                {loading.charts || loading.overview ? (
                  <Skeleton width="100%" height="400px" />
                ) : errors.overview ? (
                  <Message severity="error" text={errors.overview} className="w-full" />
                ) : (
                  <div className="chart-container" style={{ height: '400px' }}>
                    <Chart
                      type="line"
                      data={trendsChartData}
                      options={multiAxisOptions}
                    />
                  </div>
                )}
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Platform Analysis Tab */}
        <TabPanel header="Platform Analysis" leftIcon="pi pi-sitemap">
          <div className="grid">
            {/* Platform Performance Table */}
            <div className="col-12">
              <Card title="Platform Performance Breakdown">
                {renderPlatformTable()}
              </Card>
            </div>

            {/* Platform Distribution */}
            <div className="col-12 lg:col-6">
              <Card title="Infringement Distribution" className="h-full">
                {loading.platforms ? (
                  <Skeleton width="100%" height="350px" />
                ) : errors.platforms ? (
                  <Message severity="error" text={errors.platforms} className="w-full" />
                ) : analyticsData.platformBreakdown.length > 0 ? (
                  <div className="chart-container" style={{ height: '350px' }}>
                    <Chart
                      type="doughnut"
                      data={platformDistributionData}
                      options={doughnutOptions}
                    />
                  </div>
                ) : (
                  <Message severity="info" text="No platform data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* Success Rate Comparison */}
            <div className="col-12 lg:col-6">
              <Card title="Success Rate by Platform" className="h-full">
                {loading.platforms ? (
                  <Skeleton width="100%" height="350px" />
                ) : errors.platforms ? (
                  <Message severity="error" text={errors.platforms} className="w-full" />
                ) : analyticsData.platformBreakdown.length > 0 ? (
                  <div className="chart-container" style={{ height: '350px' }}>
                    <Chart
                      type="bar"
                      data={successRateComparisonData}
                      options={standardChartOptions}
                    />
                  </div>
                ) : (
                  <Message severity="info" text="No platform data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* Response Time Analysis */}
            <div className="col-12 lg:col-6">
              <Card title="Response Time Analysis" className="h-full">
                {loading.compliance ? (
                  <Skeleton width="100%" height="350px" />
                ) : errors.compliance ? (
                  <Message severity="error" text={errors.compliance} className="w-full" />
                ) : analyticsData.responseTimeAnalysis.length > 0 ? (
                  <div className="chart-container" style={{ height: '350px' }}>
                    <Chart
                      type="bar"
                      data={responseTimeChartData}
                      options={standardChartOptions}
                    />
                  </div>
                ) : (
                  <Message severity="info" text="No response time data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* ROI by Platform */}
            <div className="col-12 lg:col-6">
              <Card title="ROI by Platform" className="h-full">
                <div className="chart-container" style={{ height: '350px' }}>
                  <Chart
                    type="bar"
                    data={roiComparisonData}
                    options={standardChartOptions}
                  />
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Content Analysis Tab */}
        <TabPanel header="Content Analysis" leftIcon="pi pi-images">
          <div className="grid">
            {/* Content Type Distribution */}
            <div className="col-12 lg:col-6">
              <Card title="Content Type Distribution" className="h-full">
                {loading.content ? (
                  <Skeleton width="100%" height="350px" />
                ) : errors.content ? (
                  <Message severity="error" text={errors.content} className="w-full" />
                ) : analyticsData.contentAnalytics.length > 0 ? (
                  <div className="chart-container" style={{ height: '350px' }}>
                    <Chart
                      type="pie"
                      data={contentTypeData}
                      options={doughnutOptions}
                    />
                  </div>
                ) : (
                  <Message severity="info" text="No content type data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* Content Type Performance */}
            <div className="col-12 lg:col-6">
              <Card title="Content Type Performance" className="h-full">
                {loading.content ? (
                  <div className="grid">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="col-12">
                        <Skeleton width="100%" height="3rem" className="mb-2" />
                      </div>
                    ))}
                  </div>
                ) : errors.content ? (
                  <Message severity="error" text={errors.content} className="w-full" />
                ) : analyticsData.contentAnalytics.length > 0 ? (
                  <DataTable value={analyticsData.contentAnalytics} size="small" emptyMessage="No content data available">
                    <Column field="type" header="Content Type" />
                    <Column 
                      field="count" 
                      header="Count"
                      body={(rowData) => <Badge value={rowData.count} />}
                    />
                    <Column 
                      field="percentage" 
                      header="Percentage"
                      body={(rowData) => `${rowData.percentage.toFixed(1)}%`}
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
                          <span className="text-sm">{rowData.successRate.toFixed(1)}%</span>
                        </div>
                      )}
                    />
                  </DataTable>
                ) : (
                  <Message severity="info" text="No content type data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* Geographic Distribution */}
            <div className="col-12">
              <Card title="Geographic Distribution of Infringements">
                <div className="grid">
                  <div className="col-12 lg:col-8">
                    {loading.content ? (
                      <Skeleton width="100%" height="400px" />
                    ) : errors.content ? (
                      <Message severity="error" text={errors.content} className="w-full" />
                    ) : analyticsData.geographicData.length > 0 ? (
                      <div className="chart-container" style={{ height: '400px' }}>
                        <Chart
                          type="bar"
                          data={geoDistributionData}
                          options={standardChartOptions}
                        />
                      </div>
                    ) : (
                      <Message severity="info" text="No geographic data available" className="w-full" />
                    )}
                  </div>
                  <div className="col-12 lg:col-4">
                    {loading.content ? (
                      <div className="grid">
                        {[1, 2, 3, 4, 5].map(i => (
                          <div key={i} className="col-12">
                            <Skeleton width="100%" height="2rem" className="mb-1" />
                          </div>
                        ))}
                      </div>
                    ) : errors.content ? (
                      <Message severity="error" text={errors.content} className="w-full" />
                    ) : analyticsData.geographicData.length > 0 ? (
                      <DataTable value={analyticsData.geographicData} size="small" emptyMessage="No geographic data available">
                        <Column field="country" header="Country" />
                        <Column 
                          field="infringements" 
                          header="Infringements"
                          body={(rowData) => <Badge value={rowData.infringements} severity="warning" />}
                        />
                        <Column 
                          field="successRate" 
                          header="Success Rate"
                          body={(rowData) => `${rowData.successRate.toFixed(1)}%`}
                        />
                      </DataTable>
                    ) : (
                      <Message severity="info" text="No geographic data available" className="w-full" />
                    )}
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Compliance Tab */}
        <TabPanel header="Compliance & Response" leftIcon="pi pi-shield">
          <div className="grid">
            {/* Compliance Ratings */}
            <div className="col-12 lg:col-8">
              <Card title="Platform Compliance Ratings" className="h-full">
                {loading.compliance ? (
                  <div className="grid">
                    {[1, 2, 3, 4, 5].map(i => (
                      <div key={i} className="col-12">
                        <Skeleton width="100%" height="3rem" className="mb-2" />
                      </div>
                    ))}
                  </div>
                ) : errors.compliance ? (
                  <Message severity="error" text={errors.compliance} className="w-full" />
                ) : analyticsData.complianceMetrics.length > 0 ? (
                  <DataTable value={analyticsData.complianceMetrics} size="small" showGridlines emptyMessage="No compliance data available">
                    <Column field="platform" header="Platform" />
                    <Column 
                      field="complianceScore" 
                      header="Compliance Score"
                      sortable
                      body={(rowData) => (
                        <div className="flex align-items-center gap-2">
                          <ProgressBar 
                            value={rowData.complianceScore * 10} 
                            showValue={false} 
                            style={{ width: '80px', height: '8px' }}
                            color={rowData.complianceScore >= 8 ? '#10B981' : rowData.complianceScore >= 6 ? '#F59E0B' : '#EF4444'}
                          />
                          <Tag 
                            value={`${rowData.complianceScore.toFixed(1)}/10`}
                            severity={rowData.complianceScore >= 8 ? 'success' : rowData.complianceScore >= 6 ? 'warning' : 'danger'}
                          />
                        </div>
                      )}
                    />
                    <Column 
                      field="responseRate" 
                      header="Response Rate"
                      sortable
                      body={(rowData) => `${rowData.responseRate.toFixed(1)}%`}
                    />
                    <Column 
                      field="avgResponseTime" 
                      header="Avg Response Time"
                      sortable
                      body={(rowData) => `${rowData.avgResponseTime.toFixed(1)}h`}
                    />
                  </DataTable>
                ) : (
                  <Message severity="info" text="No compliance data available" className="w-full" />
                )}
              </Card>
            </div>

            {/* Response Time Categories */}
            <div className="col-12 lg:col-4">
              <Card title="Response Time Categories" className="h-full">
                {loading.compliance ? (
                  <div className="flex flex-column gap-3">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} width="100%" height="4rem" />
                    ))}
                  </div>
                ) : errors.compliance ? (
                  <Message severity="error" text={errors.compliance} className="w-full" />
                ) : analyticsData.responseTimeAnalysis.length > 0 ? (
                  <div className="flex flex-column gap-3">
                    <div className="p-3 border-round bg-green-50">
                      <div className="flex justify-content-between align-items-center">
                        <span className="font-medium text-green-900">Fast (&lt; 16h)</span>
                        <Badge 
                          value={analyticsData.responseTimeAnalysis.filter(r => r.category === 'fast').length} 
                          severity="success"
                        />
                      </div>
                      <div className="text-green-600 text-sm mt-1">
                        {analyticsData.responseTimeAnalysis.filter(r => r.category === 'fast').map(r => r.platform).join(', ') || 'None'}
                      </div>
                    </div>
                    
                    <div className="p-3 border-round bg-yellow-50">
                      <div className="flex justify-content-between align-items-center">
                        <span className="font-medium text-yellow-900">Medium (16-24h)</span>
                        <Badge 
                          value={analyticsData.responseTimeAnalysis.filter(r => r.category === 'medium').length} 
                          severity="warning"
                        />
                      </div>
                      <div className="text-yellow-600 text-sm mt-1">
                        {analyticsData.responseTimeAnalysis.filter(r => r.category === 'medium').map(r => r.platform).join(', ') || 'None'}
                      </div>
                    </div>
                    
                    <div className="p-3 border-round bg-red-50">
                      <div className="flex justify-content-between align-items-center">
                        <span className="font-medium text-red-900">Slow (&gt; 24h)</span>
                        <Badge 
                          value={analyticsData.responseTimeAnalysis.filter(r => r.category === 'slow').length} 
                          severity="danger"
                        />
                      </div>
                      <div className="text-red-600 text-sm mt-1">
                        {analyticsData.responseTimeAnalysis.filter(r => r.category === 'slow').map(r => r.platform).join(', ') || 'None'}
                      </div>
                    </div>
                  </div>
                ) : (
                  <Message severity="info" text="No response time data available" className="w-full" />
                )}
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Advanced Analytics Tab */}
        <TabPanel header="Advanced Analytics" leftIcon="pi pi-cog">
          <div className="grid">
            {loading.trends ? (
              <div className="col-12">
                <Skeleton width="100%" height="20rem" />
              </div>
            ) : errors.trends ? (
              <div className="col-12">
                <Message severity="error" text={errors.trends} className="w-full" />
              </div>
            ) : analyticsData.trendAnalysis && analyticsData.trendAnalysis.length > 0 ? (
              <>
                <div className="col-12">
                  <Card title="Trend Analysis">
                    <div className="grid">
                      {analyticsData.trendAnalysis.map((trend, index) => (
                        <div key={index} className="col-12 md:col-6 lg:col-4">
                          <div className="p-3 border-round bg-gray-50">
                            <div className="flex justify-content-between align-items-start mb-2">
                              <span className="font-medium">{trend.metric}</span>
                              <Tag 
                                value={trend.trend} 
                                severity={trend.trend === 'increasing' ? 'success' : trend.trend === 'decreasing' ? 'danger' : 'info'}
                              />
                            </div>
                            <div className="text-2xl font-bold mb-1">
                              {trend.changePercentage > 0 ? '+' : ''}{trend.changePercentage.toFixed(1)}%
                            </div>
                            <div className="text-sm text-600">
                              Confidence: {(trend.confidence * 100).toFixed(0)}%
                            </div>
                            {trend.projection && (
                              <div className="mt-2 text-sm">
                                <div>Next Week: {trend.projection.nextWeek}</div>
                                <div>Next Month: {trend.projection.nextMonth}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
                {analyticsData.performanceMetrics && (
                  <div className="col-12">
                    <Card title="Performance Benchmarks">
                      <div className="grid">
                        <div className="col-12 md:col-6">
                          <h5>Efficiency Metrics</h5>
                          <div className="flex flex-column gap-2">
                            <div className="flex justify-content-between">
                              <span>Detection Accuracy:</span>
                              <span className="font-medium">{(analyticsData.performanceMetrics.efficiency.detectionAccuracy * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-content-between">
                              <span>False Positive Rate:</span>
                              <span className="font-medium">{(analyticsData.performanceMetrics.efficiency.falsePositiveRate * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-content-between">
                              <span>Processing Time:</span>
                              <span className="font-medium">{analyticsData.performanceMetrics.efficiency.processingTime.toFixed(1)}s</span>
                            </div>
                          </div>
                        </div>
                        <div className="col-12 md:col-6">
                          <h5>Effectiveness Metrics</h5>
                          <div className="flex flex-column gap-2">
                            <div className="flex justify-content-between">
                              <span>Removal Success Rate:</span>
                              <span className="font-medium">{(analyticsData.performanceMetrics.effectiveness.removalSuccessRate * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-content-between">
                              <span>Avg Removal Time:</span>
                              <span className="font-medium">{analyticsData.performanceMetrics.effectiveness.avgRemovalTime.toFixed(1)}h</span>
                            </div>
                            <div className="flex justify-content-between">
                              <span>Protection Score:</span>
                              <span className="font-medium">{analyticsData.performanceMetrics.effectiveness.contentProtectionScore.toFixed(1)}/10</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                )}
              </>
            ) : (
              <div className="col-12">
                <Card title="Advanced Analytics">
                  <div className="text-center p-4">
                    <i className="pi pi-chart-line text-4xl text-400 mb-3"></i>
                    <h3 className="text-700">Analyzing Your Data</h3>
                    <p className="text-600">
                      Advanced analytics will appear here once sufficient data is collected.
                      This includes predictive modeling, trend forecasting, and performance benchmarks.
                    </p>
                    <div className="flex flex-wrap gap-2 justify-content-center mt-4">
                      <Tag value="Predictive Modeling" />
                      <Tag value="Trend Forecasting" />
                      <Tag value="Risk Assessment" />
                      <Tag value="Pattern Recognition" />
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </div>
        </TabPanel>
      </TabView>

      {/* Export Dialog */}
      <Dialog
        header="Export Report"
        visible={showExportDialog}
        style={{ width: '450px' }}
        onHide={() => setShowExportDialog(false)}
        footer={
          <div className="flex gap-2">
            <Button
              label="Cancel"
              outlined
              onClick={() => setShowExportDialog(false)}
            />
            <Button
              label="Export"
              onClick={() => handleExport('pdf')}
            />
          </div>
        }
      >
        <div className="flex flex-column gap-3">
          <div>
            <label className="block font-medium mb-2">Export Format</label>
            <Dropdown
              value="pdf"
              options={[
                { label: 'PDF Report', value: 'pdf' },
                { label: 'CSV Data', value: 'csv' },
                { label: 'Excel Spreadsheet', value: 'excel' }
              ]}
              className="w-full"
            />
          </div>
          <div>
            <label className="block font-medium mb-2">Include Sections</label>
            <MultiSelect
              value={['overview', 'platforms', 'compliance']}
              options={[
                { label: 'Overview', value: 'overview' },
                { label: 'Platform Analysis', value: 'platforms' },
                { label: 'Content Analysis', value: 'content' },
                { label: 'Compliance', value: 'compliance' }
              ]}
              className="w-full"
            />
          </div>
        </div>
      </Dialog>

      {/* Template Dialog */}
      <Dialog
        header="Report Templates"
        visible={showTemplateDialog}
        style={{ width: '600px' }}
        onHide={() => setShowTemplateDialog(false)}
      >
        <div className="flex flex-column gap-3">
          {reportTemplates.map(template => (
            <Card key={template.id} className="cursor-pointer hover:shadow-3 transition-all transition-duration-150">
              <div className="flex justify-content-between align-items-start">
                <div className="flex-1">
                  <h4 className="m-0 mb-2">{template.name}</h4>
                  <p className="text-600 m-0 mb-3">{template.description}</p>
                  <div className="flex flex-wrap gap-1">
                    {template.sections.map(section => (
                      <Tag key={section} value={section} size="small" />
                    ))}
                  </div>
                </div>
                <Button
                  label="Apply"
                  size="small"
                  onClick={() => handleTemplateApply(template)}
                />
              </div>
            </Card>
          ))}
        </div>
      </Dialog>
    </div>
  );
};

export default Reports;