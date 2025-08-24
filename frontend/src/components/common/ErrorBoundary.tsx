import React, { Component, ReactNode } from 'react';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Message } from 'primereact/message';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    
    // You can also log the error to an error reporting service here
    // logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary p-4">
          <Card className="max-w-lg mx-auto">
            <div className="text-center">
              <i className="pi pi-exclamation-triangle text-6xl text-red-500 mb-4" />
              <h2 className="text-2xl text-900 mb-3">Something went wrong</h2>
              <Message
                severity="error"
                text="We're sorry, but something unexpected happened. Please try refreshing the page."
                className="w-full mb-4"
              />
              
              {import.meta.env.DEV && this.state.error && (
                <details className="text-left mb-4 p-3 bg-gray-100 border-round">
                  <summary className="cursor-pointer font-semibold mb-2">
                    Error Details (Development Only)
                  </summary>
                  <pre className="text-xs overflow-auto">
                    {this.state.error.stack}
                  </pre>
                </details>
              )}

              <div className="flex flex-column sm:flex-row gap-2">
                <Button 
                  label="Try Again" 
                  icon="pi pi-refresh" 
                  onClick={this.handleReset}
                  className="flex-1"
                />
                <Button 
                  label="Reload Page" 
                  icon="pi pi-replay" 
                  outlined
                  onClick={() => window.location.reload()}
                  className="flex-1"
                />
              </div>

              <div className="mt-4">
                <small className="text-600">
                  If this problem persists, please contact{' '}
                  <a href="mailto:support@autodmca.com" className="text-primary">
                    support@autodmca.com
                  </a>
                </small>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;