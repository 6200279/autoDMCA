import React, { useState, useEffect, useRef } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { Menu } from 'primereact/menu';
import { confirmDialog } from 'primereact/confirmdialog';
import { FilterMatchMode } from 'primereact/api';
import { Toast } from 'primereact/toast';
import { searchEngineDelistingApi } from '../../services/api';
import type { 
  DelistingRequest, 
  DelistingStatus, 
  SearchEngine, 
  DelistingPriority,
  DelistingFilters 
} from '../../types/delisting';

interface RequestStatusTableProps {
  refreshTrigger?: number;
  onRequestSelect?: (request: DelistingRequest) => void;
}

const statusOptions = [
  { label: 'All Statuses', value: null },
  { label: 'Pending', value: 'pending' },
  { label: 'Processing', value: 'processing' },
  { label: 'Submitted', value: 'submitted' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' }
];

const searchEngineOptions = [
  { label: 'Google', value: 'google' },
  { label: 'Bing', value: 'bing' },
  { label: 'Yahoo', value: 'yahoo' },
  { label: 'Yandex', value: 'yandex' }
];

const priorityOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Normal', value: 'normal' },
  { label: 'High', value: 'high' },
  { label: 'Urgent', value: 'urgent' }
];

const getStatusSeverity = (status: DelistingStatus) => {
  switch (status) {
    case 'completed': return 'success';
    case 'processing': return 'info';
    case 'submitted': return 'info';
    case 'failed': return 'danger';
    case 'cancelled': return 'warning';
    case 'pending': return 'warning';
    case 'retrying': return 'info';
    default: return 'secondary';
  }
};

const getPrioritySeverity = (priority: DelistingPriority) => {
  switch (priority) {
    case 'urgent': return 'danger';
    case 'high': return 'warning';
    case 'normal': return 'info';
    case 'low': return 'secondary';
    default: return 'secondary';
  }
};

