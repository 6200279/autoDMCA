import { test, expect, Page, BrowserContext } from '@playwright/test';
import { chromium } from 'playwright';

// Test data
const testTemplate = {
  name: 'E2E Test Template',
  description: 'Template created during E2E testing',
  category: 'Social Media',
  content: `Dear {{platform}} Team,

I am writing to report copyright infringement of my original work.

Work Title: {{work_title}}
Infringing URL: {{infringing_url}}
Original Work URL: {{original_url}}

I have a good faith belief that the use of this material is not authorized by the copyright owner, its agent, or the law.

I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or authorized to act on behalf of the copyright owner.

Sincerely,
{{creator_name}}
{{contact_email}}`,
  variables: [
    { name: 'platform', label: 'Platform Name', type: 'text', required: true },
    { name: 'work_title', label: 'Work Title', type: 'text', required: true },
    { name: 'infringing_url', label: 'Infringing URL', type: 'url', required: true },
    { name: 'original_url', label: 'Original Work URL', type: 'url', required: false },
    { name: 'creator_name', label: 'Creator Name', type: 'text', required: true },
    { name: 'contact_email', label: 'Contact Email', type: 'email', required: true }
  ]
};

// Page Object Model
class TemplateLibraryPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/templates');
    await this.page.waitForSelector('[data-testid="template-library-dashboard"]');
  }

  async waitForTemplatesLoad() {
    await this.page.waitForSelector('[data-testid="templates-grid-view"], [data-testid="templates-list-view"]', {
      timeout: 10000
    });
  }

  async searchTemplates(query: string) {
    await this.page.fill('[data-testid="template-search-input"]', query);
    await this.page.waitForTimeout(1000); // Wait for debounce
  }

  async filterByCategory(category: string) {
    await this.page.click('[data-testid="category-filter"]');
    await this.page.click(`[data-testid="category-option-${category.toLowerCase().replace(/\s+/g, '-')}"]`);
  }

  async switchToListView() {
    await this.page.click('[data-testid="list-view-toggle"]');
    await this.page.waitForSelector('[data-testid="templates-list-view"]');
  }

  async switchToGridView() {
    await this.page.click('[data-testid="grid-view-toggle"]');
    await this.page.waitForSelector('[data-testid="templates-grid-view"]');
  }

  async selectTemplate(templateName: string) {
    const templateCard = this.page.locator(`[data-testid="template-card"]:has-text("${templateName}")`);
    await templateCard.locator('input[type="checkbox"]').check();
  }

  async bulkDeleteSelected() {
    await this.page.click('[data-testid="bulk-delete-button"]');
    await this.page.click('[data-testid="confirm-delete-button"]');
  }

  async openCreateWizard() {
    await this.page.click('[data-testid="create-template-button"]');
  }

  async openTemplateEditor(templateName: string) {
    const templateCard = this.page.locator(`[data-testid="template-card"]:has-text("${templateName}")`);
    await templateCard.locator('[data-testid="edit-template-button"]').click();
  }

  async viewTemplate(templateName: string) {
    const templateCard = this.page.locator(`[data-testid="template-card"]:has-text("${templateName}")`);
    await templateCard.locator('[data-testid="view-template-button"]').click();
  }
}

class TemplateCreationWizardPage {
  constructor(private page: Page) {}

  async waitForWizardLoad() {
    await this.page.waitForSelector('[data-testid="template-creation-wizard"]');
  }

  async selectStarterTemplate(starterName: string) {
    await this.page.click(`[data-testid="starter-template"]:has-text("${starterName}")`);
  }

  async startFromScratch() {
    await this.page.click('[data-testid="start-from-scratch"]');
  }

  async nextStep() {
    await this.page.click('[data-testid="wizard-next-button"]');
  }

  async previousStep() {
    await this.page.click('[data-testid="wizard-back-button"]');
  }

  async fillBasicInfo(templateData: typeof testTemplate) {
    await this.page.fill('[data-testid="template-name-input"]', templateData.name);
    await this.page.fill('[data-testid="template-description-input"]', templateData.description);
    await this.page.selectOption('[data-testid="template-category-select"]', templateData.category);
  }

  async fillContent(content: string) {
    await this.page.fill('[data-testid="template-content-editor"]', content);
  }

