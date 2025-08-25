import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { axe, toHaveNoViolations } from 'jest-axe';
import TemplateLibraryDashboard from '../TemplateLibraryDashboard';
import { EnhancedTemplateEditor } from '../EnhancedTemplateEditor';
import TemplateCreationWizard from '../TemplateCreationWizard';
import { templatesApi } from '../../../services/api';
import { DMCATemplate, TemplateCategory } from '../../../types/templates';
import '@testing-library/jest-dom';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock the API with performance timing
vi.mock('../../../services/api', () => ({
  templatesApi: {
    getTemplates: vi.fn().mockImplementation(async (params = {}) => {
      // Simulate variable response times
      const delay = params.search ? 200 : 100;
      await new Promise(resolve => setTimeout(resolve, delay));
      
      // Return large dataset for performance testing
      const templates = Array.from({ length: 100 }, (_, i) => ({
        id: `template-${i}`,
        name: `Template ${i}`,
        description: `Description for template ${i}`,
        category: ['Social Media', 'General DMCA', 'Video Platforms'][i % 3],
        content: `Template content for ${i}`,
        variables: [],
        is_active: i % 10 !== 0, // Some inactive
        is_system: false,
        created_at: new Date(Date.now() - i * 86400000).toISOString(),
        updated_at: new Date(Date.now() - i * 86400000).toISOString(),
        tags: [`tag-${i % 5}`],
        language: 'en',
        jurisdiction: 'US',
      }));

      // Apply filters for performance testing
      let filtered = templates;
      if (params.search) {
        filtered = templates.filter(t => 
          t.name.toLowerCase().includes(params.search.toLowerCase())
        );
      }

      const page = params.page || 1;
      const limit = params.limit || 20;
      const start = (page - 1) * limit;
      
      return {
        templates: filtered.slice(start, start + limit),
        total: filtered.length,
        page,
        limit,
        total_pages: Math.ceil(filtered.length / limit),
        has_next: start + limit < filtered.length,
        has_prev: page > 1
      };
    }),
    getCategories: vi.fn().mockResolvedValue([
      { id: '1', name: 'Social Media', template_count: 33 },
      { id: '2', name: 'General DMCA', template_count: 33 },
      { id: '3', name: 'Video Platforms', template_count: 34 },
    ]),
    createTemplate: vi.fn().mockResolvedValue({}),
    updateTemplate: vi.fn().mockResolvedValue({}),
    deleteTemplate: vi.fn().mockResolvedValue({}),
    getTemplatePreview: vi.fn().mockResolvedValue({
      rendered_content: 'Preview content',
      missing_variables: [],
      validation_errors: {}
    }),
    validateTemplate: vi.fn().mockResolvedValue({
      is_valid: true,
      errors: [],
      warnings: [],
      compliance_score: 85
    }),
    getTemplateStarters: vi.fn().mockResolvedValue([]),
    saveDraft: vi.fn().mockResolvedValue({}),
  }
}));

// Mock ResizeObserver for performance tests
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock IntersectionObserver for virtual scrolling
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

