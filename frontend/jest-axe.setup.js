// Jest-axe setup for accessibility testing
import { configureAxe } from 'jest-axe';

// Configure axe-core for our accessibility tests
const axe = configureAxe({
  // Global rules configuration
  rules: {
    // Enable specific accessibility rules
    'color-contrast': { enabled: true },
    'keyboard-navigation': { enabled: true },
    'focus-management': { enabled: true },
    'aria-labels': { enabled: true },
    'semantic-structure': { enabled: true },
    
    // Disable rules that may not apply to our test environment
    'landmark-one-main': { enabled: false }, // Our components are fragments
    'page-has-heading-one': { enabled: false }, // Components don't always need h1
    'region': { enabled: false } // May conflict with component isolation
  },
  
  // Global tags to test against
  tags: ['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice'],
  
  // Default options for all tests
  globalOptions: {
    // Increase timeout for slower CI environments
    timeout: 10000,
    
    // Include hidden elements in testing
    includeHidden: false,
    
    // Custom rule options
    rules: {
      // Color contrast requirements
      'color-contrast': {
        options: {
          noScroll: true,
          pseudoSizingMethod: 'scroll'
        }
      }
    }
  }
});

// Custom matchers for accessibility testing
expect.extend({
  async toPassAccessibilityAudit(received) {
    const results = await axe(received);
    const pass = results.violations.length === 0;
    
    if (pass) {
      return {
        message: () => `Expected element to have accessibility violations`,
        pass: true,
      };
    } else {
      const violationMessages = results.violations.map(violation => {
        const nodeMessages = violation.nodes.map(node => 
          `    - ${node.failureSummary}`
        ).join('\n');
        
        return `  ${violation.id}: ${violation.description}\n${nodeMessages}`;
      }).join('\n');
      
      return {
        message: () => `Expected element to pass accessibility audit but found ${results.violations.length} violations:\n${violationMessages}`,
        pass: false,
      };
    }
  },
  
  async toHaveNoAccessibilityViolations(received) {
    const results = await axe(received);
    const violations = results.violations;
    
    if (violations.length === 0) {
      return {
        message: () => `Expected element to have accessibility violations`,
        pass: true,
      };
    }
    
    const violationDetails = violations.map(violation => ({
      rule: violation.id,
      description: violation.description,
      impact: violation.impact,
      help: violation.help,
      helpUrl: violation.helpUrl,
      nodes: violation.nodes.length
    }));
    
    return {
      message: () => [
        `Expected no accessibility violations but found ${violations.length}:`,
        '',
        ...violationDetails.map(v => 
          `• ${v.rule} (${v.impact}): ${v.description}`
        ),
        '',
        'See the full axe-core report for details on how to fix these issues.'
      ].join('\n'),
      pass: false,
    };
  }
});

// Template-specific accessibility configurations
export const templateAccessibilityConfig = {
  // Configuration for template dashboard
  dashboard: {
    rules: {
      'scrollable-region-focusable': { enabled: false }, // Virtual scrolling
      'aria-dialog-name': { enabled: false }, // Modals handled separately
    }
  },
  
  // Configuration for template editor
  editor: {
    rules: {
      'aria-input-field-name': { enabled: true },
      'label-content-name-mismatch': { enabled: true },
      'form-field-multiple-labels': { enabled: false }, // Rich editors
    }
  },
  
  // Configuration for creation wizard
  wizard: {
    rules: {
      'aria-required-children': { enabled: false }, // Dynamic step content
      'aria-required-parent': { enabled: false }, // Dynamic step content
    }
  }
};

// Helper functions for common accessibility testing patterns
export const accessibilityTestHelpers = {
  // Test keyboard navigation through a component
  testKeyboardNavigation: async (container, expectedFocusableElements) => {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    expect(focusableElements).toHaveLength(expectedFocusableElements);
    
    // Test tab order
    for (let i = 0; i < focusableElements.length; i++) {
      focusableElements[i].focus();
      expect(document.activeElement).toBe(focusableElements[i]);
      
      // Simulate tab key
      await userEvent.keyboard('{Tab}');
    }
  },
  
  // Test screen reader announcements
  testScreenReaderAnnouncements: (container) => {
    const liveRegions = container.querySelectorAll('[aria-live]');
    const alerts = container.querySelectorAll('[role="alert"]');
    const status = container.querySelectorAll('[role="status"]');
    
    return {
      liveRegions: liveRegions.length,
      alerts: alerts.length,
      status: status.length,
      total: liveRegions.length + alerts.length + status.length
    };
  },
  
  // Test ARIA labels and descriptions
  testAriaLabels: (container) => {
    const ariaLabelled = container.querySelectorAll('[aria-label], [aria-labelledby]');
    const ariaDescribed = container.querySelectorAll('[aria-describedby]');
    const ariaExpanded = container.querySelectorAll('[aria-expanded]');
    
    return {
      labelled: ariaLabelled.length,
      described: ariaDescribed.length,
      expanded: ariaExpanded.length
    };
  },
  
  // Test form accessibility
  testFormAccessibility: (form) => {
    const formControls = form.querySelectorAll('input, select, textarea');
    const labels = form.querySelectorAll('label');
    const fieldsets = form.querySelectorAll('fieldset');
    const legends = form.querySelectorAll('legend');
    
    // Check that form controls have labels
    formControls.forEach(control => {
      const hasLabel = control.getAttribute('aria-label') ||
                      control.getAttribute('aria-labelledby') ||
                      form.querySelector(`label[for="${control.id}"]`);
      
      expect(hasLabel).toBeTruthy();
    });
    
    // Check fieldsets have legends
    fieldsets.forEach(fieldset => {
      const legend = fieldset.querySelector('legend');
      expect(legend).toBeTruthy();
    });
    
    return {
      controls: formControls.length,
      labels: labels.length,
      fieldsets: fieldsets.length,
      legends: legends.length
    };
  }
};

// Export configured axe instance
export default axe;