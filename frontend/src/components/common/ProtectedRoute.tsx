import React, { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Message } from 'primereact/message';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
  requiresVerification?: boolean;
  roles?: string[];
  redirectTo?: string;
}

/**
 * Route guard component that protects authenticated routes
 * Redirects to login if user is not authenticated
 * Shows loading state while authentication is being checked
 * Supports role-based access control
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiresVerification = false,
  roles = [],
  redirectTo = '/login'
}) => {
  const { user, isLoading, isAuthenticated } = useAuth();
  const location = useLocation();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div 
        className="flex flex-column align-items-center justify-content-center" 
        style={{ minHeight: '100vh', gap: '1rem' }}
      >
        <ProgressSpinner 
          style={{ width: '60px', height: '60px' }} 
          strokeWidth="4" 
          animationDuration="1s" 
        />
        <p className="text-lg text-color-secondary m-0">Loading...</p>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <Navigate 
        to={redirectTo} 
        state={{ from: location.pathname + location.search }} 
        replace 
      />
    );
  }

  // Check if email verification is required
  if (requiresVerification && user && !user.is_verified) {
    return (
      <div 
        className="flex flex-column align-items-center justify-content-center p-4" 
        style={{ minHeight: '100vh', gap: '1.5rem' }}
      >
        <Message
          severity="warn"
          text="Email Verification Required"
          style={{ 
            fontSize: '1.25rem', 
            fontWeight: 'bold',
            marginBottom: '0.5rem'
          }}
        />
        <div className="text-center">
          <p className="text-color-secondary m-0 line-height-3">
            Please verify your email address to access this feature.
            <br />
            Check your inbox for a verification link.
          </p>
        </div>
      </div>
    );
  }

  // Check role-based access control
  if (roles.length > 0 && user) {
    const hasRequiredRole = roles.some(role => {
      switch (role.toLowerCase()) {
        case 'admin':
        case 'superuser':
          return user.is_superuser;
        case 'verified':
          return user.is_verified;
        case 'active':
          return user.is_active;
        default:
          return false;
      }
    });

    if (!hasRequiredRole) {
      return (
        <div 
          className="flex flex-column align-items-center justify-content-center p-4" 
          style={{ minHeight: '100vh', gap: '1.5rem' }}
        >
          <Message
            severity="error"
            text="Access Denied"
            style={{ 
              fontSize: '1.25rem', 
              fontWeight: 'bold',
              marginBottom: '0.5rem'
            }}
          />
          <div className="text-center">
            <p className="text-color-secondary m-0 line-height-3">
              You don't have permission to access this resource.
              <br />
              Contact your administrator if you believe this is an error.
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;