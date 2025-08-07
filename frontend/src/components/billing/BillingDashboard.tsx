import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Grid,
  Typography,
  Button,
  LinearProgress,
  Alert,
  Chip,
  Divider
} from '@mui/material';
import {
  CreditCard,
  Receipt,
  TrendingUp,
  Settings,
  Warning,
  CheckCircle
} from '@mui/icons-material';
import { format } from 'date-fns';

import { billingApi } from '../../services/api';
import SubscriptionCard from './SubscriptionCard';
import UsageOverview from './UsageOverview';
import PaymentMethods from './PaymentMethods';
import InvoiceHistory from './InvoiceHistory';
import PlanUpgradeModal from './PlanUpgradeModal';

interface BillingDashboardData {
  subscription: any;
  currentUsage: any;
  usageLimits: any;
  upcomingInvoice: any;
  paymentMethods: any[];
  billingAddress: any;
  recentInvoices: any[];
}

const BillingDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<BillingDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await billingApi.getBillingDashboard();
      setDashboardData(response.data);
      setError(null);
    } catch (err: any) {
      setError('Failed to load billing dashboard');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'success';
      case 'trialing':
        return 'info';
      case 'past_due':
        return 'warning';
      case 'canceled':
        return 'error';
      default:
        return 'default';
    }
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    return 'primary';
  };

  const calculateUsagePercentage = (current: number, limit: number) => {
    return limit > 0 ? Math.min(100, (current / limit) * 100) : 0;
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
          Loading billing dashboard...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
        <Button onClick={fetchDashboardData} sx={{ ml: 2 }}>
          Retry
        </Button>
      </Alert>
    );
  }

  const { subscription, currentUsage, usageLimits, upcomingInvoice, recentInvoices } = dashboardData || {};

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Billing & Subscription
      </Typography>

      <Grid container spacing={3}>
        {/* Current Subscription */}
        <Grid item xs={12} md={8}>
          <SubscriptionCard
            subscription={subscription}
            onUpgrade={() => setUpgradeModalOpen(true)}
            onRefresh={fetchDashboardData}
          />
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12} md={4}>
          <Grid container spacing={2}>
            {/* Next Billing Date */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Receipt sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="subtitle2">Next Billing</Typography>
                  </Box>
                  {subscription?.currentPeriodEnd ? (
                    <Typography variant="h6">
                      {format(new Date(subscription.currentPeriodEnd), 'MMM dd, yyyy')}
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No active subscription
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Monthly Cost */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <TrendingUp sx={{ mr: 1, color: 'success.main' }} />
                    <Typography variant="subtitle2">Monthly Cost</Typography>
                  </Box>
                  <Typography variant="h6">
                    ${subscription?.amount || '0.00'}/{subscription?.interval || 'month'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Usage Overview */}
        <Grid item xs={12}>
          <UsageOverview
            currentUsage={currentUsage}
            usageLimits={usageLimits}
            subscription={subscription}
          />
        </Grid>

        {/* Upcoming Invoice */}
        {upcomingInvoice && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader
                title="Upcoming Invoice"
                avatar={<Receipt />}
              />
              <CardContent>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Amount Due: <strong>${upcomingInvoice.total}</strong>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Due Date: {format(new Date(upcomingInvoice.dueDate), 'MMM dd, yyyy')}
                  </Typography>
                </Box>
                <Divider sx={{ my: 1 }} />
                <Typography variant="body2">
                  {upcomingInvoice.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Payment Methods */}
        <Grid item xs={12} md={upcomingInvoice ? 6 : 12}>
          <PaymentMethods onRefresh={fetchDashboardData} />
        </Grid>

        {/* Recent Invoices */}
        <Grid item xs={12}>
          <InvoiceHistory
            invoices={recentInvoices}
            showAll={false}
            onRefresh={fetchDashboardData}
          />
        </Grid>
      </Grid>

      {/* Plan Upgrade Modal */}
      <PlanUpgradeModal
        open={upgradeModalOpen}
        onClose={() => setUpgradeModalOpen(false)}
        currentPlan={subscription?.plan}
        onUpgradeComplete={fetchDashboardData}
      />
    </Box>
  );
};

export default BillingDashboard;