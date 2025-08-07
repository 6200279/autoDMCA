import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Button,
  TextField,
  Grid,
  Alert,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  CircularProgress
} from '@mui/material';
import {
  Save,
  Edit,
  CreditCard,
  Receipt
} from '@mui/icons-material';

import { billingApi } from '../../services/api';

interface BillingSettingsProps {
  onRefresh?: () => void;
}

const BillingSettings: React.FC<BillingSettingsProps> = ({ onRefresh }) => {
  const [billingAddress, setBillingAddress] = useState<any>({
    company: '',
    line1: '',
    line2: '',
    city: '',
    state: '',
    postalCode: '',
    country: 'US',
    taxId: '',
    taxIdType: ''
  });
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Email preferences
  const [emailPreferences, setEmailPreferences] = useState({
    invoiceReminders: true,
    paymentFailures: true,
    usageWarnings: true,
    planChanges: true,
    trialReminders: true
  });

  const fetchBillingSettings = async () => {
    try {
      setLoading(true);
      const [subscriptionResponse, dashboardResponse] = await Promise.all([
        billingApi.getCurrentSubscription(),
        billingApi.getBillingDashboard()
      ]);

      setSubscription(subscriptionResponse.data);
      
      if (dashboardResponse.data.billingAddress) {
        setBillingAddress(dashboardResponse.data.billingAddress);
      }
    } catch (err: any) {
      setError('Failed to load billing settings');
      console.error('Billing settings error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBillingSettings();
  }, []);

  const handleSaveBillingAddress = async () => {
    try {
      setSaving(true);
      setError(null);

      // API call would go here to save billing address
      // await billingApi.updateBillingAddress(billingAddress);

      setSuccess('Billing address updated successfully');
      setEditing(false);
      
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update billing address');
    } finally {
      setSaving(false);
    }
  };

  const handleEmailPreferenceChange = async (preference: string, value: boolean) => {
    try {
      const updatedPreferences = {
        ...emailPreferences,
        [preference]: value
      };
      setEmailPreferences(updatedPreferences);

      // API call would go here to save email preferences
      // await billingApi.updateEmailPreferences(updatedPreferences);

      setSuccess('Email preferences updated');
    } catch (err: any) {
      setError('Failed to update email preferences');
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setBillingAddress(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ space: 3 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Billing Address */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Billing Address"
          action={
            <Button
              startIcon={editing ? <Save /> : <Edit />}
              onClick={editing ? handleSaveBillingAddress : () => setEditing(true)}
              disabled={saving}
              variant={editing ? 'contained' : 'outlined'}
            >
              {editing ? 'Save' : 'Edit'}
            </Button>
          }
        />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Company (Optional)"
                value={billingAddress.company}
                onChange={(e) => handleInputChange('company', e.target.value)}
                disabled={!editing}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Address Line 1"
                value={billingAddress.line1}
                onChange={(e) => handleInputChange('line1', e.target.value)}
                disabled={!editing}
                required={editing}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Address Line 2 (Optional)"
                value={billingAddress.line2}
                onChange={(e) => handleInputChange('line2', e.target.value)}
                disabled={!editing}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="City"
                value={billingAddress.city}
                onChange={(e) => handleInputChange('city', e.target.value)}
                disabled={!editing}
                required={editing}
              />
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="State/Province"
                value={billingAddress.state}
                onChange={(e) => handleInputChange('state', e.target.value)}
                disabled={!editing}
              />
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Postal Code"
                value={billingAddress.postalCode}
                onChange={(e) => handleInputChange('postalCode', e.target.value)}
                disabled={!editing}
                required={editing}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth disabled={!editing}>
                <InputLabel>Country</InputLabel>
                <Select
                  value={billingAddress.country}
                  onChange={(e) => handleInputChange('country', e.target.value)}
                  label="Country"
                >
                  <MenuItem value="US">United States</MenuItem>
                  <MenuItem value="CA">Canada</MenuItem>
                  <MenuItem value="GB">United Kingdom</MenuItem>
                  <MenuItem value="DE">Germany</MenuItem>
                  <MenuItem value="FR">France</MenuItem>
                  <MenuItem value="AU">Australia</MenuItem>
                  {/* Add more countries as needed */}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Tax ID (Optional)"
                value={billingAddress.taxId}
                onChange={(e) => handleInputChange('taxId', e.target.value)}
                disabled={!editing}
                helperText="VAT ID, Tax ID, or other tax identification number"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Email Preferences */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="Email Preferences" />
        <CardContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Choose which billing-related emails you'd like to receive.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={emailPreferences.invoiceReminders}
                  onChange={(e) => handleEmailPreferenceChange('invoiceReminders', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Invoice Reminders</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Receive reminders before invoices are due
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={emailPreferences.paymentFailures}
                  onChange={(e) => handleEmailPreferenceChange('paymentFailures', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Payment Failures</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Get notified when payments fail
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={emailPreferences.usageWarnings}
                  onChange={(e) => handleEmailPreferenceChange('usageWarnings', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Usage Warnings</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Alerts when approaching plan limits
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={emailPreferences.planChanges}
                  onChange={(e) => handleEmailPreferenceChange('planChanges', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Plan Changes</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Confirmations for plan upgrades/downgrades
                  </Typography>
                </Box>
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={emailPreferences.trialReminders}
                  onChange={(e) => handleEmailPreferenceChange('trialReminders', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Trial Reminders</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Notifications about trial expiration
                  </Typography>
                </Box>
              }
            />
          </Box>
        </CardContent>
      </Card>

      {/* Subscription Information */}
      {subscription && (
        <Card>
          <CardHeader
            title="Subscription Information"
            avatar={<Receipt />}
          />
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Current Plan
                </Typography>
                <Typography variant="h6">
                  {subscription.plan?.charAt(0).toUpperCase() + subscription.plan?.slice(1)} Plan
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Billing Cycle
                </Typography>
                <Typography variant="h6">
                  ${subscription.amount}/{subscription.interval}
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Next Billing Date
                </Typography>
                <Typography variant="body1">
                  {subscription.currentPeriodEnd 
                    ? new Date(subscription.currentPeriodEnd).toLocaleDateString()
                    : 'N/A'
                  }
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                  {subscription.status}
                </Typography>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Typography variant="body2" color="text.secondary" paragraph>
              To modify your subscription, manage payment methods, or view invoices, 
              visit your <Button variant="text" size="small">Billing Dashboard</Button>.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default BillingSettings;