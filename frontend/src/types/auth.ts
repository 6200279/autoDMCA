/**
 * Additional authentication-specific type definitions
 * Extends the base API types with auth-specific interfaces
 */

// Token response from login/register
export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: import('./api').User;
}

// JWT Token payload interface
export interface JWTPayload {
  sub: string; // subject (user ID)
  email: string;
  exp: number; // expiration timestamp
  iat: number; // issued at timestamp
  jti: string; // JWT ID
  is_superuser?: boolean;
  is_verified?: boolean;
}

// Authentication error types
export enum AuthErrorType {
  INVALID_CREDENTIALS = 'invalid_credentials',
  TOKEN_EXPIRED = 'token_expired',
  TOKEN_INVALID = 'token_invalid',
  EMAIL_NOT_VERIFIED = 'email_not_verified',
  ACCOUNT_DISABLED = 'account_disabled',
  RATE_LIMITED = 'rate_limited',
  NETWORK_ERROR = 'network_error',
  SERVER_ERROR = 'server_error',
  VALIDATION_ERROR = 'validation_error'
}

export interface AuthError {
  type: AuthErrorType;
  message: string;
  details?: Record<string, any>;
  field?: string; // For validation errors
}

// Password strength requirements
export interface PasswordRequirements {
  minLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSpecialChars: boolean;
  forbiddenPatterns?: string[];
}

// Authentication configuration
export interface AuthConfig {
  tokenRefreshThreshold: number; // seconds before expiry to refresh
  maxLoginAttempts: number;
  lockoutDuration: number; // seconds
  sessionTimeout: number; // seconds of inactivity
  passwordRequirements: PasswordRequirements;
}

// User registration with additional validation
export interface UserRegisterExtended {
  email: string;
  password: string;
  confirmPassword: string;
  full_name: string;
  phone?: string;
  company?: string;
  acceptTerms: boolean;
  marketingConsent?: boolean;
}

// Password change request
export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

// Social authentication providers
export enum SocialProvider {
  GOOGLE = 'google',
  FACEBOOK = 'facebook',
  GITHUB = 'github',
  LINKEDIN = 'linkedin'
}

export interface SocialAuthData {
  provider: SocialProvider;
  token: string;
  redirectUri?: string;
}

// Two-factor authentication
export interface TwoFactorAuthData {
  secret: string;
  qrCode: string;
  backupCodes: string[];
}

export interface VerifyTwoFactorData {
  token: string;
  code: string;
}

// Session information
export interface SessionInfo {
  id: string;
  userId: number;
  ipAddress: string;
  userAgent: string;
  location?: string;
  isCurrentSession: boolean;
  createdAt: string;
  lastActivity: string;
  expiresAt: string;
}

// User preferences for authentication
export interface AuthPreferences {
  rememberMe: boolean;
  twoFactorEnabled: boolean;
  emailNotifications: boolean;
  sessionTimeout: number;
  allowMultipleSessions: boolean;
}

// Account recovery data
export interface AccountRecoveryData {
  email: string;
  recoveryQuestions?: Array<{
    question: string;
    answer: string;
  }>;
  backupEmail?: string;
  phoneNumber?: string;
}

// Login analytics/tracking
export interface LoginAttempt {
  id: string;
  userId?: number;
  email: string;
  ipAddress: string;
  userAgent: string;
  success: boolean;
  failureReason?: string;
  timestamp: string;
  location?: string;
}

// Export commonly used types from the main API types
export type {
  User,
  UserLogin,
  UserRegister,
  ApiResponse,
  ApiError
} from './api';