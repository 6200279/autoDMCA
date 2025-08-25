// Import DMCA template types
import type { IDMCATemplate, TemplateCategoryType } from './dmca';

// User types
export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  phone?: string;
  company?: string;
  bio?: string;
  avatar_url?: string;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserRegister {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  company?: string;
}

// Subscription types
export enum SubscriptionPlan {
  FREE = "free",
  BASIC = "basic",
  PROFESSIONAL = "professional",
  ENTERPRISE = "enterprise",
}

export enum SubscriptionStatus {
  ACTIVE = "active",
  CANCELED = "canceled",
  PAST_DUE = "past_due",
  INCOMPLETE = "incomplete",
  INCOMPLETE_EXPIRED = "incomplete_expired",
  TRIALING = "trialing",
  UNPAID = "unpaid",
}

export interface Subscription {
  id: number;
  user_id: number;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  amount: number;
  currency: string;
  interval: string;
  current_period_start?: string;
  current_period_end?: string;
  max_protected_profiles: number;
  max_monthly_scans: number;
  max_takedown_requests: number;
  ai_face_recognition: boolean;
  priority_support: boolean;
  custom_branding: boolean;
  api_access: boolean;
  created_at: string;
  updated_at?: string;
}

// Protected Profile types
export interface ProtectedProfile {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  stage_name?: string;
  reference_images?: string[];
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  contact_address?: string;
  is_active: boolean;
  auto_scan: boolean;
  scan_frequency_hours: number;
  search_keywords?: string[];
  excluded_domains?: string[];
  total_infringements_found: number;
  total_takedowns_sent: number;
  success_rate: number;
  created_at: string;
  updated_at?: string;
  last_scan?: string;
}

export interface CreateProtectedProfile {
  name: string;
  description?: string;
  stage_name?: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  contact_address?: string;
  search_keywords?: string[];
  excluded_domains?: string[];
}

// Infringement types
export enum InfringementType {
  IMAGE = "image",
  VIDEO = "video",
  PROFILE = "profile",
  CONTENT = "content",
}

export enum InfringementStatus {
  PENDING = "pending",
  VERIFIED = "verified",
  FALSE_POSITIVE = "false_positive",
  TAKEDOWN_SENT = "takedown_sent",
  RESOLVED = "resolved",
  ESCALATED = "escalated",
}

export interface Infringement {
  id: number;
  profile_id: number;
  reporter_id?: number;
  type: InfringementType;
  status: InfringementStatus;
  url: string;
  domain: string;
  platform?: string;
  title?: string;
  description?: string;
  screenshot_url?: string;
  confidence_score?: number;
  detection_method?: string;
  is_verified: boolean;
  verified_at?: string;
  reviewer_notes?: string;
  priority: number;
  estimated_views?: number;
  estimated_revenue_impact?: number;
  detected_at: string;
  first_seen: string;
  last_seen: string;
  resolved_at?: string;
}

// Takedown Request types
export enum TakedownStatus {
  DRAFT = "draft",
  SENT = "sent",
  ACKNOWLEDGED = "acknowledged",
  COMPLIED = "complied",
  REFUSED = "refused",
  COUNTER_NOTICE = "counter_notice",
  ESCALATED = "escalated",
  EXPIRED = "expired",
}

export enum TakedownMethod {
  EMAIL = "email",
  PLATFORM_FORM = "platform_form",
  LEGAL_NOTICE = "legal_notice",
  API = "api",
}

export interface TakedownRequest {
  id: number;
  user_id: number;
  infringement_id: number;
  status: TakedownStatus;
  method: TakedownMethod;
  recipient_name?: string;
  recipient_email?: string;
  platform_name: string;
  subject: string;
  body: string;
  copyright_owner: string;
  original_work_description: string;
  infringement_description: string;
  good_faith_statement: string;
  accuracy_statement: string;
  signature: string;
  reference_number?: string;
  sent_at?: string;
  response_deadline?: string;
  response_received: boolean;
  response_date?: string;
  response_content?: string;
  follow_up_count: number;
  last_follow_up?: string;
  next_follow_up?: string;
  content_removed: boolean;
  removal_verified_at?: string;
  partial_compliance: boolean;
  compliance_notes?: string;
  created_at: string;
  updated_at?: string;
}

// Dashboard types - Enhanced for real API integration
export interface DashboardStats {
  totalProfiles: number;
  activeScans: number;
  infringementsFound: number;
  takedownsSent: number;
  profilesChange: number;
  scansChange: number;
  infringementsChange: number;
  takedownsChange: number;
  lastUpdated: string;
}

export interface UsageMetrics {
  scansUsed: number;
  scansLimit: number;
  successRate: number;
  monthlySuccessRate: number;
  billingCycle: string;
  resetDate: string;
}

export interface RecentActivity {
  id: string;
  type: 'infringement' | 'takedown' | 'scan' | 'profile';
  title: string;
  description: string;
  platform: string;
  status: 'pending' | 'success' | 'failed' | 'in-progress';
  timestamp: string;
  url?: string;
  metadata?: Record<string, any>;
}

export interface PlatformData {
  platform: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  trend: 'up' | 'down' | 'stable';
  avgResponseTime: number;
}

export interface AnalyticsData {
  monthlyTrends: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor: string;
      tension: number;
      fill: boolean;
    }>;
  };
  platformDistribution: {
    labels: string[];
    datasets: Array<{
      data: number[];
      backgroundColor: string[];
      hoverBackgroundColor: string[];
    }>;
  };
  successRateByPlatform: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor: string;
      borderColor: string;
      borderWidth: number;
    }>;
  };
}

export interface DashboardPreferences {
  refreshInterval: number;
  defaultDateRange: 'week' | 'month' | 'quarter' | 'year';
  visibleWidgets: string[];
  chartColors: Record<string, string>;
  timezone: string;
  emailNotifications: boolean;
  realTimeUpdates: boolean;
}

export interface QuickActionsData {
  recentProfiles: Array<{
    id: number;
    name: string;
    status: string;
  }>;
  pendingReviews: number;
  urgentTakedowns: number;
  systemAlerts: number;
}

// Legacy dashboard types for backward compatibility
export interface LegacyDashboardStats {
  total_profiles: number;
  total_infringements: number;
  pending_takedowns: number;
  success_rate: number;
  monthly_scans: number;
  recent_infringements: Infringement[];
  platform_breakdown: Record<string, number>;
  monthly_trends: Array<{
    month: string;
    infringements: number;
    resolved: number;
  }>;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  code?: string;
}

// Submission types
export enum ContentType {
  IMAGES = 'images',
  VIDEOS = 'videos', 
  DOCUMENTS = 'documents',
  URLS = 'urls'
}

export enum PriorityLevel {
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent'
}

export enum SubmissionStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface Submission {
  id: string;
  user_id: number;
  profile_id?: number;
  type: ContentType;
  priority: PriorityLevel;
  status: SubmissionStatus;
  title: string;
  urls: string[];
  files?: string[]; // File URLs after upload
  tags: string[];
  category?: string;
  description?: string;
  progress_percentage: number;
  estimated_completion?: string;
  auto_monitoring: boolean;
  notify_on_infringement: boolean;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error_message?: string;
  total_urls: number;
  processed_urls: number;
  valid_urls: number;
  invalid_urls: number;
}

export interface CreateSubmission {
  title: string;
  type: ContentType;
  priority: PriorityLevel;
  urls?: string[];
  tags?: string[];
  category?: string;
  description?: string;
  auto_monitoring?: boolean;
  notify_on_infringement?: boolean;
  profile_id?: number;
}

export interface BulkSubmission {
  submissions: CreateSubmission[];
  apply_to_all?: {
    category?: string;
    tags?: string[];
    priority?: PriorityLevel;
    auto_monitoring?: boolean;
    notify_on_infringement?: boolean;
  };
}

export interface UrlValidationResult {
  url: string;
  is_valid: boolean;
  error_message?: string;
  domain: string;
  platform?: string;
  content_type?: string;
}

// Admin-specific types
export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin',
  MODERATOR = 'moderator'
}

export enum AdminActionType {
  USER_SUSPEND = 'user_suspend',
  USER_ACTIVATE = 'user_activate',
  USER_DELETE = 'user_delete',
  SUBSCRIPTION_MODIFY = 'subscription_modify',
  SYSTEM_CONFIG = 'system_config',
  PLATFORM_UPDATE = 'platform_update',
  MAINTENANCE_MODE = 'maintenance_mode',
  FEATURE_TOGGLE = 'feature_toggle'
}

export interface AdminUser extends User {
  role: UserRole;
  subscription?: Subscription;
  last_activity?: string;
  total_infringements: number;
  total_takedowns: number;
  account_value?: number;
  risk_score?: number;
  is_suspended: boolean;
  suspension_reason?: string;
  suspension_date?: string;
  total_logins: number;
  failed_login_attempts: number;
}

export interface SystemMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  last_updated: string;
  description?: string;
}

