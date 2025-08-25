import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TemplateLibraryDashboard from '../TemplateLibraryDashboard';
import { EnhancedTemplateEditor } from '../EnhancedTemplateEditor';
import TemplateCreationWizard from '../TemplateCreationWizard';
import { templatesApi } from '../../../services/api';
import { DMCATemplate, PaginatedTemplatesResponse, TemplateCategory } from '../../../types/templates';
import '@testing-library/jest-dom';

// Mock the API with more realistic implementations
vi.mock('../../../services/api', () => {
  let mockTemplates: DMCATemplate[] = [];
  let mockCategories: TemplateCategory[] = [];
  let nextId = 1;

  return {
    templatesApi: {
      // GET endpoints
      getTemplates: vi.fn().mockImplementation(async (params = {}) => {
        await new Promise(resolve => setTimeout(resolve, 100)); // Simulate network delay
        
        let filteredTemplates = [...mockTemplates];
        
        // Apply filters
        if (params.search) {
          filteredTemplates = filteredTemplates.filter(t => 
            t.name.toLowerCase().includes(params.search.toLowerCase()) ||
            t.description.toLowerCase().includes(params.search.toLowerCase())
          );
        }
        
        if (params.category) {
          filteredTemplates = filteredTemplates.filter(t => t.category === params.category);
        }
        
        if (params.is_active !== undefined) {
          filteredTemplates = filteredTemplates.filter(t => t.is_active === params.is_active);
        }
        
        // Apply sorting
        if (params.sort_by) {
          filteredTemplates.sort((a, b) => {
            const aVal = a[params.sort_by as keyof DMCATemplate];
            const bVal = b[params.sort_by as keyof DMCATemplate];
            const order = params.sort_order === 'asc' ? 1 : -1;
            return aVal < bVal ? -order : aVal > bVal ? order : 0;
          });
        }
        
        // Apply pagination
        const page = params.page || 1;
        const limit = params.limit || 20;
        const start = (page - 1) * limit;
        const end = start + limit;
        const paginatedTemplates = filteredTemplates.slice(start, end);
        
        return {
          templates: paginatedTemplates,
          total: filteredTemplates.length,
          page,
          limit,
          total_pages: Math.ceil(filteredTemplates.length / limit),
          has_next: end < filteredTemplates.length,
          has_prev: page > 1
        };
      }),
      
      getCategories: vi.fn().mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
        return [...mockCategories];
      }),
      
      getTemplate: vi.fn().mockImplementation(async (id: string) => {
        await new Promise(resolve => setTimeout(resolve, 50));
        const template = mockTemplates.find(t => t.id === id);
        if (!template) throw new Error('Template not found');
        return template;
      }),
      
      getTemplatePreview: vi.fn().mockImplementation(async (request) => {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        let renderedContent = request.content || '';
        const values = request.values || {};
        
        // Simple variable replacement
        Object.entries(values).forEach(([key, value]) => {
          renderedContent = renderedContent.replace(
            new RegExp(`{{${key}}}`, 'g'), 
            value as string
          );
        });
        
        // Find missing variables
        const variablePattern = /{{(\w+)}}/g;
        const missingVariables: string[] = [];
        let match;
        while ((match = variablePattern.exec(renderedContent)) !== null) {
          if (!values[match[1]]) {
            missingVariables.push(match[1]);
          }
        }
        
        return {
          rendered_content: renderedContent,
          missing_variables: missingVariables,
          validation_errors: {}
        };
      }),
      
      validateTemplate: vi.fn().mockImplementation(async (template) => {
        await new Promise(resolve => setTimeout(resolve, 80));
        
        const errors: string[] = [];
        const warnings: string[] = [];
        
        if (!template.name) errors.push('Template name is required');
        if (!template.content) errors.push('Template content is required');
        if (template.content && template.content.length < 50) {
          warnings.push('Template content is quite short');
        }
        
        // Check for DMCA compliance indicators
        const requiredPhrases = [
          'copyright',
          'infringement',
          'good faith',
          'perjury'
        ];
        
        let complianceScore = 0;
        requiredPhrases.forEach(phrase => {
          if (template.content?.toLowerCase().includes(phrase)) {
            complianceScore += 25;
          }
        });
        
        return {
          is_valid: errors.length === 0,
          errors,
          warnings,
          compliance_score: complianceScore
        };
      }),
      
      // POST/PUT endpoints
      createTemplate: vi.fn().mockImplementation(async (templateData) => {
        await new Promise(resolve => setTimeout(resolve, 200)); // Longer delay for writes
        
        if (!templateData.name) throw new Error('Template name is required');
        if (!templateData.content) throw new Error('Template content is required');
        
        const newTemplate: DMCATemplate = {
          id: `template-${nextId++}`,
          name: templateData.name,
          description: templateData.description || '',
          category: templateData.category || 'General DMCA',
          content: templateData.content,
          variables: templateData.variables || [],
          is_active: templateData.is_active !== false,
          is_system: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          usage_count: 0,
          tags: templateData.tags || [],
          language: templateData.language || 'en',
          jurisdiction: templateData.jurisdiction || 'US'
        };
        
        mockTemplates.push(newTemplate);
        return newTemplate;
      }),
      
      updateTemplate: vi.fn().mockImplementation(async (id: string, updates) => {
        await new Promise(resolve => setTimeout(resolve, 200));
        
        const templateIndex = mockTemplates.findIndex(t => t.id === id);
        if (templateIndex === -1) throw new Error('Template not found');
        
        const updatedTemplate = {
          ...mockTemplates[templateIndex],
          ...updates,
          updated_at: new Date().toISOString()
        };
        
        mockTemplates[templateIndex] = updatedTemplate;
        return updatedTemplate;
      }),
      
      deleteTemplate: vi.fn().mockImplementation(async (id: string) => {
        await new Promise(resolve => setTimeout(resolve, 150));
        
        const templateIndex = mockTemplates.findIndex(t => t.id === id);
        if (templateIndex === -1) throw new Error('Template not found');
        
        mockTemplates.splice(templateIndex, 1);
        return { success: true };
      }),
      
      bulkUpdateTemplates: vi.fn().mockImplementation(async (ids: string[], updates) => {
        await new Promise(resolve => setTimeout(resolve, 300));
        
        const updatedTemplates = mockTemplates.map(template => {
          if (ids.includes(template.id)) {
            return {
              ...template,
              ...updates,
              updated_at: new Date().toISOString()
            };
          }
          return template;
        });
        
        mockTemplates = updatedTemplates;
        return { updated: ids.length };
      }),
      
      // Draft management
      saveDraft: vi.fn().mockImplementation(async (draftData) => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return { id: 'draft-1', saved_at: new Date().toISOString() };
      }),
      
      getDraft: vi.fn().mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
        return null; // No draft by default
      }),
      
      deleteDraft: vi.fn().mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
        return { success: true };
      }),
      
      // Template starters
      getTemplateStarters: vi.fn().mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return [
          {
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
            language: 'en'
          }
        ];
      }),
      
      // Test helpers to control mock state
      __setMockTemplates: (templates: DMCATemplate[]) => {
        mockTemplates = [...templates];
      },
      
      __setMockCategories: (categories: TemplateCategory[]) => {
        mockCategories = [...categories];
      },
      
      __resetMocks: () => {
        mockTemplates = [];
        mockCategories = [];
        nextId = 1;
      },
      
      __getMockTemplates: () => [...mockTemplates]
    }
  };
});

