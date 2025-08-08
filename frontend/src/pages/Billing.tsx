import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { Skeleton } from 'primereact/skeleton';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { Calendar } from 'primereact/calendar';
import { Chart } from 'primereact/chart';
import { useAuth } from '../contexts/AuthContext';

// TypeScript interfaces
interface Plan {
  id: string;
  name: string;
  price: number;
  billingCycle: 'monthly' | 'yearly';
  features: string[];
  limits: {
    profiles: number;
    searches: number;
    takedowns: number;
    storage: string;
  };
  popular?: boolean;
}

interface Invoice {
  id: string;
  date: Date;
  amount: number;
  status: 'paid' | 'pending' | 'overdue' | 'failed';
  items: InvoiceItem[];
  downloadUrl?: string;
}

interface InvoiceItem {
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
}

interface Usage {
  period: string;
  profiles: { used: number; limit: number };
  searches: { used: number; limit: number };
  takedowns: { used: number; limit: number };
  storage: { used: string; limit: string };
}

interface PaymentMethod {
  id: string;
  type: 'card' | 'paypal' | 'bank';
  last4?: string;
  brand?: string;
  expiryMonth?: number;
  expiryYear?: number;
  isDefault: boolean;
}

const Billing: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  
  // State management
  const [loading, setLoading] = useState(true);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [chartData, setChartData] = useState({});
  const [chartOptions, setChartOptions] = useState({});

  // Available plans
  const availablePlans: Plan[] = [
    {
      id: 'starter',
      name: 'Starter',
      price: 29,
      billingCycle: 'monthly',
      features: [
        'Up to 3 profiles',
        '100 searches/month',
        '10 takedown requests/month',
        '1GB storage',
        'Email support'
      ],
      limits: {
        profiles: 3,
        searches: 100,
        takedowns: 10,
        storage: '1GB'
      }
    },
    {
      id: 'professional',
      name: 'Professional',
      price: 79,
      billingCycle: 'monthly',
      popular: true,
      features: [
        'Up to 10 profiles',
        '500 searches/month',
        '50 takedown requests/month',
        '5GB storage',
        'Priority support',
        'Advanced analytics'
      ],
      limits: {
        profiles: 10,
        searches: 500,
        takedowns: 50,
        storage: '5GB'
      }
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 199,
      billingCycle: 'monthly',
      features: [
        'Unlimited profiles',
        'Unlimited searches',
        'Unlimited takedowns',
        '50GB storage',
        '24/7 support',
        'Custom integrations',
        'Dedicated account manager'
      ],
      limits: {
        profiles: -1,
        searches: -1,
        takedowns: -1,
        storage: '50GB'
      }
    }
  ];

  // Mock data initialization
  useEffect(() => {
    const timer = setTimeout(() => {
      // Set current plan
      setCurrentPlan(availablePlans[1]); // Professional plan

      // Set usage data
      setUsage({
        period: 'January 2024',
        profiles: { used: 7, limit: 10 },
        searches: { used: 342, limit: 500 },
        takedowns: { used: 28, limit: 50 },
        storage: { used: '2.3GB', limit: '5GB' }
      });

      // Set invoices
      setInvoices([
        {
          id: 'INV-2024-001',
          date: new Date('2024-01-01'),
          amount: 79.00,
          status: 'paid',
          items: [
            {
              description: 'Professional Plan - January 2024',
              quantity: 1,
              unitPrice: 79.00,
              total: 79.00
            }
          ],
          downloadUrl: '/invoices/INV-2024-001.pdf'
        },
        {
          id: 'INV-2023-012',
          date: new Date('2023-12-01'),
          amount: 79.00,
          status: 'paid',
          items: [
            {
              description: 'Professional Plan - December 2023',
              quantity: 1,
              unitPrice: 79.00,
              total: 79.00
            }
          ],
          downloadUrl: '/invoices/INV-2023-012.pdf'
        },
        {
          id: 'INV-2023-011',
          date: new Date('2023-11-01'),
          amount: 79.00,
          status: 'paid',
          items: [
            {
              description: 'Professional Plan - November 2023',
              quantity: 1,
              unitPrice: 79.00,
              total: 79.00
            }
          ]
        }
      ]);

      // Set payment methods
      setPaymentMethods([
        {
          id: 'pm_1',
          type: 'card',
          last4: '4242',
          brand: 'Visa',
          expiryMonth: 12,
          expiryYear: 2025,
          isDefault: true
        },
        {
          id: 'pm_2',
          type: 'paypal',
          isDefault: false
        }
      ]);

      // Set chart data
      const data = {
        labels: ['Sep', 'Oct', 'Nov', 'Dec', 'Jan'],
        datasets: [
          {
            label: 'Searches Used',
            data: [287, 356, 412, 398, 342],
            fill: false,
            borderColor: '#42A5F5',
            backgroundColor: '#42A5F5',
            tension: 0.4
          },
          {
            label: 'Takedowns Used',
            data: [23, 31, 28, 35, 28],
            fill: false,
            borderColor: '#FFA726',
            backgroundColor: '#FFA726',
            tension: 0.4
          }
        ]
      };

      const options = {
        maintainAspectRatio: false,
        aspectRatio: 0.8,
        plugins: {
          legend: {
            labels: {
              fontColor: '#495057'
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: '#495057'
            },
            grid: {
              color: '#ebedef'
            }
          },
          y: {
            ticks: {
              color: '#495057'
            },
            grid: {
              color: '#ebedef'
            }
          }
        }
      };

      setChartData(data);
      setChartOptions(options);
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Helper functions
  const showToast = (severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail: string) => {
    toast.current?.show({ severity, summary, detail, life: 3000 });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  // Event handlers
  const handleUpgradePlan = (plan: Plan) => {
    setSelectedPlan(plan);
    setShowUpgradeDialog(true);
  };

  const confirmPlanUpgrade = async () => {
    if (!selectedPlan) return;

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setCurrentPlan(selectedPlan);
      setShowUpgradeDialog(false);
      showToast('success', 'Plan Updated', `Successfully upgraded to ${selectedPlan.name} plan`);
    } catch (error) {
      showToast('error', 'Upgrade Failed', 'Unable to upgrade plan. Please try again.');
    }
  };

  const downloadInvoice = (invoice: Invoice) => {
    if (invoice.downloadUrl) {
      // Simulate download
      showToast('success', 'Download Started', `Downloading invoice ${invoice.id}`);
    } else {
      showToast('warn', 'Download Unavailable', 'This invoice is not available for download');
    }
  };

  // Column templates
  const invoiceIdTemplate = (rowData: Invoice) => (
    <div className="font-mono text-sm">{rowData.id}</div>
  );

  const dateTemplate = (rowData: Invoice) => (
    <div>{formatDate(rowData.date)}</div>
  );

  const amountTemplate = (rowData: Invoice) => (
    <div className="font-medium">{formatCurrency(rowData.amount)}</div>
  );

  const statusTemplate = (rowData: Invoice) => {
    const getSeverity = (status: string) => {
      switch (status) {
        case 'paid': return 'success';
        case 'pending': return 'warning';
        case 'overdue': return 'danger';
        case 'failed': return 'danger';
        default: return 'info';
      }
    };

    return (
      <Tag 
        value={rowData.status.toUpperCase()} 
        severity={getSeverity(rowData.status)}
      />
    );
  };

  const actionsTemplate = (rowData: Invoice) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-download"
        size="small"
        text
        tooltip="Download Invoice"
        onClick={() => downloadInvoice(rowData)}
        disabled={!rowData.downloadUrl}
      />
      <Button
        icon="pi pi-eye"
        size="small"
        text
        tooltip="View Details"
        onClick={() => showToast('info', 'View Invoice', `Viewing details for ${rowData.id}`)}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Card>
            <Skeleton height="2rem" className="mb-4" />
            <div className="grid">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="col-12 md:col-6 lg:col-4">
                  <Skeleton height="8rem" className="mb-3" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="grid">
      <div className="col-12">
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">Billing & Usage</h2>
            <p className="text-600 m-0 mt-1">Manage your subscription and billing information</p>
          </div>
        </div>

        {/* Current Plan & Usage */}
        <div className="grid mb-4">
          <div className="col-12 md:col-8">
            <Card title="Current Plan">
              <div className="flex align-items-center justify-content-between mb-3">
                <div>
                  <div className="text-2xl font-bold text-primary mb-1">
                    {currentPlan?.name}
                    {currentPlan?.popular && (
                      <Badge value="Popular" className="ml-2" severity="success" />
                    )}
                  </div>
                  <div className="text-600">
                    {formatCurrency(currentPlan?.price || 0)} / {currentPlan?.billingCycle}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button 
                    label="Change Plan" 
                    icon="pi pi-pencil" 
                    outlined
                    onClick={() => setShowUpgradeDialog(true)}
                  />
                  <Button 
                    label="Cancel Plan" 
                    icon="pi pi-times" 
                    outlined
                    severity="danger"
                    onClick={() => showToast('info', 'Cancel Plan', 'Contact support to cancel your plan')}
                  />
                </div>
              </div>
              
              <Divider />
              
              <div className="grid">
                <div className="col-6 md:col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-900">{usage?.profiles.used}</div>
                    <div className="text-600 text-sm">
                      of {usage?.profiles.limit === -1 ? '∞' : usage?.profiles.limit} profiles
                    </div>
                  </div>
                </div>
                <div className="col-6 md:col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-900">{usage?.searches.used}</div>
                    <div className="text-600 text-sm">
                      of {usage?.searches.limit === -1 ? '∞' : usage?.searches.limit} searches
                    </div>
                  </div>
                </div>
                <div className="col-6 md:col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-900">{usage?.takedowns.used}</div>
                    <div className="text-600 text-sm">
                      of {usage?.takedowns.limit === -1 ? '∞' : usage?.takedowns.limit} takedowns
                    </div>
                  </div>
                </div>
                <div className="col-6 md:col-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-900">{usage?.storage.used}</div>
                    <div className="text-600 text-sm">of {usage?.storage.limit} storage</div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
          
          <div className="col-12 md:col-4">
            <Card title="Usage Trends">
              <Chart type="line" data={chartData} options={chartOptions} height="200px" />
            </Card>
          </div>
        </div>

        {/* Invoices */}
        <div className="grid mb-4">
          <div className="col-12">
            <Card>
              <div className="flex justify-content-between align-items-center mb-4">
                <div>
                  <h4 className="m-0">Billing History</h4>
                  <p className="text-600 m-0 mt-1">View and download your invoices</p>
                </div>
                <Button 
                  label="View All Invoices" 
                  icon="pi pi-external-link" 
                  outlined
                  onClick={() => showToast('info', 'View All', 'Opening full invoice history')}
                />
              </div>
              
              <DataTable
                value={invoices}
                size="small"
                showGridlines
                emptyMessage="No invoices found"
                paginator
                rows={5}
              >
                <Column 
                  field="id" 
                  header="Invoice ID" 
                  body={invoiceIdTemplate}
                  style={{ width: '20%' }}
                />
                <Column 
                  field="date" 
                  header="Date" 
                  body={dateTemplate}
                  sortable
                  style={{ width: '20%' }}
                />
                <Column 
                  field="amount" 
                  header="Amount" 
                  body={amountTemplate}
                  style={{ width: '20%' }}
                />
                <Column 
                  field="status" 
                  header="Status" 
                  body={statusTemplate}
                  style={{ width: '20%' }}
                />
                <Column 
                  body={actionsTemplate} 
                  style={{ width: '20%' }}
                />
              </DataTable>
            </Card>
          </div>
        </div>

        {/* Payment Methods */}
        <div className="grid">
          <div className="col-12 md:col-8">
            <Card title="Payment Methods">
              {paymentMethods.map((method, index) => (
                <div key={method.id} className="flex align-items-center justify-content-between p-3 border-1 border-200 border-round mb-3">
                  <div className="flex align-items-center gap-3">
                    <i className={`pi ${method.type === 'card' ? 'pi-credit-card' : 'pi-paypal'} text-2xl text-600`} />
                    <div>
                      <div className="font-medium text-900">
                        {method.type === 'card' ? `${method.brand} **** ${method.last4}` : 'PayPal Account'}
                        {method.isDefault && (
                          <Badge value="Default" className="ml-2" severity="success" />
                        )}
                      </div>
                      {method.type === 'card' && (
                        <div className="text-600 text-sm">
                          Expires {method.expiryMonth}/{method.expiryYear}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {!method.isDefault && (
                      <Button
                        label="Set as Default"
                        size="small"
                        outlined
                        onClick={() => showToast('success', 'Default Updated', 'Payment method set as default')}
                      />
                    )}
                    <Button
                      icon="pi pi-trash"
                      size="small"
                      text
                      severity="danger"
                      onClick={() => showToast('info', 'Remove Method', 'Payment method removed')}
                    />
                  </div>
                </div>
              ))}
              
              <Button 
                label="Add Payment Method" 
                icon="pi pi-plus" 
                outlined
                onClick={() => setShowPaymentDialog(true)}
              />
            </Card>
          </div>
          
          <div className="col-12 md:col-4">
            <Card title="Billing Information">
              <div className="grid">
                <div className="col-12">
                  <div className="text-600 text-sm">Next Billing Date</div>
                  <div className="text-900 font-medium">February 1, 2024</div>
                </div>
                <div className="col-12 mt-3">
                  <div className="text-600 text-sm">Billing Email</div>
                  <div className="text-900 font-medium">{user?.email}</div>
                </div>
                <div className="col-12 mt-3">
                  <div className="text-600 text-sm">Tax ID</div>
                  <div className="text-900 font-medium">Not provided</div>
                </div>
              </div>
              
              <Divider />
              
              <Button 
                label="Update Billing Info" 
                icon="pi pi-pencil" 
                outlined
                className="w-full"
                onClick={() => showToast('info', 'Update Billing', 'Opening billing information form')}
              />
            </Card>
          </div>
        </div>
      </div>

      {/* Plan Upgrade Dialog */}
      <Dialog
        visible={showUpgradeDialog}
        style={{ width: '800px' }}
        header="Choose Your Plan"
        modal
        onHide={() => setShowUpgradeDialog(false)}
      >
        <div className="grid">
          {availablePlans.map((plan) => (
            <div key={plan.id} className="col-12 md:col-4">
              <Card 
                className={`h-full ${plan.id === currentPlan?.id ? 'border-primary' : ''} ${plan.popular ? 'border-orange-300' : ''}`}
              >
                <div className="text-center">
                  <div className="text-xl font-bold text-900 mb-1">
                    {plan.name}
                    {plan.popular && (
                      <Badge value="Popular" className="ml-2" severity="warning" />
                    )}
                    {plan.id === currentPlan?.id && (
                      <Badge value="Current" className="ml-2" severity="success" />
                    )}
                  </div>
                  <div className="text-3xl font-bold text-primary mb-3">
                    {formatCurrency(plan.price)}
                    <span className="text-sm text-600">/{plan.billingCycle}</span>
                  </div>
                  
                  <ul className="list-none p-0 text-left">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span className="text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  
                  <Button
                    label={plan.id === currentPlan?.id ? 'Current Plan' : 'Select Plan'}
                    className="w-full mt-3"
                    disabled={plan.id === currentPlan?.id}
                    onClick={() => setSelectedPlan(plan)}
                    severity={plan.popular ? 'warning' : 'primary'}
                  />
                </div>
              </Card>
            </div>
          ))}
        </div>
        
        {selectedPlan && selectedPlan.id !== currentPlan?.id && (
          <div className="mt-4 p-3 border-1 border-200 border-round bg-blue-50">
            <div className="text-900 font-medium mb-2">Confirm Plan Change</div>
            <div className="text-600 mb-3">
              You are about to change from {currentPlan?.name} to {selectedPlan.name}.
              The new plan will take effect immediately.
            </div>
            <div className="flex justify-content-end gap-2">
              <Button 
                label="Cancel" 
                outlined 
                onClick={() => setSelectedPlan(null)} 
              />
              <Button 
                label="Confirm Change" 
                onClick={confirmPlanUpgrade}
              />
            </div>
          </div>
        )}
      </Dialog>

      {/* Payment Method Dialog */}
      <Dialog
        visible={showPaymentDialog}
        style={{ width: '500px' }}
        header="Add Payment Method"
        modal
        onHide={() => setShowPaymentDialog(false)}
      >
        <div className="grid">
          <div className="col-12">
            <div className="text-900 font-medium mb-3">Select Payment Type</div>
            <div className="flex gap-3 mb-4">
              <Button 
                label="Credit Card" 
                icon="pi pi-credit-card" 
                onClick={() => showToast('info', 'Add Card', 'Opening credit card form')}
              />
              <Button 
                label="PayPal" 
                icon="pi pi-paypal" 
                outlined
                onClick={() => showToast('info', 'Add PayPal', 'Redirecting to PayPal')}
              />
            </div>
          </div>
        </div>
      </Dialog>

      <Toast ref={toast} />
    </div>
  );
};

export default Billing;