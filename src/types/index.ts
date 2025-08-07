// User and Authentication Types
export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  avatar?: string;
  role: 'creator' | 'admin';
  subscription: 'free' | 'pro' | 'enterprise';
  createdAt: string;
  lastActive: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  confirmPassword: string;
}

// Infringement Types
export interface Infringement {
  id: string;
  url: string;
  contentType: 'video' | 'image' | 'audio' | 'text';
  platform: string;
  status: 'detected' | 'pending' | 'removed' | 'failed' | 'reviewing';
  confidence: number;
  detectedAt: string;
  resolvedAt?: string;
  description?: string;
  originalContent?: {
    title: string;
    url: string;
    thumbnail?: string;
  };
}

export interface InfringementFilter {
  status?: string[];
  platform?: string[];
  contentType?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
}

// Dashboard Statistics Types
export interface DashboardStats {
  totalInfringements: number;
  activeMonitoring: number;
  successfulTakedowns: number;
  pendingReviews: number;
  recentActivity: Activity[];
  chartData: {
    monthly: {
      labels: string[];
      detected: number[];
      resolved: number[];
    };
    platforms: {
      platform: string;
      count: number;
    }[];
    contentTypes: {
      type: string;
      count: number;
      percentage: number;
    }[];
  };
}

export interface Activity {
  id: string;
  type: 'detection' | 'takedown' | 'review' | 'upload';
  description: string;
  timestamp: string;
  status?: string;
}

// Manual Submission Types
export interface ManualSubmission {
  urls: string[];
  contentType: 'video' | 'image' | 'audio' | 'text';
  description?: string;
  originalContentUrl?: string;
  priority: 'low' | 'medium' | 'high';
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'infringement_detected' | 'status_update' | 'takedown_success' | 'system_alert';
  data: any;
  timestamp: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

// Form Types
export interface ProfileUpdateData {
  firstName: string;
  lastName: string;
  email: string;
  avatar?: File;
}

export interface AccountSettings {
  notifications: {
    email: boolean;
    push: boolean;
    sms: boolean;
  };
  monitoring: {
    autoTakedown: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    platforms: string[];
  };
  privacy: {
    profileVisible: boolean;
    shareAnalytics: boolean;
  };
}

// Theme Types
export interface ThemeMode {
  mode: 'light' | 'dark';
}

// Navigation Types
export interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType;
  badge?: number;
}