export interface AdminDashboardStats {
  total_users: number;
  active_users: number;
  new_users_today: number;
  total_revenue: number;
  monthly_revenue: number;
  system_health: 'healthy' | 'warning' | 'critical';
  active_subscriptions: number;
  total_infringements: number;
  total_takedowns: number;
  success_rate: number;
  platform_statistics: Record<string, {
    total_requests: number;
    success_rate: number;
    avg_response_time: number;
  }>;
  recent_activities: AdminActivity[];
  system_metrics: SystemMetric[];
}

export interface AdminActivity {
  id: number;
  admin_id: number;
  admin_name: string;
  action: AdminActionType;
  target_type: string;
  target_id: string;
  description: string;
  metadata?: Record<string, any>;
  ip_address: string;
  user_agent?: string;
  created_at: string;
}

export interface SystemConfig {
  id: string;
  category: string;
  key: string;
  value: string;
  data_type: 'string' | 'number' | 'boolean' | 'json';
  description?: string;
  is_sensitive: boolean;
  last_modified: string;
  modified_by: string;
}

export interface PlatformConfig {
  id: string;
  platform_name: string;
  is_active: boolean;
  api_endpoint?: string;
  rate_limit: number;
  success_rate: number;
  last_health_check: string;
  configuration: Record<string, any>;
  error_rate: number;
  avg_response_time: number;
}

export interface AdminNotification {
  id: number;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  is_read: boolean;
  requires_action: boolean;
  action_url?: string;
  metadata?: Record<string, any>;
  created_at: string;
  expires_at?: string;
}

export interface BulkUserOperation {
  operation: 'suspend' | 'activate' | 'delete' | 'export' | 'email';
  user_ids: number[];
  reason?: string;
  metadata?: Record<string, any>;
}

export interface UserAnalytics {
  user_growth: Array<{
    date: string;
    new_users: number;
    total_users: number;
  }>;
  subscription_breakdown: Record<string, number>;
  user_activity: Array<{
    date: string;
    active_users: number;
    new_logins: number;
  }>;
  churn_analysis: {
    monthly_churn_rate: number;
    reasons: Record<string, number>;
  };
}

export interface SystemHealthCheck {
  service: string;
  status: 'healthy' | 'degraded' | 'down';
  response_time: number;
  last_check: string;
  error_message?: string;
  uptime_percentage: number;
}

export interface AuditLog {
  id: number;
  user_id?: number;
  admin_id?: number;
  action: string;
  resource_type: string;
  resource_id: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  ip_address: string;
  user_agent?: string;
  session_id?: string;
  created_at: string;
}

// Search Engine Delisting types
export interface SearchEngine {
  id: string;
  name: string;
  domain: string;
  apiEndpoint?: string;
  isActive: boolean;
  supportsImageSearch: boolean;
  supportsCacheRemoval: boolean;
  supportsRegionalDelisting: boolean;
  avgResponseTime: number;
  successRate: number;
  icon: string;
  color: string;
}

export enum DelistingType {
  URL_REMOVAL = 'url_removal',
  CACHE_REMOVAL = 'cache_removal',
  IMAGE_SEARCH = 'image_search',
  KEYWORD_BLOCKING = 'keyword_blocking',
  SAFE_SEARCH = 'safe_search',
  SITEMAP_UPDATE = 'sitemap_update'
}

export enum DelistingStatus {
  DRAFT = 'draft',
  SUBMITTED = 'submitted',
  UNDER_REVIEW = 'under_review',
  APPROVED = 'approved',
  PARTIALLY_APPROVED = 'partially_approved',
  DENIED = 'denied',
  EXPIRED = 'expired',
  APPEALED = 'appealed'
}

export interface DelistingRequest {
  id: string;
  searchEngineId: string;
  searchEngine: string;
  type: DelistingType;
  status: DelistingStatus;
  priority: PriorityLevel;
  urls: string[];
  keywords?: string[];
  region?: string;
  reason: string;
  template: string;
  submittedAt: string;
  responseExpected?: string;
  responseReceived?: string;
  responseContent?: string;
  followUpCount: number;
  nextFollowUp?: string;
  successRate: number;
  estimatedImpact: number;
  metadata: {
    cacheRemoval?: boolean;
    imageSearch?: boolean;
    safetFiltering?: boolean;
    sitemapSubmission?: boolean;
  };
}

export interface URLMonitoring {
  id: string;
  url: string;
  keywords: string[];
  searchEngines: string[];
  lastCheck: string;
  position?: number;
  visibility: number;
  alerts: boolean;
  autoDelisting: boolean;
  status: 'active' | 'removed' | 'monitoring';
}

export interface SearchResult {
  url: string;
  title: string;
  snippet: string;
  position: number;
  searchEngine: string;
  region: string;
  lastSeen: string;
  isInfringing: boolean;
}

export interface VisibilityMetrics {
  searchEngine: string;
  totalUrls: number;
  visibleUrls: number;
  hiddenUrls: number;
  visibilityReduction: number;
  trend: 'improving' | 'stable' | 'declining';
}

// Additional Search Engine Delisting types
export interface SearchEngineDelistingDashboard {
  totalRequests: number;
  successRate: number;
  visibilityReduction: number;
  avgResponseTime: number;
  searchEngines: SearchEngine[];
  requestsByEngine: number[];
  responseTimeData: number[];
  visibilityTrends: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor: string;
      tension: number;
      fill: boolean;
    }>;
  };
  regionalData: RegionData[];
  visibilityMetrics: VisibilityMetrics[];
  recentActivity: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: string;
    status: string;
  }>;
}

export interface DelistingTemplate {
  id: string;
  name: string;
  type: DelistingType;
  searchEngine?: string;
  jurisdiction?: string;
  subject: string;
  content: string;
  variables: string[];
  isActive: boolean;
  successRate: number;
  usage: number;
  createdAt: string;
  updatedAt?: string;
}

export interface DelistingProgress {
  requestId: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
  details?: Record<string, any>;
}


export interface SearchEngineCapabilities {
  id: string;
  name: string;
  features: {
    urlRemoval: boolean;
    cacheRemoval: boolean;
    imageSearch: boolean;
    bulkOperations: boolean;
    realTimeStatus: boolean;
    webhooks: boolean;
  };
  rateLimits: {
    requestsPerHour: number;
    requestsPerDay: number;
    burstLimit: number;
  };
  regions: string[];
  apiVersion: string;
  lastUpdated: string;
}

export interface DelistingReport {
  id: string;
  type: 'summary' | 'detailed' | 'compliance' | 'performance';
  title: string;
  dateRange: { start: string; end: string };
  engines: string[];
  status: 'generating' | 'completed' | 'failed';
  downloadUrl?: string;
  createdAt: string;
  expiresAt?: string;
}

export interface URLValidationResponse {
  url: string;
  isValid: boolean;
  domain: string;
  platform?: string;
  indexed: boolean;
  lastCrawled?: string;
  errorMessage?: string;
  recommendations?: string[];
}

export interface IndexStatusCheck {
  url: string;
  searchEngine: string;
  isIndexed: boolean;
  position?: number;
  lastSeen?: string;
  cacheDate?: string;
  snippet?: string;
}

export interface RemovalImpactEstimate {
  url: string;
  estimatedViews: number;
  impactScore: number;
  difficulty: 'easy' | 'medium' | 'hard';
  timeEstimate: string;
  recommendations: string[];
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down' | 'critical';
  uptime?: number;
  activeConnections?: number;
  queueSize: number;
  errorRate: number;
  components: Array<{
    name: string;
    component?: string;
    status: 'up' | 'down' | 'degraded';
    lastCheck: string;
    last_check?: string;
    responseTime?: number;
    response_time?: number;
    error_message?: string;
  }>;
  performance?: {
    queue_size: number;
    processing_rate: number;
    error_rate: number;
    uptime_seconds: number;
  };
}

export interface RegionData {
  region: string;
  country: string;
  requestCount: number;
  successRate: number;
  avgResponseTime: number;
}

// Browser Extension types
export enum BrowserType {
  CHROME = 'chrome',
  FIREFOX = 'firefox',
  EDGE = 'edge',
  SAFARI = 'safari'
}

export enum ExtensionStatus {
  NOT_INSTALLED = 'not_installed',
  INSTALLED = 'installed',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  UPDATE_AVAILABLE = 'update_available',
  ERROR = 'error'
}

export enum ExtensionAction {
  CONTENT_REPORTED = 'content_reported',
  BULK_SELECTION = 'bulk_selection',
  CONTEXT_MENU_USED = 'context_menu_used',
  AUTO_DETECTION_TRIGGERED = 'auto_detection_triggered',
  FORM_AUTOFILL = 'form_autofill',
  QUICK_ACTION = 'quick_action'
}

export interface BrowserExtension {
  id: string;
  name: string;
  browser: BrowserType;
  version: string;
  latest_version?: string;
  status: ExtensionStatus;
  is_installed: boolean;
  is_active: boolean;
  last_sync?: string;
  download_url: string;
  store_url: string;
  icon: string;
  permissions: string[];
  features: string[];
  install_count: number;
  success_rate: number;
  created_at: string;
  updated_at?: string;
}

