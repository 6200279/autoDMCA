import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { Button } from 'primereact/button';
import { Checkbox } from 'primereact/checkbox';
import { Divider } from 'primereact/divider';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import 'primereact/resources/themes/lara-light-blue/theme.css';
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';

import { useAuth } from '../hooks/useAuth';
import { UserLogin } from '../types/api';

// Validation schema
const loginSchema = yup.object({
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
});

interface LoginFormData {
  email: string;
  password: string;
  rememberMe?: boolean;
}

/**
 * Login page component with form validation and authentication
 * Uses PrimeReact components and React Hook Form for optimal UX
 */
const Login: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    reset,
    watch,
    setValue,
    trigger,
  } = useForm<LoginFormData>({
    resolver: yupResolver(loginSchema),
    mode: 'onChange',
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const watchedFields = watch();

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const credentials: UserLogin = {
        email: data.email,
        password: data.password,
      };
      
      await login(credentials);
      
      // Handle remember me functionality
      if (data.rememberMe) {
        localStorage.setItem('rememberMe', 'true');
      }
      
      navigate(from, { replace: true });
    } catch (err: any) {
      let errorMessage = 'Login failed. Please try again.';
      
      if (err?.response?.status === 401) {
        errorMessage = 'Invalid email or password. Please check your credentials.';
      } else if (err?.response?.status === 429) {
        errorMessage = 'Too many login attempts. Please try again later.';
      } else if (err?.response?.status === 403) {
        errorMessage = 'Account is locked or not verified. Please check your email.';
      } else if (err?.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      setError(errorMessage);
      reset({ password: '' }); // Clear password on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleRememberMeChange = (e: { checked: boolean }) => {
    setRememberMe(e.checked);
  };

  const getFieldError = (fieldName: keyof LoginFormData): string | null => {
    return errors[fieldName]?.message || null;
  };

  return (
    <div className="min-h-screen flex align-items-center justify-content-center" style={{ background: 'var(--surface-ground)' }}>
      <div className="flex flex-column align-items-center justify-content-center w-full px-4">
        {/* Logo/Brand */}
        <div className="text-center mb-6">
          <h1 className="text-6xl font-bold mb-2" style={{ 
            background: 'linear-gradient(45deg, var(--primary-color), #dc004e)', 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            color: 'transparent'
          }}>
            AutoDMCA
          </h1>
          <p className="text-color-secondary text-xl">
            Automated Content Protection Platform
          </p>
        </div>

        {/* Login Card */}
        <Card 
          className="w-full max-w-md shadow-3" 
          style={{ borderRadius: '12px' }}
        >
          <div className="p-6">
            {/* Header */}
            <div className="text-center mb-5">
              <i className="pi pi-sign-in text-6xl text-primary mb-3"></i>
              <h2 className="text-3xl font-semibold mb-2 text-color">Sign In</h2>
              <p className="text-color-secondary">
                Welcome back! Please sign in to your account.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4">
                <Message 
                  severity="error" 
                  text={error}
                  className="w-full"
                />
              </div>
            )}

            {/* Mock Credentials for Local Testing */}
            {(import.meta.env.DEV || import.meta.env.VITE_LOCAL_TESTING === 'true') && (
              <div className="mb-4 p-3" style={{ 
                background: 'var(--surface-100)', 
                borderRadius: '8px',
                border: '1px solid var(--surface-200)'
              }}>
                <h4 className="text-sm font-semibold mb-2 text-color">
                  🧪 Local Testing Credentials
                </h4>
                <div className="text-xs text-color-secondary">
                  <strong>Email:</strong> admin@autodmca.com<br/>
                  <strong>Password:</strong> admin123
                  <br/><br/>
                  <strong>User:</strong> user@example.com<br/>
                  <strong>Password:</strong> user1234
                </div>
                <div className="mt-2">
                  <Button
                    type="button"
                    label="Fill Admin"
                    size="small"
                    className="mr-2"
                    outlined
                    onClick={async () => {
                      setValue('email', 'admin@autodmca.com');
                      setValue('password', 'admin123');
                      // Trigger validation to enable the submit button
                      await trigger(['email', 'password']);
                    }}
                  />
                  <Button
                    type="button"
                    label="Fill User"
                    size="small"
                    outlined
                    onClick={async () => {
                      setValue('email', 'user@example.com');
                      setValue('password', 'user1234');
                      // Trigger validation to enable the submit button
                      await trigger(['email', 'password']);
                    }}
                  />
                </div>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-column gap-4">
              {/* Email Field */}
              <div className="field">
                <label htmlFor="email" className="block text-color font-medium mb-2">
                  Email Address *
                </label>
                <Controller
                  name="email"
                  control={control}
                  render={({ field }) => (
                    <div className="p-inputgroup">
                      <span className="p-inputgroup-addon">
                        <i className="pi pi-envelope"></i>
                      </span>
                      <InputText
                        {...field}
                        id="email"
                        type="email"
                        placeholder="Enter your email address"
                        className={`w-full ${errors.email ? 'p-invalid' : ''}`}
                        autoComplete="email"
                        autoFocus
                        disabled={isLoading}
                        aria-describedby={errors.email ? 'email-error' : undefined}
                      />
                    </div>
                  )}
                />
                {errors.email && (
                  <small id="email-error" className="p-error block mt-1">
                    {errors.email.message}
                  </small>
                )}
              </div>

              {/* Password Field */}
              <div className="field">
                <label htmlFor="password" className="block text-color font-medium mb-2">
                  Password *
                </label>
                <Controller
                  name="password"
                  control={control}
                  render={({ field }) => (
                    <div className="p-inputgroup">
                      <span className="p-inputgroup-addon">
                        <i className="pi pi-lock"></i>
                      </span>
                      <Password
                        {...field}
                        id="password"
                        placeholder="Enter your password"
                        className={`w-full ${errors.password ? 'p-invalid' : ''}`}
                        inputClassName="w-full"
                        autoComplete="current-password"
                        disabled={isLoading}
                        feedback={false}
                        toggleMask
                        aria-describedby={errors.password ? 'password-error' : undefined}
                      />
                    </div>
                  )}
                />
                {errors.password && (
                  <small id="password-error" className="p-error block mt-1">
                    {errors.password.message}
                  </small>
                )}
              </div>

              {/* Remember Me */}
              <div className="field-checkbox">
                <Controller
                  name="rememberMe"
                  control={control}
                  render={({ field }) => (
                    <div className="flex align-items-center">
                      <Checkbox
                        {...field}
                        id="rememberMe"
                        checked={field.value || false}
                        onChange={(e) => {
                          field.onChange(e.checked);
                          handleRememberMeChange(e);
                        }}
                        disabled={isLoading}
                      />
                      <label htmlFor="rememberMe" className="ml-2 text-color">
                        Remember me for 30 days
                      </label>
                    </div>
                  )}
                />
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                label={isLoading ? 'Signing In...' : 'Sign In'}
                icon={isLoading ? '' : 'pi pi-sign-in'}
                className="w-full p-3 text-lg font-medium"
                disabled={!isValid || isLoading}
                loading={isLoading}
                loadingIcon="pi pi-spin pi-spinner"
                aria-label={isLoading ? 'Signing in, please wait' : 'Sign in to your account'}
              />

              <Divider className="my-4" />

              {/* Links */}
              <div className="text-center">
                <p className="text-color-secondary mb-3">
                  Don't have an account?{' '}
                  <Link 
                    to="/register" 
                    className="text-primary font-medium no-underline hover:underline"
                    aria-label="Go to registration page"
                  >
                    Sign up here
                  </Link>
                </p>
                <Link 
                  to="/forgot-password" 
                  className="text-color-secondary no-underline hover:underline text-sm"
                  aria-label="Go to password recovery page"
                >
                  Forgot your password?
                </Link>
              </div>
            </form>
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-color-secondary text-sm">
            © 2024 AutoDMCA. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;