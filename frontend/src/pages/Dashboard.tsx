import React, { useState, useEffect } from 'react';
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

// Types for dashboard data
interface DashboardStats {
  totalProfiles: number;
  activeScans: number;
  infringementsFound: number;
  takedownsSent: number;
  profilesChange: number;
  scansChange: number;
  infringementsChange: number;
  takedownsChange: number;
}

interface UsageMetrics {
  scansUsed: number;
  scansLimit: number;
  successRate: number;
  monthlySuccessRate: number;
}

interface RecentActivity {
  id: string;
  type: 'infringement' | 'takedown' | 'scan' | 'profile';
  title: string;
  description: string;
  platform: string;
  status: 'pending' | 'success' | 'failed' | 'in-progress';
  timestamp: Date;
  url?: string;
}

interface PlatformData {
  platform: string;
  infringements: number;
  takedowns: number;
  successRate: number;
}

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<Date[]>([
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    new Date()
  ]);

  // Mock data - in real app, this would come from API
  const [stats, setStats] = useState<DashboardStats>({
    totalProfiles: 12,
    activeScans: 8,
    infringementsFound: 47,
    takedownsSent: 23,
    profilesChange: 20,
    scansChange: -5,
    infringementsChange: 15,
    takedownsChange: 8
  });

  const [usageMetrics, setUsageMetrics] = useState<UsageMetrics>({
    scansUsed: 150,
    scansLimit: 500,
    successRate: 85,
    monthlySuccessRate: 78
  });

  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([
    {
      id: '1',
      type: 'infringement',
      title: 'New infringement detected',
      description: 'Unauthorized content found on Instagram',
      platform: 'Instagram',
      status: 'pending',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      url: 'https://instagram.com/example'
    },
    {
      id: '2',
      type: 'takedown',
      title: 'Takedown request successful',
      description: 'Content removed from TikTok',
      platform: 'TikTok',
      status: 'success',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000)
    },
    {
      id: '3',
      type: 'scan',
      title: 'Automated scan completed',
      description: 'Profile "Model ABC" scan finished',
      platform: 'Multiple',
      status: 'success',
      timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000)
    },
    {
      id: '4',
      type: 'infringement',
      title: 'Infringement under review',
      description: 'Manual review required for OnlyFans content',
      platform: 'OnlyFans',
      status: 'in-progress',
      timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000)
    },
    {
      id: '5',
      type: 'takedown',
      title: 'Takedown request failed',
      description: 'Platform rejected DMCA request',
      platform: 'Twitter',
      status: 'failed',
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000)
    }
  ]);

  const [platformData, setPlatformData] = useState<PlatformData[]>([
    { platform: 'Instagram', infringements: 18, takedowns: 15, successRate: 83 },
    { platform: 'TikTok', infringements: 12, takedowns: 10, successRate: 83 },
    { platform: 'OnlyFans', infringements: 8, takedowns: 6, successRate: 75 },
    { platform: 'Twitter', infringements: 5, takedowns: 3, successRate: 60 },
    { platform: 'YouTube', infringements: 4, takedowns: 4, successRate: 100 }
  ]);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Chart data
  const monthlyTrendsData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Infringements Found',
        data: [23, 19, 31, 42, 38, 47],
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Takedowns Sent',
        data: [12, 15, 18, 25, 20, 23],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true
      }
    ]
  };

  const platformDistributionData = {
    labels: platformData.map(p => p.platform),
    datasets: [
      {
        data: platformData.map(p => p.infringements),
        backgroundColor: [
          '#E91E63',
          '#9C27B0',
          '#673AB7',
          '#3F51B5',
          '#2196F3'
        ],
        hoverBackgroundColor: [
          '#F06292',
          '#BA68C8',
          '#9575CD',
          '#7986CB',
          '#64B5F6'
        ]
      }
    ]
  };

  const successRateData = {
    labels: platformData.map(p => p.platform),
    datasets: [
      {
        label: 'Success Rate (%)',
        data: platformData.map(p => p.successRate),
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderColor: '#10B981',
        borderWidth: 1
      }
    ]
  };

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

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60));
      return `${diffInMinutes}m ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      return timestamp.toLocaleDateString();
    }
  };

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

  const timestampTemplate = (rowData: RecentActivity) => (
    <span className="text-color-secondary">{formatTimestamp(rowData.timestamp)}</span>
  );

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

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <div className="flex justify-content-between align-items-center mb-4">
            <Skeleton width="200px" height="2rem" />
            <Skeleton width="150px" height="2rem" />
          </div>
        </div>
        
        {/* Stats Cards Skeleton */}
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="col-12 md:col-6 lg:col-3">
            <Card>
              <Skeleton width="100%" height="80px" />
            </Card>
          </div>
        ))}
        
        {/* Charts Skeleton */}
        <div className="col-12 lg:col-8">
          <Card>
            <Skeleton width="100%" height="300px" />
          </Card>
        </div>
        <div className="col-12 lg:col-4">
          <Card>
            <Skeleton width="100%" height="300px" />
          </Card>
        </div>
      </div>
    );
  }

  return (
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
            <Button 
              label="Export Report" 
              icon="pi pi-download" 
              outlined 
              size="small"
            />
          </div>
        </div>
      </div>

      {/* Overview Statistics */}
      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-start">
            <div>
              <div className="text-500 font-medium text-sm">Total Profiles</div>
              <div className="text-900 font-bold text-xl mt-1">{stats.totalProfiles}</div>
              <div className="flex align-items-center gap-1 mt-2">
                <i className={`pi ${stats.profilesChange >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                <span className={`text-sm font-medium ${stats.profilesChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {Math.abs(stats.profilesChange)}%
                </span>
                <span className="text-500 text-sm">this month</span>
              </div>
            </div>
            <div className="bg-blue-100 text-blue-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
              <i className="pi pi-user text-xl" />
            </div>
          </div>
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-start">
            <div>
              <div className="text-500 font-medium text-sm">Active Scans</div>
              <div className="text-900 font-bold text-xl mt-1">{stats.activeScans}</div>
              <div className="flex align-items-center gap-1 mt-2">
                <i className={`pi ${stats.scansChange >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                <span className={`text-sm font-medium ${stats.scansChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {Math.abs(stats.scansChange)}%
                </span>
                <span className="text-500 text-sm">this month</span>
              </div>
            </div>
            <div className="bg-purple-100 text-purple-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
              <i className="pi pi-search text-xl" />
            </div>
          </div>
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-start">
            <div>
              <div className="text-500 font-medium text-sm">Infringements Found</div>
              <div className="text-900 font-bold text-xl mt-1">{stats.infringementsFound}</div>
              <div className="flex align-items-center gap-1 mt-2">
                <i className={`pi ${stats.infringementsChange >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                <span className={`text-sm font-medium ${stats.infringementsChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {Math.abs(stats.infringementsChange)}%
                </span>
                <span className="text-500 text-sm">this month</span>
              </div>
            </div>
            <div className="bg-orange-100 text-orange-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
              <i className="pi pi-exclamation-triangle text-xl" />
            </div>
          </div>
        </Card>
      </div>

      <div className="col-12 md:col-6 lg:col-3">
        <Card className="h-full">
          <div className="flex justify-content-between align-items-start">
            <div>
              <div className="text-500 font-medium text-sm">Takedowns Sent</div>
              <div className="text-900 font-bold text-xl mt-1">{stats.takedownsSent}</div>
              <div className="flex align-items-center gap-1 mt-2">
                <i className={`pi ${stats.takedownsChange >= 0 ? 'pi-arrow-up text-green-500' : 'pi-arrow-down text-red-500'} text-sm`} />
                <span className={`text-sm font-medium ${stats.takedownsChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {Math.abs(stats.takedownsChange)}%
                </span>
                <span className="text-500 text-sm">this month</span>
              </div>
            </div>
            <div className="bg-green-100 text-green-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center">
              <i className="pi pi-file text-xl" />
            </div>
          </div>
        </Card>
      </div>

      {/* Usage Metrics */}
      <div className="col-12 md:col-8">
        <Card title="Usage Metrics" className="h-full">
          <div className="grid">
            <div className="col-12 md:col-6">
              <div className="mb-3">
                <div className="flex justify-content-between align-items-center mb-2">
                  <span className="text-900 font-medium">Monthly Scans</span>
                  <span className="text-600">{usageMetrics.scansUsed} / {usageMetrics.scansLimit}</span>
                </div>
                <ProgressBar 
                  value={(usageMetrics.scansUsed / usageMetrics.scansLimit) * 100} 
                  showValue={false}
                  style={{ height: '8px' }}
                />
              </div>
            </div>
            <div className="col-12 md:col-6">
              <div className="mb-3">
                <div className="flex justify-content-between align-items-center mb-2">
                  <span className="text-900 font-medium">Success Rate</span>
                  <span className="text-600">{usageMetrics.successRate}%</span>
                </div>
                <ProgressBar 
                  value={usageMetrics.successRate} 
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
                <div className="text-blue-600 text-lg font-bold">{usageMetrics.scansUsed}</div>
              </div>
            </div>
            <div className="flex align-items-center gap-2 p-3 bg-green-50 border-round">
              <i className="pi pi-check-circle text-green-600" />
              <div>
                <div className="text-green-900 font-medium text-sm">Success Rate</div>
                <div className="text-green-600 text-lg font-bold">{usageMetrics.monthlySuccessRate}%</div>
              </div>
            </div>
          </div>
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
        <Card title="Monthly Trends" className="h-full">
          <div style={{ height: '300px' }}>
            <Chart 
              type="line" 
              data={monthlyTrendsData} 
              options={chartOptions} 
              height="300px"
            />
          </div>
        </Card>
      </div>

      {/* Platform Distribution */}
      <div className="col-12 lg:col-4">
        <Card title="Platform Distribution" className="h-full">
          <div style={{ height: '300px' }}>
            <Chart 
              type="doughnut" 
              data={platformDistributionData} 
              options={doughnutOptions}
              height="300px"
            />
          </div>
        </Card>
      </div>

      {/* Success Rate by Platform */}
      <div className="col-12 lg:col-6">
        <Card title="Success Rate by Platform" className="h-full">
          <div style={{ height: '250px' }}>
            <Chart 
              type="bar" 
              data={successRateData} 
              options={chartOptions}
              height="250px"
            />
          </div>
        </Card>
      </div>

      {/* Platform Performance Table */}
      <div className="col-12 lg:col-6">
        <Card title="Platform Performance" className="h-full">
          <DataTable 
            value={platformData} 
            size="small"
            showGridlines
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
                </div>
              )}
            />
          </DataTable>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="col-12">
        <Panel 
          header="Recent Activity" 
          toggleable 
          className="mt-4"
          headerTemplate={(options) => (
            <div className="flex justify-content-between align-items-center w-full">
              <span className="font-bold text-lg">{options.titleElement}</span>
              <div className="flex gap-2">
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
          <DataTable 
            value={recentActivity} 
            paginator 
            rows={10}
            size="small"
            showGridlines
            emptyMessage="No recent activity found"
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
        </Panel>
      </div>
    </div>
  );
};

export default Dashboard;