export interface ExtensionActivity {
  id: string;
  extension_id: string;
  user_id: number;
  action: ExtensionAction;
  url: string;
  domain: string;
  platform?: string;
  success: boolean;
  confidence_score?: number;
  details?: string;
  metadata?: Record<string, any>;
  timestamp: string;
  session_id?: string;
  ip_address?: string;
  user_agent?: string;
}

export interface ExtensionSettings {
  user_id: number;
  extension_id: string;
  auto_detection: boolean;
  context_menu: boolean;
  notifications: boolean;
  bulk_selection: boolean;
  auto_reporting: boolean;
  data_collection: boolean;
  sync_settings: boolean;
  quick_actions: boolean;
  detection_threshold: number;
  notification_frequency: string;
  sync_interval: number;
  excluded_domains?: string[];
  custom_keywords?: string[];
  created_at: string;
  updated_at?: string;
}

export interface ExtensionStats {
  total_installations: number;
  active_extensions: number;
  daily_active_users: number;
  total_activities: number;
  success_rate: number;
  top_actions: Array<{
    action: ExtensionAction;
    count: number;
    percentage: number;
  }>;
  browser_distribution: Record<BrowserType, number>;
  activity_trends: Array<{
    date: string;
    activities: number;
    success_rate: number;
  }>;
}

export interface ExtensionPermission {
  name: string;
  description: string;
  required: boolean;
  granted: boolean;
  risk_level: 'low' | 'medium' | 'high';
}

export interface ExtensionUpdate {
  extension_id: string;
  current_version: string;
  latest_version: string;
  update_available: boolean;
  changelog: string;
  release_date: string;
  critical: boolean;
  auto_update_enabled: boolean;
}

export interface BulkExtensionOperation {
  operation: 'install' | 'activate' | 'deactivate' | 'update' | 'uninstall';
  extension_ids: string[];
  settings?: Partial<ExtensionSettings>;
  schedule_time?: string;
}

// Reports & Analytics types
export interface ReportFilters {
  dateRange?: { start: string; end: string };
  platforms?: string[];
  contentTypes?: string[];
  reportType?: 'comprehensive' | 'executive' | 'platform' | 'roi' | 'compliance';
  timeGranularity?: 'hourly' | 'daily' | 'weekly' | 'monthly';
}

export interface OverviewMetrics {
  totalInfringements: number;
  totalTakedowns: number;
  successRate: number;
  avgResponseTime: number;
  timeSeriesData: TimeSeriesDataPoint[];
  lastUpdated: string;
}

export interface PlatformMetrics {
  platform: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  avgResponseTime: number;
  cost: number;
  roi: number;
  complianceRating: number;
  trend: 'up' | 'down' | 'stable';
}

export interface TimeSeriesDataPoint {
  date: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  visibilityReduction: number;
  responseTime?: number;
  cost?: number;
}

export interface GeographicDataPoint {
  country: string;
  region?: string;
  city?: string;
  infringements: number;
  takedowns: number;
  successRate: number;
  coordinates?: { lat: number; lng: number };
}

export interface ContentTypeMetrics {
  type: 'images' | 'videos' | 'audio' | 'text';
  count: number;
  percentage: number;
  successRate: number;
  avgDetectionTime?: number;
  avgRemovalTime?: number;
}

export interface ROIMetrics {
  totalInvestment: number;
  contentValueProtected: number;
  estimatedLossPrevented: number;
  roi: number;
  costPerTakedown: number;
  projectedROI?: number;
  breakEvenPoint?: string;
}

export interface ResponseTimeData {
  platform: string;
  avgHours: number;
  medianHours: number;
  category: 'fast' | 'medium' | 'slow';
  trend: 'improving' | 'stable' | 'declining';
  distribution: {
    under24h: number;
    under48h: number;
    under72h: number;
    over72h: number;
  };
}

