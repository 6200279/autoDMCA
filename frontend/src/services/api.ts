import axios from 'axios';
import type { 
  User, UserLogin, UserRegister, Subscription, 
  Profile, TakedownRequest, 
  SystemHealth, BillingDashboard, ApiResponse 
} from '../types/api';

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1',
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

// Response interceptor to handle token refresh and API errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Handle authentication errors
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
        window.location.href = '/login';
      }
    }
    
    // Add helpful context for unimplemented features
    if (error.response?.status === 404 && error.config?.url) {
      const url = error.config.url;
      const featureMap: Record<string, string> = {
        '/admin': 'Admin Panel',
        '/ai': 'AI Content Matching',
        '/extensions': 'Browser Extensions',
        '/social-media': 'Social Media Protection',
        '/reports': 'Advanced Reports',
        '/dmca-templates': 'DMCA Templates',
        '/search-engine-delisting': 'Search Engine Delisting',
        '/content-watermarking': 'Content Watermarking',
        '/submissions': 'Content Submissions',
        '/billing/payment-methods': 'Payment Methods',
        '/billing/invoices': 'Invoice History'
      };
      
      for (const [pattern, featureName] of Object.entries(featureMap)) {
        if (url.includes(pattern)) {
          error.featureName = featureName;
          error.isUnimplemented = true;
          break;
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// Billing API endpoints
export const billingApi = {
  // Subscriptions
  createSubscription: (data: Partial<Subscription>) => api.post('/billing/subscriptions', data),
  getCurrentSubscription: () => api.get('/billing/subscriptions/current'),
  updateSubscription: (data: Partial<Subscription>) => api.put('/billing/subscriptions/current', data),
  cancelSubscription: (data: { reason?: string }) => api.post('/billing/subscriptions/cancel', data),
  reactivateSubscription: () => api.post('/billing/subscriptions/reactivate'),
  getSubscriptionPlans: () => api.get('/billing/plans'),
  
  // Payment Methods
  createSetupIntent: (data: { payment_method_types?: string[] }) => api.post('/billing/payment-methods/setup-intent', data),
  addPaymentMethod: (data: { payment_method: string; set_as_default?: boolean }) => api.post('/billing/payment-methods', data),
  getPaymentMethods: () => api.get('/billing/payment-methods'),
  removePaymentMethod: (id: number) => api.delete(`/billing/payment-methods/${id}`),
  
  // Invoices
  getInvoices: (params?: { page?: number; limit?: number; status?: string }) => api.get('/billing/invoices', { params }),
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
  handleStripeWebhook: (data: Record<string, unknown>) => api.post('/billing/webhooks/stripe', data),
};

// Auth API endpoints
export const authApi = {
  login: (data: UserLogin) => api.post('/auth/login', data),
  register: (data: UserRegister) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  refreshToken: (data: { refreshToken: string }) => api.post('/auth/refresh', data),
  forgotPassword: (data: { email: string }) => api.post('/auth/forgot-password', data),
  resetPassword: (data: { token: string; password: string }) => api.post('/auth/reset-password', data),
  verifyEmail: (data: { token: string }) => api.post('/auth/verify-email', data),
  resendVerification: (data: { email: string }) => api.post('/auth/resend-verification', data),
};

// User API endpoints
export const userApi = {
  getCurrentUser: () => api.get('/users/me'),
  updateUser: (data: Partial<User>) => api.put('/users/me', data),
  changePassword: (data: { currentPassword: string; newPassword: string }) => api.post('/users/me/change-password', data),
  deleteAccount: () => api.delete('/users/me'),
  
  // Settings and preferences
  getUserSettings: () => api.get('/users/me/settings'),
  updateUserSettings: (data: Record<string, unknown>) => api.put('/users/me/settings', data),
  
  // Activity and audit logs
  getUserActivity: (params?: { page?: number; limit?: number; type?: string }) => api.get('/users/me/activity', { params }),
  
  // Avatar management
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  deleteAvatar: () => api.delete('/users/me/avatar'),
  
  // API Keys management
  getApiKeys: () => api.get('/users/me/api-keys'),
  createApiKey: (data: { name: string; permissions: string[] }) => api.post('/users/me/api-keys', data),
  revokeApiKey: (keyId: string) => api.delete(`/users/me/api-keys/${keyId}`),
  updateApiKey: (keyId: string, data: { name?: string; permissions?: string[] }) => api.put(`/users/me/api-keys/${keyId}`, data),
};

// Profile API endpoints
export const profileApi = {
  getProfiles: (params?: { page?: number; limit?: number; search?: string }) => api.get('/profiles', { params }),
  createProfile: (data: Partial<Profile>) => api.post('/profiles', data),
  getProfile: (id: number) => api.get(`/profiles/${id}`),
  updateProfile: (id: number, data: Partial<Profile>) => api.put(`/profiles/${id}`, data),
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
  getInfringement: (id: number | string) => api.get(`/infringements/${id}`),
  createInfringement: (data: any) => api.post('/infringements', data),
  updateInfringement: (id: number | string, data: any) => api.put(`/infringements/${id}`, data),
  deleteInfringement: (id: number | string) => api.delete(`/infringements/${id}`),
  bulkAction: (data: any) => api.post('/infringements/bulk-action', data),
  
  // Create takedown from infringement
  createTakedownFromInfringement: (infringementId: number | string) => 
    api.post(`/infringements/${infringementId}/create-takedown`),
  
  // Infringement statistics
  getInfringementStats: (params?: any) => api.get('/infringements/stats', { params }),
  
  // Mark infringement actions
  markAsFalsePositive: (id: number | string) => 
    api.put(`/infringements/${id}`, { status: 'false_positive' }),
  
  markAsResolved: (id: number | string) => 
    api.put(`/infringements/${id}`, { status: 'removed' }),
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

// AI Content Matching API endpoints
export const aiContentMatchingApi = {
  // AI Models Management
  getModels: (params?: any) => api.get('/ai/models', { params }),
  getModel: (id: string) => api.get(`/ai/models/${id}`),
  createModel: (data: any) => api.post('/ai/models', data),
  updateModel: (id: string, data: any) => api.put(`/ai/models/${id}`, data),
  deleteModel: (id: string) => api.delete(`/ai/models/${id}`),
  activateModel: (id: string) => api.post(`/ai/models/${id}/activate`),
  deactivateModel: (id: string) => api.post(`/ai/models/${id}/deactivate`),
  trainModel: (id: string) => api.post(`/ai/models/${id}/train`),
  stopTraining: (id: string) => api.post(`/ai/models/${id}/stop-training`),
  
  // Training Data Management
  getTrainingData: (params?: any) => api.get('/ai/training-data', { params }),
  uploadTrainingData: (modelId: string, files: File[], dataType: string) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('model_id', modelId);
    formData.append('data_type', dataType);
    return api.post('/ai/training-data/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  validateTrainingData: (id: string) => api.post(`/ai/training-data/${id}/validate`),
  deleteTrainingData: (id: string) => api.delete(`/ai/training-data/${id}`),
  bulkUploadTrainingData: (modelId: string, files: File[], dataType: string) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('model_id', modelId);
    formData.append('data_type', dataType);
    return api.post('/ai/training-data/bulk-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Model Training Status
  getTrainingJobs: (params?: any) => api.get('/ai/training-jobs', { params }),
  getTrainingJob: (id: string) => api.get(`/ai/training-jobs/${id}`),
  cancelTrainingJob: (id: string) => api.post(`/ai/training-jobs/${id}/cancel`),
  getTrainingProgress: (modelId: string) => api.get(`/ai/models/${modelId}/training-progress`),
  
  // Content Detection and Analysis
  detectContent: (data: any) => api.post('/ai/detect', data),
  bulkDetectContent: (data: any) => api.post('/ai/detect/bulk', data),
  analyzeImage: (file: File, modelId?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (modelId) formData.append('model_id', modelId);
    return api.post('/ai/analyze/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  analyzeVideo: (file: File, modelId?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (modelId) formData.append('model_id', modelId);
    return api.post('/ai/analyze/video', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  analyzeUrl: (url: string, modelId?: string) => api.post('/ai/analyze/url', { url, model_id: modelId }),
  
  // Detection Results Management
  getDetectionResults: (params?: any) => api.get('/ai/detection-results', { params }),
  getDetectionResult: (id: string) => api.get(`/ai/detection-results/${id}`),
  updateDetectionResult: (id: string, data: any) => api.put(`/ai/detection-results/${id}`, data),
  provideFeedback: (id: string, feedback: 'correct' | 'incorrect', notes?: string) => 
    api.post(`/ai/detection-results/${id}/feedback`, { feedback, notes }),
  bulkFeedback: (resultIds: string[], feedback: 'correct' | 'incorrect', notes?: string) =>
    api.post('/ai/detection-results/bulk-feedback', { result_ids: resultIds, feedback, notes }),
  
  // Content Fingerprinting
  getFingerprints: (params?: any) => api.get('/ai/fingerprints', { params }),
  createFingerprint: (data: any) => api.post('/ai/fingerprints', data),
  generateFingerprint: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/ai/fingerprints/generate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  compareFingerprints: (fingerprintId1: string, fingerprintId2: string) =>
    api.post('/ai/fingerprints/compare', { fingerprint1_id: fingerprintId1, fingerprint2_id: fingerprintId2 }),
  
  // Configuration and Settings
  getGlobalSettings: () => api.get('/ai/settings'),
  updateGlobalSettings: (settings: any) => api.put('/ai/settings', settings),
  getModelTypes: () => api.get('/ai/model-types'),
  getSupportedFormats: () => api.get('/ai/supported-formats'),
  getPerformanceMetrics: (modelId?: string) => 
    api.get('/ai/performance-metrics', { params: modelId ? { model_id: modelId } : {} }),
  
  // Real-time Processing
  startRealTimeDetection: (config: any) => api.post('/ai/real-time/start', config),
  stopRealTimeDetection: () => api.post('/ai/real-time/stop'),
  getRealTimeStatus: () => api.get('/ai/real-time/status'),
  
  // Batch Operations
  batchProcessContent: (data: any) => api.post('/ai/batch/process', data),
  getBatchJobs: (params?: any) => api.get('/ai/batch-jobs', { params }),
  getBatchJob: (id: string) => api.get(`/ai/batch-jobs/${id}`),
  cancelBatchJob: (id: string) => api.post(`/ai/batch-jobs/${id}/cancel`),
  
  // Analytics and Reporting
  getModelAnalytics: (modelId: string, params?: any) => 
    api.get(`/ai/models/${modelId}/analytics`, { params }),
  getSystemAnalytics: (params?: any) => api.get('/ai/analytics/system', { params }),
  getAccuracyReport: (modelId: string, params?: any) => 
    api.get(`/ai/models/${modelId}/accuracy-report`, { params }),
  getPerformanceReport: (params?: any) => api.get('/ai/performance-report', { params }),
  
  // Model Versioning
  getModelVersions: (modelId: string) => api.get(`/ai/models/${modelId}/versions`),
  createModelVersion: (modelId: string, data: any) => api.post(`/ai/models/${modelId}/versions`, data),
  rollbackToVersion: (modelId: string, versionId: string) => 
    api.post(`/ai/models/${modelId}/rollback/${versionId}`),
  
  // Export and Import
  exportModel: (modelId: string, format?: string) => 
    api.get(`/ai/models/${modelId}/export`, { params: { format } }),
  importModel: (file: File, config?: any) => {
    const formData = new FormData();
    formData.append('file', file);
    if (config) formData.append('config', JSON.stringify(config));
    return api.post('/ai/models/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Health and Monitoring
  getSystemHealth: () => api.get('/ai/health'),
  getModelHealth: (modelId: string) => api.get(`/ai/models/${modelId}/health`),
  testModelEndpoint: (modelId: string) => api.post(`/ai/models/${modelId}/test`),
};

// Social Media Protection API endpoints
export const socialMediaProtectionApi = {
  // Platform Management
  getPlatforms: (params?: any) => api.get('/social-media/platforms', { params }),
  getPlatform: (id: string) => api.get(`/social-media/platforms/${id}`),
  connectPlatform: (data: any) => api.post('/social-media/platforms/connect', data),
  disconnectPlatform: (id: string) => api.post(`/social-media/platforms/${id}/disconnect`),
  updatePlatformSettings: (id: string, settings: any) => api.put(`/social-media/platforms/${id}/settings`, settings),
  testPlatformConnection: (id: string) => api.post(`/social-media/platforms/${id}/test`),
  
  // Content Monitoring
  startScan: (platformId: string, config?: any) => api.post(`/social-media/platforms/${platformId}/scan`, config),
  stopScan: (platformId: string) => api.post(`/social-media/platforms/${platformId}/stop-scan`),
  getScanStatus: (platformId: string) => api.get(`/social-media/platforms/${platformId}/scan-status`),
  bulkScan: (platformIds: string[], config?: any) => api.post('/social-media/scan/bulk', { platformIds, ...config }),
  
  // Infringement Detection Results
  getIncidents: (params?: any) => api.get('/social-media/incidents', { params }),
  getIncident: (id: string) => api.get(`/social-media/incidents/${id}`),
  createIncident: (data: any) => api.post('/social-media/incidents', data),
  updateIncident: (id: string, data: any) => api.put(`/social-media/incidents/${id}`, data),
  deleteIncident: (id: string) => api.delete(`/social-media/incidents/${id}`),
  reportIncident: (id: string, data?: any) => api.post(`/social-media/incidents/${id}/report`, data),
  resolveIncident: (id: string, data?: any) => api.post(`/social-media/incidents/${id}/resolve`, data),
  escalateIncident: (id: string, data?: any) => api.post(`/social-media/incidents/${id}/escalate`, data),
  bulkIncidentAction: (action: string, incidentIds: string[], data?: any) => 
    api.post('/social-media/incidents/bulk-action', { action, incident_ids: incidentIds, ...data }),
  
  // Case Progression & Timeline
  getCaseProgression: (incidentId: string) => api.get(`/social-media/incidents/${incidentId}/progression`),
  addProgressionEntry: (incidentId: string, data: any) => 
    api.post(`/social-media/incidents/${incidentId}/progression`, data),
  
  // Automated Response Configuration
  getAutomationRules: (params?: any) => api.get('/social-media/automation-rules', { params }),
  getAutomationRule: (id: string) => api.get(`/social-media/automation-rules/${id}`),
  createAutomationRule: (data: any) => api.post('/social-media/automation-rules', data),
  updateAutomationRule: (id: string, data: any) => api.put(`/social-media/automation-rules/${id}`, data),
  deleteAutomationRule: (id: string) => api.delete(`/social-media/automation-rules/${id}`),
  toggleAutomationRule: (id: string, active: boolean) => 
    api.post(`/social-media/automation-rules/${id}/toggle`, { active }),
  testAutomationRule: (id: string) => api.post(`/social-media/automation-rules/${id}/test`),
  
  // Platform-specific Settings and Rules
  getPlatformRules: (platformId: string) => api.get(`/social-media/platforms/${platformId}/rules`),
  updatePlatformRules: (platformId: string, rules: any) => 
    api.put(`/social-media/platforms/${platformId}/rules`, rules),
  
  // Monitoring Statistics and Analytics
  getMonitoringStats: (params?: { 
    dateRange?: { start: string; end: string };
    platforms?: string[];
  }) => api.get('/social-media/stats', { params }),
  getPlatformAnalytics: (platformId: string, params?: any) => 
    api.get(`/social-media/platforms/${platformId}/analytics`, { params }),
  getIncidentAnalytics: (params?: any) => api.get('/social-media/analytics/incidents', { params }),
  getDetectionAccuracy: (params?: any) => api.get('/social-media/analytics/accuracy', { params }),
  
  // Identity Verification
  submitVerificationDocuments: (files: File[], data?: any) => {
    const formData = new FormData();
    files.forEach(file => formData.append('documents', file));
    if (data) {
      Object.keys(data).forEach(key => {
        formData.append(key, data[key]);
      });
    }
    return api.post('/social-media/identity-verification', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  getVerificationStatus: () => api.get('/social-media/identity-verification/status'),
  updateVerificationDocuments: (files: File[], data?: any) => {
    const formData = new FormData();
    files.forEach(file => formData.append('documents', file));
    if (data) {
      Object.keys(data).forEach(key => {
        formData.append(key, data[key]);
      });
    }
    return api.put('/social-media/identity-verification', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Evidence Management
  uploadEvidence: (incidentId: string, files: File[], description?: string) => {
    const formData = new FormData();
    files.forEach(file => formData.append('evidence', file));
    if (description) formData.append('description', description);
    return api.post(`/social-media/incidents/${incidentId}/evidence`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  deleteEvidence: (incidentId: string, evidenceId: string) => 
    api.delete(`/social-media/incidents/${incidentId}/evidence/${evidenceId}`),
  
  // Real-time Monitoring
  enableRealTimeMonitoring: (config: any) => api.post('/social-media/real-time/enable', config),
  disableRealTimeMonitoring: () => api.post('/social-media/real-time/disable'),
  getRealTimeStatus: () => api.get('/social-media/real-time/status'),
  getRealTimeMetrics: () => api.get('/social-media/real-time/metrics'),
  
  // WebSocket subscription for real-time updates
  subscribeToRealTimeUpdates: (subscriptionData: {
    types: ('incident' | 'scan_status' | 'platform_status' | 'automation')[];
    platforms?: string[];
  }) => api.post('/social-media/real-time/subscribe', subscriptionData),
  
  unsubscribeFromRealTimeUpdates: (subscriptionId: string) => 
    api.delete(`/social-media/real-time/subscribe/${subscriptionId}`),
  
  // Export and Reporting
  exportIncidents: (params?: {
    format: 'csv' | 'xlsx' | 'pdf';
    dateRange?: { start: string; end: string };
    platforms?: string[];
    statuses?: string[];
  }) => api.post('/social-media/export/incidents', params),
  
  generateReport: (params: {
    type: 'summary' | 'detailed' | 'platform_specific';
    dateRange: { start: string; end: string };
    platforms?: string[];
    format: 'pdf' | 'html';
  }) => api.post('/social-media/reports/generate', params),
  
  // Dashboard Data
  getDashboardData: (params?: {
    dateRange?: { start: string; end: string };
    refresh?: boolean;
  }) => api.get('/social-media/dashboard', { params }),
  
  // Platform-specific API integrations
  refreshPlatformData: (platformId: string) => api.post(`/social-media/platforms/${platformId}/refresh`),
  validatePlatformCredentials: (platformId: string, credentials: any) => 
    api.post(`/social-media/platforms/${platformId}/validate-credentials`, credentials),
  
  // Notification Management
  getNotificationSettings: () => api.get('/social-media/notifications/settings'),
  updateNotificationSettings: (settings: any) => api.put('/social-media/notifications/settings', settings),
  testNotification: (type: string, config?: any) => api.post('/social-media/notifications/test', { type, ...config }),
};

// Reports & Analytics API endpoints
export const reportsApi = {
  // Core Analytics Data
  getOverviewMetrics: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    contentTypes?: string[];
    timeGranularity?: 'hourly' | 'daily' | 'weekly' | 'monthly';
  }) => api.get('/reports/overview', { params }),
  
  getPlatformAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    includeCompliance?: boolean;
  }) => api.get('/reports/platforms', { params }),
  
  getContentAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    contentTypes?: string[];
    includeGeo?: boolean;
  }) => api.get('/reports/content', { params }),
  
  getComplianceMetrics: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    includeResponseTimes?: boolean;
  }) => api.get('/reports/compliance', { params }),
  
  // Time Series Data
  getTimeSeriesData: (params?: {
    dateRange?: { start: string; end: string };
    granularity?: 'hourly' | 'daily' | 'weekly' | 'monthly';
    metrics?: string[];
    platforms?: string[];
  }) => api.get('/reports/time-series', { params }),
  
  // Advanced Analytics
  getROIAnalysis: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    includeProjections?: boolean;
  }) => api.get('/reports/roi', { params }),
  
  getTrendAnalysis: (params?: {
    dateRange?: { start: string; end: string };
    trendType?: 'growth' | 'seasonal' | 'comparative';
    comparison?: { start: string; end: string };
  }) => api.get('/reports/trends', { params }),
  
  getPredictiveAnalytics: (params?: {
    forecastPeriod?: 'week' | 'month' | 'quarter';
    confidence?: number;
    includeScenarios?: boolean;
  }) => api.get('/reports/predictive', { params }),
  
  getComparativeAnalysis: (params?: {
    basePeriod: { start: string; end: string };
    comparePeriod: { start: string; end: string };
    metrics?: string[];
  }) => api.get('/reports/comparative', { params }),
  
  // Geographic and Demographic Data
  getGeographicAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    groupBy?: 'country' | 'region' | 'city';
    limit?: number;
  }) => api.get('/reports/geographic', { params }),
  
  getDemographicAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    includeAgeGroups?: boolean;
    includeInterests?: boolean;
  }) => api.get('/reports/demographics', { params }),
  
  // Report Generation and Export
  generateReport: (params: {
    reportType: 'comprehensive' | 'executive' | 'platform' | 'roi' | 'compliance';
    dateRange: { start: string; end: string };
    platforms?: string[];
    sections?: string[];
    format?: 'html' | 'pdf' | 'json';
    template?: string;
  }) => api.post('/reports/generate', params),
  
  scheduleReport: (params: {
    reportType: 'comprehensive' | 'executive' | 'platform' | 'roi' | 'compliance';
    schedule: {
      frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
      time?: string;
      dayOfWeek?: number;
      dayOfMonth?: number;
    };
    recipients: string[];
    dateRange?: 'last_week' | 'last_month' | 'last_quarter' | 'custom';
    customDateRange?: { start: string; end: string };
    platforms?: string[];
    sections?: string[];
    format: 'pdf' | 'csv' | 'excel';
    template?: string;
    active: boolean;
  }) => api.post('/reports/schedule', params),
  
  exportReport: (params: {
    reportId?: string;
    reportType?: 'comprehensive' | 'executive' | 'platform' | 'roi' | 'compliance';
    format: 'pdf' | 'csv' | 'excel' | 'json';
    dateRange?: { start: string; end: string };
    platforms?: string[];
    sections?: string[];
    template?: string;
  }) => api.post('/reports/export', params),
  
  // Report Templates
  getReportTemplates: (params?: {
    category?: 'executive' | 'operational' | 'compliance' | 'financial';
    active?: boolean;
  }) => api.get('/reports/templates', { params }),
  
  createReportTemplate: (template: {
    name: string;
    description: string;
    category: string;
    sections: string[];
    filters: Record<string, any>;
    chartConfigurations?: Record<string, any>;
    customFields?: Record<string, any>;
  }) => api.post('/reports/templates', template),
  
  updateReportTemplate: (templateId: string, template: any) => 
    api.put(`/reports/templates/${templateId}`, template),
  
  deleteReportTemplate: (templateId: string) => 
    api.delete(`/reports/templates/${templateId}`),
  
  // Scheduled Reports Management
  getScheduledReports: (params?: {
    status?: 'active' | 'inactive' | 'completed' | 'failed';
    limit?: number;
    offset?: number;
  }) => api.get('/reports/scheduled', { params }),
  
  getScheduledReport: (scheduleId: string) => 
    api.get(`/reports/scheduled/${scheduleId}`),
  
  updateScheduledReport: (scheduleId: string, updates: any) => 
    api.put(`/reports/scheduled/${scheduleId}`, updates),
  
  deleteScheduledReport: (scheduleId: string) => 
    api.delete(`/reports/scheduled/${scheduleId}`),
  
  pauseScheduledReport: (scheduleId: string) => 
    api.post(`/reports/scheduled/${scheduleId}/pause`),
  
  resumeScheduledReport: (scheduleId: string) => 
    api.post(`/reports/scheduled/${scheduleId}/resume`),
  
  // Report History and Status
  getReportHistory: (params?: {
    reportType?: string;
    status?: 'pending' | 'generating' | 'completed' | 'failed';
    dateRange?: { start: string; end: string };
    limit?: number;
    offset?: number;
  }) => api.get('/reports/history', { params }),
  
  getReportStatus: (reportId: string) => 
    api.get(`/reports/${reportId}/status`),
  
  getGeneratedReport: (reportId: string) => 
    api.get(`/reports/${reportId}/download`),
  
  deleteReport: (reportId: string) => 
    api.delete(`/reports/${reportId}`),
  
  // Performance Metrics
  getPerformanceMetrics: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    includeComparison?: boolean;
  }) => api.get('/reports/performance', { params }),
  
  getCostAnalysis: (params?: {
    dateRange?: { start: string; end: string };
    platforms?: string[];
    breakdownBy?: 'platform' | 'content_type' | 'time';
  }) => api.get('/reports/costs', { params }),
  
  getEfficiencyMetrics: (params?: {
    dateRange?: { start: string; end: string };
    includeProjections?: boolean;
  }) => api.get('/reports/efficiency', { params }),
  
  // Real-time Data
  getRealTimeMetrics: () => api.get('/reports/real-time'),
  
  subscribeToRealTimeUpdates: (subscriptionData: {
    metrics: string[];
    platforms?: string[];
    updateFrequency: 'high' | 'medium' | 'low';
  }) => api.post('/reports/real-time/subscribe', subscriptionData),
  
  unsubscribeFromRealTimeUpdates: (subscriptionId: string) => 
    api.delete(`/reports/real-time/subscribe/${subscriptionId}`),
  
  // Data Quality and Validation
  validateReportData: (params: {
    dateRange: { start: string; end: string };
    metrics?: string[];
    platforms?: string[];
  }) => api.post('/reports/validate', params),
  
  getDataQualityReport: (params?: {
    dateRange?: { start: string; end: string };
    includeRecommendations?: boolean;
  }) => api.get('/reports/data-quality', { params }),
  
  // Custom Metrics
  createCustomMetric: (metric: {
    name: string;
    description: string;
    formula: string;
    dependencies: string[];
    category: string;
  }) => api.post('/reports/custom-metrics', metric),
  
  getCustomMetrics: () => api.get('/reports/custom-metrics'),
  
  updateCustomMetric: (metricId: string, updates: any) => 
    api.put(`/reports/custom-metrics/${metricId}`, updates),
  
  deleteCustomMetric: (metricId: string) => 
    api.delete(`/reports/custom-metrics/${metricId}`),
  
  // Alerts and Thresholds
  getAlertRules: () => api.get('/reports/alerts'),
  
  createAlertRule: (alert: {
    name: string;
    metric: string;
    condition: 'above' | 'below' | 'equal';
    threshold: number;
    platform?: string;
    recipients: string[];
    active: boolean;
  }) => api.post('/reports/alerts', alert),
  
  updateAlertRule: (alertId: string, updates: any) => 
    api.put(`/reports/alerts/${alertId}`, updates),
  
  deleteAlertRule: (alertId: string) => 
    api.delete(`/reports/alerts/${alertId}`),
  
  // Report Sharing
  shareReport: (reportId: string, shareData: {
    recipients: string[];
    message?: string;
    permissions: 'view' | 'download';
    expiresAt?: string;
  }) => api.post(`/reports/${reportId}/share`, shareData),
  
  getSharedReports: () => api.get('/reports/shared'),
  
  revokeReportAccess: (reportId: string, shareId: string) => 
    api.delete(`/reports/${reportId}/share/${shareId}`),
};

// DMCA Templates API endpoints
export const dmcaTemplatesApi = {
  // Template CRUD operations
  getTemplates: (params?: {
    category?: string;
    status?: string;
    search?: string;
    page?: number;
    per_page?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => api.get('/dmca-templates', { params }),
  
  getTemplate: (id: string) => api.get(`/dmca-templates/${id}`),
  
  createTemplate: (data: any) => api.post('/dmca-templates', data),
  
  updateTemplate: (id: string, data: any) => api.put(`/dmca-templates/${id}`, data),
  
  deleteTemplate: (id: string) => api.delete(`/dmca-templates/${id}`),
  
  duplicateTemplate: (id: string, data?: { title?: string; category?: string }) => 
    api.post(`/dmca-templates/${id}/duplicate`, data),
  
  // Template categories and management
  getCategories: () => api.get('/dmca-templates/categories'),
  
  getCategoryTemplates: (category: string, params?: any) => 
    api.get(`/dmca-templates/categories/${category}`, { params }),
  
  // Legal compliance and validation
  validateTemplate: (id: string) => api.post(`/dmca-templates/${id}/validate`),
  
  validateTemplateContent: (content: string, category?: string, jurisdiction?: string) => 
    api.post('/dmca-templates/validate-content', { content, category, jurisdiction }),
  
  checkCompliance: (id: string, jurisdiction?: string) => 
    api.post(`/dmca-templates/${id}/check-compliance`, { jurisdiction }),
  
  getComplianceRequirements: (category: string, jurisdiction?: string) => 
    api.get('/dmca-templates/compliance-requirements', { 
      params: { category, jurisdiction } 
    }),
  
  // Template approval workflow
  submitForApproval: (id: string, data?: { notes?: string }) => 
    api.post(`/dmca-templates/${id}/submit-approval`, data),
  
  approveTemplate: (id: string, data?: { notes?: string; conditions?: string[] }) => 
    api.post(`/dmca-templates/${id}/approve`, data),
  
  rejectTemplate: (id: string, data: { reason: string; suggestions?: string[] }) => 
    api.post(`/dmca-templates/${id}/reject`, data),
  
  getApprovalHistory: (id: string) => api.get(`/dmca-templates/${id}/approval-history`),
  
  // Template generation and customization
  generateTemplate: (data: {
    type: 'standard' | 'platform-specific' | 'international';
    platform?: string;
    jurisdiction?: string;
    customFields?: Record<string, any>;
    baseTemplate?: string;
  }) => api.post('/dmca-templates/generate', data),
  
  customizeTemplate: (id: string, customizations: {
    variables?: Record<string, any>;
    platforms?: string[];
    jurisdiction?: string;
    additionalClauses?: string[];
  }) => api.post(`/dmca-templates/${id}/customize`, customizations),
  
  generatePreview: (id: string, previewData: any) => 
    api.post(`/dmca-templates/${id}/preview`, previewData),
  
  // Template variables and placeholders
  getTemplateVariables: (id: string) => api.get(`/dmca-templates/${id}/variables`),
  
  validateVariables: (id: string, variables: Record<string, any>) => 
    api.post(`/dmca-templates/${id}/validate-variables`, { variables }),
  
  getVariableDefinitions: () => api.get('/dmca-templates/variable-definitions'),
  
  // Platform-specific configurations
  getPlatformConfigs: () => api.get('/dmca-templates/platform-configs'),
  
  getPlatformConfig: (platform: string) => 
    api.get(`/dmca-templates/platform-configs/${platform}`),
  
  updatePlatformConfig: (platform: string, config: any) => 
    api.put(`/dmca-templates/platform-configs/${platform}`, config),
  
  validatePlatformRequirements: (templateId: string, platform: string) => 
    api.post(`/dmca-templates/${templateId}/validate-platform/${platform}`),
  
  // Jurisdiction and legal compliance
  getJurisdictions: () => api.get('/dmca-templates/jurisdictions'),
  
  getJurisdictionRequirements: (jurisdiction: string) => 
    api.get(`/dmca-templates/jurisdictions/${jurisdiction}/requirements`),
  
  validateJurisdictionCompliance: (templateId: string, jurisdiction: string) => 
    api.post(`/dmca-templates/${templateId}/validate-jurisdiction/${jurisdiction}`),
  
  // Template library and recommendations
  getTemplateLibrary: (params?: {
    category?: string;
    difficulty?: 'beginner' | 'intermediate' | 'advanced';
    platform?: string;
    jurisdiction?: string;
    tags?: string[];
  }) => api.get('/dmca-templates/library', { params }),
  
  getRecommendedTemplates: (params?: {
    based_on?: string;
    platform?: string;
    use_case?: string;
    limit?: number;
  }) => api.get('/dmca-templates/recommendations', { params }),
  
  // Usage analytics and statistics
  getTemplateUsage: (id: string, params?: {
    date_range?: { start: string; end: string };
    granularity?: 'daily' | 'weekly' | 'monthly';
  }) => api.get(`/dmca-templates/${id}/usage`, { params }),
  
  getUsageAnalytics: (params?: {
    category?: string;
    platform?: string;
    date_range?: { start: string; end: string };
    metrics?: string[];
  }) => api.get('/dmca-templates/analytics', { params }),
  
  trackUsage: (id: string, data: {
    context: string;
    platform?: string;
    success?: boolean;
    response_time?: number;
    metadata?: Record<string, any>;
  }) => api.post(`/dmca-templates/${id}/track-usage`, data),
  
  // Legal notice generation
  generateLegalNotice: (templateId: string, data: {
    recipient: {
      name: string;
      email: string;
      platform?: string;
    };
    infringement: {
      url: string;
      description: string;
      evidence_urls?: string[];
    };
    copyright_holder: {
      name: string;
      email: string;
      contact_info?: Record<string, any>;
    };
    custom_fields?: Record<string, any>;
  }) => api.post(`/dmca-templates/${templateId}/generate-notice`, data),
  
  getLegalNotices: (params?: {
    template_id?: string;
    status?: string;
    date_range?: { start: string; end: string };
    page?: number;
    per_page?: number;
  }) => api.get('/dmca-templates/legal-notices', { params }),
  
  getLegalNotice: (id: string) => api.get(`/dmca-templates/legal-notices/${id}`),
  
  sendLegalNotice: (id: string, data?: {
    delivery_method?: 'email' | 'platform_form' | 'certified_mail';
    schedule_time?: string;
    follow_up_enabled?: boolean;
  }) => api.post(`/dmca-templates/legal-notices/${id}/send`, data),
  
  // Bulk operations
  bulkAction: (data: {
    action: 'delete' | 'approve' | 'reject' | 'update_status' | 'duplicate' | 'export';
    template_ids: string[];
    parameters?: Record<string, any>;
  }) => api.post('/dmca-templates/bulk-action', data),
  
  bulkValidate: (template_ids: string[], jurisdiction?: string) => 
    api.post('/dmca-templates/bulk-validate', { template_ids, jurisdiction }),
  
  bulkUpdateCategory: (template_ids: string[], category: string) => 
    api.post('/dmca-templates/bulk-update-category', { template_ids, category }),
  
  // Import/Export
  exportTemplates: (params: {
    format: 'json' | 'xml' | 'csv' | 'pdf';
    template_ids?: string[];
    category?: string;
    include_audit_trail?: boolean;
    include_usage_stats?: boolean;
  }) => api.post('/dmca-templates/export', params),
  
  importTemplates: (file: File, options?: {
    format?: 'json' | 'xml' | 'csv';
    overwrite_existing?: boolean;
    validate_on_import?: boolean;
    default_category?: string;
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      Object.keys(options).forEach(key => {
        formData.append(key, (options as any)[key]);
      });
    }
    return api.post('/dmca-templates/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  getImportStatus: (import_id: string) => api.get(`/dmca-templates/import/${import_id}/status`),
  
  // Template versioning
  getVersions: (id: string) => api.get(`/dmca-templates/${id}/versions`),
  
  createVersion: (id: string, data: { notes?: string; major?: boolean }) => 
    api.post(`/dmca-templates/${id}/versions`, data),
  
  restoreVersion: (id: string, version_id: string) => 
    api.post(`/dmca-templates/${id}/restore-version/${version_id}`),
  
  compareVersions: (id: string, version1: string, version2: string) => 
    api.get(`/dmca-templates/${id}/compare-versions`, { 
      params: { version1, version2 } 
    }),
  
  // Audit trail and history
  getAuditTrail: (id: string, params?: {
    action_type?: string;
    user_id?: string;
    date_range?: { start: string; end: string };
    limit?: number;
  }) => api.get(`/dmca-templates/${id}/audit-trail`, { params }),
  
  getSystemAuditTrail: (params?: {
    action_type?: string;
    template_id?: string;
    user_id?: string;
    date_range?: { start: string; end: string };
    limit?: number;
    offset?: number;
  }) => api.get('/dmca-templates/audit-trail', { params }),
  
  // Real-time features and WebSocket subscriptions
  subscribeToUpdates: (subscription_data: {
    template_ids?: string[];
    categories?: string[];
    update_types: ('validation' | 'compliance' | 'usage' | 'approval')[];
  }) => api.post('/dmca-templates/subscribe', subscription_data),
  
  unsubscribe: (subscription_id: string) => 
    api.delete(`/dmca-templates/subscribe/${subscription_id}`),
  
  getRealtimeStatus: () => api.get('/dmca-templates/realtime-status'),
  
  // Testing and quality assurance
  testTemplate: (id: string, test_config: {
    test_type: 'compliance' | 'delivery' | 'response' | 'all';
    platform?: string;
    jurisdiction?: string;
    sample_data?: Record<string, any>;
  }) => api.post(`/dmca-templates/${id}/test`, test_config),
  
  getTestResults: (id: string, test_id?: string) => 
    api.get(`/dmca-templates/${id}/test-results`, { params: { test_id } }),
  
  // Dashboard and reporting
  getDashboardStats: (params?: {
    date_range?: { start: string; end: string };
    category?: string;
  }) => api.get('/dmca-templates/dashboard', { params }),
  
  getComplianceReport: (params?: {
    date_range?: { start: string; end: string };
    jurisdiction?: string;
    include_recommendations?: boolean;
  }) => api.get('/dmca-templates/compliance-report', { params }),
  
  getUsageReport: (params?: {
    date_range?: { start: string; end: string };
    template_ids?: string[];
    format?: 'summary' | 'detailed';
  }) => api.get('/dmca-templates/usage-report', { params }),
  
  // Search and filtering
  searchTemplates: (query: string, filters?: {
    category?: string;
    status?: string;
    platform?: string;
    jurisdiction?: string;
    tags?: string[];
    advanced?: {
      content_includes?: string;
      created_by?: string;
      date_range?: { start: string; end: string };
    };
  }) => api.post('/dmca-templates/search', { query, filters }),
  
  getSuggestions: (partial_query: string, context?: {
    category?: string;
    platform?: string;
    recent_templates?: string[];
  }) => api.get('/dmca-templates/suggestions', { 
    params: { q: partial_query, ...context } 
  }),
  
  // Template effectiveness analysis
  analyzeEffectiveness: (id: string, params?: {
    date_range?: { start: string; end: string };
    compare_against?: string[];
    metrics?: string[];
  }) => api.get(`/dmca-templates/${id}/effectiveness`, { params }),
  
  getEffectivenessReport: (params?: {
    category?: string;
    platform?: string;
    date_range?: { start: string; end: string };
    include_benchmarks?: boolean;
  }) => api.get('/dmca-templates/effectiveness-report', { params }),
  
  // Template collaboration features
  shareTemplate: (id: string, data: {
    recipients: string[];
    permissions: ('view' | 'edit' | 'approve')[];
    message?: string;
    expires_at?: string;
  }) => api.post(`/dmca-templates/${id}/share`, data),
  
  getSharedTemplates: (params?: {
    shared_with_me?: boolean;
    shared_by_me?: boolean;
    permissions?: string[];
  }) => api.get('/dmca-templates/shared', { params }),
  
  updateSharing: (id: string, share_id: string, data: {
    permissions?: ('view' | 'edit' | 'approve')[];
    expires_at?: string;
  }) => api.put(`/dmca-templates/${id}/share/${share_id}`, data),
  
  revokeSharing: (id: string, share_id: string) => 
    api.delete(`/dmca-templates/${id}/share/${share_id}`),
};

// Search Engine Delisting API endpoints
export const searchEngineDelistingApi = {
  // Search Engine Management
  getSearchEngines: (params?: any) => api.get('/search-engine-delisting/engines', { params }),
  getSearchEngine: (id: string) => api.get(`/search-engine-delisting/engines/${id}`),
  updateSearchEngine: (id: string, data: any) => api.put(`/search-engine-delisting/engines/${id}`, data),
  testSearchEngineConnection: (id: string) => api.post(`/search-engine-delisting/engines/${id}/test`),
  getSearchEngineStats: (id: string, params?: any) => 
    api.get(`/search-engine-delisting/engines/${id}/stats`, { params }),
  
  // Delisting Request Management
  getDelistingRequests: (params?: {
    status?: string[];
    engines?: string[];
    type?: string;
    priority?: string;
    region?: string;
    dateRange?: { start: string; end: string };
    page?: number;
    per_page?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => api.get('/search-engine-delisting/requests', { params }),
  
  getDelistingRequest: (id: string) => api.get(`/search-engine-delisting/requests/${id}`),
  
  createDelistingRequest: (data: {
    searchEngineIds: string[];
    type: string;
    priority: string;
    urls: string[];
    keywords?: string[];
    region?: string;
    reason: string;
    template?: string;
    metadata?: Record<string, any>;
  }) => api.post('/search-engine-delisting/requests', data),
  
  updateDelistingRequest: (id: string, data: any) => 
    api.put(`/search-engine-delisting/requests/${id}`, data),
  
  deleteDelistingRequest: (id: string) => api.delete(`/search-engine-delisting/requests/${id}`),
  
  submitDelistingRequest: (id: string) => api.post(`/search-engine-delisting/requests/${id}/submit`),
  
  cancelDelistingRequest: (id: string) => api.post(`/search-engine-delisting/requests/${id}/cancel`),
  
  retryDelistingRequest: (id: string) => api.post(`/search-engine-delisting/requests/${id}/retry`),
  
  // Bulk Operations
  bulkCreateRequests: (data: {
    searchEngineIds: string[];
    type: string;
    priority: string;
    urls: string[];
    region?: string;
    reason: string;
    template?: string;
    metadata?: Record<string, any>;
  }) => api.post('/search-engine-delisting/requests/bulk', data),
  
  bulkUpdateRequests: (requestIds: string[], data: any) => 
    api.put('/search-engine-delisting/requests/bulk-update', { request_ids: requestIds, ...data }),
  
  bulkSubmitRequests: (requestIds: string[]) => 
    api.post('/search-engine-delisting/requests/bulk-submit', { request_ids: requestIds }),
  
  bulkCancelRequests: (requestIds: string[]) => 
    api.post('/search-engine-delisting/requests/bulk-cancel', { request_ids: requestIds }),
  
  // URL Monitoring
  getUrlMonitoring: (params?: {
    url?: string;
    status?: string;
    engines?: string[];
    page?: number;
    per_page?: number;
  }) => api.get('/search-engine-delisting/monitoring', { params }),
  
  addUrlMonitoring: (data: {
    url: string;
    keywords: string[];
    searchEngines: string[];
    alerts: boolean;
    autoDelisting: boolean;
  }) => api.post('/search-engine-delisting/monitoring', data),
  
  updateUrlMonitoring: (id: string, data: any) => 
    api.put(`/search-engine-delisting/monitoring/${id}`, data),
  
  deleteUrlMonitoring: (id: string) => api.delete(`/search-engine-delisting/monitoring/${id}`),
  
  checkUrlVisibility: (id: string) => api.post(`/search-engine-delisting/monitoring/${id}/check`),
  
  bulkCheckVisibility: (monitorIds: string[]) => 
    api.post('/search-engine-delisting/monitoring/bulk-check', { monitor_ids: monitorIds }),
  
  // Search Results and Visibility
  searchUrl: (data: {
    url: string;
    keywords?: string[];
    searchEngines?: string[];
    region?: string;
  }) => api.post('/search-engine-delisting/search', data),
  
  getSearchHistory: (params?: {
    url?: string;
    engines?: string[];
    dateRange?: { start: string; end: string };
  }) => api.get('/search-engine-delisting/search-history', { params }),
  
  getVisibilityMetrics: (params?: {
    engines?: string[];
    dateRange?: { start: string; end: string };
    urls?: string[];
  }) => api.get('/search-engine-delisting/visibility-metrics', { params }),
  
  // Templates and Legal Notices
  getDelistingTemplates: (params?: {
    type?: string;
    searchEngine?: string;
    jurisdiction?: string;
    active?: boolean;
  }) => api.get('/search-engine-delisting/templates', { params }),
  
  getDelistingTemplate: (id: string) => api.get(`/search-engine-delisting/templates/${id}`),
  
  createDelistingTemplate: (data: {
    name: string;
    type: string;
    searchEngine?: string;
    jurisdiction?: string;
    subject: string;
    content: string;
    variables?: string[];
    metadata?: Record<string, any>;
  }) => api.post('/search-engine-delisting/templates', data),
  
  updateDelistingTemplate: (id: string, data: any) => 
    api.put(`/search-engine-delisting/templates/${id}`, data),
  
  deleteDelistingTemplate: (id: string) => api.delete(`/search-engine-delisting/templates/${id}`),
  
  generateLegalNotice: (templateId: string, data: {
    requestId: string;
    variables?: Record<string, any>;
  }) => api.post(`/search-engine-delisting/templates/${templateId}/generate`, data),
  
  // Analytics and Reporting
  getDashboardStats: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
    regions?: string[];
  }) => api.get('/search-engine-delisting/dashboard', { params }),
  
  getSuccessRateAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
    type?: string;
    granularity?: 'daily' | 'weekly' | 'monthly';
  }) => api.get('/search-engine-delisting/analytics/success-rates', { params }),
  
  getResponseTimeAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
    region?: string;
  }) => api.get('/search-engine-delisting/analytics/response-times', { params }),
  
  getVisibilityTrends: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
    urls?: string[];
    granularity?: 'daily' | 'weekly' | 'monthly';
  }) => api.get('/search-engine-delisting/analytics/visibility-trends', { params }),
  
  getRegionalAnalytics: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
  }) => api.get('/search-engine-delisting/analytics/regional', { params }),
  
  getEnginePerformance: (params?: {
    dateRange?: { start: string; end: string };
    engines?: string[];
  }) => api.get('/search-engine-delisting/analytics/engine-performance', { params }),
  
  // Real-time Status and Updates
  getRealTimeStatus: () => api.get('/search-engine-delisting/real-time/status'),
  
  getActiveRequests: () => api.get('/search-engine-delisting/real-time/active-requests'),
  
  subscribeToUpdates: (subscriptionData: {
    types: ('request_status' | 'visibility_change' | 'engine_response' | 'system_alert')[];
    engines?: string[];
    requests?: string[];
  }) => api.post('/search-engine-delisting/real-time/subscribe', subscriptionData),
  
  unsubscribeFromUpdates: (subscriptionId: string) => 
    api.delete(`/search-engine-delisting/real-time/subscribe/${subscriptionId}`),
  
  // Search Engine Integration Management
  configureEngineIntegration: (engineId: string, config: {
    apiKey?: string;
    apiSecret?: string;
    webhookUrl?: string;
    rateLimits?: Record<string, number>;
    regions?: string[];
    features?: string[];
  }) => api.post(`/search-engine-delisting/engines/${engineId}/configure`, config),
  
  testEngineIntegration: (engineId: string, testData?: any) => 
    api.post(`/search-engine-delisting/engines/${engineId}/test-integration`, testData),
  
  getEngineCapabilities: (engineId: string) => 
    api.get(`/search-engine-delisting/engines/${engineId}/capabilities`),
  
  refreshEngineStatus: (engineId: string) => 
    api.post(`/search-engine-delisting/engines/${engineId}/refresh-status`),
  
  // Automated Processing and Workflows
  enableAutomatedProcessing: (config: {
    engines?: string[];
    autoSubmit?: boolean;
    autoRetry?: boolean;
    maxRetries?: number;
    retryDelay?: number;
    notificationSettings?: Record<string, any>;
  }) => api.post('/search-engine-delisting/automation/enable', config),
  
  disableAutomatedProcessing: () => api.post('/search-engine-delisting/automation/disable'),
  
  getAutomationStatus: () => api.get('/search-engine-delisting/automation/status'),
  
  getAutomationRules: () => api.get('/search-engine-delisting/automation/rules'),
  
  createAutomationRule: (rule: {
    name: string;
    trigger: string;
    conditions: Record<string, any>;
    action: string;
    actionConfig: Record<string, any>;
    isActive: boolean;
  }) => api.post('/search-engine-delisting/automation/rules', rule),
  
  updateAutomationRule: (ruleId: string, data: any) => 
    api.put(`/search-engine-delisting/automation/rules/${ruleId}`, data),
  
  deleteAutomationRule: (ruleId: string) => 
    api.delete(`/search-engine-delisting/automation/rules/${ruleId}`),
  
  toggleAutomationRule: (ruleId: string, active: boolean) => 
    api.post(`/search-engine-delisting/automation/rules/${ruleId}/toggle`, { active }),
  
  // Progress Tracking and Notifications
  getRequestProgress: (requestId: string) => 
    api.get(`/search-engine-delisting/requests/${requestId}/progress`),
  
  getProgressHistory: (requestId: string) => 
    api.get(`/search-engine-delisting/requests/${requestId}/progress-history`),
  
  setProgressNotifications: (requestId: string, config: {
    emailEnabled: boolean;
    webhookEnabled: boolean;
    webhookUrl?: string;
    stages?: string[];
  }) => api.post(`/search-engine-delisting/requests/${requestId}/notifications`, config),
  
  // Export and Reporting
  exportDelistingData: (params: {
    format: 'csv' | 'xlsx' | 'pdf' | 'json';
    type: 'requests' | 'monitoring' | 'analytics' | 'all';
    dateRange?: { start: string; end: string };
    engines?: string[];
    statuses?: string[];
    includeDetails?: boolean;
  }) => api.post('/search-engine-delisting/export', params),
  
  generateReport: (config: {
    type: 'summary' | 'detailed' | 'compliance' | 'performance';
    dateRange: { start: string; end: string };
    engines?: string[];
    regions?: string[];
    format: 'pdf' | 'html';
    includeCharts?: boolean;
  }) => api.post('/search-engine-delisting/reports/generate', config),
  
  getReportHistory: (params?: {
    type?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }) => api.get('/search-engine-delisting/reports', { params }),
  
  getReport: (reportId: string) => api.get(`/search-engine-delisting/reports/${reportId}`),
  
  downloadReport: (reportId: string) => api.get(`/search-engine-delisting/reports/${reportId}/download`),
  
  // URL and Content Validation
  validateUrls: (urls: string[]) => 
    api.post('/search-engine-delisting/validate-urls', { urls }),
  
  checkUrlsIndexStatus: (data: {
    urls: string[];
    searchEngines: string[];
    regions?: string[];
  }) => api.post('/search-engine-delisting/check-index-status', data),
  
  estimateRemovalImpact: (data: {
    urls: string[];
    searchEngines: string[];
    keywords?: string[];
  }) => api.post('/search-engine-delisting/estimate-impact', data),
  
  // System Health and Monitoring
  getSystemHealth: () => api.get('/search-engine-delisting/system/health'),
  
  getSystemMetrics: () => api.get('/search-engine-delisting/system/metrics'),
  
  getQueueStatus: () => api.get('/search-engine-delisting/system/queue-status'),
  
  getErrorLogs: (params?: {
    level?: 'error' | 'warning' | 'info';
    component?: string;
    dateRange?: { start: string; end: string };
    page?: number;
    per_page?: number;
  }) => api.get('/search-engine-delisting/system/logs', { params }),
  
  // Configuration and Settings
  getSystemConfig: () => api.get('/search-engine-delisting/config'),
  
  updateSystemConfig: (config: {
    defaultSettings?: Record<string, any>;
    rateLimits?: Record<string, number>;
    timeouts?: Record<string, number>;
    retryConfig?: Record<string, any>;
    notificationDefaults?: Record<string, any>;
  }) => api.put('/search-engine-delisting/config', config),
  
  getRegionSettings: () => api.get('/search-engine-delisting/config/regions'),
  
  updateRegionSettings: (regionId: string, config: any) => 
    api.put(`/search-engine-delisting/config/regions/${regionId}`, config),
};

