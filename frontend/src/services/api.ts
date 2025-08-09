import axios from 'axios';

// Create axios instance
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await api.post('/auth/refresh', {
            refreshToken,
          });
          
          const { accessToken } = response.data;
          localStorage.setItem('accessToken', accessToken);
          
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/auth/login';
      }
    }
    
    return Promise.reject(error);
  }
);

// Billing API endpoints
export const billingApi = {
  // Subscriptions
  createSubscription: (data: any) => api.post('/billing/subscriptions', data),
  getCurrentSubscription: () => api.get('/billing/subscriptions/current'),
  updateSubscription: (data: any) => api.put('/billing/subscriptions/current', data),
  cancelSubscription: (data: any) => api.post('/billing/subscriptions/cancel', data),
  reactivateSubscription: () => api.post('/billing/subscriptions/reactivate'),
  getSubscriptionPlans: () => api.get('/billing/plans'),
  
  // Payment Methods
  createSetupIntent: (data: any) => api.post('/billing/payment-methods/setup-intent', data),
  addPaymentMethod: (data: any) => api.post('/billing/payment-methods', data),
  getPaymentMethods: () => api.get('/billing/payment-methods'),
  removePaymentMethod: (id: number) => api.delete(`/billing/payment-methods/${id}`),
  
  // Invoices
  getInvoices: (params?: any) => api.get('/billing/invoices', { params }),
  getInvoice: (id: number) => api.get(`/billing/invoices/${id}`),
  
  // Usage
  getCurrentUsage: () => api.get('/billing/usage/current'),
  getUsageLimits: () => api.get('/billing/usage/limits'),
  checkUsageLimit: (metric: string, quantity?: number) => 
    api.get(`/billing/usage/check/${metric}`, { params: { quantity } }),
  getUsageAnalytics: (days?: number) => 
    api.get('/billing/usage/analytics', { params: { days } }),
  
  // Dashboard
  getBillingDashboard: () => api.get('/billing/dashboard'),
  
  // Webhooks
  handleStripeWebhook: (data: any) => api.post('/billing/webhooks/stripe', data),
};

// Auth API endpoints
export const authApi = {
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  refreshToken: (data: any) => api.post('/auth/refresh', data),
  forgotPassword: (data: any) => api.post('/auth/forgot-password', data),
  resetPassword: (data: any) => api.post('/auth/reset-password', data),
  verifyEmail: (data: any) => api.post('/auth/verify-email', data),
  resendVerification: (data: any) => api.post('/auth/resend-verification', data),
};

// User API endpoints
export const userApi = {
  getCurrentUser: () => api.get('/users/me'),
  updateUser: (data: any) => api.put('/users/me', data),
  changePassword: (data: any) => api.post('/users/me/change-password', data),
  deleteAccount: () => api.delete('/users/me'),
};

