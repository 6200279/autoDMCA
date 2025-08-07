import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '@services/api';
import { wsService } from '@services/websocket';
import { User, AuthState, LoginCredentials, RegisterData } from '@types/index';

// Auth Context
interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth Provider Component
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const queryClient = useQueryClient();

  // Check if user is already authenticated on app load
  const { data: profileData, isLoading: profileLoading } = useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => {
      const token = localStorage.getItem('authToken');
      if (!token) throw new Error('No token found');
      
      const response = await apiService.getProfile();
      return response.data;
    },
    enabled: !!localStorage.getItem('authToken'),
    retry: false,
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: apiService.login,
    onSuccess: (response) => {
      const { user, token } = response.data;
      localStorage.setItem('authToken', token);
      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
      
      // Connect to WebSocket with new token
      wsService.connect(token);
      wsService.joinUserRoom(user.id);
      
      queryClient.setQueryData(['user-profile'], user);
    },
    onError: (error) => {
      console.error('Login failed:', error);
      setAuthState(prev => ({ ...prev, isLoading: false }));
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: apiService.register,
    onSuccess: (response) => {
      const { user, token } = response.data;
      localStorage.setItem('authToken', token);
      setAuthState({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
      
      wsService.connect(token);
      wsService.joinUserRoom(user.id);
      
      queryClient.setQueryData(['user-profile'], user);
    },
    onError: (error) => {
      console.error('Registration failed:', error);
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: apiService.logout,
    onSuccess: () => {
      localStorage.removeItem('authToken');
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
      
      // Disconnect WebSocket
      wsService.disconnect();
      
      // Clear all cached data
      queryClient.clear();
    },
  });

  // Update auth state when profile data is loaded
  useEffect(() => {
    if (profileData) {
      setAuthState({
        user: profileData,
        isAuthenticated: true,
        isLoading: false,
      });
      
      // Connect to WebSocket if not already connected
      if (!wsService.isConnected()) {
        wsService.connect();
        wsService.joinUserRoom(profileData.id);
      }
    } else if (!profileLoading && !localStorage.getItem('authToken')) {
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  }, [profileData, profileLoading]);

  // Handle logout on token expiry
  useEffect(() => {
    const handleTokenExpiry = () => {
      setAuthState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
      wsService.disconnect();
      queryClient.clear();
    };

    // Listen for 401 responses
    window.addEventListener('unauthorized', handleTokenExpiry);
    return () => window.removeEventListener('unauthorized', handleTokenExpiry);
  }, [queryClient]);

  const login = async (credentials: LoginCredentials) => {
    await loginMutation.mutateAsync(credentials);
  };

  const register = async (data: RegisterData) => {
    await registerMutation.mutateAsync(data);
  };

  const logout = async () => {
    await logoutMutation.mutateAsync();
  };

  const updateUser = (user: User) => {
    setAuthState(prev => ({ ...prev, user }));
    queryClient.setQueryData(['user-profile'], user);
  };

  const contextValue: AuthContextType = {
    ...authState,
    login,
    register,
    logout,
    updateUser,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Additional auth-related hooks
export const useRequireAuth = () => {
  const { isAuthenticated, isLoading } = useAuth();
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      window.location.href = '/login';
    }
  }, [isAuthenticated, isLoading]);

  return { isAuthenticated, isLoading };
};

export const useAuthGuard = (redirectTo = '/login') => {
  const { isAuthenticated, isLoading, user } = useAuth();
  
  if (isLoading) {
    return { isLoading: true, isAuthenticated: false, user: null };
  }
  
  if (!isAuthenticated) {
    window.location.href = redirectTo;
    return { isLoading: false, isAuthenticated: false, user: null };
  }
  
  return { isLoading: false, isAuthenticated: true, user };
};