// Content Watermarking API endpoints
export const contentWatermarkingApi = {
  // Content Processing
  uploadContent: (files: File[], metadata?: any) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    if (metadata) {
      Object.keys(metadata).forEach(key => {
        formData.append(key, metadata[key]);
      });
    }
    return api.post('/content-watermarking/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  applyWatermark: (contentId: string, templateId: string, options?: any) =>
    api.post(`/content-watermarking/content/${contentId}/apply-watermark`, {
      template_id: templateId,
      ...options
    }),
  
  removeWatermark: (contentId: string, watermarkId: string) =>
    api.post(`/content-watermarking/content/${contentId}/remove-watermark/${watermarkId}`),
  
  previewWatermark: (contentId: string, templateId: string, options?: any) =>
    api.post(`/content-watermarking/content/${contentId}/preview`, {
      template_id: templateId,
      ...options
    }),
  
  // Content Management
  getContent: (params?: {
    status?: string;
    type?: string;
    search?: string;
    page?: number;
    per_page?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => api.get('/content-watermarking/content', { params }),
  
  getContentDetails: (id: string) => api.get(`/content-watermarking/content/${id}`),
  
  updateContent: (id: string, data: any) => api.put(`/content-watermarking/content/${id}`, data),
  
  deleteContent: (id: string) => api.delete(`/content-watermarking/content/${id}`),
  
  downloadContent: (id: string, watermarked?: boolean) =>
    api.get(`/content-watermarking/content/${id}/download`, {
      params: { watermarked: watermarked || false },
      responseType: 'blob'
    }),
  
  // Watermark Templates
  getTemplates: (params?: {
    category?: string;
    type?: string;
    search?: string;
    page?: number;
    per_page?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => api.get('/content-watermarking/templates', { params }),
  
  getTemplate: (id: string) => api.get(`/content-watermarking/templates/${id}`),
  
  createTemplate: (data: {
    name: string;
    type: 'text' | 'image' | 'logo';
    category: string;
    settings: Record<string, any>;
    preview?: File;
    description?: string;
  }) => {
    const formData = new FormData();
    formData.append('name', data.name);
    formData.append('type', data.type);
    formData.append('category', data.category);
    formData.append('settings', JSON.stringify(data.settings));
    if (data.preview) formData.append('preview', data.preview);
    if (data.description) formData.append('description', data.description);
    
    return api.post('/content-watermarking/templates', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  updateTemplate: (id: string, data: any) => api.put(`/content-watermarking/templates/${id}`, data),
  
  deleteTemplate: (id: string) => api.delete(`/content-watermarking/templates/${id}`),
  
  duplicateTemplate: (id: string, name?: string) =>
    api.post(`/content-watermarking/templates/${id}/duplicate`, { name }),
  
  getTemplatePreview: (id: string, sampleContentId?: string) =>
    api.get(`/content-watermarking/templates/${id}/preview`, {
      params: sampleContentId ? { sample_content_id: sampleContentId } : {}
    }),
  
  // Template Library
  getLibraryTemplates: (params?: {
    category?: string;
    type?: string;
    popularity?: 'high' | 'medium' | 'low';
    free_only?: boolean;
    page?: number;
    per_page?: number;
  }) => api.get('/content-watermarking/library', { params }),
  
  installTemplate: (templateId: string) =>
    api.post(`/content-watermarking/library/${templateId}/install`),
  
  rateTemplate: (templateId: string, rating: number, review?: string) =>
    api.post(`/content-watermarking/library/${templateId}/rate`, { rating, review }),
  
  // Batch Operations
  createBatchJob: (data: {
    name: string;
    content_ids: string[];
    template_id: string;
    options?: Record<string, any>;
    output_format?: 'original' | 'jpg' | 'png' | 'pdf';
    quality?: 'low' | 'medium' | 'high';
  }) => api.post('/content-watermarking/batch', data),
  
  getBatchJobs: (params?: {
    status?: string;
    date_range?: { start: string; end: string };
    page?: number;
    per_page?: number;
  }) => api.get('/content-watermarking/batch', { params }),
  
  getBatchJob: (id: string) => api.get(`/content-watermarking/batch/${id}`),
  
  cancelBatchJob: (id: string) => api.post(`/content-watermarking/batch/${id}/cancel`),
  
  retryBatchJob: (id: string) => api.post(`/content-watermarking/batch/${id}/retry`),
  
  downloadBatchResult: (id: string) =>
    api.get(`/content-watermarking/batch/${id}/download`, {
      responseType: 'blob'
    }),
  
  // Detection & Verification
  detectWatermark: (file: File, options?: {
    sensitivity?: 'low' | 'medium' | 'high';
    expected_templates?: string[];
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      Object.keys(options).forEach(key => {
        formData.append(key, JSON.stringify((options as any)[key]));
      });
    }
    return api.post('/content-watermarking/detect', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  verifyWatermark: (contentId: string, expectedWatermarkId?: string) =>
    api.post(`/content-watermarking/content/${contentId}/verify`, {
      expected_watermark_id: expectedWatermarkId
    }),
  
  getDetectionHistory: (params?: {
    content_id?: string;
    date_range?: { start: string; end: string };
    result_type?: 'detected' | 'not_detected' | 'error';
    page?: number;
    per_page?: number;
  }) => api.get('/content-watermarking/detection-history', { params }),
  
  bulkDetection: (files: File[], options?: any) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    if (options) {
      Object.keys(options).forEach(key => {
        formData.append(key, JSON.stringify(options[key]));
      });
    }
    return api.post('/content-watermarking/detect/bulk', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Analytics & Tracking
  getAnalytics: (params?: {
    date_range?: { start: string; end: string };
    granularity?: 'daily' | 'weekly' | 'monthly';
    metrics?: string[];
  }) => api.get('/content-watermarking/analytics', { params }),
  
  getUsageStats: () => api.get('/content-watermarking/usage'),
  
  getContentStats: (contentId: string) =>
    api.get(`/content-watermarking/content/${contentId}/stats`),
  
  getTemplateStats: (templateId: string, params?: {
    date_range?: { start: string; end: string };
  }) => api.get(`/content-watermarking/templates/${templateId}/stats`, { params }),
  
  getDetectionAnalytics: (params?: {
    date_range?: { start: string; end: string };
    template_ids?: string[];
    content_types?: string[];
  }) => api.get('/content-watermarking/analytics/detection', { params }),
  
  getPerformanceMetrics: () => api.get('/content-watermarking/analytics/performance'),
  
  // Dashboard Data
  getDashboard: (params?: {
    date_range?: { start: string; end: string };
    refresh?: boolean;
  }) => api.get('/content-watermarking/dashboard', { params }),
  
  getRecentActivity: (limit?: number) =>
    api.get('/content-watermarking/activity', { params: { limit } }),
  
  getQuickStats: () => api.get('/content-watermarking/quick-stats'),
  
  // Settings & Configuration
  getSettings: () => api.get('/content-watermarking/settings'),
  
  updateSettings: (settings: {
    default_quality?: 'low' | 'medium' | 'high';
    auto_backup?: boolean;
    retention_days?: number;
    notification_preferences?: Record<string, any>;
    processing_options?: Record<string, any>;
  }) => api.put('/content-watermarking/settings', settings),
  
  getProcessingQueue: () => api.get('/content-watermarking/queue'),
  
  // Export & Import
  exportContent: (params: {
    content_ids?: string[];
    format?: 'zip' | 'folder';
    include_originals?: boolean;
    include_watermarked?: boolean;
    include_metadata?: boolean;
  }) => api.post('/content-watermarking/export', params),
  
  importContent: (file: File, options?: {
    extract_metadata?: boolean;
    auto_detect_watermarks?: boolean;
    organize_by_type?: boolean;
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      Object.keys(options).forEach(key => {
        formData.append(key, (options as any)[key]);
      });
    }
    return api.post('/content-watermarking/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  getImportStatus: (importId: string) =>
    api.get(`/content-watermarking/import/${importId}/status`),
  
  // Real-time Updates
  subscribeToUpdates: (subscriptionData: {
    types: ('content_processing' | 'batch_progress' | 'detection_result' | 'template_update')[];
    content_ids?: string[];
    batch_ids?: string[];
  }) => api.post('/content-watermarking/subscribe', subscriptionData),
  
  unsubscribeFromUpdates: (subscriptionId: string) =>
    api.delete(`/content-watermarking/subscribe/${subscriptionId}`),
  
  getRealTimeStatus: () => api.get('/content-watermarking/realtime-status'),
  
  // System Health
  getSystemHealth: () => api.get('/content-watermarking/health'),
  
  getSystemMetrics: () => api.get('/content-watermarking/metrics'),
  
  // Content Organization
  getCollections: () => api.get('/content-watermarking/collections'),
  
  createCollection: (data: {
    name: string;
    description?: string;
    content_ids?: string[];
  }) => api.post('/content-watermarking/collections', data),
  
  updateCollection: (id: string, data: any) =>
    api.put(`/content-watermarking/collections/${id}`, data),
  
  deleteCollection: (id: string) =>
    api.delete(`/content-watermarking/collections/${id}`),
  
  addToCollection: (collectionId: string, contentIds: string[]) =>
    api.post(`/content-watermarking/collections/${collectionId}/content`, { content_ids: contentIds }),
  
  removeFromCollection: (collectionId: string, contentIds: string[]) =>
    api.delete(`/content-watermarking/collections/${collectionId}/content`, {
      data: { content_ids: contentIds }
    }),
};

export default api;