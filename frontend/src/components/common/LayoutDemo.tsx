import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Divider } from 'primereact/divider';
import { Panel } from 'primereact/panel';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { useLayoutNotifications, useLayoutTheme, useLayoutSidebar } from '../../contexts/LayoutContext';

// Sample data for demo
const sampleData = [
  { 
    id: 1, 
    profile: 'Model ABC', 
    platform: 'Instagram', 
    status: 'Active', 
    infringements: 5,
    lastScan: '2024-01-15 10:30'
  },
  { 
    id: 2, 
    profile: 'Content Creator XYZ', 
    platform: 'TikTok', 
    status: 'Pending', 
    infringements: 12,
    lastScan: '2024-01-15 09:45'
  },
  { 
    id: 3, 
    profile: 'Brand DEF', 
    platform: 'Twitter', 
    status: 'Resolved', 
    infringements: 3,
    lastScan: '2024-01-15 08:20'
  }
];

/**
 * Demo component showcasing Layout features and PrimeReact components
 * This demonstrates how the Layout integrates with various UI elements
 */
export const LayoutDemo: React.FC = () => {
  // Layout context hooks for demo functionality
  const { 
    addSuccessNotification, 
    addWarningNotification, 
    addErrorNotification,
    addInfoNotification,
    unreadNotifications 
  } = useLayoutNotifications();
  
  const { currentTheme, toggleTheme, isDarkTheme } = useLayoutTheme();
  const { sidebarVisible, toggleSidebar } = useLayoutSidebar();

  // Demo functions
  const handleAddNotification = (type: string) => {
    const timestamp = new Date().toLocaleTimeString();
    
    switch (type) {
      case 'success':
        addSuccessNotification(
          'Demo Success', 
          `Success notification added at ${timestamp}`
        );
        break;
      case 'warning':
        addWarningNotification(
          'Demo Warning', 
          `Warning notification added at ${timestamp}`
        );
        break;
      case 'error':
        addErrorNotification(
          'Demo Error', 
          `Error notification added at ${timestamp}`
        );
        break;
      case 'info':
        addInfoNotification(
          'Demo Info', 
          `Info notification added at ${timestamp}`
        );
        break;
    }
  };

  const statusBodyTemplate = (rowData: any) => {
    const severity = rowData.status === 'Active' ? 'success' : 
                    rowData.status === 'Pending' ? 'warning' : 'info';
    return <Badge value={rowData.status} severity={severity} />;
  };

  const infringementsBodyTemplate = (rowData: any) => {
    return (
      <Chip 
        label={rowData.infringements.toString()} 
        className={rowData.infringements > 10 ? 'p-chip-danger' : 'p-chip-primary'}
      />
    );
  };

  return (
    <div className="layout-demo">
      {/* Page Header */}
      <div className="mb-4">
        <h1>Layout Demo & Testing</h1>
        <p className="text-color-secondary">
          This page demonstrates the Layout component features and PrimeReact integration
        </p>
      </div>

      {/* Layout Controls Card */}
      <Card title="Layout Controls" className="mb-4">
        <div className="grid">
          <div className="col-12 md:col-6">
            <h5>Theme Control</h5>
            <p className="text-color-secondary mb-3">
              Current theme: <Badge value={currentTheme} severity={isDarkTheme ? 'info' : 'warning'} />
            </p>
            <Button 
              label={`Switch to ${isDarkTheme ? 'Light' : 'Dark'} Theme`}
              icon={isDarkTheme ? 'pi pi-sun' : 'pi pi-moon'}
              onClick={toggleTheme}
              className="mr-2"
            />
          </div>
          
          <div className="col-12 md:col-6">
            <h5>Sidebar Control</h5>
            <p className="text-color-secondary mb-3">
              Sidebar visible: <Badge value={sidebarVisible ? 'Yes' : 'No'} severity={sidebarVisible ? 'success' : 'danger'} />
            </p>
            <Button 
              label="Toggle Sidebar"
              icon="pi pi-bars"
              onClick={toggleSidebar}
              className="md:hidden"
            />
            <span className="hidden md:inline text-color-secondary">
              (Sidebar toggle is only available on mobile)
            </span>
          </div>
        </div>
      </Card>

      {/* Notification Testing Card */}
      <Card title="Notification Testing" className="mb-4">
        <p className="text-color-secondary mb-3">
          Test the notification system. Current unread notifications: 
          <Badge value={unreadNotifications} severity="danger" className="ml-2" />
        </p>
        <div className="flex flex-wrap gap-2">
          <Button 
            label="Add Success" 
            severity="success" 
            icon="pi pi-check"
            onClick={() => handleAddNotification('success')}
          />
          <Button 
            label="Add Warning" 
            severity="warning" 
            icon="pi pi-exclamation-triangle"
            onClick={() => handleAddNotification('warning')}
          />
          <Button 
            label="Add Error" 
            severity="danger" 
            icon="pi pi-times"
            onClick={() => handleAddNotification('error')}
          />
          <Button 
            label="Add Info" 
            severity="info" 
            icon="pi pi-info"
            onClick={() => handleAddNotification('info')}
          />
        </div>
      </Card>

      {/* Sample Data Table */}
      <Card title="Sample Protected Profiles" className="mb-4">
        <DataTable 
          value={sampleData} 
          responsiveLayout="scroll"
          className="p-datatable-gridlines"
          showGridlines
        >
          <Column field="id" header="ID" sortable />
          <Column field="profile" header="Profile Name" sortable />
          <Column field="platform" header="Platform" sortable />
          <Column field="status" header="Status" body={statusBodyTemplate} sortable />
          <Column field="infringements" header="Infringements" body={infringementsBodyTemplate} sortable />
          <Column field="lastScan" header="Last Scan" sortable />
        </DataTable>
      </Card>

      {/* Feature Overview */}
      <div className="grid">
        <div className="col-12 md:col-6">
          <Panel header="Layout Features" className="h-full">
            <ul className="list-none p-0 m-0">
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>Responsive design with mobile sidebar</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>Dark/Light theme switching</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>Breadcrumb navigation</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>User menu with profile access</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>Real-time notifications</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-check text-green-500 mr-2"></i>
                <span>Active route highlighting</span>
              </li>
            </ul>
          </Panel>
        </div>

        <div className="col-12 md:col-6">
          <Panel header="AutoDMCA Navigation" className="h-full">
            <ul className="list-none p-0 m-0">
              <li className="flex align-items-center py-2">
                <i className="pi pi-home text-blue-500 mr-2"></i>
                <span>Dashboard - Overview and stats</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-shield text-orange-500 mr-2"></i>
                <span>Content Protection - Core features</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-chart-bar text-purple-500 mr-2"></i>
                <span>Analytics & Reports</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-credit-card text-green-500 mr-2"></i>
                <span>Billing & Account management</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-cog text-gray-500 mr-2"></i>
                <span>Settings and preferences</span>
              </li>
              <li className="flex align-items-center py-2">
                <i className="pi pi-users text-red-500 mr-2"></i>
                <span>Admin Panel (admin only)</span>
              </li>
            </ul>
          </Panel>
        </div>
      </div>

      <Divider />

      {/* Usage Instructions */}
      <Card title="Usage Instructions">
        <div className="grid">
          <div className="col-12 md:col-6">
            <h6>Basic Usage</h6>
            <pre className="bg-gray-100 p-3 border-round text-sm">
{`import { Layout } from './components/common/Layout';
import { LayoutProvider } from './contexts/LayoutContext';

function App() {
  return (
    <LayoutProvider>
      <Layout>
        {/* Your page content */}
      </Layout>
    </LayoutProvider>
  );
}`}
            </pre>
          </div>

          <div className="col-12 md:col-6">
            <h6>Context Hooks</h6>
            <pre className="bg-gray-100 p-3 border-round text-sm">
{`import { 
  useLayoutTheme, 
  useLayoutSidebar,
  useLayoutNotifications 
} from './contexts/LayoutContext';

// Use in your components
const { toggleTheme } = useLayoutTheme();
const { toggleSidebar } = useLayoutSidebar();
const { addNotification } = useLayoutNotifications();`}
            </pre>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default LayoutDemo;