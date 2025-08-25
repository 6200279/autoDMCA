import React, { useState, useRef } from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { 
  SingleRequestForm, 
  BatchRequestForm, 
  RequestStatusTable, 
  StatisticsDashboard 
} from '../components/delisting';
import type { DelistingRequest } from '../types/delisting';
import './SearchEngineDelisting.css';

const SearchEngineDelisting: React.FC = () => {
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedRequest, setSelectedRequest] = useState<DelistingRequest | null>(null);
  const toast = useRef<Toast>(null);

  const handleRequestSuccess = (requestId: string) => {
    toast.current?.show({
      severity: 'success',
      summary: 'Success',
      detail: `Delisting request submitted successfully! ID: ${requestId}`,
      life: 5000
    });
    
    // Refresh the status table and statistics
    setRefreshTrigger(prev => prev + 1);
    
    // Switch to the tracking tab to see the new request
    setActiveTabIndex(2);
  };

  const handleRequestError = (error: string) => {
    toast.current?.show({
      severity: 'error',
      summary: 'Error',
      detail: error,
      life: 5000
    });
  };

  const handleBatchSuccess = (batchId: string) => {
    toast.current?.show({
      severity: 'success',
      summary: 'Success',
      detail: `Batch delisting request submitted successfully! ID: ${batchId}`,
      life: 5000
    });
    
    // Refresh the status table and statistics
    setRefreshTrigger(prev => prev + 1);
    
    // Switch to the tracking tab to see the new requests
    setActiveTabIndex(2);
  };

  const handleRequestSelect = (request: DelistingRequest) => {
    setSelectedRequest(request);
    // TODO: Could open a detailed view modal/sidebar here
  };

  return (
    <div className="search-engine-delisting-page">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <div className="page-header">
        <div className="flex align-items-center justify-content-between">
          <div>
            <h1 className="text-4xl font-bold mb-2">🌐 Search Engine Delisting</h1>
            <p className="text-lg text-600">
              Remove infringing content from search engine results
            </p>
          </div>
          <Button
            icon="pi pi-refresh"
            label="Refresh Data"
            outlined
            onClick={() => setRefreshTrigger(prev => prev + 1)}
            tooltip="Refresh all data"
          />
        </div>
      </div>

      <div className="content-wrapper">
        <TabView 
          activeIndex={activeTabIndex} 
          onTabChange={(e) => setActiveTabIndex(e.index)}
          className="delisting-tabs"
        >
          <TabPanel 
            header="Dashboard" 
            leftIcon="pi pi-chart-bar mr-2"
          >
            <StatisticsDashboard refreshTrigger={refreshTrigger} />
          </TabPanel>

          <TabPanel 
            header="Submit Single URL" 
            leftIcon="pi pi-plus mr-2"
          >
            <div className="grid">
              <div className="col-12 lg:col-8 lg:col-offset-2">
                <SingleRequestForm
                  onSuccess={handleRequestSuccess}
                  onError={handleRequestError}
                />
              </div>
            </div>
          </TabPanel>

          <TabPanel 
            header="Batch Upload" 
            leftIcon="pi pi-upload mr-2"
          >
            <div className="grid">
              <div className="col-12 lg:col-10 lg:col-offset-1">
                <BatchRequestForm
                  onSuccess={handleBatchSuccess}
                  onError={handleRequestError}
                />
              </div>
            </div>
          </TabPanel>

          <TabPanel 
            header="Track Requests" 
            leftIcon="pi pi-list mr-2"
          >
            <Card title="Delisting Request Status" className="h-full">
              <RequestStatusTable 
                refreshTrigger={refreshTrigger}
                onRequestSelect={handleRequestSelect}
              />
            </Card>
          </TabPanel>

          <TabPanel 
            header="Analytics" 
            leftIcon="pi pi-chart-line mr-2"
          >
            <StatisticsDashboard refreshTrigger={refreshTrigger} />
          </TabPanel>
        </TabView>
      </div>

      {/* Quick Action Cards - shown on dashboard tab */}
      {activeTabIndex === 0 && (
        <div className="mt-4">
          <Card title="Quick Actions" className="quick-actions-card">
            <div className="grid">
              <div className="col-12 md:col-6 lg:col-3">
                <Button
                  label="Submit Single URL"
                  icon="pi pi-plus"
                  className="w-full p-button-outlined"
                  onClick={() => setActiveTabIndex(1)}
                />
              </div>
              <div className="col-12 md:col-6 lg:col-3">
                <Button
                  label="Batch Upload"
                  icon="pi pi-upload"
                  className="w-full p-button-outlined"
                  onClick={() => setActiveTabIndex(2)}
                />
              </div>
              <div className="col-12 md:col-6 lg:col-3">
                <Button
                  label="Track Requests"
                  icon="pi pi-list"
                  className="w-full p-button-outlined"
                  onClick={() => setActiveTabIndex(3)}
                />
              </div>
              <div className="col-12 md:col-6 lg:col-3">
                <Button
                  label="View Analytics"
                  icon="pi pi-chart-line"
                  className="w-full p-button-outlined"
                  onClick={() => setActiveTabIndex(4)}
                />
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SearchEngineDelisting;