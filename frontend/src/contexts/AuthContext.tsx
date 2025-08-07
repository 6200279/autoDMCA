import React, { createContext, useState, useEffect, ReactNode, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Toast } from 'primereact/toast';
import { authApi, userApi } from '../services/api';
import { User, UserLogin, UserRegister } from '../types/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface ForgotPasswordData {
  email: string;
}

interface ResetPasswordData {
  token: string;
  password: string;
}

interface VerifyEmailData {
  token: string;
}

interface AuthContextValue extends AuthState {
  login: (credentials: UserLogin) => Promise<void>;
  register: (userData: UserRegister) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshToken: () => Promise<void>;
  getCurrentUser: () => Promise<User | null>;
  verifyEmail: (data: VerifyEmailData) => Promise<void>;
  forgotPassword: (data: ForgotPasswordData) => Promise<void>;
  resetPassword: (data: ResetPasswordData) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();
  const toast = useRef<Toast>(null);

  // Utility function to show toast notifications
  const showToast = (severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail?: string) => {
    toast.current?.show({ 
      severity, 
      summary, 
      detail,
      life: 5000 
    });
  };

  // Check for existing token on mount and fetch user data
  const { refetch: refetchUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await userApi.getCurrentUser();
      return response.data;
    },
    enabled: false,
    retry: false,
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials: UserLogin) => {
      const response = await authApi.login(credentials);
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      setUser(data.user);
      showToast('success', 'Login Successful', 'Welcome back to AutoDMCA!');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Login failed. Please try again.';
      showToast('error', 'Login Failed', message);
      throw error;
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: async (userData: UserRegister) => {
      const response = await authApi.register(userData);
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      setUser(data.user);
      showToast('success', 'Registration Successful', 'Welcome to AutoDMCA! Please verify your email address.');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Registration failed. Please try again.';
      showToast('error', 'Registration Failed', message);
      throw error;
    },
  });

  // Verify Email mutation
  const verifyEmailMutation = useMutation({
    mutationFn: async (data: VerifyEmailData) => {
      const response = await authApi.verifyEmail(data);
      return response.data;
    },
    onSuccess: () => {
      showToast('success', 'Email Verified', 'Your email address has been successfully verified.');
      // Refresh user data to update verification status
      refreshUser();
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Email verification failed. Please try again.';
      showToast('error', 'Verification Failed', message);
      throw error;
    },
  });

  // Forgot Password mutation
  const forgotPasswordMutation = useMutation({
    mutationFn: async (data: ForgotPasswordData) => {
      const response = await authApi.forgotPassword(data);
      return response.data;
    },
    onSuccess: () => {
      showToast('success', 'Reset Email Sent', 'Please check your email for password reset instructions.');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to send reset email. Please try again.';
      showToast('error', 'Request Failed', message);
      throw error;
    },
  });

  // Reset Password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: async (data: ResetPasswordData) => {
      const response = await authApi.resetPassword(data);
      return response.data;
    },
    onSuccess: () => {
      showToast('success', 'Password Reset', 'Your password has been successfully reset. Please log in with your new password.');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Password reset failed. Please try again.';
      showToast('error', 'Reset Failed', message);
      throw error;
    },
  });

  // Refresh Token mutation
  const refreshTokenMutation = useMutation({
    mutationFn: async () => {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      const response = await authApi.refreshToken({ refreshToken });
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refreshToken', data.refresh_token);
      }
    },
    onError: (error: any) => {
      // Clear tokens and redirect to login
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      queryClient.clear();
      showToast('warn', 'Session Expired', 'Please log in again.');
      // Redirect to login page
      window.location.href = '/auth/login';
      throw error;
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: async () => {
      try {
        await authApi.logout();
      } catch (error) {
        // Continue with logout even if API call fails
        console.warn('Logout API call failed:', error);
      }
    },
    onSuccess: () => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      queryClient.clear();
      showToast('info', 'Logged Out', 'You have been successfully logged out.');
    },
  });

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('accessToken');
      
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const { data: userData } = await refetchUser();
        setUser(userData);
      } catch (error) {
        // Token is invalid, try to refresh
        try {
          await refreshTokenMutation.mutateAsync();
          const { data: userData } = await refetchUser();
          setUser(userData);
        } catch (refreshError) {
          // Both token and refresh failed, clear storage
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          console.warn('Authentication failed, cleared tokens from storage');
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [refetchUser]);

  // Set up automatic token refresh
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;

    // Parse token to check expiration
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      const timeUntilExpiry = payload.exp - currentTime;
      
      // Refresh token 5 minutes before it expires
      const refreshTime = Math.max(0, (timeUntilExpiry - 300) * 1000);
      
      const timer = setTimeout(async () => {
        try {
          await refreshTokenMutation.mutateAsync();
        } catch (error) {
          console.warn('Auto token refresh failed:', error);
        }
      }, refreshTime);

      return () => clearTimeout(timer);
    } catch (error) {
      console.warn('Invalid JWT token format:', error);
    }
  }, [user]); // Re-run when user changes (login/logout)

  // Exported functions
  const login = async (credentials: UserLogin): Promise<void> => {
    return loginMutation.mutateAsync(credentials);
  };

  const register = async (userData: UserRegister): Promise<void> => {
    return registerMutation.mutateAsync(userData);
  };

  const logout = async (): Promise<void> => {
    return logoutMutation.mutateAsync();
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const { data: userData } = await refetchUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      throw error;
    }
  };

  const refreshToken = async (): Promise<void> => {
    return refreshTokenMutation.mutateAsync();
  };

  const getCurrentUser = async (): Promise<User | null> => {
    if (user) return user;
    
    try {
      const { data: userData } = await refetchUser();
      setUser(userData);
      return userData;
    } catch (error) {
      console.error('Failed to get current user:', error);
      return null;
    }
  };

  const verifyEmail = async (data: VerifyEmailData): Promise<void> => {
    return verifyEmailMutation.mutateAsync(data);
  };

  const forgotPassword = async (data: ForgotPasswordData): Promise<void> => {
    return forgotPasswordMutation.mutateAsync(data);
  };

  const resetPassword = async (data: ResetPasswordData): Promise<void> => {
    return resetPasswordMutation.mutateAsync(data);
  };

  const value: AuthContextValue = {
    user,
    isLoading: isLoading || 
               loginMutation.isPending || 
               registerMutation.isPending || 
               logoutMutation.isPending ||
               verifyEmailMutation.isPending ||
               forgotPasswordMutation.isPending ||
               resetPasswordMutation.isPending ||
               refreshTokenMutation.isPending,
    isAuthenticated: !!user && !!localStorage.getItem('accessToken'),
    login,
    register,
    logout,
    refreshUser,
    refreshToken,
    getCurrentUser,
    verifyEmail,
    forgotPassword,
    resetPassword,
  };

  return (
    <AuthContext.Provider value={value}>
      <Toast ref={toast} position="top-right" />
      {children}
    </AuthContext.Provider>
  );
};

// Hook for using the AuthContext
export const useAuth = (): AuthContextValue => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Legacy export for backward compatibility
export const useAuthContext = useAuth;

export { AuthContext };
export default AuthContext;