// Profile API endpoints
export const profileApi = {
  getProfiles: (params?: any) => api.get('/profiles', { params }),
  createProfile: (data: any) => api.post('/profiles', data),
  getProfile: (id: number) => api.get(`/profiles/${id}`),
  updateProfile: (id: number, data: any) => api.put(`/profiles/${id}`, data),
  deleteProfile: (id: number) => api.delete(`/profiles/${id}`),
  uploadProfileImage: (id: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/profiles/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

// Infringement API endpoints
export const infringementApi = {
  getInfringements: (params?: any) => api.get('/infringements', { params }),
  getInfringement: (id: number) => api.get(`/infringements/${id}`),
  createInfringement: (data: any) => api.post('/infringements', data),
  updateInfringement: (id: number, data: any) => api.put(`/infringements/${id}`, data),
  deleteInfringement: (id: number) => api.delete(`/infringements/${id}`),
  bulkAction: (data: any) => api.post('/infringements/bulk-action', data),
};

// Takedown API endpoints
export const takedownApi = {
  getTakedowns: (params?: any) => api.get('/takedowns', { params }),
  getTakedown: (id: number) => api.get(`/takedowns/${id}`),
  createTakedown: (data: any) => api.post('/takedowns', data),
  updateTakedown: (id: number, data: any) => api.put(`/takedowns/${id}`, data),
  deleteTakedown: (id: number) => api.delete(`/takedowns/${id}`),
  sendTakedown: (id: number) => api.post(`/takedowns/${id}/send`),
  generateTemplate: (data: any) => api.post('/takedowns/generate-template', data),
};

// Submission API endpoints
export const submissionApi = {
  getSubmissions: (params?: any) => api.get('/submissions', { params }),
  getSubmission: (id: string) => api.get(`/submissions/${id}`),
  createSubmission: (data: any) => api.post('/submissions', data),
  updateSubmission: (id: string, data: any) => api.put(`/submissions/${id}`, data),
  deleteSubmission: (id: string) => api.delete(`/submissions/${id}`),
  cancelSubmission: (id: string) => api.post(`/submissions/${id}/cancel`),
  retrySubmission: (id: string) => api.post(`/submissions/${id}/retry`),
  getSubmissionProgress: (id: string) => api.get(`/submissions/${id}/progress`),
  uploadFiles: (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return api.post('/submissions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  validateUrls: (urls: string[]) => api.post('/submissions/validate-urls', { urls }),
  bulkCreate: (data: any) => api.post('/submissions/bulk', data),
};

// Admin API endpoints
export const adminApi = {
  // Dashboard
  getDashboardStats: () => api.get('/admin/dashboard'),
  getSystemMetrics: () => api.get('/admin/metrics'),
  getSystemHealth: () => api.get('/admin/health'),
  
  // User Management
  getUsers: (params?: any) => api.get('/admin/users', { params }),
  getUser: (id: number) => api.get(`/admin/users/${id}`),
  updateUser: (id: number, data: any) => api.put(`/admin/users/${id}`, data),
  suspendUser: (id: number, data: any) => api.post(`/admin/users/${id}/suspend`, data),
  activateUser: (id: number) => api.post(`/admin/users/${id}/activate`),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
  impersonateUser: (id: number) => api.post(`/admin/users/${id}/impersonate`),
  bulkUserOperation: (data: any) => api.post('/admin/users/bulk-action', data),
  exportUsers: (params?: any) => api.get('/admin/users/export', { params }),
  getUserAnalytics: (params?: any) => api.get('/admin/analytics/users', { params }),
  
  // Subscription Management
  getUserSubscription: (userId: number) => api.get(`/admin/users/${userId}/subscription`),
  updateUserSubscription: (userId: number, data: any) => api.put(`/admin/users/${userId}/subscription`, data),
  cancelUserSubscription: (userId: number, data: any) => api.post(`/admin/users/${userId}/subscription/cancel`, data),
  getSubscriptionAnalytics: () => api.get('/admin/analytics/subscriptions'),
  
  // System Configuration
  getSystemConfigs: (params?: any) => api.get('/admin/config', { params }),
  updateSystemConfig: (key: string, data: any) => api.put(`/admin/config/${key}`, data),
  getPlatformConfigs: () => api.get('/admin/platforms'),
  updatePlatformConfig: (id: string, data: any) => api.put(`/admin/platforms/${id}`, data),
  testPlatformConnection: (id: string) => api.post(`/admin/platforms/${id}/test`),
  
  // Activity & Audit Logs
  getAdminActivities: (params?: any) => api.get('/admin/activities', { params }),
  getAuditLogs: (params?: any) => api.get('/admin/audit-logs', { params }),
  
  // Notifications
  getAdminNotifications: (params?: any) => api.get('/admin/notifications', { params }),
  markNotificationRead: (id: number) => api.put(`/admin/notifications/${id}/read`),
  createAnnouncement: (data: any) => api.post('/admin/announcements', data),
  
  // System Operations
  enableMaintenanceMode: (data: any) => api.post('/admin/maintenance/enable', data),
  disableMaintenanceMode: () => api.post('/admin/maintenance/disable'),
  toggleFeatureFlag: (flag: string, data: any) => api.post(`/admin/feature-flags/${flag}/toggle`, data),
  getFeatureFlags: () => api.get('/admin/feature-flags'),
  
  // Backup & Export
  createBackup: () => api.post('/admin/backup/create'),
  getBackupStatus: () => api.get('/admin/backup/status'),
  exportSystemData: (type: string, params?: any) => api.get(`/admin/export/${type}`, { params }),
  
  // Analytics & Reports
  getRevenueSummary: (params?: any) => api.get('/admin/analytics/revenue', { params }),
  getUsageStatistics: (params?: any) => api.get('/admin/analytics/usage', { params }),
  getPlatformPerformance: (params?: any) => api.get('/admin/analytics/platforms', { params }),
  getSecurityReport: (params?: any) => api.get('/admin/security/report', { params }),
};

// Browser Extension API endpoints
export const extensionApi = {
  // Extension Management
  getExtensions: () => api.get('/extensions'),
  getExtension: (id: string) => api.get(`/extensions/${id}`),
  installExtension: (extensionId: string, browserData: any) => api.post(`/extensions/${extensionId}/install`, browserData),
  uninstallExtension: (extensionId: string) => api.delete(`/extensions/${extensionId}/install`),
  activateExtension: (extensionId: string) => api.post(`/extensions/${extensionId}/activate`),
  deactivateExtension: (extensionId: string) => api.post(`/extensions/${extensionId}/deactivate`),
  syncExtension: (extensionId: string) => api.post(`/extensions/${extensionId}/sync`),
  updateExtension: (extensionId: string) => api.post(`/extensions/${extensionId}/update`),
  
  // Extension Settings
  getExtensionSettings: (extensionId: string) => api.get(`/extensions/${extensionId}/settings`),
  updateExtensionSettings: (extensionId: string, settings: any) => api.put(`/extensions/${extensionId}/settings`, settings),
  resetExtensionSettings: (extensionId: string) => api.post(`/extensions/${extensionId}/settings/reset`),
  
  // Extension Activity
  getExtensionActivities: (params?: any) => api.get('/extensions/activities', { params }),
  getExtensionActivity: (extensionId: string, params?: any) => api.get(`/extensions/${extensionId}/activities`, { params }),
  recordActivity: (activityData: any) => api.post('/extensions/activities', activityData),
  
  // Extension Permissions
  getExtensionPermissions: (extensionId: string) => api.get(`/extensions/${extensionId}/permissions`),
  updateExtensionPermissions: (extensionId: string, permissions: any) => api.put(`/extensions/${extensionId}/permissions`, permissions),
  revokePermission: (extensionId: string, permission: string) => api.delete(`/extensions/${extensionId}/permissions/${permission}`),
  
  // Extension Statistics
  getExtensionStats: (extensionId?: string) => api.get('/extensions/stats', { params: extensionId ? { extensionId } : {} }),
  getBrowserDistribution: () => api.get('/extensions/stats/browsers'),
  getActivityTrends: (params?: any) => api.get('/extensions/stats/trends', { params }),
  
  // Extension Updates
  checkForUpdates: (extensionId?: string) => api.get('/extensions/updates', { params: extensionId ? { extensionId } : {} }),
  getUpdateDetails: (extensionId: string) => api.get(`/extensions/${extensionId}/updates`),
  scheduleUpdate: (extensionId: string, scheduleData: any) => api.post(`/extensions/${extensionId}/updates/schedule`, scheduleData),
  
  // Extension Configuration
  getExtensionConfig: (extensionId: string) => api.get(`/extensions/${extensionId}/config`),
  updateExtensionConfig: (extensionId: string, config: any) => api.put(`/extensions/${extensionId}/config`, config),
  validateExtensionConfig: (extensionId: string, config: any) => api.post(`/extensions/${extensionId}/config/validate`, config),
  
  // Extension Content Reporting
  reportContent: (reportData: any) => api.post('/extensions/report', reportData),
  bulkReportContent: (reportDataArray: any[]) => api.post('/extensions/report/bulk', { reports: reportDataArray }),
  getReportStatus: (reportId: string) => api.get(`/extensions/reports/${reportId}/status`),
  
  // Extension Health & Monitoring
  getExtensionHealth: (extensionId: string) => api.get(`/extensions/${extensionId}/health`),
  pingExtension: (extensionId: string) => api.post(`/extensions/${extensionId}/ping`),
  getExtensionLogs: (extensionId: string, params?: any) => api.get(`/extensions/${extensionId}/logs`, { params }),
  
  // Extension Export & Backup
  exportExtensionData: (extensionId: string, type: string) => api.get(`/extensions/${extensionId}/export/${type}`),
  backupExtensionSettings: (extensionId: string) => api.post(`/extensions/${extensionId}/backup`),
  restoreExtensionSettings: (extensionId: string, backupData: any) => api.post(`/extensions/${extensionId}/restore`, backupData),
  
  // Bulk Operations
  bulkExtensionOperation: (operationData: any) => api.post('/extensions/bulk', operationData),
  getOperationStatus: (operationId: string) => api.get(`/extensions/operations/${operationId}/status`),
};

// Dashboard API endpoints
export const dashboardApi = {
  // Main dashboard stats
  getStats: (dateRange?: { start: string; end: string }) => 
    api.get('/dashboard/stats', { params: dateRange }),
  
  // Recent activity feed
  getRecentActivity: (params?: { limit?: number; type?: string; status?: string }) =>
    api.get('/dashboard/activity', { params }),
  
  // Analytics data for charts
  getAnalytics: (params?: { 
    dateRange?: { start: string; end: string }; 
    granularity?: 'day' | 'week' | 'month' 
  }) =>
    api.get('/dashboard/analytics', { params }),
  
  // Platform distribution data
  getPlatformDistribution: (dateRange?: { start: string; end: string }) =>
    api.get('/dashboard/platform-distribution', { params: dateRange }),
  
  // Usage metrics
  getUsageMetrics: () => api.get('/dashboard/usage'),
  
  // Monthly trends data
  getMonthlyTrends: (params?: { months?: number }) =>
    api.get('/dashboard/trends', { params }),
  
  // Success rate analytics
  getSuccessRateAnalytics: (dateRange?: { start: string; end: string }) =>
    api.get('/dashboard/success-rates', { params: dateRange }),
  
  // Export dashboard data
  exportDashboardData: (params: { 
    format: 'csv' | 'xlsx' | 'pdf'; 
    dateRange?: { start: string; end: string };
    sections?: string[];
  }) =>
    api.get('/dashboard/export', { params }),
  
  // Dashboard preferences
  getDashboardPreferences: () => api.get('/dashboard/preferences'),
  updateDashboardPreferences: (preferences: any) => 
    api.put('/dashboard/preferences', preferences),
  
  // Real-time updates
  getLastUpdatedTimestamp: () => api.get('/dashboard/last-updated'),
  
  // Quick actions data
  getQuickActionsData: () => api.get('/dashboard/quick-actions'),
};

export default api;