// TypeScript interfaces for Search Engine Delisting functionality
// Matches backend schemas from backend/app/schemas/delisting.py

export enum SearchEngine {
  GOOGLE = 'google',
  BING = 'bing', 
  YAHOO = 'yahoo',
  YANDEX = 'yandex'
}

export enum DelistingPriority {
  LOW = 'low',
  NORMAL = 'normal', 
  HIGH = 'high',
  URGENT = 'urgent'
}

export enum DelistingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  SUBMITTED = 'submitted',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  RETRYING = 'retrying'
}

export interface DelistingRequestCreate {
  url: string;
  originalContentUrl?: string;
  reason?: string;
  evidenceUrl?: string;
  priority: DelistingPriority;
  searchEngines: SearchEngine[];
  profileId?: string;
}

export interface DelistingRequest extends DelistingRequestCreate {
  id: string;
  status: DelistingStatus;
  userId: string;
  createdAt: string;
  updatedAt: string;
  submittedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  retryCount: number;
  searchEngineResponses?: SearchEngineResponse[];
}

export interface DelistingRequestResponse {
  id: string;
  url: string;
  status: DelistingStatus;
  searchEngines: string[];
  submittedAt: string;
  message: string;
}

export interface SearchEngineResponse {
  engine: SearchEngine;
  status: DelistingStatus;
  requestId?: string;
  submittedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  successDetails?: any;
}

export interface DelistingBatchCreate {
  urls: string[];
  originalContentUrl?: string;
  reason?: string;
  evidenceUrl?: string;
  priority: DelistingPriority;
  searchEngines: SearchEngine[];
  profileId?: string;
}

export interface DelistingBatch {
  id: string;
  totalUrls: number;
  processedUrls: number;
  successfulUrls: number;
  failedUrls: number;
  status: DelistingStatus;
  createdAt: string;
  updatedAt: string;
  requests: DelistingRequest[];
}

export interface DelistingStatistics {
  totalRequests: number;
  pendingRequests: number;
  completedRequests: number;
  failedRequests: number;
  successRate: number;
  averageProcessingTime: number; // in minutes
  searchEngineBreakdown: Record<SearchEngine, {
    total: number;
    successful: number;
    failed: number;
    successRate: number;
  }>;
  recentActivity: DelistingActivityItem[];
}

export interface DelistingActivityItem {
  id: string;
  url: string;
  status: DelistingStatus;
  searchEngine: SearchEngine;
  timestamp: string;
  type: 'submitted' | 'completed' | 'failed' | 'retry';
}

export interface DashboardMetrics {
  activeRequests: number;
  completedToday: number;
  successRateToday: number;
  avgResponseTime: number;
  systemAlerts: AlertSummary[];
  recentActivity: RecentActivity[];
}

export interface AlertSummary {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  triggeredAt: string;
  isActive: boolean;
}

export interface RecentActivity {
  id: string;
  url: string;
  status: DelistingStatus;
  createdAt: string;
}

export interface DelistingVerificationResponse {
  requestId: string;
  verificationStatus: 'pending' | 'in_progress' | 'completed' | 'failed';
  results: VerificationResult[];
  lastChecked: string;
}

export interface VerificationResult {
  searchEngine: SearchEngine;
  url: string;
  isDelisted: boolean;
  lastSeen?: string;
  notes?: string;
}

// Form interfaces for UI components
export interface SingleDelistingFormData {
  url: string;
  originalContentUrl: string;
  reason: string;
  evidenceUrl: string;
  priority: DelistingPriority;
  searchEngines: SearchEngine[];
  profileId: string;
}

export interface BatchDelistingFormData {
  csvFile?: File;
  urls: string[];
  originalContentUrl: string;
  reason: string;
  evidenceUrl: string;
  priority: DelistingPriority;
  searchEngines: SearchEngine[];
  profileId: string;
}

export interface DelistingFilters {
  status?: DelistingStatus[];
  searchEngine?: SearchEngine[];
  priority?: DelistingPriority[];
  dateRange?: {
    start: string;
    end: string;
  };
  searchTerm?: string;
}

// API response wrappers
export interface DelistingApiResponse<T = any> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedDelistingResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}