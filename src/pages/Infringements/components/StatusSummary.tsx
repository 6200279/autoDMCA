import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
  alpha,
  CircularProgress,
} from '@mui/material';
import {
  Security,
  Schedule,
  CheckCircle,
  Error,
  Visibility,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@services/api';

const StatusSummary: React.FC = () => {
  const theme = useTheme();

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiService.getDashboardStats(),
  });

  const stats = dashboardData?.data;

  const statusCards = [
    {
      label: 'Total Detected',
      value: stats?.totalInfringements || 0,
      icon: Security,
      color: theme.palette.info.main,
      description: 'All time detections',
    },
    {
      label: 'Pending',
      value: stats?.pendingReviews || 0,
      icon: Schedule,
      color: theme.palette.warning.main,
      description: 'Awaiting processing',
    },
    {
      label: 'Reviewing',
      value: 8, // This would come from API
      icon: Visibility,
      color: theme.palette.primary.main,
      description: 'Under manual review',
    },
    {
      label: 'Resolved',
      value: stats?.successfulTakedowns || 0,
      icon: CheckCircle,
      color: theme.palette.success.main,
      description: 'Successfully removed',
    },
    {
      label: 'Failed',
      value: 3, // This would come from API
      icon: Error,
      color: theme.palette.error.main,
      description: 'Could not resolve',
    },
  ];

  if (isLoading) {
    return (
      <Grid container spacing={2}>
        {statusCards.map((_, index) => (
          <Grid item xs={12} sm={6} md={2.4} key={index}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <CircularProgress size={20} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  return (
    <Grid container spacing={2}>
      {statusCards.map((card, index) => {
        const Icon = card.icon;
        
        return (
          <Grid item xs={12} sm={6} md={2.4} key={index}>
            <Card
              sx={{
                height: '100%',
                background: `linear-gradient(135deg, ${alpha(card.color, 0.1)} 0%, ${alpha(card.color, 0.05)} 100%)`,
                border: `1px solid ${alpha(card.color, 0.1)}`,
                transition: 'transform 0.2s ease-in-out',
                '&:hover': {
                  transform: 'translateY(-2px)',
                },
              }}
            >
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Box
                  sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 40,
                    height: 40,
                    borderRadius: 2,
                    backgroundColor: alpha(card.color, 0.1),
                    mb: 1,
                  }}
                >
                  <Icon sx={{ color: card.color, fontSize: 20 }} />
                </Box>
                
                <Typography
                  variant="h5"
                  fontWeight="700"
                  color="text.primary"
                  gutterBottom
                >
                  {card.value.toLocaleString()}
                </Typography>
                
                <Typography
                  variant="body2"
                  fontWeight="600"
                  color="text.primary"
                  gutterBottom
                >
                  {card.label}
                </Typography>
                
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ fontSize: '0.7rem' }}
                >
                  {card.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
};

export default StatusSummary;