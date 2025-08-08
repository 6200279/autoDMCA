/**
 * Example component demonstrating how to use the AuthContext
 * This file shows various usage patterns and best practices
 * 
 * IMPORTANT: This is an example file and should not be imported in production code
 * Use these patterns in your actual components
 */

import React, { useState } from 'react';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { Card } from 'primereact/card';
import { Divider } from 'primereact/divider';
import { Tag } from 'primereact/tag';
import { useAuth } from '../hooks/useAuth';

export const AuthContextUsageExample: React.FC = () => {
  const {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    verifyEmail,
    forgotPassword,
    resetPassword,
    refreshUser,
    refreshToken,
    getCurrentUser
  } = useAuth();

  const [loginForm, setLoginForm] = useState({
    email: '',
    password: ''
  });

  const [registerForm, setRegisterForm] = useState({
    email: '',
    password: '',
    full_name: '',
    company: ''
  });

  const [emailVerificationToken, setEmailVerificationToken] = useState('');
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('');
  const [resetPasswordForm, setResetPasswordForm] = useState({
    token: '',
    password: ''
  });

  // Example: Login
  const handleLogin = async () => {
    try {
      await login(loginForm);
      // Success notification is handled by the AuthContext
      // You can add additional logic here (e.g., redirect)
      console.log('Login successful, user:', user);
    } catch (error) {
      // Error notification is handled by the AuthContext
      console.error('Login failed:', error);
    }
  };

  // Example: Register
  const handleRegister = async () => {
    try {
      await register(registerForm);
      console.log('Registration successful');
      // Optionally redirect or show additional UI
    } catch (error) {
      console.error('Registration failed:', error);
    }
  };

  // Example: Logout
  const handleLogout = async () => {
    try {
      await logout();
      console.log('Logout successful');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  // Example: Email verification
  const handleVerifyEmail = async () => {
    try {
      await verifyEmail({ token: emailVerificationToken });
      console.log('Email verified successfully');
    } catch (error) {
      console.error('Email verification failed:', error);
    }
  };

  // Example: Forgot password
  const handleForgotPassword = async () => {
    try {
      await forgotPassword({ email: forgotPasswordEmail });
      console.log('Password reset email sent');
    } catch (error) {
      console.error('Forgot password failed:', error);
    }
  };

  // Example: Reset password
  const handleResetPassword = async () => {
    try {
      await resetPassword(resetPasswordForm);
      console.log('Password reset successful');
    } catch (error) {
      console.error('Password reset failed:', error);
    }
  };

  // Example: Refresh user data
  const handleRefreshUser = async () => {
    try {
      await refreshUser();
      console.log('User data refreshed');
    } catch (error) {
      console.error('Failed to refresh user data:', error);
    }
  };

  // Example: Manual token refresh
  const handleRefreshToken = async () => {
    try {
      await refreshToken();
      console.log('Token refreshed successfully');
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
  };

  // Example: Get current user
  const handleGetCurrentUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      console.log('Current user:', currentUser);
    } catch (error) {
      console.error('Failed to get current user:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-content-center align-items-center min-h-screen">
        <i className="pi pi-spinner pi-spin" style={{ fontSize: '2rem' }} />
        <span className="ml-2">Loading authentication...</span>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">AuthContext Usage Examples</h1>
      
      {/* Authentication Status */}
      <Card title="Authentication Status" className="mb-4">
        <div className="flex align-items-center gap-3 mb-3">
          <span>Status:</span>
          <Tag 
            value={isAuthenticated ? 'Authenticated' : 'Not Authenticated'} 
            severity={isAuthenticated ? 'success' : 'danger'} 
          />
        </div>
        
        {isAuthenticated && user && (
          <div className="space-y-2">
            <p><strong>User ID:</strong> {user.id}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Name:</strong> {user.full_name}</p>
            <p><strong>Verified:</strong> {user.is_verified ? 'Yes' : 'No'}</p>
            <p><strong>Active:</strong> {user.is_active ? 'Yes' : 'No'}</p>
          </div>
        )}
        
        <div className="flex gap-2 mt-3">
          <Button 
            label="Refresh User Data" 
            icon="pi pi-refresh" 
            onClick={handleRefreshUser}
            className="p-button-outlined"
          />
          <Button 
            label="Refresh Token" 
            icon="pi pi-key" 
            onClick={handleRefreshToken}
            className="p-button-outlined"
          />
          <Button 
            label="Get Current User" 
            icon="pi pi-user" 
            onClick={handleGetCurrentUser}
            className="p-button-outlined"
          />
        </div>
      </Card>

      {!isAuthenticated ? (
        <>
          {/* Login Form */}
          <Card title="Login Example" className="mb-4">
            <div className="space-y-3">
              <div>
                <label htmlFor="login-email">Email</label>
                <InputText
                  id="login-email"
                  value={loginForm.email}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="Enter your email"
                  className="w-full"
                />
              </div>
              <div>
                <label htmlFor="login-password">Password</label>
                <Password
                  id="login-password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter your password"
                  className="w-full"
                  feedback={false}
                  toggleMask
                />
              </div>
              <Button
                label="Login"
                icon="pi pi-sign-in"
                onClick={handleLogin}
                loading={isLoading}
              />
            </div>
          </Card>

          {/* Register Form */}
          <Card title="Register Example" className="mb-4">
            <div className="space-y-3">
              <div>
                <label htmlFor="register-email">Email</label>
                <InputText
                  id="register-email"
                  value={registerForm.email}
                  onChange={(e) => setRegisterForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="Enter your email"
                  className="w-full"
                />
              </div>
              <div>
                <label htmlFor="register-password">Password</label>
                <Password
                  id="register-password"
                  value={registerForm.password}
                  onChange={(e) => setRegisterForm(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter your password"
                  className="w-full"
                />
              </div>
              <div>
                <label htmlFor="register-name">Full Name</label>
                <InputText
                  id="register-name"
                  value={registerForm.full_name}
                  onChange={(e) => setRegisterForm(prev => ({ ...prev, full_name: e.target.value }))}
                  placeholder="Enter your full name"
                  className="w-full"
                />
              </div>
              <div>
                <label htmlFor="register-company">Company (Optional)</label>
                <InputText
                  id="register-company"
                  value={registerForm.company}
                  onChange={(e) => setRegisterForm(prev => ({ ...prev, company: e.target.value }))}
                  placeholder="Enter your company"
                  className="w-full"
                />
              </div>
              <Button
                label="Register"
                icon="pi pi-user-plus"
                onClick={handleRegister}
                loading={isLoading}
              />
            </div>
          </Card>
        </>
      ) : (
        /* Authenticated User Actions */
        <Card title="User Actions" className="mb-4">
          <Button
            label="Logout"
            icon="pi pi-sign-out"
            onClick={handleLogout}
            className="p-button-danger"
            loading={isLoading}
          />
        </Card>
      )}

      <Divider />

      {/* Utility Functions */}
      <Card title="Utility Functions" className="mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Email Verification */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Email Verification</h3>
            <div className="space-y-2">
              <InputText
                value={emailVerificationToken}
                onChange={(e) => setEmailVerificationToken(e.target.value)}
                placeholder="Enter verification token"
                className="w-full"
              />
              <Button
                label="Verify Email"
                icon="pi pi-check"
                onClick={handleVerifyEmail}
                className="w-full p-button-outlined"
                loading={isLoading}
              />
            </div>
          </div>

          {/* Forgot Password */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Forgot Password</h3>
            <div className="space-y-2">
              <InputText
                value={forgotPasswordEmail}
                onChange={(e) => setForgotPasswordEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full"
              />
              <Button
                label="Send Reset Email"
                icon="pi pi-envelope"
                onClick={handleForgotPassword}
                className="w-full p-button-outlined"
                loading={isLoading}
              />
            </div>
          </div>

          {/* Reset Password */}
          <div>
            <h3 className="text-lg font-semibold mb-2">Reset Password</h3>
            <div className="space-y-2">
              <InputText
                value={resetPasswordForm.token}
                onChange={(e) => setResetPasswordForm(prev => ({ ...prev, token: e.target.value }))}
                placeholder="Enter reset token"
                className="w-full"
              />
              <Password
                value={resetPasswordForm.password}
                onChange={(e) => setResetPasswordForm(prev => ({ ...prev, password: e.target.value }))}
                placeholder="Enter new password"
                className="w-full"
              />
              <Button
                label="Reset Password"
                icon="pi pi-key"
                onClick={handleResetPassword}
                className="w-full p-button-outlined"
                loading={isLoading}
              />
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AuthContextUsageExample;