import React from 'react';
import { Message } from 'primereact/message';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { ApiError } from '../../utils/apiErrorHandler';
import ComingSoon from './ComingSoon';

interface ApiErrorDisplayProps {
  error: ApiError;
  onRetry?: () => void;
  showRetryButton?: boolean;
  showComingSoonForUnimplemented?: boolean;
  className?: string;
}

const ApiErrorDisplay: React.FC<ApiErrorDisplayProps> = ({
  error,
  onRetry,
  showRetryButton = true,
  showComingSoonForUnimplemented = true,
  className = ""
}) => {
  // Show Coming Soon component for unimplemented features
  if (error.isNotImplemented && showComingSoonForUnimplemented) {
    const featureName = (error as any).featureName || 'This Feature';
    return (
      <ComingSoon 
        featureName={featureName}
        description="This feature is currently under development and will be available in a future update."
        contactSupport={true}
      />
    );
  }

  // Get appropriate severity and icon
  const getSeverity = (): "success" | "info" | "warn" | "error" => {
    if (error.isNotImplemented) return 'info';
    if (error.isNetworkError) return 'warn';
    if (error.isServerError) return 'error';
    if (error.isClientError) return 'warn';
    return 'error';
  };

  const getIcon = (): string => {
    if (error.isNotImplemented) return 'pi-wrench';
    if (error.isNetworkError) return 'pi-wifi';
    if (error.isServerError) return 'pi-server';
    return 'pi-exclamation-triangle';
  };

  // Show inline message for minor errors
  if (!error.isServerError && !error.isNetworkError) {
    return (
      <div className={className}>
        <Message 
          severity={getSeverity()} 
          text={error.message}
          className="w-full"
        />
        {showRetryButton && onRetry && (
          <div className="mt-2">
            <Button 
              label="Try Again" 
              icon="pi pi-refresh" 
              size="small"
              outlined
              onClick={onRetry}
            />
          </div>
        )}
      </div>
    );
  }

  // Show card for major errors
  return (
    <div className={`flex justify-content-center align-items-center ${className}`}>
      <Card className="w-full max-w-600px">
        <div className="text-center">
          <i className={`pi ${getIcon()} text-6xl mb-3`} 
             style={{ color: getSeverity() === 'error' ? '#e74c3c' : '#f39c12' }} />
          
          <h3 className="text-2xl mb-3">
            {error.isNetworkError ? 'Connection Problem' : 
             error.isServerError ? 'Service Unavailable' : 
             'Something Went Wrong'}
          </h3>
          
          <Message 
            severity={getSeverity()} 
            text={error.message}
            className="mb-4 w-full"
          />

          {error.isNetworkError && (
            <div className="mb-4">
              <p className="text-600">Please check:</p>
              <ul className="text-left text-600 list-none">
                <li>• Your internet connection</li>
                <li>• VPN or firewall settings</li>
                <li>• Try refreshing the page</li>
              </ul>
            </div>
          )}

          {error.isServerError && (
            <div className="mb-4">
              <p className="text-600">
                Our team has been notified and is working on a fix. 
                Please try again in a few minutes.
              </p>
            </div>
          )}

          <div className="flex flex-column sm:flex-row gap-2 justify-content-center">
            {showRetryButton && onRetry && (
              <Button 
                label="Try Again" 
                icon="pi pi-refresh"
                onClick={onRetry}
              />
            )}
            <Button 
              label="Refresh Page" 
              icon="pi pi-replay"
              outlined
              onClick={() => window.location.reload()}
            />
          </div>

          <div className="mt-4">
            <small className="text-600">
              Need help? Contact{' '}
              <a href="mailto:support@autodmca.com" className="text-primary no-underline">
                support@autodmca.com
              </a>
            </small>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ApiErrorDisplay;