export interface PlatformCompliance {
  platform: string;
  complianceScore: number;
  responseRate: number;
  avgResponseTime: number;
  cooperationLevel: 'excellent' | 'good' | 'fair' | 'poor';
  legalCompliance: boolean;
  automatedProcessing: boolean;
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  category: 'executive' | 'operational' | 'compliance' | 'financial';
  sections: string[];
  filters: ReportFilters;
  chartConfigurations?: Record<string, any>;
  customFields?: Record<string, any>;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ScheduledReport {
  id: string;
  name: string;
  reportType: 'comprehensive' | 'executive' | 'platform' | 'roi' | 'compliance';
  schedule: {
    frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
    time?: string;
    dayOfWeek?: number;
    dayOfMonth?: number;
    timezone?: string;
  };
  recipients: string[];
  filters: ReportFilters;
  format: 'pdf' | 'csv' | 'excel';
  template?: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  nextRun?: string;
  lastRun?: string;
  createdAt: string;
  updatedAt: string;
}

export interface GeneratedReport {
  id: string;
  type: string;
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  format: 'pdf' | 'csv' | 'excel' | 'html' | 'json';
  downloadUrl?: string;
  fileSize?: number;
  error?: string;
  generatedAt?: string;
  expiresAt?: string;
  createdBy: number;
  filters: ReportFilters;
}

export interface TrendAnalysis {
  metric: string;
  trend: 'increasing' | 'decreasing' | 'stable';
  changePercentage: number;
  confidence: number;
  projection?: {
    nextWeek: number;
    nextMonth: number;
    nextQuarter: number;
  };
  seasonality?: {
    detected: boolean;
    pattern?: 'weekly' | 'monthly' | 'quarterly';
    strength?: number;
  };
}

export interface PredictiveAnalytics {
  forecastPeriod: 'week' | 'month' | 'quarter';
  predictions: {
    metric: string;
    currentValue: number;
    predictedValue: number;
    confidence: number;
    scenarios?: {
      optimistic: number;
      realistic: number;
      pessimistic: number;
    };
  }[];
  recommendations: string[];
  dataQuality: {
    completeness: number;
    accuracy: number;
    consistency: number;
  };
}

export interface ComparativeAnalysis {
  basePeriod: { start: string; end: string };
  comparePeriod: { start: string; end: string };
  metrics: {
    name: string;
    baseValue: number;
    compareValue: number;
    change: number;
    changePercent: number;
    significance: 'high' | 'medium' | 'low';
  }[];
  summary: {
    overallTrend: 'positive' | 'negative' | 'neutral';
    keyInsights: string[];
    recommendations: string[];
  };
}

export interface PerformanceMetrics {
  efficiency: {
    detectionAccuracy: number;
    falsePositiveRate: number;
    processingTime: number;
    automationRate: number;
  };
  effectiveness: {
    removalSuccessRate: number;
    avgRemovalTime: number;
    reappearanceRate: number;
    contentProtectionScore: number;
  };
  benchmarks: {
    industryAverage: Record<string, number>;
    topPerformer: Record<string, number>;
    yourRanking: Record<string, number>;
  };
}

export interface CostAnalysis {
  totalCosts: number;
  breakdown: {
    platform: Record<string, number>;
    contentType: Record<string, number>;
    timeUnit: Record<string, number>;
  };
  trends: {
    monthly: { month: string; cost: number; efficiency: number }[];
  };
  optimization: {
    potentialSavings: number;
    recommendations: string[];
    inefficiencies: string[];
  };
}

export interface RealTimeMetrics {
  timestamp: string;
  activeScans: number;
  pendingTakedowns: number;
  recentDetections: number;
  systemLoad: {
    cpu: number;
    memory: number;
    storage: number;
  };
  platformStatus: {
    platform: string;
    status: 'online' | 'offline' | 'degraded';
    responseTime: number;
    errorRate: number;
  }[];
}

export interface DataQualityReport {
  overall: {
    score: number;
    grade: 'A' | 'B' | 'C' | 'D' | 'F';
  };
  dimensions: {
    completeness: {
      score: number;
      missingFields: string[];
      affectedRecords: number;
    };
    accuracy: {
      score: number;
      inconsistencies: string[];
      validationErrors: number;
    };
    timeliness: {
      score: number;
      staleness: string;
      delayedUpdates: number;
    };
    consistency: {
      score: number;
      duplicates: number;
      conflicts: string[];
    };
  };
  recommendations: {
    priority: 'high' | 'medium' | 'low';
    action: string;
    impact: string;
    effort: 'low' | 'medium' | 'high';
  }[];
  dataFreshness: {
    lastUpdate: string;
    updateFrequency: string;
    expectedNextUpdate: string;
  };
}

export interface CustomMetric {
  id: string;
  name: string;
  description: string;
  formula: string;
  dependencies: string[];
  category: string;
  unit?: string;
  currentValue?: number;
  trend?: 'up' | 'down' | 'stable';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description?: string;
  metric: string;
  condition: 'above' | 'below' | 'equal' | 'not_equal';
  threshold: number;
  platform?: string;
  recipients: string[];
  channels: ('email' | 'sms' | 'webhook' | 'dashboard')[];
  frequency: 'immediate' | 'hourly' | 'daily';
  active: boolean;
  triggeredCount: number;
  lastTriggered?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ReportShare {
  id: string;
  reportId: string;
  sharedWith: string[];
  permissions: 'view' | 'download';
  message?: string;
  expiresAt?: string;
  accessCount: number;
  createdAt: string;
  isActive: boolean;
}

// Enhanced Analytics Response Types
export interface AnalyticsApiResponse {
  overview: OverviewMetrics;
  platformBreakdown: PlatformMetrics[];
  contentAnalytics: ContentTypeMetrics[];
  geographicData: GeographicDataPoint[];
  complianceMetrics: PlatformCompliance[];
  roiAnalysis: ROIMetrics;
  responseTimeAnalysis: ResponseTimeData[];
  trendAnalysis?: TrendAnalysis[];
  performanceMetrics?: PerformanceMetrics;
  dataQuality: DataQualityReport;
}

export interface ChartConfiguration {
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'area' | 'scatter';
  title: string;
  data: any;
  options: any;
  customization?: {
    colors?: string[];
    responsive?: boolean;
    maintainAspectRatio?: boolean;
    plugins?: Record<string, any>;
    scales?: Record<string, any>;
  };
}

export interface ReportSection {
  id: string;
  title: string;
  type: 'chart' | 'table' | 'kpi' | 'text' | 'image';
  content: any;
  configuration?: Record<string, any>;
  order: number;
  visible: boolean;
}

// WebSocket types for real-time updates
export interface WebSocketMessage {
  type: 'metric_update' | 'alert' | 'status_change' | 'error';
  payload: any;
  timestamp: string;
}

export interface RealTimeSubscription {
  id: string;
  metrics: string[];
  platforms?: string[];
  updateFrequency: 'high' | 'medium' | 'low';
  isActive: boolean;
  createdAt: string;
}

// AI Content Matching types
export enum AIModelType {
  FACE_RECOGNITION = 'face_recognition',
  IMAGE_MATCHING = 'image_matching',
  VIDEO_ANALYSIS = 'video_analysis',
  TEXT_DETECTION = 'text_detection',
  AUDIO_FINGERPRINT = 'audio_fingerprint'
}

export enum AIModelStatus {
  TRAINING = 'training',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  UPDATING = 'updating'
}

export enum TrainingDataType {
  REFERENCE = 'reference',
  POSITIVE = 'positive',
  NEGATIVE = 'negative'
}

export enum TrainingDataStatus {
  PROCESSING = 'processing',
  VALIDATED = 'validated',
  REJECTED = 'rejected',
  TRAINING = 'training'
}

export enum TrainingJobStatus {
  QUEUED = 'queued',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum DetectionMatchType {
  EXACT = 'exact',
  SIMILAR = 'similar',
  PARTIAL = 'partial'
}

export interface AIModel {
  id: string;
  name: string;
  type: AIModelType;
  version: string;
  status: AIModelStatus;
  accuracy: number;
  confidence_threshold: number;
  training_data_count: number;
  last_trained?: string;
  created_at: string;
  updated_at?: string;
  performance_metrics: {
    precision: number;
    recall: number;
    f1_score: number;
    false_positive_rate: number;
    processing_speed: number; // items per second
  };
  description?: string;
  is_default?: boolean;
}

export interface CreateAIModel {
  name: string;
  type: AIModelType;
  description?: string;
  confidence_threshold?: number;
  configuration?: Record<string, any>;
}

export interface TrainingData {
  id: string;
  model_id: string;
  name: string;
  type: TrainingDataType;
  file_path: string;
  file_size: number;
  upload_date: string;
  status: TrainingDataStatus;
  validation_score?: number;
  metadata: {
    width?: number;
    height?: number;
    duration?: number; // for videos/audio
    faces_detected?: number;
    quality_score?: number;
    file_format?: string;
  };
  error_message?: string;
}

export interface ModelTraining {
  id: string;
  model_id: string;
  status: TrainingJobStatus;
  progress: number;
  started_at: string;
  estimated_completion?: string;
  completed_at?: string;
  training_metrics: {
    epochs_completed: number;
    total_epochs: number;
    current_loss: number;
    best_accuracy: number;
    learning_rate: number;
    batch_size?: number;
  };
  error_message?: string;
  training_config?: Record<string, any>;
}

export interface DetectionResult {
  id: string;
  model_id: string;
  content_url: string;
  content_type: string;
  confidence_score: number;
  match_type: DetectionMatchType;
  detected_at: string;
  is_verified: boolean;
  reviewer_feedback?: 'correct' | 'incorrect';
  reviewer_notes?: string;
  bounding_boxes?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
    label?: string;
  }>;
  metadata?: {
    processing_time?: number;
    reference_image?: string;
    similarity_score?: number;
  };
}

export interface ContentFingerprint {
  id: string;
  content_hash: string;
  perceptual_hash: string;
  content_type: 'image' | 'video' | 'audio';
  source_url?: string;
  file_path?: string;
  created_at: string;
  model_version: string;
  metadata: {
    file_size: number;
    dimensions?: string;
    duration?: number;
    bitrate?: number;
    file_format?: string;
  };
}

export interface AIGlobalSettings {
  auto_training: boolean;
  batch_processing: boolean;
  real_time_detection: boolean;
  notification_threshold: number;
  max_concurrent_trainings: number;
  data_retention_days: number;
  processing_settings: {
    max_file_size: number;
    supported_formats: string[];
    timeout_seconds: number;
    queue_priority: 'fifo' | 'priority' | 'round_robin';
  };
  performance_settings: {
    gpu_acceleration: boolean;
    batch_size: number;
    model_cache_size: number;
    parallel_processing: boolean;
  };
}

export interface ModelPerformanceMetrics {
  model_id: string;
  model_name: string;
  time_period: {
    start: string;
    end: string;
  };
  metrics: {
    total_predictions: number;
    correct_predictions: number;
    false_positives: number;
    false_negatives: number;
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    auc_roc?: number;
    processing_speed: number;
    avg_confidence: number;
  };
  performance_trends: Array<{
    date: string;
    accuracy: number;
    processing_speed: number;
    predictions_count: number;
  }>;
}

export interface BatchJob {
  id: string;
  name: string;
  type: 'training' | 'detection' | 'fingerprinting';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total_items: number;
  processed_items: number;
  failed_items: number;
  started_at?: string;
  completed_at?: string;
  estimated_completion?: string;
  config: Record<string, any>;
  results?: {
    success_count: number;
    failure_count: number;
    output_urls?: string[];
  };
  error_message?: string;
}

export interface RealTimeDetectionConfig {
  models: string[];
  confidence_threshold: number;
  notification_webhooks: string[];
  processing_options: {
    batch_size: number;
    max_queue_size: number;
    timeout_ms: number;
  };
  filters?: {
    content_types?: string[];
    min_file_size?: number;
    max_file_size?: number;
  };
}

export interface RealTimeDetectionStatus {
  is_active: boolean;
  queue_size: number;
  processed_count: number;
  error_count: number;
  uptime: number;
  models_active: string[];
  last_activity?: string;
  performance_stats: {
    avg_processing_time: number;
    throughput_per_minute: number;
    error_rate: number;
  };
}

export interface ModelAnalytics {
  model_id: string;
  time_period: {
    start: string;
    end: string;
  };
  usage_stats: {
    total_requests: number;
    successful_detections: number;
    failed_requests: number;
    avg_response_time: number;
  };
  accuracy_metrics: {
    current_accuracy: number;
    accuracy_trend: 'improving' | 'declining' | 'stable';
    confidence_distribution: Record<string, number>;
    false_positive_rate: number;
    false_negative_rate: number;
  };
  resource_usage: {
    cpu_time: number;
    memory_peak: number;
    storage_used: number;
    gpu_utilization?: number;
  };
  training_history: Array<{
    date: string;
    accuracy: number;
    loss: number;
    epoch: number;
  }>;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version: string;
  created_at: string;
  is_active: boolean;
  performance_metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
  };
  training_info: {
    dataset_size: number;
    epochs: number;
    training_time: number;
  };
  changelog?: string;
  file_size: number;
}

export interface ModelExportConfig {
  format: 'onnx' | 'tensorflow' | 'pytorch' | 'custom';
  include_metadata: boolean;
  compression: 'none' | 'gzip' | 'brotli';
  optimization: 'none' | 'speed' | 'size';
}

export interface ModelImportResult {
  model_id: string;
  success: boolean;
  warnings: string[];
  errors: string[];
  performance_comparison?: {
    old_accuracy?: number;
    new_accuracy: number;
    improvement: number;
  };
}

export interface SystemHealthStatus {
  overall_status: 'healthy' | 'degraded' | 'critical';
  components: {
    component: string;
    status: 'healthy' | 'degraded' | 'down';
    last_check: string;
    response_time?: number;
    error_message?: string;
  }[];
  resource_usage: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
    gpu_percent?: number;
  };
  active_models: number;
  queue_sizes: {
    training: number;
    detection: number;
    processing: number;
  };
}

