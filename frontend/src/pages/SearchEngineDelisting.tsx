import React, { useState, useEffect, useMemo, useRef } from 'react';
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
import { InputSwitch } from 'primereact/inputswitch';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Skeleton } from 'primereact/skeleton';
import { Toolbar } from 'primereact/toolbar';
import { SplitButton } from 'primereact/splitbutton';
import { Timeline } from 'primereact/timeline';
import { Slider } from 'primereact/slider';
import { Checkbox } from 'primereact/checkbox';
import { SelectButton } from 'primereact/selectbutton';
import { FileUpload } from 'primereact/fileupload';
import { RadioButton } from 'primereact/radiobutton';
import { Chips } from 'primereact/chips';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Steps } from 'primereact/steps';
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
import { SearchEngine, DelistingRequest, DelistingType, DelistingStatus, URLMonitoring, SearchResult, VisibilityMetrics, PriorityLevel } from '../types/api';

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

// Additional local interfaces
interface KeywordTracking {
  id: string;
  keyword: string;
  searchEngines: string[];
  regions: string[];
  results: SearchResult[];
  trend: 'up' | 'down' | 'stable';
  alertThreshold: number;
  isProtected: boolean;
}

interface RegionData {
  region: string;
  country: string;
  requestCount: number;
  successRate: number;
  avgResponseTime: number;
}