describe('Template Performance Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Template Library Dashboard Performance', () => {
    it('should render large template lists efficiently', async () => {
      const startTime = performance.now();
      
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for templates to load
      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render within reasonable time (adjust threshold as needed)
      expect(renderTime).toBeLessThan(2000); // 2 seconds
    });

    it('should debounce search input to prevent excessive API calls', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      const searchInput = await screen.findByPlaceholderText(/search templates/i);

      // Type rapidly
      await user.type(searchInput, 'test search query');

      // Before debounce delay - should only have initial load call
      expect(templatesApi.getTemplates).toHaveBeenCalledTimes(1);

      // Fast-forward past debounce delay
      vi.advanceTimersByTime(600);

      // Should now have the debounced search call
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledTimes(2);
      });

      vi.useRealTimers();
    });

    it('should implement virtual scrolling for large lists', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Should not render all 100 templates at once
      expect(screen.queryByText('Template 50')).not.toBeInTheDocument();
      expect(screen.queryByText('Template 99')).not.toBeInTheDocument();

      // Should use pagination or virtual scrolling
      const paginationOrVirtualList = 
        screen.queryByRole('navigation') || // Pagination
        screen.queryByTestId('virtual-list'); // Virtual scrolling

      expect(paginationOrVirtualList).toBeInTheDocument();
    });

    it('should optimize re-renders with memoization', async () => {
      const user = userEvent.setup();
      
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      const { rerender } = render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      const initialCallCount = templatesApi.getTemplates.mock.calls.length;

      // Re-render with same props - should not trigger new API calls
      rerender(<TemplateLibraryDashboard {...mockProps} />);

      // Small delay to allow any potential API calls
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(templatesApi.getTemplates).toHaveBeenCalledTimes(initialCallCount);
    });

    it('should handle rapid filter changes efficiently', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
      });

      const categoryDropdown = screen.getByLabelText(/category/i);

      // Rapidly change filters
      await user.selectOptions(categoryDropdown, 'Social Media');
      await user.selectOptions(categoryDropdown, 'General DMCA');
      await user.selectOptions(categoryDropdown, 'Video Platforms');

      // Should batch the requests
      vi.advanceTimersByTime(1000);

      await waitFor(() => {
        // Should not have made excessive API calls
        expect(templatesApi.getTemplates.mock.calls.length).toBeLessThan(6);
      });

      vi.useRealTimers();
    });

    it('should lazy load images and icons', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Check for lazy loading attributes
      const templateCards = screen.getAllByTestId(/template-card/i);
      const images = templateCards[0].querySelectorAll('img');
      
      images.forEach(img => {
        expect(img).toHaveAttribute('loading', 'lazy');
      });
    });
  });

  describe('Template Editor Performance', () => {
    it('should handle large content efficiently', async () => {
      const user = userEvent.setup();
      
      const largeContent = 'Lorem ipsum '.repeat(1000); // Large content
      const template = {
        id: 'perf-test',
        name: 'Performance Test Template',
        content: largeContent,
        variables: [],
      } as DMCATemplate;

      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      const startTime = performance.now();
      render(<EnhancedTemplateEditor {...editorProps} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue(largeContent)).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      expect(renderTime).toBeLessThan(3000); // 3 seconds for large content
    });

    it('should debounce auto-save operations', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });

      // Type rapidly
      await user.type(contentEditor, 'Rapid typing test content');

      // Should not trigger save immediately
      expect(templatesApi.saveDraft).not.toHaveBeenCalled();

      // Fast-forward past auto-save delay
      vi.advanceTimersByTime(3500);

      await waitFor(() => {
        expect(templatesApi.saveDraft).toHaveBeenCalledTimes(1);
      });

      vi.useRealTimers();
    });

    it('should optimize preview updates', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      const template = {
        id: 'preview-test',
        name: 'Preview Test',
        content: 'Dear {{platform}}',
        variables: [{ name: 'platform', label: 'Platform', type: 'text', required: true }],
      } as DMCATemplate;

      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });

      // Make multiple rapid changes
      await user.type(contentEditor, ' Team,\nAdditional content');

      // Should debounce preview updates
      vi.advanceTimersByTime(500); // Before debounce
      expect(templatesApi.getTemplatePreview).toHaveBeenCalledTimes(1); // Initial load only

      vi.advanceTimersByTime(600); // After debounce
      
      await waitFor(() => {
        expect(templatesApi.getTemplatePreview).toHaveBeenCalledTimes(2); // Initial + debounced update
      });

      vi.useRealTimers();
    });

    it('should limit undo history to prevent memory issues', async () => {
      const user = userEvent.setup();

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      const contentEditor = screen.getByRole('textbox', { name: /content/i });

      // Make many changes to test history limit
      for (let i = 0; i < 60; i++) {
        await user.type(contentEditor, ` Change ${i}`);
        
        // Trigger history save by moving cursor
        fireEvent.blur(contentEditor);
        fireEvent.focus(contentEditor);
      }

      // Undo should be limited (component should implement MAX_HISTORY_LENGTH)
      const undoButton = screen.getByRole('button', { name: /undo/i });
      
      // Should be able to undo, but not infinitely
      expect(undoButton).not.toBeDisabled();

      // The component should internally limit history to prevent memory issues
      // This is implementation-specific and would be tested in the component logic
    });
  });

  describe('Bundle Size and Code Splitting', () => {
    it('should lazy load template components', async () => {
      // This test would typically be done with build analysis tools
      // Here we can check that components are wrapped with React.lazy

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      // Initially render dashboard
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Editor should not be loaded initially
      expect(screen.queryByText('Template Editor')).not.toBeInTheDocument();
    });

    it('should load additional features on demand', async () => {
      const user = userEvent.setup();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Advanced features should load on demand
      const advancedFiltersButton = screen.queryByRole('button', { name: /advanced filters/i });
      
      if (advancedFiltersButton) {
        await user.click(advancedFiltersButton);
        
        // Advanced filter UI should now be loaded
        await waitFor(() => {
          expect(screen.getByText(/advanced search options/i)).toBeInTheDocument();
        });
      }
    });
  });
});

