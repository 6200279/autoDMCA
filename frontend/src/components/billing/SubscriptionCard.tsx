import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
import { Dialog } from 'primereact/dialog';
import { InputTextarea } from 'primereact/inputtextarea';
// import { ProgressSpinner } from 'primereact/progressspinner';
import { format } from 'date-fns';

import { billingApi } from '../../services/api';

interface SubscriptionCardProps {
  subscription: any;
  onUpgrade: () => void;
  onRefresh: () => void;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscription,
  onUpgrade,
  onRefresh
}) => {
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancellationReason, setCancellationReason] = useState('');
  const [cancelling, setCancelling] = useState(false);
  const [reactivating, setReactivating] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'success';
      case 'trialing':
        return 'info';
      case 'past_due':
        return 'warning';
      case 'canceled':
        return 'danger';
      default:
        return null;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'pi pi-check-circle';
      case 'trialing':
        return 'pi pi-star';
      case 'past_due':
        return 'pi pi-exclamation-triangle';
      case 'canceled':
        return 'pi pi-times-circle';
      default:
        return null;
    }
  };

  const getPlanDisplayName = (plan: string) => {
    switch (plan?.toLowerCase()) {
      case 'basic':
        return 'Basic Plan';
      case 'professional':
        return 'Professional Plan';
      case 'enterprise':
        return 'Enterprise Plan';
      default:
        return 'Free Plan';
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setCancelling(true);
      await billingApi.cancelSubscription({
        atPeriodEnd: true,
        cancellationReason
      });
      setCancelDialogOpen(false);
      setCancellationReason('');
      onRefresh();
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
    } finally {
      setCancelling(false);
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      setReactivating(true);
      await billingApi.reactivateSubscription();
      onRefresh();
    } catch (error) {
      console.error('Failed to reactivate subscription:', error);
    } finally {
      setReactivating(false);
    }
  };

  if (!subscription) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-3">
          No Active Subscription
        </h2>
        <p className="text-gray-600 mb-4">
          You're currently on the free plan with limited features.
        </p>
        <Button
          label="Upgrade Now"
          icon="pi pi-star"
          onClick={onUpgrade}
          className="p-button-primary"
        />
      </Card>
    );
  }

  const isTrialing = subscription.status === 'trialing';
  const isCanceled = subscription.status === 'canceled';
  const isPastDue = subscription.status === 'past_due';

  const statusIconClass = getStatusIcon(subscription.status);

  return (
    <>
      <Card className="p-6">
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-xl font-semibold">
              {getPlanDisplayName(subscription.plan)}
            </h2>
            <Tag
              icon={statusIconClass}
              value={subscription.status?.toUpperCase()}
              severity={getStatusColor(subscription.status)}
            />
          </div>
          <p className="text-gray-600 text-sm">
            ${subscription.amount}/{subscription.interval}
          </p>
        </div>
        
        <div className="space-y-4">
          {/* Trial Notice */}
          {isTrialing && subscription.trialEnd && (
            <Message 
              severity="info" 
              text={
                <div>
                  <strong>Trial Period</strong>
                  <br />
                  Your trial ends on {format(new Date(subscription.trialEnd), 'MMM dd, yyyy')}
                </div>
              }
            />
          )}

          {/* Past Due Notice */}
          {isPastDue && (
            <Message 
              severity="warn" 
              text={
                <div>
                  <strong>Payment Past Due</strong>
                  <br />
                  Please update your payment method to continue service.
                </div>
              }
            />
          )}

          {/* Cancellation Notice */}
          {isCanceled && subscription.endsAt && (
            <Message 
              severity="error" 
              text={
                <div>
                  <strong>Subscription Canceled</strong>
                  <br />
                  Your subscription will end on {format(new Date(subscription.endsAt), 'MMM dd, yyyy')}
                </div>
              }
            />
          )}

          {/* Billing Information */}
          <div className="space-y-2">
            <p className="text-sm text-gray-600">
              <strong>Current Period:</strong>{' '}
              {subscription.currentPeriodStart && subscription.currentPeriodEnd
                ? `${format(new Date(subscription.currentPeriodStart), 'MMM dd')} - ${format(new Date(subscription.currentPeriodEnd), 'MMM dd, yyyy')}`
                : 'N/A'}
            </p>
            
            {subscription.stripeCustomerId && (
              <p className="text-sm text-gray-600">
                <strong>Customer ID:</strong> {subscription.stripeCustomerId}
              </p>
            )}
          </div>

          {/* Plan Features */}
          <div>
            <h4 className="font-semibold text-sm mb-2">Plan Features:</h4>
            <div className="flex flex-wrap gap-2">
              <Tag
                value={`${subscription.maxProtectedProfiles} Protected Profile${subscription.maxProtectedProfiles > 1 ? 's' : ''}`}
                className="p-tag-outlined"
              />
              <Tag
                value={`${subscription.maxMonthlyScans} Monthly Scans`}
                className="p-tag-outlined"
              />
              <Tag
                value={`${subscription.maxTakedownRequests} Takedown Requests`}
                className="p-tag-outlined"
              />
              {subscription.aiFaceRecognition && (
                <Tag value="AI Face Recognition" severity="info" className="p-tag-outlined" />
              )}
              {subscription.prioritySupport && (
                <Tag value="Priority Support" severity="info" className="p-tag-outlined" />
              )}
              {subscription.customBranding && (
                <Tag value="Custom Branding" severity="info" className="p-tag-outlined" />
              )}
              {subscription.apiAccess && (
                <Tag value="API Access" severity="info" className="p-tag-outlined" />
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          {!isCanceled && (
            <Button
              label={subscription.plan === 'basic' ? 'Upgrade Plan' : 'Change Plan'}
              icon="pi pi-star"
              onClick={onUpgrade}
              className="p-button-primary"
            />
          )}

          {!isCanceled && (
            <Button
              label="Cancel"
              icon="pi pi-times"
              onClick={() => setCancelDialogOpen(true)}
              className="p-button-outlined p-button-danger"
            />
          )}

          {isCanceled && (
            <Button
              label="Reactivate"
              icon={reactivating ? "pi pi-spin pi-spinner" : "pi pi-refresh"}
              onClick={handleReactivateSubscription}
              disabled={reactivating}
              className="p-button-primary"
            />
          )}
        </div>
      </Card>

      {/* Cancel Subscription Dialog */}
      <Dialog
        header="Cancel Subscription"
        visible={cancelDialogOpen}
        onHide={() => setCancelDialogOpen(false)}
        style={{ width: '450px' }}
        footer={
          <div className="flex justify-end gap-2">
            <Button 
              label="Keep Subscription" 
              outlined
              onClick={() => setCancelDialogOpen(false)}
            />
            <Button
              label="Cancel Subscription"
              icon={cancelling ? "pi pi-spin pi-spinner" : "pi pi-times"}
              onClick={handleCancelSubscription}
              disabled={cancelling}
              severity="danger"
            />
          </div>
        }
      >
        <p className="mb-4">
          Are you sure you want to cancel your subscription? You'll continue to have access
          until the end of your current billing period.
        </p>
        
        <InputTextarea
          value={cancellationReason}
          onChange={(e) => setCancellationReason(e.target.value)}
          placeholder="Help us improve by letting us know why you're canceling..."
          rows={3}
          className="w-full"
        />
      </Dialog>
    </>
  );
};

export default SubscriptionCard;