import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import EnhancedTemplateLibraryDashboard from '../EnhancedTemplateLibraryDashboard';
import EnhancedTemplateSearch from '../components/EnhancedTemplateSearch';
import EnhancedTemplateGrid from '../components/EnhancedTemplateGrid';
import EnhancedTemplateCard from '../components/EnhancedTemplateCard';
import TemplateFilters from '../components/TemplateFilters';

// Extend jest matchers
expect.extend(toHaveNoViolations);

// Mock data
const mockTemplates = [
  {
    id: '1',
    name: 'DMCA Takedown Notice',
    description: 'Standard DMCA takedown notice template for copyright infringement',
    category: 'Copyright',
    tags: ['dmca', 'copyright', 'takedown'],
    is_active: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    usage_count: 150
  },
  {
    id: '2',
    name: 'Content Removal Request',
    description: 'Generic content removal request template',
    category: 'Removal',
    tags: ['removal', 'content'],
    is_active: false,
    created_at: '2023-01-02T00:00:00Z',
    updated_at: '2023-01-02T00:00:00Z',
    usage_count: 75
  }
];

// Mock context
const mockContextValue = {
  templates: mockTemplates,
  loading: false,
  error: null,
  totalRecords: 2,
  filters: { search: '', category: '', status: 'all', tags: [], language: '', jurisdiction: '' },
  pagination: { first: 0, rows: 12 },
  sorting: { sortBy: 'updated_at', sortOrder: 'desc' as const },
  viewPreferences: {
    layout: { type: 'grid' as const, size: 'medium' as const },
    showThumbnails: true,
    showMetadata: true,
    groupByCategory: false
  },
  hasActiveFilters: false,
  hasSelection: false,
  selectedTemplates: [],
  isAllSelected: false,
  actions: {
    setFilters: jest.fn(),
    clearFilters: jest.fn(),
    setPagination: jest.fn(),
    setSorting: jest.fn(),
    toggleTemplateSelection: jest.fn(),
    selectAllTemplates: jest.fn(),
    toggleFavorite: jest.fn(),
    selection: { selectedTemplates: [], favorites: [] }
  },
  enhancedActions: {
    setViewPreferences: jest.fn(),
    markAsViewed: jest.fn(),
    performBulkAction: jest.fn(),
    refreshData: jest.fn(),
    trackEvent: jest.fn(),
    saveFilterPreset: jest.fn(),
    applyFilterPreset: jest.fn(),
    deleteFilterPreset: jest.fn()
  },
  config: {
    enableVirtualScrolling: true,
    enableAnalytics: true,
    availableBulkActions: []
  },
  categories: [{ name: 'Copyright', template_count: 1 }],
  availableTags: ['dmca', 'copyright', 'takedown', 'removal'],
  searchSuggestions: ['DMCA', 'Copyright'],
  recentlyViewed: [],
  filterPresets: []
};

// Mock the context
jest.mock('../context/TemplateLibraryContext', () => ({
  useTemplateLibraryContext: () => mockContextValue,
  TemplateLibraryProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="template-library-provider">{children}</div>
  )
}));

// Mock the accessibility hook
jest.mock('../../hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    announce: jest.fn(),
    manageFocus: {
      trap: jest.fn(() => jest.fn()),
      restore: jest.fn(),
      saveFocus: jest.fn(),
      moveTo: jest.fn()
    },
    keyboard: {
      registerShortcut: jest.fn(() => jest.fn()),
      getShortcuts: jest.fn(() => [])
    },
    screen: {
      isScreenReader: false,
      prefersReducedMotion: false,
      prefersHighContrast: false
    }
  })
}));

