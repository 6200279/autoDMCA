import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Dialog } from 'primereact/dialog';
import { Steps } from 'primereact/steps';
import { Button } from 'primereact/button';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { EnhancedButton } from '../common/EnhancedButton';
import { templatesApi } from '../../services/api';
import {
  DMCATemplate,
  TemplateFormData,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  TemplatePreviewResponse,
  TemplateVariable
} from '../../types/templates';

// Import wizard step components
import { StepTypeSelection } from './wizard/StepTypeSelection';
import { StepBasicInfo } from './wizard/StepBasicInfo';
import { StepContentCreation } from './wizard/StepContentCreation';
import { StepVariableSetup } from './wizard/StepVariableSetup';
import { StepPreviewFinalize } from './wizard/StepPreviewFinalize';

import './TemplateCreationWizard.css';

export interface TemplateStarter {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  variables: TemplateVariable[];
  tags: string[];
  icon: string;
  jurisdiction: string;
  language: string;
}

export interface WizardFormData extends TemplateFormData {
  selectedStarter?: TemplateStarter;
  draftId?: string;
  lastSaved?: Date;
}

export interface TemplateCreationWizardProps {
  template?: DMCATemplate | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: DMCATemplate) => void;
  mode?: 'create' | 'edit' | 'duplicate';
}

const WIZARD_STEPS = [
  { 
    label: 'Template Type', 
    icon: 'pi pi-th-large',
    description: 'Choose template category and starter'
  },
  { 
    label: 'Basic Info', 
    icon: 'pi pi-info-circle',
    description: 'Name, description, and settings'
  },
  { 
    label: 'Content', 
    icon: 'pi pi-file-edit',
    description: 'Write your template content'
  },
  { 
    label: 'Variables', 
    icon: 'pi pi-tags',
    description: 'Configure dynamic variables'
  },
  { 
    label: 'Preview', 
    icon: 'pi pi-eye',
    description: 'Review and finalize template'
  }
];

