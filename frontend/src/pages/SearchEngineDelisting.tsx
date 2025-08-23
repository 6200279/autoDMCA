/**
 * Search Engine Delisting Dashboard
 * Provides comprehensive interface for managing search engine delisting requests
 * PRD: "Dashboard integration for user visibility", "Real-time status tracking and reporting"
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Tag } from 'primereact/tag';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { ProgressBar } from 'primereact/progressbar';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { Message } from 'primereact/message';
import { TabView, TabPanel } from 'primereact/tabview';
import { Toast } from 'primereact/toast';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Chart } from 'primereact/chart';
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
  BarElement,
} from 'chart.js';
import api from '../services/api';
import ComingSoon from '../components/common/ComingSoon';
import ApiErrorDisplay from '../components/common/ApiErrorDisplay';
import ApiLoadingState from '../components/common/ApiLoadingState';
import FeatureStatusBadge from '../components/common/FeatureStatusBadge';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement,
  BarElement
);

interface DelistingRequest {
  id: string;
  url: string;
  status: 'pending' | 'submitted' | 'in_progress' | 'approved' | 'removed' | 'rejected' | 'failed';
  search_engines: string[];
  submitted_at: string;
  updated_at?: string;
  retry_count: number;
  engine_statuses?: { [key: string]: any };
  message?: string;
}

interface DelistingBatch {
  id: string;
  name: string;
  total_requests: number;
  completed_requests: number;
  failed_requests: number;
  success_rate: number;
  submitted_at: string;
  status: 'pending' | 'processing' | 'completed';
}

interface DelistingStats {
  time_period: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  pending_requests: number;
  success_rate: number;
  average_processing_time: number;
  search_engine_breakdown: { [key: string]: any };
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const SearchEngineDelisting: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [requests, setRequests] = useState<DelistingRequest[]>([]);
  const [batches, setBatches] = useState<DelistingBatch[]>([]);
  const [stats, setStats] = useState<DelistingStats | null>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [newRequestDialog, setNewRequestDialog] = useState(false);
  const [batchDialog, setBatchDialog] = useState(false);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<DelistingRequest | null>(null);
  
  // Form states
  const [newRequestForm, setNewRequestForm] = useState({
    url: '',
    original_content_url: '',
    reason: 'Copyright infringement',
    evidence_url: '',
    priority: 'normal' as 'low' | 'normal' | 'high' | 'urgent',
    search_engines: ['google', 'bing'] as string[]
  });
  
  const [batchForm, setBatchForm] = useState({
    name: '',
    description: '',
    urls: '',
    reason: 'Copyright infringement',
    priority: 'normal' as 'low' | 'normal' | 'high' | 'urgent',
    search_engines: ['google', 'bing'] as string[],
    batch_size: 10
  });
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [urlFilter, setUrlFilter] = useState('');

  // Load data on component mount
  useEffect(() => {
    loadData();
    
    // Set up periodic refresh for real-time updates
    const interval = setInterval(() => {
      loadDashboardData();
    }, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [requestsRes, statsRes, dashboardRes] = await Promise.all([
        api.get('/delisting/requests'),
        api.get('/delisting/statistics?time_period=24h'),
        api.get('/delisting/dashboard')
      ]);
      
      setRequests(requestsRes.data);
      setStats(statsRes.data);
      setDashboardData(dashboardRes.data);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load delisting data');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardData = async () => {
    try {
      const response = await api.get('/delisting/dashboard');
      setDashboardData(response.data);
    } catch (err) {
      console.error('Failed to refresh dashboard data:', err);
    }
  };

  const submitNewRequest = async () => {
    try {
      const response = await api.post('/delisting/requests', newRequestForm);
      
      // Refresh data
      await loadData();
      
      // Reset form and close dialog
      setNewRequestForm({
        url: '',
        original_content_url: '',
        reason: 'Copyright infringement',
        evidence_url: '',
        priority: 'normal',
        search_engines: ['google', 'bing']
      });
      setNewRequestDialog(false);
      
    } catch (err: any) {
      setError(err.message || 'Failed to submit delisting request');
    }
  };

  const submitBatchRequest = async () => {
    try {
      const urlList = batchForm.urls.split('\n').filter(url => url.trim());
      
      const batchData = {
        ...batchForm,
        urls: urlList
      };
      
      const response = await api.post('/delisting/batch', batchData);
      
      // Refresh data
      await loadData();
      
      // Reset form and close dialog
      setBatchForm({
        name: '',
        description: '',
        urls: '',
        reason: 'Copyright infringement',
        priority: 'normal',
        search_engines: ['google', 'bing'],
        batch_size: 10
      });
      setBatchDialog(false);
      
    } catch (err: any) {
      setError(err.message || 'Failed to submit batch request');
    }
  };

  const cancelRequest = async (requestId: string) => {
    try {
      await api.post(`/delisting/requests/${requestId}/cancel`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to cancel request');
    }
  };

  const retryRequest = async (requestId: string) => {
    try {
      await api.post(`/delisting/requests/${requestId}/retry`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to retry request');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'removed': return 'success';
      case 'approved': return 'success';
      case 'in_progress': return 'info';
      case 'submitted': return 'info';
      case 'pending': return 'warning';
      case 'rejected': return 'error';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Filter requests based on current filters
  const filteredRequests = requests.filter(request => {
    const matchesStatus = !statusFilter || request.status === statusFilter;
    const matchesUrl = !urlFilter || request.url.toLowerCase().includes(urlFilter.toLowerCase());
    return matchesStatus && matchesUrl;
  });

  // Chart configurations
  const successRateChartData = {
    labels: ['Successful', 'Failed', 'Pending'],
    datasets: [{
      data: stats ? [stats.successful_requests, stats.failed_requests, stats.pending_requests] : [0, 0, 0],
      backgroundColor: ['#4caf50', '#f44336', '#ff9800'],
      borderWidth: 0
    }]
  };

  const searchEngineChartData = {
    labels: stats ? Object.keys(stats.search_engine_breakdown) : [],
    datasets: [{
      label: 'Success Rate',
      data: stats ? Object.values(stats.search_engine_breakdown).map((engine: any) => engine.success_rate * 100) : [],
      backgroundColor: 'rgba(54, 162, 235, 0.6)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 1
    }]
  };

  if (loading) {
    return <ApiLoadingState message="Loading delisting dashboard..." />;
  }

  if (error) {
    return <ApiErrorDisplay error={error} onRetry={loadData} />;
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Search Engine Delisting
          <FeatureStatusBadge status="stable" sx={{ ml: 2 }} />
        </Typography>
        <Box>
          <Button
            startIcon={<AddIcon />}
            variant="contained"
            onClick={() => setNewRequestDialog(true)}
            sx={{ mr: 1 }}
          >
            New Request
          </Button>
          <Button
            startIcon={<AddIcon />}
            variant="outlined"
            onClick={() => setBatchDialog(true)}
            sx={{ mr: 1 }}
          >
            Batch Request
          </Button>
          <IconButton onClick={loadData}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Dashboard Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Requests
              </Typography>
              <Typography variant="h4">
                {dashboardData?.system_status?.queue_status?.processing_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Success Rate (24h)
              </Typography>
              <Typography variant="h4">
                {stats ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg Processing Time
              </Typography>
              <Typography variant="h4">
                {stats ? `${(stats.average_processing_time / 60).toFixed(0)}m` : '0m'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Queue Length
              </Typography>
              <Typography variant="h4">
                {dashboardData?.system_status?.queue_status?.queue_length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alert Section */}
      {dashboardData?.active_alerts && dashboardData.active_alerts.length > 0 && (
        <Box sx={{ mb: 3 }}>
          {dashboardData.active_alerts.map((alert: any) => (
            <Alert 
              key={alert.id} 
              severity={alert.severity === 'critical' ? 'error' : 'warning'}
              sx={{ mb: 1 }}
            >
              {alert.message}
            </Alert>
          ))}
        </Box>
      )}

      {/* Main Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label="Requests" />
          <Tab label="Analytics" />
          <Tab label="Verification" />
        </Tabs>
      </Box>

      {/* Requests Tab */}
      <TabPanel value={tabValue} index={0}>
        {/* Filters */}
        <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="submitted">Submitted</MenuItem>
              <MenuItem value="in_progress">In Progress</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="removed">Removed</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            size="small"
            label="Filter by URL"
            value={urlFilter}
            onChange={(e) => setUrlFilter(e.target.value)}
            sx={{ minWidth: 200 }}
          />
        </Box>

        {/* Requests Table */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>URL</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Search Engines</TableCell>
                <TableCell>Submitted</TableCell>
                <TableCell>Retries</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRequests.map((request) => (
                <TableRow key={request.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {request.url}
                      </Typography>
                      {request.message && (
                        <Typography variant="caption" color="textSecondary">
                          {request.message}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={request.status}
                      color={getStatusColor(request.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box>
                      {request.search_engines.map(engine => (
                        <Chip 
                          key={engine}
                          label={engine}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatDateTime(request.submitted_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {request.retry_count > 0 && (
                      <Chip 
                        label={`${request.retry_count} retries`}
                        size="small"
                        color="warning"
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedRequest(request);
                            setDetailsDialog(true);
                          }}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </Tooltip>
                      
                      {(request.status === 'pending' || request.status === 'submitted') && (
                        <Tooltip title="Cancel">
                          <IconButton
                            size="small"
                            onClick={() => cancelRequest(request.id)}
                          >
                            <CancelIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      
                      {request.status === 'failed' && (
                        <Tooltip title="Retry">
                          <IconButton
                            size="small"
                            onClick={() => retryRequest(request.id)}
                          >
                            <RetryIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* Analytics Tab */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Request Status Distribution
                </Typography>
                <Box sx={{ height: 300 }}>
                  <Doughnut data={successRateChartData} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Search Engine Success Rates
                </Typography>
                <Box sx={{ height: 300 }}>
                  <Bar data={searchEngineChartData} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Statistics (Last 24 Hours)
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2">Total Requests</Typography>
                    <Typography variant="h5">{stats?.total_requests || 0}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2">Success Rate</Typography>
                    <Typography variant="h5">
                      {stats ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%'}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2">Average Time</Typography>
                    <Typography variant="h5">
                      {stats ? `${(stats.average_processing_time / 60).toFixed(0)}min` : '0min'}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="subtitle2">Pending</Typography>
                    <Typography variant="h5">{stats?.pending_requests || 0}</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Verification Tab */}
      <TabPanel value={tabValue} index={2}>
        <ComingSoon 
          title="Delisting Verification"
          description="Real-time verification of successful URL removals from search engine indices will be available here."
          features={[
            'Automated verification checks',
            'Search result monitoring',
            'Removal confirmation reports',
            'Re-indexing alerts'
          ]}
        />
      </TabPanel>

      {/* New Request Dialog */}
      <Dialog open={newRequestDialog} onClose={() => setNewRequestDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Submit New Delisting Request</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="URL to Delist"
              value={newRequestForm.url}
              onChange={(e) => setNewRequestForm({ ...newRequestForm, url: e.target.value })}
              required
              fullWidth
              helperText="The URL that should be removed from search engines"
            />
            
            <TextField
              label="Original Content URL"
              value={newRequestForm.original_content_url}
              onChange={(e) => setNewRequestForm({ ...newRequestForm, original_content_url: e.target.value })}
              fullWidth
              helperText="URL of the original authorized content (optional)"
            />
            
            <TextField
              label="Reason"
              value={newRequestForm.reason}
              onChange={(e) => setNewRequestForm({ ...newRequestForm, reason: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            
            <TextField
              label="Evidence URL"
              value={newRequestForm.evidence_url}
              onChange={(e) => setNewRequestForm({ ...newRequestForm, evidence_url: e.target.value })}
              fullWidth
              helperText="URL containing evidence of ownership (optional)"
            />
            
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={newRequestForm.priority}
                label="Priority"
                onChange={(e) => setNewRequestForm({ ...newRequestForm, priority: e.target.value as any })}
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="normal">Normal</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="urgent">Urgent</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Search Engines</InputLabel>
              <Select
                multiple
                value={newRequestForm.search_engines}
                label="Search Engines"
                onChange={(e) => setNewRequestForm({ ...newRequestForm, search_engines: e.target.value as string[] })}
              >
                <MenuItem value="google">Google</MenuItem>
                <MenuItem value="bing">Bing</MenuItem>
                <MenuItem value="yandex">Yandex</MenuItem>
                <MenuItem value="duckduckgo">DuckDuckGo</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewRequestDialog(false)}>Cancel</Button>
          <Button onClick={submitNewRequest} variant="contained">Submit</Button>
        </DialogActions>
      </Dialog>

      {/* Batch Request Dialog */}
      <Dialog open={batchDialog} onClose={() => setBatchDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Submit Batch Delisting Request</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Batch Name"
              value={batchForm.name}
              onChange={(e) => setBatchForm({ ...batchForm, name: e.target.value })}
              fullWidth
              helperText="Name to identify this batch"
            />
            
            <TextField
              label="URLs (one per line)"
              value={batchForm.urls}
              onChange={(e) => setBatchForm({ ...batchForm, urls: e.target.value })}
              fullWidth
              multiline
              rows={8}
              required
              helperText="Enter each URL on a separate line"
            />
            
            <TextField
              label="Description"
              value={batchForm.description}
              onChange={(e) => setBatchForm({ ...batchForm, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            
            <TextField
              label="Batch Size"
              type="number"
              value={batchForm.batch_size}
              onChange={(e) => setBatchForm({ ...batchForm, batch_size: parseInt(e.target.value) || 10 })}
              fullWidth
              helperText="Number of URLs to process simultaneously"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchDialog(false)}>Cancel</Button>
          <Button onClick={submitBatchRequest} variant="contained">Submit Batch</Button>
        </DialogActions>
      </Dialog>

      {/* Request Details Dialog */}
      <Dialog open={detailsDialog} onClose={() => setDetailsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Request Details</DialogTitle>
        <DialogContent>
          {selectedRequest && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="h6" gutterBottom>
                URL: {selectedRequest.url}
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Status</Typography>
                  <Chip 
                    label={selectedRequest.status}
                    color={getStatusColor(selectedRequest.status) as any}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Submitted</Typography>
                  <Typography>{formatDateTime(selectedRequest.submitted_at)}</Typography>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Search Engines</Typography>
                  <Box>
                    {selectedRequest.search_engines.map(engine => (
                      <Chip key={engine} label={engine} size="small" sx={{ mr: 0.5 }} />
                    ))}
                  </Box>
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2">Retry Count</Typography>
                  <Typography>{selectedRequest.retry_count}</Typography>
                </Grid>
              </Grid>
              
              {selectedRequest.engine_statuses && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="h6" gutterBottom>Search Engine Status</Typography>
                  {Object.entries(selectedRequest.engine_statuses).map(([engine, status]) => (
                    <Box key={engine} sx={{ mb: 1 }}>
                      <Typography variant="subtitle2">{engine.toUpperCase()}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Status: {(status as any).status} | 
                        {(status as any).message && ` Message: ${(status as any).message}`}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SearchEngineDelisting;