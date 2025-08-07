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

export default api;