// Helper to create test wrapper with React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Test data factories
const createMockTemplate = (overrides: Partial<DMCATemplate> = {}): DMCATemplate => ({
  id: 'template-1',
  name: 'Test Template',
  description: 'A test template for integration testing',
  category: 'General DMCA',
  content: 'Dear {{platform}}, I am writing to report copyright infringement of my work "{{work_title}}"...',
  variables: [
    { name: 'platform', label: 'Platform Name', type: 'text', required: true },
    { name: 'work_title', label: 'Work Title', type: 'text', required: true }
  ],
  is_active: true,
  is_system: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  usage_count: 0,
  tags: ['test'],
  language: 'en',
  jurisdiction: 'US',
  ...overrides
});

const createMockCategory = (overrides: Partial<TemplateCategory> = {}): TemplateCategory => ({
  id: 'cat-1',
  name: 'General DMCA',
  description: 'General purpose DMCA templates',
  template_count: 5,
  icon: 'pi-file',
  color: '#007bff',
  ...overrides
});

describe('Template Integration Tests', () => {
  const Wrapper = createWrapper();

  beforeEach(() => {
    (templatesApi as any).__resetMocks();
    vi.clearAllMocks();
  });

  describe('Complete Template Lifecycle', () => {
    it('should create, edit, and delete a template through the UI', async () => {
      const user = userEvent.setup();
      
      // Set up initial state
      (templatesApi as any).__setMockCategories([
        createMockCategory({ name: 'Social Media' })
      ]);

      const mockProps = {
        onTemplateEdit: vi.fn(),
        onTemplateCreate: vi.fn(),
        onTemplateView: vi.fn(),
      };

      // Start with empty template list
      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Should show empty state initially
      await waitFor(() => {
        expect(screen.getByText(/no templates found/i)).toBeInTheDocument();
      });

      // Click create template button
      const createButton = screen.getByRole('button', { name: /create template/i });
      await user.click(createButton);

      expect(mockProps.onTemplateCreate).toHaveBeenCalled();

      // Simulate template creation through wizard
      const template = createMockTemplate({
        name: 'New Integration Test Template',
        category: 'Social Media'
      });
      
      (templatesApi as any).__setMockTemplates([template]);

      // Re-render dashboard to show new template
      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Should now show the created template
      await waitFor(() => {
        expect(screen.getByText('New Integration Test Template')).toBeInTheDocument();
      });

      // Edit the template
      const editButton = screen.getByLabelText(/edit.*new integration test template/i);
      await user.click(editButton);

      expect(mockProps.onTemplateEdit).toHaveBeenCalledWith(template);

      // Simulate editing
      const updatedTemplate = { ...template, name: 'Updated Template Name' };
      (templatesApi as any).__setMockTemplates([updatedTemplate]);

      // Re-render to show updated template
      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText('Updated Template Name')).toBeInTheDocument();
      });

      // Delete the template
      const checkbox = screen.getByRole('checkbox', { name: /select.*updated template name/i });
      await user.click(checkbox);

      const deleteButton = screen.getByRole('button', { name: /delete selected/i });
      await user.click(deleteButton);

      const confirmButton = await screen.findByRole('button', { name: /yes.*delete/i });
      await user.click(confirmButton);

      // Template should be removed
      await waitFor(() => {
        expect(templatesApi.deleteTemplate).toHaveBeenCalledWith(template.id);
      });

      // Should show empty state again
      (templatesApi as any).__setMockTemplates([]);
      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText(/no templates found/i)).toBeInTheDocument();
      });
    });

    it('should handle wizard to editor workflow', async () => {
      const user = userEvent.setup();
      
      const wizardProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      // Start wizard
      render(<TemplateCreationWizard {...wizardProps} />, { wrapper: Wrapper });

      // Complete wizard flow
      await waitFor(() => {
        expect(screen.getByText('Social Media DMCA')).toBeInTheDocument();
      });

      // Select starter
      const starterCard = screen.getByText('Social Media DMCA').closest('.starter-card');
      await user.click(starterCard!);

      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      // Fill basic info
      await waitFor(() => {
        expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(/template name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Wizard to Editor Test');

      const descInput = screen.getByLabelText(/description/i);
      await user.type(descInput, 'Created through wizard');

      // Continue to final step
      await user.click(nextButton); // Content step
      await user.click(nextButton); // Variables step
      await user.click(nextButton); // Preview step

      // Save template
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should create template via API
      await waitFor(() => {
        expect(templatesApi.createTemplate).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Wizard to Editor Test',
            description: 'Created through wizard'
          })
        );
      });

      // Simulate opening in editor for further editing
      const createdTemplate = (templatesApi as any).__getMockTemplates()[0];
      
      const editorProps = {
        template: createdTemplate,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Should populate with template data
      await waitFor(() => {
        expect(screen.getByDisplayValue('Wizard to Editor Test')).toBeInTheDocument();
      });

      // Make additional changes
      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, ' Additional content added in editor.');

      // Save changes
      const editorSaveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(editorSaveButton);

      // Should update template
      await waitFor(() => {
        expect(templatesApi.updateTemplate).toHaveBeenCalledWith(
          createdTemplate.id,
          expect.objectContaining({
            content: expect.stringContaining('Additional content added in editor.')
          })
        );
      });
    });
  });

  describe('Search and Filter Integration', () => {
    beforeEach(() => {
      const templates = [
        createMockTemplate({ 
          id: '1', 
          name: 'YouTube DMCA Template', 
          category: 'Video Platforms',
          tags: ['youtube', 'video']
        }),
        createMockTemplate({ 
          id: '2', 
          name: 'Instagram Copyright Notice', 
          category: 'Social Media',
          tags: ['instagram', 'image']
        }),
        createMockTemplate({ 
          id: '3', 
          name: 'General DMCA Takedown', 
          category: 'General DMCA',
          tags: ['general']
        }),
      ];
      
      (templatesApi as any).__setMockTemplates(templates);
      (templatesApi as any).__setMockCategories([
        createMockCategory({ name: 'Video Platforms' }),
        createMockCategory({ name: 'Social Media' }),
        createMockCategory({ name: 'General DMCA' }),
      ]);
    });

    it('should filter templates by search term', async () => {
      const user = userEvent.setup();
      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('YouTube DMCA Template')).toBeInTheDocument();
        expect(screen.getByText('Instagram Copyright Notice')).toBeInTheDocument();
        expect(screen.getByText('General DMCA Takedown')).toBeInTheDocument();
      });

      // Search for "YouTube"
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.type(searchInput, 'YouTube');

      // Should filter results
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'YouTube' })
        );
      });

      // Only YouTube template should be visible in new render
      expect(screen.getByText('YouTube DMCA Template')).toBeInTheDocument();
    });

    it('should filter by category', async () => {
      const user = userEvent.setup();
      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Wait for categories to load
      await waitFor(() => {
        expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
      });

      // Select Social Media category
      const categoryDropdown = screen.getByLabelText(/category/i);
      await user.click(categoryDropdown);
      
      const socialMediaOption = screen.getByText('Social Media');
      await user.click(socialMediaOption);

      // Should call API with category filter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ category: 'Social Media' })
        );
      });
    });

    it('should combine multiple filters', async () => {
      const user = userEvent.setup();
      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Apply search filter
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.type(searchInput, 'DMCA');

      // Apply category filter
      const categoryDropdown = screen.getByLabelText(/category/i);
      await user.selectOptions(categoryDropdown, 'General DMCA');

      // Apply status filter
      const statusDropdown = screen.getByLabelText(/status/i);
      await user.selectOptions(statusDropdown, 'active');

      // Should combine all filters in API call
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'DMCA',
            category: 'General DMCA',
            is_active: true
          })
        );
      });
    });
  });

  describe('Template Validation Integration', () => {
    it('should validate template during creation and show results', async () => {
      const user = userEvent.setup();
      
      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Fill template data
      await user.type(screen.getByLabelText(/template name/i), 'Validation Test Template');
      await user.type(screen.getByLabelText(/description/i), 'Testing validation integration');

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, 'This is a copyright infringement notice made in good faith under penalty of perjury.');

      // Trigger validation
      await waitFor(() => {
        expect(templatesApi.validateTemplate).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Validation Test Template',
            content: expect.stringContaining('copyright infringement')
          })
        );
      });

      // Should show compliance score
      await waitFor(() => {
        expect(screen.getByText(/compliance.*100/i)).toBeInTheDocument();
      });
    });

    it('should show validation errors and prevent saving invalid templates', async () => {
      const user = userEvent.setup();
      
      // Mock validation to return errors
      (templatesApi.validateTemplate as vi.Mock).mockResolvedValue({
        is_valid: false,
        errors: ['Template content is required', 'Missing copyright statement'],
        warnings: ['Template is quite short'],
        compliance_score: 25
      });

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Fill incomplete template data
      await user.type(screen.getByLabelText(/template name/i), 'Invalid Template');
      await user.type(screen.getByLabelText(/description/i), 'Testing validation errors');

      const contentEditor = screen.getByRole('textbox', { name: /content/i });
      await user.type(contentEditor, 'Short content');

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/missing copyright statement/i)).toBeInTheDocument();
        expect(screen.getByText(/template is quite short/i)).toBeInTheDocument();
      });

      // Try to save
      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should show validation prevents save
      await waitFor(() => {
        expect(screen.getByText(/please fix validation errors/i)).toBeInTheDocument();
      });

      // Should not call create API
      expect(templatesApi.createTemplate).not.toHaveBeenCalled();
    });
  });

  describe('Preview Integration', () => {
    it('should generate and update preview with variable values', async () => {
      const user = userEvent.setup();
      
      const template = createMockTemplate({
        content: 'Dear {{platform}} Team,\n\nI am reporting infringement of "{{work_title}}".',
        variables: [
          { name: 'platform', label: 'Platform', type: 'text', required: true },
          { name: 'work_title', label: 'Work Title', type: 'text', required: true }
        ]
      });

      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Wait for preview to load
      await waitFor(() => {
        expect(templatesApi.getTemplatePreview).toHaveBeenCalled();
      });

      // Should show preview with variables
      expect(screen.getByTestId('preview-panel')).toBeInTheDocument();

      // Update test values
      const platformInput = screen.getByLabelText(/test.*platform/i);
      await user.clear(platformInput);
      await user.type(platformInput, 'YouTube');

      const workTitleInput = screen.getByLabelText(/test.*work.*title/i);
      await user.clear(workTitleInput);
      await user.type(workTitleInput, 'My Original Song');

      // Refresh preview
      const refreshButton = screen.getByRole('button', { name: /refresh preview/i });
      await user.click(refreshButton);

      // Should call preview API with test values
      await waitFor(() => {
        expect(templatesApi.getTemplatePreview).toHaveBeenCalledWith(
          expect.objectContaining({
            values: {
              platform: 'YouTube',
              work_title: 'My Original Song'
            }
          })
        );
      });
    });

    it('should handle preview errors gracefully', async () => {
      (templatesApi.getTemplatePreview as vi.Mock).mockRejectedValue(
        new Error('Preview generation failed')
      );

      const template = createMockTemplate();
      const editorProps = {
        template,
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'edit' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Should show preview error state
      await waitFor(() => {
        expect(screen.getByText(/preview.*error/i)).toBeInTheDocument();
      });

      // Should provide retry option
      expect(screen.getByRole('button', { name: /retry.*preview/i })).toBeInTheDocument();
    });
  });

  describe('Bulk Operations Integration', () => {
    beforeEach(() => {
      const templates = [
        createMockTemplate({ id: '1', name: 'Template 1' }),
        createMockTemplate({ id: '2', name: 'Template 2' }),
        createMockTemplate({ id: '3', name: 'Template 3' }),
      ];
      
      (templatesApi as any).__setMockTemplates(templates);
    });

    it('should perform bulk status updates', async () => {
      const user = userEvent.setup();
      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Wait for templates to load
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
      });

      // Select multiple templates
      const selectAll = screen.getByRole('checkbox', { name: /select all/i });
      await user.click(selectAll);

      // Should show bulk actions
      await waitFor(() => {
        expect(screen.getByText(/3 selected/i)).toBeInTheDocument();
      });

      // Deactivate selected templates
      const deactivateButton = screen.getByRole('button', { name: /deactivate selected/i });
      await user.click(deactivateButton);

      const confirmButton = await screen.findByRole('button', { name: /yes.*deactivate/i });
      await user.click(confirmButton);

      // Should call bulk update API
      await waitFor(() => {
        expect(templatesApi.bulkUpdateTemplates).toHaveBeenCalledWith(
          ['1', '2', '3'],
          { is_active: false }
        );
      });
    });

    it('should handle bulk delete operations', async () => {
      const user = userEvent.setup();
      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Wait for templates and select some
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
      });

      const checkbox1 = screen.getByRole('checkbox', { name: /select.*template 1/i });
      const checkbox2 = screen.getByRole('checkbox', { name: /select.*template 2/i });
      
      await user.click(checkbox1);
      await user.click(checkbox2);

      // Delete selected
      const deleteButton = screen.getByRole('button', { name: /delete selected/i });
      await user.click(deleteButton);

      const confirmButton = await screen.findByRole('button', { name: /yes.*delete/i });
      await user.click(confirmButton);

      // Should call delete for each template
      await waitFor(() => {
        expect(templatesApi.deleteTemplate).toHaveBeenCalledTimes(2);
        expect(templatesApi.deleteTemplate).toHaveBeenCalledWith('1');
        expect(templatesApi.deleteTemplate).toHaveBeenCalledWith('2');
      });
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle API errors during template loading', async () => {
      (templatesApi.getTemplates as vi.Mock).mockRejectedValue(
        new Error('Server unavailable')
      );

      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Should show error state
      await waitFor(() => {
        expect(screen.getByText(/error loading templates/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('should handle network errors during template creation', async () => {
      const user = userEvent.setup();
      
      (templatesApi.createTemplate as vi.Mock).mockRejectedValue(
        new Error('Network error')
      );

      const editorProps = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn(),
        mode: 'create' as const,
      };

      render(<EnhancedTemplateEditor {...editorProps} />, { wrapper: Wrapper });

      // Fill and try to save
      await user.type(screen.getByLabelText(/template name/i), 'Network Test');
      await user.type(screen.getByLabelText(/description/i), 'Testing network error');
      await user.type(screen.getByRole('textbox', { name: /content/i }), 'Template content');

      const saveButton = screen.getByRole('button', { name: /save template/i });
      await user.click(saveButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      });
    });

    it('should retry failed operations', async () => {
      const user = userEvent.setup();
      
      // Mock initial failure then success
      (templatesApi.getTemplates as vi.Mock)
        .mockRejectedValueOnce(new Error('Temporary failure'))
        .mockResolvedValue({ templates: [], total: 0, page: 1, limit: 20, total_pages: 0, has_next: false, has_prev: false });

      const mockProps = { onTemplateEdit: vi.fn(), onTemplateCreate: vi.fn(), onTemplateView: vi.fn() };

      render(<TemplateLibraryDashboard {...mockProps} />, { wrapper: Wrapper });

      // Should show error state
      await waitFor(() => {
        expect(screen.getByText(/error loading templates/i)).toBeInTheDocument();
      });

      // Click retry
      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      // Should succeed on retry
      await waitFor(() => {
        expect(screen.queryByText(/error loading templates/i)).not.toBeInTheDocument();
      });

      // Should have called API twice
      expect(templatesApi.getTemplates).toHaveBeenCalledTimes(2);
    });
  });
});