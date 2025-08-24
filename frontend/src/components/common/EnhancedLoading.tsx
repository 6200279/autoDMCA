import React from 'react';
import { Skeleton } from 'primereact/skeleton';
import { ProgressSpinner } from 'primereact/progressspinner';
import { classNames } from 'primereact/utils';

export interface EnhancedLoadingProps {
  type?: 'spinner' | 'skeleton' | 'dots' | 'pulse';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'card' | 'list' | 'table' | 'dashboard' | 'custom';
  lines?: number;
  showAvatar?: boolean;
  showHeader?: boolean;
  message?: string;
  className?: string;
}

export const EnhancedLoading: React.FC<EnhancedLoadingProps> = ({
  type = 'skeleton',
  size = 'md',
  variant = 'card',
  lines = 3,
  showAvatar = false,
  showHeader = false,
  message,
  className
}) => {
  const getSpinnerSize = () => {
    switch (size) {
      case 'sm': return '2rem';
      case 'md': return '3rem';
      case 'lg': return '4rem';
      case 'xl': return '5rem';
      default: return '3rem';
    }
  };

  const renderSpinner = () => (
    <div className={classNames('enhanced-loading-spinner', `enhanced-loading-${size}`, className)}>
      <ProgressSpinner 
        style={{ width: getSpinnerSize(), height: getSpinnerSize() }}
        strokeWidth="3"
        animationDuration="1s"
      />
      {message && <p className="enhanced-loading-message">{message}</p>}
    </div>
  );

  const renderDots = () => (
    <div className={classNames('enhanced-loading-dots', `enhanced-loading-${size}`, className)}>
      <div className="dots">
        <div className="dot"></div>
        <div className="dot"></div>
        <div className="dot"></div>
      </div>
      {message && <p className="enhanced-loading-message">{message}</p>}
    </div>
  );

  const renderPulse = () => (
    <div className={classNames('enhanced-loading-pulse', `enhanced-loading-${size}`, className)}>
      <div className="pulse-circle"></div>
      {message && <p className="enhanced-loading-message">{message}</p>}
    </div>
  );

  const renderCardSkeleton = () => (
    <div className={classNames('enhanced-loading-skeleton', 'skeleton-card', `enhanced-loading-${size}`, className)}>
      {showHeader && (
        <div className="skeleton-header">
          {showAvatar && <Skeleton shape="circle" size="3rem" className="mr-3" />}
          <div className="skeleton-header-content">
            <Skeleton width="60%" height="1.2rem" className="mb-2" />
            <Skeleton width="40%" height="1rem" />
          </div>
        </div>
      )}
      <div className="skeleton-content">
        {Array.from({ length: lines }, (_, i) => (
          <Skeleton 
            key={i} 
            width={i === lines - 1 ? '70%' : '100%'} 
            height="1rem" 
            className="mb-2" 
          />
        ))}
      </div>
    </div>
  );

  const renderListSkeleton = () => (
    <div className={classNames('enhanced-loading-skeleton', 'skeleton-list', `enhanced-loading-${size}`, className)}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton-list-item">
          {showAvatar && <Skeleton shape="circle" size="2.5rem" className="mr-3" />}
          <div className="skeleton-list-content">
            <Skeleton width="70%" height="1rem" className="mb-1" />
            <Skeleton width="50%" height="0.8rem" />
          </div>
        </div>
      ))}
    </div>
  );

  const renderTableSkeleton = () => (
    <div className={classNames('enhanced-loading-skeleton', 'skeleton-table', `enhanced-loading-${size}`, className)}>
      {/* Table header */}
      <div className="skeleton-table-header">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} width="100%" height="2rem" />
        ))}
      </div>
      {/* Table rows */}
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton-table-row">
          {Array.from({ length: 4 }, (_, j) => (
            <Skeleton key={j} width="100%" height="1.5rem" />
          ))}
        </div>
      ))}
    </div>
  );

  const renderDashboardSkeleton = () => (
    <div className={classNames('enhanced-loading-skeleton', 'skeleton-dashboard', `enhanced-loading-${size}`, className)}>
      {/* Stats cards row */}
      <div className="skeleton-stats-row">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton-stat-card">
            <Skeleton width="100%" height="3rem" className="mb-2" />
            <Skeleton width="60%" height="1rem" />
          </div>
        ))}
      </div>
      
      {/* Chart and table row */}
      <div className="skeleton-content-row">
        <div className="skeleton-chart-section">
          <Skeleton width="100%" height="20rem" />
        </div>
        <div className="skeleton-sidebar-section">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="skeleton-sidebar-item">
              <Skeleton width="100%" height="2.5rem" className="mb-2" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderCustomSkeleton = () => (
    <div className={classNames('enhanced-loading-skeleton', 'skeleton-custom', `enhanced-loading-${size}`, className)}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton 
          key={i} 
          width="100%" 
          height="1rem" 
          className="mb-2" 
        />
      ))}
    </div>
  );

  const renderSkeleton = () => {
    switch (variant) {
      case 'card':
        return renderCardSkeleton();
      case 'list':
        return renderListSkeleton();
      case 'table':
        return renderTableSkeleton();
      case 'dashboard':
        return renderDashboardSkeleton();
      case 'custom':
        return renderCustomSkeleton();
      default:
        return renderCardSkeleton();
    }
  };

  switch (type) {
    case 'spinner':
      return renderSpinner();
    case 'dots':
      return renderDots();
    case 'pulse':
      return renderPulse();
    case 'skeleton':
    default:
      return renderSkeleton();
  }
};