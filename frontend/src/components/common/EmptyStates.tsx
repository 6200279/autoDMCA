import React from 'react';
import { classNames } from 'primereact/utils';
import { EnhancedButton } from './EnhancedButton';
import { SecurityShield } from './TrustIndicators';

export interface EmptyStateProps {
  variant?: 'default' | 'search' | 'error' | 'loading' | 'security' | 'success';
  size?: 'sm' | 'md' | 'lg';
  title: string;
  description?: string;
  icon?: React.ReactNode | string;
  primaryAction?: {
    label: string;
    onClick: () => void;
    loading?: boolean;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'default',
  size = 'md',
  title,
  description,
  icon,
  primaryAction,
  secondaryAction,
  className
}) => {
  const getVariantConfig = () => {
    switch (variant) {
      case 'search':
        return {
          defaultIcon: '🔍',
          containerClass: 'empty-state-search',
          iconColor: 'var(--autodmca-info-500)'
        };
      case 'error':
        return {
          defaultIcon: '❌',
          containerClass: 'empty-state-error',
          iconColor: 'var(--autodmca-danger-500)'
        };
      case 'loading':
        return {
          defaultIcon: '⏳',
          containerClass: 'empty-state-loading',
          iconColor: 'var(--autodmca-warning-500)'
        };
      case 'security':
        return {
          defaultIcon: <SecurityShield level="premium" size="lg" />,
          containerClass: 'empty-state-security',
          iconColor: 'var(--autodmca-primary-500)'
        };
      case 'success':
        return {
          defaultIcon: '✅',
          containerClass: 'empty-state-success',
          iconColor: 'var(--autodmca-success-500)'
        };
      default:
        return {
          defaultIcon: '📄',
          containerClass: 'empty-state-default',
          iconColor: 'var(--autodmca-text-muted)'
        };
    }
  };

  const config = getVariantConfig();

  return (
    <div className={classNames(
      'empty-state',
      `empty-state-${size}`,
      config.containerClass,
      className
    )}>
      <div className="empty-state-content">
        <div className="empty-state-icon" style={{ color: config.iconColor }}>
          {icon || config.defaultIcon}
        </div>
        
        <div className="empty-state-text">
          <h3 className="empty-state-title">{title}</h3>
          {description && (
            <p className="empty-state-description">{description}</p>
          )}
        </div>

        {(primaryAction || secondaryAction) && (
          <div className="empty-state-actions">
            {primaryAction && (
              <EnhancedButton
                variant="primary"
                size={size === 'lg' ? 'lg' : 'md'}
                elevation="2"
                loading={primaryAction.loading}
                onClick={primaryAction.onClick}
              >
                {primaryAction.label}
              </EnhancedButton>
            )}
            {secondaryAction && (
              <EnhancedButton
                variant="outline"
                size={size === 'lg' ? 'lg' : 'md'}
                onClick={secondaryAction.onClick}
              >
                {secondaryAction.label}
              </EnhancedButton>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export interface NoDataProps {
  type?: 'profiles' | 'infringements' | 'takedowns' | 'reports' | 'generic';
  title?: string;
  description?: string;
  createAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const NoData: React.FC<NoDataProps> = ({
  type = 'generic',
  title,
  description,
  createAction,
  className
}) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'profiles':
        return {
          title: title || 'No Protected Profiles',
          description: description || 'Start protecting your content by creating your first profile. Add your social media accounts and content to monitor for infringements.',
          icon: '👤',
          defaultAction: 'Create First Profile'
        };
      case 'infringements':
        return {
          title: title || 'No Infringements Detected',
          description: description || 'Great news! No copyright infringements have been detected for your protected content. Our system is actively monitoring.',
          icon: <SecurityShield level="premium" size="lg" />,
          defaultAction: 'View Protection Status'
        };
      case 'takedowns':
        return {
          title: title || 'No Takedown Requests',
          description: description || 'You haven\'t submitted any DMCA takedown requests yet. When infringements are detected, you can quickly generate and send takedown notices.',
          icon: '⚖️',
          defaultAction: 'Learn About DMCA'
        };
      case 'reports':
        return {
          title: title || 'No Reports Available',
          description: description || 'Reports will appear here once you have activity data. Start by adding profiles and monitoring for infringements.',
          icon: '📊',
          defaultAction: 'Get Started'
        };
      default:
        return {
          title: title || 'No Data Available',
          description: description || 'There\'s no data to display right now. Check back later or try refreshing the page.',
          icon: '📄',
          defaultAction: 'Refresh'
        };
    }
  };

  const config = getTypeConfig();

  return (
    <EmptyState
      variant={type === 'infringements' ? 'success' : 'default'}
      size="lg"
      title={config.title}
      description={config.description}
      icon={config.icon}
      primaryAction={createAction ? {
        label: createAction.label,
        onClick: createAction.onClick
      } : undefined}
      className={className}
    />
  );
};

export interface LoadingStateProps {
  type?: 'dashboard' | 'table' | 'card' | 'list';
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'card',
  message = 'Loading...',
  size = 'md',
  className
}) => {
  return (
    <EmptyState
      variant="loading"
      size={size}
      title={message}
      description="Please wait while we fetch your data"
      icon="⏳"
      className={className}
    />
  );
};

export interface ErrorStateProps {
  title?: string;
  description?: string;
  retryAction?: () => void;
  supportAction?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  description = 'We encountered an error while loading your data. Please try again or contact support if the problem persists.',
  retryAction,
  supportAction,
  className
}) => {
  return (
    <EmptyState
      variant="error"
      size="lg"
      title={title}
      description={description}
      primaryAction={retryAction ? {
        label: 'Try Again',
        onClick: retryAction
      } : undefined}
      secondaryAction={supportAction ? {
        label: 'Contact Support',
        onClick: supportAction
      } : undefined}
      className={className}
    />
  );
};