import React, { useState, useEffect, useRef } from 'react';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { InputNumber } from 'primereact/inputnumber';
import { Card } from 'primereact/card';
import { Divider } from 'primereact/divider';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Button } from 'primereact/button';
import { Toast } from 'primereact/toast';
import { Skeleton } from 'primereact/skeleton';
import { ScrollPanel } from 'primereact/scrollpanel';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Message } from 'primereact/message';
import { EnhancedCard } from '../common/EnhancedCard';
import { EnhancedButton } from '../common/EnhancedButton';
import { templatesApi } from '../../services/api';
import {
  DMCATemplate,
  TemplateVariable,
  TemplatePreviewRequest,
  TemplatePreviewResponse
} from '../../types/templates';
import './TemplatePreview.css';

interface TemplatePreviewProps {
  template: DMCATemplate | null;
  isOpen: boolean;
  onClose: () => void;
  onEdit?: (template: DMCATemplate) => void;
  onDuplicate?: (template: DMCATemplate) => void;
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({
  template,
  isOpen,
  onClose,
  onEdit,
  onDuplicate
}) => {
  const [variableValues, setVariableValues] = useState<Record<string, any>>({});
  const [previewResult, setPreviewResult] = useState<TemplatePreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const toast = useRef<Toast>(null);

  // Initialize variable values when template changes
  useEffect(() => {
    if (template && template.variables) {
      const initialValues: Record<string, any> = {};
      template.variables.forEach(variable => {
        if (variable.default_value) {
          if (variable.type === 'date') {
            initialValues[variable.name] = new Date(variable.default_value);
          } else if (variable.type === 'number') {
            initialValues[variable.name] = parseFloat(variable.default_value);
          } else {
            initialValues[variable.name] = variable.default_value;
          }
        } else {
          // Set empty default values based on type
          switch (variable.type) {
            case 'date':
              initialValues[variable.name] = new Date();
              break;
            case 'number':
              initialValues[variable.name] = 0;
              break;
            default:
              initialValues[variable.name] = '';
          }
        }
      });
      setVariableValues(initialValues);
      setErrors({});
    }
  }, [template]);

  // Auto-generate preview when variable values change
  useEffect(() => {
    if (template && Object.keys(variableValues).length > 0) {
      generatePreview();
    }
  }, [variableValues, template]);

  const generatePreview = async () => {
    if (!template) return;

    setLoading(true);
    try {
      // Convert date objects to strings for API
      const apiVariableValues: Record<string, any> = {};
      Object.entries(variableValues).forEach(([key, value]) => {
        if (value instanceof Date) {
          apiVariableValues[key] = value.toISOString().split('T')[0]; // YYYY-MM-DD format
        } else {
          apiVariableValues[key] = value;
        }
      });

      const request: TemplatePreviewRequest = {
        template_id: template.id,
        variables: apiVariableValues
      };

      const response = await templatesApi.previewTemplate(request);
      setPreviewResult(response.data);
      setErrors(response.data.validation_errors || {});
    } catch (error) {
      console.error('Error generating preview:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Preview Error',
        detail: 'Failed to generate template preview'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVariableChange = (variableName: string, value: any) => {
    setVariableValues(prev => ({
      ...prev,
      [variableName]: value
    }));
    
    // Clear field-specific errors
    if (errors[variableName]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[variableName];
        return newErrors;
      });
    }
  };

  const validateRequiredFields = (): boolean => {
    if (!template) return false;
    
    const newErrors: Record<string, string> = {};
    
    template.variables?.forEach(variable => {
      if (variable.required) {
        const value = variableValues[variable.name];
        if (!value || (typeof value === 'string' && value.trim() === '')) {
          newErrors[variable.name] = `${variable.label} is required`;
        }
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleExport = async (format: 'html' | 'pdf') => {
    if (!template || !validateRequiredFields()) {
      toast.current?.show({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'Please fill in all required fields'
      });
      return;
    }

    try {
      const response = await templatesApi.exportTemplate(template.id, format);
      
      if (format === 'pdf') {
        // Handle PDF blob download
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${template.name}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
      } else {
        // Handle HTML download
        const blob = new Blob([previewResult?.rendered_content || ''], { type: 'text/html' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${template.name}.html`;
        link.click();
        window.URL.revokeObjectURL(url);
      }

      toast.current?.show({
        severity: 'success',
        summary: 'Export Success',
        detail: `Template exported as ${format.toUpperCase()}`
      });
    } catch (error) {
      console.error('Export error:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Export Error',
        detail: 'Failed to export template'
      });
    }
  };

  const renderVariableInput = (variable: TemplateVariable) => {
    const value = variableValues[variable.name];
    const hasError = !!errors[variable.name];

    switch (variable.type) {
      case 'textarea':
        return (
          <InputTextarea
            id={`var_${variable.name}`}
            value={value || ''}
            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
            placeholder={variable.placeholder}
            rows={3}
            className={`w-full ${hasError ? 'p-invalid' : ''}`}
            aria-describedby={variable.description ? `var_${variable.name}_help` : undefined}
          />
        );

      case 'select':
        return (
          <Dropdown
            id={`var_${variable.name}`}
            value={value || ''}
            onChange={(e) => handleVariableChange(variable.name, e.value)}
            options={variable.options?.map(opt => ({ label: opt, value: opt })) || []}
            placeholder={variable.placeholder || `Select ${variable.label}`}
            className={`w-full ${hasError ? 'p-invalid' : ''}`}
            aria-describedby={variable.description ? `var_${variable.name}_help` : undefined}
          />
        );

      case 'date':
        return (
          <Calendar
            id={`var_${variable.name}`}
            value={value || null}
            onChange={(e) => handleVariableChange(variable.name, e.value)}
            placeholder={variable.placeholder || 'Select date'}
            className={`w-full ${hasError ? 'p-invalid' : ''}`}
            dateFormat="yy-mm-dd"
            showIcon
            aria-describedby={variable.description ? `var_${variable.name}_help` : undefined}
          />
        );

      case 'number':
        return (
          <InputNumber
            id={`var_${variable.name}`}
            value={value || 0}
            onValueChange={(e) => handleVariableChange(variable.name, e.value)}
            placeholder={variable.placeholder}
            className={`w-full ${hasError ? 'p-invalid' : ''}`}
            aria-describedby={variable.description ? `var_${variable.name}_help` : undefined}
          />
        );

      default: // text, email, url
        return (
          <InputText
            id={`var_${variable.name}`}
            type={variable.type === 'email' ? 'email' : variable.type === 'url' ? 'url' : 'text'}
            value={value || ''}
            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
            placeholder={variable.placeholder}
            className={`w-full ${hasError ? 'p-invalid' : ''}`}
            aria-describedby={variable.description ? `var_${variable.name}_help` : undefined}
          />
        );
    }
  };

  const renderVariablesPanel = () => (
    <div className="variables-panel">
      <div className="panel-header mb-4">
        <h3 className="text-xl font-semibold mb-2">Template Variables</h3>
        <p className="text-color-secondary text-sm">
          Fill in the variables to customize the template content
        </p>
      </div>

      {template?.variables && template.variables.length > 0 ? (
        <div className="variables-form">
          {template.variables.map((variable, index) => (
            <div key={variable.name} className="field mb-4">
              <label 
                htmlFor={`var_${variable.name}`} 
                className="block mb-2 font-medium"
              >
                {variable.label}
                {variable.required && <span className="text-red-500 ml-1">*</span>}
                <Tag 
                  value={variable.type} 
                  className="ml-2 text-xs" 
                  severity="secondary"
                />
              </label>

              {renderVariableInput(variable)}

              {variable.description && (
                <small 
                  id={`var_${variable.name}_help`}
                  className="block mt-1 text-color-secondary"
                >
                  {variable.description}
                </small>
              )}

              {errors[variable.name] && (
                <small className="block mt-1 text-red-500">
                  {errors[variable.name]}
                </small>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="no-variables text-center py-8">
          <i className="pi pi-info-circle text-4xl text-color-secondary mb-3 block"></i>
          <h4 className="text-lg font-medium mb-2">No Variables Defined</h4>
          <p className="text-color-secondary">
            This template doesn't use any custom variables.
          </p>
        </div>
      )}
    </div>
  );

  const renderPreviewPanel = () => (
    <div className="preview-panel">
      <div className="panel-header mb-4">
        <div className="flex justify-content-between align-items-center">
          <div>
            <h3 className="text-xl font-semibold mb-1">Preview</h3>
            <p className="text-color-secondary text-sm">
              Live preview of your rendered template
            </p>
          </div>
          <div className="flex gap-2">
            <EnhancedButton
              icon="pi pi-refresh"
              size="small"
              variant="outlined"
              onClick={generatePreview}
              loading={loading}
              tooltip="Refresh Preview"
            />
            <EnhancedButton
              icon="pi pi-download"
              size="small"
              variant="outlined"
              onClick={() => handleExport('html')}
              tooltip="Export as HTML"
            />
            <EnhancedButton
              icon="pi pi-file-pdf"
              size="small"
              variant="outlined" 
              onClick={() => handleExport('pdf')}
              tooltip="Export as PDF"
            />
          </div>
        </div>
      </div>

      <Card className="preview-card">
        {loading && (
          <div className="preview-loading">
            <Skeleton height="2rem" className="mb-3" />
            <Skeleton height="1rem" className="mb-2" />
            <Skeleton height="1rem" className="mb-2" />
            <Skeleton height="1rem" width="60%" className="mb-3" />
            <Skeleton height="1rem" className="mb-2" />
            <Skeleton height="1rem" className="mb-2" />
          </div>
        )}

        {!loading && previewResult && (
          <div className="preview-content">
            {previewResult.missing_variables.length > 0 && (
              <Message 
                severity="warn" 
                className="mb-3"
                content={
                  <div>
                    <strong>Missing Variables:</strong>
                    <ul className="mt-2 mb-0">
                      {previewResult.missing_variables.map((variable, index) => (
                        <li key={index}>{variable}</li>
                      ))}
                    </ul>
                  </div>
                }
              />
            )}

            {Object.keys(previewResult.validation_errors).length > 0 && (
              <Message 
                severity="error" 
                className="mb-3"
                content={
                  <div>
                    <strong>Validation Errors:</strong>
                    <ul className="mt-2 mb-0">
                      {Object.entries(previewResult.validation_errors).map(([field, error], index) => (
                        <li key={index}><strong>{field}:</strong> {error}</li>
                      ))}
                    </ul>
                  </div>
                }
              />
            )}

            <div 
              className="rendered-content"
              dangerouslySetInnerHTML={{ __html: previewResult.rendered_content }}
            />
          </div>
        )}

        {!loading && !previewResult && (
          <div className="no-preview text-center py-8">
            <i className="pi pi-eye-slash text-4xl text-color-secondary mb-3 block"></i>
            <h4 className="text-lg font-medium mb-2">No Preview Available</h4>
            <p className="text-color-secondary">
              Fill in the template variables to generate a preview.
            </p>
          </div>
        )}
      </Card>
    </div>
  );

  const dialogHeader = (
    <div className="template-preview-header">
      <div className="flex align-items-center gap-3">
        <div className="template-info flex-1">
          <h2 className="text-2xl font-bold mb-1">{template?.name}</h2>
          <div className="template-meta flex align-items-center gap-2 text-sm text-color-secondary">
            <Badge value={template?.category} className="mr-2" />
            <Tag 
              value={template?.is_active ? 'Active' : 'Inactive'} 
              severity={template?.is_active ? 'success' : 'secondary'}
              className="mr-2"
            />
            {template?.is_system && (
              <Tag value="System" severity="info" className="mr-2" />
            )}
            <span>
              <i className="pi pi-users mr-1"></i>
              {template?.usage_count || 0} uses
            </span>
          </div>
        </div>
        <div className="template-actions flex gap-2">
          {onDuplicate && (
            <EnhancedButton
              icon="pi pi-copy"
              size="small"
              variant="outlined"
              onClick={() => template && onDuplicate(template)}
              tooltip="Duplicate Template"
            />
          )}
          {onEdit && (
            <EnhancedButton
              icon="pi pi-pencil"
              size="small"
              onClick={() => template && onEdit(template)}
              tooltip="Edit Template"
            />
          )}
        </div>
      </div>
    </div>
  );

  const dialogFooter = (
    <div className="flex justify-content-end gap-2">
      <EnhancedButton
        label="Close"
        variant="outlined"
        onClick={onClose}
      />
    </div>
  );

  return (
    <>
      <Toast ref={toast} />
      
      <Dialog
        header={dialogHeader}
        visible={isOpen}
        style={{ width: '95vw', maxWidth: '1400px' }}
        modal
        footer={dialogFooter}
        onHide={onClose}
        maximizable
        className="template-preview-dialog"
      >
        <div className="template-preview">
          {template?.description && (
            <div className="template-description mb-4 p-3 bg-blue-50 border-round">
              <p className="m-0 text-blue-800">{template.description}</p>
            </div>
          )}

          <Splitter className="preview-splitter">
            <SplitterPanel size={35} minSize={25}>
              <ScrollPanel style={{ width: '100%', height: '500px' }}>
                {renderVariablesPanel()}
              </ScrollPanel>
            </SplitterPanel>
            <SplitterPanel size={65} minSize={50}>
              <ScrollPanel style={{ width: '100%', height: '500px' }}>
                {renderPreviewPanel()}
              </ScrollPanel>
            </SplitterPanel>
          </Splitter>
        </div>
      </Dialog>
    </>
  );
};

export default TemplatePreview;