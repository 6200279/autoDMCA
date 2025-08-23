import React from 'react';
import { BreadCrumb } from 'primereact/breadcrumb';

import BillingDashboard from '../../components/billing/BillingDashboard';

const BillingPage: React.FC = () => {
  const items = [
    { label: 'Dashboard', url: '/dashboard' },
    { label: 'Billing' }
  ];

  return (
    <div className="p-4">
      {/* Breadcrumbs */}
      <BreadCrumb 
        model={items} 
        home={{ icon: 'pi pi-home', url: '/dashboard' }}
        className="mb-4" 
      />

      {/* Main Content */}
      <BillingDashboard />
    </div>
  );
};

export default BillingPage;