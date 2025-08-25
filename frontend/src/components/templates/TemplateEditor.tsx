import React, { useState, useEffect, useCallback, useRef } from 'react';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Chips } from 'primereact/chips';
import { Checkbox } from 'primereact/checkbox';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Toast } from 'primereact/toast';
import { Divider } from 'primereact/divider';
import { TabView, TabPanel } from 'primereact/tabview';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Card } from 'primereact/card';
import { Tag } from 'primereact/tag';
import { Tooltip } from 'primereact/tooltip';
import { Editor } from 'primereact/editor';
import { EnhancedCard } from '../common/EnhancedCard';
import { EnhancedButton } from '../common/EnhancedButton';
import { templatesApi } from '../../services/api';
import {
  DMCATemplate,
  TemplateVariable,
  TemplateFormData,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  TemplatePreviewRequest,
  TemplatePreviewResponse,
  DEFAULT_CATEGORIES,
  SUPPORTED_LANGUAGES,
  JURISDICTIONS,
  VARIABLE_TYPES,
  TEMPLATE_VALIDATION_RULES
} from '../../types/templates';
import './TemplateEditor.css';

interface TemplateEditorProps {
  template?: DMCATemplate | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: DMCATemplate) => void;
  mode?: 'create' | 'edit' | 'duplicate';
}

