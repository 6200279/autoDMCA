export interface DMCATemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  variables: TemplateVariable[];
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  usage_count?: number;
  tags?: string[];
  language?: string;
  jurisdiction?: string;
}

export interface TemplateVariable {
  name: string;
  label: string;
  type: 'text' | 'email' | 'url' | 'date' | 'number' | 'textarea' | 'select';
  required: boolean;
  default_value?: string;
  description?: string;
  options?: string[]; // For select type
  validation_pattern?: string;
  placeholder?: string;
}

export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
  template_count: number;
  icon?: string;
  color?: string;
}

export interface TemplatePreviewRequest {
  template_id?: string;
  content?: string;
  variables: TemplateVariable[];
  values: Record<string, string>;
}

export interface TemplatePreviewResponse {
  rendered_content: string;
  missing_variables: string[];
  validation_errors: Record<string, string>;
}

export interface CreateTemplateRequest {
  name: string;
  description: string;
  category: string;
  content: string;
  variables: TemplateVariable[];
  tags?: string[];
  language?: string;
  jurisdiction?: string;
  is_active?: boolean;
}

export interface UpdateTemplateRequest extends Partial<CreateTemplateRequest> {
  id: string;
}

export interface TemplateListParams {
  page?: number;
  limit?: number;
  category?: string;
  search?: string;
  is_active?: boolean;
  language?: string;
  jurisdiction?: string;
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'usage_count';
  sort_order?: 'asc' | 'desc';
  tags?: string[];
}

export interface PaginatedTemplatesResponse {
  templates: DMCATemplate[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface TemplateFormData {
  name: string;
  description: string;
  category: string;
  content: string;
  variables: TemplateVariable[];
  tags: string[];
  language: string;
  jurisdiction: string;
  is_active: boolean;
}

export interface TemplateEditorState {
  template: DMCATemplate | null;
  isEditing: boolean;
  hasUnsavedChanges: boolean;
  previewData: Record<string, any>;
  errors: Record<string, string>;
}

// Variable type definitions for the template editor
export const VARIABLE_TYPES = [
  { label: 'Text', value: 'text' },
  { label: 'Email', value: 'email' },
  { label: 'URL', value: 'url' },
  { label: 'Date', value: 'date' },
  { label: 'Number', value: 'number' },
  { label: 'Text Area', value: 'textarea' },
  { label: 'Select', value: 'select' }
] as const;

// Common template categories
export const DEFAULT_CATEGORIES = [
  'General DMCA',
  'Social Media',
  'Search Engines',
  'Hosting Providers',
  'E-commerce',
  'Video Platforms',
  'Image Hosting',
  'File Sharing',
  'Forums',
  'Educational',
  'International'
] as const;

// Supported languages
export const SUPPORTED_LANGUAGES = [
  { label: 'English', value: 'en' },
  { label: 'Spanish', value: 'es' },
  { label: 'French', value: 'fr' },
  { label: 'German', value: 'de' },
  { label: 'Portuguese', value: 'pt' },
  { label: 'Italian', value: 'it' },
  { label: 'Dutch', value: 'nl' },
  { label: 'Japanese', value: 'ja' },
  { label: 'Korean', value: 'ko' },
  { label: 'Chinese (Simplified)', value: 'zh-cn' },
  { label: 'Chinese (Traditional)', value: 'zh-tw' }
] as const;

// Common jurisdictions
export const JURISDICTIONS = [
  { label: 'United States', value: 'US' },
  { label: 'European Union', value: 'EU' },
  { label: 'United Kingdom', value: 'UK' },
  { label: 'Canada', value: 'CA' },
  { label: 'Australia', value: 'AU' },
  { label: 'Japan', value: 'JP' },
  { label: 'South Korea', value: 'KR' },
  { label: 'Brazil', value: 'BR' },
  { label: 'Mexico', value: 'MX' },
  { label: 'India', value: 'IN' },
  { label: 'International', value: 'INTL' }
] as const;

// Template validation rules
export interface TemplateValidationRule {
  field: keyof TemplateFormData;
  rule: string;
  message: string;
}

export const TEMPLATE_VALIDATION_RULES: TemplateValidationRule[] = [
  { field: 'name', rule: 'required', message: 'Template name is required' },
  { field: 'name', rule: 'minLength:3', message: 'Template name must be at least 3 characters' },
  { field: 'name', rule: 'maxLength:100', message: 'Template name cannot exceed 100 characters' },
  { field: 'description', rule: 'required', message: 'Description is required' },
  { field: 'description', rule: 'maxLength:500', message: 'Description cannot exceed 500 characters' },
  { field: 'category', rule: 'required', message: 'Category is required' },
  { field: 'content', rule: 'required', message: 'Template content is required' },
  { field: 'content', rule: 'minLength:50', message: 'Template content must be at least 50 characters' }
];