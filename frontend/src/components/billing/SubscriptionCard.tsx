import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Box,
  Typography,
  Button,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress
} from '@mui/material';
import {
  Star,
  Cancel,
  Refresh,
  Warning,
  CheckCircle
} from '@mui/icons-material';
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
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <CheckCircle />;
      case 'trialing':
        return <Star />;
      case 'past_due':
        return <Warning />;
      case 'canceled':
        return <Cancel />;
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
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            No Active Subscription
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            You're currently on the free plan with limited features.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={onUpgrade}
            startIcon={<Star />}
          >
            Upgrade Now
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isTrialing = subscription.status === 'trialing';
  const isCanceled = subscription.status === 'canceled';
  const isPastDue = subscription.status === 'past_due';

  return (
    <>
      <Card>
        <CardHeader
          title={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">
                {getPlanDisplayName(subscription.plan)}
              </Typography>
              <Chip
                icon={getStatusIcon(subscription.status)}
                label={subscription.status?.toUpperCase()}
                color={getStatusColor(subscription.status)}
                size="small"
              />
            </Box>
          }
          subheader={
            <Typography variant="body2" color="text.secondary">
              ${subscription.amount}/{subscription.interval}
            </Typography>
          }
        />
        
        <CardContent>
          {/* Trial Notice */}
          {isTrialing && subscription.trialEnd && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Trial Period</strong>
                <br />
                Your trial ends on {format(new Date(subscription.trialEnd), 'MMM dd, yyyy')}
              </Typography>
            </Alert>
          )}

          {/* Past Due Notice */}
          {isPastDue && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Payment Past Due</strong>
                <br />
                Please update your payment method to continue service.
              </Typography>
            </Alert>
          )}

          {/* Cancellation Notice */}
          {isCanceled && subscription.endsAt && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Subscription Canceled</strong>
                <br />
                Your subscription will end on {format(new Date(subscription.endsAt), 'MMM dd, yyyy')}
              </Typography>
            </Alert>
          )}

          {/* Billing Information */}
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Current Period:</strong>{' '}
              {subscription.currentPeriodStart && subscription.currentPeriodEnd
                ? `${format(new Date(subscription.currentPeriodStart), 'MMM dd')} - ${format(new Date(subscription.currentPeriodEnd), 'MMM dd, yyyy')}`
                : 'N/A'}
            </Typography>
            
            {subscription.stripeCustomerId && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                <strong>Customer ID:</strong> {subscription.stripeCustomerId}
              </Typography>
            )}
          </Box>

          {/* Plan Features */}
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Plan Features:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              <Chip
                label={`${subscription.maxProtectedProfiles} Protected Profile${subscription.maxProtectedProfiles > 1 ? 's' : ''}`}
                size="small"
                variant="outlined"
              />
              <Chip
                label={`${subscription.maxMonthlyScans} Monthly Scans`}
                size="small"
                variant="outlined"
              />
              <Chip
                label={`${subscription.maxTakedownRequests} Takedown Requests`}
                size="small"
                variant="outlined"
              />
              {subscription.aiFaceRecognition && (
                <Chip label="AI Face Recognition" size="small" variant="outlined" color="primary" />
              )}
              {subscription.prioritySupport && (
                <Chip label="Priority Support" size="small" variant="outlined" color="primary" />
              )}
              {subscription.customBranding && (
                <Chip label="Custom Branding" size="small" variant="outlined" color="primary" />
              )}
              {subscription.apiAccess && (
                <Chip label="API Access" size="small" variant="outlined" color="primary" />
              )}
            </Box>
          </Box>
        </CardContent>

        <CardActions>
          {!isCanceled && (
            <Button
              variant="contained"
              color="primary"
              onClick={onUpgrade}
              startIcon={<Star />}
            >
              {subscription.plan === 'basic' ? 'Upgrade Plan' : 'Change Plan'}
            </Button>
          )}

          {!isCanceled && (
            <Button
              variant="outlined"
              color="error"
              onClick={() => setCancelDialogOpen(true)}
              startIcon={<Cancel />}
            >
              Cancel
            </Button>
          )}

          {isCanceled && (
            <Button
              variant="contained"
              color="primary"
              onClick={handleReactivateSubscription}
              disabled={reactivating}
              startIcon={reactivating ? <CircularProgress size={16} /> : <Refresh />}
            >
              Reactivate
            </Button>
          )}
        </CardActions>
      </Card>

      {/* Cancel Subscription Dialog */}
      <Dialog
        open={cancelDialogOpen}
        onClose={() => setCancelDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Cancel Subscription</DialogTitle>
        <DialogContent>
          <Typography variant="body1" paragraph>
            Are you sure you want to cancel your subscription? You'll continue to have access
            until the end of your current billing period.
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Reason for cancellation (optional)"
            value={cancellationReason}
            onChange={(e) => setCancellationReason(e.target.value)}
            placeholder="Help us improve by letting us know why you're canceling..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>
            Keep Subscription
          </Button>
          <Button
            onClick={handleCancelSubscription}
            color="error"
            disabled={cancelling}
            startIcon={cancelling ? <CircularProgress size={16} /> : <Cancel />}
          >
            Cancel Subscription
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default SubscriptionCard;