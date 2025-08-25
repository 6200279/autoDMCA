import React from 'react';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Chips } from 'primereact/chips';
import { Checkbox } from 'primereact/checkbox';
import { EnhancedCard } from '../../common/EnhancedCard';
import { 
  SUPPORTED_LANGUAGES,
  JURISDICTIONS
} from '../../../types/templates';
import { WizardFormData } from '../TemplateCreationWizard';

interface StepBasicInfoProps {
  formData: WizardFormData;
  errors: Record<string, string>;
  onChange: (updates: Partial<WizardFormData>) => void;
}

export const StepBasicInfo: React.FC<StepBasicInfoProps> = ({
  formData,
  errors,
  onChange
}) => {
  const handleFieldChange = (field: keyof WizardFormData, value: any) => {
    onChange({ [field]: value });
  };

  // Generate smart suggestions based on selected starter
  const generateSmartSuggestions = () => {
    const suggestions: { name?: string; description?: string; tags?: string[] } = {};
    
    if (formData.selectedStarter && !formData.name) {
      // Suggest name based on starter and customization
      suggestions.name = formData.selectedStarter.name;
    }
    
    if (formData.selectedStarter && !formData.description) {
      suggestions.description = formData.selectedStarter.description;
    }
    
    if (formData.selectedStarter && formData.tags.length === 0) {
      suggestions.tags = formData.selectedStarter.tags;
    }
    
    return suggestions;
  };

  const suggestions = generateSmartSuggestions();

  const applySuggestion = (field: keyof WizardFormData, value: any) => {
    onChange({ [field]: value });
  };

  return (
    <div className="step-basic-info">
      <div className="step-header mb-4">
        <h4 className="m-0 mb-2">Basic Information</h4>
        <p className="text-color-secondary m-0">
          Provide essential details about your template including name, description, and settings.
        </p>
      </div>

      {/* Smart Suggestions */}
      {(suggestions.name || suggestions.description || suggestions.tags) && (
        <EnhancedCard className="mb-4 suggestions-card">
          <div className="flex align-items-center gap-2 mb-3">
            <i className="pi pi-lightbulb text-primary" />
            <h6 className="m-0">Smart Suggestions</h6>
          </div>
          
          {suggestions.name && !formData.name && (
            <div className="suggestion-item mb-2">
              <div className="flex justify-content-between align-items-center">
                <span className="text-sm">
                  <strong>Name:</strong> {suggestions.name}
                </span>
                <button
                  type="button"
                  className="p-link text-primary text-sm"
                  onClick={() => applySuggestion('name', suggestions.name)}
                >
                  Apply
                </button>
              </div>
            </div>
          )}
          
          {suggestions.description && !formData.description && (
            <div className="suggestion-item mb-2">
              <div className="flex justify-content-between align-items-start">
                <span className="text-sm flex-1">
                  <strong>Description:</strong> {suggestions.description}
                </span>
                <button
                  type="button"
                  className="p-link text-primary text-sm ml-2"
                  onClick={() => applySuggestion('description', suggestions.description)}
                >
                  Apply
                </button>
              </div>
            </div>
          )}
          
          {suggestions.tags && formData.tags.length === 0 && (
            <div className="suggestion-item">
              <div className="flex justify-content-between align-items-start">
                <span className="text-sm flex-1">
                  <strong>Tags:</strong> {suggestions.tags.join(', ')}
                </span>
                <button
                  type="button"
                  className="p-link text-primary text-sm ml-2"
                  onClick={() => applySuggestion('tags', suggestions.tags)}
                >
                  Apply
                </button>
              </div>
            </div>
          )}
        </EnhancedCard>
      )}

      <div className="grid">
        {/* Template Name */}
        <div className="col-12 md:col-8">
          <EnhancedCard>
            <div className="field">
              <label htmlFor="template_name" className="block mb-2 font-medium">
                Template Name <span className="text-red-500">*</span>
              </label>
              <InputText
                id="template_name"
                value={formData.name}
                onChange={(e) => handleFieldChange('name', e.target.value)}
                className={`w-full ${errors.name ? 'p-invalid' : ''}`}
                placeholder="Enter a descriptive name for your template"
                maxLength={100}
              />
              {errors.name && (
                <small className="p-error block mt-1">{errors.name}</small>
              )}
              <div className="flex justify-content-between align-items-center mt-1">
                <small className="text-color-secondary">
                  Choose a clear, descriptive name that helps identify the template's purpose
                </small>
                <small className="text-color-secondary">
                  {formData.name.length}/100
                </small>
              </div>
            </div>
          </EnhancedCard>
        </div>

        {/* Template Status */}
        <div className="col-12 md:col-4">
          <EnhancedCard>
            <div className="field">
              <label className="block mb-2 font-medium">Template Status</label>
              <div className="flex align-items-center">
                <Checkbox
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => handleFieldChange('is_active', e.checked)}
                />
                <label htmlFor="is_active" className="ml-2">
                  Active template
                </label>
              </div>
              <small className="block mt-1 text-color-secondary">
                Active templates are available for use in takedown requests
              </small>
            </div>
          </EnhancedCard>
        </div>

        {/* Description */}
        <div className="col-12">
          <EnhancedCard>
            <div className="field">
              <label htmlFor="template_description" className="block mb-2 font-medium">
                Description <span className="text-red-500">*</span>
              </label>
              <InputTextarea
                id="template_description"
                value={formData.description}
                onChange={(e) => handleFieldChange('description', e.target.value)}
                rows={4}
                className={`w-full ${errors.description ? 'p-invalid' : ''}`}
                placeholder="Describe when and how this template should be used. Include any specific scenarios, platforms, or requirements."
                maxLength={500}
              />
              {errors.description && (
                <small className="p-error block mt-1">{errors.description}</small>
              )}
              <div className="flex justify-content-between align-items-center mt-1">
                <small className="text-color-secondary">
                  Provide context about the template's purpose, ideal use cases, and any special considerations
                </small>
                <small className="text-color-secondary">
                  {formData.description.length}/500
                </small>
              </div>
            </div>
          </EnhancedCard>
        </div>

        {/* Language and Jurisdiction */}
        <div className="col-12 md:col-6">
          <EnhancedCard>
            <div className="field mb-3">
              <label htmlFor="template_language" className="block mb-2 font-medium">
                Language
              </label>
              <Dropdown
                id="template_language"
                value={formData.language}
                onChange={(e) => handleFieldChange('language', e.value)}
                options={SUPPORTED_LANGUAGES}
                placeholder="Select template language"
                className="w-full"
                filter
              />
              <small className="block mt-1 text-color-secondary">
                The language this template is written in
              </small>
            </div>
          </EnhancedCard>
        </div>

        <div className="col-12 md:col-6">
          <EnhancedCard>
            <div className="field mb-3">
              <label htmlFor="template_jurisdiction" className="block mb-2 font-medium">
                Jurisdiction
              </label>
              <Dropdown
                id="template_jurisdiction"
                value={formData.jurisdiction}
                onChange={(e) => handleFieldChange('jurisdiction', e.value)}
                options={JURISDICTIONS}
                placeholder="Select applicable jurisdiction"
                className="w-full"
                filter
              />
              <small className="block mt-1 text-color-secondary">
                The legal jurisdiction this template is designed for
              </small>
            </div>
          </EnhancedCard>
        </div>

        {/* Tags */}
        <div className="col-12">
          <EnhancedCard>
            <div className="field">
              <label htmlFor="template_tags" className="block mb-2 font-medium">
                Tags
              </label>
              <Chips
                id="template_tags"
                value={formData.tags}
                onChange={(e) => handleFieldChange('tags', e.value || [])}
                placeholder="Add tags to categorize your template (press Enter)"
                className="w-full"
                max={10}
              />
              <small className="block mt-2 text-color-secondary">
                Add relevant tags to help organize and search for this template. 
                Examples: platform names, content types, urgency levels
              </small>
              
              {/* Tag suggestions based on category */}
              {formData.category && (
                <div className="tag-suggestions mt-2">
                  <small className="block mb-2 font-medium text-color-secondary">
                    Suggested tags for {formData.category}:
                  </small>
                  <div className="flex flex-wrap gap-2">
                    {getTagSuggestions(formData.category).map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        className="p-link text-primary text-sm p-1 border-round"
                        onClick={() => {
                          if (!formData.tags.includes(tag)) {
                            handleFieldChange('tags', [...formData.tags, tag]);
                          }
                        }}
                        disabled={formData.tags.includes(tag)}
                      >
                        + {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </EnhancedCard>
        </div>
      </div>

      {/* Template Preview Info */}
      {formData.selectedStarter && (
        <div className="template-info mt-4">
          <EnhancedCard className="bg-blue-50">
            <div className="flex align-items-start gap-3">
              <i className="pi pi-info-circle text-blue-600 text-xl mt-1" />
              <div>
                <h6 className="m-0 mb-2 text-blue-700">Template Information</h6>
                <div className="text-sm text-blue-600">
                  <p className="m-0 mb-2">
                    <strong>Based on:</strong> {formData.selectedStarter.name}
                  </p>
                  <p className="m-0 mb-2">
                    <strong>Variables included:</strong> {formData.selectedStarter.variables.length} pre-configured variables
                  </p>
                  <p className="m-0">
                    <strong>Content length:</strong> ~{Math.round(formData.selectedStarter.content.length / 100) * 100} characters
                  </p>
                </div>
              </div>
            </div>
          </EnhancedCard>
        </div>
      )}

      {/* Validation Help */}
      <div className="validation-help mt-4 p-3 bg-gray-50 border-round">
        <div className="flex align-items-start gap-2">
          <i className="pi pi-check-circle text-green-600 mt-1" />
          <div>
            <h6 className="m-0 mb-2 text-green-700">Template Guidelines</h6>
            <ul className="m-0 text-green-600 text-sm">
              <li>Use descriptive names that clearly indicate the template's purpose</li>
              <li>Include comprehensive descriptions with use cases and requirements</li>
              <li>Choose appropriate jurisdiction based on your target legal framework</li>
              <li>Add relevant tags to improve discoverability and organization</li>
              <li>Ensure the language setting matches your template content</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to get tag suggestions based on category
const getTagSuggestions = (category: string): string[] => {
  const tagMap: Record<string, string[]> = {
    'General DMCA': ['standard', 'copyright', 'takedown', 'infringement'],
    'Social Media': ['facebook', 'instagram', 'twitter', 'tiktok', 'social'],
    'Search Engines': ['google', 'bing', 'search-results', 'indexing'],
    'Hosting Providers': ['web-hosting', 'server', 'domain', 'hosting'],
    'E-commerce': ['amazon', 'ebay', 'marketplace', 'product-listing'],
    'Video Platforms': ['youtube', 'vimeo', 'video', 'streaming'],
    'Image Hosting': ['image', 'photo', 'gallery', 'visual'],
    'File Sharing': ['download', 'file-host', 'sharing', 'storage'],
    'Forums': ['forum', 'discussion', 'community', 'board'],
    'Educational': ['academic', 'research', 'educational', 'institution'],
    'International': ['cross-border', 'multi-jurisdiction', 'international']
  };
  
  return tagMap[category] || ['dmca', 'copyright', 'takedown'];
};

export default StepBasicInfo;