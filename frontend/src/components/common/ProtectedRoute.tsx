import React, { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useAuth } from '../../hooks/useAuth';

interface ProtectedRouteProps {
  children: ReactNode;
  requiresVerification?: boolean;
}

/**
 * Route guard component that protects authenticated routes
 * Redirects to login if user is not authenticated
 * Shows loading state while authentication is being checked
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiresVerification = false 
}) => {
  const { user, isLoading, isAuthenticated } = useAuth();
  const location = useLocation();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        gap={2}
      >
        <CircularProgress size={60} />
        <Typography variant="h6" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <Navigate 
        to="/login" 
        state={{ from: location }} 
        replace 
      />
    );
  }

  // Check if email verification is required
  if (requiresVerification && user && !user.is_verified) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        gap={2}
        p={3}
      >
        <Typography variant="h5" color="warning.main" gutterBottom>
          Email Verification Required
        </Typography>
        <Typography variant="body1" color="text.secondary" textAlign="center">
          Please verify your email address to access this feature.
          Check your inbox for a verification link.
        </Typography>
      </Box>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;