// Social Media Protection types
export enum SocialMediaPlatformType {
  INSTAGRAM = 'instagram',
  FACEBOOK = 'facebook',
  TWITTER = 'twitter',
  TIKTOK = 'tiktok',
  ONLYFANS = 'onlyfans',
  TELEGRAM = 'telegram',
  DISCORD = 'discord',
  LINKEDIN = 'linkedin',
  SNAPCHAT = 'snapchat',
  REDDIT = 'reddit'
}

export enum ScanStatus {
  IDLE = 'idle',
  SCANNING = 'scanning',
  COMPLETED = 'completed',
  ERROR = 'error',
  PAUSED = 'paused'
}

export enum APIStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  LIMITED = 'limited',
  ERROR = 'error'
}

export enum IncidentSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum IncidentStatus {
  DETECTED = 'detected',
  REPORTED = 'reported',
  UNDER_REVIEW = 'under_review',
  RESOLVED = 'resolved',
  ESCALATED = 'escalated',
  FALSE_POSITIVE = 'false_positive'
}

export enum ReportedBy {
  AI = 'ai',
  USER = 'user',
  MANUAL = 'manual',
  AUTOMATION = 'automation'
}

export enum AutomationTrigger {
  SIMILARITY_THRESHOLD = 'similarity_threshold',
  KEYWORD_MATCH = 'keyword_match',
  IMAGE_MATCH = 'image_match',
  VIDEO_MATCH = 'video_match',
  PROFILE_MATCH = 'profile_match'
}

export enum AutomationAction {
  REPORT = 'report',
  ESCALATE = 'escalate',
  NOTIFY = 'notify',
  AUTO_TAKEDOWN = 'auto_takedown'
}

export interface SocialMediaPlatform {
  id: string;
  name: string;
  type: SocialMediaPlatformType;
  icon: string;
  color: string;
  is_connected: boolean;
  last_scan?: string;
  total_profiles: number;
  impersonations: number;
  scan_status: ScanStatus;
  api_status: APIStatus;
  features: string[];
  rate_limit?: {
    requests_per_hour: number;
    remaining: number;
    reset_time?: string;
  };
  credentials?: {
    api_key?: string;
    access_token?: string;
    expires_at?: string;
  };
  configuration?: {
    auto_scan: boolean;
    scan_frequency_hours: number;
    confidence_threshold: number;
    notification_enabled: boolean;
  };
  created_at: string;
  updated_at?: string;
}

export interface ImpersonationIncident {
  id: string;
  platform_id: string;
  platform: string;
  profile_url: string;
  profile_name: string;
  profile_description?: string;
  detected_at: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  confidence_score: number;
  evidence_urls: string[];
  reported_by: ReportedBy;
  similarity_score: number;
  estimated_followers: number;
  risk_level: number;
  notes?: string;
  metadata?: {
    profile_creation_date?: string;
    last_activity?: string;
    verification_status?: string;
    follower_growth_rate?: number;
    engagement_rate?: number;
    suspicious_patterns?: string[];
  };
  created_at: string;
  updated_at?: string;
}

export interface CreateIncidentReport {
  platform_id: string;
  profile_url: string;
  description: string;
  severity: IncidentSeverity;
  contact_attempted: boolean;
  additional_info?: string;
}

export interface CaseProgression {
  id: string;
  incident_id: string;
  status: string;
  timestamp: string;
  action: string;
  actor: string;
  notes?: string;
  attachments?: string[];
  metadata?: Record<string, any>;
}

export interface AutomationRule {
  id: string;
  name: string;
  description?: string;
  platform: string; // 'all' for all platforms
  trigger: AutomationTrigger;
  threshold: number;
  action: AutomationAction;
  is_active: boolean;
  conditions?: {
    min_confidence?: number;
    max_confidence?: number;
    keywords?: string[];
    exclude_keywords?: string[];
    min_followers?: number;
    max_followers?: number;
  };
  notification_settings?: {
    email: boolean;
    webhook: boolean;
    dashboard: boolean;
    webhook_url?: string;
  };
  created_at: string;
  updated_at?: string;
  last_triggered?: string;
  trigger_count: number;
}

export interface CreateAutomationRule {
  name: string;
  description?: string;
  platform: string;
  trigger: AutomationTrigger;
  threshold: number;
  action: AutomationAction;
  conditions?: {
    min_confidence?: number;
    max_confidence?: number;
    keywords?: string[];
    exclude_keywords?: string[];
    min_followers?: number;
    max_followers?: number;
  };
  notification_settings?: {
    email: boolean;
    webhook: boolean;
    dashboard: boolean;
    webhook_url?: string;
  };
}

export interface IdentityVerification {
  id: string;
  user_id: number;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  documents: {
    id: string;
    filename: string;
    type: 'government_id' | 'proof_of_ownership' | 'business_license' | 'other';
    url: string;
  }[];
  submitted_at: string;
  reviewed_at?: string;
  expires_at?: string;
  reviewer_notes?: string;
  verification_score?: number;
}

export interface MonitoringStats {
  total_platforms: number;
  connected_platforms: number;
  active_scans: number;
  total_incidents: number;
  resolved_incidents: number;
  pending_incidents: number;
  success_rate: number;
  avg_detection_time: number;
  avg_resolution_time: number;
  incident_trends: {
    date: string;
    detected: number;
    resolved: number;
    false_positives: number;
  }[];
  platform_breakdown: {
    platform: string;
    incidents: number;
    success_rate: number;
    avg_response_time: number;
  }[];
  severity_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  automation_metrics: {
    rules_active: number;
    automated_actions: number;
    manual_interventions: number;
    automation_success_rate: number;
  };
  last_updated: string;
}

export interface PlatformAnalytics {
  platform_id: string;
  platform_name: string;
  time_period: {
    start: string;
    end: string;
  };
  metrics: {
    total_scans: number;
    profiles_monitored: number;
    incidents_detected: number;
    false_positives: number;
    true_positives: number;
    accuracy_rate: number;
    avg_confidence_score: number;
  };
  performance: {
    scan_frequency: number;
    avg_scan_duration: number;
    api_uptime: number;
    error_rate: number;
    rate_limit_hits: number;
  };
  incident_breakdown: {
    severity: IncidentSeverity;
    count: number;
    percentage: number;
    avg_resolution_time: number;
  }[];
  trends: {
    date: string;
    scans: number;
    detections: number;
    accuracy: number;
  }[];
}

export interface RealTimeMonitoringStatus {
  is_enabled: boolean;
  active_platforms: string[];
  scan_queue_size: number;
  processing_rate: number;
  last_activity: string;
  uptime: number;
  errors_last_hour: number;
  notifications_sent: number;
  resource_usage: {
    cpu_percent: number;
    memory_percent: number;
    active_threads: number;
  };
}

export interface RealTimeMetrics {
  timestamp: string;
  active_monitors: number;
  incidents_detected_today: number;
  scans_in_progress: number;
  platform_health: {
    platform: string;
    status: 'healthy' | 'degraded' | 'offline';
    response_time: number;
    error_rate: number;
  }[];
  recent_detections: {
    id: string;
    platform: string;
    severity: IncidentSeverity;
    confidence: number;
    timestamp: string;
  }[];
}

export interface NotificationSettings {
  email_notifications: {
    incident_detected: boolean;
    incident_resolved: boolean;
    platform_disconnected: boolean;
    scan_completed: boolean;
    automation_triggered: boolean;
  };
  push_notifications: {
    high_priority_incidents: boolean;
    platform_alerts: boolean;
    daily_summaries: boolean;
  };
  webhook_notifications: {
    enabled: boolean;
    url?: string;
    events: string[];
    secret?: string;
  };
  notification_frequency: 'immediate' | 'hourly' | 'daily';
  quiet_hours: {
    enabled: boolean;
    start_time?: string;
    end_time?: string;
    timezone?: string;
  };
}

export interface SocialMediaDashboardData {
  stats: MonitoringStats;
  recent_incidents: ImpersonationIncident[];
  platform_status: SocialMediaPlatform[];
  active_scans: {
    platform: string;
    progress: number;
    estimated_completion: string;
  }[];
  alerts: {
    id: string;
    type: 'warning' | 'error' | 'info';
    message: string;
    timestamp: string;
    platform?: string;
  }[];
  automation_summary: {
    active_rules: number;
    actions_today: number;
    success_rate: number;
  };
}

// Bulk operation types
export interface BulkIncidentAction {
  action: 'report' | 'resolve' | 'escalate' | 'delete' | 'change_severity';
  incident_ids: string[];
  data?: {
    severity?: IncidentSeverity;
    notes?: string;
    notify_platforms?: boolean;
  };
}

export interface BulkScanRequest {
  platform_ids: string[];
  scan_config?: {
    deep_scan: boolean;
    confidence_threshold: number;
    include_historical: boolean;
  };
  priority: 'low' | 'normal' | 'high';
  notify_on_completion: boolean;
}

// WebSocket message types for real-time updates
export interface SocialMediaWebSocketMessage {
  type: 'incident_detected' | 'scan_status_update' | 'platform_status_change' | 'automation_triggered';
  payload: {
    incident?: ImpersonationIncident;
    platform?: {
      id: string;
      status: ScanStatus | APIStatus;
      progress?: number;
    };
    automation?: {
      rule_id: string;
      rule_name: string;
      action: AutomationAction;
      incident_id?: string;
    };
  };
  timestamp: string;
}

