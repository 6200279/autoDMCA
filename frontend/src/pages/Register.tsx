import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
import { UserRegister } from '../types/api';

// Password strength validation
const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

// Validation schema
const registerSchema = yup.object({
  firstName: yup
    .string()
    .required('First name is required')
    .min(2, 'First name must be at least 2 characters')
    .max(50, 'First name cannot exceed 50 characters')
    .matches(/^[a-zA-Z\s'-]+$/, 'First name can only contain letters, spaces, hyphens, and apostrophes'),
  lastName: yup
    .string()
    .required('Last name is required')
    .min(2, 'Last name must be at least 2 characters')
    .max(50, 'Last name cannot exceed 50 characters')
    .matches(/^[a-zA-Z\s'-]+$/, 'Last name can only contain letters, spaces, hyphens, and apostrophes'),
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required')
    .lowercase('Email must be lowercase'),
  password: yup
    .string()
    .required('Password is required')
    .min(8, 'Password must be at least 8 characters')
    .matches(
      passwordRegex,
      'Password must contain at least one uppercase letter, one lowercase letter, and one number'
    ),
  confirmPassword: yup
    .string()
    .required('Please confirm your password')
    .oneOf([yup.ref('password')], 'Passwords must match'),
  acceptTerms: yup
    .boolean()
    .required('You must accept the Terms and Conditions')
    .oneOf([true], 'You must accept the Terms and Conditions'),
  subscribeNewsletter: yup.boolean(),
});

interface RegisterFormData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
  acceptTerms: boolean;
  subscribeNewsletter: boolean;
}

/**
 * Password strength checker component
 */
const PasswordStrengthIndicator: React.FC<{ password: string }> = ({ password }) => {
  const getStrengthScore = (password: string): number => {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.match(/[a-z]/)) score++;
    if (password.match(/[A-Z]/)) score++;
    if (password.match(/[0-9]/)) score++;
    if (password.match(/[^a-zA-Z0-9]/)) score++;
    return score;
  };

  const getStrengthLabel = (score: number): string => {
    if (score === 0) return '';
    if (score <= 2) return 'Weak';
    if (score <= 3) return 'Fair';
    if (score <= 4) return 'Good';
    return 'Strong';
  };

  const getStrengthColor = (score: number): string => {
    if (score === 0) return '';
    if (score <= 2) return 'var(--red-500)';
    if (score <= 3) return 'var(--orange-500)';
    if (score <= 4) return 'var(--yellow-500)';
    return 'var(--green-500)';
  };

  if (!password) return null;

  const score = getStrengthScore(password);
  const label = getStrengthLabel(score);
  const color = getStrengthColor(score);

  return (
    <div className="mt-2">
      <div className="flex align-items-center gap-2">
        <div className="flex-1 border-round overflow-hidden bg-surface-200" style={{ height: '4px' }}>
          <div 
            className="h-full border-round transition-all transition-duration-300"
            style={{ 
              width: `${(score / 5) * 100}%`,
              backgroundColor: color 
            }}
          />
        </div>
        <small 
          className="font-medium"
          style={{ color, minWidth: '60px', textAlign: 'right' }}
        >
          {label}
        </small>
      </div>
    </div>
  );
};

/**
 * Register page component with comprehensive form validation and PrimeReact components
 * Matches Login page design for consistency and integrates with AuthContext
 */
const Register: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    reset,
    watch,
  } = useForm<RegisterFormData>({
    resolver: yupResolver(registerSchema),
    mode: 'onChange',
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptTerms: false,
      subscribeNewsletter: false,
    },
  });

  const watchedPassword = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const userData: UserRegister = {
        email: data.email.toLowerCase(),
        password: data.password,
        full_name: `${data.firstName.trim()} ${data.lastName.trim()}`,
      };
      
      await register(userData);
      
      // Navigate to email verification page or dashboard
      navigate('/email-verification', { 
        replace: true,
        state: { email: data.email }
      });
    } catch (err: any) {
      let errorMessage = 'Registration failed. Please try again.';
      
      if (err?.response?.status === 400) {
        const detail = err.response.data?.detail;
        if (detail?.includes('email')) {
          errorMessage = 'This email address is already registered. Please use a different email or sign in instead.';
        } else if (detail?.includes('password')) {
          errorMessage = 'Password does not meet security requirements. Please choose a stronger password.';
        } else {
          errorMessage = detail || errorMessage;
        }
      } else if (err?.response?.status === 422) {
        errorMessage = 'Please check your information and try again.';
      } else if (err?.response?.status === 429) {
        errorMessage = 'Too many registration attempts. Please try again later.';
      } else if (err?.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      setError(errorMessage);
      // Clear passwords on error for security
      reset({ 
        password: '', 
        confirmPassword: '' 
      }, { 
        keepValues: true,
        keepErrors: true 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getFieldError = (fieldName: keyof RegisterFormData): string | null => {
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

        {/* Registration Card */}
        <Card 
          className="w-full max-w-lg shadow-3" 
          style={{ borderRadius: '12px' }}
        >
          <div className="p-6">
            {/* Header */}
            <div className="text-center mb-5">
              <i className="pi pi-user-plus text-6xl text-primary mb-3"></i>
              <h2 className="text-3xl font-semibold mb-2 text-color">Create Account</h2>
              <p className="text-color-secondary">
                Join AutoDMCA to protect your content from unauthorized use
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

            {/* Registration Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-column gap-4">
              {/* Name Fields Row */}
              <div className="grid">
                {/* First Name Field */}
                <div className="col-12 md:col-6">
                  <div className="field">
                    <label htmlFor="firstName" className="block text-color font-medium mb-2">
                      First Name *
                    </label>
                    <Controller
                      name="firstName"
                      control={control}
                      render={({ field }) => (
                        <InputText
                          {...field}
                          id="firstName"
                          placeholder="Enter your first name"
                          className={`w-full ${errors.firstName ? 'p-invalid' : ''}`}
                          autoComplete="given-name"
                          disabled={isLoading}
                          aria-describedby={errors.firstName ? 'firstName-error' : undefined}
                        />
                      )}
                    />
                    {errors.firstName && (
                      <small id="firstName-error" className="p-error block mt-1">
                        {errors.firstName.message}
                      </small>
                    )}
                  </div>
                </div>

                {/* Last Name Field */}
                <div className="col-12 md:col-6">
                  <div className="field">
                    <label htmlFor="lastName" className="block text-color font-medium mb-2">
                      Last Name *
                    </label>
                    <Controller
                      name="lastName"
                      control={control}
                      render={({ field }) => (
                        <InputText
                          {...field}
                          id="lastName"
                          placeholder="Enter your last name"
                          className={`w-full ${errors.lastName ? 'p-invalid' : ''}`}
                          autoComplete="family-name"
                          disabled={isLoading}
                          aria-describedby={errors.lastName ? 'lastName-error' : undefined}
                        />
                      )}
                    />
                    {errors.lastName && (
                      <small id="lastName-error" className="p-error block mt-1">
                        {errors.lastName.message}
                      </small>
                    )}
                  </div>
                </div>
              </div>

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
                        placeholder="Create a strong password"
                        className={`w-full ${errors.password ? 'p-invalid' : ''}`}
                        inputClassName="w-full"
                        autoComplete="new-password"
                        disabled={isLoading}
                        feedback={false}
                        toggleMask
                        aria-describedby={errors.password ? 'password-error' : 'password-help'}
                      />
                    </div>
                  )}
                />
                <PasswordStrengthIndicator password={watchedPassword} />
                {errors.password && (
                  <small id="password-error" className="p-error block mt-1">
                    {errors.password.message}
                  </small>
                )}
                <small id="password-help" className="text-color-secondary block mt-1">
                  Must be 8+ characters with uppercase, lowercase, and number
                </small>
              </div>

              {/* Confirm Password Field */}
              <div className="field">
                <label htmlFor="confirmPassword" className="block text-color font-medium mb-2">
                  Confirm Password *
                </label>
                <Controller
                  name="confirmPassword"
                  control={control}
                  render={({ field }) => (
                    <div className="p-inputgroup">
                      <span className="p-inputgroup-addon">
                        <i className="pi pi-lock"></i>
                      </span>
                      <Password
                        {...field}
                        id="confirmPassword"
                        placeholder="Confirm your password"
                        className={`w-full ${errors.confirmPassword ? 'p-invalid' : ''}`}
                        inputClassName="w-full"
                        autoComplete="new-password"
                        disabled={isLoading}
                        feedback={false}
                        toggleMask
                        aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
                      />
                    </div>
                  )}
                />
                {errors.confirmPassword && (
                  <small id="confirmPassword-error" className="p-error block mt-1">
                    {errors.confirmPassword.message}
                  </small>
                )}
              </div>

              {/* Terms and Conditions Checkbox */}
              <div className="field-checkbox">
                <Controller
                  name="acceptTerms"
                  control={control}
                  render={({ field }) => (
                    <div className="flex align-items-start">
                      <Checkbox
                        {...field}
                        id="acceptTerms"
                        checked={field.value}
                        onChange={(e) => field.onChange(e.checked)}
                        disabled={isLoading}
                        className={`${errors.acceptTerms ? 'p-invalid' : ''}`}
                        aria-describedby={errors.acceptTerms ? 'acceptTerms-error' : undefined}
                      />
                      <label htmlFor="acceptTerms" className="ml-2 text-color text-sm line-height-3">
                        I agree to the{' '}
                        <Link 
                          to="/terms" 
                          className="text-primary no-underline hover:underline"
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label="Open Terms and Conditions in new tab"
                        >
                          Terms and Conditions
                        </Link>
                        {' '}and{' '}
                        <Link 
                          to="/privacy" 
                          className="text-primary no-underline hover:underline"
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label="Open Privacy Policy in new tab"
                        >
                          Privacy Policy
                        </Link>
                        {' '}*
                      </label>
                    </div>
                  )}
                />
                {errors.acceptTerms && (
                  <small id="acceptTerms-error" className="p-error block mt-1 ml-4">
                    {errors.acceptTerms.message}
                  </small>
                )}
              </div>

              {/* Newsletter Subscription Checkbox */}
              <div className="field-checkbox">
                <Controller
                  name="subscribeNewsletter"
                  control={control}
                  render={({ field }) => (
                    <div className="flex align-items-start">
                      <Checkbox
                        {...field}
                        id="subscribeNewsletter"
                        checked={field.value}
                        onChange={(e) => field.onChange(e.checked)}
                        disabled={isLoading}
                      />
                      <label htmlFor="subscribeNewsletter" className="ml-2 text-color text-sm line-height-3">
                        Subscribe to our newsletter for updates and tips on content protection
                      </label>
                    </div>
                  )}
                />
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                label={isLoading ? 'Creating Account...' : 'Create Account'}
                icon={isLoading ? '' : 'pi pi-user-plus'}
                className="w-full p-3 text-lg font-medium"
                disabled={!isValid || isLoading}
                loading={isLoading}
                loadingIcon="pi pi-spin pi-spinner"
                aria-label={isLoading ? 'Creating account, please wait' : 'Create your AutoDMCA account'}
              />

              <Divider className="my-4" />

              {/* Links */}
              <div className="text-center">
                <p className="text-color-secondary">
                  Already have an account?{' '}
                  <Link 
                    to="/login" 
                    className="text-primary font-medium no-underline hover:underline"
                    aria-label="Go to sign in page"
                  >
                    Sign in here
                  </Link>
                </p>
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

export default Register;