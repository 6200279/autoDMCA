import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Security,
  RemoveRedEye,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import { DashboardStats } from '@types/index';

interface StatCardsProps {
  stats?: DashboardStats;
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType;
  color: string;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  color,
  trend 
}) => {
  const theme = useTheme();

  return (
    <Card
      sx={{
        height: '100%',
        background: `linear-gradient(135deg, ${alpha(color, 0.1)} 0%, ${alpha(color, 0.05)} 100%)`,
        border: `1px solid ${alpha(color, 0.1)}`,
        transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: `0 8px 25px ${alpha(color, 0.15)}`,
        },
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" mb={2}>
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              backgroundColor: alpha(color, 0.1),
              mr: 2,
            }}
          >
            <Icon sx={{ color, fontSize: 24 }} />
          </Box>
          <Box flex={1}>
            <Typography variant="h4" fontWeight="700" color="text.primary">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </Typography>
          </Box>
        </Box>
        
        <Typography variant="h6" fontWeight="600" gutterBottom>
          {title}
        </Typography>
        
        {subtitle && (
          <Typography variant="body2" color="textSecondary" mb={1}>
            {subtitle}
          </Typography>
        )}
        
        {trend && (
          <Box display="flex" alignItems="center">
            <Typography
              variant="body2"
              fontWeight="600"
              color={trend.isPositive ? 'success.main' : 'error.main'}
              mr={1}
            >
              {trend.isPositive ? '+' : ''}{trend.value}%
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {trend.label}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

const StatCards: React.FC<StatCardsProps> = ({ stats }) => {
  const theme = useTheme();

  const cardData = [
    {
      title: 'Total Infringements',
      value: stats?.totalInfringements || 0,
      subtitle: 'Detected violations',
      icon: Security,
      color: theme.palette.error.main,
      trend: {
        value: 12,
        label: 'from last month',
        isPositive: false,
      },
    },
    {
      title: 'Active Monitoring',
      value: stats?.activeMonitoring || 0,
      subtitle: 'URLs being watched',
      icon: RemoveRedEye,
      color: theme.palette.primary.main,
      trend: {
        value: 8,
        label: 'new this week',
        isPositive: true,
      },
    },
    {
      title: 'Successful Takedowns',
      value: stats?.successfulTakedowns || 0,
      subtitle: 'Content removed',
      icon: CheckCircle,
      color: theme.palette.success.main,
      trend: {
        value: 24,
        label: 'this month',
        isPositive: true,
      },
    },
    {
      title: 'Pending Reviews',
      value: stats?.pendingReviews || 0,
      subtitle: 'Awaiting action',
      icon: Schedule,
      color: theme.palette.warning.main,
      trend: {
        value: 5,
        label: 'need attention',
        isPositive: false,
      },
    },
  ];

  return (
    <Grid container spacing={3}>
      {cardData.map((card, index) => (
        <Grid item xs={12} sm={6} md={3} key={index}>
          <StatCard {...card} />
        </Grid>
      ))}
    </Grid>
  );
};

export default StatCards;