export interface RealTimeSubscription {
  id: string;
  types: ('incident' | 'scan_status' | 'platform_status' | 'automation')[];
  platforms?: string[];
  is_active: boolean;
  created_at: string;
}

// Report and export types
export interface SocialMediaReport {
  id: string;
  type: 'summary' | 'detailed' | 'platform_specific';
  title: string;
  date_range: {
    start: string;
    end: string;
  };
  platforms: string[];
  status: 'generating' | 'completed' | 'failed';
  file_url?: string;
  file_size?: number;
  format: 'pdf' | 'html' | 'csv' | 'xlsx';
  created_at: string;
  expires_at?: string;
}

export interface ExportRequest {
  format: 'csv' | 'xlsx' | 'pdf';
  data_type: 'incidents' | 'platforms' | 'analytics';
  filters?: {
    date_range?: { start: string; end: string };
    platforms?: string[];
    statuses?: string[];
    severity?: IncidentSeverity[];
  };
}

// DMCA Templates API Response Types
export interface DMCATemplateApiResponse extends IDMCATemplate {
  created_by?: {
    id: string;
    name: string;
    email: string;
  };
  last_modified_by?: {
    id: string;
    name: string;
    email: string;
  };
  approval_history?: TemplateApprovalEntry[];
  sharing_info?: TemplateSharing[];
}

export interface TemplateApprovalEntry {
  id: string;
  action: 'submitted' | 'approved' | 'rejected';
  approved_by?: {
    id: string;
    name: string;
    role: string;
  };
  notes?: string;
  conditions?: string[];
  timestamp: string;
}

export interface TemplateSharing {
  id: string;
  shared_with: {
    id: string;
    name: string;
    email: string;
  };
  permissions: ('view' | 'edit' | 'approve')[];
  shared_at: string;
  expires_at?: string;
  is_active: boolean;
}

export interface TemplateValidationResponse {
  is_valid: boolean;
  compliance_score: number;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  required_elements: DMCAComplianceElement[];
  recommendations: string[];
  jurisdiction_compliance?: JurisdictionCompliance;
  platform_compatibility?: PlatformCompatibility[];
}

export interface ValidationError {
  code: string;
  message: string;
  field?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  suggestion?: string;
}

export interface ValidationWarning {
  code: string;
  message: string;
  field?: string;
  suggestion?: string;
  impact?: string;
}

export interface DMCAComplianceElement {
  element: string;
  required: boolean;
  present: boolean;
  description: string;
  legal_reference: string;
  location?: {
    line: number;
    column: number;
    length: number;
  };
}

export interface JurisdictionCompliance {
  jurisdiction: string;
  compliant: boolean;
  specific_requirements: {
    requirement: string;
    met: boolean;
    description: string;
    reference?: string;
  }[];
  additional_clauses?: string[];
}

export interface PlatformCompatibility {
  platform: string;
  compatible: boolean;
  requirements: {
    requirement: string;
    met: boolean;
    description: string;
  }[];
  limitations?: string[];
  modifications_suggested?: string[];
}

export interface TemplatePreviewResponse {
  preview_html: string;
  preview_text: string;
  preview_pdf_url?: string;
  variables_used: string[];
  estimated_effectiveness: number;
  compliance_warnings?: string[];
}

export interface TemplateUsageStatsResponse {
  template_id: string;
  time_period: {
    start: string;
    end: string;
  };
  usage_metrics: {
    total_usage: number;
    successful_notices: number;
    failed_notices: number;
    success_rate: number;
    avg_response_time_hours: number;
  };
  platform_breakdown: {
    platform: string;
    usage_count: number;
    success_rate: number;
    avg_response_time: number;
  }[];
  geographic_distribution: {
    jurisdiction: string;
    usage_count: number;
    success_rate: number;
  }[];
  trend_data: {
    date: string;
    usage_count: number;
    success_rate: number;
  }[];
  effectiveness_score: number;
  recommendations?: string[];
}

export interface TemplateAnalyticsResponse {
  overview: {
    total_templates: number;
    active_templates: number;
    total_usage: number;
    avg_success_rate: number;
    most_used_category: string;
  };
  category_breakdown: {
    category: string;
    template_count: number;
    usage_count: number;
    success_rate: number;
    trend: 'increasing' | 'decreasing' | 'stable';
  }[];
  platform_performance: {
    platform: string;
    templates_count: number;
    avg_success_rate: number;
    usage_volume: number;
  }[];
  jurisdiction_analysis: {
    jurisdiction: string;
    compliance_rate: number;
    template_count: number;
    usage_count: number;
  }[];
  effectiveness_trends: {
    date: string;
    avg_effectiveness: number;
    total_usage: number;
    success_rate: number;
  }[];
  top_performing: IDMCATemplate[];
  recommendations: {
    type: 'optimization' | 'compliance' | 'coverage';
    priority: 'high' | 'medium' | 'low';
    message: string;
    action?: string;
  }[];
}

