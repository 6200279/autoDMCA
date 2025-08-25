import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { EnhancedTemplateEditor } from '../EnhancedTemplateEditor';
import { templatesApi } from '../../../services/api';
import { DMCATemplate, TemplateVariable } from '../../../types/templates';
import '@testing-library/jest-dom';

// Mock the API
vi.mock('../../../services/api', () => ({
  templatesApi: {
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    getTemplatePreview: vi.fn(),
    validateTemplate: vi.fn(),
    saveDraft: vi.fn(),
  }
}));

// Mock the validation service
vi.mock('../../../services/dmcaTemplateValidator', () => ({
  validateDMCATemplate: vi.fn().mockReturnValue({
    isValid: true,
    errors: [],
    warnings: [],
    complianceScore: 85,
    requiredElements: []
  }),
  generateTemplatePreview: vi.fn().mockReturnValue('Preview content'),
  analyzeTemplateEffectiveness: vi.fn().mockReturnValue({
    score: 85,
    strengths: ['Professional tone'],
    improvements: ['Add more specific details']
  })
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue(''),
  },
});

// Test data factories
const createMockTemplate = (overrides: Partial<DMCATemplate> = {}): DMCATemplate => ({
  id: 'template-1',
  name: 'Test Template',
  description: 'A test template',
  category: 'General DMCA',
  content: 'Dear {{platform}},\n\nI am writing to report copyright infringement of my work titled "{{work_title}}"...',
  variables: [
    {
      name: 'platform',
      label: 'Platform Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., YouTube'
    },
    {
      name: 'work_title',
      label: 'Work Title',
      type: 'text',
      required: true,
      placeholder: 'Title of your copyrighted work'
    }
  ],
  is_active: true,
  is_system: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  tags: ['general'],
  language: 'en',
  jurisdiction: 'US',
  ...overrides
});

const createMockVariable = (overrides: Partial<TemplateVariable> = {}): TemplateVariable => ({
  name: 'test_var',
  label: 'Test Variable',
  type: 'text',
  required: false,
  placeholder: 'Enter value',
  ...overrides
});

