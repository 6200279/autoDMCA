import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TemplateLibraryDashboard from '../TemplateLibraryDashboard';
import { templatesApi } from '../../../services/api';
import { DMCATemplate, TemplateCategory, PaginatedTemplatesResponse } from '../../../types/templates';
import '@testing-library/jest-dom';

// Mock the API
vi.mock('../../../services/api', () => ({
  templatesApi: {
    getTemplates: vi.fn(),
    getCategories: vi.fn(),
    deleteTemplate: vi.fn(),
    bulkUpdateTemplates: vi.fn(),
    updateTemplate: vi.fn(),
  }
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Test data factories
const createMockTemplate = (overrides: Partial<DMCATemplate> = {}): DMCATemplate => ({
  id: 'template-1',
  name: 'Test Template',
  description: 'A test template for DMCA takedowns',
  category: 'General DMCA',
  content: 'Dear {{platform}}, I am writing to report copyright infringement...',
  variables: [
    {
      name: 'platform',
      label: 'Platform Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., YouTube, Instagram'
    }
  ],
  is_active: true,
  is_system: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  usage_count: 0,
  tags: ['social-media', 'general'],
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

const createMockPaginatedResponse = (
  templates: DMCATemplate[] = [],
  overrides: Partial<PaginatedTemplatesResponse> = {}
): PaginatedTemplatesResponse => ({
  templates,
  total: templates.length,
  page: 1,
  limit: 20,
  total_pages: 1,
  has_next: false,
  has_prev: false,
  ...overrides
});

describe('TemplateLibraryDashboard', () => {
  const mockProps = {
    onTemplateEdit: vi.fn(),
    onTemplateCreate: vi.fn(),
    onTemplateView: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default API responses
    (templatesApi.getTemplates as any).mockResolvedValue(
      createMockPaginatedResponse([createMockTemplate()])
    );
    (templatesApi.getCategories as any).mockResolvedValue([createMockCategory()]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render the dashboard with loading state initially', () => {
      render(<TemplateLibraryDashboard {...mockProps} />);
      
      expect(screen.getByText('Template Library')).toBeInTheDocument();
      expect(screen.getAllByTestId(/skeleton/i)).toHaveLength.toBeGreaterThan(0);
    });

    it('should render templates after loading', async () => {
      const template = createMockTemplate({ name: 'Social Media Template' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText('Social Media Template')).toBeInTheDocument();
      });
    });

    it('should render empty state when no templates exist', async () => {
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText(/no templates found/i)).toBeInTheDocument();
        expect(screen.getByText(/create your first template/i)).toBeInTheDocument();
      });
    });

    it('should render error state when API fails', async () => {
      (templatesApi.getTemplates as any).mockRejectedValue(new Error('API Error'));

      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByText(/error loading templates/i)).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('should filter templates based on search input', async () => {
      const user = userEvent.setup();
      const templates = [
        createMockTemplate({ id: '1', name: 'YouTube Template' }),
        createMockTemplate({ id: '2', name: 'Instagram Template' }),
      ];
      
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse(templates)
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('YouTube Template')).toBeInTheDocument();
        expect(screen.getByText('Instagram Template')).toBeInTheDocument();
      });

      // Search for YouTube
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.type(searchInput, 'YouTube');

      // Verify API is called with search parameter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ search: 'YouTube' })
        );
      });
    });

    it('should debounce search input to prevent excessive API calls', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      render(<TemplateLibraryDashboard {...mockProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      
      // Type multiple characters quickly
      await user.type(searchInput, 'test');
      
      // Fast-forward time by less than debounce delay
      vi.advanceTimersByTime(200);
      
      // Should not have been called yet (initial load + debounced call not triggered)
      expect(templatesApi.getTemplates).toHaveBeenCalledTimes(1);
      
      // Fast-forward past debounce delay
      vi.advanceTimersByTime(500);
      
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledTimes(2);
      });

      vi.useRealTimers();
    });

    it('should show search suggestions', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.click(searchInput);
      await user.type(searchInput, 'yo');

      // Should show suggestions (mocked in component)
      await waitFor(() => {
        const suggestionList = screen.getByRole('listbox');
        expect(suggestionList).toBeInTheDocument();
      });
    });
  });

  describe('Filtering', () => {
    it('should filter by category', async () => {
      const user = userEvent.setup();
      const categories = [
        createMockCategory({ id: '1', name: 'Social Media' }),
        createMockCategory({ id: '2', name: 'Search Engines' }),
      ];

      (templatesApi.getCategories as any).mockResolvedValue(categories);

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for categories to load
      await waitFor(() => {
        expect(screen.getByText('Category')).toBeInTheDocument();
      });

      // Open category dropdown and select
      const categoryDropdown = screen.getByLabelText(/category/i);
      await user.click(categoryDropdown);
      
      const socialMediaOption = screen.getByText('Social Media');
      await user.click(socialMediaOption);

      // Verify API is called with category filter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ category: 'Social Media' })
        );
      });
    });

    it('should filter by status (active/inactive/favorites)', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Find and click status filter dropdown
      const statusDropdown = screen.getByLabelText(/status/i);
      await user.click(statusDropdown);

      // Select "Active Only"
      const activeOption = screen.getByText('Active Only');
      await user.click(activeOption);

      // Verify API is called with active filter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ is_active: true })
        );
      });
    });

    it('should clear all filters when clear button is clicked', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Set some filters first
      const searchInput = screen.getByPlaceholderText(/search templates/i);
      await user.type(searchInput, 'test search');

      // Click clear filters button
      const clearButton = screen.getByText(/clear filters/i);
      await user.click(clearButton);

      // Verify filters are reset
      expect(searchInput).toHaveValue('');
      
      // Verify API is called without filters
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({
            search: '',
            category: '',
            language: '',
            jurisdiction: '',
            is_active: undefined
          })
        );
      });
    });
  });

  describe('View Modes', () => {
    it('should switch between grid and list view modes', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Initially should be in grid mode
      const gridToggle = screen.getByLabelText(/grid view/i);
      expect(gridToggle).toBeInTheDocument();

      // Switch to list view
      const listToggle = screen.getByLabelText(/list view/i);
      await user.click(listToggle);

      // Should now show list view
      await waitFor(() => {
        expect(screen.getByTestId('templates-list-view')).toBeInTheDocument();
      });

      // Switch back to grid view
      await user.click(gridToggle);

      await waitFor(() => {
        expect(screen.getByTestId('templates-grid-view')).toBeInTheDocument();
      });
    });

    it('should adjust grid size in grid view mode', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Find grid size controls
      const smallGridButton = screen.getByLabelText(/small grid/i);
      const mediumGridButton = screen.getByLabelText(/medium grid/i);
      const largeGridButton = screen.getByLabelText(/large grid/i);

      // Test switching to small grid
      await user.click(smallGridButton);
      
      const gridContainer = screen.getByTestId('templates-grid-view');
      expect(gridContainer).toHaveClass('grid-small');

      // Test switching to large grid
      await user.click(largeGridButton);
      expect(gridContainer).toHaveClass('grid-large');
    });
  });

  describe('Sorting', () => {
    it('should sort templates by different criteria', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Find sort dropdown
      const sortDropdown = screen.getByLabelText(/sort by/i);
      await user.click(sortDropdown);

      // Select "Name" sorting
      const nameOption = screen.getByText(/name/i);
      await user.click(nameOption);

      // Verify API is called with sort parameter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({
            sort_by: 'name',
            sort_order: 'desc'
          })
        );
      });
    });

    it('should toggle sort order when clicking the same sort option', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Click sort order toggle button
      const sortOrderToggle = screen.getByLabelText(/sort order/i);
      await user.click(sortOrderToggle);

      // Should switch from desc to asc
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ sort_order: 'asc' })
        );
      });
    });
  });

  describe('Pagination', () => {
    it('should handle pagination correctly', async () => {
      const user = userEvent.setup();
      const templates = Array.from({ length: 25 }, (_, i) => 
        createMockTemplate({ id: `template-${i}`, name: `Template ${i}` })
      );

      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse(
          templates.slice(0, 20), 
          { total: 25, has_next: true, total_pages: 2 }
        )
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Template 0')).toBeInTheDocument();
      });

      // Should show pagination controls
      const paginator = screen.getByRole('navigation');
      expect(paginator).toBeInTheDocument();

      // Click next page
      const nextButton = within(paginator).getByLabelText(/next page/i);
      await user.click(nextButton);

      // Verify API is called with page parameter
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ page: 2 })
        );
      });
    });

    it('should change rows per page', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Find rows per page dropdown
      const rowsDropdown = screen.getByLabelText(/items per page/i);
      await user.click(rowsDropdown);

      // Select 50 items per page
      const fiftyOption = screen.getByText('50');
      await user.click(fiftyOption);

      // Verify API is called with new limit
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledWith(
          expect.objectContaining({ limit: 50 })
        );
      });
    });
  });

  describe('Selection and Bulk Operations', () => {
    it('should allow single template selection', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate({ name: 'Selectable Template' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for template to load
      await waitFor(() => {
        expect(screen.getByText('Selectable Template')).toBeInTheDocument();
      });

      // Find and click selection checkbox
      const checkbox = screen.getByRole('checkbox', { name: /select template/i });
      await user.click(checkbox);

      // Should show bulk actions
      await waitFor(() => {
        expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
        expect(screen.getByText(/bulk actions/i)).toBeInTheDocument();
      });
    });

    it('should allow select all functionality', async () => {
      const user = userEvent.setup();
      const templates = [
        createMockTemplate({ id: '1', name: 'Template 1' }),
        createMockTemplate({ id: '2', name: 'Template 2' }),
      ];
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse(templates)
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for templates to load
      await waitFor(() => {
        expect(screen.getByText('Template 1')).toBeInTheDocument();
        expect(screen.getByText('Template 2')).toBeInTheDocument();
      });

      // Find and click select all checkbox
      const selectAllCheckbox = screen.getByRole('checkbox', { name: /select all/i });
      await user.click(selectAllCheckbox);

      // Should show all selected
      await waitFor(() => {
        expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
      });
    });

    it('should perform bulk delete operation', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate({ name: 'Delete Me' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );
      (templatesApi.deleteTemplate as any).mockResolvedValue({});

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for template and select it
      await waitFor(() => {
        expect(screen.getByText('Delete Me')).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox', { name: /select template/i });
      await user.click(checkbox);

      // Click bulk delete
      const deleteButton = screen.getByText(/delete selected/i);
      await user.click(deleteButton);

      // Confirm deletion in dialog
      const confirmButton = await screen.findByText(/yes.*delete/i);
      await user.click(confirmButton);

      // Verify API is called
      await waitFor(() => {
        expect(templatesApi.deleteTemplate).toHaveBeenCalledWith(template.id);
      });
    });
  });

  describe('Template Actions', () => {
    it('should call onTemplateView when view button is clicked', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate({ name: 'Viewable Template' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for template and click view
      await waitFor(() => {
        expect(screen.getByText('Viewable Template')).toBeInTheDocument();
      });

      const viewButton = screen.getByLabelText(/view template/i);
      await user.click(viewButton);

      expect(mockProps.onTemplateView).toHaveBeenCalledWith(template);
    });

    it('should call onTemplateEdit when edit button is clicked', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate({ name: 'Editable Template' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for template and click edit
      await waitFor(() => {
        expect(screen.getByText('Editable Template')).toBeInTheDocument();
      });

      const editButton = screen.getByLabelText(/edit template/i);
      await user.click(editButton);

      expect(mockProps.onTemplateEdit).toHaveBeenCalledWith(template);
    });

    it('should toggle favorite status', async () => {
      const user = userEvent.setup();
      const template = createMockTemplate({ name: 'Favorite Template' });
      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse([template])
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Wait for template and click favorite
      await waitFor(() => {
        expect(screen.getByText('Favorite Template')).toBeInTheDocument();
      });

      const favoriteButton = screen.getByLabelText(/add to favorites/i);
      await user.click(favoriteButton);

      // Should update local state (favorites stored in localStorage)
      expect(favoriteButton).toHaveAttribute('aria-label', 'Remove from favorites');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', async () => {
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Main heading
      expect(screen.getByRole('heading', { name: /template library/i })).toBeInTheDocument();

      // Search input
      expect(screen.getByLabelText(/search templates/i)).toBeInTheDocument();

      // Filter controls
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/status/i)).toBeInTheDocument();

      // View mode toggles
      expect(screen.getByLabelText(/grid view/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/list view/i)).toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Tab through main controls
      await user.tab(); // Search input
      expect(screen.getByPlaceholderText(/search templates/i)).toHaveFocus();

      await user.tab(); // Category filter
      expect(screen.getByLabelText(/category/i)).toHaveFocus();

      await user.tab(); // Status filter
      expect(screen.getByLabelText(/status/i)).toHaveFocus();
    });

    it('should announce loading and error states to screen readers', async () => {
      render(<TemplateLibraryDashboard {...mockProps} />);

      // Loading state should have proper aria-live region
      expect(screen.getByLabelText(/loading templates/i)).toBeInTheDocument();

      // Mock API error
      (templatesApi.getTemplates as any).mockRejectedValue(new Error('API Error'));
      
      // Re-render to trigger error state
      render(<TemplateLibraryDashboard {...mockProps} />);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should adapt layout for mobile screens', async () => {
      // Mock smaller viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Should show mobile sidebar toggle
      expect(screen.getByLabelText(/open filters/i)).toBeInTheDocument();
      
      // Grid should use single column on mobile
      await waitFor(() => {
        const gridContainer = screen.getByTestId('templates-grid-view');
        expect(gridContainer).toHaveClass('mobile-single-column');
      });
    });

    it('should show/hide sidebar filters on mobile', async () => {
      const user = userEvent.setup();
      
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Click sidebar toggle
      const sidebarToggle = screen.getByLabelText(/open filters/i);
      await user.click(sidebarToggle);

      // Sidebar should be visible
      await waitFor(() => {
        expect(screen.getByRole('complementary')).toBeVisible();
      });
    });
  });

  describe('Performance', () => {
    it('should not make excessive API calls during rapid interactions', async () => {
      const user = userEvent.setup();
      vi.useFakeTimers();

      render(<TemplateLibraryDashboard {...mockProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);

      // Type quickly (should be debounced)
      await user.type(searchInput, 'rapid typing test');
      
      // Before debounce delay
      vi.advanceTimersByTime(200);
      expect(templatesApi.getTemplates).toHaveBeenCalledTimes(1); // Initial load only

      // After debounce delay
      vi.advanceTimersByTime(400);
      
      await waitFor(() => {
        expect(templatesApi.getTemplates).toHaveBeenCalledTimes(2); // Initial + debounced search
      });

      vi.useRealTimers();
    });

    it('should virtualize large lists when in list view', async () => {
      const user = userEvent.setup();
      const largeTemplateList = Array.from({ length: 100 }, (_, i) => 
        createMockTemplate({ id: `template-${i}`, name: `Template ${i}` })
      );

      (templatesApi.getTemplates as any).mockResolvedValue(
        createMockPaginatedResponse(largeTemplateList)
      );

      render(<TemplateLibraryDashboard {...mockProps} />);

      // Switch to list view
      const listToggle = screen.getByLabelText(/list view/i);
      await user.click(listToggle);

      await waitFor(() => {
        // Should use virtual scrolling for large lists
        const listContainer = screen.getByTestId('templates-list-view');
        expect(listContainer).toHaveAttribute('data-virtualized', 'true');
      });
    });
  });
});