export interface LegalNoticeResponse {
  id: string;
  template_id: string;
  status: 'draft' | 'sent' | 'delivered' | 'acknowledged' | 'complied' | 'failed';
  recipient: {
    name: string;
    email: string;
    platform?: string;
    contact_method: string;
  };
  infringement_details: {
    url: string;
    description: string;
    evidence_urls: string[];
    discovery_date: string;
  };
  copyright_holder: {
    name: string;
    email: string;
    contact_info: Record<string, any>;
  };
  generated_content: {
    subject: string;
    body_html: string;
    body_text: string;
    attachments?: string[];
  };
  delivery_info?: {
    method: 'email' | 'platform_form' | 'certified_mail';
    sent_at: string;
    delivered_at?: string;
    tracking_info?: Record<string, any>;
  };
  response_info?: {
    received_at: string;
    response_type: 'compliance' | 'counter_notice' | 'refusal' | 'acknowledgment';
    content?: string;
    action_taken?: string;
  };
  follow_up?: {
    scheduled_at?: string;
    count: number;
    last_attempt?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface TemplateLibraryResponse {
  templates: TemplateLibraryItem[];
  categories: {
    name: string;
    count: number;
    description: string;
  }[];
  tags: {
    name: string;
    count: number;
  }[];
  difficulty_levels: {
    level: 'beginner' | 'intermediate' | 'advanced';
    count: number;
    description: string;
  }[];
  total_count: number;
  featured_templates: string[];
}

export interface TemplateLibraryItem {
  id: string;
  name: string;
  description: string;
  category: TemplateCategoryType;
  tags: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  platforms: string[];
  jurisdictions: string[];
  usage_count: number;
  success_rate: number;
  rating: number;
  last_updated: string;
  author: {
    name: string;
    organization?: string;
    verified: boolean;
  };
  preview_url?: string;
  license?: string;
}

export interface TemplateVersionResponse {
  id: string;
  template_id: string;
  version: string;
  title: string;
  content_diff?: {
    additions: string[];
    deletions: string[];
    modifications: string[];
  };
  created_by: {
    id: string;
    name: string;
  };
  created_at: string;
  notes?: string;
  is_major: boolean;
  is_current: boolean;
  compliance_score?: number;
  change_summary: string;
}

export interface TemplateAuditResponse {
  entries: TemplateAuditEntryResponse[];
  total_count: number;
  filters_applied: {
    action_type?: string;
    user_id?: string;
    date_range?: { start: string; end: string };
  };
  summary: {
    total_actions: number;
    unique_users: number;
    most_common_action: string;
    activity_trend: 'increasing' | 'decreasing' | 'stable';
  };
}

export interface TemplateAuditEntryResponse {
  id: string;
  template_id: string;
  action: 'created' | 'updated' | 'deleted' | 'approved' | 'rejected' | 'used' | 'shared';
  user: {
    id: string;
    name: string;
    email: string;
    role?: string;
  };
  timestamp: string;
  description: string;
  changes?: {
    field: string;
    old_value?: any;
    new_value?: any;
  }[];
  metadata?: {
    ip_address?: string;
    user_agent?: string;
    location?: string;
    session_id?: string;
  };
  impact_assessment?: {
    affected_notices: number;
    compliance_impact: 'positive' | 'negative' | 'neutral';
    risk_level: 'low' | 'medium' | 'high';
  };
}

export interface TemplateBulkActionResponse {
  operation_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  results: {
    template_id: string;
    status: 'success' | 'failed';
    message?: string;
    updated_data?: Partial<IDMCATemplate>;
  }[];
  started_at: string;
  completed_at?: string;
  estimated_completion?: string;
  errors?: {
    template_id: string;
    error_code: string;
    message: string;
  }[];
}

export interface TemplateImportResponse {
  import_id: string;
  status: 'processing' | 'completed' | 'failed';
  total_templates: number;
  imported_count: number;
  failed_count: number;
  skipped_count: number;
  results: {
    line_number?: number;
    template_title?: string;
    status: 'imported' | 'failed' | 'skipped';
    template_id?: string;
    message?: string;
  }[];
  validation_errors?: {
    line_number: number;
    field: string;
    message: string;
    severity: 'error' | 'warning';
  }[];
  warnings?: string[];
  started_at: string;
  completed_at?: string;
}

export interface TemplateDashboardStatsResponse {
  summary: {
    total_templates: number;
    active_templates: number;
    pending_approval: number;
    total_usage: number;
    avg_success_rate: number;
    compliance_rate: number;
  };
  recent_activity: {
    id: string;
    type: 'created' | 'updated' | 'used' | 'approved';
    template_name: string;
    user_name: string;
    timestamp: string;
    details?: string;
  }[];
  category_distribution: {
    category: string;
    count: number;
    percentage: number;
  }[];
  platform_usage: {
    platform: string;
    usage_count: number;
    success_rate: number;
    trend: 'up' | 'down' | 'stable';
  }[];
  compliance_overview: {
    compliant: number;
    needs_review: number;
    non_compliant: number;
    pending: number;
  };
  effectiveness_metrics: {
    date: string;
    avg_effectiveness: number;
    template_usage: number;
    success_rate: number;
  }[];
  alerts: {
    id: string;
    type: 'compliance' | 'performance' | 'usage' | 'approval';
    severity: 'info' | 'warning' | 'critical';
    message: string;
    template_id?: string;
    action_required?: boolean;
    timestamp: string;
  }[];
}

export interface TemplateSearchResponse {
  templates: IDMCATemplate[];
  total_results: number;
  facets: {
    categories: { name: string; count: number }[];
    platforms: { name: string; count: number }[];
    jurisdictions: { name: string; count: number }[];
    statuses: { name: string; count: number }[];
  };
  suggestions?: string[];
  search_metadata: {
    query: string;
    execution_time_ms: number;
    filters_applied: Record<string, any>;
  };
}

export interface TemplateEffectivenessResponse {
  template_id: string;
  overall_score: number;
  metrics: {
    success_rate: number;
    avg_response_time: number;
    compliance_rate: number;
    platform_compatibility: number;
    user_satisfaction: number;
  };
  benchmarks: {
    category_average: number;
    platform_average: Record<string, number>;
    jurisdiction_average: Record<string, number>;
  };
  improvement_areas: {
    area: string;
    current_score: number;
    target_score: number;
    recommendations: string[];
  }[];
  performance_trends: {
    date: string;
    effectiveness_score: number;
    usage_volume: number;
  }[];
  comparison_data?: {
    compared_against: string[];
    relative_performance: {
      template_id: string;
      name: string;
      score_difference: number;
      better_in: string[];
      worse_in: string[];
    }[];
  };
}

export interface TemplateTestResponse {
  test_id: string;
  template_id: string;
  test_type: 'compliance' | 'delivery' | 'response' | 'all';
  status: 'running' | 'completed' | 'failed';
  results: {
    compliance_test?: {
      passed: boolean;
      score: number;
      issues: ValidationError[];
      recommendations: string[];
    };
    delivery_test?: {
      passed: boolean;
      platforms_tested: string[];
      delivery_success_rate: number;
      failed_platforms: string[];
      avg_delivery_time: number;
    };
    response_test?: {
      passed: boolean;
      expected_responses: number;
      actual_responses: number;
      response_quality: number;
      response_time: number;
    };
  };
  started_at: string;
  completed_at?: string;
  test_parameters: Record<string, any>;
  environment: 'production' | 'staging' | 'development';
}

export interface PlatformConfigResponse {
  platform: string;
  display_name: string;
  is_active: boolean;
  configuration: {
    api_endpoint?: string;
    form_endpoint?: string;
    required_fields: string[];
    optional_fields: string[];
    max_content_length: number;
    supported_formats: ('html' | 'text' | 'markdown')[];
    rate_limits: {
      requests_per_hour: number;
      requests_per_day: number;
    };
    authentication?: {
      type: 'api_key' | 'oauth' | 'none';
      required_fields: string[];
    };
  };
  templates: {
    template_id: string;
    title: string;
    success_rate: number;
    last_used: string;
  }[];
  statistics: {
    total_submissions: number;
    success_rate: number;
    avg_response_time: number;
    last_successful_submission: string;
  };
  validation_rules: {
    rule_id: string;
    description: string;
    validation_regex?: string;
    is_required: boolean;
  }[];
  last_updated: string;
}

export interface JurisdictionConfigResponse {
  jurisdiction: string;
  display_name: string;
  legal_framework: {
    primary_law: string;
    relevant_sections: string[];
    last_updated: string;
  };
  requirements: {
    category: string;
    requirements: {
      requirement: string;
      description: string;
      is_mandatory: boolean;
      reference?: string;
      example?: string;
    }[];
  }[];
  language_requirements: {
    primary_language: string;
    accepted_languages: string[];
    translation_required: boolean;
  };
  specific_clauses: {
    clause_type: string;
    content: string;
    placement: 'header' | 'body' | 'footer';
    is_required: boolean;
  }[];
  templates: {
    template_id: string;
    title: string;
    compliance_score: number;
    last_validated: string;
  }[];
  compliance_statistics: {
    total_templates: number;
    compliant_templates: number;
    pending_review: number;
    non_compliant: number;
    compliance_rate: number;
  };
}

// Real-time subscription types
export interface TemplateRealtimeSubscription {
  subscription_id: string;
  user_id: string;
  template_ids?: string[];
  categories?: string[];
  update_types: ('validation' | 'compliance' | 'usage' | 'approval')[];
  is_active: boolean;
  created_at: string;
  last_activity?: string;
}

export interface TemplateRealtimeUpdate {
  subscription_id: string;
  update_type: 'validation' | 'compliance' | 'usage' | 'approval';
  template_id: string;
  data: {
    template_name: string;
    category: string;
    status?: string;
    changes?: Record<string, any>;
    user?: {
      id: string;
      name: string;
    };
    message?: string;
    severity?: 'info' | 'warning' | 'critical';
  };
  timestamp: string;
}

export interface TemplateRealtimeStatus {
  service_status: 'healthy' | 'degraded' | 'down';
  connected_users: number;
  active_subscriptions: number;
  message_queue_size: number;
  avg_delivery_time_ms: number;
  uptime_percentage: number;
  last_health_check: string;
  supported_features: string[];
}

// Content Watermarking types
export enum WatermarkType {
  TEXT = 'text',
  IMAGE = 'image',
  LOGO = 'logo',
  INVISIBLE = 'invisible',
  QR_CODE = 'qr_code'
}

export enum WatermarkPosition {
  TOP_LEFT = 'top_left',
  TOP_CENTER = 'top_center',
  TOP_RIGHT = 'top_right',
  MIDDLE_LEFT = 'middle_left',
  CENTER = 'center',
  MIDDLE_RIGHT = 'middle_right',
  BOTTOM_LEFT = 'bottom_left',
  BOTTOM_CENTER = 'bottom_center',
  BOTTOM_RIGHT = 'bottom_right',
  CUSTOM = 'custom'
}

export enum ContentStatus {
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  WATERMARKED = 'watermarked',
  FAILED = 'failed',
  ARCHIVED = 'archived'
}

export enum BatchJobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  PAUSED = 'paused'
}

export enum DetectionConfidence {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  VERY_HIGH = 'very_high'
}

export enum TemplateCategory {
  BUSINESS = 'business',
  PERSONAL = 'personal',
  PHOTOGRAPHY = 'photography',
  DOCUMENTS = 'documents',
  ARTWORK = 'artwork',
  BRAND = 'brand',
  CUSTOM = 'custom'
}

export interface WatermarkContent {
  id: string;
  user_id: number;
  name: string;
  original_filename: string;
  content_type: 'image' | 'video' | 'document' | 'audio';
  file_size: number;
  file_url: string;
  thumbnail_url?: string;
  status: ContentStatus;
  watermarked_versions: WatermarkedVersion[];
  metadata: {
    width?: number;
    height?: number;
    duration?: number;
    format: string;
    created_date?: string;
    camera_info?: Record<string, any>;
    location?: { lat: number; lng: number };
    tags?: string[];
  };
  uploaded_at: string;
  updated_at: string;
  collection_ids?: string[];
  protection_level?: 'basic' | 'standard' | 'premium';
  copyright_info?: {
    owner: string;
    year?: number;
    license?: string;
    usage_rights?: string[];
  };
}

export interface WatermarkedVersion {
  id: string;
  template_id: string;
  template_name: string;
  file_url: string;
  thumbnail_url?: string;
  created_at: string;
  settings: WatermarkSettings;
  detection_score?: number;
}

export interface WatermarkTemplate {
  id: string;
  user_id: number;
  name: string;
  type: WatermarkType;
  category: TemplateCategory;
  description?: string;
  preview_url?: string;
  is_public: boolean;
  is_featured: boolean;
  usage_count: number;
  rating: number;
  settings: WatermarkSettings;
  created_at: string;
  updated_at: string;
  tags?: string[];
  compatibility: {
    image: boolean;
    video: boolean;
    document: boolean;
    audio: boolean;
  };
  price?: number;
  author?: {
    name: string;
    organization?: string;
    verified: boolean;
  };
}

export interface WatermarkSettings {
  // Text watermark settings
  text?: {
    content: string;
    font_family: string;
    font_size: number;
    color: string;
    opacity: number;
    rotation: number;
    bold: boolean;
    italic: boolean;
    outline: boolean;
    outline_color?: string;
    shadow: boolean;
    shadow_color?: string;
  };
  
