import { useAuth as useAuthHook } from '../contexts/AuthContext';

/**
 * Custom hook for accessing authentication context
 * Provides convenient access to user state and auth functions
 * 
 * @example
 * const { user, login, logout, isLoading, isAuthenticated } = useAuth();
 * 
 * // Login
 * await login({ email: 'user@example.com', password: 'password' });
 * 
 * // Register
 * await register({ email: 'user@example.com', password: 'password', full_name: 'User Name' });
 * 
 * // Logout
 * await logout();
 * 
 * // Email verification
 * await verifyEmail({ token: 'verification-token' });
 * 
 * // Password reset flow
 * await forgotPassword({ email: 'user@example.com' });
 * await resetPassword({ token: 'reset-token', password: 'new-password' });
 */
export const useAuth = useAuthHook;

export default useAuth;