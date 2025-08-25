import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Toast } from 'primereact/toast';
import { Toolbar } from 'primereact/toolbar';
import { Badge } from 'primereact/badge';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Chip } from 'primereact/chip';
import { Divider } from 'primereact/divider';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Chips } from 'primereact/chips';
import { Checkbox } from 'primereact/checkbox';
import { Panel } from 'primereact/panel';
import { ScrollPanel } from 'primereact/scrollpanel';
import { EditorToolbar } from './editor/EditorToolbar';
import { VariableInserter } from './editor/VariableInserter';
import { LivePreviewPanel } from './editor/LivePreviewPanel';
import { ValidationPanel } from './editor/ValidationPanel';
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
import './EnhancedTemplateEditor.css';

interface EnhancedTemplateEditorProps {
  template?: DMCATemplate | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: DMCATemplate) => void;
  mode?: 'create' | 'edit' | 'duplicate';
}

interface EditorState {
  content: string;
  cursorPosition: number;
  history: string[];
  historyIndex: number;
  lastSaved: Date | null;
  hasUnsavedChanges: boolean;
}

interface AutoSaveState {
  saving: boolean;
  lastSaved: Date | null;
  error: string | null;
}

const AUTOSAVE_DELAY = 3000; // 3 seconds
const MAX_HISTORY_LENGTH = 50;