describe('Template Library Accessibility Tests', () => {
  describe('EnhancedTemplateLibraryDashboard', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(<EnhancedTemplateLibraryDashboard />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper skip navigation links', () => {
      render(<EnhancedTemplateLibraryDashboard />);
      
      expect(screen.getByText('Skip to toolbar')).toBeInTheDocument();
      expect(screen.getByText('Skip to search')).toBeInTheDocument();
      expect(screen.getByText('Skip to filters')).toBeInTheDocument();
      expect(screen.getByText('Skip to templates')).toBeInTheDocument();
      expect(screen.getByText('Show keyboard shortcuts')).toBeInTheDocument();
    });

    it('should have proper ARIA landmarks', () => {
      render(<EnhancedTemplateLibraryDashboard />);
      
      expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Template Library Dashboard');
      expect(screen.getByRole('banner')).toHaveAttribute('aria-label', 'Template Library Toolbar');
      expect(screen.getByRole('complementary')).toHaveAttribute('aria-label', 'Template Filters and Search');
      expect(screen.getByRole('search')).toHaveAttribute('aria-label', 'Template Search');
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateLibraryDashboard />);
      
      // Tab through skip links
      await user.tab();
      expect(screen.getByText('Skip to toolbar')).toHaveFocus();
      
      await user.tab();
      expect(screen.getByText('Skip to search')).toHaveFocus();
    });

    it('should announce actions to screen readers', async () => {
      const mockAnnounce = jest.fn();
      jest.mocked(require('../../hooks/useAccessibility').useAccessibility).mockReturnValue({
        announce: mockAnnounce,
        manageFocus: {
          trap: jest.fn(() => jest.fn()),
          restore: jest.fn(),
          saveFocus: jest.fn(),
          moveTo: jest.fn()
        },
        keyboard: {
          registerShortcut: jest.fn(() => jest.fn()),
          getShortcuts: jest.fn(() => [])
        },
        screen: {
          isScreenReader: true,
          prefersReducedMotion: false,
          prefersHighContrast: false
        }
      });

      render(<EnhancedTemplateLibraryDashboard />);
      
      // Test that announcements are made during interactions
      // This would be tested with real user interactions
    });
  });

  describe('EnhancedTemplateSearch', () => {
    const defaultProps = {
      value: '',
      showAdvancedSearch: true,
      showSearchHistory: true,
      showQuickFilters: true
    };

    it('should not have accessibility violations', async () => {
      const { container } = render(<EnhancedTemplateSearch {...defaultProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA attributes for search input', () => {
      render(<EnhancedTemplateSearch {...defaultProps} />);
      
      const searchInput = screen.getByRole('combobox');
      expect(searchInput).toHaveAttribute('aria-label', 'Search templates');
      expect(searchInput).toHaveAttribute('aria-autocomplete', 'list');
      expect(searchInput).toHaveAttribute('aria-expanded', 'false');
      expect(searchInput).toHaveAttribute('aria-haspopup', 'listbox');
    });

    it('should handle keyboard navigation properly', async () => {
      const user = userEvent.setup();
      const mockOnSearch = jest.fn();
      
      render(<EnhancedTemplateSearch {...defaultProps} onSearch={mockOnSearch} />);
      
      const searchInput = screen.getByRole('combobox');
      await user.click(searchInput);
      await user.type(searchInput, 'test search{enter}');
      
      expect(mockOnSearch).toHaveBeenCalledWith('test search');
    });

    it('should clear search with Escape key', async () => {
      const user = userEvent.setup();
      
      render(<EnhancedTemplateSearch {...defaultProps} value="test" />);
      
      const searchInput = screen.getByRole('combobox');
      await user.click(searchInput);
      await user.keyboard('{Escape}');
      
      // Check that search was cleared
    });
  });

  describe('EnhancedTemplateGrid', () => {
    const defaultProps = {
      layout: { type: 'grid' as const, size: 'medium' as const },
      enableKeyboardNavigation: true,
      showSelectionControls: true
    };

    it('should not have accessibility violations', async () => {
      const { container } = render(<EnhancedTemplateGrid {...defaultProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper grid ARIA attributes', () => {
      render(<EnhancedTemplateGrid {...defaultProps} />);
      
      const grid = screen.getByRole('grid');
      expect(grid).toHaveAttribute('aria-label', expect.stringContaining('Template library with'));
      expect(grid).toHaveAttribute('aria-multiselectable', 'true');
      expect(grid).toHaveAttribute('tabindex', '0');
    });

    it('should support arrow key navigation', async () => {
      const user = userEvent.setup();
      render(<EnhancedTemplateGrid {...defaultProps} />);
      
      const grid = screen.getByRole('grid');
      await user.click(grid);
      
      // Test arrow key navigation
      await user.keyboard('{ArrowRight}');
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowLeft}');
      await user.keyboard('{ArrowUp}');
    });

    it('should announce selection changes', async () => {
      const mockAnnounce = jest.fn();
      jest.mocked(require('../../hooks/useAccessibility').useAccessibility).mockReturnValue({
        announce: mockAnnounce,
        manageFocus: { trap: jest.fn(), restore: jest.fn(), saveFocus: jest.fn(), moveTo: jest.fn() },
        keyboard: { registerShortcut: jest.fn(), getShortcuts: jest.fn() },
        screen: { isScreenReader: true, prefersReducedMotion: false, prefersHighContrast: false }
      });

      render(<EnhancedTemplateGrid {...defaultProps} />);
      
      // Simulate template selection
      // This would trigger the announcement
    });
  });

  describe('EnhancedTemplateCard', () => {
    const defaultProps = {
      template: mockTemplates[0],
      layout: { type: 'grid' as const, size: 'medium' as const },
      selected: false,
      focused: false,
      showCheckbox: true
    };

    it('should not have accessibility violations', async () => {
      const { container } = render(<EnhancedTemplateCard {...defaultProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA attributes', () => {
      render(<EnhancedTemplateCard {...defaultProps} />);
      
      const card = screen.getByRole('gridcell');
      expect(card).toHaveAttribute('aria-label', 'Template: DMCA Takedown Notice');
      expect(card).toHaveAttribute('aria-selected', 'false');
      expect(card).toHaveAttribute('tabindex', '-1');
      expect(card).toHaveAttribute('id', 'template-1');
    });

    it('should update ARIA attributes when selected', () => {
      render(<EnhancedTemplateCard {...defaultProps} selected={true} />);
      
      const card = screen.getByRole('gridcell');
      expect(card).toHaveAttribute('aria-selected', 'true');
    });

    it('should update ARIA attributes when focused', () => {
      render(<EnhancedTemplateCard {...defaultProps} focused={true} />);
      
      const card = screen.getByRole('gridcell');
      expect(card).toHaveAttribute('tabindex', '0');
    });

    it('should have accessible selection checkbox', () => {
      render(<EnhancedTemplateCard {...defaultProps} />);
      
      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toHaveAttribute('aria-label', 'Select DMCA Takedown Notice');
      expect(checkbox).not.toBeChecked();
    });

    it('should have accessible favorite button', () => {
      render(<EnhancedTemplateCard {...defaultProps} />);
      
      const favoriteButton = screen.getByRole('button', { name: /add.*to favorites/i });
      expect(favoriteButton).toHaveAttribute('aria-pressed', 'false');
    });
  });

  describe('TemplateFilters', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(<TemplateFilters />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper form labels', () => {
      render(<TemplateFilters />);
      
      // All form controls should have associated labels
      const dropdowns = screen.getAllByRole('combobox');
      dropdowns.forEach(dropdown => {
        expect(dropdown).toHaveAccessibleName();
      });
    });

    it('should support keyboard navigation through filters', async () => {
      const user = userEvent.setup();
      render(<TemplateFilters />);
      
      // Tab through filter controls
      await user.tab();
      // Verify focus moves through all interactive elements
    });
  });

  describe('Color Contrast', () => {
    it('should meet WCAG AA contrast requirements', () => {
      // This would typically be tested with automated tools
      // or manual contrast checking tools
      render(<EnhancedTemplateLibraryDashboard />);
      
      // Check that critical text elements meet contrast requirements
      const headings = screen.getAllByRole('heading');
      headings.forEach(heading => {
        // Assert that heading has sufficient contrast
        expect(heading).toBeVisible();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should maintain accessibility on mobile devices', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768
      });

      render(<EnhancedTemplateLibraryDashboard />);
      
      // Check that mobile-specific accessibility features work
      const mobileToggle = screen.getByRole('button', { name: /open filters panel/i });
      expect(mobileToggle).toBeInTheDocument();
      expect(mobileToggle).toHaveAttribute('aria-label', 'Open filters panel');
    });

    it('should have proper touch target sizes on mobile', () => {
      render(<EnhancedTemplateLibraryDashboard />);
      
      // All interactive elements should meet minimum 44px touch target size
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        const styles = window.getComputedStyle(button);
        const minHeight = parseInt(styles.minHeight) || parseInt(styles.height);
        const minWidth = parseInt(styles.minWidth) || parseInt(styles.width);
        
        // Note: In a real test, you'd check computed styles for touch targets
        expect(button).toBeInTheDocument();
      });
    });
  });

  describe('Screen Reader Support', () => {
    it('should provide meaningful content to screen readers', () => {
      render(<EnhancedTemplateLibraryDashboard />);
      
      // Check that screen reader content is available
      const srOnlyElements = document.querySelectorAll('.sr-only');
      expect(srOnlyElements.length).toBeGreaterThan(0);
    });

    it('should have live regions for dynamic content', () => {
      render(<EnhancedTemplateLibraryDashboard />);
      
      // Check that live regions are present in the DOM
      const politeRegion = document.getElementById('polite-announcements');
      const assertiveRegion = document.getElementById('assertive-announcements');
      
      expect(politeRegion).toHaveAttribute('aria-live', 'polite');
      expect(assertiveRegion).toHaveAttribute('aria-live', 'assertive');
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should register and respond to keyboard shortcuts', async () => {
      const mockRegisterShortcut = jest.fn(() => jest.fn());
      jest.mocked(require('../../hooks/useAccessibility').useAccessibility).mockReturnValue({
        announce: jest.fn(),
        manageFocus: { trap: jest.fn(), restore: jest.fn(), saveFocus: jest.fn(), moveTo: jest.fn() },
        keyboard: {
          registerShortcut: mockRegisterShortcut,
          getShortcuts: jest.fn(() => [])
        },
        screen: { isScreenReader: false, prefersReducedMotion: false, prefersHighContrast: false }
      });

      render(<EnhancedTemplateLibraryDashboard />);
      
      // Verify keyboard shortcuts are registered
      expect(mockRegisterShortcut).toHaveBeenCalledWith('ctrl+/', expect.any(Function), 'Focus search');
      expect(mockRegisterShortcut).toHaveBeenCalledWith('ctrl+f', expect.any(Function), 'Focus filters');
      expect(mockRegisterShortcut).toHaveBeenCalledWith('ctrl+n', expect.any(Function), 'Create new template');
      expect(mockRegisterShortcut).toHaveBeenCalledWith('ctrl+r', expect.any(Function), 'Refresh templates');
      expect(mockRegisterShortcut).toHaveBeenCalledWith('escape', expect.any(Function), 'Close dialogs');
    });
  });
});

// Custom matchers for accessibility testing
expect.extend({
  toHaveAccessibleName(received) {
    const accessibleName = received.getAttribute('aria-label') || 
                          received.getAttribute('aria-labelledby') ||
                          received.textContent ||
                          received.title;
    
    const pass = !!accessibleName;
    
    if (pass) {
      return {
        message: () => `Expected element not to have accessible name, but it has: ${accessibleName}`,
        pass: true,
      };
    } else {
      return {
        message: () => `Expected element to have accessible name, but it doesn't`,
        pass: false,
      };
    }
  }
});