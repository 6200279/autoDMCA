import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { useApiCall, useApiCallWithFallback } from '../../hooks/useApiCall';
import { dashboardApi, adminApi } from '../../services/api';
import ApiErrorDisplay from '../common/ApiErrorDisplay';
import ApiLoadingState from '../common/ApiLoadingState';

// Example component showing how to use the new API error handling system
const ApiCallExample: React.FC = () => {
  // Example 1: Working API call with error handling
  const { 
    data: dashboardData, 
    loading: dashboardLoading, 
    error: dashboardError, 
    execute: loadDashboard 
  } = useApiCall(() => dashboardApi.getStats());

  // Example 2: API call that will fail (admin API not implemented) with fallback
  const { 
    data: adminData, 
    loading: adminLoading, 
    error: adminError, 
    execute: loadAdmin,
    isFeatureNotAvailable 
  } = useApiCallWithFallback(
    () => adminApi.getDashboardStats(),
    { message: 'Admin features coming soon!' }
  );

  return (
    <div className="grid p-4">
      <div className="col-12">
        <h2>API Error Handling Examples</h2>
        <p className="text-600 mb-4">
          This demonstrates the new API error handling system with proper loading states and user-friendly error messages.
        </p>
      </div>

      {/* Example 1: Working API */}
      <div className="col-12 md:col-6">
        <Card title="Working API Example" className="h-full">
          <div className="mb-3">
            <Button 
              label="Load Dashboard Stats" 
              icon="pi pi-refresh"
              onClick={() => loadDashboard()}
              loading={dashboardLoading}
              className="w-full"
            />
          </div>

          {dashboardLoading && (
            <ApiLoadingState 
              type="spinner" 
              message="Loading dashboard data..."
              size="small"
            />
          )}

          {dashboardError && (
            <ApiErrorDisplay 
              error={dashboardError}
              onRetry={() => loadDashboard()}
              className="mt-3"
            />
          )}

          {dashboardData && !dashboardLoading && !dashboardError && (
            <div className="text-green-600">
              <i className="pi pi-check-circle mr-2" />
              Dashboard data loaded successfully!
            </div>
          )}
        </Card>
      </div>

      {/* Example 2: Non-implemented API */}
      <div className="col-12 md:col-6">
        <Card title="Unimplemented API Example" className="h-full">
          <div className="mb-3">
            <Button 
              label="Load Admin Stats" 
              icon="pi pi-refresh"
              onClick={() => loadAdmin()}
              loading={adminLoading}
              className="w-full"
            />
          </div>

          {adminLoading && (
            <ApiLoadingState 
              type="spinner" 
              message="Loading admin data..."
              size="small"
            />
          )}

          {adminError && (
            <ApiErrorDisplay 
              error={adminError}
              onRetry={() => loadAdmin()}
              showComingSoonForUnimplemented={true}
              className="mt-3"
            />
          )}

          {adminData && !adminLoading && !adminError && (
            <div className="text-blue-600">
              <i className="pi pi-info-circle mr-2" />
              {typeof adminData === 'object' && 'message' in adminData 
                ? adminData.message 
                : 'Admin data loaded with fallback!'}
            </div>
          )}

          {isFeatureNotAvailable && (
            <div className="mt-2">
              <small className="text-500">
                This demonstrates graceful fallback for unimplemented features.
              </small>
            </div>
          )}
        </Card>
      </div>

      {/* Loading State Examples */}
      <div className="col-12">
        <Card title="Loading State Examples">
          <div className="grid">
            <div className="col-12 md:col-3">
              <h4>Spinner Loading</h4>
              <ApiLoadingState 
                type="spinner" 
                message="Loading data..." 
                size="small"
              />
            </div>
            <div className="col-12 md:col-3">
              <h4>Table Loading</h4>
              <ApiLoadingState 
                type="table" 
                rows={3}
              />
            </div>
            <div className="col-12 md:col-3">
              <h4>Card Loading</h4>
              <ApiLoadingState 
                type="card"
              />
            </div>
            <div className="col-12 md:col-3">
              <h4>Skeleton Loading</h4>
              <ApiLoadingState 
                type="skeleton"
              />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ApiCallExample;