const TemplateCreationWizard: React.FC<TemplateCreationWizardProps> = ({
  template,
  isOpen,
  onClose,
  onSave,
  mode = 'create'
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<WizardFormData>({
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
  const [previewResult, setPreviewResult] = useState<TemplatePreviewResponse | null>(null);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  const [lastAutoSave, setLastAutoSave] = useState<Date | null>(null);
  
  const toast = useRef<Toast>(null);
  const autoSaveTimer = useRef<NodeJS.Timeout | null>(null);

  // Initialize form data
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
    } else if (mode === 'create') {
      // Check for existing draft
      loadDraft();
    }
    
    setCurrentStep(0);
    setErrors({});
    setHasUnsavedChanges(false);
  }, [template, mode, isOpen]);

  // Auto-save functionality
  useEffect(() => {
    if (hasUnsavedChanges && autoSaveEnabled && mode === 'create') {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current);
      }
      
      autoSaveTimer.current = setTimeout(() => {
        saveDraft();
      }, 3000); // Auto-save after 3 seconds of inactivity
    }
    
    return () => {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current);
      }
    };
  }, [formData, hasUnsavedChanges, autoSaveEnabled, mode]);

  // Load draft from localStorage
  const loadDraft = () => {
    const draftKey = 'template_creation_draft';
    const savedDraft = localStorage.getItem(draftKey);
    
    if (savedDraft) {
      try {
        const draft = JSON.parse(savedDraft);
        if (draft.lastSaved && new Date().getTime() - new Date(draft.lastSaved).getTime() < 86400000) { // 24 hours
          setFormData(draft.data);
          setLastAutoSave(new Date(draft.lastSaved));
          
          toast.current?.show({
            severity: 'info',
            summary: 'Draft Restored',
            detail: 'Your previous work has been restored',
            life: 5000
          });
        }
      } catch (error) {
        console.error('Error loading draft:', error);
      }
    }
  };

  // Save draft to localStorage
  const saveDraft = async () => {
    if (mode !== 'create' || !formData.name) return;
    
    try {
      const draftKey = 'template_creation_draft';
      const draft = {
        data: formData,
        lastSaved: new Date().toISOString()
      };
      
      localStorage.setItem(draftKey, JSON.stringify(draft));
      setLastAutoSave(new Date());
      setHasUnsavedChanges(false);
      
      // Show subtle notification
      toast.current?.show({
        severity: 'success',
        summary: 'Draft Saved',
        detail: 'Your progress has been saved',
        life: 2000
      });
    } catch (error) {
      console.error('Error saving draft:', error);
    }
  };

  // Clear draft from localStorage
  const clearDraft = () => {
    const draftKey = 'template_creation_draft';
    localStorage.removeItem(draftKey);
    setLastAutoSave(null);
  };

  // Handle form data changes
  const handleFormChange = useCallback((updates: Partial<WizardFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
    setHasUnsavedChanges(true);
    
    // Clear related errors
    const newErrors = { ...errors };
    Object.keys(updates).forEach(key => {
      if (newErrors[key]) {
        delete newErrors[key];
      }
    });
    setErrors(newErrors);
  }, [errors]);

  // Validate current step
  const validateCurrentStep = (): boolean => {
    const stepErrors: Record<string, string> = {};
    
    switch (currentStep) {
      case 0: // Template Type Selection
        if (!formData.category) {
          stepErrors.category = 'Please select a template category';
        }
        break;
        
      case 1: // Basic Information
        if (!formData.name?.trim()) {
          stepErrors.name = 'Template name is required';
        } else if (formData.name.length < 3) {
          stepErrors.name = 'Template name must be at least 3 characters';
        } else if (formData.name.length > 100) {
          stepErrors.name = 'Template name cannot exceed 100 characters';
        }
        
        if (!formData.description?.trim()) {
          stepErrors.description = 'Description is required';
        } else if (formData.description.length > 500) {
          stepErrors.description = 'Description cannot exceed 500 characters';
        }
        break;
        
      case 2: // Content Creation
        if (!formData.content?.trim()) {
          stepErrors.content = 'Template content is required';
        } else if (formData.content.length < 50) {
          stepErrors.content = 'Template content must be at least 50 characters';
        }
        break;
        
      case 3: // Variable Setup
        formData.variables.forEach((variable, index) => {
          if (!variable.name.trim()) {
            stepErrors[`variable_${index}_name`] = 'Variable name is required';
          }
          if (!variable.label.trim()) {
            stepErrors[`variable_${index}_label`] = 'Variable label is required';
          }
          if (variable.name && !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(variable.name)) {
            stepErrors[`variable_${index}_name`] = 'Variable name must be a valid identifier';
          }
        });
        break;
    }
    
    setErrors(stepErrors);
    return Object.keys(stepErrors).length === 0;
  };

  // Navigate between steps
  const goToStep = (stepIndex: number) => {
    if (stepIndex < currentStep || validateCurrentStep()) {
      setCurrentStep(stepIndex);
    }
  };

  const goToNextStep = () => {
    if (validateCurrentStep() && currentStep < WIZARD_STEPS.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const goToPreviousStep = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  // Handle final save
  const handleSave = async () => {
    if (!validateCurrentStep()) {
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
          summary: 'Template Created',
          detail: 'Your template has been created successfully'
        });
        
        clearDraft();
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
          summary: 'Template Updated',
          detail: 'Your template has been updated successfully'
        });
      }
      
      setHasUnsavedChanges(false);
      onClose();
    } catch (error) {
      console.error('Error saving template:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Save Error',
        detail: 'Failed to save template. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle close with unsaved changes check
  const handleClose = () => {
    if (hasUnsavedChanges) {
      // This will be handled by the confirm dialog
      return;
    }
    onClose();
  };

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <StepTypeSelection
            formData={formData}
            errors={errors}
            onChange={handleFormChange}
          />
        );
      case 1:
        return (
          <StepBasicInfo
            formData={formData}
            errors={errors}
            onChange={handleFormChange}
          />
        );
      case 2:
        return (
          <StepContentCreation
            formData={formData}
            errors={errors}
            onChange={handleFormChange}
          />
        );
      case 3:
        return (
          <StepVariableSetup
            formData={formData}
            errors={errors}
            onChange={handleFormChange}
          />
        );
      case 4:
        return (
          <StepPreviewFinalize
            formData={formData}
            errors={errors}
            onChange={handleFormChange}
            previewResult={previewResult}
            onPreviewResult={setPreviewResult}
          />
        );
      default:
        return null;
    }
  };

  // Dialog footer with navigation buttons
  const dialogFooter = (
    <div className="wizard-footer flex justify-content-between align-items-center">
      <div className="flex align-items-center gap-3">
        {lastAutoSave && (
          <small className="text-color-secondary">
            Last saved: {lastAutoSave.toLocaleTimeString()}
          </small>
        )}
      </div>
      
      <div className="flex gap-2">
        <Button
          label="Cancel"
          icon="pi pi-times"
          className="p-button-outlined"
          onClick={handleClose}
          disabled={loading}
        />
        
        {currentStep > 0 && (
          <EnhancedButton
            label="Previous"
            icon="pi pi-chevron-left"
            variant="outlined"
            onClick={goToPreviousStep}
            disabled={loading}
          />
        )}
        
        {currentStep < WIZARD_STEPS.length - 1 ? (
          <EnhancedButton
            label="Next"
            icon="pi pi-chevron-right"
            iconPos="right"
            onClick={goToNextStep}
            disabled={loading}
          />
        ) : (
          <EnhancedButton
            label={mode === 'edit' ? 'Update Template' : 'Create Template'}
            icon="pi pi-check"
            onClick={handleSave}
            loading={loading}
          />
        )}
      </div>
    </div>
  );

  return (
    <>
      <Toast ref={toast} />
      
      <ConfirmDialog />
      
      <Dialog
        header={
          <div className="wizard-header">
            <h3 className="m-0">
              {mode === 'create' ? 'Create New Template' : 
               mode === 'duplicate' ? 'Duplicate Template' : 
               'Edit Template'}
            </h3>
            <p className="m-0 text-color-secondary">
              {WIZARD_STEPS[currentStep].description}
            </p>
          </div>
        }
        visible={isOpen}
        style={{ width: '95vw', maxWidth: '1000px' }}
        modal
        footer={dialogFooter}
        onHide={handleClose}
        maximizable
        className="template-wizard-dialog"
        dismissableMask={false}
      >
        <div className="template-creation-wizard">
          {/* Progress Steps */}
          <div className="wizard-steps-container mb-4">
            <Steps 
              model={WIZARD_STEPS.map((step, index) => ({
                label: step.label,
                icon: step.icon,
                command: () => goToStep(index)
              }))} 
              activeIndex={currentStep}
              className="wizard-steps"
            />
          </div>
          
          {/* Step Content */}
          <div className="wizard-step-content">
            {renderStepContent()}
          </div>
        </div>
      </Dialog>
    </>
  );
};

export default TemplateCreationWizard;