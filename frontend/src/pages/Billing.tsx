import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
import { Toast } from 'primereact/toast';
import { Divider } from 'primereact/divider';
import { TabView, TabPanel } from 'primereact/tabview';
import { useAuth } from '../contexts/AuthContext';
import ComingSoon from '../components/common/ComingSoon';

const Billing: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const [activeTab, setActiveTab] = useState(0);

  const mockPlans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      billingCycle: 'monthly' as const,
      features: ['5 Protected Profiles', '50 Monthly Scans', 'Basic Support', 'Dashboard Analytics'],
      limits: { profiles: 5, searches: 50, takedowns: 10, storage: '1GB' }
    },
    {
      id: 'pro',
      name: 'Professional',
      price: 29,
      billingCycle: 'monthly' as const,
      features: ['50 Protected Profiles', '500 Monthly Scans', 'Priority Support', 'Advanced Analytics', 'DMCA Templates'],
      limits: { profiles: 50, searches: 500, takedowns: 100, storage: '10GB' },
      popular: true
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 99,
      billingCycle: 'monthly' as const,
      features: ['Unlimited Profiles', 'Unlimited Scans', '24/7 Support', 'Custom Templates', 'API Access', 'White Label'],
      limits: { profiles: -1, searches: -1, takedowns: -1, storage: 'Unlimited' }
    }
  ];

  const showInfo = (message: string) => {
    toast.current?.show({ severity: 'info', summary: 'Info', detail: message });
  };

  const currentPlan = mockPlans[0]; // Default to free plan

  return (
    <div className="p-4">
      <Toast ref={toast} />
      
      <div className="flex justify-content-between align-items-center mb-4">
        <h1 className="text-3xl font-bold text-900">Billing & Subscription</h1>
        <Tag value="Basic Billing Active" severity="success" />
      </div>

      <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
        {/* Current Plan Tab */}
        <TabPanel header="Current Plan" leftIcon="pi pi-credit-card">
          <div className="grid">
            <div className="col-12 md:col-8">
              <Card title="Current Subscription">
                <div className="flex align-items-center justify-content-between mb-4">
                  <div>
                    <h3 className="m-0 mb-2">{currentPlan.name} Plan</h3>
                    <div className="flex align-items-center gap-2">
                      <span className="text-2xl font-bold">${currentPlan.price}</span>
                      <span className="text-600">per month</span>
                      {currentPlan.popular && <Tag value="Current" severity="success" />}
                    </div>
                  </div>
                  <Button 
                    label="Upgrade Plan" 
                    icon="pi pi-arrow-up"
                    onClick={() => showInfo('Plan upgrades available soon!')}
                  />
                </div>
                
                <Divider />
                
                <div className="mb-4">
                  <h4>Plan Features</h4>
                  <ul className="list-none p-0">
                    {currentPlan.features.map((feature, index) => (
                      <li key={index} className="flex align-items-center gap-2 mb-2">
                        <i className="pi pi-check text-green-500" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="grid">
                  <div className="col-6 md:col-3">
                    <div className="text-center p-3 border-1 border-300 border-round">
                      <div className="text-2xl font-bold text-blue-500">
                        {currentPlan.limits.profiles === -1 ? '∞' : currentPlan.limits.profiles}
                      </div>
                      <div className="text-sm text-600">Profiles</div>
                    </div>
                  </div>
                  <div className="col-6 md:col-3">
                    <div className="text-center p-3 border-1 border-300 border-round">
                      <div className="text-2xl font-bold text-green-500">
                        {currentPlan.limits.searches === -1 ? '∞' : currentPlan.limits.searches}
                      </div>
                      <div className="text-sm text-600">Monthly Scans</div>
                    </div>
                  </div>
                  <div className="col-6 md:col-3">
                    <div className="text-center p-3 border-1 border-300 border-round">
                      <div className="text-2xl font-bold text-orange-500">
                        {currentPlan.limits.takedowns === -1 ? '∞' : currentPlan.limits.takedowns}
                      </div>
                      <div className="text-sm text-600">Takedowns</div>
                    </div>
                  </div>
                  <div className="col-6 md:col-3">
                    <div className="text-center p-3 border-1 border-300 border-round">
                      <div className="text-2xl font-bold text-purple-500">{currentPlan.limits.storage}</div>
                      <div className="text-sm text-600">Storage</div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            <div className="col-12 md:col-4">
              <Card title="Quick Actions">
                <div className="flex flex-column gap-3">
                  <Button 
                    label="Upgrade Plan" 
                    icon="pi pi-arrow-up"
                    className="w-full"
                    onClick={() => showInfo('Plan upgrades coming soon!')}
                  />
                  <Button 
                    label="Browse Add-ons" 
                    icon="pi pi-plus-circle"
                    severity="secondary"
                    className="w-full"
                    onClick={() => window.location.href = '/billing/addons'}
                  />
                  <Button 
                    label="Usage Reports" 
                    icon="pi pi-chart-line"
                    severity="secondary"
                    className="w-full"
                    onClick={() => showInfo('Usage reports coming soon!')}
                  />
                  <Button 
                    label="Billing History" 
                    icon="pi pi-history"
                    severity="secondary"
                    className="w-full"
                    onClick={() => showInfo('Billing history coming soon!')}
                  />
                  <Button 
                    label="Download Receipt" 
                    icon="pi pi-download"
                    severity="help"
                    className="w-full"
                    onClick={() => showInfo('Receipt downloads coming soon!')}
                  />
                </div>
              </Card>
            </div>
          </div>

          <Message 
            severity="info" 
            text="Full billing functionality including payment methods, invoices, and plan changes will be available soon!"
            className="mt-4"
          />
        </TabPanel>

        {/* Plans Tab */}
        <TabPanel header="Available Plans" leftIcon="pi pi-list">
          <div className="grid">
            {mockPlans.map((plan) => (
              <div key={plan.id} className="col-12 md:col-4">
                <Card className={`h-full ${plan.popular ? 'border-primary border-2' : ''}`}>
                  <div className="text-center">
                    {plan.popular && (
                      <Tag value="Most Popular" severity="success" className="mb-3" />
                    )}
                    <h3 className="m-0 mb-2">{plan.name}</h3>
                    <div className="flex align-items-center justify-content-center gap-2 mb-4">
                      <span className="text-3xl font-bold">${plan.price}</span>
                      <span className="text-600">per month</span>
                    </div>
                    
                    <ul className="list-none p-0 mb-4">
                      {plan.features.map((feature, index) => (
                        <li key={index} className="flex align-items-center gap-2 mb-2">
                          <i className="pi pi-check text-green-500" />
                          <span className="text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    
                    <Button 
                      label={plan.id === currentPlan.id ? "Current Plan" : "Select Plan"}
                      disabled={plan.id === currentPlan.id}
                      className="w-full"
                      onClick={() => showInfo(`${plan.name} plan selection coming soon!`)}
                    />
                  </div>
                </Card>
              </div>
            ))}
          </div>
        </TabPanel>

        {/* Payment Methods Tab */}
        <TabPanel header="Payment Methods" leftIcon="pi pi-wallet">
          <ComingSoon 
            featureName="Payment Methods"
            description="Manage your payment methods, add credit cards, and set up automatic billing."
            icon="pi-wallet"
            expectedDate="Q2 2024"
            contactSupport={false}
          />
        </TabPanel>

        {/* Invoices Tab */}
        <TabPanel header="Invoices" leftIcon="pi pi-file">
          <ComingSoon 
            featureName="Invoice History"
            description="View and download your billing history, invoices, and payment receipts."
            icon="pi-file"
            expectedDate="Q2 2024"
            contactSupport={false}
          />
        </TabPanel>

        {/* Add-on Services Tab */}
        <TabPanel header="Add-on Services" leftIcon="pi pi-plus-circle">
          <div className="grid">
            <div className="col-12 md:col-8">
              <Card title="Available Add-ons" className="mb-4">
                <div className="grid">
                  {/* Extra Profile Add-on */}
                  <div className="col-12 md:col-6 mb-3">
                    <div className="border-1 border-300 border-round p-3 h-full flex flex-column">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <h4 className="m-0">Extra Profile</h4>
                        <Tag value="$10/month" severity="success" />
                      </div>
                      <p className="text-600 mb-3 flex-1">
                        Add an additional profile to monitor. Perfect for managing multiple online identities.
                      </p>
                      <ul className="list-none p-0 mb-3 text-sm">
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          1 Additional Profile
                        </li>
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Same monitoring features
                        </li>
                        <li className="flex align-items-center">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Separate analytics
                        </li>
                      </ul>
                      <Button 
                        label="Add Extra Profile" 
                        icon="pi pi-plus"
                        className="w-full"
                        onClick={() => showInfo('Extra profile add-on coming soon!')}
                        size="small"
                      />
                    </div>
                  </div>

                  {/* Copyright Registration */}
                  <div className="col-12 md:col-6 mb-3">
                    <div className="border-1 border-300 border-round p-3 h-full flex flex-column">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <h4 className="m-0">Copyright Registration</h4>
                        <Tag value="$199 one-time" severity="info" />
                      </div>
                      <p className="text-600 mb-3 flex-1">
                        Professional copyright registration service with USPTO filing assistance.
                      </p>
                      <ul className="list-none p-0 mb-3 text-sm">
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Professional filing
                        </li>
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Legal document prep
                        </li>
                        <li className="flex align-items-center">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Certificate delivery
                        </li>
                      </ul>
                      <Button 
                        label="Get Copyright Help" 
                        icon="pi pi-shield"
                        className="w-full"
                        onClick={() => showInfo('Copyright registration service coming soon!')}
                        size="small"
                        severity="secondary"
                      />
                    </div>
                  </div>

                  {/* Priority Takedown */}
                  <div className="col-12 md:col-6 mb-3">
                    <div className="border-1 border-300 border-round p-3 h-full flex flex-column">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <h4 className="m-0">Priority Takedown</h4>
                        <Tag value="$49/month" severity="warning" />
                      </div>
                      <p className="text-600 mb-3 flex-1">
                        24-hour priority processing for urgent takedown requests.
                      </p>
                      <ul className="list-none p-0 mb-3 text-sm">
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          24-hour guarantee
                        </li>
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Priority queue
                        </li>
                        <li className="flex align-items-center">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Dedicated support
                        </li>
                      </ul>
                      <Button 
                        label="Enable Priority" 
                        icon="pi pi-bolt"
                        className="w-full"
                        onClick={() => showInfo('Priority takedown service coming soon!')}
                        size="small"
                        severity="help"
                      />
                    </div>
                  </div>

                  {/* API Access */}
                  <div className="col-12 md:col-6 mb-3">
                    <div className="border-1 border-300 border-round p-3 h-full flex flex-column">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <h4 className="m-0">API Access</h4>
                        <Tag value="$99/month" severity="contrast" />
                      </div>
                      <p className="text-600 mb-3 flex-1">
                        Full API access for integrations and custom automations.
                      </p>
                      <ul className="list-none p-0 mb-3 text-sm">
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          10,000 requests/month
                        </li>
                        <li className="flex align-items-center mb-1">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Webhook support
                        </li>
                        <li className="flex align-items-center">
                          <i className="pi pi-check text-green-500 mr-2" />
                          Full documentation
                        </li>
                      </ul>
                      <Button 
                        label="Get API Access" 
                        icon="pi pi-code"
                        className="w-full"
                        onClick={() => showInfo('API access add-on coming soon!')}
                        size="small"
                      />
                    </div>
                  </div>
                </div>
              </Card>

              <Card title="My Add-ons">
                <Message 
                  severity="info" 
                  text="You don't have any active add-on services. Choose from the add-ons above to enhance your account." 
                />
              </Card>
            </div>

            <div className="col-12 md:col-4">
              <Card title="Add-on Benefits">
                <div className="text-center mb-4">
                  <i className="pi pi-star text-6xl text-yellow-500 mb-3"></i>
                  <h4>Supercharge Your Protection</h4>
                  <p className="text-600 mb-4">
                    Add-on services help you get more value from your subscription without upgrading your entire plan.
                  </p>
                </div>

                <div className="mb-4">
                  <h5>Why Add-ons?</h5>
                  <ul className="list-none p-0">
                    <li className="flex align-items-center mb-2">
                      <i className="pi pi-check text-green-500 mr-2" />
                      <span className="text-sm">Pay only for what you need</span>
                    </li>
                    <li className="flex align-items-center mb-2">
                      <i className="pi pi-check text-green-500 mr-2" />
                      <span className="text-sm">No plan upgrade required</span>
                    </li>
                    <li className="flex align-items-center mb-2">
                      <i className="pi pi-check text-green-500 mr-2" />
                      <span className="text-sm">Cancel anytime</span>
                    </li>
                    <li className="flex align-items-center">
                      <i className="pi pi-check text-green-500 mr-2" />
                      <span className="text-sm">Instant activation</span>
                    </li>
                  </ul>
                </div>

                <Divider />

                <div className="text-center">
                  <p className="text-600 mb-3">Need help choosing?</p>
                  <Button 
                    label="Contact Support" 
                    icon="pi pi-envelope"
                    size="small"
                    severity="secondary"
                    onClick={() => showInfo('Support contact coming soon!')}
                  />
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Usage Tab */}
        <TabPanel header="Usage Analytics" leftIcon="pi pi-chart-bar">
          <ComingSoon 
            featureName="Usage Analytics"
            description="Detailed usage analytics, cost breakdown, and resource consumption tracking."
            icon="pi-chart-bar"
            expectedDate="Q3 2024"
            contactSupport={false}
          />
        </TabPanel>
      </TabView>
    </div>
  );
};

export default Billing;