const SearchEngineDelisting: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const [loading, setLoading] = useState(true);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  
  // Dialog states
  const [showRequestDialog, setShowRequestDialog] = useState(false);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [showMonitoringDialog, setShowMonitoringDialog] = useState(false);
  const [showAnalyticsDialog, setShowAnalyticsDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<DelistingRequest | null>(null);
  
  // Form states
  const [newRequest, setNewRequest] = useState<Partial<DelistingRequest>>({
    type: DelistingType.URL_REMOVAL,
    priority: PriorityLevel.MEDIUM,
    urls: [],
    keywords: [],
    metadata: {}
  });
  const [bulkUrls, setBulkUrls] = useState<string>('');
  const [selectedSearchEngines, setSelectedSearchEngines] = useState<string[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string>('global');
  
  // Filter states
  const [dateRange, setDateRange] = useState<Date[]>([
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    new Date()
  ]);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [engineFilter, setEngineFilter] = useState<string[]>([]);
  
  // Data states
  const [searchEngines] = useState<SearchEngine[]>([
    {
      id: 'google',
      name: 'Google Search',
      domain: 'google.com',
      isActive: true,
      supportsImageSearch: true,
      supportsCacheRemoval: true,
      supportsRegionalDelisting: true,
      avgResponseTime: 72,
      successRate: 87.3,
      icon: 'pi pi-google',
      color: '#4285F4'
    },
    {
      id: 'google-images',
      name: 'Google Images',
      domain: 'images.google.com',
      isActive: true,
      supportsImageSearch: true,
      supportsCacheRemoval: true,
      supportsRegionalDelisting: true,
      avgResponseTime: 48,
      successRate: 91.2,
      icon: 'pi pi-images',
      color: '#34A853'
    },
    {
      id: 'bing',
      name: 'Bing Search',
      domain: 'bing.com',
      isActive: true,
      supportsImageSearch: true,
      supportsCacheRemoval: true,
      supportsRegionalDelisting: true,
      avgResponseTime: 96,
      successRate: 83.7,
      icon: 'pi pi-microsoft',
      color: '#0078D4'
    },
    {
      id: 'yahoo',
      name: 'Yahoo Search',
      domain: 'search.yahoo.com',
      isActive: true,
      supportsImageSearch: true,
      supportsCacheRemoval: false,
      supportsRegionalDelisting: true,
      avgResponseTime: 120,
      successRate: 79.4,
      icon: 'pi pi-search',
      color: '#7B0099'
    },
    {
      id: 'duckduckgo',
      name: 'DuckDuckGo',
      domain: 'duckduckgo.com',
      isActive: true,
      supportsImageSearch: true,
      supportsCacheRemoval: false,
      supportsRegionalDelisting: false,
      avgResponseTime: 168,
      successRate: 71.8,
      icon: 'pi pi-shield',
      color: '#DE5833'
    }
  ]);

  const [delistingRequests] = useState<DelistingRequest[]>([
    {
      id: 'req-001',
      searchEngineId: 'google',
      searchEngine: 'Google Search',
      type: DelistingType.URL_REMOVAL,
      status: DelistingStatus.APPROVED,
      priority: PriorityLevel.HIGH,
      urls: ['https://example.com/infringing-content-1', 'https://example.com/infringing-content-2'],
      keywords: ['brand name', 'copyrighted content'],
      region: 'US',
      reason: 'Copyright infringement - unauthorized use of copyrighted material',
      template: 'Copyright Violation Template',
      submittedAt: '2024-01-15T10:30:00Z',
      responseExpected: '2024-01-18T10:30:00Z',
      responseReceived: '2024-01-17T14:20:00Z',
      responseContent: 'Request approved. Content removed from search results.',
      followUpCount: 0,
      successRate: 100,
      estimatedImpact: 85,
      metadata: {
        cacheRemoval: true,
        imageSearch: true,
        safetFiltering: false,
        sitemapSubmission: false
      }
    },
    {
      id: 'req-002',
      searchEngineId: 'bing',
      searchEngine: 'Bing Search',
      type: DelistingType.CACHE_REMOVAL,
      status: DelistingStatus.UNDER_REVIEW,
      priority: PriorityLevel.MEDIUM,
      urls: ['https://badsite.com/stolen-images'],
      keywords: ['model photos', 'exclusive content'],
      region: 'Global',
      reason: 'Cached content removal request for previously removed infringing material',
      template: 'Cache Removal Template',
      submittedAt: '2024-01-14T09:15:00Z',
      responseExpected: '2024-01-17T09:15:00Z',
      followUpCount: 1,
      nextFollowUp: '2024-01-18T09:15:00Z',
      successRate: 0,
      estimatedImpact: 45,
      metadata: {
        cacheRemoval: true,
        imageSearch: false,
        safetFiltering: false,
        sitemapSubmission: false
      }
    },
    {
      id: 'req-003',
      searchEngineId: 'google-images',
      searchEngine: 'Google Images',
      type: DelistingType.IMAGE_SEARCH,
      status: DelistingStatus.PARTIALLY_APPROVED,
      priority: PriorityLevel.HIGH,
      urls: ['https://pirate-site.com/gallery/stolen-photos'],
      keywords: ['professional photos', 'model portfolio'],
      region: 'EU',
      reason: 'Unauthorized distribution of professional photography in image search results',
      template: 'Image Search Removal Template',
      submittedAt: '2024-01-12T16:45:00Z',
      responseExpected: '2024-01-15T16:45:00Z',
      responseReceived: '2024-01-15T11:30:00Z',
      responseContent: 'Partial approval. 3 of 5 URLs removed from image search.',
      followUpCount: 1,
      nextFollowUp: '2024-01-20T16:45:00Z',
      successRate: 60,
      estimatedImpact: 70,
      metadata: {
        cacheRemoval: false,
        imageSearch: true,
        safetFiltering: true,
        sitemapSubmission: false
      }
    }
  ]);

  const [urlMonitoring] = useState<URLMonitoring[]>([
    {
      id: 'monitor-001',
      url: 'https://example.com/infringing-content',
      keywords: ['brand name', 'copyrighted material'],
      searchEngines: ['google', 'bing'],
      lastCheck: '2024-01-16T12:00:00Z',
      position: undefined,
      visibility: 15,
      alerts: true,
      autoDelisting: true,
      status: 'removed'
    },
    {
      id: 'monitor-002',
      url: 'https://badsite.com/stolen-content',
      keywords: ['exclusive content', 'premium material'],
      searchEngines: ['google', 'yahoo'],
      lastCheck: '2024-01-16T11:30:00Z',
      position: 3,
      visibility: 78,
      alerts: true,
      autoDelisting: false,
      status: 'active'
    }
  ]);

  const [visibilityMetrics] = useState<VisibilityMetrics[]>([
    {
      searchEngine: 'Google Search',
      totalUrls: 245,
      visibleUrls: 32,
      hiddenUrls: 213,
      visibilityReduction: 87.0,
      trend: 'improving'
    },
    {
      searchEngine: 'Bing Search',
      totalUrls: 198,
      visibleUrls: 41,
      hiddenUrls: 157,
      visibilityReduction: 79.3,
      trend: 'stable'
    },
    {
      searchEngine: 'Yahoo Search',
      totalUrls: 156,
      visibleUrls: 38,
      hiddenUrls: 118,
      visibilityReduction: 75.6,
      trend: 'declining'
    }
  ]);

  const [regionData] = useState<RegionData[]>([
    { region: 'North America', country: 'US', requestCount: 89, successRate: 91.2, avgResponseTime: 68 },
    { region: 'Europe', country: 'EU', requestCount: 67, successRate: 87.4, avgResponseTime: 72 },
    { region: 'Asia Pacific', country: 'AP', requestCount: 34, successRate: 83.1, avgResponseTime: 89 },
    { region: 'Global', country: 'Global', requestCount: 142, successRate: 85.7, avgResponseTime: 76 }
  ]);

  // Options for dropdowns
  const delistingTypeOptions = [
    { label: 'URL Removal', value: DelistingType.URL_REMOVAL },
    { label: 'Cache Removal', value: DelistingType.CACHE_REMOVAL },
    { label: 'Image Search Removal', value: DelistingType.IMAGE_SEARCH },
    { label: 'Keyword Blocking', value: DelistingType.KEYWORD_BLOCKING },
    { label: 'Safe Search Configuration', value: DelistingType.SAFE_SEARCH },
    { label: 'Sitemap Update', value: DelistingType.SITEMAP_UPDATE }
  ];

  const priorityOptions = [
    { label: 'Low', value: PriorityLevel.LOW },
    { label: 'Medium', value: PriorityLevel.MEDIUM },
    { label: 'High', value: PriorityLevel.HIGH },
    { label: 'Urgent', value: PriorityLevel.URGENT }
  ];

  const statusOptions = [
    { label: 'Draft', value: DelistingStatus.DRAFT },
    { label: 'Submitted', value: DelistingStatus.SUBMITTED },
    { label: 'Under Review', value: DelistingStatus.UNDER_REVIEW },
    { label: 'Approved', value: DelistingStatus.APPROVED },
    { label: 'Partially Approved', value: DelistingStatus.PARTIALLY_APPROVED },
    { label: 'Denied', value: DelistingStatus.DENIED },
    { label: 'Expired', value: DelistingStatus.EXPIRED },
    { label: 'Appealed', value: DelistingStatus.APPEALED }
  ];

  const regionOptions = [
    { label: 'Global', value: 'global' },
    { label: 'United States', value: 'US' },
    { label: 'European Union', value: 'EU' },
    { label: 'United Kingdom', value: 'UK' },
    { label: 'Canada', value: 'CA' },
    { label: 'Australia', value: 'AU' },
    { label: 'Asia Pacific', value: 'AP' }
  ];

  const templateOptions = [
    { label: 'Copyright Violation Template', value: 'copyright' },
    { label: 'Cache Removal Template', value: 'cache' },
    { label: 'Image Search Removal Template', value: 'image' },
    { label: 'Safe Search Template', value: 'safesearch' },
    { label: 'Custom Template', value: 'custom' }
  ];

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Chart data
  const visibilityTrendsData = useMemo(() => ({
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Visibility Reduction (%)',
        data: [65, 72, 78, 81, 85, 87],
        borderColor: '#4ECDC4',
        backgroundColor: 'rgba(78, 205, 196, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Success Rate (%)',
        data: [78, 82, 85, 88, 89, 91],
        borderColor: '#45B7D1',
        backgroundColor: 'rgba(69, 183, 209, 0.1)',
        tension: 0.4,
        fill: true
      }
    ]
  }), []);

  const requestsByEngineData = useMemo(() => ({
    labels: searchEngines.map(e => e.name),
    datasets: [{
      data: [145, 89, 67, 34, 23],
      backgroundColor: searchEngines.map(e => e.color),
      hoverBackgroundColor: searchEngines.map(e => e.color)
    }]
  }), [searchEngines]);

  const responseTimeData = useMemo(() => ({
    labels: searchEngines.map(e => e.name),
    datasets: [{
      label: 'Average Response Time (Hours)',
      data: searchEngines.map(e => e.avgResponseTime),
      backgroundColor: 'rgba(255, 159, 64, 0.8)',
      borderColor: '#FF9F40',
      borderWidth: 1
    }]
  }), [searchEngines]);

  // Event handlers
  const handleSubmitRequest = () => {
    if (!newRequest.urls || newRequest.urls.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Validation Error',
        detail: 'Please provide at least one URL'
      });
      return;
    }

    if (selectedSearchEngines.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Validation Error',
        detail: 'Please select at least one search engine'
      });
      return;
    }

    console.log('Submitting delisting request:', {
      ...newRequest,
      searchEngines: selectedSearchEngines,
      region: selectedRegion
    });

    toast.current?.show({
      severity: 'success',
      summary: 'Request Submitted',
      detail: 'Your delisting request has been submitted successfully'
    });

    setShowRequestDialog(false);
    resetForm();
  };

  const handleBulkSubmit = () => {
    const urls = bulkUrls.split('\n').filter(url => url.trim());
    
    if (urls.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Validation Error',
        detail: 'Please provide URLs for bulk submission'
      });
      return;
    }

    console.log('Submitting bulk delisting request for', urls.length, 'URLs');
    
    toast.current?.show({
      severity: 'success',
      summary: 'Bulk Request Submitted',
      detail: `${urls.length} URLs submitted for delisting`
    });

    setShowBulkDialog(false);
    setBulkUrls('');
  };

  const resetForm = () => {
    setNewRequest({
      type: DelistingType.URL_REMOVAL,
      priority: PriorityLevel.MEDIUM,
      urls: [],
      keywords: [],
      metadata: {}
    });
    setSelectedSearchEngines([]);
    setSelectedRegion('global');
  };

  const getStatusSeverity = (status: DelistingStatus) => {
    switch (status) {
      case DelistingStatus.APPROVED:
        return 'success';
      case DelistingStatus.PARTIALLY_APPROVED:
        return 'info';
      case DelistingStatus.UNDER_REVIEW:
        return 'warning';
      case DelistingStatus.DENIED:
      case DelistingStatus.EXPIRED:
        return 'danger';
      default:
        return 'secondary';
    }
  };

  const getPriorityIcon = (priority: PriorityLevel) => {
    switch (priority) {
      case PriorityLevel.URGENT:
        return 'pi pi-exclamation-circle';
      case PriorityLevel.HIGH:
        return 'pi pi-arrow-up';
      case PriorityLevel.MEDIUM:
        return 'pi pi-minus';
      case PriorityLevel.LOW:
        return 'pi pi-arrow-down';
      default:
        return 'pi pi-circle';
    }
  };

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

  if (loading) {
    return (
      <div className="search-engine-delisting-page">
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
    <div className="search-engine-delisting-page">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Header */}
      <div className="grid">
        <div className="col-12">
          <div className="flex flex-column lg:flex-row lg:justify-content-between lg:align-items-start gap-4 mb-4">
            <div>
              <h2 className="m-0 text-900">Advanced Search Engine Delisting</h2>
              <p className="text-600 m-0 mt-1">Manage content removal from search engines and monitor visibility</p>
            </div>
            
            <div className="flex flex-wrap gap-2">
              <Button 
                label="New Request" 
                icon="pi pi-plus" 
                onClick={() => setShowRequestDialog(true)}
              />
              <Button 
                label="Bulk Submit" 
                icon="pi pi-upload" 
                outlined
                onClick={() => setShowBulkDialog(true)}
              />
              <Button 
                label="Templates" 
                icon="pi pi-book" 
                outlined
                onClick={() => setShowTemplateDialog(true)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid mb-4">
        <div className="col-12 md:col-6 lg:col-3">
          {renderKPICard(
            'Total Requests',
            delistingRequests.length.toString(),
            'All time',
            'pi pi-list',
            'bg-blue-100 text-blue-800'
          )}
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          {renderKPICard(
            'Success Rate',
            '87.3%',
            'Average across engines',
            'pi pi-check-circle',
            'bg-green-100 text-green-800'
          )}
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          {renderKPICard(
            'Visibility Reduction',
            '82.4%',
            'Content hidden',
            'pi pi-eye-slash',
            'bg-orange-100 text-orange-800'
          )}
        </div>
        <div className="col-12 md:col-6 lg:col-3">
          {renderKPICard(
            'Avg Response Time',
            '76h',
            'Search engine response',
            'pi pi-clock',
            'bg-purple-100 text-purple-800'
          )}
        </div>
      </div>

      {/* Main Content Tabs */}
      <TabView activeIndex={activeTabIndex} onTabChange={(e) => setActiveTabIndex(e.index)}>
        
        {/* Dashboard Tab */}
        <TabPanel header="Dashboard" leftIcon="pi pi-chart-line">
          <div className="grid">
            {/* Search Engine Status Cards */}
            <div className="col-12">
              <Card title="Search Engine Status">
                <div className="grid">
                  {searchEngines.map((engine) => (
                    <div key={engine.id} className="col-12 md:col-6 lg:col-4 xl:col-3">
                      <Card className={`h-full engine-card border-2 ${engine.isActive ? 'border-green-200' : 'border-gray-200'}`}>
                        <div className="flex align-items-center gap-3 mb-3">
                          <div className={`engine-icon`} style={{ backgroundColor: engine.color + '20', color: engine.color }}>
                            <i className={engine.icon}></i>
                          </div>
                          <div>
                            <h4 className="m-0">{engine.name}</h4>
                            <div className="text-sm text-600">{engine.domain}</div>
                          </div>
                        </div>
                        
                        <div className="grid">
                          <div className="col-6">
                            <div className="text-sm text-600">Success Rate</div>
                            <div className="font-bold">{engine.successRate}%</div>
                          </div>
                          <div className="col-6">
                            <div className="text-sm text-600">Response Time</div>
                            <div className="font-bold">{engine.avgResponseTime}h</div>
                          </div>
                        </div>
                        
                        <Divider />
                        
                        <div className="flex flex-wrap gap-1">
                          {engine.supportsImageSearch && <Tag value="Images" severity="info" size="small" />}
                          {engine.supportsCacheRemoval && <Tag value="Cache" severity="success" size="small" />}
                          {engine.supportsRegionalDelisting && <Tag value="Regional" severity="warning" size="small" />}
                        </div>
                      </Card>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Charts */}
            <div className="col-12 lg:col-8">
              <Card title="Visibility Trends" className="h-full">
                <div style={{ height: '350px' }}>
                  <Chart
                    type="line"
                    data={visibilityTrendsData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'top' as const,
                        }
                      },
                      scales: {
                        y: {
                          beginAtZero: false,
                          min: 60,
                          max: 100
                        }
                      }
                    }}
                  />
                </div>
              </Card>
            </div>

            <div className="col-12 lg:col-4">
              <Card title="Requests by Engine" className="h-full">
                <div style={{ height: '350px' }}>
                  <Chart
                    type="doughnut"
                    data={requestsByEngineData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'bottom' as const,
                        }
                      }
                    }}
                  />
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Delisting Requests Tab */}
        <TabPanel header="Delisting Requests" leftIcon="pi pi-list">
          <div className="grid">
            <div className="col-12">
              <Card>
                <Toolbar 
                  start={
                    <div className="flex gap-2">
                      <MultiSelect
                        value={statusFilter}
                        options={statusOptions}
                        onChange={(e) => setStatusFilter(e.value)}
                        placeholder="Filter by Status"
                        maxSelectedLabels={2}
                        display="chip"
                      />
                      <MultiSelect
                        value={engineFilter}
                        options={searchEngines.map(e => ({ label: e.name, value: e.id }))}
                        onChange={(e) => setEngineFilter(e.value)}
                        placeholder="Filter by Engine"
                        maxSelectedLabels={2}
                        display="chip"
                      />
                    </div>
                  }
                  end={
                    <div className="flex gap-2">
                      <Button label="Refresh" icon="pi pi-refresh" outlined size="small" />
                      <Button label="Export" icon="pi pi-download" outlined size="small" />
                    </div>
                  }
                />
                
                <DataTable
                  value={delistingRequests}
                  paginator
                  rows={10}
                  sortMode="multiple"
                  selectionMode="multiple"
                  showGridlines
                  responsiveLayout="scroll"
                >
                  <Column
                    field="id"
                    header="Request ID"
                    sortable
                    style={{ minWidth: '120px' }}
                  />
                  <Column
                    field="searchEngine"
                    header="Search Engine"
                    sortable
                    body={(rowData) => (
                      <div className="flex align-items-center gap-2">
                        <i className={searchEngines.find(e => e.id === rowData.searchEngineId)?.icon} 
                           style={{ color: searchEngines.find(e => e.id === rowData.searchEngineId)?.color }}></i>
                        {rowData.searchEngine}
                      </div>
                    )}
                  />
                  <Column
                    field="type"
                    header="Type"
                    sortable
                    body={(rowData) => (
                      <Tag 
                        value={rowData.type.replace('_', ' ')}
                        severity="info"
                        style={{ textTransform: 'capitalize' }}
                      />
                    )}
                  />
                  <Column
                    field="status"
                    header="Status"
                    sortable
                    body={(rowData) => (
                      <Tag
                        value={rowData.status.replace('_', ' ')}
                        severity={getStatusSeverity(rowData.status)}
                        style={{ textTransform: 'capitalize' }}
                      />
                    )}
                  />
                  <Column
                    field="priority"
                    header="Priority"
                    sortable
                    body={(rowData) => (
                      <div className="flex align-items-center gap-1">
                        <i className={getPriorityIcon(rowData.priority)}></i>
                        <span style={{ textTransform: 'capitalize' }}>{rowData.priority}</span>
                      </div>
                    )}
                  />
                  <Column
                    field="urls"
                    header="URLs"
                    body={(rowData) => (
                      <Badge value={rowData.urls.length} severity="info" />
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
                        <span className="text-sm">{rowData.successRate}%</span>
                      </div>
                    )}
                  />
                  <Column
                    field="submittedAt"
                    header="Submitted"
                    sortable
                    body={(rowData) => new Date(rowData.submittedAt).toLocaleDateString()}
                  />
                  <Column
                    body={(rowData) => (
                      <Button
                        icon="pi pi-eye"
                        rounded
                        outlined
                        size="small"
                        onClick={() => setSelectedRequest(rowData)}
                      />
                    )}
                    style={{ width: '4rem' }}
                  />
                </DataTable>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* URL Monitoring Tab */}
        <TabPanel header="URL Monitoring" leftIcon="pi pi-eye">
          <div className="grid">
            <div className="col-12">
              <Card>
                <Toolbar
                  start={<h3 className="m-0">Monitored URLs</h3>}
                  end={
                    <Button 
                      label="Add URL" 
                      icon="pi pi-plus" 
                      size="small"
                      onClick={() => setShowMonitoringDialog(true)}
                    />
                  }
                />

                <DataTable
                  value={urlMonitoring}
                  paginator
                  rows={10}
                  showGridlines
                  responsiveLayout="scroll"
                >
                  <Column field="url" header="URL" style={{ minWidth: '300px' }} />
                  <Column
                    field="keywords"
                    header="Keywords"
                    body={(rowData) => (
                      <div className="flex flex-wrap gap-1">
                        {rowData.keywords.slice(0, 2).map((keyword: string, index: number) => (
                          <Tag key={index} value={keyword} severity="info" size="small" />
                        ))}
                        {rowData.keywords.length > 2 && (
                          <Tag value={`+${rowData.keywords.length - 2} more`} severity="secondary" size="small" />
                        )}
                      </div>
                    )}
                  />
                  <Column
                    field="visibility"
                    header="Visibility"
                    body={(rowData) => (
                      <div className="flex align-items-center gap-2">
                        <ProgressBar 
                          value={rowData.visibility} 
                          showValue={false} 
                          style={{ width: '80px', height: '8px' }}
                          color={rowData.visibility < 25 ? '#10B981' : rowData.visibility < 50 ? '#F59E0B' : '#EF4444'}
                        />
                        <span className="text-sm font-medium">{rowData.visibility}%</span>
                      </div>
                    )}
                  />
                  <Column
                    field="status"
                    header="Status"
                    body={(rowData) => (
                      <Tag
                        value={rowData.status}
                        severity={
                          rowData.status === 'removed' ? 'success' :
                          rowData.status === 'monitoring' ? 'warning' : 'danger'
                        }
                        style={{ textTransform: 'capitalize' }}
                      />
                    )}
                  />
                  <Column
                    field="lastCheck"
                    header="Last Check"
                    body={(rowData) => new Date(rowData.lastCheck).toLocaleString()}
                  />
                  <Column
                    field="alerts"
                    header="Alerts"
                    body={(rowData) => (
                      <InputSwitch checked={rowData.alerts} />
                    )}
                  />
                  <Column
                    body={() => (
                      <div className="flex gap-1">
                        <Button icon="pi pi-search" rounded outlined size="small" tooltip="Search Results" />
                        <Button icon="pi pi-cog" rounded outlined size="small" tooltip="Configure" />
                      </div>
                    )}
                  />
                </DataTable>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel header="Analytics" leftIcon="pi pi-chart-bar">
          <div className="grid">
            {/* Visibility Metrics */}
            <div className="col-12">
              <Card title="Visibility Metrics by Search Engine">
                <div className="grid">
                  {visibilityMetrics.map((metric) => (
                    <div key={metric.searchEngine} className="col-12 md:col-6 lg:col-4">
                      <Card className="h-full border-1 surface-border">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <h4 className="m-0">{metric.searchEngine}</h4>
                          <i className={`pi ${
                            metric.trend === 'improving' ? 'pi-arrow-up text-green-500' :
                            metric.trend === 'declining' ? 'pi-arrow-down text-red-500' :
                            'pi-minus text-yellow-500'
                          }`}></i>
                        </div>
                        
                        <div className="grid">
                          <div className="col-6">
                            <div className="text-sm text-600">Total URLs</div>
                            <div className="text-lg font-bold">{metric.totalUrls}</div>
                          </div>
                          <div className="col-6">
                            <div className="text-sm text-600">Hidden</div>
                            <div className="text-lg font-bold text-green-600">{metric.hiddenUrls}</div>
                          </div>
                          <div className="col-6">
                            <div className="text-sm text-600">Visible</div>
                            <div className="text-lg font-bold text-red-600">{metric.visibleUrls}</div>
                          </div>
                          <div className="col-6">
                            <div className="text-sm text-600">Reduction</div>
                            <div className="text-lg font-bold">{metric.visibilityReduction}%</div>
                          </div>
                        </div>
                        
                        <Divider />
                        
                        <ProgressBar 
                          value={metric.visibilityReduction}
                          showValue={false}
                          style={{ height: '8px' }}
                        />
                      </Card>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Regional Performance */}
            <div className="col-12 lg:col-8">
              <Card title="Regional Performance">
                <DataTable value={regionData} showGridlines>
                  <Column field="region" header="Region" />
                  <Column field="requestCount" header="Requests" />
                  <Column 
                    field="successRate" 
                    header="Success Rate"
                    body={(rowData) => (
                      <div className="flex align-items-center gap-2">
                        <ProgressBar 
                          value={rowData.successRate} 
                          showValue={false} 
                          style={{ width: '80px', height: '6px' }}
                        />
                        <span className="text-sm">{rowData.successRate}%</span>
                      </div>
                    )}
                  />
                  <Column 
                    field="avgResponseTime" 
                    header="Avg Response Time"
                    body={(rowData) => `${rowData.avgResponseTime}h`}
                  />
                </DataTable>
              </Card>
            </div>

            {/* Response Times Chart */}
            <div className="col-12 lg:col-4">
              <Card title="Response Times" className="h-full">
                <div style={{ height: '300px' }}>
                  <Chart
                    type="bar"
                    data={responseTimeData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      indexAxis: 'y' as const,
                      plugins: {
                        legend: {
                          display: false
                        }
                      },
                      scales: {
                        x: {
                          beginAtZero: true,
                          title: {
                            display: true,
                            text: 'Hours'
                          }
                        }
                      }
                    }}
                  />
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>
      </TabView>

      {/* New Request Dialog */}
      <Dialog
        header="Create Delisting Request"
        visible={showRequestDialog}
        style={{ width: '800px' }}
        onHide={() => setShowRequestDialog(false)}
        footer={
          <div className="flex gap-2">
            <Button label="Cancel" outlined onClick={() => setShowRequestDialog(false)} />
            <Button label="Submit Request" onClick={handleSubmitRequest} />
          </div>
        }
      >
        <div className="grid">
          <div className="col-12 md:col-6">
            <label className="block font-medium mb-2">Request Type</label>
            <Dropdown
              value={newRequest.type}
              options={delistingTypeOptions}
              onChange={(e) => setNewRequest(prev => ({ ...prev, type: e.value }))}
              className="w-full"
            />
          </div>
          
          <div className="col-12 md:col-6">
            <label className="block font-medium mb-2">Priority</label>
            <Dropdown
              value={newRequest.priority}
              options={priorityOptions}
              onChange={(e) => setNewRequest(prev => ({ ...prev, priority: e.value }))}
              className="w-full"
            />
          </div>
          
          <div className="col-12">
            <label className="block font-medium mb-2">Search Engines</label>
            <div className="grid">
              {searchEngines.map(engine => (
                <div key={engine.id} className="col-12 md:col-6">
                  <div className="flex align-items-center gap-2">
                    <Checkbox
                      inputId={engine.id}
                      checked={selectedSearchEngines.includes(engine.id)}
                      onChange={() => {
                        const updated = selectedSearchEngines.includes(engine.id)
                          ? selectedSearchEngines.filter(id => id !== engine.id)
                          : [...selectedSearchEngines, engine.id];
                        setSelectedSearchEngines(updated);
                      }}
                    />
                    <label htmlFor={engine.id} className="flex align-items-center gap-2">
                      <i className={engine.icon} style={{ color: engine.color }}></i>
                      {engine.name}
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="col-12">
            <label className="block font-medium mb-2">URLs (one per line)</label>
            <InputTextarea
              value={newRequest.urls?.join('\n') || ''}
              onChange={(e) => {
                const urls = e.target.value.split('\n').filter(url => url.trim());
                setNewRequest(prev => ({ ...prev, urls }));
              }}
              rows={4}
              className="w-full"
              placeholder="https://example.com/infringing-content&#10;https://badsite.com/stolen-material"
            />
          </div>
          
          <div className="col-12 md:col-6">
            <label className="block font-medium mb-2">Region</label>
            <Dropdown
              value={selectedRegion}
              options={regionOptions}
              onChange={(e) => setSelectedRegion(e.value)}
              className="w-full"
            />
          </div>
          
          <div className="col-12 md:col-6">
            <label className="block font-medium mb-2">Template</label>
            <Dropdown
              options={templateOptions}
              placeholder="Select template"
              className="w-full"
            />
          </div>
          
          <div className="col-12">
            <label className="block font-medium mb-2">Keywords (optional)</label>
            <Chips
              value={newRequest.keywords}
              onChange={(e) => setNewRequest(prev => ({ ...prev, keywords: e.value }))}
              className="w-full"
              placeholder="Add keywords"
            />
          </div>
          
          <div className="col-12">
            <label className="block font-medium mb-2">Reason for Removal</label>
            <InputTextarea
              value={newRequest.reason || ''}
              onChange={(e) => setNewRequest(prev => ({ ...prev, reason: e.value }))}
              rows={3}
              className="w-full"
              placeholder="Describe why this content should be removed from search results..."
            />
          </div>
          
          <div className="col-12">
            <h4>Additional Options</h4>
            <div className="grid">
              <div className="col-12 md:col-6">
                <div className="flex align-items-center gap-2">
                  <Checkbox
                    inputId="cache-removal"
                    checked={newRequest.metadata?.cacheRemoval || false}
                    onChange={(e) => setNewRequest(prev => ({
                      ...prev,
                      metadata: { ...prev.metadata, cacheRemoval: e.checked }
                    }))}
                  />
                  <label htmlFor="cache-removal">Request cache removal</label>
                </div>
              </div>
              <div className="col-12 md:col-6">
                <div className="flex align-items-center gap-2">
                  <Checkbox
                    inputId="image-search"
                    checked={newRequest.metadata?.imageSearch || false}
                    onChange={(e) => setNewRequest(prev => ({
                      ...prev,
                      metadata: { ...prev.metadata, imageSearch: e.checked }
                    }))}
                  />
                  <label htmlFor="image-search">Include image search</label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Dialog>

      {/* Bulk Submit Dialog */}
      <Dialog
        header="Bulk URL Submission"
        visible={showBulkDialog}
        style={{ width: '600px' }}
        onHide={() => setShowBulkDialog(false)}
        footer={
          <div className="flex gap-2">
            <Button label="Cancel" outlined onClick={() => setShowBulkDialog(false)} />
            <Button label="Submit All" onClick={handleBulkSubmit} />
          </div>
        }
      >
        <div className="grid">
          <div className="col-12">
            <label className="block font-medium mb-2">URLs (one per line)</label>
            <InputTextarea
              value={bulkUrls}
              onChange={(e) => setBulkUrls(e.target.value)}
              rows={8}
              className="w-full"
              placeholder="https://example.com/url1&#10;https://example.com/url2&#10;https://example.com/url3"
            />
          </div>
          <div className="col-12">
            <div className="text-sm text-600 mb-3">
              {bulkUrls.split('\n').filter(url => url.trim()).length} URLs detected
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default SearchEngineDelisting;