const TemplateEditor: React.FC<TemplateEditorProps> = ({
  template,
  isOpen,
  onClose,
  onSave,
  mode = 'create'
}) => {
  const [formData, setFormData] = useState<TemplateFormData>({
    name: '',
    description: '',
    category: '',
    content: '',
    variables: [],
    tags: [],
    language: 'en',
    jurisdiction: 'US',
    is_active: true
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  
  // Variable editor state
  const [showVariableDialog, setShowVariableDialog] = useState(false);
  const [editingVariable, setEditingVariable] = useState<TemplateVariable | null>(null);
  const [variableFormData, setVariableFormData] = useState<TemplateVariable>({
    name: '',
    label: '',
    type: 'text',
    required: false,
    default_value: '',
    description: '',
    options: [],
    validation_pattern: '',
    placeholder: ''
  });

  // Preview state
  const [previewData, setPreviewData] = useState<Record<string, any>>({});
  const [previewResult, setPreviewResult] = useState<TemplatePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const toast = useRef<Toast>(null);
  const editorRef = useRef<any>(null);

  // Initialize form data when template changes
  useEffect(() => {
    if (template && (mode === 'edit' || mode === 'duplicate')) {
      setFormData({
        name: mode === 'duplicate' ? `${template.name} (Copy)` : template.name,
        description: template.description,
        category: template.category,
        content: template.content,
        variables: template.variables || [],
        tags: template.tags || [],
        language: template.language || 'en',
        jurisdiction: template.jurisdiction || 'US',
        is_active: template.is_active
      });
      
      // Initialize preview data with default values
      const initialPreview: Record<string, any> = {};
      template.variables?.forEach(variable => {
        if (variable.default_value) {
          initialPreview[variable.name] = variable.default_value;
        }
      });
      setPreviewData(initialPreview);
    } else if (mode === 'create') {
      setFormData({
        name: '',
        description: '',
        category: '',
        content: '',
        variables: [],
        tags: [],
        language: 'en',
        jurisdiction: 'US',
        is_active: true
      });
      setPreviewData({});
    }
    
    setErrors({});
    setHasUnsavedChanges(false);
  }, [template, mode]);

  // Track changes
  const handleFormChange = (field: keyof TemplateFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
    
    // Clear field error
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    TEMPLATE_VALIDATION_RULES.forEach(rule => {
      const value = formData[rule.field] as string;
      const [ruleName, ruleValue] = rule.rule.split(':');
      
      switch (ruleName) {
        case 'required':
          if (!value || value.toString().trim() === '') {
            newErrors[rule.field] = rule.message;
          }
          break;
        case 'minLength':
          if (value && value.length < parseInt(ruleValue)) {
            newErrors[rule.field] = rule.message;
          }
          break;
        case 'maxLength':
          if (value && value.length > parseInt(ruleValue)) {
            newErrors[rule.field] = rule.message;
          }
          break;
      }
    });

    // Validate variables
    formData.variables.forEach((variable, index) => {
      if (!variable.name.trim()) {
        newErrors[`variable_${index}_name`] = 'Variable name is required';
      }
      if (!variable.label.trim()) {
        newErrors[`variable_${index}_label`] = 'Variable label is required';
      }
      if (variable.name && !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(variable.name)) {
        newErrors[`variable_${index}_name`] = 'Variable name must be a valid identifier';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle save
  const handleSave = async () => {
    if (!validateForm()) {
      toast.current?.show({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'Please fix the errors before saving'
      });
      return;
    }

    setLoading(true);
    try {
      if (mode === 'create' || mode === 'duplicate') {
        const request: CreateTemplateRequest = {
          name: formData.name,
          description: formData.description,
          category: formData.category,
          content: formData.content,
          variables: formData.variables,
          tags: formData.tags,
          language: formData.language,
          jurisdiction: formData.jurisdiction,
          is_active: formData.is_active
        };
        
        const response = await templatesApi.createTemplate(request);
        onSave(response.data);
        
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: 'Template created successfully'
        });
      } else if (mode === 'edit' && template) {
        const request: UpdateTemplateRequest = {
          id: template.id,
          name: formData.name,
          description: formData.description,
          category: formData.category,
          content: formData.content,
          variables: formData.variables,
          tags: formData.tags,
          language: formData.language,
          jurisdiction: formData.jurisdiction,
          is_active: formData.is_active
        };
        
        const response = await templatesApi.updateTemplate(template.id, request);
        onSave(response.data);
        
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: 'Template updated successfully'
        });
      }
      
      setHasUnsavedChanges(false);
      onClose();
    } catch (error) {
      console.error('Error saving template:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to save template'
      });
    } finally {
      setLoading(false);
    }
  };

  // Variable management
  const handleAddVariable = () => {
    setEditingVariable(null);
    setVariableFormData({
      name: '',
      label: '',
      type: 'text',
      required: false,
      default_value: '',
      description: '',
      options: [],
      validation_pattern: '',
      placeholder: ''
    });
    setShowVariableDialog(true);
  };

  const handleEditVariable = (variable: TemplateVariable, index: number) => {
    setEditingVariable({ ...variable, index } as any);
    setVariableFormData(variable);
    setShowVariableDialog(true);
  };

  const handleSaveVariable = () => {
    if (!variableFormData.name.trim() || !variableFormData.label.trim()) {
      toast.current?.show({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'Variable name and label are required'
      });
      return;
    }

    const updatedVariables = [...formData.variables];
    if (editingVariable && 'index' in editingVariable) {
      updatedVariables[editingVariable.index as any] = variableFormData;
    } else {
      updatedVariables.push(variableFormData);
    }

    handleFormChange('variables', updatedVariables);
    setShowVariableDialog(false);
    setEditingVariable(null);
  };

  const handleDeleteVariable = (index: number) => {
    const updatedVariables = formData.variables.filter((_, i) => i !== index);
    handleFormChange('variables', updatedVariables);
  };

  // Template preview
  const handlePreview = async () => {
    if (!formData.content.trim()) return;

    setPreviewLoading(true);
    try {
      const request: TemplatePreviewRequest = {
        content: formData.content,
        variables: previewData
      };
      
      const response = await templatesApi.previewTemplate(request);
      setPreviewResult(response.data);
    } catch (error) {
      console.error('Error generating preview:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to generate preview'
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  // Auto-extract variables from content
  const handleExtractVariables = async () => {
    if (!formData.content.trim()) return;

    try {
      const response = await templatesApi.extractVariables(formData.content);
      const extractedVariables = response.data;
      
      // Merge with existing variables, avoiding duplicates
      const existingNames = new Set(formData.variables.map(v => v.name));
      const newVariables = extractedVariables.filter((v: any) => !existingNames.has(v.name));
      
      handleFormChange('variables', [...formData.variables, ...newVariables]);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: `Extracted ${newVariables.length} new variables`
      });
    } catch (error) {
      console.error('Error extracting variables:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to extract variables'
      });
    }
  };

  // Render preview variables form
  const renderPreviewVariables = () => (
    <div className="preview-variables">
      <h4 className="mb-3">Preview Variables</h4>
      {formData.variables.map((variable, index) => (
        <div key={index} className="field mb-3">
          <label htmlFor={`preview_${variable.name}`} className="block mb-2 font-medium">
            {variable.label}
            {variable.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          
          {variable.type === 'textarea' ? (
            <InputTextarea
              id={`preview_${variable.name}`}
              value={previewData[variable.name] || ''}
              onChange={(e) => setPreviewData(prev => ({
                ...prev,
                [variable.name]: e.target.value
              }))}
              placeholder={variable.placeholder}
              rows={3}
              className="w-full"
            />
          ) : variable.type === 'select' ? (
            <Dropdown
              id={`preview_${variable.name}`}
              value={previewData[variable.name] || ''}
              onChange={(e) => setPreviewData(prev => ({
                ...prev,
                [variable.name]: e.value
              }))}
              options={variable.options?.map(opt => ({ label: opt, value: opt })) || []}
              placeholder={variable.placeholder || `Select ${variable.label}`}
              className="w-full"
            />
          ) : (
            <InputText
              id={`preview_${variable.name}`}
              type={variable.type === 'email' ? 'email' : variable.type === 'url' ? 'url' : 'text'}
              value={previewData[variable.name] || ''}
              onChange={(e) => setPreviewData(prev => ({
                ...prev,
                [variable.name]: e.target.value
              }))}
              placeholder={variable.placeholder}
              className="w-full"
            />
          )}
          
          {variable.description && (
            <small className="block mt-1 text-color-secondary">
              {variable.description}
            </small>
          )}
        </div>
      ))}
      
      <EnhancedButton
        label="Update Preview"
        icon="pi pi-refresh"
        onClick={handlePreview}
        loading={previewLoading}
        className="mt-3"
        variant="outlined"
      />
    </div>
  );

  const dialogFooter = (
    <div className="flex justify-content-end gap-2">
      <EnhancedButton
        label="Cancel"
        variant="outlined"
        onClick={onClose}
        disabled={loading}
      />
      <EnhancedButton
        label="Save Template"
        icon="pi pi-save"
        onClick={handleSave}
        loading={loading}
      />
    </div>
  );

  const variableDialogFooter = (
    <div className="flex justify-content-end gap-2">
      <Button
        label="Cancel"
        className="p-button-outlined"
        onClick={() => setShowVariableDialog(false)}
      />
      <Button
        label="Save Variable"
        onClick={handleSaveVariable}
      />
    </div>
  );

  return (
    <>
      <Toast ref={toast} />
      
      <Dialog
        header={`${mode === 'create' ? 'Create' : mode === 'duplicate' ? 'Duplicate' : 'Edit'} Template`}
        visible={isOpen}
        style={{ width: '95vw', maxWidth: '1200px' }}
        modal
        footer={dialogFooter}
        onHide={onClose}
        maximizable
        className="template-editor-dialog"
      >
        <div className="template-editor">
          <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
            <TabPanel header="Basic Information" leftIcon="pi pi-info-circle">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <div className="field">
                    <label htmlFor="name" className="block mb-2 font-medium">
                      Template Name <span className="text-red-500">*</span>
                    </label>
                    <InputText
                      id="name"
                      value={formData.name}
                      onChange={(e) => handleFormChange('name', e.target.value)}
                      className={`w-full ${errors.name ? 'p-invalid' : ''}`}
                      placeholder="Enter template name"
                    />
                    {errors.name && <small className="p-error block mt-1">{errors.name}</small>}
                  </div>
                </div>
                
                <div className="col-12 md:col-6">
                  <div className="field">
                    <label htmlFor="category" className="block mb-2 font-medium">
                      Category <span className="text-red-500">*</span>
                    </label>
                    <Dropdown
                      id="category"
                      value={formData.category}
                      onChange={(e) => handleFormChange('category', e.value)}
                      options={DEFAULT_CATEGORIES.map(cat => ({ label: cat, value: cat }))}
                      placeholder="Select category"
                      className={`w-full ${errors.category ? 'p-invalid' : ''}`}
                      editable
                    />
                    {errors.category && <small className="p-error block mt-1">{errors.category}</small>}
                  </div>
                </div>

                <div className="col-12">
                  <div className="field">
                    <label htmlFor="description" className="block mb-2 font-medium">
                      Description <span className="text-red-500">*</span>
                    </label>
                    <InputTextarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => handleFormChange('description', e.target.value)}
                      rows={3}
                      className={`w-full ${errors.description ? 'p-invalid' : ''}`}
                      placeholder="Describe the purpose and usage of this template"
                    />
                    {errors.description && <small className="p-error block mt-1">{errors.description}</small>}
                  </div>
                </div>

                <div className="col-12 md:col-4">
                  <div className="field">
                    <label htmlFor="language" className="block mb-2 font-medium">
                      Language
                    </label>
                    <Dropdown
                      id="language"
                      value={formData.language}
                      onChange={(e) => handleFormChange('language', e.value)}
                      options={SUPPORTED_LANGUAGES}
                      placeholder="Select language"
                      className="w-full"
                    />
                  </div>
                </div>

                <div className="col-12 md:col-4">
                  <div className="field">
                    <label htmlFor="jurisdiction" className="block mb-2 font-medium">
                      Jurisdiction
                    </label>
                    <Dropdown
                      id="jurisdiction"
                      value={formData.jurisdiction}
                      onChange={(e) => handleFormChange('jurisdiction', e.value)}
                      options={JURISDICTIONS}
                      placeholder="Select jurisdiction"
                      className="w-full"
                    />
                  </div>
                </div>

                <div className="col-12 md:col-4">
                  <div className="field">
                    <label className="block mb-2 font-medium">Status</label>
                    <div className="flex align-items-center">
                      <Checkbox
                        id="is_active"
                        checked={formData.is_active}
                        onChange={(e) => handleFormChange('is_active', e.checked)}
                      />
                      <label htmlFor="is_active" className="ml-2">Active</label>
                    </div>
                  </div>
                </div>

                <div className="col-12">
                  <div className="field">
                    <label htmlFor="tags" className="block mb-2 font-medium">
                      Tags
                    </label>
                    <Chips
                      id="tags"
                      value={formData.tags}
                      onChange={(e) => handleFormChange('tags', e.value)}
                      placeholder="Add tags (press Enter)"
                      className="w-full"
                    />
                    <small className="block mt-1 text-color-secondary">
                      Add tags to help categorize and search for this template
                    </small>
                  </div>
                </div>
              </div>
            </TabPanel>

            <TabPanel header="Template Content" leftIcon="pi pi-file-edit">
              <div className="template-content-editor">
                <div className="flex justify-content-between align-items-center mb-3">
                  <h4 className="m-0">Template Content</h4>
                  <div className="flex gap-2">
                    <Button
                      label="Extract Variables"
                      icon="pi pi-code"
                      className="p-button-outlined p-button-sm"
                      onClick={handleExtractVariables}
                      tooltip="Automatically extract variables from template content"
                    />
                    <Button
                      label="Help"
                      icon="pi pi-question-circle"
                      className="p-button-text p-button-sm"
                      tooltip="Template syntax help"
                    />
                  </div>
                </div>

                <div className="field">
                  <Editor
                    ref={editorRef}
                    value={formData.content}
                    onTextChange={(e) => handleFormChange('content', e.htmlValue || '')}
                    style={{ height: '400px' }}
                    modules={{
                      toolbar: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link'],
                        ['clean']
                      ]
                    }}
                    placeholder="Enter your template content here. Use {{variable_name}} syntax for dynamic content."
                  />
                  {errors.content && <small className="p-error block mt-1">{errors.content}</small>}
                </div>

                <div className="template-syntax-help mt-3 p-3 bg-blue-50 border-round">
                  <h5 className="mt-0 mb-2 text-blue-700">Template Syntax</h5>
                  <ul className="mt-0 mb-0 text-blue-600 text-sm">
                    <li><strong>{'{{variable_name}}'}</strong> - Insert a variable value</li>
                    <li><strong>{'{{#if variable_name}}'}</strong> - Conditional content (requires variables setup)</li>
                    <li><strong>{'{{#each list_variable}}'}</strong> - Loop over arrays (requires variables setup)</li>
                    <li><strong>{'{{date}}'}</strong> - Current date</li>
                    <li><strong>{'{{time}}'}</strong> - Current time</li>
                  </ul>
                </div>
              </div>
            </TabPanel>

            <TabPanel header="Variables" leftIcon="pi pi-tags">
              <div className="template-variables">
                <div className="flex justify-content-between align-items-center mb-3">
                  <h4 className="m-0">Template Variables</h4>
                  <EnhancedButton
                    label="Add Variable"
                    icon="pi pi-plus"
                    size="small"
                    onClick={handleAddVariable}
                  />
                </div>

                {formData.variables.length === 0 ? (
                  <div className="text-center py-4 text-color-secondary">
                    <i className="pi pi-tags text-4xl mb-3 block"></i>
                    <p>No variables defined yet.</p>
                    <p>Variables make your templates dynamic by allowing customizable content.</p>
                  </div>
                ) : (
                  <DataTable value={formData.variables} responsiveLayout="scroll">
                    <Column field="name" header="Name" />
                    <Column field="label" header="Label" />
                    <Column 
                      field="type" 
                      header="Type" 
                      body={(variable) => (
                        <Tag value={variable.type} className="text-xs" />
                      )}
                    />
                    <Column 
                      field="required" 
                      header="Required" 
                      body={(variable) => variable.required ? 
                        <i className="pi pi-check text-green-500"></i> : 
                        <i className="pi pi-times text-red-500"></i>
                      }
                    />
                    <Column 
                      header="Actions"
                      body={(variable, options) => (
                        <div className="flex gap-1">
                          <Button
                            icon="pi pi-pencil"
                            className="p-button-text p-button-sm"
                            onClick={() => handleEditVariable(variable, options.rowIndex)}
                          />
                          <Button
                            icon="pi pi-trash"
                            className="p-button-text p-button-sm p-button-danger"
                            onClick={() => handleDeleteVariable(options.rowIndex)}
                          />
                        </div>
                      )}
                    />
                  </DataTable>
                )}
              </div>
            </TabPanel>

            <TabPanel header="Preview" leftIcon="pi pi-eye">
              <div className="template-preview">
                <Splitter>
                  <SplitterPanel size={30} minSize={20}>
                    {renderPreviewVariables()}
                  </SplitterPanel>
                  <SplitterPanel size={70} minSize={50}>
                    <Card title="Preview Output" className="h-full">
                      {previewResult ? (
                        <div className="template-preview-content">
                          {previewResult.missing_variables.length > 0 && (
                            <div className="mb-3 p-3 bg-yellow-50 border-left-3 border-yellow-500">
                              <h6 className="mt-0 mb-2 text-yellow-700">Missing Variables:</h6>
                              <ul className="mt-0 mb-0 text-yellow-600">
                                {previewResult.missing_variables.map((variable, index) => (
                                  <li key={index}>{variable}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {Object.keys(previewResult.validation_errors).length > 0 && (
                            <div className="mb-3 p-3 bg-red-50 border-left-3 border-red-500">
                              <h6 className="mt-0 mb-2 text-red-700">Validation Errors:</h6>
                              <ul className="mt-0 mb-0 text-red-600">
                                {Object.entries(previewResult.validation_errors).map(([field, error], index) => (
                                  <li key={index}><strong>{field}:</strong> {error}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          <div 
                            className="template-rendered-content"
                            dangerouslySetInnerHTML={{ __html: previewResult.rendered_content }}
                          />
                        </div>
                      ) : (
                        <div className="text-center py-4 text-color-secondary">
                          <i className="pi pi-eye text-4xl mb-3 block"></i>
                          <p>Fill in the variables and click "Update Preview" to see the rendered template.</p>
                        </div>
                      )}
                    </Card>
                  </SplitterPanel>
                </Splitter>
              </div>
            </TabPanel>
          </TabView>
        </div>
      </Dialog>

      {/* Variable Editor Dialog */}
      <Dialog
        header={editingVariable ? 'Edit Variable' : 'Add Variable'}
        visible={showVariableDialog}
        style={{ width: '600px' }}
        modal
        footer={variableDialogFooter}
        onHide={() => setShowVariableDialog(false)}
      >
        <div className="grid">
          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="var_name" className="block mb-2 font-medium">
                Variable Name <span className="text-red-500">*</span>
              </label>
              <InputText
                id="var_name"
                value={variableFormData.name}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full"
                placeholder="e.g., company_name"
              />
              <small className="block mt-1 text-color-secondary">
                Must be a valid identifier (letters, numbers, underscores only)
              </small>
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="var_label" className="block mb-2 font-medium">
                Label <span className="text-red-500">*</span>
              </label>
              <InputText
                id="var_label"
                value={variableFormData.label}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, label: e.target.value }))}
                className="w-full"
                placeholder="e.g., Company Name"
              />
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="var_type" className="block mb-2 font-medium">Type</label>
              <Dropdown
                id="var_type"
                value={variableFormData.type}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, type: e.value }))}
                options={VARIABLE_TYPES}
                className="w-full"
              />
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label className="block mb-2 font-medium">Required</label>
              <div className="flex align-items-center">
                <Checkbox
                  checked={variableFormData.required}
                  onChange={(e) => setVariableFormData(prev => ({ ...prev, required: e.checked }))}
                />
                <label className="ml-2">This field is required</label>
              </div>
            </div>
          </div>

          <div className="col-12">
            <div className="field">
              <label htmlFor="var_description" className="block mb-2 font-medium">Description</label>
              <InputTextarea
                id="var_description"
                value={variableFormData.description}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, description: e.target.value }))}
                rows={2}
                className="w-full"
                placeholder="Describe what this variable is used for"
              />
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="var_placeholder" className="block mb-2 font-medium">Placeholder</label>
              <InputText
                id="var_placeholder"
                value={variableFormData.placeholder}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, placeholder: e.target.value }))}
                className="w-full"
                placeholder="Hint text for users"
              />
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="var_default" className="block mb-2 font-medium">Default Value</label>
              <InputText
                id="var_default"
                value={variableFormData.default_value}
                onChange={(e) => setVariableFormData(prev => ({ ...prev, default_value: e.target.value }))}
                className="w-full"
                placeholder="Default value (optional)"
              />
            </div>
          </div>

          {variableFormData.type === 'select' && (
            <div className="col-12">
              <div className="field">
                <label htmlFor="var_options" className="block mb-2 font-medium">Options</label>
                <Chips
                  id="var_options"
                  value={variableFormData.options || []}
                  onChange={(e) => setVariableFormData(prev => ({ ...prev, options: e.value }))}
                  placeholder="Add options (press Enter)"
                  className="w-full"
                />
                <small className="block mt-1 text-color-secondary">
                  Add each option and press Enter
                </small>
              </div>
            </div>
          )}
        </div>
      </Dialog>
    </>
  );
};

export default TemplateEditor;