  // Image/Logo watermark settings
  image?: {
    file_url: string;
    opacity: number;
    scale: number;
    rotation: number;
    blend_mode?: 'normal' | 'multiply' | 'overlay' | 'soft_light';
  };
  
  // Position settings
  position: {
    type: WatermarkPosition;
    x?: number; // for custom positioning
    y?: number; // for custom positioning
    margin_x: number;
    margin_y: number;
  };
  
  // Advanced settings
  advanced?: {
    repeat: boolean;
    repeat_spacing?: number;
    adaptive_opacity?: boolean;
    edge_avoidance?: boolean;
    content_aware?: boolean;
    batch_optimization?: boolean;
  };
  
  // Quality settings
  quality: {
    compression: number;
    preserve_metadata: boolean;
    output_format?: 'original' | 'jpg' | 'png' | 'pdf';
    resolution_limit?: number;
  };
}

export interface CreateWatermarkTemplate {
  name: string;
  type: WatermarkType;
  category: TemplateCategory;
  description?: string;
  settings: WatermarkSettings;
  is_public?: boolean;
  tags?: string[];
  preview_file?: File;
}

export interface BatchWatermarkJob {
  id: string;
  name: string;
  user_id: number;
  status: BatchJobStatus;
  content_ids: string[];
  template_id: string;
  template_name: string;
  progress: number;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  started_at: string;
  completed_at?: string;
  estimated_completion?: string;
  error_message?: string;
  options: {
    output_format?: 'original' | 'jpg' | 'png' | 'pdf';
    quality?: 'low' | 'medium' | 'high';
    preserve_originals: boolean;
    notification_email?: string;
    auto_organize?: boolean;
  };
  results: BatchJobResult[];
}

export interface BatchJobResult {
  content_id: string;
  content_name: string;
  status: 'success' | 'failed' | 'skipped';
  watermarked_version_id?: string;
  file_url?: string;
  error_message?: string;
  processing_time?: number;
}

export interface WatermarkDetectionResult {
  id: string;
  content_id?: string;
  detected_watermarks: DetectedWatermark[];
  confidence_score: number;
  detection_method: 'visual' | 'metadata' | 'hash' | 'ai' | 'hybrid';
  processing_time: number;
  detected_at: string;
  metadata?: {
    file_hash?: string;
    similarity_score?: number;
    reference_templates?: string[];
    ai_model_version?: string;
  };
}

export interface DetectedWatermark {
  template_id?: string;
  template_name?: string;
  confidence: DetectionConfidence;
  location?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  properties?: {
    text_content?: string;
    image_hash?: string;
    opacity?: number;
    rotation?: number;
  };
  verification_status: 'verified' | 'suspected' | 'false_positive';
}

export interface WatermarkAnalytics {
  content_stats: {
    total_content: number;
    watermarked_content: number;
    processing_queue: number;
    storage_used: number;
    monthly_uploads: number;
  };
  template_stats: {
    total_templates: number;
    public_templates: number;
    private_templates: number;
    most_used_template: {
      id: string;
      name: string;
      usage_count: number;
    };
  };
  batch_stats: {
    total_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    avg_processing_time: number;
  };
  detection_stats: {
    total_scans: number;
    watermarks_detected: number;
    false_positives: number;
    accuracy_rate: number;
  };
  usage_trends: {
    date: string;
    content_uploaded: number;
    watermarks_applied: number;
    detections_run: number;
  }[];
  popular_categories: {
    category: TemplateCategory;
    count: number;
    percentage: number;
  }[];
}

export interface ContentCollection {
  id: string;
  name: string;
  description?: string;
  user_id: number;
  content_count: number;
  total_size: number;
  created_at: string;
  updated_at: string;
  tags?: string[];
  is_shared: boolean;
  shared_users?: string[];
  thumbnail_url?: string;
}

export interface WatermarkingDashboard {
  overview: {
    total_content: number;
    watermarked_content: number;
    active_jobs: number;
    storage_used: number;
    monthly_usage: number;
    protection_rate: number;
  };
  recent_activity: {
    id: string;
    type: 'upload' | 'watermark' | 'detection' | 'batch_complete';
    description: string;
    content_name?: string;
    template_name?: string;
    timestamp: string;
    status: 'success' | 'failed' | 'warning';
  }[];
  processing_queue: {
    pending_jobs: number;
    estimated_time: string;
    current_job?: {
      name: string;
      progress: number;
    };
  };
  top_templates: WatermarkTemplate[];
  detection_alerts: {
    id: string;
    content_name: string;
    detection_type: 'unauthorized_use' | 'tampered_watermark' | 'suspicious_activity';
    confidence: DetectionConfidence;
    timestamp: string;
    url?: string;
  }[];
  storage_breakdown: {
    originals: number;
    watermarked: number;
    thumbnails: number;
    metadata: number;
  };
  performance_metrics: {
    avg_processing_time: number;
    success_rate: number;
    uptime: number;
    queue_health: 'good' | 'warning' | 'critical';
  };
}

export interface WatermarkingSettings {
  default_quality: 'low' | 'medium' | 'high';
  auto_backup: boolean;
  retention_days: number;
  max_file_size: number;
  supported_formats: string[];
  notification_preferences: {
    email_on_completion: boolean;
    email_on_detection: boolean;
    email_on_errors: boolean;
    webhook_url?: string;
  };
  processing_options: {
    parallel_processing: boolean;
    gpu_acceleration: boolean;
    smart_crop: boolean;
    metadata_preservation: boolean;
    auto_optimize: boolean;
  };
  privacy_settings: {
    public_templates: boolean;
    analytics_sharing: boolean;
    usage_statistics: boolean;
  };
  integration_settings: {
    cloud_storage?: {
      provider: 'aws' | 'google' | 'azure';
      bucket: string;
      credentials: Record<string, any>;
    };
    api_access: {
      enabled: boolean;
      rate_limit: number;
      api_key?: string;
    };
  };
}

export interface WatermarkPreview {
  preview_url: string;
  thumbnail_url: string;
  settings_used: WatermarkSettings;
  estimated_quality: number;
  file_size_estimate: number;
  processing_time_estimate: number;
  warnings?: string[];
  suggestions?: string[];
}

export interface TemplateLibrary {
  categories: {
    category: TemplateCategory;
    count: number;
    featured_templates: string[];
  }[];
  featured: WatermarkTemplate[];
  recent: WatermarkTemplate[];
  trending: WatermarkTemplate[];
  user_templates: WatermarkTemplate[];
  filters: {
    type: WatermarkType[];
    category: TemplateCategory[];
    price_range: { min: number; max: number };
    rating: { min: number; max: number };
    compatibility: string[];
  };
}


export interface ExportRequest {
  content_ids?: string[];
  collection_ids?: string[];
  format: 'zip' | 'folder';
  include_originals: boolean;
  include_watermarked: boolean;
  include_metadata: boolean;
  include_templates: boolean;
  compression_level: 'none' | 'fast' | 'best';
  organization: 'flat' | 'by_date' | 'by_type' | 'by_collection';
}

export interface ImportStatus {
  import_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  total_files: number;
  processed_files: number;
  successful_imports: number;
  failed_imports: number;
  estimated_completion?: string;
  results?: {
    content_id: string;
    filename: string;
    status: 'success' | 'failed';
    error_message?: string;
    watermarks_detected?: number;
  }[];
  metadata?: {
    extraction_enabled: boolean;
    auto_detection_enabled: boolean;
    organization_method: string;
  };
}

// WebSocket message types for real-time updates
export interface WatermarkingWebSocketMessage {
  type: 'content_processing' | 'batch_progress' | 'detection_result' | 'template_update' | 'system_alert';
  payload: {
    content?: {
      id: string;
      name: string;
      status: ContentStatus;
      progress?: number;
    };
    batch?: {
      id: string;
      name: string;
      progress: number;
      status: BatchJobStatus;
      completed_items?: number;
      total_items?: number;
    };
    detection?: {
      content_id: string;
      result: WatermarkDetectionResult;
    };
    template?: {
      id: string;
      name: string;
      action: 'created' | 'updated' | 'deleted' | 'shared';
    };
    system?: {
      component: string;
      status: 'healthy' | 'degraded' | 'critical';
      message: string;
    };
  };
  timestamp: string;
}

export interface WatermarkingSubscription {
  id: string;
  types: ('content_processing' | 'batch_progress' | 'detection_result' | 'template_update')[];
  content_ids?: string[];
  batch_ids?: string[];
  template_ids?: string[];
  is_active: boolean;
  created_at: string;
}

// Re-export DMCA types for consistency
export * from './dmca';