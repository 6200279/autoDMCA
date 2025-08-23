import React from 'react';
import { Skeleton } from 'primereact/skeleton';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Card } from 'primereact/card';

interface ApiLoadingStateProps {
  type?: 'spinner' | 'skeleton' | 'card' | 'table' | 'dashboard';
  message?: string;
  size?: 'small' | 'medium' | 'large';
  rows?: number;
  className?: string;
}

const ApiLoadingState: React.FC<ApiLoadingStateProps> = ({
  type = 'spinner',
  message = 'Loading...',
  size = 'medium',
  rows = 5,
  className = ""
}) => {
  const getSpinnerSize = () => {
    switch (size) {
      case 'small': return '2rem';
      case 'large': return '4rem';
      default: return '3rem';
    }
  };

  const renderSpinner = () => (
    <div className={`flex flex-column align-items-center justify-content-center p-4 ${className}`}>
      <ProgressSpinner 
        style={{ width: getSpinnerSize(), height: getSpinnerSize() }}
        strokeWidth="4"
      />
      {message && (
        <p className="mt-3 text-600 text-center">{message}</p>
      )}
    </div>
  );

  const renderSkeleton = () => (
    <div className={`p-4 ${className}`}>
      <Skeleton width="100%" height="2rem" className="mb-3" />
      <div className="flex gap-3">
        <Skeleton width="30%" height="1.5rem" />
        <Skeleton width="50%" height="1.5rem" />
        <Skeleton width="20%" height="1.5rem" />
      </div>
    </div>
  );

  const renderCardSkeleton = () => (
    <div className={`grid ${className}`}>
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="col-12 md:col-4">
          <Card>
            <Skeleton width="100%" height="8rem" className="mb-3" />
            <Skeleton width="80%" height="1.5rem" className="mb-2" />
            <Skeleton width="60%" height="1rem" />
          </Card>
        </div>
      ))}
    </div>
  );

  const renderTableSkeleton = () => (
    <div className={`p-4 ${className}`}>
      <Skeleton width="100%" height="3rem" className="mb-3" />
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex gap-3 mb-2">
          <Skeleton width="20%" height="2rem" />
          <Skeleton width="30%" height="2rem" />
          <Skeleton width="25%" height="2rem" />
          <Skeleton width="15%" height="2rem" />
          <Skeleton width="10%" height="2rem" />
        </div>
      ))}
    </div>
  );

  const renderDashboardSkeleton = () => (
    <div className={`p-4 ${className}`}>
      {/* Header */}
      <div className="flex justify-content-between align-items-center mb-4">
        <Skeleton width="200px" height="2.5rem" />
        <Skeleton width="100px" height="2rem" />
      </div>
      
      {/* Stats Cards */}
      <div className="grid mb-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="col-12 md:col-3">
            <Card>
              <div className="flex justify-content-between align-items-center">
                <div>
                  <Skeleton width="120px" height="1rem" className="mb-2" />
                  <Skeleton width="80px" height="2rem" />
                </div>
                <Skeleton width="3rem" height="3rem" borderRadius="50%" />
              </div>
            </Card>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid">
        <div className="col-12 md:col-8">
          <Card>
            <Skeleton width="150px" height="1.5rem" className="mb-3" />
            <Skeleton width="100%" height="20rem" />
          </Card>
        </div>
        <div className="col-12 md:col-4">
          <Card>
            <Skeleton width="120px" height="1.5rem" className="mb-3" />
            <div className="flex flex-column gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="flex justify-content-between align-items-center">
                  <Skeleton width="100px" height="1rem" />
                  <Skeleton width="60px" height="1.5rem" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );

  switch (type) {
    case 'skeleton':
      return renderSkeleton();
    case 'card':
      return renderCardSkeleton();
    case 'table':
      return renderTableSkeleton();
    case 'dashboard':
      return renderDashboardSkeleton();
    default:
      return renderSpinner();
  }
};

export default ApiLoadingState;