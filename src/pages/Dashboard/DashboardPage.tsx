import React from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  useTheme,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useWebSocket } from '@hooks/useWebSocket';
import { apiService } from '@services/api';
import StatCards from './components/StatCards';
import InfringementChart from './components/InfringementChart';
import PlatformDistribution from './components/PlatformDistribution';
import RecentActivity from './components/RecentActivity';
import QuickActions from './components/QuickActions';

const DashboardPage: React.FC = () => {
  const theme = useTheme();

  // Fetch dashboard statistics
  const { 
    data: dashboardData, 
    isLoading, 
    refetch: refetchStats 
  } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiService.getDashboardStats(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Set up WebSocket for real-time updates
  useWebSocket({
    onAnalyticsUpdate: (data) => {
      // Update dashboard data with real-time analytics
      refetchStats();
    },
    onInfringementDetected: (data) => {
      // Refresh stats when new infringement is detected
      refetchStats();
    },
    onStatusUpdate: (data) => {
      // Refresh when status changes occur
      refetchStats();
    },
    enableNotifications: true,
  });

  const stats = dashboardData?.data;

  if (isLoading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <Grid container spacing={3}>
          {[...Array(4)].map((_, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card>
                <CardContent>
                  <Box sx={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div className="loading-spinner" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  return (
    <Box>
      {/* Page Header */}
      <Box mb={3}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="600">
          Dashboard
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Monitor your content protection status and recent activity
        </Typography>
      </Box>

      {/* Statistics Cards */}
      <Box mb={4}>
        <StatCards stats={stats} />
      </Box>

      {/* Main Content Grid */}
      <Grid container spacing={3}>
        {/* Charts Section */}
        <Grid item xs={12} lg={8}>
          <Grid container spacing={3}>
            {/* Infringement Trends Chart */}
            <Grid item xs={12}>
              <Card sx={{ height: '400px' }}>
                <CardContent sx={{ height: '100%' }}>
                  <Typography variant="h6" gutterBottom fontWeight="600">
                    Detection & Resolution Trends
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    Monthly overview of detected and resolved infringements
                  </Typography>
                  <InfringementChart data={stats?.chartData?.monthly} />
                </CardContent>
              </Card>
            </Grid>

            {/* Platform Distribution */}
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '300px' }}>
                <CardContent sx={{ height: '100%' }}>
                  <Typography variant="h6" gutterBottom fontWeight="600">
                    Platform Distribution
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    Where infringements are most commonly found
                  </Typography>
                  <PlatformDistribution data={stats?.chartData?.platforms} />
                </CardContent>
              </Card>
            </Grid>

            {/* Quick Actions */}
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '300px' }}>
                <CardContent sx={{ height: '100%' }}>
                  <Typography variant="h6" gutterBottom fontWeight="600">
                    Quick Actions
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    Common tasks and shortcuts
                  </Typography>
                  <QuickActions />
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={3}>
            {/* Recent Activity */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight="600">
                    Recent Activity
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    Latest system events and updates
                  </Typography>
                  <RecentActivity activities={stats?.recentActivity} />
                </CardContent>
              </Card>
            </Grid>

            {/* Content Type Breakdown */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight="600">
                    Content Types
                  </Typography>
                  <Typography variant="body2" color="textSecondary" mb={2}>
                    Breakdown of protected content
                  </Typography>
                  <Box>
                    {stats?.chartData?.contentTypes?.map((type, index) => (
                      <Box
                        key={type.type}
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1.5}
                      >
                        <Typography variant="body2" textTransform="capitalize">
                          {type.type}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2" fontWeight="600">
                            {type.count}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            ({type.percentage}%)
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;