  async addVariable(variable: typeof testTemplate.variables[0]) {
    await this.page.click('[data-testid="add-variable-button"]');
    
    const variableForm = this.page.locator('[data-testid="variable-form"]').last();
    await variableForm.locator('[data-testid="variable-name-input"]').fill(variable.name);
    await variableForm.locator('[data-testid="variable-label-input"]').fill(variable.label);
    await variableForm.locator('[data-testid="variable-type-select"]').selectOption(variable.type);
    
    if (variable.required) {
      await variableForm.locator('[data-testid="variable-required-checkbox"]').check();
    }
    
    await variableForm.locator('[data-testid="save-variable-button"]').click();
  }

  async previewTemplate() {
    await this.page.click('[data-testid="preview-template-button"]');
    await this.page.waitForSelector('[data-testid="template-preview"]');
  }

  async saveTemplate() {
    await this.page.click('[data-testid="save-template-button"]');
    await this.page.waitForSelector('[data-testid="template-saved-success"]', { timeout: 5000 });
  }

  async closeWizard() {
    await this.page.click('[data-testid="close-wizard-button"]');
  }
}

class TemplateEditorPage {
  constructor(private page: Page) {}

  async waitForEditorLoad() {
    await this.page.waitForSelector('[data-testid="enhanced-template-editor"]');
  }

  async editTemplateContent(content: string) {
    await this.page.fill('[data-testid="template-content-editor"]', content);
  }

  async insertVariable(variableName: string) {
    await this.page.click(`[data-testid="insert-variable-${variableName}"]`);
  }

  async addNewVariable(variable: typeof testTemplate.variables[0]) {
    await this.page.click('[data-testid="add-variable-button"]');
    
    const variableDialog = this.page.locator('[data-testid="variable-dialog"]');
    await variableDialog.locator('[data-testid="variable-name-input"]').fill(variable.name);
    await variableDialog.locator('[data-testid="variable-label-input"]').fill(variable.label);
    await variableDialog.locator('[data-testid="variable-type-select"]').selectOption(variable.type);
    
    await variableDialog.locator('[data-testid="save-variable-button"]').click();
  }

  async updatePreviewData(variableName: string, value: string) {
    await this.page.fill(`[data-testid="preview-variable-${variableName}"]`, value);
    await this.page.click('[data-testid="refresh-preview-button"]');
  }

  async saveTemplate() {
    await this.page.click('[data-testid="save-template-button"]');
    await this.page.waitForSelector('[data-testid="template-saved-indicator"]');
  }

  async closeEditor() {
    await this.page.click('[data-testid="close-editor-button"]');
  }

  async getValidationScore() {
    const scoreElement = await this.page.locator('[data-testid="compliance-score"]');
    return await scoreElement.textContent();
  }

  async getPreviewContent() {
    const previewElement = await this.page.locator('[data-testid="preview-content"]');
    return await previewElement.textContent();
  }
}

// Test Setup
test.beforeEach(async ({ page }) => {
  // Mock API responses for E2E tests
  await page.route('**/api/v1/templates**', async route => {
    const url = route.request().url();
    const method = route.request().method();
    
    if (method === 'GET' && url.includes('/templates')) {
      // Return mock template list
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          templates: [],
          total: 0,
          page: 1,
          limit: 20,
          total_pages: 0,
          has_next: false,
          has_prev: false
        })
      });
    } else if (method === 'POST' && url.includes('/templates')) {
      // Mock template creation
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-template-1',
          ...testTemplate,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_active: true,
          is_system: false
        })
      });
    } else {
      await route.continue();
    }
  });

  // Mock categories endpoint
  await page.route('**/api/v1/templates/categories', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: '1', name: 'General DMCA', template_count: 10 },
        { id: '2', name: 'Social Media', template_count: 15 },
        { id: '3', name: 'Video Platforms', template_count: 8 }
      ])
    });
  });

  // Mock template starters
  await page.route('**/api/v1/templates/starters', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'starter-1',
          name: 'Social Media DMCA',
          description: 'Template for social media platforms',
          category: 'Social Media',
          content: 'Dear {{platform}}, I am reporting copyright infringement...',
          variables: [
            { name: 'platform', label: 'Platform Name', type: 'text', required: true }
          ]
        }
      ])
    });
  });

  // Mock validation endpoint
  await page.route('**/api/v1/templates/validate', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        is_valid: true,
        errors: [],
        warnings: [],
        compliance_score: 85
      })
    });
  });

  // Mock preview endpoint
  await page.route('**/api/v1/templates/preview', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        rendered_content: 'Dear YouTube Team, I am reporting copyright infringement of My Song...',
        missing_variables: [],
        validation_errors: {}
      })
    });
  });

  // Navigate to login and authenticate (mock auth)
  await page.goto('/login');
  await page.fill('[data-testid="email-input"]', 'test@example.com');
  await page.fill('[data-testid="password-input"]', 'password123');
  await page.click('[data-testid="login-button"]');
  
  // Wait for dashboard to load
  await page.waitForURL('**/dashboard');
});

