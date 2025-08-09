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

// Re-export DMCA types for consistency
export * from './dmca';