export const EnhancedTemplateEditor: React.FC<EnhancedTemplateEditorProps> = ({
  template,
  isOpen,
  onClose,
  onSave,
  mode = 'create'
}) => {
  // Core state
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

  // Editor state
  const [editorState, setEditorState] = useState<EditorState>({
    content: '',
    cursorPosition: 0,
    history: [],
    historyIndex: -1,
    lastSaved: null,
    hasUnsavedChanges: false
  });

  // Auto-save state
  const [autoSaveState, setAutoSaveState] = useState<AutoSaveState>({
    saving: false,
    lastSaved: null,
    error: null
  });

  // UI state
  const [leftPanelSize, setLeftPanelSize] = useState(60);
  const [rightPanelSize, setRightPanelSize] = useState(40);
  const [showMetadata, setShowMetadata] = useState(true);
  const [showVariables, setShowVariables] = useState(true);
  const [showValidation, setShowValidation] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Preview state
  const [previewData, setPreviewData] = useState<Record<string, any>>({});
  const [previewResult, setPreviewResult] = useState<TemplatePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Variable dialog state
  const [showVariableDialog, setShowVariableDialog] = useState(false);
  const [editingVariable, setEditingVariable] = useState<TemplateVariable | null>(null);

  // Refs
  const toast = useRef<Toast>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previewTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize form data when template changes
  useEffect(() => {
    if (template && (mode === 'edit' || mode === 'duplicate')) {
      const newFormData = {
        name: mode === 'duplicate' ? `${template.name} (Copy)` : template.name,
        description: template.description,
        category: template.category,
        content: template.content,
        variables: template.variables || [],
        tags: template.tags || [],
        language: template.language || 'en',
        jurisdiction: template.jurisdiction || 'US',
        is_active: template.is_active
      };
      
      setFormData(newFormData);
      setEditorState(prev => ({
        ...prev,
        content: template.content,
        history: [template.content],
        historyIndex: 0,
        hasUnsavedChanges: false
      }));
      
      // Initialize preview data with default values
      const initialPreview: Record<string, any> = {};
      template.variables?.forEach(variable => {
        if (variable.default_value) {
          initialPreview[variable.name] = variable.default_value;
        }
      });
      setPreviewData(initialPreview);
    } else if (mode === 'create') {
      const newFormData = {
        name: '',
        description: '',
        category: '',
        content: '',
        variables: [],
        tags: [],
        language: 'en',
        jurisdiction: 'US',
        is_active: true
      };
      
      setFormData(newFormData);
      setEditorState(prev => ({
        ...prev,
        content: '',
        history: [''],
        historyIndex: 0,
        hasUnsavedChanges: false
      }));
      setPreviewData({});
    }
    
    setErrors({});
    setAutoSaveState({
      saving: false,
      lastSaved: null,
      error: null
    });
  }, [template, mode]);

  // Handle content changes with history tracking
  const handleContentChange = useCallback((newContent: string, addToHistory: boolean = true) => {
    setFormData(prev => ({ ...prev, content: newContent }));
    
    setEditorState(prev => {
      const newHistory = addToHistory 
        ? [...prev.history.slice(0, prev.historyIndex + 1), newContent].slice(-MAX_HISTORY_LENGTH)
        : prev.history;
      const newHistoryIndex = addToHistory ? newHistory.length - 1 : prev.historyIndex;
      
      return {
        ...prev,
        content: newContent,
        history: newHistory,
        historyIndex: newHistoryIndex,
        hasUnsavedChanges: true
      };
    });

    // Clear any existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    // Set new auto-save timeout
    autoSaveTimeoutRef.current = setTimeout(() => {
      handleAutoSave(newContent);
    }, AUTOSAVE_DELAY);

    // Schedule preview update
    if (previewTimeoutRef.current) {
      clearTimeout(previewTimeoutRef.current);
    }
    previewTimeoutRef.current = setTimeout(() => {
      handlePreviewUpdate();
    }, 1000);
  }, []);

  // Auto-save functionality
  const handleAutoSave = useCallback(async (content: string) => {
    if (mode === 'create' || !template) return; // Only auto-save for existing templates

    setAutoSaveState(prev => ({ ...prev, saving: true, error: null }));

    try {
      const request: UpdateTemplateRequest = {
        id: template.id,
        content,
        // Include other form data to maintain consistency
        ...formData
      };
      
      await templatesApi.updateTemplate(template.id, request);
      
      setAutoSaveState({
        saving: false,
        lastSaved: new Date(),
        error: null
      });
      
      setEditorState(prev => ({
        ...prev,
        hasUnsavedChanges: false
      }));
    } catch (error) {
      console.error('Auto-save failed:', error);
      setAutoSaveState(prev => ({
        ...prev,
        saving: false,
        error: 'Auto-save failed'
      }));
    }
  }, [template, mode, formData]);

  // Undo/Redo functionality
  const handleUndo = useCallback(() => {
    setEditorState(prev => {
      if (prev.historyIndex > 0) {
        const newIndex = prev.historyIndex - 1;
        const content = prev.history[newIndex];
        setFormData(current => ({ ...current, content }));
        return {
          ...prev,
          content,
          historyIndex: newIndex,
          hasUnsavedChanges: true
        };
      }
      return prev;
    });
  }, []);

  const handleRedo = useCallback(() => {
    setEditorState(prev => {
      if (prev.historyIndex < prev.history.length - 1) {
        const newIndex = prev.historyIndex + 1;
        const content = prev.history[newIndex];
        setFormData(current => ({ ...current, content }));
        return {
          ...prev,
          content,
          historyIndex: newIndex,
          hasUnsavedChanges: true
        };
      }
      return prev;
    });
  }, []);

  // Variable insertion
  const handleInsertVariable = useCallback((variableName: string) => {
    const textarea = editorRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const currentContent = formData.content;
    const beforeCursor = currentContent.substring(0, cursorPosition);
    const afterCursor = currentContent.substring(cursorPosition);
    const newContent = `${beforeCursor}{{${variableName}}}${afterCursor}`;
    
    handleContentChange(newContent);

    // Set cursor position after the inserted variable
    setTimeout(() => {
      const newPosition = cursorPosition + variableName.length + 4; // 4 for {{}}
      textarea.setSelectionRange(newPosition, newPosition);
      textarea.focus();
    }, 0);
  }, [formData.content, handleContentChange]);

  // Preview update
  const handlePreviewUpdate = useCallback(async () => {
    if (!formData.content.trim()) {
      setPreviewResult(null);
      return;
    }

    setPreviewLoading(true);
    try {
      const request: TemplatePreviewRequest = {
        content: formData.content,
        variables: formData.variables,
        values: previewData
      };
      
      const response = await templatesApi.previewTemplate(request);
      setPreviewResult(response.data);
    } catch (error) {
      console.error('Preview failed:', error);
      setPreviewResult(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [formData.content, formData.variables, previewData]);

  // Form field changes
  const handleFormChange = useCallback((field: keyof TemplateFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear field error
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  // Variable management
  const handleAddVariable = useCallback(() => {
    setEditingVariable(null);
    setShowVariableDialog(true);
  }, []);

  const handleEditVariable = useCallback((variable: TemplateVariable, index: number) => {
    setEditingVariable({ ...variable, index } as any);
    setShowVariableDialog(true);
  }, []);

  const handleDeleteVariable = useCallback((index: number) => {
    const updatedVariables = formData.variables.filter((_, i) => i !== index);
    handleFormChange('variables', updatedVariables);
  }, [formData.variables, handleFormChange]);

  // Validation
  const validateForm = useCallback((): boolean => {
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

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  // Save handler
  const handleSave = useCallback(async () => {
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
      
      setEditorState(prev => ({ ...prev, hasUnsavedChanges: false }));
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
  }, [formData, mode, template, validateForm, onSave, onClose]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        handleRedo();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleSave, handleUndo, handleRedo]);

  // Cleanup timeouts
  useEffect(() => {
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current);
      }
    };
  }, []);

  // Memoized validation results
  const validationResults = useMemo(() => {
    return TEMPLATE_VALIDATION_RULES.map(rule => ({
      ...rule,
      isValid: !errors[rule.field],
      error: errors[rule.field]
    }));
  }, [errors]);

  const dialogFooter = (
    <div className="enhanced-template-editor-footer">
      <div className="footer-left">
        {autoSaveState.saving && (
          <div className="auto-save-indicator">
            <ProgressSpinner size="16px" />
            <span className="ml-2">Saving...</span>
          </div>
        )}
        {autoSaveState.lastSaved && (
          <div className="auto-save-status">
            <i className="pi pi-check text-green-500 mr-1" />
            <span>Saved {autoSaveState.lastSaved.toLocaleTimeString()}</span>
          </div>
        )}
        {autoSaveState.error && (
          <div className="auto-save-error">
            <i className="pi pi-exclamation-triangle text-orange-500 mr-1" />
            <span>{autoSaveState.error}</span>
          </div>
        )}
      </div>
      
      <div className="footer-right">
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
          className="ml-2"
        />
      </div>
    </div>
  );

  return (
    <>
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <Dialog
        header={
          <div className="enhanced-template-editor-header">
            <div className="header-title">
              <i className="pi pi-file-edit mr-2" />
              {`${mode === 'create' ? 'Create' : mode === 'duplicate' ? 'Duplicate' : 'Edit'} Template`}
            </div>
            <div className="header-badges">
              {editorState.hasUnsavedChanges && (
                <Badge value="Unsaved" severity="warning" />
              )}
              {mode === 'edit' && (
                <Chip 
                  label={template?.language || 'en'} 
                  className="ml-2 text-xs"
                />
              )}
            </div>
          </div>
        }
        visible={isOpen}
        style={{ width: '95vw', maxWidth: '1400px', height: '90vh' }}
        modal
        footer={dialogFooter}
        onHide={onClose}
        maximizable
        className="enhanced-template-editor-dialog"
        contentStyle={{ padding: '0' }}
      >
        <div className="enhanced-template-editor">
          {/* Editor Toolbar */}
          <EditorToolbar
            canUndo={editorState.historyIndex > 0}
            canRedo={editorState.historyIndex < editorState.history.length - 1}
            onUndo={handleUndo}
            onRedo={handleRedo}
            onSave={handleSave}
            hasUnsavedChanges={editorState.hasUnsavedChanges}
          />
          
          <Divider className="m-0" />
          
          {/* Main Editor Layout */}
          <div className="editor-main-content">
            <Splitter 
              style={{ height: 'calc(100vh - 200px)' }}
              onResizeEnd={(e) => {
                setLeftPanelSize(e.sizes[0]);
                setRightPanelSize(e.sizes[1]);
              }}
            >
              {/* Left Panel - Editor */}
              <SplitterPanel size={leftPanelSize} minSize={40}>
                <div className="editor-left-panel">
                  {/* Metadata Panel */}
                  <Panel 
                    header="Template Metadata" 
                    collapsed={!showMetadata}
                    onToggle={(e) => setShowMetadata(!e.value)}
                    toggleable
                    className="mb-3"
                  >
                    <div className="grid">
                      <div className="col-12 md:col-6">
                        <div className="field">
                          <label htmlFor="name" className="block mb-2 font-medium">
                            Name <span className="text-red-500">*</span>
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
                            rows={2}
                            className={`w-full ${errors.description ? 'p-invalid' : ''}`}
                            placeholder="Describe the purpose and usage of this template"
                          />
                          {errors.description && <small className="p-error block mt-1">{errors.description}</small>}
                        </div>
                      </div>
                    </div>
                  </Panel>
                  
                  {/* Content Editor */}
                  <Card title="Template Content" className="editor-content-card">
                    <div className="editor-content-wrapper">
                      <VariableInserter
                        variables={formData.variables}
                        onInsertVariable={handleInsertVariable}
                      />
                      
                      <div className="editor-textarea-wrapper">
                        <InputTextarea
                          ref={editorRef}
                          value={formData.content}
                          onChange={(e) => handleContentChange(e.target.value)}
                          className={`editor-textarea ${errors.content ? 'p-invalid' : ''}`}
                          placeholder="Enter your template content here. Use {{variable_name}} syntax for dynamic content."
                          rows={20}
                          style={{ 
                            fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                            fontSize: '14px',
                            lineHeight: '1.5'
                          }}
                        />
                        {errors.content && <small className="p-error block mt-1">{errors.content}</small>}
                      </div>
                      
                      <div className="editor-status-bar">
                        <div className="status-left">
                          <span>Lines: {formData.content.split('\n').length}</span>
                          <span className="ml-3">Characters: {formData.content.length}</span>
                          <span className="ml-3">Variables: {formData.variables.length}</span>
                        </div>
                        <div className="status-right">
                          {editorState.hasUnsavedChanges && (
                            <span className="unsaved-indicator">
                              <i className="pi pi-circle-fill text-orange-500 mr-1" />
                              Unsaved
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>
              </SplitterPanel>
              
              {/* Right Panel - Preview and Tools */}
              <SplitterPanel size={rightPanelSize} minSize={30}>
                <div className="editor-right-panel">
                  <ScrollPanel style={{ height: '100%' }}>
                    {/* Live Preview */}
                    <LivePreviewPanel
                      content={formData.content}
                      variables={formData.variables}
                      previewData={previewData}
                      previewResult={previewResult}
                      loading={previewLoading}
                      onPreviewDataChange={setPreviewData}
                      onRefreshPreview={handlePreviewUpdate}
                    />
                    
                    {/* Variable Management */}
                    <Panel 
                      header={`Variables (${formData.variables.length})`}
                      collapsed={!showVariables}
                      onToggle={(e) => setShowVariables(!e.value)}
                      toggleable
                      className="mt-3"
                    >
                      <div className="variable-management">
                        <div className="flex justify-content-between align-items-center mb-3">
                          <span className="text-color-secondary">Manage template variables</span>
                          <Button
                            label="Add Variable"
                            icon="pi pi-plus"
                            size="small"
                            onClick={handleAddVariable}
                          />
                        </div>
                        
                        {formData.variables.length === 0 ? (
                          <div className="text-center py-3 text-color-secondary">
                            <i className="pi pi-tags text-2xl mb-2 block"></i>
                            <p className="m-0">No variables defined</p>
                          </div>
                        ) : (
                          <div className="variables-list">
                            {formData.variables.map((variable, index) => (
                              <div key={index} className="variable-item">
                                <div className="variable-info">
                                  <div className="variable-name">{variable.name}</div>
                                  <div className="variable-label">{variable.label}</div>
                                  <div className="variable-meta">
                                    <Chip 
                                      label={variable.type} 
                                      className="mr-1 text-xs"
                                    />
                                    {variable.required && (
                                      <Chip 
                                        label="Required" 
                                        severity="warning"
                                        className="text-xs"
                                      />
                                    )}
                                  </div>
                                </div>
                                <div className="variable-actions">
                                  <Button
                                    icon="pi pi-pencil"
                                    className="p-button-text p-button-sm"
                                    onClick={() => handleEditVariable(variable, index)}
                                  />
                                  <Button
                                    icon="pi pi-trash"
                                    className="p-button-text p-button-sm p-button-danger"
                                    onClick={() => handleDeleteVariable(index)}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </Panel>
                    
                    {/* Validation Panel */}
                    <ValidationPanel
                      validationResults={validationResults}
                      collapsed={!showValidation}
                      onToggle={setShowValidation}
                    />
                  </ScrollPanel>
                </div>
              </SplitterPanel>
            </Splitter>
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default EnhancedTemplateEditor;