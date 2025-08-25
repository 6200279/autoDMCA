import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Chart } from 'primereact/chart';
import { ProgressBar } from 'primereact/progressbar';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { Skeleton } from 'primereact/skeleton';
import { Message } from 'primereact/message';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { searchEngineDelistingApi } from '../../services/api';
import type { DelistingStatistics, DashboardMetrics } from '../../types/delisting';

interface StatisticsDashboardProps {
  refreshTrigger?: number;
}

const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({
  refreshTrigger
}) => {
  const [statistics, setStatistics] = useState<DelistingStatistics | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statsResponse, dashboardResponse] = await Promise.all([
        searchEngineDelistingApi.getDelistingStatistics(),
        searchEngineDelistingApi.getDashboardData()
      ]);
      
      setStatistics(statsResponse.data);
      setDashboardData(dashboardResponse.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [refreshTrigger]);

  if (error) {
    return (
      <Message 
        severity="error" 
        text={error} 
        className="w-full"
      />
    );
  }

  // Chart configurations
  const getSuccessRateChartData = () => {
    if (!statistics?.searchEngineBreakdown) return null;
    
    const engines = Object.keys(statistics.searchEngineBreakdown);
    const data = engines.map(engine => statistics.searchEngineBreakdown[engine].successRate);
    
    return {
      labels: engines.map(e => e.charAt(0).toUpperCase() + e.slice(1)),
      datasets: [
        {
          label: 'Success Rate (%)',
          data: data,
          backgroundColor: [
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)'
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)'
          ],
          borderWidth: 1
        }
      ]
    };
  };

  const getStatusDistributionData = () => {
    if (!statistics) return null;
    
    return {
      labels: ['Completed', 'Pending', 'Failed'],
      datasets: [
        {
          data: [
            statistics.completedRequests,
            statistics.pendingRequests,
            statistics.failedRequests
          ],
          backgroundColor: [
            '#22C55E',
            '#F59E0B',
            '#EF4444'
          ],
          hoverBackgroundColor: [
            '#16A34A',
            '#D97706',
            '#DC2626'
          ]
        }
      ]
    };
  };

  const chartOptions = {
    plugins: {
      legend: {
        position: 'top' as const,
      }
    },
    responsive: true,
    maintainAspectRatio: false
  };

  return (
    <div className="statistics-dashboard">
      <div className="grid">
        {/* Key Metrics Cards */}
        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="text-center">
              {loading ? (
                <Skeleton width="100%" height="80px" />
              ) : (
                <>
                  <div className="text-3xl font-bold text-primary mb-2">
                    {statistics?.totalRequests.toLocaleString() || 0}
                  </div>
                  <div className="text-600">Total Requests</div>
                </>
              )}
            </div>
          </Card>
        </div>

        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="text-center">
              {loading ? (
                <Skeleton width="100%" height="80px" />
              ) : (
                <>
                  <div className="text-3xl font-bold text-green-500 mb-2">
                    {Math.round(statistics?.successRate || 0)}%
                  </div>
                  <div className="text-600">Success Rate</div>
                </>
              )}
            </div>
          </Card>
        </div>

        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="text-center">
              {loading ? (
                <Skeleton width="100%" height="80px" />
              ) : (
                <>
                  <div className="text-3xl font-bold text-blue-500 mb-2">
                    {dashboardData?.activeRequests || 0}
                  </div>
                  <div className="text-600">Active Requests</div>
                </>
              )}
            </div>
          </Card>
        </div>

        <div className="col-12 md:col-3">
          <Card className="h-full">
            <div className="text-center">
              {loading ? (
                <Skeleton width="100%" height="80px" />
              ) : (
                <>
                  <div className="text-3xl font-bold text-orange-500 mb-2">
                    {Math.round(statistics?.averageProcessingTime || 0)}
                  </div>
                  <div className="text-600">Avg. Processing (min)</div>
                </>
              )}
            </div>
          </Card>
        </div>

        {/* Success Rate by Search Engine */}
        <div className="col-12 lg:col-8">
          <Card title="Success Rate by Search Engine" className="h-full">
            {loading ? (
              <Skeleton width="100%" height="300px" />
            ) : (
              <Chart
                type="bar"
                data={getSuccessRateChartData()}
                options={chartOptions}
                style={{ height: '300px' }}
              />
            )}
          </Card>
        </div>

        {/* Status Distribution */}
        <div className="col-12 lg:col-4">
          <Card title="Request Status Distribution" className="h-full">
            {loading ? (
              <Skeleton width="100%" height="300px" />
            ) : (
              <Chart
                type="doughnut"
                data={getStatusDistributionData()}
                options={chartOptions}
                style={{ height: '300px' }}
              />
            )}
          </Card>
        </div>

        {/* Search Engine Performance Breakdown */}
        <div className="col-12">
          <Card title="Search Engine Performance Details">
            {loading ? (
              <div className="grid">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="col-12 md:col-6 lg:col-3">
                    <Skeleton width="100%" height="120px" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid">
                {statistics && Object.entries(statistics.searchEngineBreakdown).map(([engine, data]) => (
                  <div key={engine} className="col-12 md:col-6 lg:col-3">
                    <div className="surface-card border-round p-4">
                      <div className="flex align-items-center justify-content-between mb-3">
                        <h4 className="m-0 text-lg font-semibold">
                          {engine.charAt(0).toUpperCase() + engine.slice(1)}
                        </h4>
                        <Tag
                          value={`${Math.round(data.successRate)}%`}
                          severity={data.successRate >= 80 ? 'success' : 
                                   data.successRate >= 60 ? 'warning' : 'danger'}
                        />
                      </div>
                      
                      <div className="mb-3">
                        <ProgressBar
                          value={data.successRate}
                          color={data.successRate >= 80 ? '#22C55E' : 
                                data.successRate >= 60 ? '#F59E0B' : '#EF4444'}
                          style={{ height: '8px' }}
                        />
                      </div>
                      
                      <div className="grid text-sm">
                        <div className="col-6">
                          <div className="text-600">Total</div>
                          <div className="font-semibold">{data.total}</div>
                        </div>
                        <div className="col-6">
                          <div className="text-600">Successful</div>
                          <div className="font-semibold text-green-600">{data.successful}</div>
                        </div>
                        <div className="col-6">
                          <div className="text-600">Failed</div>
                          <div className="font-semibold text-red-600">{data.failed}</div>
                        </div>
                        <div className="col-6">
                          <div className="text-600">Rate</div>
                          <div className="font-semibold">{Math.round(data.successRate)}%</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Recent Activity */}
        {dashboardData?.recentActivity && (
          <div className="col-12">
            <Card title="Recent Activity">
              <DataTable
                value={dashboardData.recentActivity}
                responsiveLayout="scroll"
                emptyMessage="No recent activity"
              >
                <Column
                  field="url"
                  header="URL"
                  body={(data) => (
                    <span className="text-sm">
                      {data.url.length > 50 ? `${data.url.substring(0, 50)}...` : data.url}
                    </span>
                  )}
                />
                <Column
                  field="status"
                  header="Status"
                  body={(data) => (
                    <Tag
                      value={data.status.toUpperCase()}
                      severity={
                        data.status === 'completed' ? 'success' :
                        data.status === 'failed' ? 'danger' :
                        'info'
                      }
                    />
                  )}
                />
                <Column
                  field="createdAt"
                  header="Time"
                  body={(data) => (
                    <span className="text-sm">
                      {new Date(data.createdAt).toLocaleString()}
                    </span>
                  )}
                />
              </DataTable>
            </Card>
          </div>
        )}

        {/* System Alerts */}
        {dashboardData?.systemAlerts && dashboardData.systemAlerts.length > 0 && (
          <div className="col-12">
            <Card title="System Alerts">
              <div className="grid">
                {dashboardData.systemAlerts.map((alert, index) => (
                  <div key={index} className="col-12">
                    <Message
                      severity={alert.severity === 'critical' ? 'error' : 
                               alert.severity === 'high' ? 'warn' : 'info'}
                      text={`${alert.type}: ${alert.message}`}
                      className="w-full"
                    />
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatisticsDashboard;