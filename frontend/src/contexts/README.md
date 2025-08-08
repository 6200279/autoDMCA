# AuthContext Documentation

This directory contains the comprehensive authentication system for the AutoDMCA frontend, built with PrimeReact components and TypeScript.

## 🚀 Quick Start

### Basic Setup

```tsx
import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { AuthErrorBoundary } from './contexts/AuthErrorBoundary';
import App from './App';

function Main() {
  return (
    <AuthErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </AuthErrorBoundary>
  );
}
```

### Using the Auth Hook

```tsx
import { useAuth } from './hooks/useAuth';

function MyComponent() {
  const { user, isAuthenticated, login, logout, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  return (
    <div>
      <h1>Welcome, {user?.full_name}!</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

## 📚 API Reference

### AuthContextValue Interface

```tsx
interface AuthContextValue {
  // State
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  // Core Functions
  login: (credentials: UserLogin) => Promise<void>;
  register: (userData: UserRegister) => Promise<void>;
  logout: () => Promise<void>;
  
  // User Management
  refreshUser: () => Promise<void>;
  getCurrentUser: () => Promise<User | null>;
  
  // Token Management
  refreshToken: () => Promise<void>;
  
  // Email & Password Management
  verifyEmail: (data: VerifyEmailData) => Promise<void>;
  forgotPassword: (data: ForgotPasswordData) => Promise<void>;
  resetPassword: (data: ResetPasswordData) => Promise<void>;
}
```

## 🔑 Core Functions

### Authentication

#### `login(credentials)`
Authenticates a user with email and password.

```tsx
const { login } = useAuth();

try {
  await login({
    email: 'user@example.com',
    password: 'password123'
  });
  // Success toast shown automatically
} catch (error) {
  // Error toast shown automatically
  console.error('Login failed:', error);
}
```

#### `register(userData)`
Creates a new user account.

```tsx
const { register } = useAuth();

try {
  await register({
    email: 'user@example.com',
    password: 'password123',
    full_name: 'John Doe',
    company: 'Acme Corp' // optional
  });
} catch (error) {
  console.error('Registration failed:', error);
}
```

#### `logout()`
Logs out the current user and clears tokens.

```tsx
const { logout } = useAuth();

await logout();
// User is logged out, tokens cleared, success toast shown
```

### Email Verification

#### `verifyEmail(data)`
Verifies a user's email address using a token.

```tsx
const { verifyEmail } = useAuth();

try {
  await verifyEmail({ token: 'verification-token-from-email' });
  // Success toast shown, user data refreshed
} catch (error) {
  console.error('Verification failed:', error);
}
```

### Password Recovery

#### `forgotPassword(data)`
Initiates password reset flow by sending reset email.

```tsx
const { forgotPassword } = useAuth();

try {
  await forgotPassword({ email: 'user@example.com' });
  // Success toast shown with instructions
} catch (error) {
  console.error('Failed to send reset email:', error);
}
```

#### `resetPassword(data)`
Completes password reset using token from email.

```tsx
const { resetPassword } = useAuth();

try {
  await resetPassword({
    token: 'reset-token-from-email',
    password: 'newPassword123'
  });
  // Success toast shown, user should login with new password
} catch (error) {
  console.error('Password reset failed:', error);
}
```

### User & Token Management

#### `refreshUser()`
Refreshes user data from the server.

```tsx
const { refreshUser } = useAuth();

await refreshUser();
// User data updated with latest from server
```

#### `getCurrentUser()`
Gets current user data (from cache or server).

```tsx
const { getCurrentUser } = useAuth();

const user = await getCurrentUser();
console.log('Current user:', user);
```

#### `refreshToken()`
Manually refreshes the access token.

```tsx
const { refreshToken } = useAuth();

try {
  await refreshToken();
  // Token refreshed successfully
} catch (error) {
  // User will be redirected to login
  console.error('Token refresh failed:', error);
}
```

## 🎨 Toast Notifications

The AuthContext uses PrimeReact Toast for user notifications. All success and error messages are displayed automatically:

- **Success**: Login, registration, logout, email verification, password reset
- **Error**: Authentication failures, network errors, validation errors
- **Warning**: Session expired, token refresh needed
- **Info**: General information messages

Toast notifications appear in the top-right corner and auto-dismiss after 5 seconds.

## 🔒 Security Features

### Automatic Token Refresh
- Tokens are automatically refreshed 5 minutes before expiration
- Failed refresh attempts redirect user to login
- Refresh logic handles edge cases and race conditions

### Secure Token Storage
- Tokens stored in localStorage (consider httpOnly cookies for production)
- Tokens cleared on logout and authentication errors
- Invalid tokens automatically cleaned up

### Error Handling
- Comprehensive error boundary for authentication failures
- Graceful fallback UI when auth system fails
- Development-only error details for debugging

## 🛡️ Error Boundary

The `AuthErrorBoundary` component catches and handles authentication-related errors:

```tsx
import { AuthErrorBoundary } from './contexts/AuthErrorBoundary';

<AuthErrorBoundary>
  <AuthProvider>
    <App />
  </AuthProvider>
</AuthErrorBoundary>
```

Features:
- Fallback UI for authentication failures
- Retry mechanism with token cleanup
- Development error details
- User-friendly error messages

## 📱 TypeScript Support

Full TypeScript support with comprehensive type definitions:

```tsx
import type { 
  User, 
  UserLogin, 
  UserRegister,
  AuthContextValue 
} from '../types/api';

import type {
  AuthTokenResponse,
  AuthError,
  JWTPayload
} from '../types/auth';
```

## 🧪 Testing

### Mock the Auth Context

```tsx
import { jest } from '@jest/globals';
import type { AuthContextValue } from '../contexts/AuthContext';

const mockAuthContext: AuthContextValue = {
  user: null,
  isLoading: false,
  isAuthenticated: false,
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  refreshUser: jest.fn(),
  getCurrentUser: jest.fn(),
  refreshToken: jest.fn(),
  verifyEmail: jest.fn(),
  forgotPassword: jest.fn(),
  resetPassword: jest.fn(),
};

jest.mock('../hooks/useAuth', () => ({
  useAuth: () => mockAuthContext
}));
```

## 🔧 Configuration

### Environment Variables
Set these in your `.env` file:

```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
NODE_ENV=development
```

### API Integration
The AuthContext integrates with these backend endpoints:

- `POST /auth/login` - User login
- `POST /auth/register` - User registration  
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Token refresh
- `POST /auth/verify-email` - Email verification
- `POST /auth/forgot-password` - Initiate password reset
- `POST /auth/reset-password` - Complete password reset
- `GET /users/me` - Get current user

## 🔄 Migration from Material-UI

This implementation replaces the previous Material-UI version:

| Old (Material-UI) | New (PrimeReact) |
|------------------|------------------|
| `useSnackbar()` | `Toast` component |
| `enqueueSnackbar()` | `toast.current?.show()` |
| Material-UI themes | PrimeReact themes |

## 📝 Best Practices

1. **Always wrap with ErrorBoundary**: Use `AuthErrorBoundary` for error handling
2. **Handle loading states**: Check `isLoading` before rendering auth-dependent UI
3. **Use TypeScript**: Leverage full type safety with provided interfaces
4. **Error handling**: Let the context handle notifications, add custom logic as needed
5. **Token management**: Don't manually manage tokens, use provided functions
6. **Testing**: Mock the auth context in tests for predictable behavior

## 🐛 Common Issues

### "useAuth must be used within an AuthProvider"
Ensure your component is wrapped in `AuthProvider`:

```tsx
<AuthProvider>
  <YourComponent />
</AuthProvider>
```

### Tokens not persisting across sessions
Check localStorage is available and not being cleared by other code.

### Network errors during token refresh
The context handles this automatically by redirecting to login.

## 🔮 Future Enhancements

Planned features:
- Two-factor authentication support
- Social login integration (Google, GitHub)
- Session management (multiple devices)
- Biometric authentication
- Remember device functionality
- Advanced security analytics

---

For more examples, see `src/examples/AuthContextUsage.tsx`