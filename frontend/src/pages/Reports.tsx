import React, { useState, useEffect, useMemo } from 'react';
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

// Types and Interfaces
interface ReportFilters {
  dateRange: Date[];
  platforms: string[];
  contentTypes: string[];
  reportType: string;
  timeGranularity: string;
}

interface AnalyticsData {
  totalInfringements: number;
  totalTakedowns: number;
  successRate: number;
  avgResponseTime: number;
  platformBreakdown: PlatformMetrics[];
  timeSeriesData: TimeSeriesDataPoint[];
  geographicData: GeographicDataPoint[];
  contentTypeBreakdown: ContentTypeMetrics[];
  roiMetrics: ROIMetrics;
  responseTimeData: ResponseTimeData[];
  complianceRating: PlatformCompliance[];
}

interface PlatformMetrics {
  platform: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  avgResponseTime: number;
  cost: number;
  roi: number;
  complianceRating: number;
}

interface TimeSeriesDataPoint {
  date: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  visibilityReduction: number;
}

interface GeographicDataPoint {
  country: string;
  infringements: number;
  takedowns: number;
  successRate: number;
}

interface ContentTypeMetrics {
  type: string;
  count: number;
  percentage: number;
  successRate: number;
}

interface ROIMetrics {
  totalInvestment: number;
  contentValueProtected: number;
  estimatedLossPrevented: number;
  roi: number;
  costPerTakedown: number;
}

interface ResponseTimeData {
  platform: string;
  avgHours: number;
  category: 'fast' | 'medium' | 'slow';
}

interface PlatformCompliance {
  platform: string;
  complianceScore: number;
  responseRate: number;
  avgResponseTime: number;
}

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  sections: string[];
  filters: Partial<ReportFilters>;
}