test.describe('Template Library Dashboard Workflows', () => {
  test('should display template library with proper layout', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Check main elements are present
    await expect(page.locator('[data-testid="template-library-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="template-search-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="category-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="create-template-button"]')).toBeVisible();
  });

  test('should search and filter templates effectively', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Test search functionality
    await templateLibrary.searchTemplates('Social Media');
    
    // Verify search was triggered (via network request)
    await page.waitForTimeout(1500); // Wait for debounce + API call

    // Test category filtering
    await templateLibrary.filterByCategory('Social Media');
    
    // Verify filter was applied
    await page.waitForTimeout(500);
  });

  test('should switch between grid and list view modes', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Switch to list view
    await templateLibrary.switchToListView();
    await expect(page.locator('[data-testid="templates-list-view"]')).toBeVisible();

    // Switch back to grid view
    await templateLibrary.switchToGridView();
    await expect(page.locator('[data-testid="templates-grid-view"]')).toBeVisible();
  });

  test('should handle empty state properly', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Should show empty state when no templates
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
    await expect(page.locator('text=No templates found')).toBeVisible();
    await expect(page.locator('text=Create your first template')).toBeVisible();
  });
});

test.describe('Template Creation Wizard Workflows', () => {
  test('should complete full template creation workflow', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const wizard = new TemplateCreationWizardPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    await wizard.waitForWizardLoad();

    // Step 1: Select template type
    await wizard.startFromScratch();
    await wizard.nextStep();

    // Step 2: Basic information
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();

    // Step 3: Content creation
    await wizard.fillContent(testTemplate.content);
    await wizard.nextStep();

    // Step 4: Variables setup
    for (const variable of testTemplate.variables) {
      await wizard.addVariable(variable);
    }
    await wizard.nextStep();

    // Step 5: Preview and finalize
    await wizard.previewTemplate();
    await expect(page.locator('[data-testid="template-preview"]')).toBeVisible();
    
    await wizard.saveTemplate();
    
    // Should show success message and close wizard
    await expect(page.locator('[data-testid="template-saved-success"]')).toBeVisible();
  });

  test('should create template from starter', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const wizard = new TemplateCreationWizardPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    await wizard.waitForWizardLoad();

    // Select starter template
    await wizard.selectStarterTemplate('Social Media DMCA');
    await wizard.nextStep();

    // Should pre-populate basic info from starter
    await expect(page.locator('[data-testid="template-name-input"]')).toHaveValue('Social Media DMCA');
    
    // Continue through workflow
    await wizard.nextStep(); // Skip to content
    await wizard.nextStep(); // Skip to variables (should be pre-populated)
    await wizard.nextStep(); // Go to preview
    
    await wizard.saveTemplate();
    await expect(page.locator('[data-testid="template-saved-success"]')).toBeVisible();
  });

  test('should validate required fields in wizard', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const wizard = new TemplateCreationWizardPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    await wizard.waitForWizardLoad();

    // Try to proceed without selecting template type
    await wizard.nextStep();
    
    // Should show validation error
    await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();

    // Select template type and proceed
    await wizard.startFromScratch();
    await wizard.nextStep();

    // Try to proceed without filling required basic info
    await wizard.nextStep();
    
    // Should show field validation errors
    await expect(page.locator('text=Template name is required')).toBeVisible();
  });

  test('should support wizard navigation (back/forward)', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const wizard = new TemplateCreationWizardPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    await wizard.waitForWizardLoad();

    // Navigate forward through steps
    await wizard.startFromScratch();
    await wizard.nextStep();
    
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();

    // Navigate back
    await wizard.previousStep();
    
    // Should be on basic info step with preserved data
    await expect(page.locator('[data-testid="template-name-input"]')).toHaveValue(testTemplate.name);

    // Navigate forward again
    await wizard.nextStep();
    await wizard.nextStep(); // Content step
  });
});

