// DMCA Template Management Types

export type TemplateCategoryType = 
  | 'Standard DMCA Notices'
  | 'Platform-Specific' 
  | 'International'
  | 'Counter-Notices'
  | 'Follow-up'
  | 'Search Engine';

export type TemplateComplianceStatus = 
  | 'PENDING'
  | 'COMPLIANT'
  | 'NEEDS_REVISION';

export type TemplateApprovalStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'REJECTED';

export interface IDMCATemplate {
  id: string;
  title: string;
  content: string;
  category: TemplateCategoryType;
  complianceStatus: TemplateComplianceStatus;
  approvalStatus?: TemplateApprovalStatus;
  version?: string;
  createdAt?: Date;
  updatedAt?: Date;
  createdBy?: string;
  lastModifiedBy?: string;
  variables?: TemplateVariable[];
  platforms?: string[];
  jurisdiction?: string;
  legalReferences?: LegalReference[];
  usageStats?: TemplateUsageStats;
  auditTrail?: TemplateAuditEntry[];
}

export interface TemplateVariable {
  name: string;
  placeholder: string;
  type: 'text' | 'url' | 'email' | 'date';
  required: boolean;
  description: string;
  defaultValue?: string;
}

export interface LegalReference {
  statute: string;
  section: string;
  description: string;
  url?: string;
}

export interface TemplateUsageStats {
  totalUsage: number;
  successRate: number;
  platformBreakdown: Record<string, number>;
  lastUsed?: Date;
  averageResponseTime?: number;
}

export interface TemplateAuditEntry {
  timestamp: Date;
  action: 'created' | 'modified' | 'approved' | 'rejected' | 'used';
  userId: string;
  description: string;
  changes?: Record<string, any>;
}

export interface TemplateValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  complianceScore: number;
  requiredElements: DMCARequiredElement[];
}

export interface DMCARequiredElement {
  element: string;
  present: boolean;
  description: string;
  legalRequirement: string;
}

export interface TemplatePreviewData {
  creatorName: string;
  infringingUrl: string;
  platform: string;
  workDescription: string;
  contactEmail: string;
  copyrightUrl: string;
  dateOfInfringement: string;
}

// Platform-specific template configurations
export interface PlatformTemplateConfig {
  platform: string;
  apiEndpoint?: string;
  requiredFields: string[];
  maximumLength?: number;
  supportedFormats: ('html' | 'text' | 'markdown')[];
  specificRequirements: string[];
}

// International jurisdiction configurations
export interface JurisdictionConfig {
  country: string;
  legalFramework: string;
  requiredDisclosures: string[];
  languageRequirements: string[];
  specificClauses: string[];
}

// Template library and categorization
export interface TemplateLibraryEntry {
  id: string;
  name: string;
  description: string;
  category: TemplateCategoryType;
  tags: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  template: IDMCATemplate;
}

// Bulk operations interface
export interface BulkTemplateOperation {
  operation: 'update' | 'delete' | 'approve' | 'reject';
  templateIds: string[];
  data?: Partial<IDMCATemplate>;
}

// Template testing and validation
export interface TemplateTestResult {
  templateId: string;
  testType: 'compliance' | 'delivery' | 'response';
  passed: boolean;
  issues: string[];
  recommendations: string[];
  timestamp: Date;
}

// Export/Import interfaces
export interface TemplateExportOptions {
  format: 'json' | 'xml' | 'csv';
  includeAuditTrail: boolean;
  includeUsageStats: boolean;
  categories?: TemplateCategoryType[];
}

export interface TemplateImportResult {
  imported: number;
  failed: number;
  errors: string[];
  warnings: string[];
}