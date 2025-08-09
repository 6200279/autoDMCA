import React, { Component, ReactNode } from 'react';
import { Message } from 'primereact/message';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';

interface AuthErrorBoundaryProps {
  children: ReactNode;
}

interface AuthErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: string | null;
}

/**
 * Error Boundary specifically designed for authentication-related errors
 * Provides a fallback UI when authentication context fails
 */
export class AuthErrorBoundary extends Component<AuthErrorBoundaryProps, AuthErrorBoundaryState> {
  constructor(props: AuthErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): AuthErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: error.stack || 'No additional error information available.'
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log the error for debugging
    console.error('Auth Error Boundary caught an error:', error, errorInfo);
    
    // You could also log to an error reporting service here
    // errorReportingService.captureException(error, { extra: errorInfo });

    this.setState({
      hasError: true,
      error,
      errorInfo: errorInfo.componentStack || null
    });
  }

  handleRetry = () => {
    // Clear local storage and reset state
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
    
    // Reload the page to reinitialize the app
    window.location.reload();
  };

  handleLoginRedirect = () => {
    // Clear tokens and redirect to login
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.location.href = '/auth/login';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex align-items-center justify-content-center min-h-screen p-4">
          <Card 
            title="Authentication Error" 
            className="max-w-30rem w-full"
            footer={
              <div className="flex justify-content-between">
                <Button 
                  label="Try Again" 
                  icon="pi pi-refresh" 
                  onClick={this.handleRetry}
                  className="p-button-outlined"
                />
                <Button 
                  label="Go to Login" 
                  icon="pi pi-sign-in" 
                  onClick={this.handleLoginRedirect}
                />
              </div>
            }
          >
            <div className="space-y-3">
              <Message 
                severity="error" 
                text="An error occurred while loading the authentication system." 
              />
              
              <div className="text-sm text-600">
                <p className="mb-2">This error typically occurs when:</p>
                <ul className="list-disc ml-4">
                  <li>Your session has expired</li>
                  <li>There's a network connectivity issue</li>
                  <li>The authentication service is temporarily unavailable</li>
                </ul>
              </div>
              
              {process.env.NODE_ENV === 'development' && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-sm font-medium">
                    Technical Details (Development Only)
                  </summary>
                  <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                    <p><strong>Error:</strong> {this.state.error?.message}</p>
                    {this.state.errorInfo && (
                      <pre className="mt-2 whitespace-pre-wrap">
                        {this.state.errorInfo}
                      </pre>
                    )}
                  </div>
                </details>
              )}
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default AuthErrorBoundary;