test.describe('Template Editor Workflows', () => {
  test('should edit template content and variables', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const editor = new TemplateEditorPage(page);
    
    // First create a template to edit
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    
    const wizard = new TemplateCreationWizardPage(page);
    await wizard.waitForWizardLoad();
    
    // Quick template creation
    await wizard.startFromScratch();
    await wizard.nextStep();
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();
    await wizard.fillContent(testTemplate.content);
    await wizard.nextStep();
    await wizard.nextStep(); // Skip variables for now
    await wizard.saveTemplate();

    // Now edit the created template
    await templateLibrary.goto();
    await templateLibrary.openTemplateEditor(testTemplate.name);
    await editor.waitForEditorLoad();

    // Edit content
    const updatedContent = testTemplate.content + '\n\nAdditional content added in editor.';
    await editor.editTemplateContent(updatedContent);

    // Add a new variable
    await editor.addNewVariable({
      name: 'additional_info',
      label: 'Additional Information',
      type: 'textarea',
      required: false
    });

    // Insert the new variable into content
    await editor.insertVariable('additional_info');

    // Save changes
    await editor.saveTemplate();
    
    // Should show save confirmation
    await expect(page.locator('[data-testid="template-saved-indicator"]')).toBeVisible();
  });

  test('should provide real-time preview with variable values', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const editor = new TemplateEditorPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    
    // Create template with variables
    const wizard = new TemplateCreationWizardPage(page);
    await wizard.waitForWizardLoad();
    await wizard.startFromScratch();
    await wizard.nextStep();
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();
    await wizard.fillContent(testTemplate.content);
    await wizard.nextStep();
    
    // Add variables
    for (const variable of testTemplate.variables.slice(0, 2)) {
      await wizard.addVariable(variable);
    }
    await wizard.nextStep();
    await wizard.saveTemplate();

    // Open editor
    await templateLibrary.goto();
    await templateLibrary.openTemplateEditor(testTemplate.name);
    await editor.waitForEditorLoad();

    // Update preview data
    await editor.updatePreviewData('platform', 'YouTube');
    await editor.updatePreviewData('work_title', 'My Original Song');

    // Check preview updates
    const previewContent = await editor.getPreviewContent();
    expect(previewContent).toContain('YouTube');
    expect(previewContent).toContain('My Original Song');
  });

  test('should display validation and compliance scores', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const editor = new TemplateEditorPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    
    // Create template
    const wizard = new TemplateCreationWizardPage(page);
    await wizard.waitForWizardLoad();
    await wizard.startFromScratch();
    await wizard.nextStep();
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();
    await wizard.fillContent(testTemplate.content);
    await wizard.nextStep();
    await wizard.nextStep();
    await wizard.saveTemplate();

    // Open editor
    await templateLibrary.goto();
    await templateLibrary.openTemplateEditor(testTemplate.name);
    await editor.waitForEditorLoad();

    // Check validation panel
    await expect(page.locator('[data-testid="validation-panel"]')).toBeVisible();
    
    // Check compliance score
    const complianceScore = await editor.getValidationScore();
    expect(complianceScore).toContain('85'); // From mock
  });

  test('should auto-save changes periodically', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const editor = new TemplateEditorPage(page);
    
    // Create and open template for editing
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    
    const wizard = new TemplateCreationWizardPage(page);
    await wizard.waitForWizardLoad();
    await wizard.startFromScratch();
    await wizard.nextStep();
    await wizard.fillBasicInfo(testTemplate);
    await wizard.nextStep();
    await wizard.fillContent(testTemplate.content);
    await wizard.nextStep();
    await wizard.nextStep();
    await wizard.saveTemplate();

    await templateLibrary.goto();
    await templateLibrary.openTemplateEditor(testTemplate.name);
    await editor.waitForEditorLoad();

    // Make changes to trigger auto-save
    await page.fill('[data-testid="template-name-input"]', 'Auto-save Test Template');

    // Wait for auto-save indicator
    await expect(page.locator('[data-testid="auto-save-indicator"]')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Accessibility and Keyboard Navigation', () => {
  test('should support keyboard navigation throughout templates UI', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Test tab navigation
    await page.keyboard.press('Tab'); // Search input
    await expect(page.locator('[data-testid="template-search-input"]')).toBeFocused();

    await page.keyboard.press('Tab'); // Category filter
    await expect(page.locator('[data-testid="category-filter"]')).toBeFocused();

    await page.keyboard.press('Tab'); // Status filter
    await expect(page.locator('[data-testid="status-filter"]')).toBeFocused();

    // Test escape key functionality
    await templateLibrary.openCreateWizard();
    await page.keyboard.press('Escape');
    
    // Wizard should close
    await expect(page.locator('[data-testid="template-creation-wizard"]')).not.toBeVisible();
  });

  test('should have proper ARIA labels and screen reader support', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Check ARIA labels
    await expect(page.locator('[data-testid="template-search-input"]')).toHaveAttribute('aria-label', /search/i);
    await expect(page.locator('[data-testid="template-library-dashboard"]')).toHaveAttribute('role', 'main');
    await expect(page.locator('[data-testid="templates-grid-view"]')).toHaveAttribute('role', 'grid');
  });

  test('should announce dynamic content changes to screen readers', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Search should announce results
    await templateLibrary.searchTemplates('test');
    
    // Check for live region
    await expect(page.locator('[aria-live="polite"]')).toBeVisible();
  });
});

