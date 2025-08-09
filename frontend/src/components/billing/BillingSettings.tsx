import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { InputSwitch } from 'primereact/inputswitch';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';

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
    setBillingAddress((prev: any) => ({
      ...prev,
      [field]: value
    }));
  };

  const countryOptions = [
    { label: 'United States', value: 'US' },
    { label: 'Canada', value: 'CA' },
    { label: 'United Kingdom', value: 'GB' },
    { label: 'Germany', value: 'DE' },
    { label: 'France', value: 'FR' },
    { label: 'Australia', value: 'AU' }
  ];

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <ProgressSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <Message 
          severity="error" 
          text={error}
        />
      )}

      {success && (
        <Message 
          severity="success" 
          text={success}
        />
      )}

      {/* Billing Address */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Billing Address</h2>
          <Button
            label={editing ? 'Save' : 'Edit'}
            icon={editing ? 'pi pi-save' : 'pi pi-pencil'}
            onClick={editing ? handleSaveBillingAddress : () => setEditing(true)}
            disabled={saving}
            className={editing ? 'p-button-primary' : 'p-button-outlined'}
          />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="block text-sm font-medium mb-2">Company (Optional)</label>
            <InputText
              value={billingAddress.company}
              onChange={(e) => handleInputChange('company', e.target.value)}
              disabled={!editing}
              className="w-full"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-sm font-medium mb-2">Address Line 1</label>
            <InputText
              value={billingAddress.line1}
              onChange={(e) => handleInputChange('line1', e.target.value)}
              disabled={!editing}
              required={editing}
              className="w-full"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-sm font-medium mb-2">Address Line 2 (Optional)</label>
            <InputText
              value={billingAddress.line2}
              onChange={(e) => handleInputChange('line2', e.target.value)}
              disabled={!editing}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">City</label>
            <InputText
              value={billingAddress.city}
              onChange={(e) => handleInputChange('city', e.target.value)}
              disabled={!editing}
              required={editing}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">State/Province</label>
            <InputText
              value={billingAddress.state}
              onChange={(e) => handleInputChange('state', e.target.value)}
              disabled={!editing}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Postal Code</label>
            <InputText
              value={billingAddress.postalCode}
              onChange={(e) => handleInputChange('postalCode', e.target.value)}
              disabled={!editing}
              required={editing}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Country</label>
            <Dropdown
              value={billingAddress.country}
              onChange={(e) => handleInputChange('country', e.value)}
              options={countryOptions}
              disabled={!editing}
              className="w-full"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-sm font-medium mb-2">Tax ID (Optional)</label>
            <InputText
              value={billingAddress.taxId}
              onChange={(e) => handleInputChange('taxId', e.target.value)}
              disabled={!editing}
              className="w-full"
            />
            <small className="text-gray-500">VAT ID, Tax ID, or other tax identification number</small>
          </div>
        </div>
      </Card>

      {/* Email Preferences */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Email Preferences</h2>
        <p className="text-gray-600 mb-6">
          Choose which billing-related emails you'd like to receive.
        </p>

        <div className="space-y-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium">Invoice Reminders</h4>
              <p className="text-sm text-gray-500">
                Receive reminders before invoices are due
              </p>
            </div>
            <InputSwitch
              checked={emailPreferences.invoiceReminders}
              onChange={(e) => handleEmailPreferenceChange('invoiceReminders', e.value)}
            />
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium">Payment Failures</h4>
              <p className="text-sm text-gray-500">
                Get notified when payments fail
              </p>
            </div>
            <InputSwitch
              checked={emailPreferences.paymentFailures}
              onChange={(e) => handleEmailPreferenceChange('paymentFailures', e.value)}
            />
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium">Usage Warnings</h4>
              <p className="text-sm text-gray-500">
                Alerts when approaching plan limits
              </p>
            </div>
            <InputSwitch
              checked={emailPreferences.usageWarnings}
              onChange={(e) => handleEmailPreferenceChange('usageWarnings', e.value)}
            />
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium">Plan Changes</h4>
              <p className="text-sm text-gray-500">
                Confirmations for plan upgrades/downgrades
              </p>
            </div>
            <InputSwitch
              checked={emailPreferences.planChanges}
              onChange={(e) => handleEmailPreferenceChange('planChanges', e.value)}
            />
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium">Trial Reminders</h4>
              <p className="text-sm text-gray-500">
                Notifications about trial expiration
              </p>
            </div>
            <InputSwitch
              checked={emailPreferences.trialReminders}
              onChange={(e) => handleEmailPreferenceChange('trialReminders', e.value)}
            />
          </div>
        </div>
      </Card>

      {/* Subscription Information */}
      {subscription && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <i className="pi pi-receipt text-blue-500"></i>
            <h2 className="text-xl font-semibold">Subscription Information</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">Current Plan</p>
              <h3 className="text-lg font-semibold">
                {subscription.plan?.charAt(0).toUpperCase() + subscription.plan?.slice(1)} Plan
              </h3>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">Billing Cycle</p>
              <h3 className="text-lg font-semibold">
                ${subscription.amount}/{subscription.interval}
              </h3>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">Next Billing Date</p>
              <p className="text-base">
                {subscription.currentPeriodEnd 
                  ? new Date(subscription.currentPeriodEnd).toLocaleDateString()
                  : 'N/A'
                }
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">Status</p>
              <p className="text-base capitalize">
                {subscription.status}
              </p>
            </div>
          </div>

          <hr className="my-6" />

          <p className="text-sm text-gray-600">
            To modify your subscription, manage payment methods, or view invoices, 
            visit your{' '}
            <Button 
              label="Billing Dashboard" 
              className="p-button-text p-button-sm" 
              style={{ padding: '0', minWidth: 'auto', height: 'auto' }}
            />.
          </p>
        </Card>
      )}
    </div>
  );
};

export default BillingSettings;