import React from 'react';
import { Card } from 'primereact/card';
import { ProgressBar } from 'primereact/progressbar';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';

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
    if (percentage >= 90) return 'danger';
    if (percentage >= 75) return 'warning';
    return 'info';
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
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Usage Overview</h2>
        <Message 
          severity="info" 
          text="No usage data available. Usage tracking will begin once you have an active subscription." 
        />
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
      icon: 'pi pi-user',
      current: currentUsage.protectedProfiles,
      limit: usageLimits.maxProtectedProfiles,
      percentage: protectedProfilesPercentage,
      unit: 'profiles'
    },
    {
      title: 'Monthly Scans',
      icon: 'pi pi-search',
      current: currentUsage.monthlyScans,
      limit: usageLimits.maxMonthlyScans,
      percentage: monthlyScansPercentage,
      unit: 'scans'
    },
    {
      title: 'Takedown Requests',
      icon: 'pi pi-file',
      current: currentUsage.takedownRequests,
      limit: usageLimits.maxTakedownRequests,
      percentage: takedownRequestsPercentage,
      unit: 'requests'
    }
  ];

  const hasWarnings = usageMetrics.some(metric => metric.percentage >= 75);

  return (
    <Card className="p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl font-semibold">Usage Overview</h2>
          {currentUsage.periodStart && currentUsage.periodEnd && (
            <p className="text-sm text-gray-600 mt-1">
              Billing period: {new Date(currentUsage.periodStart).toLocaleDateString()} - {new Date(currentUsage.periodEnd).toLocaleDateString()}
            </p>
          )}
        </div>
        {hasWarnings ? (
          <Tag
            icon="pi pi-exclamation-triangle"
            value="Usage Warning"
            severity="warning"
          />
        ) : (
          <Tag
            icon="pi pi-check-circle"
            value="Healthy Usage"
            severity="success"
          />
        )}
      </div>
      
      <div className="space-y-4">
        {/* Overall Status Alert */}
        {hasWarnings && (
          <Message 
            severity="warn" 
            text="You're approaching usage limits for some features. Consider upgrading your plan to avoid service interruptions."
          />
        )}

        {/* Usage Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {usageMetrics.map((metric, index) => {
            const status = getUsageStatus(metric.percentage);
            const color = getUsageColor(metric.percentage);

            return (
              <div key={index} className="space-y-3">
                <div className="flex items-center gap-2">
                  <i className={`${metric.icon} ${
                    color === 'danger' ? 'text-red-500' : 
                    color === 'warning' ? 'text-yellow-500' : 
                    'text-blue-500'
                  }`}></i>
                  <span className="font-semibold text-sm">
                    {metric.title}
                  </span>
                  {status === 'exceeded' && (
                    <Tag
                      value="Exceeded"
                      severity="danger"
                      className="text-xs"
                    />
                  )}
                  {status === 'critical' && (
                    <Tag
                      value="Critical"
                      severity="warning"
                      className="text-xs"
                    />
                  )}
                </div>

                <div className="flex justify-between text-sm text-gray-600">
                  <span>{formatUsageText(metric.current, metric.limit, metric.unit)}</span>
                  <span>{Math.round(metric.percentage)}%</span>
                </div>

                <ProgressBar
                  value={metric.percentage}
                  className="h-2"
                  pt={{
                    value: {
                      className: color === 'danger' ? 'bg-red-500' : 
                                color === 'warning' ? 'bg-yellow-500' : 
                                'bg-blue-500'
                    }
                  }}
                />

                <p className="text-xs text-gray-500">
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
                </p>
              </div>
            );
          })}
        </div>

        {/* Additional Information */}
        <div className="mt-6 p-4 bg-gray-50 rounded">
          <p className="text-sm text-gray-600">
            <strong>Usage Reset:</strong> Usage limits reset at the beginning of each billing cycle.
            {subscription?.currentPeriodEnd && (
              <> Next reset: {new Date(subscription.currentPeriodEnd).toLocaleDateString()}</>
            )}
          </p>
        </div>

        {/* Upgrade Suggestion */}
        {hasWarnings && (
          <Message 
            severity="info" 
            text="Need more capacity? Upgrade to a higher plan for increased limits and additional features."
          />
        )}
      </div>
    </Card>
  );
};

export default UsageOverview;