describe('EnhancedTemplateEditor', () => {
  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn(),
    mode: 'create' as const,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default API responses
    (templatesApi.createTemplate as any).mockResolvedValue(createMockTemplate());
    (templatesApi.updateTemplate as any).mockResolvedValue(createMockTemplate());
    (templatesApi.getTemplatePreview as any).mockResolvedValue({
      rendered_content: 'Preview content with filled variables',
      missing_variables: [],
      validation_errors: {}
    });
    (templatesApi.validateTemplate as any).mockResolvedValue({
      is_valid: true,
      errors: [],
      warnings: [],
      compliance_score: 85
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render the editor interface', () => {
      render(<EnhancedTemplateEditor {...mockProps} />);
      
      expect(screen.getByText('Template Editor')).toBeInTheDocument();
      expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: /content/i })).toBeInTheDocument();
    });

    it('should show splitter layout with editor and preview panels', () => {
      render(<EnhancedTemplateEditor {...mockProps} />);
      
      expect(screen.getByTestId('editor-panel')).toBeInTheDocument();
      expect(screen.getByTestId('preview-panel')).toBeInTheDocument();
      expect(screen.getByTestId('validation-panel')).toBeInTheDocument();
    });

    it('should populate editor with existing template data', () => {
      const template = createMockTemplate({
        name: 'Existing Template',
        description: 'Existing description',
        content: 'Existing content'
      });

      render(<EnhancedTemplateEditor 
        {...mockProps} 
        template={template} 
        mode="edit" 
      />);

      expect(screen.getByDisplayValue('Existing Template')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing description')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing content')).toBeInTheDocument();
    });
  });

  describe('Content Editing', () => {
    it('should update content as user types', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, 'New template content');

      expect(contentEditor).toHaveValue('New template content');
    });

    it('should track cursor position', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i }) as HTMLTextAreaElement;
      await user.type(contentEditor, 'Hello world');
      
      // Move cursor to position 5
      contentEditor.setSelectionRange(5, 5);
      fireEvent.click(contentEditor);

      // Cursor position should be tracked (used for variable insertion)
      expect(contentEditor.selectionStart).toBe(5);
    });

    it('should maintain edit history for undo/redo', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      
      // Type some content
      await user.type(contentEditor, 'First line');
      await user.type(contentEditor, '\nSecond line');

      // Undo should be available
      const undoButton = screen.getByRole('button', { name: /undo/i });
      expect(undoButton).not.toBeDisabled();

      // Perform undo
      await user.click(undoButton);

      // Content should revert to previous state
      expect(contentEditor).toHaveValue('First line');
    });

    it('should support redo functionality', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      
      // Type and undo
      await user.type(contentEditor, 'Test content');
      const undoButton = screen.getByRole('button', { name: /undo/i });
      await user.click(undoButton);

      // Redo should be available
      const redoButton = screen.getByRole('button', { name: /redo/i });
      expect(redoButton).not.toBeDisabled();

      await user.click(redoButton);

      // Content should be restored
      expect(contentEditor).toHaveValue('Test content');
    });

    it('should support keyboard shortcuts for undo/redo', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      
      await user.type(contentEditor, 'Original content');
      await user.type(contentEditor, ' with addition');

      // Ctrl+Z for undo
      await user.keyboard('{Control>}z{/Control}');
      expect(contentEditor).toHaveValue('Original content');

      // Ctrl+Y for redo
      await user.keyboard('{Control>}y{/Control}');
      expect(contentEditor).toHaveValue('Original content with addition');
    });
  });

  describe('Variable Management', () => {
    it('should display existing variables', () => {
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      expect(screen.getByText('platform')).toBeInTheDocument();
      expect(screen.getByText('work_title')).toBeInTheDocument();
    });

    it('should allow adding new variables', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const addVariableButton = screen.getByRole('button', { name: /add variable/i });
      await user.click(addVariableButton);

      // Variable creation form should appear
      expect(screen.getByLabelText(/variable name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/variable label/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/variable type/i)).toBeInTheDocument();
    });

    it('should validate variable names', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const addVariableButton = screen.getByRole('button', { name: /add variable/i });
      await user.click(addVariableButton);

      const nameInput = screen.getByLabelText(/variable name/i);
      await user.type(nameInput, 'invalid name with spaces');

      const saveButton = screen.getByRole('button', { name: /save variable/i });
      await user.click(saveButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/variable name must contain only letters/i)).toBeInTheDocument();
      });
    });

    it('should insert variables at cursor position', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i }) as HTMLTextAreaElement;
      
      // Position cursor
      await user.click(contentEditor);
      contentEditor.setSelectionRange(0, 0);
      fireEvent.click(contentEditor);

      // Insert variable
      const platformVariableButton = screen.getByRole('button', { name: /insert.*platform/i });
      await user.click(platformVariableButton);

      // Variable should be inserted
      expect(contentEditor.value).toContain('{{platform}}');
    });

    it('should detect unused variables', () => {
      const template = createMockTemplate({
        content: 'Content without variables',
        variables: [createMockVariable({ name: 'unused_var' })]
      });

      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      expect(screen.getByText(/unused variable/i)).toBeInTheDocument();
      expect(screen.getByText('unused_var')).toBeInTheDocument();
    });

    it('should detect variables in content that are not defined', () => {
      const template = createMockTemplate({
        content: 'Dear {{undefined_platform}}, this uses an undefined variable.',
        variables: []
      });

      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      expect(screen.getByText(/undefined variable/i)).toBeInTheDocument();
      expect(screen.getByText('undefined_platform')).toBeInTheDocument();
    });

    it('should allow editing existing variables', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      const editButton = screen.getByRole('button', { name: /edit.*platform/i });
      await user.click(editButton);

      // Should show edit form with current values
      const labelInput = screen.getByLabelText(/variable label/i);
      expect(labelInput).toHaveValue('Platform Name');
    });

    it('should allow deleting variables', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      const deleteButton = screen.getByRole('button', { name: /delete.*platform/i });
      await user.click(deleteButton);

      // Should show confirmation dialog
      await waitFor(() => {
        expect(screen.getByText(/delete variable/i)).toBeInTheDocument();
      });

      const confirmButton = screen.getByRole('button', { name: /yes.*delete/i });
      await user.click(confirmButton);

      // Variable should be removed
      await waitFor(() => {
        expect(screen.queryByText('platform')).not.toBeInTheDocument();
      });
    });
  });

  describe('Live Preview', () => {
    it('should show template preview with sample data', async () => {
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      // Preview panel should be visible
      const previewPanel = screen.getByTestId('preview-panel');
      expect(previewPanel).toBeInTheDocument();

      // Should show preview content
      await waitFor(() => {
        expect(screen.getByText(/preview content/i)).toBeInTheDocument();
      });
    });

    it('should update preview as content changes', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();
      
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, 'New content {{test_var}}');

      // Fast-forward debounce timer
      vi.advanceTimersByTime(1000);

      // Preview should update
      await waitFor(() => {
        expect(templatesApi.getTemplatePreview).toHaveBeenCalledWith(
          expect.objectContaining({
            content: expect.stringContaining('New content {{test_var}}')
          })
        );
      });

      vi.useRealTimers();
    });

    it('should allow editing preview test data', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      // Find test data input for platform variable
      const platformTestInput = screen.getByLabelText(/test.*platform/i);
      await user.clear(platformTestInput);
      await user.type(platformTestInput, 'YouTube');

      // Refresh preview
      const refreshButton = screen.getByRole('button', { name: /refresh preview/i });
      await user.click(refreshButton);

      // Should call preview API with test data
      expect(templatesApi.getTemplatePreview).toHaveBeenCalledWith(
        expect.objectContaining({
          values: expect.objectContaining({ platform: 'YouTube' })
        })
      );
    });

    it('should show preview in different formats', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      // Switch to HTML preview
      const htmlFormatButton = screen.getByRole('button', { name: /html.*format/i });
      await user.click(htmlFormatButton);

      // Should show HTML formatted preview
      const previewContent = screen.getByTestId('preview-content');
      expect(previewContent).toHaveClass('html-format');
    });

    it('should handle preview errors gracefully', async () => {
      (templatesApi.getTemplatePreview as any).mockRejectedValue(new Error('Preview Error'));

      render(<EnhancedTemplateEditor {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText(/preview error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Validation', () => {
    it('should show real-time validation results', async () => {
      const template = createMockTemplate();
      render(<EnhancedTemplateEditor {...mockProps} template={template} />);

      // Validation panel should show compliance score
      expect(screen.getByText(/compliance.*85/i)).toBeInTheDocument();
      expect(screen.getByText(/dmca requirements/i)).toBeInTheDocument();
    });

    it('should highlight validation errors in content', async () => {
      const user = userEvent.setup();
      
      // Mock validation with errors
      (templatesApi.validateTemplate as any).mockResolvedValue({
        is_valid: false,
        errors: ['Missing required signature element'],
        warnings: ['Template may be too brief'],
        compliance_score: 45
      });

      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, 'Invalid template content');

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/missing required signature/i)).toBeInTheDocument();
      });
    });

    it('should show form field validation errors', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Try to save without required fields
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should show field validation errors
      await waitFor(() => {
        expect(screen.getByText(/template name is required/i)).toBeInTheDocument();
      });
    });

    it('should validate variable configurations', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Add invalid variable
      const addVariableButton = screen.getByRole('button', { name: /add variable/i });
      await user.click(addVariableButton);

      const typeSelect = screen.getByLabelText(/variable type/i);
      await user.selectOptions(typeSelect, 'email');

      const patternInput = screen.getByLabelText(/validation pattern/i);
      await user.type(patternInput, '[invalid regex');

      const saveButton = screen.getByRole('button', { name: /save variable/i });
      await user.click(saveButton);

      // Should show regex validation error
      await waitFor(() => {
        expect(screen.getByText(/invalid validation pattern/i)).toBeInTheDocument();
      });
    });
  });

  describe('Auto-save Functionality', () => {
    it('should auto-save changes after delay', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();
      
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Make changes
      const nameInput = screen.getByLabelText(/template name/i);
      await user.type(nameInput, 'Auto-saved template');

      // Fast-forward past auto-save delay
      vi.advanceTimersByTime(3500);

      // Should call save draft API
      await waitFor(() => {
        expect(templatesApi.saveDraft).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Auto-saved template'
          })
        );
      });

      vi.useRealTimers();
    });

    it('should show auto-save status indicator', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();
      
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Make changes to trigger auto-save
      const nameInput = screen.getByLabelText(/template name/i);
      await user.type(nameInput, 'Test');

      // Should show "saving..." indicator
      vi.advanceTimersByTime(3000);
      
      await waitFor(() => {
        expect(screen.getByText(/saving/i)).toBeInTheDocument();
      });

      // After save completes, should show "saved" indicator
      vi.advanceTimersByTime(1000);
      
      await waitFor(() => {
        expect(screen.getByText(/saved/i)).toBeInTheDocument();
      });

      vi.useRealTimers();
    });

    it('should handle auto-save errors', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();
      
      (templatesApi.saveDraft as any).mockRejectedValue(new Error('Save failed'));

      render(<EnhancedTemplateEditor {...mockProps} />);

      const nameInput = screen.getByLabelText(/template name/i);
      await user.type(nameInput, 'Test');

      vi.advanceTimersByTime(3500);

      // Should show error indicator
      await waitFor(() => {
        expect(screen.getByText(/save failed/i)).toBeInTheDocument();
      });

      vi.useRealTimers();
    });

    it('should not auto-save if no changes made', async () => {
      vi.useFakeTimers();
      
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Wait for auto-save delay without making changes
      vi.advanceTimersByTime(5000);

      // Should not call save API
      expect(templatesApi.saveDraft).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('Template Saving', () => {
    it('should save new template with form data', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Fill in form
      await user.type(screen.getByLabelText(/template name/i), 'New Template');
      await user.type(screen.getByLabelText(/description/i), 'New description');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'New content');

      // Select category
      const categorySelect = screen.getByLabelText(/category/i);
      await user.selectOptions(categorySelect, 'General DMCA');

      // Save template
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should call create API
      await waitFor(() => {
        expect(templatesApi.createTemplate).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'New Template',
            description: 'New description',
            content: 'New content',
            category: 'General DMCA'
          })
        );
      });
    });

    it('should update existing template', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate();
      
      render(<EnhancedTemplateEditor 
        {...mockProps} 
        template={template} 
        mode="edit" 
      />);

      // Modify template
      const nameInput = screen.getByLabelText(/template name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Template');

      // Save
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should call update API
      await waitFor(() => {
        expect(templatesApi.updateTemplate).toHaveBeenCalledWith(
          template.id,
          expect.objectContaining({
            name: 'Updated Template'
          })
        );
      });
    });

    it('should handle save errors', async () => {
      const user = userEvent.setup();
      (templatesApi.createTemplate as any).mockRejectedValue(new Error('Save failed'));

      render(<EnhancedTemplateEditor {...mockProps} />);

      // Fill minimal required data
      await user.type(screen.getByLabelText(/template name/i), 'Test Template');
      await user.type(screen.getByLabelText(/description/i), 'Test description');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'Test content');

      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/failed to save template/i)).toBeInTheDocument();
      });
    });

    it('should call onSave callback on successful save', async () => {
      const user = userEvent.setup();
      const savedTemplate = createMockTemplate({ name: 'Saved Template' });
      (templatesApi.createTemplate as any).mockResolvedValue(savedTemplate);

      render(<EnhancedTemplateEditor {...mockProps} />);

      // Fill and save
      await user.type(screen.getByLabelText(/template name/i), 'Test Template');
      await user.type(screen.getByLabelText(/description/i), 'Test description');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'Test content');

      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should call onSave callback
      await waitFor(() => {
        expect(mockProps.onSave).toHaveBeenCalledWith(savedTemplate);
      });
    });
  });

  describe('Editor Toolbar', () => {
    it('should provide formatting tools', () => {
      render(<EnhancedTemplateEditor {...mockProps} />);

      expect(screen.getByRole('button', { name: /bold/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /italic/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /underline/i })).toBeInTheDocument();
    });

    it('should provide find and replace functionality', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const findButton = screen.getByRole('button', { name: /find.*replace/i });
      await user.click(findButton);

      // Find/replace dialog should open
      expect(screen.getByLabelText(/find text/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/replace with/i)).toBeInTheDocument();
    });

    it('should support text formatting shortcuts', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      
      // Select some text
      await user.type(contentEditor, 'Bold text');
      contentEditor.setSelectionRange(0, 4); // Select "Bold"

      // Apply bold formatting with Ctrl+B
      await user.keyboard('{Control>}b{/Control}');

      // Text should be wrapped with formatting (implementation specific)
      expect(contentEditor.value).toContain('**Bold**');
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should support save shortcut', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Fill minimum required data
      await user.type(screen.getByLabelText(/template name/i), 'Shortcut Test');
      await user.type(screen.getByLabelText(/description/i), 'Test description');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'Test content');

      // Use Ctrl+S to save
      await user.keyboard('{Control>}s{/Control}');

      // Should trigger save
      await waitFor(() => {
        expect(templatesApi.createTemplate).toHaveBeenCalled();
      });
    });

    it('should support close shortcut', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Use Escape to close
      await user.keyboard('{Escape}');

      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<EnhancedTemplateEditor {...mockProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: /template content/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Tab through form elements
      await user.tab();
      expect(screen.getByLabelText(/template name/i)).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/description/i)).toHaveFocus();
    });

    it('should announce validation errors to screen readers', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateEditor {...mockProps} />);

      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Error messages should have role="alert"
      await waitFor(() => {
        const errorMessage = screen.getByText(/template name is required/i);
        expect(errorMessage.closest('[role="alert"]')).toBeInTheDocument();
      });
    });

    it('should provide screen reader friendly status updates', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();
      
      render(<EnhancedTemplateEditor {...mockProps} />);

      // Trigger auto-save
      await user.type(screen.getByLabelText(/template name/i), 'Test');
      vi.advanceTimersByTime(3500);

      // Status should be announced
      await waitFor(() => {
        const statusRegion = screen.getByLabelText(/save status/i);
        expect(statusRegion).toHaveAttribute('aria-live', 'polite');
      });

      vi.useRealTimers();
    });
  });

  describe('Responsive Design', () => {
    it('should adapt layout for mobile screens', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      render(<EnhancedTemplateEditor {...mockProps} />);

      // Should use stacked layout on mobile
      const splitter = screen.getByTestId('editor-splitter');
      expect(splitter).toHaveClass('mobile-stacked');
    });

    it('should allow collapsing panels on mobile', async () => {
      const user = userEvent.setup();
      
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      render(<EnhancedTemplateEditor {...mockProps} />);

      // Should have panel collapse buttons
      const collapsePreviewButton = screen.getByRole('button', { name: /collapse preview/i });
      await user.click(collapsePreviewButton);

      // Preview panel should be collapsed
      const previewPanel = screen.getByTestId('preview-panel');
      expect(previewPanel).toHaveClass('collapsed');
    });
  });

  describe('Error Boundary', () => {
    it('should handle component errors gracefully', () => {
      // Mock console.error to avoid test output pollution
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Force an error by providing invalid template data
      const invalidTemplate = { ...createMockTemplate(), variables: null } as any;

      render(<EnhancedTemplateEditor 
        {...mockProps} 
        template={invalidTemplate} 
      />);

      // Should show error fallback UI
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reload editor/i })).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });
});