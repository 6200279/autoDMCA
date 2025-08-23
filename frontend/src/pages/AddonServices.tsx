import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { Divider } from 'primereact/divider';
import { ProgressBar } from 'primereact/progressbar';
import { TabView, TabPanel } from 'primereact/tabview';
import { Message } from 'primereact/message';
import { Panel } from 'primereact/panel';
import { Skeleton } from 'primereact/skeleton';
import { confirmDialog, ConfirmDialog } from 'primereact/confirmdialog';
import { 
  addonService, 
  AddonService, 
  UserAddonSubscription, 
  AddonUsage,
  ExtraProfileInfo 
} from '../services/addonService';

const AddonServices: React.FC = () => {
  const toast = useRef<Toast>(null);
  const [loading, setLoading] = useState(true);
  const [availableAddons, setAvailableAddons] = useState<AddonService[]>([]);
  const [myAddons, setMyAddons] = useState<UserAddonSubscription[]>([]);
  const [extraProfileInfo, setExtraProfileInfo] = useState<ExtraProfileInfo | null>(null);
  const [selectedAddon, setSelectedAddon] = useState<AddonService | null>(null);
  const [showPurchaseDialog, setShowPurchaseDialog] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [addons, userAddons, profileInfo] = await Promise.all([
        addonService.getAvailableAddons(),
        addonService.getMyAddons(),
        addonService.getExtraProfileInfo().catch(() => null)
      ]);

      setAvailableAddons(addons);
      setMyAddons(userAddons);
      setExtraProfileInfo(profileInfo);
    } catch (error) {
      console.error('Error loading add-on data:', error);
      showError('Failed to load add-on services');
    } finally {
      setLoading(false);
    }
  };

  const showSuccess = (message: string) => {
    toast.current?.show({ severity: 'success', summary: 'Success', detail: message });
  };

  const showError = (message: string) => {
    toast.current?.show({ severity: 'error', summary: 'Error', detail: message });
  };

  const showInfo = (message: string) => {
    toast.current?.show({ severity: 'info', summary: 'Info', detail: message });
  };

  const handlePurchaseAddon = (addon: AddonService) => {
    setSelectedAddon(addon);
    setShowPurchaseDialog(true);
  };

  const confirmPurchase = async () => {
    if (!selectedAddon) return;

    try {
      setPurchasing(true);
      
      // For now, show info message about coming soon
      showInfo(`${selectedAddon.name} will be available soon! You'll be notified when it's ready.`);
      
      // TODO: Implement actual Stripe payment flow
      // const result = await addonService.subscribeToAddon({
      //   addon_service_id: selectedAddon.id,
      //   quantity: 1
      // });
      
      setShowPurchaseDialog(false);
      setSelectedAddon(null);
    } catch (error) {
      showError('Failed to purchase add-on service');
    } finally {
      setPurchasing(false);
    }
  };

  const handleCancelAddon = async (subscription: UserAddonSubscription) => {
    confirmDialog({
      message: `Are you sure you want to cancel your ${subscription.addon_service.name} subscription?`,
      header: 'Cancel Add-on',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await addonService.cancelAddon(subscription.id);
          showSuccess('Add-on subscription cancelled successfully');
          loadData(); // Reload data
        } catch (error) {
          showError('Failed to cancel add-on subscription');
        }
      }
    });
  };

  const renderAvailableAddons = () => {
    if (loading) {
      return (
        <div className="grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="col-12 md:col-6 lg:col-4 mb-4">
              <Card>
                <Skeleton width="100%" height="200px" />
              </Card>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="grid">
        {availableAddons.map(addon => {
          const features = addonService.parseFeatures(addon.features);
          const isSubscribed = myAddons.some(sub => sub.addon_service.id === addon.id);
          
          return (
            <div key={addon.id} className="col-12 md:col-6 lg:col-4 mb-4">
              <Card className="h-full">
                <div className="flex flex-column h-full">
                  <div className="flex align-items-center justify-content-between mb-3">
                    <h4 className="m-0">{addon.name}</h4>
                    <Tag 
                      value={addonService.getDisplayPrice(addon)} 
                      severity={addon.is_recurring ? "success" : "info"} 
                    />
                  </div>
                  
                  <p className="text-600 mb-3 flex-1">{addon.description}</p>
                  
                  {features.length > 0 && (
                    <div className="mb-4">
                      <ul className="list-none p-0 m-0">
                        {features.slice(0, 3).map((feature, index) => (
                          <li key={index} className="flex align-items-center mb-1">
                            <i className="pi pi-check text-green-500 mr-2 text-sm" />
                            <span className="text-sm">{feature}</span>
                          </li>
                        ))}
                        {features.length > 3 && (
                          <li className="text-sm text-600">
                            +{features.length - 3} more features
                          </li>
                        )}
                      </ul>
                    </div>
                  )}
                  
                  <div className="mt-auto">
                    {isSubscribed ? (
                      <Button
                        label="Subscribed"
                        icon="pi pi-check"
                        disabled
                        className="w-full"
                        severity="success"
                      />
                    ) : (
                      <Button
                        label={addon.is_recurring ? "Subscribe" : "Purchase"}
                        icon={addon.is_recurring ? "pi pi-refresh" : "pi pi-shopping-cart"}
                        className="w-full"
                        onClick={() => handlePurchaseAddon(addon)}
                      />
                    )}
                  </div>
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    );
  };

  const renderMyAddons = () => {
    if (loading) {
      return <Skeleton width="100%" height="300px" />;
    }

    if (myAddons.length === 0) {
      return (
        <Message 
          severity="info" 
          text="You don't have any active add-on services. Browse available add-ons to enhance your account." 
        />
      );
    }

    return (
      <div className="grid">
        {myAddons.map(subscription => {
          const statusInfo = addonService.getStatusInfo(subscription.status);
          const nextBilling = addonService.getNextBillingDate(subscription);
          const isExpiring = addonService.isExpiringSoon(subscription);
          
          return (
            <div key={subscription.id} className="col-12 md:col-6 mb-4">
              <Card>
                <div className="flex justify-content-between align-items-start mb-3">
                  <div>
                    <h4 className="m-0 mb-1">{subscription.addon_service.name}</h4>
                    <p className="text-600 m-0">{subscription.addon_service.description}</p>
                  </div>
                  <Tag 
                    value={statusInfo.label} 
                    severity={statusInfo.severity} 
                  />
                </div>
                
                <div className="grid mb-3">
                  <div className="col-6">
                    <span className="font-semibold">Quantity:</span>
                    <div className="mt-1">
                      <Badge value={subscription.quantity} size="large" />
                    </div>
                  </div>
                  <div className="col-6">
                    <span className="font-semibold">Price:</span>
                    <div className="mt-1 text-lg font-bold">
                      {addonService.getDisplayPrice(subscription.addon_service)}
                    </div>
                  </div>
                </div>
                
                {nextBilling && (
                  <div className="mb-3">
                    <span className="font-semibold">Next billing:</span>
                    <div className="mt-1">
                      {nextBilling.toLocaleDateString()}
                      {isExpiring && (
                        <Tag 
                          value="Expiring Soon" 
                          severity="warning" 
                          className="ml-2" 
                        />
                      )}
                    </div>
                  </div>
                )}
                
                <div className="flex gap-2">
                  <Button
                    label="Cancel"
                    icon="pi pi-times"
                    severity="danger"
                    size="small"
                    onClick={() => handleCancelAddon(subscription)}
                  />
                  <Button
                    label="Manage"
                    icon="pi pi-cog"
                    severity="secondary"
                    size="small"
                    onClick={() => showInfo('Addon management coming soon!')}
                  />
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    );
  };

  const renderUsagePanel = () => {
    if (!extraProfileInfo) {
      return (
        <Message 
          severity="info" 
          text="Usage information is not available at this time." 
        />
      );
    }

    const usagePercentage = extraProfileInfo.total_available > 0 
      ? Math.round((extraProfileInfo.currently_used / extraProfileInfo.total_available) * 100)
      : 0;

    return (
      <div className="grid">
        <div className="col-12 md:col-6">
          <Panel header="Profile Usage" className="mb-4">
            <div className="mb-3">
              <div className="flex justify-content-between mb-2">
                <span>Profiles Used</span>
                <span>{extraProfileInfo.currently_used} / {extraProfileInfo.total_available === -1 ? '∞' : extraProfileInfo.total_available}</span>
              </div>
              {extraProfileInfo.total_available > 0 && (
                <ProgressBar 
                  value={usagePercentage}
                  color={usagePercentage > 80 ? '#e74c3c' : usagePercentage > 60 ? '#f39c12' : '#27ae60'}
                />
              )}
            </div>
            
            <div className="grid text-center">
              <div className="col-6">
                <div className="text-2xl font-bold text-blue-500">
                  {extraProfileInfo.base_profiles}
                </div>
                <div className="text-sm text-600">Base Profiles</div>
              </div>
              <div className="col-6">
                <div className="text-2xl font-bold text-green-500">
                  +{extraProfileInfo.extra_profiles}
                </div>
                <div className="text-sm text-600">Extra Profiles</div>
              </div>
            </div>
            
            {!extraProfileInfo.can_add_more && (
              <Message 
                severity="warning" 
                text="You've reached your profile limit. Consider adding more profiles or upgrading your plan." 
                className="mt-3"
              />
            )}
          </Panel>
        </div>
        
        <div className="col-12 md:col-6">
          <Panel header="Quick Actions" className="mb-4">
            <div className="flex flex-column gap-3">
              <Button
                label="Add Extra Profile"
                icon="pi pi-plus"
                className="w-full"
                disabled={!extraProfileInfo.can_add_more}
                onClick={() => {
                  const extraProfileAddon = availableAddons.find(a => a.service_type === 'extra_profile');
                  if (extraProfileAddon) {
                    handlePurchaseAddon(extraProfileAddon);
                  }
                }}
              />
              <Button
                label="View All Add-ons"
                icon="pi pi-shopping-cart"
                severity="secondary"
                className="w-full"
                onClick={() => setActiveTab(0)}
              />
              <Button
                label="Usage History"
                icon="pi pi-chart-line"
                severity="help"
                className="w-full"
                onClick={() => showInfo('Usage history coming soon!')}
              />
            </div>
          </Panel>
        </div>
      </div>
    );
  };

  return (
    <div className="p-4">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <div className="flex justify-content-between align-items-center mb-4">
        <h1 className="text-3xl font-bold text-900">Add-on Services</h1>
        <Tag value="Enhance Your Protection" severity="info" />
      </div>

      <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
        <TabPanel header="Available Add-ons" leftIcon="pi pi-shopping-cart">
          <div className="mb-4">
            <h2>Enhance Your Protection</h2>
            <p className="text-600">
              Add-on services let you customize your protection without upgrading your entire plan. 
              Pay only for what you need.
            </p>
          </div>
          {renderAvailableAddons()}
        </TabPanel>

        <TabPanel header="My Add-ons" leftIcon="pi pi-list">
          <div className="mb-4">
            <h2>Your Active Add-ons</h2>
            <p className="text-600">
              Manage your current add-on subscriptions and view billing information.
            </p>
          </div>
          {renderMyAddons()}
        </TabPanel>

        <TabPanel header="Usage & Limits" leftIcon="pi pi-chart-bar">
          <div className="mb-4">
            <h2>Usage Overview</h2>
            <p className="text-600">
              Monitor your add-on usage and track your limits.
            </p>
          </div>
          {renderUsagePanel()}
        </TabPanel>
      </TabView>

      {/* Purchase Confirmation Dialog */}
      <Dialog
        header={`Purchase ${selectedAddon?.name}`}
        visible={showPurchaseDialog}
        onHide={() => setShowPurchaseDialog(false)}
        modal
        style={{ width: '500px' }}
      >
        {selectedAddon && (
          <div>
            <div className="mb-4">
              <h4>{selectedAddon.name}</h4>
              <p className="text-600">{selectedAddon.description}</p>
              <div className="flex align-items-center gap-2 mb-3">
                <span className="text-2xl font-bold">
                  {addonService.getDisplayPrice(selectedAddon)}
                </span>
                <Tag 
                  value={selectedAddon.is_recurring ? "Monthly" : "One-time"} 
                  severity="info" 
                />
              </div>
            </div>

            {addonService.parseFeatures(selectedAddon.features).length > 0 && (
              <div className="mb-4">
                <h5>What you'll get:</h5>
                <ul className="list-none p-0">
                  {addonService.parseFeatures(selectedAddon.features).map((feature, index) => (
                    <li key={index} className="flex align-items-center mb-2">
                      <i className="pi pi-check text-green-500 mr-2" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Message 
              severity="info" 
              text="This add-on service is coming soon! You'll be notified when it becomes available." 
              className="mb-4"
            />

            <div className="flex gap-2 justify-content-end">
              <Button
                label="Cancel"
                severity="secondary"
                onClick={() => setShowPurchaseDialog(false)}
                disabled={purchasing}
              />
              <Button
                label="Notify Me"
                icon={purchasing ? "pi pi-spin pi-spinner" : "pi pi-bell"}
                onClick={confirmPurchase}
                loading={purchasing}
              />
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default AddonServices;