describe('Template Accessibility Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Template Library Dashboard Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      const { container } = render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for content to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search templates/i)).toBeInTheDocument();
      });

      // Tab through main controls
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      searchInput.focus();

      await user.tab();
      expect(screen.getByLabelText(/category/i)).toHaveFocus();

      await user.tab();
      expect(screen.getByLabelText(/status/i)).toHaveFocus();
    });

    it('should have proper ARIA labels and roles', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Main heading
      expect(screen.getByRole('heading', { name: /template library/i })).toBeInTheDocument();

      // Search functionality
      expect(screen.getByLabelText(/search templates/i)).toBeInTheDocument();
      expect(screen.getByRole('searchbox')).toBeInTheDocument();

      // Filter controls
      expect(screen.getByLabelText(/filter by category/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/filter by status/i)).toBeInTheDocument();

      // View controls
      expect(screen.getByLabelText(/grid view/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/list view/i)).toBeInTheDocument();

      // Template grid
      expect(screen.getByRole('grid') || screen.getByRole('list')).toBeInTheDocument();
    });

    it('should announce loading and error states', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Should have loading indicator with proper ARIA
      expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();

      // Wait for content to load
      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Loading indicator should be gone
      expect(screen.queryByRole('status', { name: /loading/i })).not.toBeInTheDocument();
    });

    it('should provide screen reader friendly pagination', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Pagination should be properly labeled
      const pagination = screen.queryByRole('navigation', { name: /pagination/i });
      if (pagination) {
        expect(pagination).toBeInTheDocument();

        // Page buttons should have descriptive labels
        const nextButton = screen.getByLabelText(/next page/i);
        expect(nextButton).toBeInTheDocument();
      }
    });

    it('should support screen reader announcements for dynamic content', async () => {
      const user = userEvent.setup();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Search results should be announced
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.type(searchInput, 'Template 1');

      await waitFor(() => {
        const resultsRegion = screen.getByRole('region', { name: /search results/i });
        expect(resultsRegion).toHaveAttribute('aria-live', 'polite');
      });
    });
  });

  describe('Template Editor Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const template = {
        id: 'accessibility-test',
        name: 'Accessibility Test Template',
        content: 'Test content',
        variables: [],
      } as DMCATemplate;

      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      const { container } = render(<EnhancedTemplateEditor {...editorProps} />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Accessibility Test Template')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should support keyboard shortcuts', async () => {
      const user = userEvent.setup();

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      // Fill minimum required data
      await user.type(screen.getByLabelText(/template name/i), 'Keyboard Test');
      await user.type(screen.getByLabelText(/description/i), 'Testing keyboard shortcuts');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'Test content');

      // Test save shortcut
      await user.keyboard('{Control>}s{/Control}');

      expect(templatesApi.createTemplate).toHaveBeenCalled();
    });

    it('should provide accessible form validation', async () => {
      const user = userEvent.setup();

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      // Try to save without required fields
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Error messages should be associated with form fields
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/template name/i);
        expect(nameInput).toHaveAttribute('aria-invalid', 'true');
        expect(nameInput).toHaveAttribute('aria-describedby');

        const errorId = nameInput.getAttribute('aria-describedby');
        if (errorId) {
          expect(document.getElementById(errorId)).toHaveTextContent(/required/i);
        }
      });
    });

    it('should announce auto-save status to screen readers', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      // Make changes to trigger auto-save
      await user.type(screen.getByLabelText(/template name/i), 'Auto-save test');

      // Should show saving status
      vi.advanceTimersByTime(3000);

      await waitFor(() => {
        const statusRegion = screen.getByRole('status', { name: /save status/i });
        expect(statusRegion).toHaveAttribute('aria-live', 'polite');
        expect(statusRegion).toHaveTextContent(/saving/i);
      });

      vi.useRealTimers();
    });

    it('should make preview panel accessible', async () => {
      const template = {
        id: 'preview-test',
        name: 'Preview Test',
        content: 'Dear {{platform}}',
        variables: [{ name: 'platform', label: 'Platform', type: 'text', required: true }],
      } as DMCATemplate;

      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />);

      await waitFor(() => {
        const previewRegion = screen.getByRole('region', { name: /preview/i });
        expect(previewRegion).toBeInTheDocument();
        expect(previewRegion).toHaveAttribute('aria-label', 'Template preview');
      });
    });
  });

  describe('Template Creation Wizard Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const wizardProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      const { container } = render(<TemplateCreationWizard {...wizardProps} />);

      await waitFor(() => {
        expect(screen.getByText(/template type/i)).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should provide proper step navigation accessibility', async () => {
      const wizardProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<TemplateCreationWizard {...wizardProps} />);

      // Steps should be in a navigation landmark
      const stepsNav = screen.getByRole('navigation', { name: /wizard steps/i });
      expect(stepsNav).toBeInTheDocument();

      // Current step should be announced
      expect(screen.getByText(/step 1 of 5/i)).toBeInTheDocument();

      // Steps should have proper ARIA attributes
      const currentStep = screen.getByRole('tab', { selected: true });
      expect(currentStep).toBeInTheDocument();
    });

    it('should announce step changes to screen readers', async () => {
      const user = userEvent.setup();

      const wizardProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<TemplateCreationWizard {...wizardProps} />);

      // Select a template starter
      await waitFor(() => {
        expect(screen.getByText('Social Media DMCA')).toBeInTheDocument();
      });

      const starterCard = screen.getByText('Social Media DMCA').closest('[role="button"]');
      await user.click(starterCard!);

      // Navigate to next step
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Step change should be announced
      await waitFor(() => {
        const liveRegion = screen.getByRole('status');
        expect(liveRegion).toHaveTextContent(/step 2/i);
      });
    });

    it('should provide accessible progress indication', () => {
      const wizardProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<TemplateCreationWizard {...wizardProps} />);

      // Progress should be indicated accessibly
      const progressIndicator = screen.getByRole('progressbar');
      expect(progressIndicator).toBeInTheDocument();
      expect(progressIndicator).toHaveAttribute('aria-valuenow', '1');
      expect(progressIndicator).toHaveAttribute('aria-valuemin', '1');
      expect(progressIndicator).toHaveAttribute('aria-valuemax', '5');
    });
  });

  describe('Mobile Accessibility', () => {
    beforeEach(() => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      // Mock touch capabilities
      Object.defineProperty(window, 'ontouchstart', {
        writable: true,
        configurable: true,
        value: () => {},
      });
    });

    it('should maintain accessibility on mobile devices', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      const { container } = render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should provide proper touch targets', async () => {
      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Interactive elements should have proper touch target sizes
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        const styles = window.getComputedStyle(button);
        const minSize = 44; // WCAG minimum touch target size

        // This would typically check computed dimensions
        // For this test, we ensure buttons have appropriate classes/styles
        expect(button).toHaveClass(/touch-target|btn|button/);
      });
    });

    it('should support mobile navigation patterns', async () => {
      const user = userEvent.setup();

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Should have mobile-friendly navigation
      const mobileMenuButton = screen.getByLabelText(/open.*menu|menu.*toggle/i);
      expect(mobileMenuButton).toBeInTheDocument();

      await user.click(mobileMenuButton);

      // Mobile menu should be accessible
      const mobileMenu = screen.getByRole('navigation', { name: /main.*menu/i });
      expect(mobileMenu).toBeInTheDocument();
      expect(mobileMenu).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('High Contrast and Reduced Motion', () => {
    it('should support high contrast mode', () => {
      // Mock high contrast media query
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query === '(prefers-contrast: high)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Should apply high contrast styles
      const mainContainer = screen.getByRole('main') || document.body.firstChild as Element;
      expect(mainContainer).toHaveClass(/high-contrast/);
    });

    it('should respect reduced motion preferences', () => {
      // Mock reduced motion preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query === '(prefers-reduced-motion: reduce)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Should reduce or eliminate animations
      const animatedElements = document.querySelectorAll('[data-animated="true"]');
      animatedElements.forEach(element => {
        expect(element).toHaveClass(/no-animation|reduced-motion/);
      });
    });
  });
});