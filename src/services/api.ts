import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { 
  User, 
  LoginCredentials, 
  RegisterData, 
  Infringement, 
  InfringementFilter,
  DashboardStats,
  ManualSubmission,
  ProfileUpdateData,
  AccountSettings,
  ApiResponse,
  PaginatedResponse 
} from '@types/index';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3001/api',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<ApiResponse<{ user: User; token: string }>> {
    const response = await this.api.post('/auth/login', credentials);
    return response.data;
  }

  async register(userData: RegisterData): Promise<ApiResponse<{ user: User; token: string }>> {
    const response = await this.api.post('/auth/register', userData);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    localStorage.removeItem('authToken');
  }

  async refreshToken(): Promise<ApiResponse<{ token: string }>> {
    const response = await this.api.post('/auth/refresh');
    return response.data;
  }

  async verifyEmail(token: string): Promise<ApiResponse<{ message: string }>> {
    const response = await this.api.post('/auth/verify-email', { token });
    return response.data;
  }

  async forgotPassword(email: string): Promise<ApiResponse<{ message: string }>> {
    const response = await this.api.post('/auth/forgot-password', { email });
    return response.data;
  }

  // User profile endpoints
  async getProfile(): Promise<ApiResponse<User>> {
    const response = await this.api.get('/user/profile');
    return response.data;
  }

  async updateProfile(data: ProfileUpdateData): Promise<ApiResponse<User>> {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (value instanceof File) {
        formData.append(key, value);
      } else if (value !== undefined) {
        formData.append(key, String(value));
      }
    });

    const response = await this.api.put('/user/profile', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async getAccountSettings(): Promise<ApiResponse<AccountSettings>> {
    const response = await this.api.get('/user/settings');
    return response.data;
  }

  async updateAccountSettings(settings: AccountSettings): Promise<ApiResponse<AccountSettings>> {
    const response = await this.api.put('/user/settings', settings);
    return response.data;
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    const response = await this.api.get('/dashboard/stats');
    return response.data;
  }

  async getRecentActivity(limit = 10): Promise<ApiResponse<any[]>> {
    const response = await this.api.get(`/dashboard/activity?limit=${limit}`);
    return response.data;
  }

  // Infringement endpoints
  async getInfringements(
    page = 1,
    limit = 20,
    filters?: InfringementFilter
  ): Promise<PaginatedResponse<Infringement>> {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });

    if (filters) {
      if (filters.status?.length) params.append('status', filters.status.join(','));
      if (filters.platform?.length) params.append('platform', filters.platform.join(','));
      if (filters.contentType?.length) params.append('contentType', filters.contentType.join(','));
      if (filters.searchQuery) params.append('search', filters.searchQuery);
      if (filters.dateRange) {
        params.append('startDate', filters.dateRange.start.toISOString());
        params.append('endDate', filters.dateRange.end.toISOString());
      }
    }

    const response = await this.api.get(`/infringements?${params}`);
    return response.data;
  }

  async getInfringement(id: string): Promise<ApiResponse<Infringement>> {
    const response = await this.api.get(`/infringements/${id}`);
    return response.data;
  }

  async updateInfringementStatus(
    id: string,
    status: string,
    notes?: string
  ): Promise<ApiResponse<Infringement>> {
    const response = await this.api.patch(`/infringements/${id}`, { status, notes });
    return response.data;
  }

  async deleteInfringement(id: string): Promise<ApiResponse<{ message: string }>> {
    const response = await this.api.delete(`/infringements/${id}`);
    return response.data;
  }

  // Manual submission endpoints
  async submitUrls(submission: ManualSubmission): Promise<ApiResponse<{ submissionId: string }>> {
    const response = await this.api.post('/submissions', submission);
    return response.data;
  }

  async getSubmissions(page = 1, limit = 20): Promise<PaginatedResponse<any>> {
    const response = await this.api.get(`/submissions?page=${page}&limit=${limit}`);
    return response.data;
  }

  // Monitoring endpoints
  async addMonitoringUrl(url: string, contentType: string): Promise<ApiResponse<{ message: string }>> {
    const response = await this.api.post('/monitoring', { url, contentType });
    return response.data;
  }

  async getMonitoringUrls(): Promise<ApiResponse<any[]>> {
    const response = await this.api.get('/monitoring');
    return response.data;
  }

  async removeMonitoringUrl(id: string): Promise<ApiResponse<{ message: string }>> {
    const response = await this.api.delete(`/monitoring/${id}`);
    return response.data;
  }

  // Statistics endpoints
  async getAnalytics(period: 'day' | 'week' | 'month' | 'year' = 'month'): Promise<ApiResponse<any>> {
    const response = await this.api.get(`/analytics?period=${period}`);
    return response.data;
  }

  async exportData(format: 'csv' | 'json' = 'csv'): Promise<Blob> {
    const response = await this.api.get(`/export?format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();

// Export for dependency injection in tests
export default ApiService;