test.describe('Error Handling and Edge Cases', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/templates', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    const templateLibrary = new TemplateLibraryPage(page);
    await templateLibrary.goto();

    // Should show error state
    await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
    await expect(page.locator('text=Error loading templates')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
  });

  test('should handle network connectivity issues', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    await templateLibrary.goto();

    // Simulate network failure
    await page.context().setOffline(true);

    // Trigger an action that requires network
    await templateLibrary.openCreateWizard();
    
    // Should show offline message
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

    // Restore connectivity
    await page.context().setOffline(false);
    
    // Should recover automatically
    await expect(page.locator('[data-testid="offline-indicator"]')).not.toBeVisible({ timeout: 5000 });
  });

  test('should validate form inputs and show appropriate errors', async ({ page }) => {
    const templateLibrary = new TemplateLibraryPage(page);
    const wizard = new TemplateCreationWizardPage(page);
    
    await templateLibrary.goto();
    await templateLibrary.openCreateWizard();
    await wizard.waitForWizardLoad();

    await wizard.startFromScratch();
    await wizard.nextStep();

    // Fill invalid data
    await page.fill('[data-testid="template-name-input"]', ''); // Empty name
    await page.fill('[data-testid="template-description-input"]', 'a'.repeat(1000)); // Too long description

    await wizard.nextStep();

    // Should show validation errors
    await expect(page.locator('text=Template name is required')).toBeVisible();
    await expect(page.locator('text=Description too long')).toBeVisible();
  });
});

test.describe('Performance and Load Testing', () => {
  test('should handle large template lists efficiently', async ({ page }) => {
    // Mock large dataset
    await page.route('**/api/v1/templates', async route => {
      const templates = Array.from({ length: 100 }, (_, i) => ({
        id: `template-${i}`,
        name: `Template ${i}`,
        description: `Description ${i}`,
        category: 'General DMCA',
        is_active: true,
        created_at: new Date().toISOString()
      }));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          templates: templates.slice(0, 20), // First page
          total: 100,
          page: 1,
          limit: 20,
          total_pages: 5,
          has_next: true,
          has_prev: false
        })
      });
    });

    const templateLibrary = new TemplateLibraryPage(page);
    
    const startTime = Date.now();
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();
    const endTime = Date.now();

    // Should load within reasonable time
    expect(endTime - startTime).toBeLessThan(5000); // 5 seconds
    
    // Should show pagination
    await expect(page.locator('[data-testid="pagination"]')).toBeVisible();
  });

  test('should debounce search input appropriately', async ({ page }) => {
    let apiCallCount = 0;
    
    await page.route('**/api/v1/templates*', async route => {
      apiCallCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ templates: [], total: 0 })
      });
    });

    const templateLibrary = new TemplateLibraryPage(page);
    await templateLibrary.goto();
    
    const initialCalls = apiCallCount;
    
    // Type rapidly
    const searchInput = page.locator('[data-testid="template-search-input"]');
    await searchInput.type('rapid typing test', { delay: 50 });

    // Wait for debounce period
    await page.waitForTimeout(1000);

    // Should have made minimal API calls due to debouncing
    expect(apiCallCount - initialCalls).toBeLessThanOrEqual(2);
  });
});

test.describe('Mobile Responsiveness', () => {
  test('should adapt layout for mobile devices', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    const templateLibrary = new TemplateLibraryPage(page);
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Should show mobile layout
    await expect(page.locator('[data-testid="mobile-sidebar-toggle"]')).toBeVisible();
    
    // Grid should use single column
    const gridContainer = page.locator('[data-testid="templates-grid-view"]');
    await expect(gridContainer).toHaveClass(/mobile-single-column/);
  });

  test('should provide touch-friendly interactions', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    const templateLibrary = new TemplateLibraryPage(page);
    await templateLibrary.goto();
    await templateLibrary.waitForTemplatesLoad();

    // Touch targets should be appropriately sized
    const buttons = page.locator('button');
    const count = await buttons.count();
    
    for (let i = 0; i < count; i++) {
      const button = buttons.nth(i);
      const box = await button.boundingBox();
      if (box) {
        // Minimum touch target size (44px)
        expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(40);
      }
    }
  });
});