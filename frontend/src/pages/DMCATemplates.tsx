import React, { useState, useCallback } from 'react';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Dialog } from 'primereact/dialog';
import { Button } from 'primereact/button';
import { Divider } from 'primereact/divider';
import { TemplateLibraryDashboard, TemplateCreationWizard, EnhancedTemplateEditor, TemplatePreview } from '../components/templates';
import { DMCATemplate } from '../types/templates';
import './DMCATemplates.css';

type EditorMode = 'create' | 'edit' | 'duplicate';

interface EditorState {
  isOpen: boolean;
  mode: EditorMode;
  template: DMCATemplate | null;
}

interface PreviewState {
  isOpen: boolean;
  template: DMCATemplate | null;
}

const DMCATemplates: React.FC = () => {
  const [editorState, setEditorState] = useState<EditorState>({
    isOpen: false,
    mode: 'create',
    template: null
  });

  const [enhancedEditorState, setEnhancedEditorState] = useState<EditorState>({
    isOpen: false,
    mode: 'create',
    template: null
  });

  const [previewState, setPreviewState] = useState<PreviewState>({
    isOpen: false,
    template: null
  });

  const [showEditorSelection, setShowEditorSelection] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Refresh dashboard when templates are modified
  const triggerRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  // Template creation - show editor selection dialog
  const handleCreateTemplate = useCallback(() => {
    setShowEditorSelection(true);
  }, []);

  // Editor selection handlers
  const handleUseWizard = useCallback(() => {
    setShowEditorSelection(false);
    setEditorState({
      isOpen: true,
      mode: 'create',
      template: null
    });
  }, []);

  const handleUseEnhancedEditor = useCallback(() => {
    setShowEditorSelection(false);
    setEnhancedEditorState({
      isOpen: true,
      mode: 'create',
      template: null
    });
  }, []);

  // Template editing - use enhanced editor by default
  const handleEditTemplate = useCallback((template: DMCATemplate) => {
    setEnhancedEditorState({
      isOpen: true,
      mode: 'edit',
      template
    });
  }, []);

  // Template duplication - use enhanced editor by default
  const handleDuplicateTemplate = useCallback((template: DMCATemplate) => {
    setEnhancedEditorState({
      isOpen: true,
      mode: 'duplicate',
      template
    });
  }, []);

  // Template preview
  const handleViewTemplate = useCallback((template: DMCATemplate) => {
    setPreviewState({
      isOpen: true,
      template
    });
  }, []);

  // Editor handlers
  const handleEditorClose = useCallback(() => {
    setEditorState({
      isOpen: false,
      mode: 'create',
      template: null
    });
  }, []);

  const handleEditorSave = useCallback((template: DMCATemplate) => {
    triggerRefresh();
    handleEditorClose();
  }, [triggerRefresh, handleEditorClose]);

  // Enhanced Editor handlers
  const handleEnhancedEditorClose = useCallback(() => {
    setEnhancedEditorState({
      isOpen: false,
      mode: 'create',
      template: null
    });
  }, []);

  const handleEnhancedEditorSave = useCallback((template: DMCATemplate) => {
    triggerRefresh();
    handleEnhancedEditorClose();
  }, [triggerRefresh, handleEnhancedEditorClose]);

  // Preview handlers
  const handlePreviewClose = useCallback(() => {
    setPreviewState({
      isOpen: false,
      template: null
    });
  }, []);

  const handlePreviewEdit = useCallback((template: DMCATemplate) => {
    setPreviewState({
      isOpen: false,
      template: null
    });
    handleEditTemplate(template);
  }, [handleEditTemplate]);

  const handlePreviewDuplicate = useCallback((template: DMCATemplate) => {
    setPreviewState({
      isOpen: false,
      template: null
    });
    handleDuplicateTemplate(template);
  }, [handleDuplicateTemplate]);

  return (
    <div className="dmca-templates-page">
      <Toast />
      <ConfirmDialog />
      
      {/* Main Dashboard */}
      <TemplateLibraryDashboard
        key={refreshTrigger} // Force refresh when templates change
        onTemplateCreate={handleCreateTemplate}
        onTemplateEdit={handleEditTemplate}
        onTemplateView={handleViewTemplate}
      />

      {/* Editor Selection Dialog */}
      <Dialog
        header="Choose Template Editor"
        visible={showEditorSelection}
        style={{ width: '500px' }}
        modal
        onHide={() => setShowEditorSelection(false)}
        className="editor-selection-dialog"
      >
        <div className="editor-selection-content">
          <p className="mb-4 text-color-secondary">
            Choose how you'd like to create your template:
          </p>
          
          <div className="editor-options">
            <div 
              className="editor-option"
              onClick={handleUseEnhancedEditor}
            >
              <div className="option-header">
                <i className="pi pi-code text-primary text-2xl"></i>
                <h4 className="option-title">Enhanced Editor</h4>
                <span className="option-badge">Recommended</span>
              </div>
              <p className="option-description">
                Modern editor with live preview, real-time validation, auto-save, 
                and advanced editing features. Perfect for power users and complex templates.
              </p>
              <div className="option-features">
                <span className="feature-tag">Live Preview</span>
                <span className="feature-tag">Auto-save</span>
                <span className="feature-tag">Syntax Highlighting</span>
                <span className="feature-tag">Validation</span>
              </div>
            </div>
            
            <Divider />
            
            <div 
              className="editor-option"
              onClick={handleUseWizard}
            >
              <div className="option-header">
                <i className="pi pi-list-check text-secondary text-2xl"></i>
                <h4 className="option-title">Creation Wizard</h4>
              </div>
              <p className="option-description">
                Step-by-step guided process that walks you through creating a template. 
                Great for beginners or when you need structured guidance.
              </p>
              <div className="option-features">
                <span className="feature-tag">Step-by-step</span>
                <span className="feature-tag">Guided</span>
                <span className="feature-tag">Beginner Friendly</span>
              </div>
            </div>
          </div>
        </div>
      </Dialog>

      {/* Template Creation Wizard Dialog */}
      <TemplateCreationWizard
        template={editorState.template}
        isOpen={editorState.isOpen}
        mode={editorState.mode}
        onClose={handleEditorClose}
        onSave={handleEditorSave}
      />

      {/* Enhanced Template Editor Dialog */}
      <EnhancedTemplateEditor
        template={enhancedEditorState.template}
        isOpen={enhancedEditorState.isOpen}
        mode={enhancedEditorState.mode}
        onClose={handleEnhancedEditorClose}
        onSave={handleEnhancedEditorSave}
      />

      {/* Template Preview Dialog */}
      <TemplatePreview
        template={previewState.template}
        isOpen={previewState.isOpen}
        onClose={handlePreviewClose}
        onEdit={handlePreviewEdit}
        onDuplicate={handlePreviewDuplicate}
      />
    </div>
  );
};

export default DMCATemplates;