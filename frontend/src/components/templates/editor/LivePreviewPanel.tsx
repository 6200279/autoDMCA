import React, { useState, useCallback } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Calendar } from 'primereact/calendar';
import { InputNumber } from 'primereact/inputnumber';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { ProgressSpinner } from 'primereact/progressspinner';
import { ScrollPanel } from 'primereact/scrollpanel';
import { Panel } from 'primereact/panel';
import { TemplateVariable, TemplatePreviewResponse } from '../../../types/templates';

interface LivePreviewPanelProps {
  content: string;
  variables: TemplateVariable[];
  previewData: Record<string, any>;
  previewResult: TemplatePreviewResponse | null;
  loading: boolean;
  onPreviewDataChange: (data: Record<string, any>) => void;
  onRefreshPreview: () => void;
}

export const LivePreviewPanel: React.FC<LivePreviewPanelProps> = ({
  content,
  variables,
  previewData,
  previewResult,
  loading,
  onPreviewDataChange,
  onRefreshPreview
}) => {
  const [showVariables, setShowVariables] = useState(true);

  // Handle variable value changes
  const handleVariableChange = useCallback((variableName: string, value: any) => {
    onPreviewDataChange({
      ...previewData,
      [variableName]: value
    });
  }, [previewData, onPreviewDataChange]);

  // Render variable input based on type
  const renderVariableInput = (variable: TemplateVariable) => {
    const value = previewData[variable.name] || variable.default_value || '';

    switch (variable.type) {
      case 'textarea':
        return (
          <InputTextarea
            value={value}
            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
            placeholder={variable.placeholder}
            rows={3}
            className="w-full"
            autoResize
          />
        );

      case 'select':
        return (
          <Dropdown
            value={value}
            onChange={(e) => handleVariableChange(variable.name, e.value)}
            options={variable.options?.map(opt => ({ label: opt, value: opt })) || []}
            placeholder={variable.placeholder || `Select ${variable.label}`}
            className="w-full"
            showClear
          />
        );

      case 'date':
        return (
          <Calendar
            value={value ? new Date(value) : null}
            onChange={(e) => handleVariableChange(variable.name, e.value?.toISOString().split('T')[0])}
            placeholder={variable.placeholder}
            className="w-full"
            dateFormat="yy-mm-dd"
            showIcon
          />
        );

      case 'number':
        return (
          <InputNumber
            value={value ? parseFloat(value) : null}
            onChange={(e) => handleVariableChange(variable.name, e.value?.toString())}
            placeholder={variable.placeholder}
            className="w-full"
          />
        );

      case 'email':
      case 'url':
      case 'text':
      default:
        return (
          <InputText
            type={variable.type === 'email' ? 'email' : variable.type === 'url' ? 'url' : 'text'}
            value={value}
            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
            placeholder={variable.placeholder}
            className="w-full"
          />
        );
    }
  };

  // Get missing variables count
  const missingCount = previewResult?.missing_variables?.length || 0;
  const errorCount = Object.keys(previewResult?.validation_errors || {}).length;

  // Card header with status indicators
  const previewHeader = (
    <div className="preview-header">
      <div className="preview-title">
        <i className="pi pi-eye mr-2" />
        Live Preview
      </div>
      <div className="preview-status">
        {missingCount > 0 && (
          <Badge 
            value={`${missingCount} missing`} 
            severity="warning" 
            className="mr-2"
          />
        )}
        {errorCount > 0 && (
          <Badge 
            value={`${errorCount} errors`} 
            severity="danger" 
            className="mr-2"
          />
        )}
        <Button
          icon="pi pi-refresh"
          className="p-button-text p-button-sm"
          onClick={onRefreshPreview}
          loading={loading}
          tooltip="Refresh Preview"
          tooltipOptions={{ position: 'top' }}
        />
      </div>
    </div>
  );

  return (
    <div className="live-preview-panel">
      {/* Variables Panel */}
      <Panel
        header={`Preview Variables (${variables.length})`}
        collapsed={!showVariables}
        onToggle={(e) => setShowVariables(!e.value)}
        toggleable
        className="mb-3 variables-panel"
      >
        <div className="preview-variables">
          {variables.length === 0 ? (
            <div className="no-variables-message">
              <i className="pi pi-info-circle text-2xl mb-2 block text-color-secondary"></i>
              <p className="text-color-secondary m-0">No variables defined yet.</p>
              <p className="text-color-secondary text-sm m-0">Add variables to see preview controls here.</p>
            </div>
          ) : (
            <div className="variables-form">
              {variables.map((variable, index) => (
                <div key={index} className="field mb-3 variable-field">
                  <label 
                    htmlFor={`preview_${variable.name}`} 
                    className="block mb-2 font-medium variable-label"
                  >
                    {variable.label}
                    {variable.required && <span className="text-red-500 ml-1">*</span>}
                  </label>
                  
                  {renderVariableInput(variable)}
                  
                  {variable.description && (
                    <small className="block mt-1 text-color-secondary variable-description">
                      {variable.description}
                    </small>
                  )}
                  
                  {/* Validation feedback for this variable */}
                  {previewResult?.validation_errors?.[variable.name] && (
                    <small className="block mt-1 text-red-500">
                      {previewResult.validation_errors[variable.name]}
                    </small>
                  )}
                </div>
              ))}
              
              <div className="preview-actions mt-4">
                <Button
                  label="Update Preview"
                  icon="pi pi-refresh"
                  onClick={onRefreshPreview}
                  loading={loading}
                  className="w-full"
                  size="small"
                />
              </div>
            </div>
          )}
        </div>
      </Panel>

      {/* Preview Output */}
      <Card 
        header={previewHeader} 
        className="preview-output-card"
      >
        <div className="preview-content">
          {loading ? (
            <div className="preview-loading">
              <ProgressSpinner size="32px" />
              <p className="mt-2 text-color-secondary">Generating preview...</p>
            </div>
          ) : !content.trim() ? (
            <div className="preview-empty">
              <i className="pi pi-file-edit text-4xl mb-3 block text-color-secondary"></i>
              <p className="text-color-secondary m-0">Start typing your template content to see a live preview.</p>
            </div>
          ) : !previewResult ? (
            <div className="preview-prompt">
              <i className="pi pi-eye text-4xl mb-3 block text-color-secondary"></i>
              <p className="text-color-secondary mb-2">Fill in the variables above and click "Update Preview"</p>
              <p className="text-color-secondary text-sm m-0">to see how your template will look.</p>
            </div>
          ) : (
            <div className="preview-result">
              {/* Missing Variables Warning */}
              {previewResult.missing_variables.length > 0 && (
                <div className="preview-warning mb-3">
                  <div className="warning-header">
                    <i className="pi pi-exclamation-triangle text-orange-500 mr-2"></i>
                    <strong className="text-orange-700">Missing Variables</strong>
                  </div>
                  <ul className="warning-list mt-2 mb-0">
                    {previewResult.missing_variables.map((variable, index) => (
                      <li key={index} className="text-orange-600">
                        <code>{'{{' + variable + '}}'}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Validation Errors */}
              {Object.keys(previewResult.validation_errors).length > 0 && (
                <div className="preview-errors mb-3">
                  <div className="error-header">
                    <i className="pi pi-times-circle text-red-500 mr-2"></i>
                    <strong className="text-red-700">Validation Errors</strong>
                  </div>
                  <ul className="error-list mt-2 mb-0">
                    {Object.entries(previewResult.validation_errors).map(([field, error], index) => (
                      <li key={index} className="text-red-600">
                        <strong>{field}:</strong> {error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <Divider />
              
              {/* Rendered Content */}
              <div className="rendered-content">
                <ScrollPanel style={{ height: '300px' }}>
                  <div 
                    className="preview-html"
                    dangerouslySetInnerHTML={{ __html: previewResult.rendered_content }}
                  />
                </ScrollPanel>
              </div>
              
              {/* Preview Actions */}
              <div className="preview-footer mt-3">
                <div className="preview-stats">
                  <span className="text-color-secondary text-sm">
                    {previewResult.rendered_content.replace(/<[^>]*>/g, '').length} characters
                  </span>
                </div>
                <div className="preview-actions-right">
                  <Button
                    icon="pi pi-copy"
                    className="p-button-text p-button-sm"
                    tooltip="Copy to Clipboard"
                    onClick={() => {
                      navigator.clipboard.writeText(previewResult.rendered_content.replace(/<[^>]*>/g, ''));
                    }}
                  />
                  <Button
                    icon="pi pi-external-link"
                    className="p-button-text p-button-sm"
                    tooltip="Open in New Window"
                    onClick={() => {
                      const newWindow = window.open('', '_blank');
                      if (newWindow) {
                        newWindow.document.write(`
                          <html>
                            <head><title>Template Preview</title></head>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6; padding: 20px;">
                              ${previewResult.rendered_content}
                            </body>
                          </html>
                        `);
                        newWindow.document.close();
                      }
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      <style jsx>{`
        .live-preview-panel {
          height: 100%;
        }

        .preview-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }

        .preview-title {
          display: flex;
          align-items: center;
          font-weight: 600;
          color: var(--primary-color);
        }

        .preview-status {
          display: flex;
          align-items: center;
        }

        .variables-panel .p-panel-content {
          padding: 1rem;
        }

        .no-variables-message {
          text-align: center;
          padding: 2rem 1rem;
        }

        .variable-field {
          border-bottom: 1px solid var(--surface-border);
          padding-bottom: 1rem;
        }

        .variable-field:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }

        .variable-label {
          color: var(--text-color);
          font-size: 0.9rem;
        }

        .variable-description {
          font-style: italic;
          line-height: 1.4;
        }

        .preview-content {
          min-height: 200px;
        }

        .preview-loading,
        .preview-empty,
        .preview-prompt {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem 1rem;
          text-align: center;
        }

        .preview-warning,
        .preview-errors {
          background: var(--surface-100);
          border: 1px solid var(--orange-200);
          border-radius: 6px;
          padding: 1rem;
        }

        .preview-errors {
          border-color: var(--red-200);
        }

        .warning-header,
        .error-header {
          display: flex;
          align-items: center;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .warning-list,
        .error-list {
          list-style: none;
          padding-left: 1.5rem;
          margin: 0;
        }

        .warning-list li,
        .error-list li {
          margin-bottom: 0.25rem;
          font-size: 0.9rem;
        }

        .warning-list code,
        .error-list code {
          background: rgba(255, 255, 255, 0.8);
          padding: 0.125rem 0.25rem;
          border-radius: 3px;
          font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
        }

        .rendered-content {
          border: 1px solid var(--surface-border);
          border-radius: 6px;
          background: white;
        }

        .preview-html {
          padding: 1rem;
          line-height: 1.6;
          font-size: 0.9rem;
        }

        .preview-html p {
          margin-bottom: 1rem;
        }

        .preview-html h1,
        .preview-html h2,
        .preview-html h3 {
          margin-top: 1.5rem;
          margin-bottom: 0.75rem;
          color: var(--text-color);
        }

        .preview-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 0.75rem;
          border-top: 1px solid var(--surface-border);
        }

        .preview-stats {
          color: var(--text-color-secondary);
        }

        .preview-actions-right {
          display: flex;
          gap: 0.25rem;
        }

        /* Dark theme */
        .p-dark .preview-warning,
        .p-dark .preview-errors {
          background: var(--surface-800);
        }

        .p-dark .rendered-content {
          background: var(--surface-900);
          border-color: var(--surface-600);
        }

        .p-dark .preview-html {
          color: var(--text-color);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .preview-header {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
          }

          .preview-status {
            align-self: flex-end;
          }

          .preview-footer {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
          }

          .preview-actions-right {
            align-self: flex-end;
          }
        }
      `}</style>
    </div>
  );
};