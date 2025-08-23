import api from './api';

export interface AddonService {
  id: number;
  name: string;
  service_type: string;
  description: string;
  price_monthly?: number;
  price_one_time?: number;
  is_recurring: boolean;
  features?: string;
}

export interface UserAddonSubscription {
  id: number;
  addon_service: AddonService;
  status: string;
  quantity: number;
  current_period_start?: string;
  current_period_end?: string;
  activated_at: string;
}

export interface AddonUsage {
  addon_type: string;
  has_addon: boolean;
  limit: number;
  used: number;
  remaining: number;
}

export interface AddonSubscribeRequest {
  addon_service_id: number;
  quantity?: number;
  payment_method_id?: string;
}

export interface ExtraProfileInfo {
  base_profiles: number;
  extra_profiles: number;
  total_available: number;
  currently_used: number;
  can_add_more: boolean;
}

class AddonServiceAPI {
  /**
   * Get all available add-on services
   */
  async getAvailableAddons(): Promise<AddonService[]> {
    const response = await api.get('/addons/available');
    return response.data;
  }

  /**
   * Get user's current add-on subscriptions
   */
  async getMyAddons(): Promise<UserAddonSubscription[]> {
    const response = await api.get('/addons/my-addons');
    return response.data;
  }

  /**
   * Subscribe to an add-on service
   */
  async subscribeToAddon(request: AddonSubscribeRequest): Promise<{
    success: boolean;
    subscription_id?: number;
    stripe_subscription_id?: string;
    payment_intent_id?: string;
    client_secret?: string;
  }> {
    const response = await api.post('/addons/subscribe', request);
    return response.data;
  }

  /**
   * Cancel an add-on subscription
   */
  async cancelAddon(subscriptionId: number): Promise<{ message: string }> {
    const response = await api.post(`/addons/cancel/${subscriptionId}`);
    return response.data;
  }

  /**
   * Get usage statistics for an add-on type
   */
  async getAddonUsage(addonType: string): Promise<AddonUsage> {
    const response = await api.get(`/addons/usage/${addonType}`);
    return response.data;
  }

  /**
   * Get extra profile availability information
   */
  async getExtraProfileInfo(): Promise<ExtraProfileInfo> {
    const response = await api.get('/addons/extra-profiles/available');
    return response.data;
  }

  /**
   * Format addon features from JSON string
   */
  parseFeatures(featuresJson?: string): string[] {
    if (!featuresJson) return [];
    
    try {
      return JSON.parse(featuresJson);
    } catch {
      return [];
    }
  }

  /**
   * Get display price for addon
   */
  getDisplayPrice(addon: AddonService): string {
    if (addon.is_recurring && addon.price_monthly) {
      return `$${addon.price_monthly.toFixed(0)}/month`;
    } else if (!addon.is_recurring && addon.price_one_time) {
      return `$${addon.price_one_time.toFixed(0)} one-time`;
    }
    return 'Contact us';
  }

  /**
   * Get addon type display name
   */
  getAddonTypeDisplayName(serviceType: string): string {
    switch (serviceType) {
      case 'extra_profile':
        return 'Extra Profile';
      case 'copyright_registration':
        return 'Copyright Registration';
      case 'priority_takedown':
        return 'Priority Takedown';
      case 'custom_branding':
        return 'Custom Branding';
      case 'api_access':
        return 'API Access';
      case 'bulk_monitoring':
        return 'Bulk Monitoring';
      default:
        return serviceType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  }

  /**
   * Get status display info
   */
  getStatusInfo(status: string): { label: string; severity: 'success' | 'info' | 'warning' | 'danger' } {
    switch (status.toLowerCase()) {
      case 'active':
        return { label: 'Active', severity: 'success' };
      case 'inactive':
        return { label: 'Inactive', severity: 'warning' };
      case 'suspended':
        return { label: 'Suspended', severity: 'danger' };
      case 'cancelled':
        return { label: 'Cancelled', severity: 'info' };
      default:
        return { label: status, severity: 'info' };
    }
  }

  /**
   * Calculate next billing date
   */
  getNextBillingDate(subscription: UserAddonSubscription): Date | null {
    if (!subscription.current_period_end) return null;
    return new Date(subscription.current_period_end);
  }

  /**
   * Check if subscription is expiring soon (within 7 days)
   */
  isExpiringSoon(subscription: UserAddonSubscription): boolean {
    const nextBilling = this.getNextBillingDate(subscription);
    if (!nextBilling) return false;
    
    const daysDiff = Math.ceil((nextBilling.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return daysDiff <= 7 && daysDiff > 0;
  }

  /**
   * Get usage percentage for display
   */
  getUsagePercentage(usage: AddonUsage): number {
    if (usage.limit === 0) return 0;
    if (usage.limit === -1) return 0; // Unlimited
    return Math.round((usage.used / usage.limit) * 100);
  }

  /**
   * Get usage status color
   */
  getUsageStatusColor(usage: AddonUsage): 'success' | 'warning' | 'danger' {
    const percentage = this.getUsagePercentage(usage);
    if (percentage < 70) return 'success';
    if (percentage < 90) return 'warning';
    return 'danger';
  }
}

export const addonService = new AddonServiceAPI();