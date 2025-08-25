import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { Checkbox } from 'primereact/checkbox';
import { Toast } from 'primereact/toast';
import { TabView, TabPanel } from 'primereact/tabview';
import { Accordion, AccordionTab } from 'primereact/accordion';
import { Fieldset } from 'primereact/fieldset';
import { EnhancedCard } from '../../common/EnhancedCard';
import { EnhancedButton } from '../../common/EnhancedButton';
import { templatesApi } from '../../../services/api';
import { TemplateVariable, TemplatePreviewResponse } from '../../../types/templates';
import { WizardFormData } from '../TemplateCreationWizard';

interface StepPreviewFinalizeProps {
  formData: WizardFormData;
  errors: Record<string, string>;
  onChange: (updates: Partial<WizardFormData>) => void;
  previewResult: TemplatePreviewResponse | null;
  onPreviewResult: (result: TemplatePreviewResponse | null) => void;
}

interface PreviewFormValues {
  [key: string]: string | boolean | Date | null;
}

interface ValidationIssue {
  type: 'error' | 'warning' | 'info';
  message: string;
  field?: string;
  suggestion?: string;
}

export const StepPreviewFinalize: React.FC<StepPreviewFinalizeProps> = ({
  formData,
  errors,
  onChange,
  previewResult,
  onPreviewResult
}) => {
  const [previewValues, setPreviewValues] = useState<PreviewFormValues>({});
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  
  const toast = useRef<Toast>(null);

  // Initialize preview values with defaults
  useEffect(() => {
    const initialValues: PreviewFormValues = {};
    formData.variables.forEach(variable => {
      if (variable.default_value) {
        if (variable.type === 'date') {
          try {
            initialValues[variable.name] = new Date(variable.default_value);
          } catch {
            initialValues[variable.name] = new Date();
          }
        } else if (variable.type === 'checkbox') {
          initialValues[variable.name] = variable.default_value === 'true';
        } else {
          initialValues[variable.name] = variable.default_value;
        }
      } else {
        // Set smart defaults
        switch (variable.name) {
          case 'current_date':
            initialValues[variable.name] = new Date();
            break;
          case 'platform_name':
            initialValues[variable.name] = 'YouTube';
            break;
          case 'contact_name':
            initialValues[variable.name] = 'John Doe';
            break;
          case 'contact_email':
            initialValues[variable.name] = 'john@example.com';
            break;
          case 'work_title':
            initialValues[variable.name] = 'My Creative Work';
            break;
          case 'copyright_owner':
            initialValues[variable.name] = 'John Doe';
            break;
          default:
            initialValues[variable.name] = variable.type === 'checkbox' ? false : '';
        }
      }
    });
    setPreviewValues(initialValues);
  }, [formData.variables]);

  // Validate template for common issues
  const validateTemplate = (): ValidationIssue[] => {
    const issues: ValidationIssue[] = [];
    
    // Check for missing required legal statements
    const content = formData.content.toLowerCase();
    
    if (!content.includes('good faith') && !content.includes('goodfaith')) {
      issues.push({
        type: 'error',
        message: 'DMCA templates typically require a "good faith" statement',
        suggestion: 'Add: "I have a good faith belief that the use is not authorized..."'
      });
    }
    
    if (!content.includes('perjury') && !content.includes('penalty')) {
      issues.push({
        type: 'error',
        message: 'DMCA templates typically require a perjury statement',
        suggestion: 'Add: "Under penalty of perjury, I certify that this information is accurate..."'
      });
    }
    
    if (!content.includes('copyright') && !content.includes('infringement')) {
      issues.push({
        type: 'warning',
        message: 'Consider explicitly mentioning "copyright infringement" in your template'
      });
    }
    
    // Check for contact information
    const hasContactInfo = formData.variables.some(v => 
      ['contact_name', 'contact_email', 'contact_phone', 'contact_address'].includes(v.name)
    );
    if (!hasContactInfo) {
      issues.push({
        type: 'warning',
        message: 'Consider adding contact information variables for proper DMCA compliance'
      });
    }
    
    // Check for signature
    const hasSignature = formData.variables.some(v => 
      ['signature', 'digital_signature'].includes(v.name)
    );
    if (!hasSignature) {
      issues.push({
        type: 'warning',
        message: 'Consider adding a signature variable to authenticate the notice'
      });
    }
    
    // Check for proper URL fields
    const hasUrlField = formData.variables.some(v => v.type === 'url' || v.name.includes('url'));
    if (!hasUrlField) {
      issues.push({
        type: 'warning',
        message: 'Consider adding URL fields for infringing and original content locations'
      });
    }
    
    // Check variable count
    if (formData.variables.length === 0) {
      issues.push({
        type: 'error',
        message: 'Template has no variables - users won\'t be able to customize it'
      });
    } else if (formData.variables.length > 20) {
      issues.push({
        type: 'warning',
        message: 'Template has many variables - consider grouping or simplifying for better user experience'
      });
    }
    
    // Check for jurisdiction appropriateness
    if (formData.jurisdiction === 'US' && !content.includes('dmca')) {
      issues.push({
        type: 'info',
        message: 'US jurisdiction selected but DMCA not mentioned - ensure this is appropriate'
      });
    }
    
    return issues;
  };

  // Generate preview
  const generatePreview = async () => {
    if (!formData.content.trim()) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Content',
        detail: 'Please add template content before generating preview'
      });
      return;
    }

    setIsGeneratingPreview(true);
    try {
      // Convert preview values for API
      const apiValues: Record<string, string> = {};
      Object.entries(previewValues).forEach(([key, value]) => {
        if (value instanceof Date) {
          apiValues[key] = value.toLocaleDateString();
        } else if (typeof value === 'boolean') {
          apiValues[key] = value ? 'Yes' : 'No';
        } else {
          apiValues[key] = String(value || '');
        }
      });

      const response = await templatesApi.previewTemplate({
        content: formData.content,
        variables: formData.variables,
        values: apiValues
      });
      
      onPreviewResult(response.data);
      
      // Run validation
      const issues = validateTemplate();
      setValidationIssues(issues);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Preview Generated',
        detail: 'Template preview has been generated successfully'
      });
    } catch (error) {
      console.error('Error generating preview:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Preview Error',
        detail: 'Failed to generate template preview'
      });
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  // Handle preview value change
  const handlePreviewValueChange = (variableName: string, value: any) => {
    setPreviewValues(prev => ({
      ...prev,
      [variableName]: value
    }));
  };

  // Render variable input for preview
  const renderVariableInput = (variable: TemplateVariable) => {
    const value = previewValues[variable.name];
    
    switch (variable.type) {
      case 'textarea':
        return (
          <InputTextarea
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.target.value)}
            rows={3}
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
      
      case 'email':
        return (
          <InputText
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.target.value)}
            type="email"
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
      
      case 'url':
        return (
          <InputText
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.target.value)}
            type="url"
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
      
      case 'date':
        return (
          <Calendar
            value={value as Date}
            onChange={(e) => handlePreviewValueChange(variable.name, e.value)}
            className="w-full"
            dateFormat="mm/dd/yy"
          />
        );
      
      case 'number':
        return (
          <InputText
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.target.value)}
            type="number"
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
      
      case 'select':
        return (
          <Dropdown
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.value)}
            options={variable.options?.map(opt => ({ label: opt, value: opt })) || []}
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
      
      case 'checkbox':
        return (
          <div className="flex align-items-center">
            <Checkbox
              checked={Boolean(value)}
              onChange={(e) => handlePreviewValueChange(variable.name, e.checked)}
            />
            <label className="ml-2">{variable.placeholder || 'Yes'}</label>
          </div>
        );
      
      default:
        return (
          <InputText
            value={String(value || '')}
            onChange={(e) => handlePreviewValueChange(variable.name, e.target.value)}
            className="w-full"
            placeholder={variable.placeholder}
          />
        );
    }
  };

  // Get severity color for validation issues
  const getSeverityProps = (type: ValidationIssue['type']) => {
    switch (type) {
      case 'error':
        return { severity: 'danger' as const, icon: 'pi pi-times-circle' };
      case 'warning':
        return { severity: 'warning' as const, icon: 'pi pi-exclamation-triangle' };
      case 'info':
        return { severity: 'info' as const, icon: 'pi pi-info-circle' };
      default:
        return { severity: 'info' as const, icon: 'pi pi-info-circle' };
    }
  };

  const errorCount = validationIssues.filter(i => i.type === 'error').length;
  const warningCount = validationIssues.filter(i => i.type === 'warning').length;

  return (
    <div className="step-preview-finalize">
      <Toast ref={toast} />
      
      <div className="step-header mb-4">
        <h4 className="m-0 mb-2">Preview & Finalize</h4>
        <p className="text-color-secondary m-0">
          Test your template with sample data, review validation results, and finalize your creation.
        </p>
      </div>

      <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
        {/* Template Summary Tab */}
        <TabPanel 
          header="Summary" 
          leftIcon="pi pi-info-circle"
        >
          <div className="grid">
            <div className="col-12 lg:col-8">
              <EnhancedCard className="mb-4">
                <h5>Template Overview</h5>
                <div className="grid">
                  <div className="col-6">
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Name</label>
                      <div className="text-lg font-semibold">{formData.name}</div>
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Category</label>
                      <Tag value={formData.category} severity="info" />
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Language</label>
                      <div>{formData.language?.toUpperCase() || 'EN'}</div>
                    </div>
                  </div>
                  <div className="col-6">
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Variables</label>
                      <div className="text-lg font-semibold">{formData.variables.length}</div>
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Jurisdiction</label>
                      <div>{formData.jurisdiction}</div>
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium text-color-secondary mb-1">Status</label>
                      <Tag 
                        value={formData.is_active ? 'Active' : 'Inactive'} 
                        severity={formData.is_active ? 'success' : 'secondary'} 
                      />
                    </div>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="block text-sm font-medium text-color-secondary mb-1">Description</label>
                  <p className="m-0">{formData.description}</p>
                </div>
                {formData.tags.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-color-secondary mb-2">Tags</label>
                    <div className="flex flex-wrap gap-1">
                      {formData.tags.map((tag, index) => (
                        <Tag key={index} value={tag} severity="secondary" className="text-xs" />
                      ))}
                    </div>
                  </div>
                )}
              </EnhancedCard>

              {/* Content Statistics */}
              <EnhancedCard>
                <h5>Content Statistics</h5>
                <div className="grid text-center">
                  <div className="col-3">
                    <div className="text-2xl font-bold text-primary">{formData.content.length}</div>
                    <div className="text-sm text-color-secondary">Characters</div>
                  </div>
                  <div className="col-3">
                    <div className="text-2xl font-bold text-primary">
                      {formData.content.split(/\s+/).filter(word => word.length > 0).length}
                    </div>
                    <div className="text-sm text-color-secondary">Words</div>
                  </div>
                  <div className="col-3">
                    <div className="text-2xl font-bold text-primary">{formData.variables.length}</div>
                    <div className="text-sm text-color-secondary">Variables</div>
                  </div>
                  <div className="col-3">
                    <div className="text-2xl font-bold text-primary">
                      {formData.variables.filter(v => v.required).length}
                    </div>
                    <div className="text-sm text-color-secondary">Required</div>
                  </div>
                </div>
              </EnhancedCard>
            </div>

            <div className="col-12 lg:col-4">
              {/* Quick Actions */}
              <EnhancedCard className="mb-4">
                <h5>Quick Actions</h5>
                <div className="flex flex-column gap-2">
                  <EnhancedButton
                    label="Generate Preview"
                    icon="pi pi-eye"
                    onClick={generatePreview}
                    loading={isGeneratingPreview}
                    className="w-full"
                  />
                  <Button
                    label="Test with Sample Data"
                    icon="pi pi-play"
                    className="p-button-outlined w-full"
                    onClick={() => setActiveTab(1)}
                  />
                  <Button
                    label="View Variables"
                    icon="pi pi-tags"
                    className="p-button-text w-full"
                    onClick={() => setActiveTab(2)}
                  />
                </div>
              </EnhancedCard>

              {/* Template Health */}
              <EnhancedCard>
                <div className="flex align-items-center justify-content-between mb-3">
                  <h5 className="m-0">Template Health</h5>
                  <Button
                    icon="pi pi-refresh"
                    className="p-button-text p-button-sm"
                    onClick={() => setValidationIssues(validateTemplate())}
                  />
                </div>
                {validationIssues.length === 0 ? (
                  <div className="text-center py-3">
                    <i className="pi pi-check-circle text-green-500 text-3xl mb-2 block" />
                    <div className="text-green-700 font-medium">All Good!</div>
                    <div className="text-sm text-color-secondary">No issues found</div>
                  </div>
                ) : (
                  <div>
                    <div className="flex gap-3 mb-3">
                      {errorCount > 0 && (
                        <Badge value={errorCount} severity="danger" className="mr-1">
                          <i className="pi pi-times-circle mr-1" />
                          Errors
                        </Badge>
                      )}
                      {warningCount > 0 && (
                        <Badge value={warningCount} severity="warning">
                          <i className="pi pi-exclamation-triangle mr-1" />
                          Warnings
                        </Badge>
                      )}
                    </div>
                    <Button
                      label="View Details"
                      icon="pi pi-list"
                      className="p-button-text p-button-sm w-full"
                      onClick={() => setActiveTab(3)}
                    />
                  </div>
                )}
              </EnhancedCard>
            </div>
          </div>
        </TabPanel>

        {/* Live Preview Tab */}
        <TabPanel 
          header="Live Preview" 
          leftIcon="pi pi-eye"
        >
          <div className="grid">
            <div className="col-12 lg:col-4">
              <EnhancedCard className="sticky-top">
                <div className="flex justify-content-between align-items-center mb-3">
                  <h5 className="m-0">Sample Values</h5>
                  <EnhancedButton
                    label="Generate"
                    icon="pi pi-sync"
                    size="small"
                    onClick={generatePreview}
                    loading={isGeneratingPreview}
                  />
                </div>
                
                <div className="preview-form max-h-30rem overflow-auto">
                  {formData.variables.map((variable) => (
                    <div key={variable.name} className="field">
                      <label className="block text-sm font-medium mb-1">
                        {variable.label}
                        {variable.required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      {renderVariableInput(variable)}
                      {variable.description && (
                        <small className="block mt-1 text-color-secondary">
                          {variable.description}
                        </small>
                      )}
                    </div>
                  ))}
                </div>
              </EnhancedCard>
            </div>

            <div className="col-12 lg:col-8">
              <EnhancedCard>
                <div className="flex justify-content-between align-items-center mb-3">
                  <h5 className="m-0">Generated Preview</h5>
                  {previewResult && (
                    <div className="flex gap-2">
                      <Button
                        icon="pi pi-copy"
                        className="p-button-text p-button-sm"
                        tooltip="Copy to clipboard"
                        onClick={() => navigator.clipboard.writeText(previewResult.rendered_content)}
                      />
                      <Button
                        icon="pi pi-download"
                        className="p-button-text p-button-sm"
                        tooltip="Download as text file"
                        onClick={() => {
                          const blob = new Blob([previewResult.rendered_content], { type: 'text/plain' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${formData.name.replace(/[^a-zA-Z0-9]/g, '_')}_preview.txt`;
                          a.click();
                          URL.revokeObjectURL(url);
                        }}
                      />
                    </div>
                  )}
                </div>
                
                {previewResult ? (
                  <div className="preview-content">
                    <div 
                      className="p-3 bg-gray-50 border-round font-monospace text-sm"
                      style={{ whiteSpace: 'pre-wrap', minHeight: '400px' }}
                    >
                      {previewResult.rendered_content}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <i className="pi pi-eye-slash text-4xl text-color-secondary mb-3 block" />
                    <h6 className="text-color-secondary">No Preview Generated</h6>
                    <p className="text-color-secondary">
                      Fill in the sample values and click "Generate" to see how your template will look.
                    </p>
                  </div>
                )}
              </EnhancedCard>
            </div>
          </div>
        </TabPanel>

        {/* Variables Tab */}
        <TabPanel 
          header="Variables" 
          leftIcon="pi pi-tags"
        >
          <EnhancedCard>
            <div className="flex justify-content-between align-items-center mb-4">
              <h5 className="m-0">Template Variables ({formData.variables.length})</h5>
            </div>
            
            {formData.variables.length === 0 ? (
              <div className="text-center py-6">
                <i className="pi pi-tags text-4xl text-color-secondary mb-3 block" />
                <h6 className="text-color-secondary">No Variables Defined</h6>
                <p className="text-color-secondary">
                  Your template doesn't have any variables. Users won't be able to customize the content.
                </p>
              </div>
            ) : (
              <Accordion multiple>
                {formData.variables.map((variable, index) => (
                  <AccordionTab
                    key={variable.name}
                    header={
                      <div className="flex align-items-center justify-content-between w-full pr-3">
                        <div className="flex align-items-center gap-3">
                          <code className="text-primary font-semibold">
                            {variable.name}
                          </code>
                          <span>{variable.label}</span>
                        </div>
                        <div className="flex align-items-center gap-2">
                          <Tag value={variable.type} severity="info" className="text-xs" />
                          {variable.required && (
                            <Tag value="required" severity="danger" className="text-xs" />
                          )}
                        </div>
                      </div>
                    }
                  >
                    <div className="grid">
                      <div className="col-12 md:col-6">
                        <div className="mb-3">
                          <strong>Type:</strong> {variable.type}
                        </div>
                        <div className="mb-3">
                          <strong>Required:</strong> {variable.required ? 'Yes' : 'No'}
                        </div>
                        {variable.default_value && (
                          <div className="mb-3">
                            <strong>Default Value:</strong> {variable.default_value}
                          </div>
                        )}
                      </div>
                      <div className="col-12 md:col-6">
                        {variable.placeholder && (
                          <div className="mb-3">
                            <strong>Placeholder:</strong> {variable.placeholder}
                          </div>
                        )}
                        {variable.validation_pattern && (
                          <div className="mb-3">
                            <strong>Validation Pattern:</strong> 
                            <code className="ml-2 text-sm">{variable.validation_pattern}</code>
                          </div>
                        )}
                      </div>
                      {variable.description && (
                        <div className="col-12">
                          <div className="mb-3">
                            <strong>Description:</strong>
                            <p className="mt-1 mb-0">{variable.description}</p>
                          </div>
                        </div>
                      )}
                      {variable.options && variable.options.length > 0 && (
                        <div className="col-12">
                          <strong>Options:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {variable.options.map((option, optIndex) => (
                              <Tag key={optIndex} value={option} severity="secondary" className="text-xs" />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </AccordionTab>
                ))}
              </Accordion>
            )}
          </EnhancedCard>
        </TabPanel>

        {/* Validation Tab */}
        <TabPanel 
          header={
            <div className="flex align-items-center gap-2">
              <span>Validation</span>
              {validationIssues.length > 0 && (
                <Badge value={validationIssues.length} severity="warning" />
              )}
            </div>
          } 
          leftIcon="pi pi-shield"
        >
          <EnhancedCard>
            <div className="flex justify-content-between align-items-center mb-4">
              <h5 className="m-0">Template Validation</h5>
              <Button
                label="Re-validate"
                icon="pi pi-refresh"
                className="p-button-outlined p-button-sm"
                onClick={() => setValidationIssues(validateTemplate())}
              />
            </div>
            
            {validationIssues.length === 0 ? (
              <div className="text-center py-6">
                <i className="pi pi-check-circle text-green-500 text-4xl mb-3 block" />
                <h6 className="text-green-700">Validation Passed!</h6>
                <p className="text-color-secondary">
                  Your template follows best practices and appears ready for use.
                </p>
              </div>
            ) : (
              <div className="validation-issues">
                {validationIssues.map((issue, index) => (
                  <Card key={index} className={`mb-3 border-left-3 ${
                    issue.type === 'error' ? 'border-red-500' : 
                    issue.type === 'warning' ? 'border-yellow-500' : 
                    'border-blue-500'
                  }`}>
                    <div className="flex align-items-start gap-3">
                      <i className={`${getSeverityProps(issue.type).icon} text-xl mt-1 ${
                        issue.type === 'error' ? 'text-red-500' : 
                        issue.type === 'warning' ? 'text-yellow-600' : 
                        'text-blue-500'
                      }`} />
                      <div className="flex-1">
                        <div className={`font-medium mb-1 ${
                          issue.type === 'error' ? 'text-red-700' : 
                          issue.type === 'warning' ? 'text-yellow-700' : 
                          'text-blue-700'
                        }`}>
                          {issue.message}
                        </div>
                        {issue.suggestion && (
                          <div className="text-sm text-color-secondary">
                            <strong>Suggestion:</strong> {issue.suggestion}
                          </div>
                        )}
                        {issue.field && (
                          <div className="text-sm text-color-secondary mt-1">
                            <strong>Field:</strong> {issue.field}
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </EnhancedCard>
        </TabPanel>
      </TabView>
    </div>
  );
};

export default StepPreviewFinalize;