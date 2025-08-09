import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { ProgressBar } from 'primereact/progressbar';
import { Message } from 'primereact/message';
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


  if (loading) {
    return (
      <div className="w-full mt-2">
        <ProgressBar mode="indeterminate" className="h-1" />
        <p className="text-center text-sm text-gray-600 mt-2">
          Loading billing dashboard...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <Message 
        severity="error" 
        text={error}
        className="mt-2"
        content={
          <div className="flex justify-between items-center w-full">
            <span>{error}</span>
            <Button 
              label="Retry" 
              size="small" 
              onClick={fetchDashboardData}
              className="ml-2"
            />
          </div>
        }
      />
    );
  }

  const { subscription, currentUsage, usageLimits, upcomingInvoice, recentInvoices } = dashboardData || {};

  return (
    <div className="flex-1 p-6">
      <h1 className="text-3xl font-bold mb-6">Billing & Subscription</h1>

      <div className="grid grid-cols-1 gap-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Current Subscription */}
          <div className="lg:col-span-2">
            <SubscriptionCard
              subscription={subscription}
              onUpgrade={() => setUpgradeModalOpen(true)}
              onRefresh={fetchDashboardData}
            />
          </div>

          {/* Quick Stats */}
          <div className="space-y-4">
            {/* Next Billing Date */}
            <Card className="p-4">
              <div className="flex items-center mb-3">
                <i className="pi pi-receipt text-blue-500 mr-2"></i>
                <span className="font-semibold text-sm">Next Billing</span>
              </div>
              {subscription?.currentPeriodEnd ? (
                <h3 className="text-lg font-bold">
                  {format(new Date(subscription.currentPeriodEnd), 'MMM dd, yyyy')}
                </h3>
              ) : (
                <p className="text-gray-500 text-sm">
                  No active subscription
                </p>
              )}
            </Card>

            {/* Monthly Cost */}
            <Card className="p-4">
              <div className="flex items-center mb-3">
                <i className="pi pi-chart-line text-green-500 mr-2"></i>
                <span className="font-semibold text-sm">Monthly Cost</span>
              </div>
              <h3 className="text-lg font-bold">
                ${subscription?.amount || '0.00'}/{subscription?.interval || 'month'}
              </h3>
            </Card>
          </div>
        </div>

        {/* Usage Overview */}
        <UsageOverview
          currentUsage={currentUsage}
          usageLimits={usageLimits}
          subscription={subscription}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upcoming Invoice */}
          {upcomingInvoice && (
            <Card
              title="Upcoming Invoice"
              className="h-fit"
              pt={{
                title: { className: "flex items-center gap-2" },
                content: { className: "pt-0" }
              }}
            >
              <div className="flex items-center gap-2 mb-4">
                <i className="pi pi-receipt text-blue-500"></i>
                <h3 className="font-semibold">Upcoming Invoice</h3>
              </div>
              <div className="space-y-2 mb-4">
                <p className="text-gray-600 text-sm">
                  Amount Due: <strong>${upcomingInvoice.total}</strong>
                </p>
                <p className="text-gray-600 text-sm">
                  Due Date: {format(new Date(upcomingInvoice.dueDate), 'MMM dd, yyyy')}
                </p>
              </div>
              <hr className="my-3" />
              <p className="text-sm">
                {upcomingInvoice.description}
              </p>
            </Card>
          )}

          {/* Payment Methods */}
          <div className={upcomingInvoice ? "" : "lg:col-span-2"}>
            <PaymentMethods onRefresh={fetchDashboardData} />
          </div>
        </div>

        {/* Recent Invoices */}
        <InvoiceHistory
          invoices={recentInvoices || []}
          showAll={false}
          onRefresh={fetchDashboardData}
        />
      </div>

      {/* Plan Upgrade Modal */}
      <PlanUpgradeModal
        open={upgradeModalOpen}
        onClose={() => setUpgradeModalOpen(false)}
        currentPlan={subscription?.plan}
        onUpgradeComplete={fetchDashboardData}
      />
    </div>
  );
};

export default BillingDashboard;