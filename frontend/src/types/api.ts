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

// Dashboard types
export interface DashboardStats {
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