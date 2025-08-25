import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TemplateCreationWizard, { TemplateStarter, WizardFormData } from '../TemplateCreationWizard';
import { templatesApi } from '../../../services/api';
import { DMCATemplate, TemplateVariable } from '../../../types/templates';
import '@testing-library/jest-dom';

// Mock the API
vi.mock('../../../services/api', () => ({
  templatesApi: {
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    getTemplatePreview: vi.fn(),
    getTemplateStarters: vi.fn(),
    saveDraft: vi.fn(),
    getDraft: vi.fn(),
    deleteDraft: vi.fn(),
  }
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Test data factories
const createMockTemplate = (overrides: Partial<DMCATemplate> = {}): DMCATemplate => ({
  id: 'template-1',
  name: 'Test Template',
  description: 'A test template',
  category: 'General DMCA',
  content: 'Dear {{platform}}, I am writing to report copyright infringement...',
  variables: [
    {
      name: 'platform',
      label: 'Platform Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., YouTube'
    }
  ],
  is_active: true,
  is_system: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  tags: [],
  language: 'en',
  jurisdiction: 'US',
  ...overrides
});

const createMockStarter = (overrides: Partial<TemplateStarter> = {}): TemplateStarter => ({
  id: 'starter-1',
  name: 'Social Media DMCA',
  description: 'Template for social media platforms',
  category: 'Social Media',
  content: 'Dear {{platform}} Team,\n\nI am writing to report copyright infringement...',
  variables: [
    { name: 'platform', label: 'Platform Name', type: 'text', required: true }
  ],
  tags: ['social-media'],
  icon: 'pi-share-alt',
  jurisdiction: 'US',
  language: 'en',
  ...overrides
});

describe('TemplateCreationWizard', () => {
  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn(),
    mode: 'create' as const,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    
    // Default API responses
    (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
    (templatesApi.createTemplate as any).mockResolvedValue(createMockTemplate());
    (templatesApi.getTemplatePreview as any).mockResolvedValue({
      rendered_content: 'Preview content',
      missing_variables: [],
      validation_errors: {}
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Wizard Navigation', () => {
    it('should render all wizard steps', () => {
      render(<TemplateCreationWizard {...mockProps} />);
      
      expect(screen.getByText('Template Type')).toBeInTheDocument();
      expect(screen.getByText('Basic Info')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
      expect(screen.getByText('Variables')).toBeInTheDocument();
      expect(screen.getByText('Preview')).toBeInTheDocument();
    });

    it('should start on the first step', () => {
      render(<TemplateCreationWizard {...mockProps} />);
      
      // Step 1 should be active
      const step1 = screen.getByText('Template Type').closest('.p-steps-item');
      expect(step1).toHaveClass('p-steps-current');
      
      // Should show step 1 content
      expect(screen.getByText(/choose a template category/i)).toBeInTheDocument();
    });

    it('should navigate to next step when clicking next', async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
      
      render(<TemplateCreationWizard {...mockProps} />);

      // Select a starter first
      await waitFor(() => {
        expect(screen.getByText('Social Media DMCA')).toBeInTheDocument();
      });
      
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);

      // Click next
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Should be on step 2
      await waitFor(() => {
        const step2 = screen.getByText('Basic Info').closest('.p-steps-item');
        expect(step2).toHaveClass('p-steps-current');
      });
    });

    it('should navigate back to previous step when clicking back', async () => {
      const user = userEvent.setup();
      
      render(<TemplateCreationWizard {...mockProps} />);

      // Navigate to step 2 first
      const starterCard = await screen.findByText('Social Media DMCA');
      await user.click(starterCard.closest('.starter-card')!);
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Now go back
      const backButton = screen.getByRole('button', { name: /back/i });
      await user.click(backButton);

      // Should be back on step 1
      await waitFor(() => {
        const step1 = screen.getByText('Template Type').closest('.p-steps-item');
        expect(step1).toHaveClass('p-steps-current');
      });
    });

    it('should disable next button when current step is invalid', () => {
      render(<TemplateCreationWizard {...mockProps} />);
      
      // Next should be disabled until a template starter is selected
      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).toBeDisabled();
    });

    it('should show step validation errors', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      // Try to proceed without selecting a starter
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/please select a template starter/i)).toBeInTheDocument();
      });
    });
  });

  describe('Step 1: Template Type Selection', () => {
    it('should load and display template starters', async () => {
      const starters = [
        createMockStarter({ name: 'Social Media Template' }),
        createMockStarter({ 
          id: 'starter-2', 
          name: 'Search Engine Template', 
          category: 'Search Engines' 
        }),
      ];
      (templatesApi.getTemplateStarters as any).mockResolvedValue(starters);

      render(<TemplateCreationWizard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Social Media Template')).toBeInTheDocument();
        expect(screen.getByText('Search Engine Template')).toBeInTheDocument();
      });
    });

    it('should filter starters by category', async () => {
      const user = userEvent.setup();
      const starters = [
        createMockStarter({ name: 'Social Media Template', category: 'Social Media' }),
        createMockStarter({ 
          id: 'starter-2', 
          name: 'Search Engine Template', 
          category: 'Search Engines' 
        }),
      ];
      (templatesApi.getTemplateStarters as any).mockResolvedValue(starters);

      render(<TemplateCreationWizard {...mockProps} />);

      // Filter by Social Media category
      const categoryFilter = screen.getByRole('combobox', { name: /category/i });
      await user.selectOptions(categoryFilter, 'Social Media');

      await waitFor(() => {
        expect(screen.getByText('Social Media Template')).toBeInTheDocument();
        expect(screen.queryByText('Search Engine Template')).not.toBeInTheDocument();
      });
    });

    it('should select a template starter', async () => {
      const user = userEvent.setup();
      const starter = createMockStarter({ name: 'Selected Starter' });
      (templatesApi.getTemplateStarters as any).mockResolvedValue([starter]);

      render(<TemplateCreationWizard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Selected Starter')).toBeInTheDocument();
      });

      const starterCard = screen.getByText('Selected Starter').closest('.starter-card');
      await user.click(starterCard!);

      // Card should be selected
      expect(starterCard).toHaveClass('selected');
      
      // Next button should be enabled
      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).not.toBeDisabled();
    });

    it('should show option to start from scratch', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      const fromScratchOption = screen.getByText(/start from scratch/i);
      await user.click(fromScratchOption);

      // Should enable next button
      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).not.toBeDisabled();
    });
  });

  describe('Step 2: Basic Info', () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
      
      render(<TemplateCreationWizard {...mockProps} />);

      // Navigate to step 2
      await waitFor(() => screen.getByText('Social Media DMCA'));
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);
      
      await waitFor(() => {
        const step2 = screen.getByText('Basic Info').closest('.p-steps-item');
        expect(step2).toHaveClass('p-steps-current');
      });
    });

    it('should display basic info form fields', () => {
      expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/jurisdiction/i)).toBeInTheDocument();
    });

    it('should validate required fields', async () => {
      const user = userEvent.setup();
      
      // Try to proceed without filling required fields
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/template name is required/i)).toBeInTheDocument();
        expect(screen.getByText(/description is required/i)).toBeInTheDocument();
      });
    });

    it('should populate form with starter data', () => {
      // Should pre-populate from selected starter
      const nameInput = screen.getByLabelText(/template name/i) as HTMLInputElement;
      const categorySelect = screen.getByLabelText(/category/i) as HTMLSelectElement;
      
      expect(nameInput.value).toBe('Social Media DMCA');
      expect(categorySelect.value).toBe('Social Media');
    });

    it('should allow form editing', async () => {
      const user = userEvent.setup();

      const nameInput = screen.getByLabelText(/template name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'My Custom Template');

      const descriptionInput = screen.getByLabelText(/description/i);
      await user.type(descriptionInput, 'Custom description for my template');

      expect(nameInput).toHaveValue('My Custom Template');
      expect(descriptionInput).toHaveValue('Custom description for my template');
    });

    it('should show character limits for fields', () => {
      expect(screen.getByText(/100 characters/i)).toBeInTheDocument(); // Name limit
      expect(screen.getByText(/500 characters/i)).toBeInTheDocument(); // Description limit
    });
  });

  describe('Step 3: Content Creation', () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
      
      render(<TemplateCreationWizard {...mockProps} />);

      // Navigate to step 3
      await navigateToStep(user, 3);
    });

    it('should display content editor', () => {
      expect(screen.getByRole('textbox', { name: /template content/i })).toBeInTheDocument();
    });

    it('should show content suggestions and AI assistance', () => {
      expect(screen.getByText(/ai suggestions/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /improve content/i })).toBeInTheDocument();
    });

    it('should show legal compliance indicators', () => {
      expect(screen.getByText(/legal compliance/i)).toBeInTheDocument();
      expect(screen.getByText(/dmca requirements/i)).toBeInTheDocument();
    });

    it('should validate content requirements', async () => {
      const user = userEvent.setup();
      
      const contentEditor = screen.getByRole('textbox', { name: /template content/i });
      await user.clear(contentEditor);

      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/template content is required/i)).toBeInTheDocument();
      });
    });

    it('should detect and suggest variables in content', async () => {
      const user = userEvent.setup();
      
      const contentEditor = screen.getByRole('textbox', { name: /template content/i });
      await user.type(contentEditor, 'Dear PLATFORM_NAME team...');

      // Should suggest variable creation
      await waitFor(() => {
        expect(screen.getByText(/detected potential variable/i)).toBeInTheDocument();
      });
    });
  });

  describe('Step 4: Variable Setup', () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
      
      render(<TemplateCreationWizard {...mockProps} />);
      await navigateToStep(user, 4);
    });

    it('should display variable list', () => {
      expect(screen.getByText(/template variables/i)).toBeInTheDocument();
      expect(screen.getByText('platform')).toBeInTheDocument(); // From starter
    });

    it('should allow adding new variables', async () => {
      const user = userEvent.setup();
      
      const addButton = screen.getByRole('button', { name: /add variable/i });
      await user.click(addButton);

      // Should show variable creation form
      expect(screen.getByLabelText(/variable name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/variable type/i)).toBeInTheDocument();
    });

    it('should validate variable configuration', async () => {
      const user = userEvent.setup();
      
      const addButton = screen.getByRole('button', { name: /add variable/i });
      await user.click(addButton);

      const saveButton = screen.getByRole('button', { name: /save variable/i });
      await user.click(saveButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/variable name is required/i)).toBeInTheDocument();
      });
    });

    it('should allow editing existing variables', async () => {
      const user = userEvent.setup();
      
      const editButton = screen.getByRole('button', { name: /edit.*platform/i });
      await user.click(editButton);

      // Should open edit form
      const labelInput = screen.getByLabelText(/variable label/i);
      expect(labelInput).toHaveValue('Platform Name');
    });

    it('should detect unused variables', () => {
      // Mock scenario where variable exists but isn't used in content
      expect(screen.getByText(/unused variable/i)).toBeInTheDocument();
    });
  });

  describe('Step 5: Preview and Finalize', () => {
    beforeEach(async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockResolvedValue([createMockStarter()]);
      
      render(<TemplateCreationWizard {...mockProps} />);
      await navigateToStep(user, 5);
    });

    it('should display template preview', async () => {
      await waitFor(() => {
        expect(screen.getByText(/template preview/i)).toBeInTheDocument();
        expect(screen.getByText('Preview content')).toBeInTheDocument(); // Mocked preview
      });
    });

    it('should show legal compliance score', () => {
      expect(screen.getByText(/compliance score/i)).toBeInTheDocument();
      expect(screen.getByText(/dmca requirements/i)).toBeInTheDocument();
    });

    it('should allow testing with sample data', async () => {
      const user = userEvent.setup();
      
      const testInput = screen.getByLabelText(/platform.*test/i);
      await user.type(testInput, 'YouTube');

      const refreshButton = screen.getByRole('button', { name: /refresh preview/i });
      await user.click(refreshButton);

      // Should call preview API with test data
      expect(templatesApi.getTemplatePreview).toHaveBeenCalledWith(
        expect.objectContaining({
          values: expect.objectContaining({ platform: 'YouTube' })
        })
      );
    });

    it('should show validation warnings', () => {
      expect(screen.getByText(/validation summary/i)).toBeInTheDocument();
      // Should show any warnings or issues
    });
  });

  describe('Auto-save and Draft Management', () => {
    it('should auto-save draft data periodically', async () => {
      vi.useFakeTimers();
      const user = userEvent.setup();
      
      render(<TemplateCreationWizard {...mockProps} />);

      // Make some changes
      await waitFor(() => screen.getByText('Social Media DMCA'));
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);

      // Advance timer to trigger auto-save
      vi.advanceTimersByTime(30000); // 30 seconds

      await waitFor(() => {
        expect(templatesApi.saveDraft).toHaveBeenCalled();
      });

      vi.useRealTimers();
    });

    it('should load saved draft on wizard open', async () => {
      const draftData = {
        name: 'Draft Template',
        category: 'Social Media',
        content: 'Draft content...',
      };
      
      (templatesApi.getDraft as any).mockResolvedValue(draftData);

      render(<TemplateCreationWizard {...mockProps} />);

      // Should show draft recovery option
      await waitFor(() => {
        expect(screen.getByText(/recover draft/i)).toBeInTheDocument();
      });
    });

    it('should clear draft on successful save', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      // Complete wizard
      await completeWizardFlow(user);

      // Should clear draft
      expect(templatesApi.deleteDraft).toHaveBeenCalled();
    });

    it('should warn about unsaved changes on close', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      // Make changes
      await waitFor(() => screen.getByText('Social Media DMCA'));
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);

      // Try to close
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      // Should show confirmation dialog
      await waitFor(() => {
        expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
      });
    });
  });

  describe('Edit Mode', () => {
    it('should populate wizard with existing template data', () => {
      const existingTemplate = createMockTemplate({
        name: 'Existing Template',
        description: 'Existing description',
      });

      render(<TemplateCreationWizard 
        {...mockProps} 
        template={existingTemplate} 
        mode="edit" 
      />);

      // Should pre-populate with template data
      expect(screen.getByDisplayValue('Existing Template')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing description')).toBeInTheDocument();
    });

    it('should call update API instead of create', async () => {
      const user = userEvent.setup();
      const existingTemplate = createMockTemplate();

      render(<TemplateCreationWizard 
        {...mockProps} 
        template={existingTemplate} 
        mode="edit" 
      />);

      // Complete edit flow
      await completeWizardFlow(user);

      expect(templatesApi.updateTemplate).toHaveBeenCalledWith(
        existingTemplate.id,
        expect.any(Object)
      );
      expect(templatesApi.createTemplate).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      render(<TemplateCreationWizard {...mockProps} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByLabelText(/step.*1.*of.*5/i)).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      // Should be able to tab through controls
      await user.tab();
      expect(screen.getByRole('button', { name: /close/i })).toHaveFocus();

      // Step navigation should be keyboard accessible
      await user.keyboard('{ArrowRight}');
      // Should move focus to next step (if applicable)
    });

    it('should announce step changes to screen readers', async () => {
      const user = userEvent.setup();
      render(<TemplateCreationWizard {...mockProps} />);

      // Navigate forward
      await waitFor(() => screen.getByText('Social Media DMCA'));
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Should have live region announcing step change
      await waitFor(() => {
        expect(screen.getByLabelText(/step 2 of 5/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      const user = userEvent.setup();
      (templatesApi.createTemplate as any).mockRejectedValue(new Error('API Error'));

      render(<TemplateCreationWizard {...mockProps} />);

      // Complete wizard
      await completeWizardFlow(user);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/failed to save template/i)).toBeInTheDocument();
      });
    });

    it('should handle network connectivity issues', async () => {
      const user = userEvent.setup();
      (templatesApi.getTemplateStarters as any).mockRejectedValue(new Error('Network Error'));

      render(<TemplateCreationWizard {...mockProps} />);

      // Should show offline state
      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });
  });

  // Helper functions
  async function navigateToStep(user: any, stepNumber: number) {
    // Navigate through steps to reach the desired step
    for (let i = 1; i < stepNumber; i++) {
      if (i === 1) {
        // Select starter on step 1
        await waitFor(() => screen.getByText('Social Media DMCA'));
        const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
        await user.click(starterCard!);
      } else if (i === 2) {
        // Fill basic info on step 2
        const nameInput = screen.getByLabelText(/template name/i);
        await user.clear(nameInput);
        await user.type(nameInput, 'Test Template');
        
        const descInput = screen.getByLabelText(/description/i);
        await user.type(descInput, 'Test description');
      } else if (i === 3) {
        // Content is already populated from starter
      } else if (i === 4) {
        // Variables are already populated from starter
      }
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);
      
      await waitFor(() => {
        const currentStep = screen.getByText(`Step ${i + 1}`).closest('.p-steps-item');
        expect(currentStep).toHaveClass('p-steps-current');
      });
    }
  }

  async function completeWizardFlow(user: any) {
    // Navigate to final step and save
    await navigateToStep(user, 5);
    
    const saveButton = screen.getByRole('button', { name: /save template/i });
    await user.click(saveButton);
  }
});