const Reports: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [realTimeMode, setRealTimeMode] = useState(false);
  
  // Filters and Settings
  const [filters, setFilters] = useState<ReportFilters>({
    dateRange: [
      new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
      new Date()
    ],
    platforms: ['Instagram', 'TikTok', 'OnlyFans', 'Twitter', 'YouTube'],
    contentTypes: ['Images', 'Videos', 'Audio', 'Text'],
    reportType: 'comprehensive',
    timeGranularity: 'daily'
  });

  // Mock data - In real app, this would come from API
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData>({
    totalInfringements: 1247,
    totalTakedowns: 1089,
    successRate: 87.3,
    avgResponseTime: 18.5,
    platformBreakdown: [
      { platform: 'Instagram', infringements: 487, takedowns: 423, successRate: 86.9, avgResponseTime: 12.3, cost: 2115, roi: 340, complianceRating: 8.7 },
      { platform: 'TikTok', infringements: 342, takedowns: 301, successRate: 88.0, avgResponseTime: 15.2, cost: 1505, roi: 410, complianceRating: 9.1 },
      { platform: 'OnlyFans', infringements: 198, takedowns: 178, successRate: 89.9, avgResponseTime: 8.7, cost: 890, roi: 520, complianceRating: 9.5 },
      { platform: 'Twitter', infringements: 134, takedowns: 107, successRate: 79.9, avgResponseTime: 28.4, cost: 535, roi: 210, complianceRating: 6.8 },
      { platform: 'YouTube', infringements: 86, takedowns: 80, successRate: 93.0, avgResponseTime: 22.1, cost: 400, roi: 380, complianceRating: 8.9 }
    ],
    timeSeriesData: [
      { date: '2024-01-01', infringements: 89, takedowns: 76, successRate: 85.4, visibilityReduction: 78 },
      { date: '2024-01-02', infringements: 94, takedowns: 82, successRate: 87.2, visibilityReduction: 82 },
      { date: '2024-01-03', infringements: 76, takedowns: 68, successRate: 89.5, visibilityReduction: 85 },
      { date: '2024-01-04', infringements: 112, takedowns: 95, successRate: 84.8, visibilityReduction: 75 },
      { date: '2024-01-05', infringements: 103, takedowns: 91, successRate: 88.3, visibilityReduction: 80 },
      { date: '2024-01-06', infringements: 87, takedowns: 79, successRate: 90.8, visibilityReduction: 88 },
      { date: '2024-01-07', infringements: 98, takedowns: 85, successRate: 86.7, visibilityReduction: 77 }
    ],
    geographicData: [
      { country: 'United States', infringements: 523, takedowns: 456, successRate: 87.2 },
      { country: 'United Kingdom', infringements: 198, takedowns: 176, successRate: 88.9 },
      { country: 'Canada', infringements: 134, takedowns: 119, successRate: 88.8 },
      { country: 'Australia', infringements: 98, takedowns: 87, successRate: 88.8 },
      { country: 'Germany', infringements: 87, takedowns: 74, successRate: 85.1 }
    ],
    contentTypeBreakdown: [
      { type: 'Images', count: 678, percentage: 54.4, successRate: 89.2 },
      { type: 'Videos', count: 423, percentage: 33.9, successRate: 85.1 },
      { type: 'Audio', count: 98, percentage: 7.9, successRate: 91.8 },
      { type: 'Text', count: 48, percentage: 3.8, successRate: 79.2 }
    ],
    roiMetrics: {
      totalInvestment: 5445,
      contentValueProtected: 42300,
      estimatedLossPrevented: 18600,
      roi: 341.6,
      costPerTakedown: 5.0
    },
    responseTimeData: [
      { platform: 'OnlyFans', avgHours: 8.7, category: 'fast' },
      { platform: 'Instagram', avgHours: 12.3, category: 'fast' },
      { platform: 'TikTok', avgHours: 15.2, category: 'medium' },
      { platform: 'YouTube', avgHours: 22.1, category: 'medium' },
      { platform: 'Twitter', avgHours: 28.4, category: 'slow' }
    ],
    complianceRating: [
      { platform: 'OnlyFans', complianceScore: 9.5, responseRate: 96.8, avgResponseTime: 8.7 },
      { platform: 'TikTok', complianceScore: 9.1, responseRate: 91.2, avgResponseTime: 15.2 },
      { platform: 'YouTube', complianceScore: 8.9, responseRate: 89.4, avgResponseTime: 22.1 },
      { platform: 'Instagram', complianceScore: 8.7, responseRate: 88.1, avgResponseTime: 12.3 },
      { platform: 'Twitter', complianceScore: 6.8, responseRate: 73.2, avgResponseTime: 28.4 }
    ]
  });

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

  const reportTemplates: ReportTemplate[] = [
    {
      id: 'monthly-executive',
      name: 'Monthly Executive Summary',
      description: 'High-level monthly performance overview for executives',
      sections: ['overview', 'roi', 'trends'],
      filters: { timeGranularity: 'monthly' }
    },
    {
      id: 'platform-deep-dive',
      name: 'Platform Deep Dive',
      description: 'Detailed analysis of platform performance and compliance',
      sections: ['platforms', 'compliance', 'response-times'],
      filters: { reportType: 'platform' }
    },
    {
      id: 'roi-analysis',
      name: 'ROI & Cost Analysis',
      description: 'Financial performance and return on investment metrics',
      sections: ['roi', 'costs', 'value-protected'],
      filters: { reportType: 'roi' }
    }
  ];

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Auto-refresh for real-time mode
  useEffect(() => {
    if (!realTimeMode) return;
    
    const interval = setInterval(() => {
      // Simulate real-time data updates
      console.log('Refreshing real-time data...');
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [realTimeMode]);

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

  const responseTimeData = useMemo(() => ({
    labels: analyticsData.responseTimeData.map(r => r.platform),
    datasets: [{
      label: 'Average Response Time (Hours)',
      data: analyticsData.responseTimeData.map(r => r.avgHours),
      backgroundColor: analyticsData.responseTimeData.map(r => 
        r.category === 'fast' ? 'rgba(76, 175, 80, 0.8)' :
        r.category === 'medium' ? 'rgba(255, 193, 7, 0.8)' :
        'rgba(244, 67, 54, 0.8)'
      ),
      borderColor: analyticsData.responseTimeData.map(r => 
        r.category === 'fast' ? '#4CAF50' :
        r.category === 'medium' ? '#FFC107' :
        '#F44336'
      ),
      borderWidth: 1
    }]
  }), [analyticsData.responseTimeData]);

  const contentTypeData = useMemo(() => ({
    labels: analyticsData.contentTypeBreakdown.map(c => c.type),
    datasets: [{
      data: analyticsData.contentTypeBreakdown.map(c => c.percentage),
      backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'],
      hoverBackgroundColor: ['#FF5252', '#26C6DA', '#42A5F5', '#66BB6A']
    }]
  }), [analyticsData.contentTypeBreakdown]);

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
  const handleFilterChange = (key: keyof ReportFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleExport = (format: 'pdf' | 'csv' | 'excel') => {
    console.log(`Exporting report as ${format.toUpperCase()}`);
    // Implement export logic here
    setShowExportDialog(false);
  };

  const handleTemplateApply = (template: ReportTemplate) => {
    setFilters(prev => ({
      ...prev,
      ...template.filters
    }));
    setShowTemplateDialog(false);
  };

  const handleScheduleReport = () => {
    console.log('Scheduling report...');
    // Implement scheduling logic
  };

  // Template functions
  const renderKPICard = (title: string, value: string | number, subtitle?: string, icon?: string, color?: string) => (
    <Card className="h-full kpi-card">
      <div className="flex justify-content-between align-items-start">
        <div>
          <div className="text-500 font-medium text-sm">{title}</div>
          <div className="text-900 font-bold text-xl mt-1">{value}</div>
          {subtitle && (
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

  const renderPlatformTable = () => (
    <DataTable 
      value={analyticsData.platformBreakdown}
      size="small"
      showGridlines
      sortMode="multiple"
      paginator
      rows={10}
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
            <span className="text-sm font-medium">{rowData.successRate}%</span>
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
            value={`${rowData.roi}%`} 
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
            <span className="text-sm font-medium">{rowData.complianceRating}/10</span>
          </div>
        )}
      />
    </DataTable>
  );

  if (loading) {
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
      <Toast />
      
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
                />
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
                analyticsData.totalInfringements.toLocaleString(),
                'Detected this period',
                'pi pi-exclamation-triangle',
                'bg-orange-100 text-orange-800'
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Successful Takedowns',
                analyticsData.totalTakedowns.toLocaleString(),
                'Content removed',
                'pi pi-check-circle',
                'bg-green-100 text-green-800'
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Success Rate',
                `${analyticsData.successRate}%`,
                'Overall effectiveness',
                'pi pi-chart-pie',
                'bg-blue-100 text-blue-800'
              )}
            </div>
            
            <div className="col-12 md:col-6 lg:col-3">
              {renderKPICard(
                'Avg Response Time',
                `${analyticsData.avgResponseTime}h`,
                'Platform response',
                'pi pi-clock',
                'bg-purple-100 text-purple-800'
              )}
            </div>

            {/* ROI Overview */}
            <div className="col-12 lg:col-8">
              <Card title="Return on Investment Analysis" className="h-full">
                <div className="grid">
                  <div className="col-12 md:col-6">
                    <div className="text-center p-3 border-round bg-blue-50">
                      <div className="text-blue-900 text-lg font-bold">${analyticsData.roiMetrics.totalInvestment.toLocaleString()}</div>
                      <div className="text-blue-600 text-sm font-medium">Total Investment</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-6">
                    <div className="text-center p-3 border-round bg-green-50">
                      <div className="text-green-900 text-lg font-bold">${analyticsData.roiMetrics.contentValueProtected.toLocaleString()}</div>
                      <div className="text-green-600 text-sm font-medium">Content Value Protected</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-6">
                    <div className="text-center p-3 border-round bg-orange-50">
                      <div className="text-orange-900 text-lg font-bold">${analyticsData.roiMetrics.estimatedLossPrevented.toLocaleString()}</div>
                      <div className="text-orange-600 text-sm font-medium">Loss Prevented</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-6">
                    <div className="text-center p-3 border-round bg-purple-50">
                      <div className="text-purple-900 text-lg font-bold">{analyticsData.roiMetrics.roi}%</div>
                      <div className="text-purple-600 text-sm font-medium">ROI</div>
                    </div>
                  </div>
                </div>
                <Divider />
                <div className="flex justify-content-between align-items-center">
                  <span className="font-medium">Cost per Takedown:</span>
                  <Tag value={`$${analyticsData.roiMetrics.costPerTakedown}`} severity="info" />
                </div>
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
                    <Badge value={`${analyticsData.contentTypeBreakdown.length} types`} />
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Geographic Reach</span>
                    <Badge value={`${analyticsData.geographicData.length} countries`} />
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-sm">Data Freshness</span>
                    <Tag value={realTimeMode ? "Real-time" : "Last updated 5 min ago"} severity="success" />
                  </div>
                </div>
              </Card>
            </div>

            {/* Trends Chart */}
            <div className="col-12">
              <Card title="Performance Trends" className="h-full">
                <div className="chart-container" style={{ height: '400px' }}>
                  <Chart
                    type="line"
                    data={trendsChartData}
                    options={multiAxisOptions}
                  />
                </div>
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
                <div className="chart-container" style={{ height: '350px' }}>
                  <Chart
                    type="doughnut"
                    data={platformDistributionData}
                    options={doughnutOptions}
                  />
                </div>
              </Card>
            </div>

            {/* Success Rate Comparison */}
            <div className="col-12 lg:col-6">
              <Card title="Success Rate by Platform" className="h-full">
                <div className="chart-container" style={{ height: '350px' }}>
                  <Chart
                    type="bar"
                    data={successRateComparisonData}
                    options={standardChartOptions}
                  />
                </div>
              </Card>
            </div>

            {/* Response Time Analysis */}
            <div className="col-12 lg:col-6">
              <Card title="Response Time Analysis" className="h-full">
                <div className="chart-container" style={{ height: '350px' }}>
                  <Chart
                    type="bar"
                    data={responseTimeData}
                    options={standardChartOptions}
                  />
                </div>
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
                <div className="chart-container" style={{ height: '350px' }}>
                  <Chart
                    type="pie"
                    data={contentTypeData}
                    options={doughnutOptions}
                  />
                </div>
              </Card>
            </div>

            {/* Content Type Performance */}
            <div className="col-12 lg:col-6">
              <Card title="Content Type Performance" className="h-full">
                <DataTable value={analyticsData.contentTypeBreakdown} size="small">
                  <Column field="type" header="Content Type" />
                  <Column 
                    field="count" 
                    header="Count"
                    body={(rowData) => <Badge value={rowData.count} />}
                  />
                  <Column 
                    field="percentage" 
                    header="Percentage"
                    body={(rowData) => `${rowData.percentage}%`}
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
                      </div>
                    )}
                  />
                </DataTable>
              </Card>
            </div>

            {/* Geographic Distribution */}
            <div className="col-12">
              <Card title="Geographic Distribution of Infringements">
                <div className="grid">
                  <div className="col-12 lg:col-8">
                    <div className="chart-container" style={{ height: '400px' }}>
                      <Chart
                        type="bar"
                        data={geoDistributionData}
                        options={standardChartOptions}
                      />
                    </div>
                  </div>
                  <div className="col-12 lg:col-4">
                    <DataTable value={analyticsData.geographicData} size="small">
                      <Column field="country" header="Country" />
                      <Column 
                        field="infringements" 
                        header="Infringements"
                        body={(rowData) => <Badge value={rowData.infringements} severity="warning" />}
                      />
                      <Column 
                        field="successRate" 
                        header="Success Rate"
                        body={(rowData) => `${rowData.successRate}%`}
                      />
                    </DataTable>
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
                <DataTable value={analyticsData.complianceRating} size="small" showGridlines>
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
                          value={`${rowData.complianceScore}/10`}
                          severity={rowData.complianceScore >= 8 ? 'success' : rowData.complianceScore >= 6 ? 'warning' : 'danger'}
                        />
                      </div>
                    )}
                  />
                  <Column 
                    field="responseRate" 
                    header="Response Rate"
                    sortable
                    body={(rowData) => `${rowData.responseRate}%`}
                  />
                  <Column 
                    field="avgResponseTime" 
                    header="Avg Response Time"
                    sortable
                    body={(rowData) => `${rowData.avgResponseTime}h`}
                  />
                </DataTable>
              </Card>
            </div>

            {/* Response Time Categories */}
            <div className="col-12 lg:col-4">
              <Card title="Response Time Categories" className="h-full">
                <div className="flex flex-column gap-3">
                  <div className="p-3 border-round bg-green-50">
                    <div className="flex justify-content-between align-items-center">
                      <span className="font-medium text-green-900">Fast (&lt; 16h)</span>
                      <Badge 
                        value={analyticsData.responseTimeData.filter(r => r.category === 'fast').length} 
                        severity="success"
                      />
                    </div>
                    <div className="text-green-600 text-sm mt-1">
                      {analyticsData.responseTimeData.filter(r => r.category === 'fast').map(r => r.platform).join(', ')}
                    </div>
                  </div>
                  
                  <div className="p-3 border-round bg-yellow-50">
                    <div className="flex justify-content-between align-items-center">
                      <span className="font-medium text-yellow-900">Medium (16-24h)</span>
                      <Badge 
                        value={analyticsData.responseTimeData.filter(r => r.category === 'medium').length} 
                        severity="warning"
                      />
                    </div>
                    <div className="text-yellow-600 text-sm mt-1">
                      {analyticsData.responseTimeData.filter(r => r.category === 'medium').map(r => r.platform).join(', ')}
                    </div>
                  </div>
                  
                  <div className="p-3 border-round bg-red-50">
                    <div className="flex justify-content-between align-items-center">
                      <span className="font-medium text-red-900">Slow (&gt; 24h)</span>
                      <Badge 
                        value={analyticsData.responseTimeData.filter(r => r.category === 'slow').length} 
                        severity="danger"
                      />
                    </div>
                    <div className="text-red-600 text-sm mt-1">
                      {analyticsData.responseTimeData.filter(r => r.category === 'slow').map(r => r.platform).join(', ')}
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Advanced Analytics Tab */}
        <TabPanel header="Advanced Analytics" leftIcon="pi pi-cog">
          <div className="grid">
            <div className="col-12">
              <Card title="Predictive Analytics & Trends">
                <div className="text-center p-4">
                  <i className="pi pi-chart-line text-4xl text-400 mb-3"></i>
                  <h3 className="text-700">Advanced Analytics Coming Soon</h3>
                  <p className="text-600">
                    This section will include predictive modeling, trend forecasting,
                    machine learning insights, and advanced statistical analysis.
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