const RequestStatusTable: React.FC<RequestStatusTableProps> = ({
  refreshTrigger,
  onRequestSelect
}) => {
  const [requests, setRequests] = useState<DelistingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequests, setSelectedRequests] = useState<DelistingRequest[]>([]);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
  });
  
  // Filter states
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [searchEngineFilter, setSearchEngineFilter] = useState<string[]>([]);
  const [priorityFilter, setPriorityFilter] = useState<string[]>([]);
  
  const [totalRecords, setTotalRecords] = useState(0);
  const [lazyParams, setLazyParams] = useState({
    first: 0,
    rows: 10,
    page: 0
  });
  
  const actionMenuRef = useRef<Menu>(null);
  const toast = useRef<Toast>(null);

  const loadRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params: any = {
        page: lazyParams.page + 1,
        size: lazyParams.rows
      };
      
      if (statusFilter) params.status = statusFilter;
      if (searchEngineFilter.length > 0) params.search_engine = searchEngineFilter.join(',');
      if (priorityFilter.length > 0) params.priority = priorityFilter.join(',');
      if (globalFilterValue) params.search = globalFilterValue;
      
      const response = await searchEngineDelistingApi.listDelistingRequests(params);
      setRequests(response.data.items);
      setTotalRecords(response.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, [lazyParams, statusFilter, searchEngineFilter, priorityFilter, refreshTrigger]);

  const onPage = (event: any) => {
    setLazyParams(event);
  };

  const onGlobalFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setGlobalFilterValue(value);
    setFilters({
      global: { value, matchMode: FilterMatchMode.CONTAINS }
    });
  };

  const handleRetryRequest = async (requestId: string) => {
    try {
      await searchEngineDelistingApi.retryDelistingRequest(requestId);
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Request retry initiated successfully'
      });
      loadRequests();
    } catch (err: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: err.response?.data?.detail || 'Failed to retry request'
      });
    }
  };

  const handleCancelRequest = async (requestId: string) => {
    try {
      await searchEngineDelistingApi.cancelDelistingRequest(requestId);
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Request cancelled successfully'
      });
      loadRequests();
    } catch (err: any) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: err.response?.data?.detail || 'Failed to cancel request'
      });
    }
  };

  const handleBulkCancel = async () => {
    if (selectedRequests.length === 0) return;
    
    confirmDialog({
      message: `Are you sure you want to cancel ${selectedRequests.length} selected requests?`,
      header: 'Confirm Bulk Cancel',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          const requestIds = selectedRequests.map(r => r.id);
          await searchEngineDelistingApi.bulkCancel(requestIds);
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: `${selectedRequests.length} requests cancelled successfully`
          });
          setSelectedRequests([]);
          loadRequests();
        } catch (err: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: err.response?.data?.detail || 'Failed to cancel requests'
          });
        }
      }
    });
  };

  const handleBulkRetry = async () => {
    if (selectedRequests.length === 0) return;
    
    confirmDialog({
      message: `Are you sure you want to retry ${selectedRequests.length} selected requests?`,
      header: 'Confirm Bulk Retry',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          const requestIds = selectedRequests.map(r => r.id);
          await searchEngineDelistingApi.bulkRetry(requestIds);
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: `${selectedRequests.length} requests retried successfully`
          });
          setSelectedRequests([]);
          loadRequests();
        } catch (err: any) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: err.response?.data?.detail || 'Failed to retry requests'
          });
        }
      }
    });
  };

  // Column renderers
  const statusBodyTemplate = (rowData: DelistingRequest) => (
    <Tag 
      value={rowData.status.toUpperCase()} 
      severity={getStatusSeverity(rowData.status)}
    />
  );

  const priorityBodyTemplate = (rowData: DelistingRequest) => (
    <Tag 
      value={rowData.priority.toUpperCase()} 
      severity={getPrioritySeverity(rowData.priority)}
    />
  );

  const urlBodyTemplate = (rowData: DelistingRequest) => (
    <div className="max-w-20rem">
      <a 
        href={rowData.url} 
        target="_blank" 
        rel="noopener noreferrer"
        className="text-primary hover:underline text-sm"
      >
        {rowData.url.length > 60 ? `${rowData.url.substring(0, 60)}...` : rowData.url}
      </a>
    </div>
  );

  const searchEnginesBodyTemplate = (rowData: DelistingRequest) => (
    <div className="flex flex-wrap gap-1">
      {rowData.searchEngineResponses?.map((engine, index) => (
        <Badge
          key={index}
          value={engine.engine}
          severity={getStatusSeverity(engine.status)}
        />
      )) || <span className="text-600">-</span>}
    </div>
  );

  const dateBodyTemplate = (date: string) => (
    <span className="text-sm">
      {new Date(date).toLocaleDateString()} {new Date(date).toLocaleTimeString()}
    </span>
  );

  const actionsBodyTemplate = (rowData: DelistingRequest) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-eye"
        size="small"
        text
        rounded
        tooltip="View Details"
        onClick={() => onRequestSelect?.(rowData)}
      />
      
      {(rowData.status === 'failed' || rowData.status === 'cancelled') && (
        <Button
          icon="pi pi-refresh"
          size="small"
          text
          rounded
          severity="warning"
          tooltip="Retry Request"
          onClick={() => handleRetryRequest(rowData.id)}
        />
      )}
      
      {(rowData.status === 'pending' || rowData.status === 'processing') && (
        <Button
          icon="pi pi-times"
          size="small"
          text
          rounded
          severity="danger"
          tooltip="Cancel Request"
          onClick={() => handleCancelRequest(rowData.id)}
        />
      )}
    </div>
  );

  const header = (
    <div className="flex flex-column gap-3">
      <div className="flex flex-wrap gap-3 align-items-center">
        <div className="flex align-items-center gap-2">
          <i className="pi pi-search" />
          <InputText
            value={globalFilterValue}
            onChange={onGlobalFilterChange}
            placeholder="Search requests..."
            className="w-20rem"
          />
        </div>
        
        <Dropdown
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.value)}
          options={statusOptions}
          optionLabel="label"
          optionValue="value"
          placeholder="Filter by Status"
          className="w-12rem"
          showClear
        />
        
        <MultiSelect
          value={searchEngineFilter}
          onChange={(e) => setSearchEngineFilter(e.value)}
          options={searchEngineOptions}
          optionLabel="label"
          optionValue="value"
          placeholder="Filter by Engine"
          className="w-14rem"
          display="chip"
        />
        
        <MultiSelect
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.value)}
          options={priorityOptions}
          optionLabel="label"
          optionValue="value"
          placeholder="Filter by Priority"
          className="w-12rem"
          display="chip"
        />
        
        <Button
          icon="pi pi-refresh"
          rounded
          outlined
          tooltip="Refresh"
          onClick={loadRequests}
        />
      </div>
      
      {selectedRequests.length > 0 && (
        <div className="flex gap-2 align-items-center">
          <span className="text-600">{selectedRequests.length} selected</span>
          <Button
            label="Cancel Selected"
            icon="pi pi-times"
            size="small"
            severity="warning"
            onClick={handleBulkCancel}
          />
          <Button
            label="Retry Selected"
            icon="pi pi-refresh"
            size="small"
            severity="info"
            onClick={handleBulkRetry}
          />
        </div>
      )}
    </div>
  );

  if (error) {
    return (
      <Message 
        severity="error" 
        text={error} 
        className="w-full"
      />
    );
  }

  return (
    <>
      <Toast ref={toast} />
      <DataTable
        value={requests}
        selection={selectedRequests}
        onSelectionChange={(e) => setSelectedRequests(e.value)}
        lazy
        paginator
        first={lazyParams.first}
        rows={lazyParams.rows}
        totalRecords={totalRecords}
        onPage={onPage}
        loading={loading}
        filters={filters}
        globalFilterFields={['url', 'reason']}
        header={header}
        emptyMessage="No delisting requests found."
        scrollable
        scrollHeight="600px"
        className="delisting-requests-table"
      >
        <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
        
        <Column
          field="url"
          header="URL"
          body={urlBodyTemplate}
          style={{ width: '25%' }}
          sortable
        />
        
        <Column
          field="status"
          header="Status"
          body={statusBodyTemplate}
          style={{ width: '10%' }}
          sortable
        />
        
        <Column
          field="priority"
          header="Priority"
          body={priorityBodyTemplate}
          style={{ width: '8%' }}
          sortable
        />
        
        <Column
          header="Search Engines"
          body={searchEnginesBodyTemplate}
          style={{ width: '15%' }}
        />
        
        <Column
          field="createdAt"
          header="Created"
          body={(data) => dateBodyTemplate(data.createdAt)}
          style={{ width: '12%' }}
          sortable
        />
        
        <Column
          field="updatedAt"
          header="Updated"
          body={(data) => dateBodyTemplate(data.updatedAt)}
          style={{ width: '12%' }}
          sortable
        />
        
        <Column
          field="retryCount"
          header="Retries"
          style={{ width: '8%' }}
          sortable
        />
        
        <Column
          header="Actions"
          body={actionsBodyTemplate}
          style={{ width: '10%' }}
        />
      </DataTable>
    </>
  );
};

export default RequestStatusTable;