import React from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Typography,
  LinearProgress,
  Grid,
  Alert,
  Chip
} from '@mui/material';
import {
  Person,
  Search,
  Report,
  Warning,
  CheckCircle
} from '@mui/icons-material';

interface UsageOverviewProps {
  currentUsage: any;
  usageLimits: any;
  subscription: any;
}

const UsageOverview: React.FC<UsageOverviewProps> = ({
  currentUsage,
  usageLimits,
  subscription
}) => {
  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    return 'primary';
  };

  const getUsageStatus = (percentage: number) => {
    if (percentage >= 100) return 'exceeded';
    if (percentage >= 90) return 'critical';
    if (percentage >= 75) return 'warning';
    return 'normal';
  };

  const calculateUsagePercentage = (current: number, limit: number) => {
    return limit > 0 ? Math.min(100, (current / limit) * 100) : 0;
  };

  const formatUsageText = (current: number, limit: number, unit: string = '') => {
    return `${current?.toLocaleString() || 0} / ${limit?.toLocaleString() || 0} ${unit}`;
  };

  if (!currentUsage || !usageLimits) {
    return (
      <Card>
        <CardHeader title="Usage Overview" />
        <CardContent>
          <Alert severity="info">
            No usage data available. Usage tracking will begin once you have an active subscription.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const protectedProfilesPercentage = calculateUsagePercentage(
    currentUsage.protectedProfiles,
    usageLimits.maxProtectedProfiles
  );

  const monthlyScansPercentage = calculateUsagePercentage(
    currentUsage.monthlyScans,
    usageLimits.maxMonthlyScans
  );

  const takedownRequestsPercentage = calculateUsagePercentage(
    currentUsage.takedownRequests,
    usageLimits.maxTakedownRequests
  );

  const usageMetrics = [
    {
      title: 'Protected Profiles',
      icon: <Person />,
      current: currentUsage.protectedProfiles,
      limit: usageLimits.maxProtectedProfiles,
      percentage: protectedProfilesPercentage,
      unit: 'profiles'
    },
    {
      title: 'Monthly Scans',
      icon: <Search />,
      current: currentUsage.monthlyScans,
      limit: usageLimits.maxMonthlyScans,
      percentage: monthlyScansPercentage,
      unit: 'scans'
    },
    {
      title: 'Takedown Requests',
      icon: <Report />,
      current: currentUsage.takedownRequests,
      limit: usageLimits.maxTakedownRequests,
      percentage: takedownRequestsPercentage,
      unit: 'requests'
    }
  ];

  const hasWarnings = usageMetrics.some(metric => metric.percentage >= 75);

  return (
    <Card>
      <CardHeader
        title="Usage Overview"
        subheader={currentUsage.periodStart && currentUsage.periodEnd ? (
          `Billing period: ${new Date(currentUsage.periodStart).toLocaleDateString()} - ${new Date(currentUsage.periodEnd).toLocaleDateString()}`
        ) : undefined}
        action={
          hasWarnings ? (
            <Chip
              icon={<Warning />}
              label="Usage Warning"
              color="warning"
              size="small"
            />
          ) : (
            <Chip
              icon={<CheckCircle />}
              label="Healthy Usage"
              color="success"
              size="small"
            />
          )
        }
      />
      <CardContent>
        {/* Overall Status Alert */}
        {hasWarnings && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="body2">
              You're approaching usage limits for some features. Consider upgrading your plan
              to avoid service interruptions.
            </Typography>
          </Alert>
        )}

        {/* Usage Metrics */}
        <Grid container spacing={3}>
          {usageMetrics.map((metric, index) => {
            const status = getUsageStatus(metric.percentage);
            const color = getUsageColor(metric.percentage);

            return (
              <Grid item xs={12} md={4} key={index}>
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Box sx={{ mr: 1, color: `${color}.main` }}>
                      {metric.icon}
                    </Box>
                    <Typography variant="subtitle2">
                      {metric.title}
                    </Typography>
                    {status === 'exceeded' && (
                      <Chip
                        label="Exceeded"
                        color="error"
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    )}
                    {status === 'critical' && (
                      <Chip
                        label="Critical"
                        color="warning"
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    )}
                  </Box>

                  <Box sx={{ mb: 1 }}>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ display: 'flex', justifyContent: 'space-between' }}
                    >
                      <span>{formatUsageText(metric.current, metric.limit, metric.unit)}</span>
                      <span>{Math.round(metric.percentage)}%</span>
                    </Typography>
                  </Box>

                  <LinearProgress
                    variant="determinate"
                    value={metric.percentage}
                    color={color}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                      },
                    }}
                  />

                  {/* Usage details */}
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    {metric.current > 0 && metric.limit > 0 && (
                      <>
                        {metric.limit - metric.current} {metric.unit} remaining
                      </>
                    )}
                    {metric.current >= metric.limit && metric.limit > 0 && (
                      <>
                        Limit exceeded by {metric.current - metric.limit} {metric.unit}
                      </>
                    )}
                  </Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>

        {/* Additional Information */}
        <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Usage Reset:</strong> Usage limits reset at the beginning of each billing cycle.
            {subscription?.currentPeriodEnd && (
              <> Next reset: {new Date(subscription.currentPeriodEnd).toLocaleDateString()}</>
            )}
          </Typography>
        </Box>

        {/* Upgrade Suggestion */}
        {hasWarnings && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="info">
              <Typography variant="body2">
                Need more capacity? Upgrade to a higher plan for increased limits and additional features.
              </Typography>
            </Alert>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default UsageOverview;